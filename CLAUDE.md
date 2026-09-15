# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An umbrelOS community app store (`umbrel-app-store.yml`, id `longstreet`) shipping two apps:
`longstreet-litecoin` and `longstreet-dogecoin`. Each is a wallet-less Core full node plus a
Python status dashboard, intended to feed a future merged-mining app. There is no build system,
test suite, or package manager — the repo is shell, YAML, Dockerfiles, and one stdlib-only Python
file per app. CI on GitHub Actions does the building.

## Commands

```sh
# Check upstream Core releases (PGP-verified) without touching files; needs curl, gpg, jq
scripts/check-core-updates.sh --dry-run
scripts/check-core-updates.sh --dry-run litecoind     # one image only

# Build a node image locally (values from images/<name>/version.env)
docker build --build-arg VERSION=1.14.9 --build-arg SHA256=<sum> -t dogecoind images/dogecoind

# Run a status dashboard locally against any reachable node
COIN_NAME=Litecoin RPC_URL=http://host:9332 RPC_USER=u RPC_PASS=p python3 longstreet-litecoin/status/app.py

# On the Umbrel: talk to a running node using the runtime config entrypoint.sh assembled
docker exec longstreet-litecoin_litecoind_1 litecoin-cli -conf=/tmp/litecoin.conf -datadir=/data/.litecoin getblockchaininfo
docker logs -f longstreet-litecoin_litecoind_1
```

## Hard rule: every change to an app directory must bump its version

umbrelOS only offers an update when `version:` in `longstreet-<coin>/umbrel-app.yml` differs
from what is installed. The `check-versions` job in `.github/workflows/build_images.yml` fails
the push if any file under `longstreet-*/` (other than `.gitkeep`) changed without a version
bump. Bump `version` and update `releaseNotes` in the same commit. The app version is
independent of the Core version the image ships.

`scripts/check-core-updates.sh` bumps the patch version itself when it rewrites
`releaseNotes`, so a push straight after running it passes. If you edit *only*
`images/<name>/version.env` by hand (no manifest change), you may leave the version alone
and CI's `pin` job bumps it; but any manual touch to `umbrel-app.yml` needs the bump in the
same push. The `check-versions` job does not gate `build`/`pin` — those run regardless.

## The two apps are mirrors of each other

`longstreet-litecoin/` and `longstreet-dogecoin/` are deliberately parallel. Right now
`entrypoint.sh`, `status/app.py` and `hooks/pre-start` are byte-identical between them (verify with `diff`);
`docker-compose.yml`, `exports.sh`, `<coin>.conf`, and `umbrel-app.yml` differ only in coin
names, IPs, ports, and coin-specific conf lines. The same goes for `images/litecoind/` vs
`images/dogecoind/`. **When changing one, make the matching change in the other** unless the
difference is genuinely coin-specific (e.g. Litecoin's `blockfilterindex=0`, Dogecoin's
`MALLOC_ARENA_MAX`).

## Release pipeline (three files, two workflows)

1. `images/<name>/version.env` — Core `VERSION`, tarball `SHA256`, plus `UPSTREAM_REPO`,
   `ASSET`, `SUMS_URLS`, `APP_DIR`, `RELEASE_LABEL` consumed by the update checker.
2. `.github/workflows/check_core_updates.yml` (daily) runs `scripts/check-core-updates.sh`,
   which verifies upstream `SHA256SUMS.asc` **only** against keys in `keys/<name>/*.asc`
   and opens/updates a PR on branch `core-updates` editing `version.env`, the
   `releaseNotes` line matching `RELEASE_LABEL <version>`, and the app patch version. An unknown signer fails the check
   on purpose — see `keys/README.md` before adding a key.
