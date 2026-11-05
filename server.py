#!/usr/bin/env python3
"""Local server that serves the HTML files AND proxies API calls to Bonfires.

Serves static files from this directory on port 8888.
Proxies any request to /api/* → https://tnt-v2.api.bonfires.ai/*
This avoids CORS issues entirely since the browser only talks to localhost.

The API key is read from DELVE_API_KEY and added to proxied requests, so it
never has to appear in the HTML. BONFIRE_ID is handed to the pages via
/config.json. See .env.example.

Usage:
    export DELVE_API_KEY=... BONFIRE_ID=...
    python3 server.py
    # Then open http://localhost:8888/pulse.html
"""

import http.server
import json
import os
import socketserver
import sys
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

PORT = 8888
API_BASE = "http://localhost:8000"
API_KEY = os.environ.get("DELVE_API_KEY", "")
BONFIRE_ID = os.environ.get("BONFIRE_ID", "")

# Only the pages served by this server may use the key-bearing proxy.
ALLOWED_ORIGINS = {f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"}


class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
        if self.path.startswith("/api/"):
            self._proxy("GET")
        elif path == "/config.json":
            # Non-secret settings for the pages. Never include the API key here.
            body = json.dumps({"bonfire_id": BONFIRE_ID}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif any(part.startswith(".") for part in path.split("/")):
            # Don't serve .env, .git, etc.
            self.send_error(404)
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._proxy("POST")
        else:
            self.send_error(405)

    def _proxy(self, method):
        # Browsers always send Origin on cross-origin requests; refuse those so
        # other websites can't use the key this proxy adds.
        origin = self.headers.get("Origin")
        if origin and origin not in ALLOWED_ORIGINS:
            self.send_error(403, "Cross-origin requests are not proxied")
            return

        # /api/delve → https://tnt-v2.api.bonfires.ai/delve
        target = API_BASE + self.path[4:]  # strip "/api"

        # Read request body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else None

        # Forward headers
        headers = {}
        for key in ("Content-Type", "Authorization", "X-API-Key"):
            val = self.headers.get(key)
            if val:
                headers[key] = val
        headers.setdefault("Authorization", f"Bearer {API_KEY}")

        req = urllib.request.Request(target, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_body = resp.read()
                self.send_response(resp.status)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.end_headers()
                self.wfile.write(resp_body)
        except urllib.error.HTTPError as exc:
            resp_body = exc.read()
            self.send_response(exc.code)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp_body)
        except Exception as exc:
            self.send_response(502)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode())


if __name__ == "__main__":
    missing = [name for name, value in (("DELVE_API_KEY", API_KEY), ("BONFIRE_ID", BONFIRE_ID)) if not value]
    if missing:
        print(f"\n  Error: {' and '.join(missing)} must be set in the environment (see .env.example).\n", file=sys.stderr)
        sys.exit(1)

    # Kill any existing server on this port
    socketserver.TCPServer.allow_reuse_address = True

    # Bind to loopback only: the proxy adds the API key to every request.
    with socketserver.TCPServer(("127.0.0.1", PORT), ProxyHandler) as httpd:
        print(f"\n  Bonfires local server running on http://localhost:{PORT}")
        print(f"  Static files: {Path(__file__).parent}")
        print(f"  API proxy:    /api/* → {API_BASE}/*")
        print(f"\n  Open: http://localhost:{PORT}/pulse.html")
        print(f"  Open: http://localhost:{PORT}/memory-explorer.html")
        print(f"  Open: http://localhost:{PORT}/synthesis.html\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Shutting down.")
