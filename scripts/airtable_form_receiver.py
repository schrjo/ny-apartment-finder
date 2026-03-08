"""Local receiver for Airtable form dropdown snapshots.

Run this script locally, then use the Tampermonkey userscript to
POST the dropdown values to http://localhost:<port>/airtable-form.

Env vars:
- AIRTABLE_FORM_RECEIVER_PORT (default: 8765)
- AIRTABLE_FORM_SNAPSHOT_PATH (default: data/airtable_form_snapshot.json)
- AIRTABLE_FORM_RECEIVER_TOKEN (optional, require X-Token header)
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


PORT = int(os.getenv("AIRTABLE_FORM_RECEIVER_PORT", "8765"))
SNAPSHOT_PATH = Path(os.getenv("AIRTABLE_FORM_SNAPSHOT_PATH", "data/airtable_form_snapshot.json"))
RECEIVER_TOKEN = os.getenv("AIRTABLE_FORM_RECEIVER_TOKEN")


class Receiver(BaseHTTPRequestHandler):
    def _set_headers(self, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    def do_POST(self):
        if self.path != "/airtable-form":
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "not found"}).encode("utf-8"))
            return

        if RECEIVER_TOKEN:
            token = self.headers.get("X-Token")
            if token != RECEIVER_TOKEN:
                self._set_headers(401)
                self.wfile.write(json.dumps({"error": "unauthorized"}).encode("utf-8"))
                return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "invalid json"}).encode("utf-8"))
            return

        items = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            # allow posting raw list
            if isinstance(payload, list):
                items = payload
            else:
                items = []

        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(json.dumps({"items": items}, indent=2), encoding="utf-8")

        self._set_headers(200)
        self.wfile.write(json.dumps({"ok": True, "count": len(items)}).encode("utf-8"))

    def log_message(self, format, *args):
        return


def main():
    httpd = HTTPServer(("127.0.0.1", PORT), Receiver)
    print(f"Listening on http://127.0.0.1:{PORT}/airtable-form")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
