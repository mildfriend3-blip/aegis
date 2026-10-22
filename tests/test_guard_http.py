"""HTTP ingest: the guard answering an inline agent over the network.

The server runs in a thread inside the test, so there is no background job -- the
whole round trip (socket, JSON, decision) is exercised for real.
"""
import json
import threading
import urllib.error
import urllib.request

import pytest

from aegis.guard import Guard, GuardConfig, GuardServer


def _make_server(token=None):
    guard = Guard(GuardConfig(heartbeat_every=0, incidents_path=None))
    srv = GuardServer(guard, host="127.0.0.1", port=0, token=token)  # port 0 = ephemeral
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, guard


@pytest.fixture()
def server():
    srv, guard = _make_server()
    yield srv, guard
    srv.shutdown()


def _post(srv, payload, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-AEGIS-Token"] = token
    req = urllib.request.Request(f"http://{srv.host}:{srv.port}/event",
                                 data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def _get(srv, path, token=None):
    headers = {"X-AEGIS-Token": token} if token else {}
    req = urllib.request.Request(f"http://{srv.host}:{srv.port}{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def test_exfil_call_is_refused_inline(server):
    srv, _ = server
    out = _post(srv, {"source": "agent-1", "kind": "tool_call", "tool": "send_email",
                      "args": {"to": "x@evil.example", "body": ""}})
    assert out["allowed"] is False
    assert out["layer"] == "tool-policy"


def test_legitimate_call_is_allowed_inline(server):
    srv, _ = server
    out = _post(srv, {"source": "agent-1", "kind": "tool_call", "tool": "send_email",
                      "args": {"to": "alice@corp.example", "body": "hi"}})
    assert out["allowed"] is True


def test_health_and_metrics(server):
    srv, _ = server
    assert _get(srv, "/health")["status"] == "ok"
    _post(srv, {"source": "a", "kind": "tool_call", "tool": "send_email",
                "args": {"to": "x@evil.example"}})
    metrics = _get(srv, "/metrics")
    assert metrics["events"] == 1 and metrics["blocked"] == 1


def test_incidents_endpoint_exposes_the_audit_trail(server):
    srv, _ = server
    _post(srv, {"source": "a", "kind": "tool_call", "tool": "send_email",
                "args": {"to": "x@evil.example"}})
    incidents = _get(srv, "/incidents")["incidents"]
    assert incidents and incidents[0]["layer"] == "tool-policy"


def test_malformed_event_is_rejected(server):
    srv, _ = server
    req = urllib.request.Request(f"http://{srv.host}:{srv.port}/event", data=b"{not json",
                                 headers={"Content-Type": "application/json"}, method="POST")
    with pytest.raises(urllib.error.HTTPError) as err:
        urllib.request.urlopen(req, timeout=5)
    assert err.value.code == 400


def test_token_is_required_when_configured():
    srv, _ = _make_server(token="s3cret")
    try:
        req = urllib.request.Request(f"http://{srv.host}:{srv.port}/event", data=b"{}",
                                     headers={"Content-Type": "application/json"}, method="POST")
        with pytest.raises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(req, timeout=5)
        assert err.value.code == 401
        assert _get(srv, "/health", token="s3cret")["status"] == "ok"
    finally:
        srv.shutdown()
