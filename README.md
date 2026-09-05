# Longstreet Labs — Umbrel community app store

Apps:

| App ID | What it is | Exposes to dependent apps |
|---|---|---|
| `longstreet-litecoin` | Litecoin Core full node (wallet disabled) + sync status page | `APP_LONGSTREET_LITECOIN_*` (node IP, RPC/P2P/ZMQ ports, RPC creds) |
| `longstreet-dogecoin` | Dogecoin Core full node (wallet disabled) + sync status page | `APP_LONGSTREET_DOGECOIN_*` |
| `longstreet-miner` | *(future)* solo merged-mining Stratum engine, depends on both nodes | — |

## Versioning and releases

Each app has its own semantic version in `umbrel-app.yml` (`1.0.0`, `1.0.1`, ...),
independent of the Core version it ships. umbrelOS offers an update whenever the
version string in this repo differs from the installed one, so **every change to an
app directory must bump its version**. CI fails the push if you forget.

The Core version and tarball checksum for each image live in
`images/<name>/version.env`. Every push to `main` runs the **Build node images**
workflow, which:

1. Builds `ghcr.io/<owner>/<name>:<VERSION>` only if that tag does not exist yet
   (re-run it from the Actions tab with **force** to rebuild anyway).
2. Writes the resulting digest into the app's `docker-compose.yml`, bumps the app's
   patch version if this push did not already bump it, and pushes that commit to `main`.

So to ship a new Core release: edit `version.env`, push, and let CI pin and bump.
To ship any other change (status page, `.conf`, ports): bump `version` yourself
and update `releaseNotes` in `umbrel-app.yml`. umbrelOS re-reads community stores
periodically and pulls the newly pinned images when the user accepts the update.

### Upstream Core releases are discovered automatically

`.github/workflows/check_core_updates.yml` runs daily (or on demand from the Actions
tab). It asks GitHub for the latest Litecoin/Dogecoin Core release, downloads the
upstream `SHA256SUMS.asc`, and verifies its PGP signature against the keys pinned in
`keys/`. Only then does it take the tarball checksum and open a pull request updating
`images/<name>/version.env` and the app's `releaseNotes`. Review the upstream release
notes, merge, and the build-and-pin flow above does the rest. If a release is signed
by an unknown key the check fails instead of opening a PR; see `keys/README.md`.

Run the same check locally with `scripts/check-core-updates.sh --dry-run` (needs
`curl`, `gpg`, `jq`).

## First-time setup

1. Check that the `port:` values in each `umbrel-app.yml` and the `10.21.42.x` IPs in
   each `exports.sh` are unused on your Umbrel.
2. Push to GitHub and let the **Build node images** workflow run. Make the GHCR
   packages public (or umbrelOS won't be able to pull them).
3. On umbrelOS: Settings → App Store → Community App Stores → add this repo's URL.
4. Install **Litecoin Node** first. Watch it over SSH:
   `docker logs -f longstreet-litecoin_litecoind_1`. Open the app tile for the sync dashboard.
5. Install **Dogecoin Node**. It syncs slower than Litecoin — that's expected.
6. After both report `initialblockdownload: false`, lower `dbcache` in the `.conf`
   files (~450) and restart the apps to give RAM back to the rest of the box.

## Verifying from inside the Umbrel

```sh
docker exec longstreet-litecoin_litecoind_1 litecoin-cli -datadir=/data/.litecoin getblockchaininfo
docker exec longstreet-dogecoin_dogecoind_1 dogecoin-cli -datadir=/data/.dogecoin createauxblock <DOGE_ADDRESS>
```

## Notes

- RPC and ZMQ are reachable only on Umbrel's internal app network (`10.21.0.0/16`).
  Only the P2P ports are published to the LAN, and nothing needs to be forwarded from WAN.
- The RPC password is derived from the per-app `APP_SEED` umbreld provides, so it is
  stable across restarts without being committed to git.
- Pruning is commented out in both `.conf` files. Both `getblocktemplate` (LTC) and
  `createauxblock` (DOGE) work on pruned nodes if disk gets tight.
- `stop_grace_period: 15m` matters: killing a node mid-flush corrupts the chainstate
  and costs you a resync.
