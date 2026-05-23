"""Minimal HTTP server exposing a /health JSON endpoint."""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from cronwatcher.health import HealthChecker

logger = logging.getLogger(__name__)


class _HealthHandler(BaseHTTPRequestHandler):
    checker: HealthChecker  # injected via server attribute

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return

        try:
            status = self.server.checker.check()  # type: ignore[attr-defined]
            body = json.dumps(status.as_dict()).encode()
            code = 200 if status.healthy else 503
        except Exception as exc:  # pragma: no cover
            logger.exception("Health check failed: %s", exc)
            body = json.dumps({"healthy": False, "error": str(exc)}).encode()
            code = 500

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:  # pragma: no cover
        logger.debug(fmt, *args)


class HealthServer:
    """Runs the health HTTP server in a background daemon thread."""

    def __init__(self, checker: HealthChecker, host: str = "127.0.0.1", port: int = 8765) -> None:
        self._checker = checker
        self._host = host
        self._port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._server = HTTPServer((self._host, self._port), _HealthHandler)
        self._server.checker = self._checker  # type: ignore[attr-defined]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("Health server listening on %s:%s", self._host, self._port)

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            logger.info("Health server stopped")

    @property
    def is_running(self) -> bool:
        """Return True if the server thread is alive and serving requests."""
        return (
            self._thread is not None
            and self._thread.is_alive()
        )

    def __repr__(self) -> str:
        status = "running" if self.is_running else "stopped"
        return f"HealthServer({self._host}:{self._port}, {status})"