3. `.github/workflows/build_images.yml` (every push to `main`) builds
   `ghcr.io/<owner>/<name>:<VERSION>` only if that tag doesn't exist, then the `pin` job
   rewrites the `image:` line in the app's `docker-compose.yml` to `tag@sha256:digest`, bumps
   the app patch version if this push didn't already, and pushes to `main` as
   `github-actions[bot]` (GITHUB_TOKEN pushes don't retrigger, so no loop).

Consequences: the `image:` line in `docker-compose.yml` is machine-managed — the `sed` in the
`pin` job matches `image: ghcr\.io/[^/]+/<name>:...`, so keep that shape. The `version:` line
in `umbrel-app.yml` is parsed by regex in both workflows; keep it quoted and on its own line.

## Runtime architecture per app

- **`docker-compose.yml`**: `app_proxy` → `status` container (python:3.12-alpine running
  `/app/app.py` bind-mounted from `${APP_DATA_DIR}/status`), and the `<coin>d` container
  running `entrypoint.sh` (also bind-mounted) as user 1000. Both get static IPs from
  `exports.sh`. `stop_grace_period: 15m` is load-bearing — a killed node mid-flush corrupts
  chainstate.
- **`exports.sh`**: sourced by umbreld; defines `APP_LONGSTREET_<COIN>_*` (IPs, RPC/P2P/ZMQ
  ports, RPC creds). These are the public contract for dependent apps. The RPC password is
  generated once with `openssl rand` and persisted to `${EXPORTS_APP_DIR}/.env`, which is
  sourced on every read. Never derive it from `$APP_SEED`: umbreld sources a dependency's
  exports.sh inside the dependent app's environment, where `APP_SEED` differs, so the node
  and its consumers would disagree on the password.
- **`entrypoint.sh`**: assembles `/tmp/<coin>.conf` at start from, in order,
  `$DATADIR/<coin>.local.conf` (user overrides, survives updates) → `dbcache=` → shipped
  `/etc/<coin>/<coin>.conf` → `rpcuser/rpcpassword`. Core keeps the *first* value it sees, so
  earlier sources win. It also runs the dbcache automation: start with `DBCACHE_IBD` (1536),
  a background watcher polls `getblockchaininfo`, and when `initialblockdownload` clears it
  touches `$DATADIR/.synced`, RPC-stops the node, and the outer loop relaunches with
  `DBCACHE_SYNCED` (450). A `dbcache=` in the local conf disables the automation. The
  signal-trap/`wait` dance at the bottom exists so a SIGTERM from Docker is forwarded and the
  daemon's real exit code is returned.
- **`<coin>.conf`**: shipped defaults; overwritten at every app start by the hook below, so
  never tell users to edit it — point them at `<coin>.local.conf` in the data dir.
- **`hooks/pre-start`**: umbrelOS app updates only re-copy `docker-compose.yml`, `exports.sh`,
  `umbrel-app.yml`, `*.template`, `torrc` and `hooks/` from the store checkout into
  `app-data` (see `UPDATE_FILES_WHITELIST_*` in umbreld's legacy `app-script`); everything
  else is copied on install only. This hook, run by umbreld before every start with
  `SCRIPT_APP_REPO_DIR` set to the store checkout, copies `entrypoint.sh`, `status/` and
  `<coin>.conf` over — but only when the checkout's `version:` equals the installed one, so a
  store refresh the user hasn't accepted can't leak into a restart. Any new bind-mounted
  file must be added to this hook or it will never reach existing installs.
- **`status/app.py`**: single-file `http.server` app; `/` serves inline HTML that polls `/api`.
  Includes a background sampler that extrapolates a sync ETA from `verificationprogress`.
  Must stay stdlib-only (stock alpine image, no pip step).
- **`images/<name>/Dockerfile`**: two-stage; fetches the official tarball, checks it against
  the `SHA256` build-arg, copies `<coin>d` and `<coin>-cli` into a bookworm-slim runtime as
  uid 1000.

## Things marked TODO in the repo

`port:` in each `umbrel-app.yml` and the `10.21.42.x` IPs in each `exports.sh` are flagged
as "confirm unused on your Umbrel" — don't remove those comments until they're verified.
