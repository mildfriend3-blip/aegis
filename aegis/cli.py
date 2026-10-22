"""Command-line interface.

    python -m aegis.cli run
    python -m aegis.cli run --defenses none,tool-policy,full --out results
    python -m aegis.cli list
    python -m aegis.cli run --target openai   # requires AEGIS_OPENAI_API_KEY
"""
from __future__ import annotations

import argparse
import sys

from . import adaptive, report
from .attacks import ATTACKS
from .defenses import DEFENSE_CONFIGS
from .harness import run_suite
from .targets import MockAgent


def _agent_factory(target: str):
    if target == "mock":
        return MockAgent
    if target == "openai":
        from .targets.openai_agent import OpenAIAgent
        return OpenAIAgent
    raise SystemExit(f"unknown target '{target}'")


def _select_attacks(spec: str):
    if spec in ("all", ""):
        return ATTACKS
    wanted = {s.strip() for s in spec.split(",") if s.strip()}
    chosen = [a for a in ATTACKS if a.id in wanted or a.category in wanted]
    if not chosen:
        raise SystemExit(f"no attacks matched '{spec}'")
    return chosen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aegis", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="run the benchmark")
    run.add_argument("--defenses", default=",".join(DEFENSE_CONFIGS),
                     help="comma-separated defense configs")
    run.add_argument("--attacks", default="all",
                     help="'all', or comma-separated attack ids/categories")
    run.add_argument("--target", default="mock", choices=["mock", "openai"])
    run.add_argument("--out", default="results", help="output directory")

    sub.add_parser("list", help="list attacks and defense configs")

    ad = sub.add_parser("adaptive", help="run the adaptive attacker (searches for bypasses)")
    ad.add_argument("--defenses", default="none,full,hardened",
                    help="comma-separated defense configs")
    ad.add_argument("--attacks", default="all",
                    help="'all', or comma-separated attack ids/categories")
    ad.add_argument("--out", default="results", help="output directory")

    args = parser.parse_args(argv)

    if args.cmd == "list":
        print("Defense configs:", ", ".join(DEFENSE_CONFIGS))
        print("\nAttacks:")
        for a in ATTACKS:
            print(f"  {a.id:22s} [{a.category:14s}] -> {a.objective}")
        return 0

    if args.cmd == "adaptive":
        defenses = [d.strip() for d in args.defenses.split(",") if d.strip()]
        attacks = _select_attacks(args.attacks)
        recs = adaptive.run_adaptive(attacks, defenses)
        info = adaptive.write_results(recs, args.out)
        print(adaptive.markdown(recs))
        print(f"\nWrote {info['markdown']} and {info['json']}")
        return 0

    defenses = [d.strip() for d in args.defenses.split(",") if d.strip()]
    attacks = _select_attacks(args.attacks)
    records = run_suite(attacks, defenses, agent_factory=_agent_factory(args.target))
    info = report.write_results(records, args.out)

    print(report.markdown_report(records))
    print(f"\nWrote {info['markdown']} and {info['json']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
