# Longstreet Labs — Umbrel community app store

Apps:

| App ID | What it is | Exposes to dependent apps |
|---|---|---|
| `longstreet-litecoin` | Litecoin Core full node (wallet disabled) + sync status page | `APP_LONGSTREET_LITECOIN_*` (node IP, RPC/P2P/ZMQ ports, RPC creds) |
| `longstreet-dogecoin` | Dogecoin Core full node (wallet disabled) + sync status page | `APP_LONGSTREET_DOGECOIN_*` |
| `longstreet-miner` | *(future)* solo merged-mining Stratum engine, depends on both nodes | — |

## First-time setup

1. Search the repo for `TODO` and fill in: your GitHub handle, pinned Litecoin/Dogecoin
   versions, the tarball SHA256 sums, and check that the `port:` values in each
   `umbrel-app.yml` and the `10.21.42.x` IPs in each `exports.sh` are unused on your Umbrel.
2. Push to GitHub. Run the **Build node images** workflow (Actions tab). Copy the
   `ghcr.io/...@sha256:...` digest it prints into each app's `docker-compose.yml`.
   Make the GHCR packages public (or umbrelOS won't be able to pull them).
3. On umbrelOS: Settings → App Store → Community App Stores → add this repo's URL.
4. Install **Litecoin Node** first. Watch it over SSH:
   `docker logs -f longstreet-litecoin_litecoind_1`. Open the app tile for sync %.
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
