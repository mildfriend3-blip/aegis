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
import codecs
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


def _looks_like_text(s: str) -> bool:
    if not s:
        return False
    printable = sum(c.isprintable() or c in "\n\t" for c in s) / len(s)
    return printable > 0.85 and bool(re.search(r"[a-z]{3}", s))


def _decode_candidates(text: str) -> list[str]:
    """Decode the encodings a capable model would be able to read: base64 and hex
    blobs anywhere, plus rot13 and reversed text when the input asks for it."""
    out: list[str] = []
    for tok in re.findall(r"[A-Za-z0-9+/]{20,}={0,2}", text):
        try:
            dec = base64.b64decode(tok + "=" * (-len(tok) % 4), validate=True).decode("utf-8", "ignore")
        except (binascii.Error, ValueError):
            continue
        if _looks_like_text(dec):
            out.append(dec)
    for tok in re.findall(r"\b[0-9a-fA-F]{24,}\b", text):
        if len(tok) % 2:
            continue
        try:
            dec = bytes.fromhex(tok).decode("utf-8", "ignore")
        except ValueError:
            continue
        if _looks_like_text(dec):
            out.append(dec)
    if re.search(r"rot\s*-?13", text, re.I):
        out.append(codecs.decode(text, "rot_13"))
    if re.search(r"revers|backwards|back-to-front", text, re.I):
        out.append(text[::-1])
    return out


# An instruction to return the value in an encoded form ("... base64-encoded",
# "encode it as hex"). Deliberately narrower than just naming an encoding, so a
# payload that merely *carries* a base64 blob does not also trigger it.
_ENCODE_INSTR_RE = re.compile(
    r"(?:encod\w*[^\n]{0,30}?\b(base64|b64|hex|hexadecimal|rot\s*-?13|reversed?|backwards)"
    r"|\b(base64|b64|hex|hexadecimal|rot\s*-?13|reversed?|backwards)[\s-]*encod)",
    re.I,
)


def _encode_value(value: str, name: str) -> str:
    n = (name or "").lower()
    if n.startswith("b64") or "base64" in n:
        return base64.b64encode(value.encode()).decode()
    if "hex" in n:
        return value.encode().hex()
    if n.startswith("rot"):
        return codecs.encode(value, "rot_13")
    return value[::-1]  # reversed / backwards


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
        haystack += "\n" + "\n".join(_decode_candidates(haystack))
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
            enc = _ENCODE_INSTR_RE.search(haystack)
            value = _encode_value(SECRET_SENTINEL, (enc.group(1) or enc.group(2))) if enc else SECRET_SENTINEL
            response += f"\n\nAs requested, the value is: {value}"

        return AgentRun(final_response=response, tool_calls=calls)
