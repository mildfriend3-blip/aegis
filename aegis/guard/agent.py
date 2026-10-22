"""A guarded agent -- an agent whose every move passes the guard first.

This is the loop closed. The guard is not a report and not a wrapper around the
benchmark; it sits in the agent's path:

1. the inbound instruction is checked at the door; a refused prompt means the
   agent never acts on it
2. the agent proposes its tool calls, and each one is checked **before** it runs
   -- only allowed calls are returned for execution
3. the answer is checked before it leaves; a leaking answer is withheld

Because the agent returns only the calls that survived, the existing evaluation
harness can score it unchanged: run it with the ``none`` defence and the guard is
the only thing standing between the model and the world. If an attack still
records its forbidden effect, the guard has a hole -- and the number that matters
is zero.
"""
from __future__ import annotations

from ..targets import MockAgent
from ..types import AgentRun
from .client import InProcessDecider
from .events import Event


class GuardedAgent:
    """Wraps any agent and puts the guard in its path."""

    name = "guarded-agent"

    def __init__(self, inner=None, decider=None, session: str = "agent"):
        self.inner = inner if inner is not None else MockAgent()
        self.decider = decider if decider is not None else InProcessDecider()
        self.session = session
        # -- what happened, for reporting
        self.refused_prompt = False
        self.proposed_calls = 0
        self.blocked_calls = 0
        self.blocked_reasons: list[str] = []
        self.withheld_answer = False

    def run(self, task: str, documents: list[str]) -> AgentRun:
        # 1. the door
        if not self.decider.decide(Event(source=self.session, kind="prompt", text=task)).allowed:
            self.refused_prompt = True
            return AgentRun(final_response="", tool_calls=[])

        # 2. the model acts
        run = self.inner.run(task, documents)

        # 3. every action is checked before it happens
        allowed = []
        for call in run.tool_calls:
            self.proposed_calls += 1
            verdict = self.decider.decide(
                Event(source=self.session, kind="tool_call", tool=call.name, args=call.args))
            if verdict.allowed:
                allowed.append(call)
            else:
                self.blocked_calls += 1
                self.blocked_reasons.append(verdict.reason)

        # 4. the answer is checked before it leaves
        response = run.final_response
        if not self.decider.decide(
                Event(source=self.session, kind="response", text=response)).allowed:
            self.withheld_answer = True
            response = ""

        return AgentRun(final_response=response, tool_calls=allowed)
