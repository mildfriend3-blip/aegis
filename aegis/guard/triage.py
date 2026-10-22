"""Analyst triage: turn a raw block into one line a human can act on.

This is where the LLM earns its place in the guard -- and only here. Triage is
*advisory*: it explains and prioritises. It never decides whether to block. That
separation is deliberate, because a model that reads attacker-controlled text can
be talked out of a decision, and a policy engine cannot.

The default is deterministic and offline. If an LLM adapter is supplied (any
callable taking the incident and returning a string) it is used, with the
deterministic summary as the fallback if it fails -- so the guard never depends
on a model being reachable to stay useful.
"""
from __future__ import annotations

_VERB = {
    "prompt": "sent an instruction carrying an injection signature",
    "tool_call": "attempted a tool call that breaks policy",
    "response": "returned an answer that leaked the protected secret",
}

_IMPACT = {
    "exfil": "protected data leaving the network",
    "secret": "a credential exposed in the agent's answer",
    "destructive": "a destructive database statement",
    "injection": "an attempt to redirect the agent",
}


def _impact(reason: str) -> str:
    r = (reason or "").lower()
    if "domain" in r or "host" in r or "post" in r or "email" in r:
        return _IMPACT["exfil"]
    if "secret" in r:
        return _IMPACT["secret"]
    if "sql" in r:
        return _IMPACT["destructive"]
    return _IMPACT["injection"]


def deterministic(incident) -> str:
    verb = _VERB.get(incident.kind, "tripped a control")
    return (f"{incident.severity.upper()}: session '{incident.source}' {verb} "
            f"({incident.layer}); risk is {_impact(incident.reason)}. "
            f"Action taken: {incident.action}.")


def triage(incident, llm=None) -> str:
    """One-line analyst summary. ``llm`` is optional and advisory only."""
    if llm is not None:
        try:
            out = llm(incident)
            if out and isinstance(out, str):
                return out.strip()
        except Exception:
            pass
    return deterministic(incident)
