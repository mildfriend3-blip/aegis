"""Render docs/results-table.png from a live benchmark run.

Regenerate with:  python docs/make_results_image.py
(requires matplotlib; not needed to use AEGIS itself)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from aegis.attacks import ATTACKS  # noqa: E402
from aegis.defenses import DEFENSE_CONFIGS  # noqa: E402
from aegis.harness import run_suite  # noqa: E402
from aegis.metrics import by_defense  # noqa: E402

NAVY = "#1F3A5F"
ACCENT = "#2E5A88"
DISPLAY = {
    "none": "none", "sanitizer": "sanitizer", "datamarking": "datamarking",
    "tool-policy": "tool-policy", "output-filter": "output-filter",
    "sanitizer+tool-policy": "sanitizer + tool-policy",
    "datamarking+tool-policy": "datamarking + tool-policy",
    "full": "full stack",
}


def tint(v: float):
    """Light green (0.0) -> light red (1.0), readable behind dark text."""
    r0, g0, b0 = (0.84, 0.93, 0.86)
    r1, g1, b1 = (0.98, 0.83, 0.81)
    return (r0 + (r1 - r0) * v, g0 + (g1 - g0) * v, b0 + (b1 - b0) * v)


def main() -> None:
    stats = by_defense(run_suite(ATTACKS, list(DEFENSE_CONFIGS)))
    rows = [(d, stats[d]["asr"], stats[d]["utility"]) for d in DEFENSE_CONFIGS]

    fig, ax = plt.subplots(figsize=(9.6, 5.0), dpi=200)
    ax.axis("off")
    ax.set_title("AEGIS  -  Attack Success Rate by defence", fontsize=15,
                 fontweight="bold", color=NAVY, pad=16)

    col_labels = ["Defence", "Attack Success Rate\n(lower is better)",
                  "Utility\n(higher is better)"]
    cell_text, cell_cols = [], []
    for d, a, u in rows:
        cell_text.append([DISPLAY.get(d, d), f"{a * 100:.1f}%", f"{u * 100:.1f}%"])
        cell_cols.append(["#FFFFFF", tint(a), "#EAF1E6"])

    tbl = ax.table(cellText=cell_text, colLabels=col_labels,
                   cellColours=cell_cols, colColours=[ACCENT] * 3,
                   loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(11)
    tbl.scale(1, 1.65)

    for (row, col), cell in tbl.get_celld().items():
        cell.set_edgecolor("#C9D3E0")
        cell.set_linewidth(0.6)
        if row == 0:
            cell.set_text_props(color="white", fontweight="bold", fontsize=10.5)
        else:
            cell.set_text_props(color="#1A1A1A")

    full_row = list(DEFENSE_CONFIGS).index("full") + 1
    for col in range(3):
        tbl[(full_row, col)].set_text_props(color="#1A1A1A", fontweight="bold")

    fig.text(0.5, 0.04,
             "17 attacks across 9 categories x 8 defence configurations.  "
             "Utility = the legitimate task is still achievable.",
             ha="center", fontsize=9, color="#555555")

    fig.savefig("docs/results-table.png", bbox_inches="tight", facecolor="white")
    print("wrote docs/results-table.png")


if __name__ == "__main__":
    main()
