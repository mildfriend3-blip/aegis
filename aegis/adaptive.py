"""The adaptive attacker.

Given a defence, it searches the mutation space for each attack and reports
whether *any* variant still achieves the forbidden effect. The number it produces
is the honest counter to the static benchmark: a fixed catalogue can read 0% while
an attacker who is allowed to search finds a way through.

The search is breadth-first over the mutation families and stops at the first
variant that lands, recording which family won -- so the result is not just
"bypassed / not" but "bypassed, and by encoding the answer".
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass

from .attacks import ATTACKS, BENIGN_DOCS, BENIGN_TASK
from .attacks.mutations import mutations_for
from .defenses import build_defense
from .harness import run_case
from .targets import MockAgent
from .world import World


@dataclass
class Bypass:
    attack_id: str
    category: str
    objective: str
    defense: str
    success: bool
    mutation: str | None = None   # winning mutation tag, "original", or None
    tried: int = 0


def _succeeds(attack, defense, agent_factory, world_factory, benign_task, benign_docs) -> bool:
    return run_case(attack, defense, agent_factory, world_factory,
                    benign_task, benign_docs).success


def adaptive_search(attack, defense, agent_factory=MockAgent, world_factory=World,
                    benign_task: str = BENIGN_TASK, benign_docs: list | None = None,
                    max_depth: int = 2, budget: int = 600) -> Bypass:
    """Breadth-first search over the mutation space, up to ``max_depth`` composed
    mutations, stopping at the first variant that lands. Depth 2 matters: some
    defences fall only to a *combination* -- paraphrase the trigger away, then
    ask for the answer encoded."""
    benign_docs = benign_docs if benign_docs is not None else BENIGN_DOCS

    def run(a) -> bool:
        return _succeeds(a, defense, agent_factory, world_factory, benign_task, benign_docs)

    def result(ok, tag, n):
        return Bypass(attack.id, attack.category, attack.objective, defense.name, ok, tag, n)

    if run(attack):
        return result(True, "original", 0)

    tried = 0
    frontier = [(attack, "")]
    for _ in range(max_depth):
        nxt = []
        for base, prefix in frontier:
            for tag, variant in mutations_for(base):
                tried += 1
                if tried > budget:
                    return result(False, None, tried)
                full = f"{prefix}+{tag}" if prefix else tag
                if run(variant):
                    return result(True, full, tried)
                nxt.append((variant, full))
        frontier = nxt
    return result(False, None, tried)


def run_adaptive(attacks: list | None = None, defense_names: list | None = None,
                 agent_factory=MockAgent, world_factory=World) -> list[Bypass]:
    attacks = attacks if attacks is not None else ATTACKS
    defense_names = defense_names or ["none", "full", "hardened"]
    out: list[Bypass] = []
    for name in defense_names:
        defense = build_defense(name)
        for attack in attacks:
            out.append(adaptive_search(attack, defense, agent_factory, world_factory))
    return out


# --- aggregation --------------------------------------------------------
def bypass_rate(records) -> float:
    records = list(records)
    if not records:
        return 0.0
    return sum(r.success for r in records) / len(records)


def by_defense(records) -> dict:
    groups = defaultdict(list)
    for r in records:
        groups[r.defense].append(r)
    return {d: {"bypass_rate": bypass_rate(rs), "n": len(rs)} for d, rs in groups.items()}


def winning_mutations(records) -> dict:
    """Which mutation family beat each defence, counted."""
    return dict(Counter(r.mutation for r in records if r.success).most_common())


def by_objective(records) -> dict:
    groups = defaultdict(list)
    for r in records:
        groups[(r.defense, r.objective)].append(r)
    return {f"{d} · {o}": bypass_rate(rs) for (d, o), rs in groups.items()}


# --- reporting ----------------------------------------------------------
_PCT = lambda x: f"{x * 100:5.1f}%"


def _table(headers, rows) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def markdown(records: list[Bypass], title: str = "AEGIS Adaptive Attack Report") -> str:
    per_def = by_defense(records)
    defs = list(per_def)
    lines = [f"# {title}", "",
             "The adaptive attacker mutates each attack and reports whether *any* "
             "variant still lands. A defence can read 0% statically and still fall "
             "to an attacker who searches.", ""]

    lines += ["## 1. Adaptive bypass rate by defence", ""]
    rows = [[d, _PCT(per_def[d]["bypass_rate"]), str(per_def[d]["n"])] for d in defs]
    lines += [_table(["Defence", "Bypass rate (lower=better)", "Attacks"], rows), ""]

    lines += ["## 2. What beats each defence", ""]
    for d in defs:
        wins = winning_mutations([r for r in records if r.defense == d])
        if not wins:
            lines.append(f"- **{d}**: nothing bypassed it.")
            continue
        top = ", ".join(f"{k} ({v})" for k, v in list(wins.items())[:5])
        lines.append(f"- **{d}**: {top}")
    lines.append("")

    lines += ["## 3. Bypass rate by defence and objective", ""]
    obj = by_objective(records)
    objectives = sorted({o for _, o in [(r.defense, r.objective) for r in records]})
    rows = []
    for d in defs:
        rows.append([d] + [_PCT(obj.get(f"{d} · {o}", 0.0)) for o in objectives])
    lines += [_table(["Defence", *objectives], rows), ""]

    return "\n".join(lines)


def write_results(records: list[Bypass], outdir: str,
                  title: str = "AEGIS Adaptive Attack Report") -> dict:
    os.makedirs(outdir, exist_ok=True)
    md = os.path.join(outdir, "adaptive.md")
    js = os.path.join(outdir, "adaptive.json")
    with open(md, "w") as fh:
        fh.write(markdown(records, title))
    with open(js, "w") as fh:
        json.dump([r.__dict__ for r in records], fh, indent=2)
    return {"markdown": md, "json": js, "summary": by_defense(records)}
