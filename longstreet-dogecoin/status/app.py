"""Node status dashboard. Serves a single HTML page at / that polls /api
(JSON from getblockchaininfo / getnetworkinfo / getmempoolinfo / uptime).
Stdlib only so it runs on the stock python:alpine image."""
import base64
import json
import os
import threading
import time
import urllib.request
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer

COIN = os.environ.get("COIN_NAME", "Node")
TICKER = os.environ.get("COIN_TICKER") or {"Litecoin": "LTC", "Dogecoin": "DOGE"}.get(COIN, "")
ACCENT = os.environ.get("ACCENT") or {"Litecoin": "#5b8def", "Dogecoin": "#e3b93a"}.get(COIN, "#7c8cf8")
RPC_URL = os.environ["RPC_URL"]
AUTH = base64.b64encode(
    f"{os.environ['RPC_USER']}:{os.environ['RPC_PASS']}".encode()
).decode()


def rpc(method, params=None):
    body = json.dumps({"jsonrpc": "1.0", "id": "status", "method": method, "params": params or []}).encode()
    req = urllib.request.Request(
        RPC_URL, data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Basic {AUTH}"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)["result"]


# Rough time-to-sync estimate. Core exposes no ETA, so do what its GUI does:
# sample verificationprogress over time and extrapolate the recent rate.
# verificationprogress is already weighted by expected transaction count, so the
# rate is roughly linear in wall-clock time, but treat the result as a ballpark.
SAMPLE_EVERY = 30          # seconds
WINDOW = 45 * 60           # keep 45 min of samples
MIN_SPAN = 5 * 60          # need at least 5 min of history before estimating
_samples = deque()         # (monotonic time, progress)
_lock = threading.Lock()


def _sampler():
    while True:
        try:
            b = rpc("getblockchaininfo")
            now = time.monotonic()
            with _lock:
                _samples.append((now, b.get("verificationprogress", 0)))
                while _samples and now - _samples[0][0] > WINDOW:
                    _samples.popleft()
        except Exception:  # noqa: BLE001 - node down; drop history so we restart clean
            with _lock:
                _samples.clear()
        time.sleep(SAMPLE_EVERY)


def eta_seconds(progress):
    """Seconds until progress reaches 1.0, or None if we can't say yet."""
    with _lock:
        if len(_samples) < 2:
            return None
        t0, p0 = _samples[0]
        t1, p1 = _samples[-1]
    span = t1 - t0
    if span < MIN_SPAN or p1 <= p0:
        return None
    rate = (p1 - p0) / span
    return max(0.0, (1.0 - progress) / rate)


def snapshot():
    b = rpc("getblockchaininfo")
    n = rpc("getnetworkinfo")
    m = rpc("getmempoolinfo")
    try:
        up = rpc("uptime")
    except Exception:  # noqa: BLE001 - older cores lack this RPC
        up = None
    progress = b.get("verificationprogress", 0)
    ibd = bool(b.get("initialblockdownload"))
    if not ibd and progress > 0.9999:
        progress = 1.0
    return {
        "eta": None if progress >= 1.0 else eta_seconds(progress),
        "ok": True,
        "chain": b.get("chain"),
        "blocks": b.get("blocks", 0),
        "headers": b.get("headers", 0),
        "progress": progress,
        "ibd": ibd,
        "pruned": bool(b.get("pruned")),
        "disk": b.get("size_on_disk", 0),
        "difficulty": b.get("difficulty"),
        "best": b.get("bestblockhash"),
        "mediantime": b.get("mediantime"),
        "peers": n.get("connections", 0),
        "peers_in": n.get("connections_in"),
        "peers_out": n.get("connections_out"),
        "version": n.get("subversion", "").strip("/"),
        "protocol": n.get("protocolversion"),
        "mempool_tx": m.get("size", 0),
        "mempool_bytes": m.get("bytes", 0),
        "uptime": up,
    }


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__COIN__ node</title>
<style>
:root{--accent:__ACCENT__;--bg:#0b0e14;--card:#131826;--card2:#182036;--text:#e8ecf4;--muted:#8a93a8;--ok:#3ddc84;--warn:#f5b342;--bad:#ff5c6c;--line:#222a3d}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;-webkit-font-smoothing:antialiased}
body::before{content:"";position:fixed;inset:-40vh -20vw auto;height:80vh;background:radial-gradient(60% 60% at 50% 0%,color-mix(in srgb,var(--accent) 28%,transparent),transparent 70%);pointer-events:none;z-index:0}
main{position:relative;z-index:1;max-width:60rem;margin:0 auto;padding:2.5rem 1.25rem 3rem}
header{display:flex;align-items:center;gap:1rem;margin-bottom:1.75rem}
.logo{width:52px;height:52px;border-radius:14px;display:grid;place-items:center;font-weight:800;font-size:1.05rem;letter-spacing:.02em;background:linear-gradient(145deg,var(--accent),color-mix(in srgb,var(--accent) 45%,#000));color:#fff;box-shadow:0 8px 24px color-mix(in srgb,var(--accent) 40%,transparent)}
h1{margin:0;font-size:1.45rem;font-weight:700;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:.9rem;display:flex;gap:.6rem;align-items:center;flex-wrap:wrap}
.dot{width:9px;height:9px;border-radius:50%;background:var(--muted);display:inline-block;box-shadow:0 0 0 0 transparent;transition:background .3s}
.dot.ok{background:var(--ok);box-shadow:0 0 0 4px color-mix(in srgb,var(--ok) 20%,transparent)}
.dot.warn{background:var(--warn);box-shadow:0 0 0 4px color-mix(in srgb,var(--warn) 20%,transparent)}
.dot.bad{background:var(--bad);box-shadow:0 0 0 4px color-mix(in srgb,var(--bad) 20%,transparent)}
.hero{background:linear-gradient(180deg,var(--card2),var(--card));border:1px solid var(--line);border-radius:18px;padding:1.5rem 1.6rem;margin-bottom:1rem;box-shadow:0 20px 50px rgba(0,0,0,.35)}
.hero .row{display:flex;justify-content:space-between;align-items:baseline;gap:1rem;flex-wrap:wrap}
.pct{font-size:3rem;font-weight:800;letter-spacing:-.03em;line-height:1;font-variant-numeric:tabular-nums}
.pct small{font-size:1.2rem;color:var(--muted);font-weight:600;margin-left:.15rem}
.heights{color:var(--muted);font-variant-numeric:tabular-nums}
.heights b{color:var(--text);font-weight:600}
.eta{display:block;text-align:right;margin-top:.15rem;font-size:.85rem}
.eta b{color:var(--accent)}
@media(max-width:480px){.eta{text-align:left}}
.bar{height:12px;border-radius:999px;background:#0e1220;border:1px solid var(--line);overflow:hidden;margin-top:1.1rem;position:relative}
.bar i{display:block;height:100%;width:0;border-radius:999px;background:linear-gradient(90deg,color-mix(in srgb,var(--accent) 70%,#fff 0%),var(--accent));transition:width .8s cubic-bezier(.2,.8,.2,1);position:relative}
.bar i::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,.35),transparent);background-size:200% 100%;animation:sheen 2.4s linear infinite}
.bar.done i::after{animation:none}
@keyframes sheen{from{background-position:200% 0}to{background-position:-200% 0}}
.badges{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:1rem}
.badge{font-size:.78rem;font-weight:600;padding:.28rem .65rem;border-radius:999px;border:1px solid var(--line);color:var(--muted);background:#0e1220}
.badge.accent{color:var(--accent);border-color:color-mix(in srgb,var(--accent) 45%,transparent);background:color-mix(in srgb,var(--accent) 12%,transparent)}
.badge.ok{color:var(--ok);border-color:color-mix(in srgb,var(--ok) 45%,transparent);background:color-mix(in srgb,var(--ok) 10%,transparent)}
.badge.warn{color:var(--warn);border-color:color-mix(in srgb,var(--warn) 45%,transparent);background:color-mix(in srgb,var(--warn) 10%,transparent)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(9.5rem,1fr));gap:.85rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:1rem 1.1rem;transition:transform .2s,border-color .2s}
.card:hover{transform:translateY(-2px);border-color:color-mix(in srgb,var(--accent) 40%,var(--line))}
.card .k{color:var(--muted);font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;font-weight:600}
.card .v{font-size:1.45rem;font-weight:700;margin-top:.2rem;font-variant-numeric:tabular-nums;letter-spacing:-.01em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.card .s{color:var(--muted);font-size:.82rem;margin-top:.1rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.85rem}
.err{display:none;background:color-mix(in srgb,var(--bad) 12%,var(--card));border:1px solid color-mix(in srgb,var(--bad) 45%,transparent);border-radius:14px;padding:1rem 1.1rem;margin-bottom:1rem}
.err b{color:var(--bad)}
.err code{color:var(--muted);font-size:.85rem;display:block;margin-top:.3rem;word-break:break-all}
body.down .err{display:block}
body.down .hero,body.down .grid{opacity:.45;filter:saturate(.4)}
footer{color:var(--muted);font-size:.8rem;margin-top:1.5rem;display:flex;justify-content:space-between;flex-wrap:wrap;gap:.5rem}
@media(max-width:480px){.pct{font-size:2.4rem}main{padding-top:1.5rem}}
</style></head>
<body>
<main>
<header>
  <div class="logo">__TICKER__</div>
  <div>
    <h1>__COIN__ Node</h1>
    <div class="sub"><span class="dot" id="dot"></span><span id="state">Connecting…</span><span id="ver"></span></div>
  </div>
</header>

<div class="err"><b>RPC not reachable.</b> The node may still be starting, or it crashed. Check the app logs in Umbrel.<code id="errmsg"></code></div>

<section class="hero">
  <div class="row">
    <div class="pct"><span id="pct">—</span><small>%</small></div>
    <div class="heights">Block <b id="blocks">—</b> of <b id="headers">—</b> headers<span id="eta" class="eta" hidden></span></div>
  </div>
  <div class="bar" id="bar"><i id="fill"></i></div>
  <div class="badges" id="badges"></div>
</section>

<section class="grid">
  <div class="card"><div class="k">Peers</div><div class="v" id="peers">—</div><div class="s" id="peersub"></div></div>
  <div class="card"><div class="k">Mempool</div><div class="v" id="mempool">—</div><div class="s" id="mempoolsub"></div></div>
  <div class="card"><div class="k">Chain size</div><div class="v" id="disk">—</div><div class="s" id="disksub"></div></div>
  <div class="card"><div class="k">Uptime</div><div class="v" id="uptime">—</div><div class="s" id="uptimesub"></div></div>
  <div class="card"><div class="k">Difficulty</div><div class="v" id="diff">—</div><div class="s">network</div></div>
  <div class="card"><div class="k">Last block</div><div class="v" id="age">—</div><div class="s" id="agesub"></div></div>
  <div class="card" style="grid-column:1/-1"><div class="k">Best block hash</div><div class="v mono" id="best">—</div></div>
</section>

<footer><span>Updates every 10 s</span><span id="stamp"></span></footer>
</main>

<script>
const $ = id => document.getElementById(id);
const n = x => x == null ? "—" : Number(x).toLocaleString();
const gb = b => (b/1e9).toFixed(b < 1e10 ? 2 : 1) + " GB";
const mb = b => b < 1e6 ? (b/1e3).toFixed(0)+" kB" : (b/1e6).toFixed(1)+" MB";
function dur(s){ if(s==null) return "—"; const d=Math.floor(s/86400), h=Math.floor(s%86400/3600), m=Math.floor(s%3600/60);
  return d ? `${d}d ${h}h` : h ? `${h}h ${m}m` : `${m}m`; }
function ago(t){ const s=Math.max(0,Date.now()/1000-t); return s<90?`${Math.round(s)}s`:s<5400?`${Math.round(s/60)}m`:s<172800?`${(s/3600).toFixed(1)}h`:`${Math.round(s/86400)}d`; }
function compact(x){ const u=[["T",1e12],["G",1e9],["M",1e6],["k",1e3]]; for(const [s,v] of u) if(x>=v) return (x/v).toFixed(x/v<10?2:1)+" "+s; return Number(x).toFixed(0); }
function badge(cls,text){ const e=document.createElement("span"); e.className="badge "+cls; e.textContent=text; return e; }

async function tick(){
  try{
    const r = await fetch("api", {cache:"no-store"});
    const d = await r.json();
    if(!d.ok) throw new Error(d.error || "unknown error");
    document.body.classList.remove("down");
    const pct = d.progress*100;
    $("pct").textContent = pct >= 99.995 ? "100" : pct.toFixed(2);
    $("fill").style.width = Math.max(1, pct) + "%";
    $("bar").classList.toggle("done", d.progress >= 1);
    $("blocks").textContent = n(d.blocks); $("headers").textContent = n(d.headers);
    const synced = !d.ibd && d.progress >= 1;
    const eta = $("eta");
    if (synced || d.eta == null) { eta.hidden = true; }
    else { eta.hidden = false; eta.innerHTML = d.eta > 14*86400 ? "more than <b>2 weeks</b> to go" : "roughly <b>" + dur(d.eta) + "</b> remaining"; }
    $("dot").className = "dot " + (synced ? "ok" : "warn");
    $("state").textContent = synced ? "Synced" : d.ibd ? "Initial block download" : "Catching up";
    $("ver").textContent = d.version ? "· " + d.version : "";
    const b = $("badges"); b.innerHTML = "";
    b.append(badge("accent", (d.chain||"?").toUpperCase()));
    b.append(badge(synced?"ok":"warn", synced ? "Fully validated" : `${n(d.headers - d.blocks)} blocks behind`));
    if(d.pruned) b.append(badge("", "Pruned"));
    if(d.protocol) b.append(badge("", "Protocol " + d.protocol));
    $("peers").textContent = n(d.peers);
    $("peersub").textContent = d.peers_in != null ? `${d.peers_in} in · ${d.peers_out} out` : "connections";
    $("mempool").textContent = n(d.mempool_tx) + " tx";
    $("mempoolsub").textContent = mb(d.mempool_bytes);
    $("disk").textContent = gb(d.disk);
    $("disksub").textContent = d.pruned ? "pruned datadir" : "full blocks + chainstate";
    $("uptime").textContent = dur(d.uptime);
    $("uptimesub").textContent = d.uptime != null ? "since node start" : "not reported";
    $("diff").textContent = d.difficulty ? compact(d.difficulty) : "—";
    $("age").textContent = d.mediantime ? ago(d.mediantime) + " ago" : "—";
    $("agesub").textContent = d.mediantime ? "median time past" : "";
    $("best").textContent = d.best || "—";
    $("stamp").textContent = "Updated " + new Date().toLocaleTimeString();
  }catch(e){
    document.body.classList.add("down");
    $("dot").className = "dot bad"; $("state").textContent = "Offline";
    $("errmsg").textContent = String(e.message || e);
  }
}
tick(); setInterval(tick, 10000);
</script>
</body></html>
"""
PAGE = PAGE.replace("__COIN__", COIN).replace("__TICKER__", TICKER or COIN[:3].upper()).replace("__ACCENT__", ACCENT)


class H(BaseHTTPRequestHandler):
    def _send(self, body, ctype, status=200):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        if path.endswith("/api"):
            try:
                payload = snapshot()
            except Exception as e:  # noqa: BLE001
                payload = {"ok": False, "error": str(e)}
            self._send(json.dumps(payload).encode(), "application/json")
        else:
            self._send(PAGE.encode(), "text/html; charset=utf-8")

    def log_message(self, *_):  # keep container logs quiet
        pass


if __name__ == "__main__":
    threading.Thread(target=_sampler, daemon=True).start()
    HTTPServer(("0.0.0.0", 8080), H).serve_forever()
