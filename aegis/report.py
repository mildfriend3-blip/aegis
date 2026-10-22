"""Render benchmark results as Markdown (and a raw JSON sidecar)."""
from __future__ import annotations

import json

from . import metrics
from .types import RunRecord

_PCT = lambda x: f"{x*100:5.1f}%"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def markdown_report(records: list[RunRecord], title: str = "AEGIS Benchmark Report") -> str:
    defs = metrics.defense_names(records)
    cats = metrics.category_names(records)
    per_def = metrics.by_defense(records)

    lines = [f"# {title}", ""]
    lines += [f"Attacks evaluated: **{len(records)//max(len(defs),1)}** per defense "
              f"across **{len(defs)}** defense configurations "
              f"(**{len(records)}** total runs).", ""]

    lines += ["## 1. Overall: attack success vs. legitimate utility", ""]
    rows = [[d, _PCT(per_def[d]["asr"]), _PCT(per_def[d]["utility"])] for d in defs]
    lines += [_table(["Defense", "Attack Success Rate (lower=better)",
                      "Utility (higher=better)"], rows), ""]

    lines += ["## 2. Attack Success Rate by defense x attack category", ""]
    mat = metrics.matrix(records, defs, cats)
    rows = [[d] + [_PCT(v) for v in row] for d, row in zip(defs, mat)]
    lines += [_table(["Defense", *cats], rows), ""]

    lines += ["## 3. Per-attack outcome: undefended vs. full stack", ""]
    by_key = {(r.defense, r.attack_id): r for r in records}
    attack_ids = list(dict.fromkeys(r.attack_id for r in records))
    rows = []
    for aid in attack_ids:
        base = by_key.get(("none", aid))
        full = by_key.get(("full", aid))
        if base is None:
            continue
        cat = base.attack_category
        rows.append([aid, cat,
                     "SUCCESS" if base.success else "blocked",
                     "SUCCESS" if (full and full.success) else "blocked"])
    lines += [_table(["Attack", "Category", "Undefended", "Full stack"], rows), ""]

    return "\n".join(lines)


def write_results(records: list[RunRecord], outdir: str,
                  title: str = "AEGIS Benchmark Report") -> dict:
    import os
    os.makedirs(outdir, exist_ok=True)
    md_path = os.path.join(outdir, "report.md")
    json_path = os.path.join(outdir, "results.json")
    with open(md_path, "w") as fh:
        fh.write(markdown_report(records, title))
    with open(json_path, "w") as fh:
        json.dump([r.__dict__ for r in records], fh, indent=2)
    return {"markdown": md_path, "json": json_path,
            "summary": metrics.by_defense(records)}
