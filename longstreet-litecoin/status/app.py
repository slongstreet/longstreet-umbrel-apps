"""Tiny sync-status page. Polls getblockchaininfo / getnetworkinfo over RPC.
Stdlib only so it runs on the stock python:alpine image."""
import base64
import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

COIN = os.environ.get("COIN_NAME", "Node")
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


PAGE = """<!doctype html><meta charset=utf-8><meta http-equiv=refresh content=30>
<title>{coin} node</title>
<body style="font-family:system-ui;max-width:40rem;margin:3rem auto;line-height:1.5">
<h1>{coin} node</h1>
<p><b>Sync:</b> {pct:.2f}% &nbsp; <b>Height:</b> {blocks:,} / {headers:,}</p>
<p><b>Initial block download:</b> {ibd} &nbsp; <b>Peers:</b> {peers}</p>
<p><b>Version:</b> {ver} &nbsp; <b>Chain:</b> {chain} &nbsp; <b>Disk:</b> {disk:.1f} GB{pruned}</p>
<p style="color:#888">Refreshes every 30 s.</p>
"""

ERR = "<!doctype html><meta http-equiv=refresh content=10><body style='font-family:system-ui;margin:3rem'><h1>{coin} node</h1><p>RPC not ready yet: {e}</p>"


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            b = rpc("getblockchaininfo")
            n = rpc("getnetworkinfo")
            html = PAGE.format(
                coin=COIN, pct=b["verificationprogress"] * 100, blocks=b["blocks"],
                headers=b["headers"], ibd=b.get("initialblockdownload"), peers=n["connections"],
                ver=n["subversion"], chain=b["chain"], disk=b.get("size_on_disk", 0) / 1e9,
                pruned=" (pruned)" if b.get("pruned") else "",
            )
        except Exception as e:  # noqa: BLE001
            html = ERR.format(coin=COIN, e=e)
        data = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_):  # keep container logs quiet
        pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), H).serve_forever()
