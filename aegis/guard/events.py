"""The unit the guard watches: one thing an agent did, or that arrived for it.

Three kinds, matching the three places a defence can act:

* ``prompt``     -- an inbound instruction (untrusted text reaching the agent)
* ``tool_call``  -- an action the agent is about to take
* ``response``   -- an answer the agent is about to return

The guard sits *behind* the model and in front of the world, so it sees the
actions and the answers, not just the prompt. That is the whole point: it does
not need the model to resist anything.
"""
from __future__ import annotations

from dataclasses import dataclass, field

KINDS = ("prompt", "tool_call", "response")


@dataclass
class Event:
    source: str                       # session / agent / client id
    kind: str                         # one of KINDS
    text: str = ""                    # prompt text, or the response body
    tool: str | None = None           # tool name, for kind == "tool_call"
    args: dict = field(default_factory=dict)
    ts: str = ""
    meta: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        return cls(
            source=d.get("source", "unknown"),
            kind=d.get("kind", "tool_call"),
            text=d.get("text", "") or "",
            tool=d.get("tool"),
            args=d.get("args") or {},
            ts=d.get("ts", "") or "",
            meta=d.get("meta") or {},
        )

    def to_dict(self) -> dict:
        return {"source": self.source, "kind": self.kind, "text": self.text,
                "tool": self.tool, "args": self.args, "ts": self.ts, "meta": self.meta}

    def label(self) -> str:
        if self.kind == "tool_call":
            return f"{self.tool}({', '.join(f'{k}={v!r}' for k, v in (self.args or {}).items())})"
        return f"{self.kind}: {self.text[:80]}"
