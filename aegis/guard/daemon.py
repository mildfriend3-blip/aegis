"""The always-on guard.

A watch loop over an event stream that never stops on its own. For every event it
asks the engine for a decision, then acts on it according to the configured
*autonomy*:

* ``observe``   -- record everything, act on nothing (shadow mode; use it first)
* ``recommend`` -- record and alert, but never block (a human decides)
* ``enforce``   -- record, alert and block; a repeat offender is quarantined

Autonomy is the safety design, not a nicety. Nobody should point an autonomous
blocker at production on day one; they run it in shadow mode, read the incidents,
then turn enforcement on. The guard also takes a kill switch (``SIGTERM`` or a
stop-file) and stands down gracefully with a final report.
"""
from __future__ import annotations

import os
import signal
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from .engine import GuardEngine
from .events import Event
from .incidents import Incident, IncidentLog
from .triage import triage as default_triage


class Autonomy(str, Enum):
    OBSERVE = "observe"
    RECOMMEND = "recommend"
    ENFORCE = "enforce"


@dataclass
class GuardConfig:
    autonomy: Autonomy = Autonomy.ENFORCE
    quarantine_threshold: int = 3      # violations from one session before it is cut off
    heartbeat_every: int = 20          # status line every N events (0 disables)
    stop_file: str | None = None       # touch this file to stand the guard down
    incidents_path: str | None = None  # JSONL audit trail
    triage_llm: object | None = None   # optional advisory analyst


class Guard:
    def __init__(self, config: GuardConfig | None = None, engine: GuardEngine | None = None):
        self.config = config or GuardConfig()
        self.engine = engine or GuardEngine()
        self.log = IncidentLog(self.config.incidents_path)
        self.counts: Counter = Counter()
        self.per_session_blocks: Counter = Counter()
        self.quarantined: set[str] = set()
        self.seen = 0
        self._stop = False

    # -- lifecycle -------------------------------------------------------
    def request_stop(self, *_):
        self._stop = True

    def _install_signals(self) -> None:
        try:
            signal.signal(signal.SIGTERM, self.request_stop)
            signal.signal(signal.SIGINT, self.request_stop)
        except (ValueError, OSError, AttributeError):
            pass

    def _stop_requested(self) -> bool:
        if self._stop:
            return True
        sf = self.config.stop_file
        return bool(sf) and os.path.exists(sf)

    # -- the work --------------------------------------------------------
    def handle(self, event: Event) -> str:
        self.seen += 1
        if event.source in self.quarantined:
            self._record(event, "quarantined", "critical", "quarantine",
                         f"session '{event.source}' is quarantined")
            effective = "blocked"
        else:
            decision = self.engine.evaluate(event)
            if decision.blocked:
                self.per_session_blocks[event.source] += 1
                effective = self._enforce(event, decision)
            else:
                effective = "allowed"

        self.counts[effective] += 1
        if self.config.heartbeat_every and self.seen % self.config.heartbeat_every == 0:
            self._heartbeat()
        return effective

    def _enforce(self, event: Event, decision) -> str:
        autonomy = self.config.autonomy
        if autonomy is Autonomy.OBSERVE:
            effective = "observed"
        elif autonomy is Autonomy.RECOMMEND:
            effective = "recommended"
        else:
            effective = "blocked"

        self._record(event, effective, decision.severity, decision.layer, decision.reason)

        if (autonomy is Autonomy.ENFORCE
                and self.per_session_blocks[event.source] >= self.config.quarantine_threshold
                and event.source not in self.quarantined):
            self.quarantined.add(event.source)
            self._record(event, "quarantined", "critical", "quarantine",
                         f"session '{event.source}' cut off after "
                         f"{self.per_session_blocks[event.source]} policy violations")
        return effective

    def _record(self, event: Event, action: str, severity: str, layer: str, reason: str) -> None:
        detail = event.label() if event.kind == "tool_call" else (event.text or "")[:120]
        incident = Incident(source=event.source, kind=event.kind, action=action,
                            severity=severity, layer=layer, reason=reason, detail=detail)
        incident.triage = default_triage(incident, self.config.triage_llm)
        self.log.write(incident)

    def _heartbeat(self) -> None:
        print(f"  [guard] on watch - {self.seen} events, {self.counts['blocked']} blocked, "
              f"{len(self.quarantined)} session(s) quarantined", flush=True)

    # -- the loop --------------------------------------------------------
    def run(self, events, max_events: int | None = None, quiet: bool = False) -> dict:
        self._install_signals()
        started = datetime.now(timezone.utc)
        try:
            for event in events:
                if max_events is not None and self.seen >= max_events:
                    break
                if self._stop_requested():
                    print("  [guard] stand-down requested - disengaging", flush=True)
                    break
                effective = self.handle(event)
                if not quiet and effective in ("blocked", "quarantined"):
                    last = self.log.records[-1]
                    print(f"  [BLOCK] {event.source:<26} {last.layer:<13} {last.reason}")
        finally:
            self.log.close()
        return self.summary(started)

    def summary(self, started=None) -> dict:
        ended = datetime.now(timezone.utc)
        return {
            "autonomy": self.config.autonomy.value,
            "events": self.seen,
            "allowed": self.counts["allowed"],
            "blocked": self.counts["blocked"],
            "recommended": self.counts["recommended"],
            "observed": self.counts["observed"],
            "quarantined_sessions": sorted(self.quarantined),
            "incidents": len(self.log.records),
            "seconds": round((ended - started).total_seconds(), 3) if started else None,
        }
