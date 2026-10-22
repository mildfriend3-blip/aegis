"""Layer 1 -- input sanitisation.

A signature-based filter: sentences containing classic injection markers
("ignore previous instructions", "you are now", role-play openers, ...) are
redacted before the agent sees them. This is what most naive in-house filters
do. Its weakness is deliberate and measurable: it only catches *known* phrasings,
so paraphrased or encoded payloads slip through.
"""
from __future__ import annotations

import re

from .base import Defense

INJECTION_SIGNATURES = [
    re.compile(p, re.I) for p in (
        r"(ignore|disregard|forget|override)\s+(all\s+)?(the\s+)?"
        r"(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|context)",
        r"you\s+are\s+now\b",
        r"new\s+instructions?\s*[:.\-]",
        r"system\s*[:>]",
        r"<\s*/?\s*(system|assistant|im_start|im_end)\s*>",
        r"\bAI\s*[:>]",
        r"do\s+not\s+(tell|inform|notify)\s+the\s+user",
        r"as\s+an?\s+(ai|assistant|language\s+model)\b[^.\n]{0,40}"
        r"(you\s+(must|will|should)|ignore)",
        r"\bdeveloper\s+mode\b",
        r"pretend\s+(to\s+be|you\s+are)",
        r"act\s+as\s+(if|though|an?\b)",
    )
]

_REDACTION = " [redacted: possible prompt injection] "
_SPLIT = re.compile(r"(?<=[.!?\n])")


class InputSanitizer(Defense):
    name = "sanitizer"

    def __init__(self, signatures: list[re.Pattern] | None = None):
        self.signatures = signatures if signatures is not None else INJECTION_SIGNATURES

    def _scrub(self, text: str) -> str:
        out = []
        for sentence in _SPLIT.split(text):
            if sentence and any(s.search(sentence) for s in self.signatures):
                out.append(_REDACTION)
            else:
                out.append(sentence)
        return "".join(out)

    def transform_inputs(self, task, documents):
        return self._scrub(task), [self._scrub(d) for d in documents]
