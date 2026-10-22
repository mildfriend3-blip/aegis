"""The guard's enforcement core.

It applies the *hardened* defence stack -- the one the adaptive attacker could not
get through -- to live events. The mapping is direct:

* a ``prompt``     is passed through the input sanitizer; if it is rewritten, the
  instruction carried an injection signature and the guard refuses it
* a ``tool_call``  is passed through the tool-call policy; if the call breaks
  policy it is refused, whatever the model believed it was doing
* a ``response``   is passed through the output filter; if it reveals the secret
  in any encoding, it is refused

Because the enforcement reuses the same ``DefenseStack`` the benchmark scores,
the guard's measured bypass rate *is* the ``hardened`` config's -- the guard does
not get to be better than its own benchmark.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..defenses import build_defense
from ..types import ToolCall


@dataclass
class Decision:
    action: str        # "allow" | "block"
    severity: str      # info | low | medium | high | critical
    layer: str         # which layer made the call, or "-"
    reason: str

    @property
    def blocked(self) -> bool:
        return self.action == "block"


ALLOW = Decision("allow", "info", "-", "no policy violation")


class GuardEngine:
    def __init__(self, defense=None):
        self.defense = defense if defense is not None else build_defense("hardened")

    # -- one event in, one decision out ----------------------------------
    def evaluate(self, event) -> Decision:
        if event.kind == "prompt":
            return self._check_prompt(event)
        if event.kind == "tool_call":
            return self._check_tool_call(event)
        if event.kind == "response":
            return self._check_response(event)
        return Decision("block", "medium", "engine", f"unknown event kind '{event.kind}'")

    def _check_prompt(self, event) -> Decision:
        text = event.text or ""
        if not text:
            return ALLOW
        rewritten, _ = self.defense.transform_inputs(text, [])
        if rewritten != text:
            return Decision("block", "medium", "sanitizer",
                            "inbound instruction carried an injection signature")
        return ALLOW

    def _check_tool_call(self, event) -> Decision:
        if not event.tool:
            return Decision("block", "medium", "engine", "tool_call with no tool name")
        call = ToolCall(event.tool, event.args or {})
        allowed, blocked = self.defense.filter_tool_calls([call])
        if blocked:
            return Decision("block", "high", "tool-policy", blocked[0].reason)
        return ALLOW

    def _check_response(self, event) -> Decision:
        text = event.text or ""
        if not text:
            return ALLOW
        filtered = self.defense.filter_response(text)
        if filtered != text:
            return Decision("block", "high", "output-filter",
                            "response revealed the protected secret")
        return ALLOW
