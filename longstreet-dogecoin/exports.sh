# Sourced by umbreld. Visible to this app and to apps that depend on longstreet-dogecoin.

# TODO: confirm these IPs are unused on your Umbrel.
export APP_LONGSTREET_DOGECOIN_NODE_IP="10.21.42.20"
export APP_LONGSTREET_DOGECOIN_STATUS_IP="10.21.42.21"

export APP_LONGSTREET_DOGECOIN_RPC_PORT="22555"
export APP_LONGSTREET_DOGECOIN_P2P_PORT="22556"
export APP_LONGSTREET_DOGECOIN_ZMQ_HASHBLOCK_PORT="28434"
export APP_LONGSTREET_DOGECOIN_ZMQ_RAWBLOCK_PORT="28435"

export APP_LONGSTREET_DOGECOIN_RPC_USER="umbrel"
export APP_LONGSTREET_DOGECOIN_RPC_PASS="$(echo -n "${APP_SEED}dogecoin-rpc" | sha256sum | head -c 32)"
