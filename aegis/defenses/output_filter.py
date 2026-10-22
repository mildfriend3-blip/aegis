"""Layer 4 -- output filtering.

The last line of defence against *response leakage*: if the protected secret
appears in the agent's final answer, it is redacted. Cheap, and it covers the
one objective (secret_leak_response) that a tool-call policy cannot see, because
no tool call is involved.
"""
from __future__ import annotations

from ..world import SECRET_SENTINEL
from .base import Defense


class OutputFilter(Defense):
    name = "output-filter"

    def __init__(self, secret_sentinel: str = SECRET_SENTINEL,
                 replacement: str = "[REDACTED]"):
        self.secret_sentinel = secret_sentinel
        self.replacement = replacement

    def filter_response(self, response: str) -> str:
        return (response or "").replace(self.secret_sentinel, self.replacement)
