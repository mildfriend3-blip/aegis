from __future__ import annotations

from ..types import ToolCall, ToolResult


class Defense:
    """A defensive layer. Layers compose: a DefenseStack runs each in order."""

    name = "base"

    def transform_inputs(self, task: str, documents: list[str]) -> tuple[str, list[str]]:
        """Rewrite inbound text (task + untrusted docs) before the agent sees it."""
        return task, documents

    def filter_tool_calls(self, calls: list[ToolCall]) -> tuple[list[ToolCall], list[ToolResult]]:
        """Split proposed tool calls into (allowed, blocked)."""
        return calls, []

    def filter_response(self, response: str) -> str:
        """Post-process the agent's final answer."""
        return response


class DefenseStack(Defense):
    """Compose several defenses; each stage is applied in sequence."""

    def __init__(self, layers: list[Defense] | None = None, name: str | None = None):
        self.layers = layers or []
        self.name = name or ("+".join(l.name for l in self.layers) or "none")

    def transform_inputs(self, task, documents):
        for l in self.layers:
            task, documents = l.transform_inputs(task, documents)
        return task, documents

    def filter_tool_calls(self, calls):
        allowed, blocked = calls, []
        for l in self.layers:
            allowed, b = l.filter_tool_calls(allowed)
            blocked.extend(b)
        return allowed, blocked

    def filter_response(self, response):
        for l in self.layers:
            response = l.filter_response(response)
        return response
