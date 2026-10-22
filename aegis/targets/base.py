from __future__ import annotations

from abc import ABC, abstractmethod

from ..types import AgentRun


class AgentTarget(ABC):
    """An agent under test: given a task and some untrusted documents, it
    proposes tool calls and produces a final response."""

    name = "agent"

    @abstractmethod
    def run(self, task: str, documents: list[str]) -> AgentRun:  # pragma: no cover
        raise NotImplementedError
