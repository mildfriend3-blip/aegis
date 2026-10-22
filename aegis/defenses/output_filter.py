"""Layer 4 -- output filtering.

The last line of defence against *response leakage*: if the protected secret
appears in the agent's final answer, it is redacted. Cheap, and it covers the one
objective (secret_leak_response) that a tool-call policy cannot see, because no
tool call is involved.

Two variants ship here, and the difference between them is the point of the
adaptive benchmark:

* ``OutputFilter`` matches the secret literally. It stops a plain leak, but a
  secret the model was told to return base64-, hex-, rot13- or reverse-encoded is
  not that literal string, so it slips straight through.
* ``DecodingOutputFilter`` asks the shared ``reveals_secret`` check -- the same
  definition the benchmark uses to *score* a leak -- so it cannot disagree with
  the scorer. It redacts a literal leak surgically and fails closed on an encoded
  one. That closes the encoding bypass the adaptive attacker finds, at the cost
  of still not covering an encoding it does not know about: the arms race, in
  miniature.
"""
from __future__ import annotations

from ..world import SECRET_SENTINEL, reveals_secret
from .base import Defense


class OutputFilter(Defense):
    name = "output-filter"

    def __init__(self, secret_sentinel: str = SECRET_SENTINEL,
                 replacement: str = "[REDACTED]"):
        self.secret_sentinel = secret_sentinel
        self.replacement = replacement

    def filter_response(self, response: str) -> str:
        return (response or "").replace(self.secret_sentinel, self.replacement)


class DecodingOutputFilter(Defense):
    """Hardened output filter: detects the secret in any known encoding."""

    name = "output-filter-decoding"

    def __init__(self, secret_sentinel: str = SECRET_SENTINEL,
                 replacement: str = "[REDACTED]"):
        self.secret_sentinel = secret_sentinel
        self.replacement = replacement

    def filter_response(self, response: str) -> str:
        out = (response or "").replace(self.secret_sentinel, self.replacement)
        if reveals_secret(out, self.secret_sentinel):
            return self.replacement  # fail closed on an encoded leak
        return out
