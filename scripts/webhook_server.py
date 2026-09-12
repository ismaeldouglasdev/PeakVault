#!/usr/bin/env python3
# scripts/webhook_server.py
# Minimal Stripe webhook receiver for local QA.
# POST /api/billing/webhook -> app.billing.handle_webhook (signature verified).
# Python stdlib only (no new deps). This is the shape the real endpoint will
# take on Render; defensively returns 400 so Stripe retries failed deliveries.
#
# Usage (from the repo root):
#   set -a; source .env; set +a
#   python3 scripts/webhook_server.py            # 127.0.0.1:8787

import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import billing  # noqa: E402

HOST = os.getenv("WEBHOOK_HOST", "127.0.0.1")
PORT = int(os.getenv("WEBHOOK_PORT", "8787"))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter access log
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def do_GET(self):  # noqa: N802 - http.server API
        if urlparse(self.path).path == "/api/billing/health":
            return self._json(200, {"ok": True, "service": "peakvault-webhook"})
        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):  # noqa: N802 - http.server API
        if urlparse(self.path).path != "/api/billing/webhook":
            return self._json(404, {"ok": False, "error": "not found"})
        length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(length)
        sig = self.headers.get("Stripe-Signature", "")
        try:
            # handle_webhook is async; each HTTP request thread gets its own loop.
            result = asyncio.run(billing.handle_webhook(payload, sig))
        except Exception as exc:  # noqa: BLE001 - surface any delivery failure
            print(f"webhook FAILED: {exc!r}", flush=True)
            return self._json(400, {"ok": False, "error": str(exc)})
        print(f"webhook OK: {result}", flush=True)
        self._json(200, result)

    def _json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"webhook server listening on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()