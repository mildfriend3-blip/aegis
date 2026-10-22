"""How an agent asks the guard for a decision.

Two implementations, one interface:

* ``InProcessDecider`` -- ask a local ``Guard`` directly. No network; for tests,
  single-process deployments, and the offline demo.
* ``HttpDecider`` -- ask a running guard over HTTP. This is the deployment path:
  the agent holds the action, calls the guard, and acts only if it is allowed.

Both return a ``Verdict``. The agent never sees *why* the policy engine decided
what it decided beyond the layer and reason -- and it cannot override it.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

from .events import Event


@dataclass
class Verdict:
    allowed: bool
    layer: str = "-"
    reason: str = "no policy violation"


class InProcessDecider:
    def __init__(self, guard=None):
        from .daemon import Guard, GuardConfig
        self.guard = guard or Guard(GuardConfig(incidents_path=None, heartbeat_every=0))

    def decide(self, event: Event) -> Verdict:
        effective = self.guard.handle(event)
        if effective == "allowed":
            return Verdict(True)
        last = self.guard.log.records[-1]
        return Verdict(False, last.layer, last.reason)


class HttpDecider:
    def __init__(self, url: str = "http://127.0.0.1:8765", token: str | None = None,
                 timeout: float = 5.0):
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def decide(self, event: Event) -> Verdict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-AEGIS-Token"] = self.token
        req = urllib.request.Request(self.url + "/event",
                                     data=json.dumps(event.to_dict()).encode(),
                                     headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            out = json.loads(resp.read())
        return Verdict(bool(out.get("allowed")), out.get("layer", "-"), out.get("reason", ""))
