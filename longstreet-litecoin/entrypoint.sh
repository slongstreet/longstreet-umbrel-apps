#!/bin/sh
# Assemble the runtime config, then exec the daemon.
#
#   <coin>.local.conf   your overrides, lives in the data dir, survives app updates
#   <coin>.conf         shipped with the app, overwritten on every app update
#   rpcuser/rpcpassword from umbreld, so <coin>-cli inside the container works
#
# Core keeps the FIRST value it sees for an option, so overrides go first.
set -eu
: "${DAEMON:?}" "${DATADIR:?}" "${RPC_USER:?}" "${RPC_PASS:?}"
name=${DAEMON%d}                 # litecoind -> litecoin
conf=/tmp/$name.conf
umask 077
{
  if [ -f "$DATADIR/$name.local.conf" ]; then
    echo "# ---- $name.local.conf (local overrides)"
    cat "$DATADIR/$name.local.conf"; echo
  fi
  echo "# ---- $name.conf (shipped with the app)"
  cat "/etc/$name/$name.conf"; echo
  echo "# ---- RPC credentials (from umbreld)"
  echo "rpcuser=$RPC_USER"
  echo "rpcpassword=$RPC_PASS"
} > "$conf"
exec "$DAEMON" -conf="$conf" -datadir="$DATADIR" "$@"
