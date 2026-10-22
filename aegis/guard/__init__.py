"""AEGIS guard -- an always-on defensive agent for a tool-using LLM agent.

It watches the agent's traffic (inbound instructions, outbound tool calls and
answers), applies the hardened defence stack live, and acts on its own: record,
alert, block, and cut off a repeat offender. The LLM's role is analyst triage --
it explains and prioritises; it never decides whether to block. That decision
belongs to a policy engine, because a model that reads attacker text can be
talked out of a decision and a policy cannot.
"""
from .daemon import Autonomy, Guard, GuardConfig
from .engine import Decision, GuardEngine
from .events import Event
from .incidents import Incident, IncidentLog
from .simulate import live_stream
from .triage import triage

__all__ = ["Autonomy", "Guard", "GuardConfig", "GuardEngine", "Decision", "Event",
           "Incident", "IncidentLog", "live_stream", "triage"]
