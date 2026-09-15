# Sourced by umbreld. Visible to this app and to apps that depend on longstreet-dogecoin.

# TODO: confirm these IPs are unused on your Umbrel.
export APP_LONGSTREET_DOGECOIN_NODE_IP="10.21.42.20"
export APP_LONGSTREET_DOGECOIN_STATUS_IP="10.21.42.21"

export APP_LONGSTREET_DOGECOIN_RPC_PORT="22555"
export APP_LONGSTREET_DOGECOIN_P2P_PORT="22556"
export APP_LONGSTREET_DOGECOIN_ZMQ_HASHBLOCK_PORT="28434"
export APP_LONGSTREET_DOGECOIN_ZMQ_RAWBLOCK_PORT="28435"

export APP_LONGSTREET_DOGECOIN_RPC_USER="umbrel"
# RPC is reachable only on the internal app network. The password is generated once
# and persisted in this app's data directory, then re-read every time this file is
# sourced. It must not depend on $APP_SEED: umbreld sources a dependency's exports.sh
# in the *dependent* app's environment, so a seed-derived value differs between this
# app and the apps that connect to it.
DOGECOIN_ENV_FILE="${EXPORTS_APP_DIR:-$(dirname "${BASH_SOURCE[0]}")}/.env"
if [[ ! -f "${DOGECOIN_ENV_FILE}" ]]; then
  echo "export APP_LONGSTREET_DOGECOIN_RPC_PASS='$(openssl rand -hex 16)'" > "${DOGECOIN_ENV_FILE}"
fi
. "${DOGECOIN_ENV_FILE}"
