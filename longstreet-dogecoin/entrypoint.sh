#!/bin/sh
# Supervises the Core daemon and assembles its runtime config.
#
# Config precedence (Core keeps the FIRST value it sees for an option):
#   1. $DATADIR/<coin>.local.conf   your overrides; lives in the data dir, survives updates
#   2. dbcache=...                  chosen here: large during initial sync, small afterwards
#   3. /etc/<coin>/<coin>.conf      shipped with the app, overwritten on every update
#   4. rpcuser/rpcpassword          from umbreld, so <coin>-cli works inside the container
#
# dbcache automation: the daemon starts with DBCACHE_IBD. A watcher polls the
# node; when initialblockdownload turns false it writes $DATADIR/.synced, asks
# the node to stop cleanly, and this script relaunches it with DBCACHE_SYNCED.
# Setting dbcache in <coin>.local.conf disables the automation for that node.
set -eu
: "${DAEMON:?}" "${DATADIR:?}" "${RPC_USER:?}" "${RPC_PASS:?}"
DBCACHE_IBD=${DBCACHE_IBD:-1536}
DBCACHE_SYNCED=${DBCACHE_SYNCED:-450}
POLL=${SYNC_POLL_SECONDS:-60}

name=${DAEMON%d}                       # litecoind -> litecoin
cli="${name}-cli"
conf=/tmp/$name.conf
local_conf="$DATADIR/$name.local.conf"
marker="$DATADIR/.synced"
rpcport=""
for a in "$@"; do case "$a" in -rpcport=*) rpcport=$a ;; esac; done

log() { echo "entrypoint: $*"; }

write_conf() {  # $1 = dbcache MiB
  umask 077
  {
    if [ -f "$local_conf" ]; then
      echo "# ---- $name.local.conf (local overrides)"; cat "$local_conf"; echo
    fi
    echo "# ---- dbcache chosen by entrypoint.sh"; echo "dbcache=$1"
    echo "# ---- $name.conf (shipped with the app)"; cat "/etc/$name/$name.conf"; echo
    echo "# ---- RPC credentials (from umbreld)"
    echo "rpcuser=$RPC_USER"; echo "rpcpassword=$RPC_PASS"
  } > "$conf"
}

rpc() { "$cli" -conf="$conf" -datadir="$DATADIR" ${rpcport:+"$rpcport"} "$@" 2>/dev/null; }

watch_sync() {  # runs in the background while the daemon is up
  while kill -0 "$pid" 2>/dev/null; do
    sleep "$POLL"
    if rpc getblockchaininfo | grep -q '"initialblockdownload": *false'; then
      log "initial block download finished; restarting with dbcache=$DBCACHE_SYNCED"
      touch "$marker"
      rpc stop >/dev/null || true
      return
    fi
  done
}

pid=""; watcher=""; stopping=""
on_term() {
  stopping=1
  [ -n "$watcher" ] && kill "$watcher" 2>/dev/null
  [ -n "$pid" ] && kill -TERM "$pid" 2>/dev/null
}
trap on_term TERM INT

while :; do
  if grep -q '^dbcache=' "$local_conf" 2>/dev/null; then
    cache=$(sed -n 's/^dbcache=//p' "$local_conf" | head -1); auto=""
    log "dbcache=$cache from $name.local.conf (automation off)"
  elif [ -f "$marker" ]; then
    cache=$DBCACHE_SYNCED; auto=""
    log "chain previously synced; dbcache=$cache"
  else
    cache=$DBCACHE_IBD; auto=1
    log "initial sync; dbcache=$cache until initialblockdownload clears"
  fi
  write_conf "$cache"

  "$DAEMON" -conf="$conf" -datadir="$DATADIR" "$@" &
  pid=$!
  if [ -n "$auto" ]; then watch_sync & watcher=$!; fi

  rc=0; wait "$pid" || rc=$?
  if kill -0 "$pid" 2>/dev/null; then            # a trapped signal interrupted wait; let the daemon finish
    while kill -0 "$pid" 2>/dev/null; do sleep 1; done
    rc=0; wait "$pid" || rc=$?                   # now returns the daemon's real exit code
  fi
  [ -n "$watcher" ] && { kill "$watcher" 2>/dev/null || true; wait "$watcher" 2>/dev/null || true; watcher=""; }

  if [ -n "$stopping" ]; then exit "$rc"; fi
  if [ -n "$auto" ] && [ -f "$marker" ] && [ "$rc" -eq 0 ]; then continue; fi   # planned restart
  exit "$rc"
done
