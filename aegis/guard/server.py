"""HTTP ingest, so the guard can sit in front of a real agent over the network.

The contract is *inline*: the caller POSTs an event and holds the action until the
guard answers. ``{"allowed": false}`` means **do not perform it**.

    POST /event      {"source": "...", "kind": "tool_call", "tool": "send_email",
                      "args": {"to": "x@evil.example"}}
                  -> {"decision": "blocked", "allowed": false, "layer": "tool-policy",
                      "reason": "recipient domain 'evil.example' not allow-listed"}

    GET  /health     liveness -- the "still standing" signal for a supervisor
    GET  /metrics    counters: events, allowed, blocked, quarantined sessions
    GET  /incidents  the recent audit trail

Binds to loopback by default. Binding to 0.0.0.0 exposes the guard to the network;
if you do that, set ``token`` and send it as the ``X-AEGIS-Token`` header. stdlib
only -- no framework, no dependencies.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .events import Event


def make_handler(guard, token: str | None = None):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AEGISGuard/0.1"
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args):  # the guard does its own logging
            pass

        # -- helpers ----------------------------------------------------
        def _send(self, code: int, payload: dict) -> None:
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)

        def _authorised(self) -> bool:
            return not token or self.headers.get("X-AEGIS-Token") == token

        # -- routes -----------------------------------------------------
        def do_GET(self):
            if not self._authorised():
                return self._send(401, {"error": "unauthorised"})
            if self.path == "/health":
                return self._send(200, {"status": "ok", "events": guard.seen,
                                        "autonomy": guard.config.autonomy.value})
            if self.path == "/metrics":
                return self._send(200, guard.summary())
            if self.path == "/incidents":
                return self._send(200, {"incidents": [i.to_dict() for i in guard.log.records[-50:]]})
            return self._send(404, {"error": "not found"})

        def do_POST(self):
            if not self._authorised():
                return self._send(401, {"error": "unauthorised"})
            if self.path != "/event":
                return self._send(404, {"error": "not found"})
            try:
                length = int(self.headers.get("Content-Length") or 0)
                data = json.loads(self.rfile.read(length) or b"{}")
                event = Event.from_dict(data)
            except (ValueError, TypeError):
                return self._send(400, {"error": "invalid event json"})
            decision = guard.handle(event)
            last = guard.log.records[-1] if guard.log.records else None
            blocked = decision in ("blocked", "quarantined")
            return self._send(200, {
                "decision": decision,
                "allowed": not blocked,
                "layer": last.layer if (last and blocked) else "-",
                "reason": last.reason if (last and blocked) else "no policy violation",
            })

    return Handler


class GuardServer:
    def __init__(self, guard, host: str = "127.0.0.1", port: int = 8765,
                 token: str | None = None):
        self.guard = guard
        self.httpd = ThreadingHTTPServer((host, port), make_handler(guard, token))
        self.host, self.port = self.httpd.server_address[0], self.httpd.server_address[1]

    def serve_forever(self) -> None:
        self.httpd.serve_forever()

    def shutdown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
