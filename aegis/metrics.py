"""Aggregate raw RunRecords into the numbers a report needs."""
from __future__ import annotations

from collections import defaultdict

from .types import RunRecord


def _rate(records, key):
    records = list(records)
    if not records:
        return 0.0
    return sum(bool(getattr(r, key)) for r in records) / len(records)


def asr(records: list[RunRecord]) -> float:
    """Attack Success Rate."""
    return _rate(records, "success")


def utility(records: list[RunRecord]) -> float:
    """Fraction of cases where the legitimate task was still achievable."""
    return _rate(records, "utility_ok")


def by_defense(records: list[RunRecord]) -> dict:
    groups = defaultdict(list)
    for r in records:
        groups[r.defense].append(r)
    return {d: {"asr": asr(rs), "utility": utility(rs), "n": len(rs)}
            for d, rs in groups.items()}


def by_category(records: list[RunRecord]) -> dict:
    groups = defaultdict(list)
    for r in records:
        groups[r.attack_category].append(r)
    return {c: asr(rs) for c, rs in groups.items()}


def matrix(records: list[RunRecord], defense_order: list[str],
           category_order: list[str]) -> list[list[float]]:
    """defense x category ASR table."""
    idx = defaultdict(list)
    for r in records:
        idx[(r.defense, r.attack_category)].append(r)
    return [[asr(idx[(d, c)]) for c in category_order] for d in defense_order]


def defense_names(records: list[RunRecord]) -> list[str]:
    seen = []
    for r in records:
        if r.defense not in seen:
            seen.append(r.defense)
    return seen


def category_names(records: list[RunRecord]) -> list[str]:
    seen = []
    for r in records:
        if r.attack_category not in seen:
            seen.append(r.attack_category)
    return seen
