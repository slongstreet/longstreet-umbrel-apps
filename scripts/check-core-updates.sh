#!/usr/bin/env bash
# Check upstream for new Core releases and, if found, update images/<name>/version.env
# with the new version and a PGP-verified SHA256.
#
#   scripts/check-core-updates.sh            # check + update files in place
#   scripts/check-core-updates.sh --dry-run  # report only
#   scripts/check-core-updates.sh litecoind  # limit to one image
#
# Needs: curl, gpg, jq. Uses GITHUB_TOKEN/GH_TOKEN for the API if set.
# Exit 0 = nothing to do or files updated; 1 = verification/tooling failure.
set -euo pipefail
cd "$(dirname "$0")/.."

DRY_RUN=0
NAMES=()
for a in "$@"; do
  case "$a" in
    --dry-run) DRY_RUN=1 ;;
    *) NAMES+=("$a") ;;
  esac
done
[ ${#NAMES[@]} -gt 0 ] || NAMES=($(ls images))

for t in curl gpg jq; do command -v "$t" >/dev/null || { echo "missing tool: $t" >&2; exit 1; }; done

api() {
  local auth=()
  local tok="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
  [ -n "$tok" ] && auth=(-H "Authorization: Bearer $tok")
  curl -fsSL -H "Accept: application/vnd.github+json" "${auth[@]}" "https://api.github.com/$1"
}

UPDATED=()
FAILED=0
for name in "${NAMES[@]}"; do
  env_file="images/$name/version.env"
  [ -f "$env_file" ] || { echo "$name: no $env_file" >&2; FAILED=1; continue; }
  # shellcheck disable=SC1090
  source "$env_file"
  : "${VERSION:?}" "${SHA256:?}" "${UPSTREAM_REPO:?}" "${ASSET:?}" "${SUMS_URLS:?}"

  latest=$(api "repos/$UPSTREAM_REPO/releases?per_page=10" \
           | jq -r '[.[] | select(.prerelease == false and .draft == false)][0].tag_name')
  latest=${latest#v}
  if [ -z "$latest" ] || [ "$latest" = "null" ]; then
    echo "$name: could not determine latest release" >&2; FAILED=1; continue
  fi
  if [ "$latest" = "$VERSION" ]; then
    echo "$name: $VERSION is current"
    continue
  fi
  echo "$name: $VERSION -> $latest available"

  work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
  asset=${ASSET//\{VERSION\}/$latest}
  sums=""
  for url in $SUMS_URLS; do
    url=${url//\{VERSION\}/$latest}
    if curl -fsSL -o "$work/SHA256SUMS.asc" "$url"; then sums="$url"; break; fi
  done
  if [ -z "$sums" ]; then
    echo "$name: no SHA256SUMS.asc found for $latest at any known URL" >&2; FAILED=1; continue
  fi

  # Verify against ONLY the keys pinned in keys/<name>/.
  export GNUPGHOME="$work/gnupg"; mkdir -m 700 "$GNUPGHOME"
  gpg --batch --quiet --import keys/"$name"/*.asc
  if ! gpg --batch --status-fd 1 --verify "$work/SHA256SUMS.asc" 2>/dev/null | grep -q '^\[GNUPG:\] GOODSIG '; then
    echo "$name: SHA256SUMS.asc for $latest is NOT signed by a pinned key ($sums). Refusing." >&2
    gpg --batch --verify "$work/SHA256SUMS.asc" 2>&1 | sed 's/^/  /' >&2 || true
    FAILED=1; continue
  fi
  signer=$(gpg --batch --status-fd 1 --verify "$work/SHA256SUMS.asc" 2>/dev/null | sed -n 's/^\[GNUPG:\] GOODSIG [0-9A-F]* //p' | head -1)

  # The .asc is a clearsigned text file; pull the line for our tarball out of it.
  sha=$(gpg --batch --decrypt "$work/SHA256SUMS.asc" 2>/dev/null | awk -v f="$asset" '$2 == f { print $1 }' | head -1)
  if ! [[ "$sha" =~ ^[0-9a-f]{64}$ ]]; then
    echo "$name: $asset not listed in verified SHA256SUMS for $latest" >&2; FAILED=1; continue
  fi
  echo "$name: verified $asset"
  echo "$name:   sha256 $sha (signed by $signer)"

  if [ "$DRY_RUN" = 1 ]; then continue; fi
  sed -i.bak -E "s/^VERSION=.*/VERSION=$latest/; s/^SHA256=.*/SHA256=$sha/" "$env_file" && rm -f "$env_file.bak"
  if [ -n "${APP_DIR:-}" ] && [ -n "${RELEASE_LABEL:-}" ] && [ -f "$APP_DIR/umbrel-app.yml" ]; then
    sed -i.bak -E "s/$RELEASE_LABEL [0-9]+(\.[0-9]+)*/$RELEASE_LABEL $latest/" "$APP_DIR/umbrel-app.yml" && rm -f "$APP_DIR/umbrel-app.yml.bak"
  fi
  UPDATED+=("$name $VERSION $latest https://github.com/$UPSTREAM_REPO/releases/tag/v$latest")
  echo "$name: updated $env_file"
done

if [ -n "${GITHUB_OUTPUT:-}" ]; then
  {
    echo "updated<<EOT"; printf '%s\n' "${UPDATED[@]:-}"; echo "EOT"
  } >> "$GITHUB_OUTPUT"
fi
exit $FAILED
