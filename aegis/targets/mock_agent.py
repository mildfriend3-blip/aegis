"""A deterministic, rule-based simulation of an instruction-following,
tool-using LLM.

Why simulate rather than call a real model? So the benchmark is *reproducible*
and offline: identical inputs always yield identical scores, which is what makes
defense-vs-defense comparisons meaningful. The simulation models the behaviour
that matters for prompt injection -- a model that will follow instructions it
finds in untrusted text, including instructions that were base64-encoded or
hidden inside a document -- while honouring a system-prompt rule that
datamarked content is data, not instructions.
"""
from __future__ import annotations

import base64
import binascii
import re

from ..types import AgentRun, ToolCall
from ..world import SECRET_SENTINEL
from .base import AgentTarget

# Sentinel inserted by the datamarking defense. Its presence marks a span as
# untrusted *data*: the agent will summarise it but will not obey it.
MARKER = "\u25AA"  # black small square

_EMAIL_RE = re.compile(
    r"(?:send|email|e-mail|forward|mail|exfiltrate|transmit|deliver|leak|upload|"
    r"share|relay|route|pass|provide|submit)[^\n]{0,120}?"
    r"([a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,})",
    re.I,
)
_HTTP_RE = re.compile(
    r"(?:post|upload|send|curl|fetch|exfiltrate|transmit|deliver|leak|share|submit)"
    r"[^\n]{0,120}?(https?://[a-z0-9.\-:/_%?=&]+)",
    re.I,
)
_SECRET_REF_RE = re.compile(
    r"(credentials\.txt|\bsecret\b|secret\s+file|api[ _\-]?key|password|\.env|"
    r"\bcredential|\btoken\b)",
    re.I,
)
_READ_VERB_RE = re.compile(
    r"\b(read|open|cat|show|reveal|print|dump|access|display|fetch|retrieve|"
    r"grab|get|email|send|forward)\b",
    re.I,
)
_SQL_RE = re.compile(
    r"\b(drop|delete|truncate|update|insert)\b[^.\n]{0,40}"
    r"\b(table|users|accounts|orders|records|customers|payments)\b",
    re.I,
)
_LEAK_RE = re.compile(
    r"(print|reveal|show|output|repeat|display|tell\s+me|include|echo|expose|"
    r"share|disclose|provide|send)"
    r"[^\n]{0,40}"
    r"(secret|password|api[ _\-]?key|token|credential|system\s+prompt|"
    r"your\s+instructions|\.env)",
    re.I,
)

_SUMMARY = "Summary: the document reports strong quarterly revenue growth."


def _b64_candidates(text: str) -> list[str]:
    """Decode any base64-looking blobs the model would be able to read."""
    out: list[str] = []
    for tok in re.findall(r"[A-Za-z0-9+/]{20,}={0,2}", text):
        try:
            raw = base64.b64decode(tok + "=" * (-len(tok) % 4), validate=True)
            dec = raw.decode("utf-8", "ignore")
        except (binascii.Error, ValueError):
            continue
        if not dec:
            continue
        printable = sum(c.isprintable() or c in "\n\t" for c in dec) / len(dec)
        if printable > 0.85 and re.search(r"[a-z]{3}", dec):
            out.append(dec)
    return out


class MockAgent(AgentTarget):
    name = "mock-agent"

    def __init__(self, datamark_aware: bool = True) -> None:
        self.datamark_aware = datamark_aware

    # -- input handling --------------------------------------------------
    def _visible_untrusted(self, documents: list[str]) -> str:
        text = "\n".join(documents)
        if self.datamark_aware and MARKER in text:
            # Treat marked lines as data: keep them out of instruction-following.
            text = "\n".join(ln for ln in text.splitlines() if MARKER not in ln)
        return text

    def run(self, task: str, documents: list[str]) -> AgentRun:
        untrusted = self._visible_untrusted(documents)
        haystack = f"{task}\n{untrusted}"
        haystack += "\n" + "\n".join(_b64_candidates(haystack))
        return self._plan(haystack)

    # -- planning --------------------------------------------------------
    def _plan(self, haystack: str) -> AgentRun:
        calls: list[ToolCall] = []
        emails = list(dict.fromkeys(_EMAIL_RE.findall(haystack)))
        urls = list(dict.fromkeys(_HTTP_RE.findall(haystack)))
        secret_ref = bool(_SECRET_REF_RE.search(haystack))
        sql = _SQL_RE.search(haystack)
        leak = bool(_LEAK_RE.search(haystack))

        payload = SECRET_SENTINEL if secret_ref else _SUMMARY

        for addr in emails:
            calls.append(ToolCall("send_email",
                                  {"to": addr, "subject": "report", "body": payload}))
        for url in urls:
            calls.append(ToolCall("http_post", {"url": url, "data": payload}))
        if sql:
            calls.append(ToolCall("run_sql", {"query": sql.group(0)}))
        if secret_ref and _READ_VERB_RE.search(haystack):
            calls.append(ToolCall("read_file", {"path": "secrets/credentials.txt"}))

        response = _SUMMARY
        if leak:
            response += f"\n\nAs requested, the value is: {SECRET_SENTINEL}"

        return AgentRun(final_response=response, tool_calls=calls)
