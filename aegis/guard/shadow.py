"""Shadow mode: what the guard *would* have done, before you let it act.

Nobody points an autonomous blocker at production on day one. They run it
alongside, in shadow, over real traffic, and read a report: here is everything it
would have blocked, grouped so you can check each line, and here is whether it
touched anything legitimate.

The guard has no side effects -- a "block" is only a decision returned to the
caller -- so shadow mode is simply: run the enforcement path over a log and report
the decisions without wiring them into anything.

The report is the adoption artifact. The line that matters most is
``legitimate sessions blocked``: if that is zero, enforcement is safe to turn on.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import dataclass, field

from .daemon import Autonomy, Guard, GuardConfig

BLOCK_ACTIONS = ("blocked", "quarantined")


@dataclass
class ShadowReport:
    events: int = 0
    would_allow: int = 0
    would_block: int = 0
    sessions_flagged: int = 0
    would_quarantine: list = field(default_factory=list)
    by_layer: dict = field(default_factory=dict)
    by_severity: dict = field(default_factory=dict)
    legitimate_sessions_blocked: list = field(default_factory=list)
    blocked_examples: list = field(default_factory=list)


def run_shadow(events, engine=None, legitimate_marker: str = "legit") -> ShadowReport:
    guard = Guard(GuardConfig(autonomy=Autonomy.ENFORCE, heartbeat_every=0,
                              incidents_path=None), engine)
    guard.run(events, quiet=True)

    rep = ShadowReport(events=guard.seen)
    blocks = [i for i in guard.log.records if i.action in BLOCK_ACTIONS]
    rep.would_block = guard.counts["blocked"]
    rep.would_allow = rep.events - rep.would_block
    rep.sessions_flagged = len({i.source for i in blocks})
    rep.would_quarantine = sorted(guard.quarantined)
    rep.by_layer = dict(Counter(i.layer for i in blocks).most_common())
    rep.by_severity = dict(Counter(i.severity for i in blocks).most_common())
    rep.legitimate_sessions_blocked = sorted(
        {i.source for i in blocks if legitimate_marker in i.source})
    rep.blocked_examples = [
        {"source": i.source, "kind": i.kind, "layer": i.layer,
         "severity": i.severity, "reason": i.reason, "detail": i.detail}
        for i in blocks[:12]
    ]
    return rep


def _table(headers, rows) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def markdown(rep: ShadowReport, title: str = "AEGIS shadow-mode report") -> str:
    pct = f"{(rep.would_block / rep.events * 100):.1f}%" if rep.events else "0.0%"
    L = [f"# {title}", "",
         f"Replayed **{rep.events}** events in shadow mode. The guard would have blocked "
         f"**{rep.would_block}** of them ({pct}) across **{rep.sessions_flagged}** sessions.", ""]

    L += ["## 1. What enforcement would do", "",
          _table(["Metric", "Value"], [
              ["Events seen", str(rep.events)],
              ["Would allow", str(rep.would_allow)],
              ["Would block", str(rep.would_block)],
              ["Sessions flagged", str(rep.sessions_flagged)],
              ["Sessions that would be quarantined", str(len(rep.would_quarantine))],
              ["**Legitimate sessions blocked**", f"**{len(rep.legitimate_sessions_blocked)}**"],
          ]), ""]

    L += ["## 2. What it would have blocked, by layer", "",
          _table(["Layer", "Blocks"], [[k, str(v)] for k, v in rep.by_layer.items()] or [["—", "0"]]), "",
          _table(["Severity", "Blocks"], [[k, str(v)] for k, v in rep.by_severity.items()] or [["—", "0"]]), ""]

    if rep.would_quarantine:
        L += ["## 3. Sessions that would be quarantined", ""]
        L += [f"- `{s}`" for s in rep.would_quarantine]
        L.append("")

    L += ["## 4. Sample of blocked events (check each line)", ""]
    rows = [[f"`{e['source'][:24]}`", e["kind"], e["layer"], e["severity"], e["reason"][:52]]
            for e in rep.blocked_examples]
    L += [_table(["Session", "Kind", "Layer", "Severity", "Reason"], rows) if rows else "_none_", ""]

    verdict = ("**No legitimate traffic was touched.** Enforcement is safe to switch on."
               if not rep.legitimate_sessions_blocked
               else f"**{len(rep.legitimate_sessions_blocked)} legitimate session(s) would be blocked** — "
                    f"fix the policy before enabling enforcement: "
                    f"{', '.join('`' + s + '`' for s in rep.legitimate_sessions_blocked)}.")
    L += ["## 5. The decision", "",
          "Run in `observe` first, read this report, then move to `enforce`.", "", verdict, ""]
    return "\n".join(L)


def write_report(rep: ShadowReport, path: str, title: str = "AEGIS shadow-mode report") -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(markdown(rep, title))
    return path
