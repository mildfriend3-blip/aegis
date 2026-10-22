"""Layer 3 -- a tool-call policy engine (defence in depth).

The strongest layer, because it does not depend on the model resisting the
injection. Every proposed tool call is inspected *before* execution and blocked
if it violates policy: emailing outside the allow-listed domains, POSTing to a
non-allow-listed host, shipping the protected secret off-box, or running a
destructive SQL statement. Even a fully-compromised model cannot cause the
forbidden effect if the effect itself is refused.
"""
from __future__ import annotations

from ..types import ToolCall, ToolResult
from ..world import DESTRUCTIVE_SQL, SECRET_SENTINEL, World
from .base import Defense


class ToolPolicy(Defense):
    name = "tool-policy"

    def __init__(self, allowed_email_domains: set | None = None,
                 allowed_hosts: set | None = None,
                 secret_sentinel: str = SECRET_SENTINEL):
        self.allowed_email_domains = allowed_email_domains or {"corp.example"}
        self.allowed_hosts = allowed_hosts or {"api.corp.example"}
        self.secret_sentinel = secret_sentinel

    def _reason(self, call: ToolCall) -> str | None:
        a = call.args or {}
        if call.name == "send_email":
            dom = World.domain(a.get("to", ""))
            if dom not in self.allowed_email_domains:
                return f"recipient domain '{dom}' not allow-listed"
            if self.secret_sentinel in (a.get("body", "") or "") and \
                    dom not in self.allowed_email_domains:
                return "protected secret in outbound email"
        elif call.name == "http_post":
            host = World.host(a.get("url", ""))
            if host not in self.allowed_hosts:
                return f"host '{host}' not allow-listed"
            if self.secret_sentinel in (a.get("data", "") or ""):
                return "protected secret in outbound POST"
        elif call.name == "run_sql":
            if DESTRUCTIVE_SQL.search(a.get("query", "")):
                return "destructive SQL statement"
        return None

    def filter_tool_calls(self, calls):
        allowed, blocked = [], []
        for c in calls:
            reason = self._reason(c)
            if reason:
                blocked.append(ToolResult(c.name, False, blocked=True, reason=reason))
            else:
                allowed.append(c)
        return allowed, blocked
