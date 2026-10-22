"""Command-line interface.

    python -m aegis.cli run
    python -m aegis.cli run --defenses none,tool-policy,full --out results
    python -m aegis.cli list
    python -m aegis.cli run --target openai   # requires AEGIS_OPENAI_API_KEY
"""
from __future__ import annotations

import argparse
import os
import sys

from . import adaptive, guard, report
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


def _tail(path: str):
    """Follow a JSONL file, like tail -f. This is what a guard does on a live
    host: it never returns."""
    import json
    import time

    from .guard import Event
    with open(path, "r", encoding="utf-8") as fh:
        while True:
            line = fh.readline()
            if not line:
                time.sleep(0.2)
                continue
            if line.strip():
                yield Event.from_dict(json.loads(line))


def _read_log(path: str):
    """Read a finite event log to EOF (used by shadow mode)."""
    import json

    from .guard import Event
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield Event.from_dict(json.loads(line))


def _run_guard(args) -> int:
    import json

    from .guard import Autonomy, Event, Guard, GuardConfig, live_stream

    # -- network mode: serve the guard over HTTP -------------------------
    if args.serve:
        from .guard.server import GuardServer
        g = Guard(GuardConfig(autonomy=Autonomy(args.autonomy), incidents_path=args.incidents))
        srv = GuardServer(g, host=args.host, port=args.port, token=args.token)
        print(f"AEGIS guard listening on http://{srv.host}:{srv.port} | autonomy={args.autonomy}")
        print("  POST /event   GET /health   GET /metrics   GET /incidents")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\n  [guard] stand-down requested - disengaging")
        finally:
            srv.shutdown()
        print("  final:", g.summary())
        return 0

    # -- pick the event source -------------------------------------------
    if args.simulate or not args.watch:
        events = live_stream(include_adaptive=args.adaptive)
        source = "built-in live stream"
    elif args.watch == "-":
        events = (Event.from_dict(json.loads(line)) for line in sys.stdin if line.strip())
        source = "stdin"
    else:
        events = _read_log(args.watch) if args.shadow else _tail(args.watch)
        source = args.watch

    # -- shadow mode: report what it would have done ----------------------
    if args.shadow:
        from .guard.shadow import markdown, run_shadow, write_report
        report_ = run_shadow(events)
        write_report(report_, args.shadow_out)
        print(markdown(report_))
        print(f"\nWrote {args.shadow_out}")
        return 0

    # -- live enforcement -------------------------------------------------
    cfg = GuardConfig(autonomy=Autonomy(args.autonomy), incidents_path=args.incidents)
    g = Guard(cfg)
    print(f"AEGIS guard - {source} | autonomy={args.autonomy} | incidents -> {args.incidents}")
    summary = g.run(events, max_events=args.max_events, quiet=args.quiet)
    print("\n--- guard summary ---")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    return 0


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

    g = sub.add_parser("guard", help="run the always-on defensive guard")
    g.add_argument("--simulate", action="store_true",
                   help="run over a built-in live attack stream")
    g.add_argument("--watch", default=None,
                   help="watch a JSONL event file, or '-' for stdin")
    g.add_argument("--adaptive", action="store_true",
                   help="include adaptive mutations in the simulated stream")
    g.add_argument("--autonomy", default="enforce",
                   choices=["observe", "recommend", "enforce"])
    g.add_argument("--max-events", type=int, default=None)
    g.add_argument("--incidents", default="results/incidents.jsonl")
    g.add_argument("--quiet", action="store_true")
    g.add_argument("--shadow", action="store_true",
                   help="report what the guard would have blocked, without acting")
    g.add_argument("--shadow-out", default="results/shadow-report.md")
    g.add_argument("--serve", action="store_true",
                   help="serve the guard over HTTP for an inline agent to call")
    g.add_argument("--host", default="127.0.0.1")
    g.add_argument("--port", type=int, default=8765)
    g.add_argument("--token", default=None,
                   help="shared secret required in the X-AEGIS-Token header")

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

    if args.cmd == "guard":
        return _run_guard(args)


    defenses = [d.strip() for d in args.defenses.split(",") if d.strip()]
    attacks = _select_attacks(args.attacks)
    records = run_suite(attacks, defenses, agent_factory=_agent_factory(args.target))
    info = report.write_results(records, args.out)

    print(report.markdown_report(records))
    print(f"\nWrote {info['markdown']} and {info['json']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
