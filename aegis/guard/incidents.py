"""The guard's memory: one durable record per decision worth keeping.

Every block (or recommended block) is written as a JSON line, so the guard leaves
an audit trail an operator can review, ship to a SIEM, or diff over time. The
record carries the event, the layer that caught it, and the analyst summary.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

SEVERITIES = ("info", "low", "medium", "high", "critical")


@dataclass
class Incident:
    source: str
    kind: str
    action: str          # observed | recommended-block | blocked | quarantined
    severity: str
    layer: str
    reason: str
    detail: str = ""     # the offending text / call, truncated
    triage: str = ""     # one-line analyst summary
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return {"ts": self.ts, "source": self.source, "kind": self.kind,
                "action": self.action, "severity": self.severity, "layer": self.layer,
                "reason": self.reason, "detail": self.detail, "triage": self.triage}


class IncidentLog:
    """Append-only JSONL sink. ``path=None`` keeps incidents in memory only."""

    def __init__(self, path: str | None = None):
        self.path = path
        self.records: list[Incident] = []
        self._fh = None
        if path:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            self._fh = open(path, "a", encoding="utf-8")

    def write(self, incident: Incident) -> None:
        self.records.append(incident)
        if self._fh:
            self._fh.write(json.dumps(incident.to_dict()) + "\n")
            self._fh.flush()

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None
