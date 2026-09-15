# Sourced by umbreld. These variables are visible to this app's compose file
# and to any app that lists longstreet-litecoin in its dependencies.

# TODO: confirm these IPs are unused (Umbrel's app network is 10.21.0.0/16;
# official apps live mostly in 10.21.21.x / 10.21.22.x).
export APP_LONGSTREET_LITECOIN_NODE_IP="10.21.42.10"
export APP_LONGSTREET_LITECOIN_STATUS_IP="10.21.42.11"

export APP_LONGSTREET_LITECOIN_RPC_PORT="9332"
export APP_LONGSTREET_LITECOIN_P2P_PORT="9333"
export APP_LONGSTREET_LITECOIN_ZMQ_HASHBLOCK_PORT="28432"
export APP_LONGSTREET_LITECOIN_ZMQ_RAWBLOCK_PORT="28433"

export APP_LONGSTREET_LITECOIN_RPC_USER="umbrel"
# RPC is reachable only on the internal app network. The password is generated once
# and persisted in this app's data directory, then re-read every time this file is
# sourced. It must not depend on $APP_SEED: umbreld sources a dependency's exports.sh
# in the *dependent* app's environment, so a seed-derived value differs between this
# app and the apps that connect to it.
LITECOIN_ENV_FILE="${EXPORTS_APP_DIR:-$(dirname "${BASH_SOURCE[0]}")}/.env"
if [[ ! -f "${LITECOIN_ENV_FILE}" ]]; then
  echo "export APP_LONGSTREET_LITECOIN_RPC_PASS='$(openssl rand -hex 16)'" > "${LITECOIN_ENV_FILE}"
fi
. "${LITECOIN_ENV_FILE}"
