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
6. That's it. Each node runs with `dbcache=1536` during the initial sync and restarts
   itself once with `dbcache=450` when the sync finishes (see next section).

## Automatic dbcache

`dbcache` caps the in-memory UTXO cache. A big cache makes the initial sync much
faster (fewer flushes to disk) but is wasted RAM afterwards, so `entrypoint.sh`
handles it: the daemon starts with `DBCACHE_IBD` (1536 MiB); a watcher polls
`getblockchaininfo` once a minute and, when `initialblockdownload` turns false,
writes `data/<coin>/.synced`, stops the node cleanly and relaunches it with
`DBCACHE_SYNCED` (450 MiB). Later starts see the marker and use the small cache
directly. Delete the marker to get the large cache back for a long catch-up.

To take manual control, set `dbcache=` in `<coin>.local.conf`; that value wins and
the automation stays off. Both limits can also be changed via the `DBCACHE_IBD` /
`DBCACHE_SYNCED` environment variables in `docker-compose.yml`.

## Local configuration overrides

App updates copy every file in this repo over the app's directory on the Umbrel, so
edits to `litecoin.conf` / `dogecoin.conf` there are lost on the next update. Put your
own settings in the data directory instead, which is never touched:

```sh
# on the Umbrel
echo "dbcache=450" >> ~/umbrel/app-data/longstreet-litecoin/data/litecoin/litecoin.local.conf
echo "dbcache=450" >> ~/umbrel/app-data/longstreet-dogecoin/data/dogecoin/dogecoin.local.conf
```

then restart the app. `entrypoint.sh` assembles the runtime config as
*your overrides* + *dbcache* + *shipped conf* + *RPC credentials*. Core keeps the first value it
sees for an option, so anything in the local file wins. (Dogecoin 1.14 predates
`includeconf`, which is why it's done this way for both.)

## Bootstrapping the initial sync

Neither Litecoin Core 0.21 nor Dogecoin Core 1.14 supports UTXO snapshots
(`assumeutxo`), so every block is validated locally on first run. You can still skip
the *download*:

- **Copy a data directory from a node you already run.** Stop both nodes, then rsync
  the `blocks/` and `chainstate/` folders into
  `~/umbrel/app-data/longstreet-<coin>/data/<coin>/` and
  `sudo chown -R 1000:1000` the result. Fastest option, and it adds no trust because
  it is your own node's validated output.
- **Drop a `bootstrap.dat` into that same directory** and start the app. Both cores
  import it automatically (renaming it `bootstrap.dat.old` when done) and fully validate
  every block, so the file's origin does not matter. This only saves bandwidth, not
  CPU time, so it mainly helps on slow or metered connections.
- Third-party chainstate snapshots exist for both coins. Avoid them for a node that
  feeds a miner: a bad chainstate means mining on the wrong chain with nothing to warn you.

Chain data lives in `app-data/.../data/` on the host and survives app updates and
restarts. Only uninstalling the app removes it.

## Verifying from inside the Umbrel

```sh
docker exec longstreet-litecoin_litecoind_1 litecoin-cli -conf=/tmp/litecoin.conf -datadir=/data/.litecoin getblockchaininfo
docker exec longstreet-dogecoin_dogecoind_1 dogecoin-cli -conf=/tmp/dogecoin.conf -datadir=/data/.dogecoin createauxblock <DOGE_ADDRESS>
```

## Notes

- `-conf=/tmp/<coin>.conf` in the commands above points at the runtime config that
  `entrypoint.sh` assembles; it carries the RPC credentials, so `-cli` works without
  pasting a password.

- RPC and ZMQ are reachable only on Umbrel's internal app network (`10.21.0.0/16`).
  Only the P2P ports are published to the LAN, and nothing needs to be forwarded from WAN.
- The RPC password is derived from the per-app `APP_SEED` umbreld provides, so it is
  stable across restarts without being committed to git.
- Pruning is commented out in both `.conf` files. Both `getblocktemplate` (LTC) and
  `createauxblock` (DOGE) work on pruned nodes if disk gets tight.
- `stop_grace_period: 15m` matters: killing a node mid-flush corrupts the chainstate
  and costs you a resync.
