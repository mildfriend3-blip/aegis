"""Layer 2 -- spotlighting / datamarking.

Untrusted documents are transformed so that a sentinel token separates every
word. The agent's system prompt tells it that marked content is *data*: it may be
summarised, but instructions inside it must never be obeyed. This is the
"spotlighting" family of defenses (Hines et al., 2024) and it specifically
targets *indirect* injection -- payloads hidden in retrieved documents -- which
input sanitisation cannot reliably catch.
"""
from __future__ import annotations

from .base import Defense
from ..targets.mock_agent import MARKER


class DataMarking(Defense):
    name = "datamarking"

    def __init__(self, marker: str = MARKER):
        self.marker = marker

    def transform_inputs(self, task, documents):
        marked = [self.marker.join(doc.split()) for doc in documents]
        return task, marked
