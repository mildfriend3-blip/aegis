"""Core data types shared across AEGIS."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# The effect an attack is trying to cause. Success is defined per-effect.
OBJECTIVES = (
    "exfil_email",          # send protected data to an external recipient
    "exfil_http",           # POST protected data to an external host
    "secret_leak_response", # emit protected data in the final answer
    "destructive_sql",      # execute a destructive database statement
)


@dataclass
class ToolCall:
    """A tool invocation proposed by an agent."""
    name: str
    args: dict
    id: str = ""


@dataclass
class ToolResult:
    """Outcome of executing (or blocking) a tool call."""
    name: str
    ok: bool
    output: str = ""
    blocked: bool = False
    reason: str = ""


@dataclass
class AgentRun:
    """Everything an agent produced for one input."""
    final_response: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)   # proposed
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Attack:
    """A single prompt-injection test case."""
    id: str
    name: str
    category: str
    channel: str            # "user" (direct) | "document" (indirect)
    objective: str          # one of OBJECTIVES
    payload: str
    turns: Optional[list[str]] = None   # multi-turn variant (user channel)
    notes: str = ""


@dataclass
class RunRecord:
    """The result of one (attack, defense) evaluation."""
    attack_id: str
    attack_category: str
    objective: str
    defense: str
    success: bool
    blocked_calls: int = 0
    proposed_calls: int = 0
    executed_calls: int = 0
    utility_ok: bool = False
    detail: dict[str, Any] = field(default_factory=dict)
