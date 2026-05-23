"""Lightweight HTTP endpoint that exposes recent audit log entries as JSON."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse

from cronwatcher.audit_log import AuditLog


class _AuditHandler(BaseHTTPRequestHandler):
    audit_log: AuditLog  # injected by AuditServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/audit":
            self._respond(404, {"error": "not found"})
            return

        params = parse_qs(parsed.query)
        event_type = params.get("event_type", [None])[0]
        try:
            limit = int(params.get("limit", ["50"])[0])
        except ValueError:
            limit = 50

        if event_type:
            entries = self.audit_log.by_event_type(event_type)
        else:
            entries = self.audit_log.recent(limit=limit)

        self._respond(200, [e.as_dict() for e in entries])

    def _respond(self, status: int, body: object) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args: object) -> None:  # silence default logging
        pass


class AuditServer:
    def __init__(self, audit_log: AuditLog, host: str = "0.0.0.0", port: int = 8084) -> None:
        self._log = audit_log
        handler = type("_H", (_AuditHandler,), {"audit_log": audit_log})
        self._server = HTTPServer((host, port), handler)
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        if self._thread:
            self._thread.join(timeout=5)
