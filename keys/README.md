# Release signing keys

Public keys trusted to sign upstream `SHA256SUMS.asc` files. `scripts/check-core-updates.sh`
refuses a checksum file unless it carries a good signature from a key in the matching
directory, so a compromised download page cannot feed us a bad checksum.

| Directory | Key | Fingerprint | Source |
|---|---|---|---|
| `litecoind/` | David Burkett | `D356 21D5 3A1C C6A3 4567 58D0 3620 E9D3 87E5 5666` | https://download.litecoin.org/litecoin-0.21.5.6/davidburkett38-key.pgp |
| `dogecoind/` | Patrick Lodder | `DC6E F4A8 BF9F 1B1E 4DE1 EE52 2D3A 345B 98D0 DC1F` | https://github.com/dogecoin/dogecoin/blob/master/contrib/gitian-keys/patricklodder-key.pgp |

If upstream changes signer, the update check fails on purpose. Confirm the new key from
a second source (project repo, release announcement, maintainer's profile) before adding it here.
