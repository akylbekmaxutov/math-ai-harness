"""Execute rollouts. The ONLY entry point that calls a solver.

Everything this produces is a trace. Nothing here grades anything — see
scripts/grade.py, whose separate existence is the structural proof that the
architecture is trace-first.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dataclasses

from core.config import Registry, load_dotenv, validate_env
from core.trace import TRACES
from display import live
from runner.rollouts import run_batch
from tasks.math.loader import answer_key, load_tasks


def main() -> int:
    ap = argparse.ArgumentParser(description="Run rollouts and record traces.")
    ap.add_argument("--config", default="S1", choices=["S1", "S2", "S3", "all"])
    ap.add_argument("--task", default=None, help="task_id, e.g. aime2026-07")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--usd-budget", type=float, default=None,
                    help="override the per-rollout spend cap (M4 demo: set it low)")
    ap.add_argument("--max-turns", type=int, default=None)
    ap.add_argument("--effort", default=None, choices=["none", "low", "medium", "high"],
                    help="override reasoning effort; it is part of the config hash")
    ap.add_argument("--sweep-effort", action="store_true",
                    help="run every effort level in turn — the reasoning-effort study")
    ap.add_argument("--mock", action="store_true",
                    help="offline simulator: no keys, no network, traces marked simulated")
    ap.add_argument("--no-resume", action="store_true")
    a = ap.parse_args()

    load_dotenv()
    reg = Registry.load()
    configs = ["S1", "S2", "S3"] if a.config == "all" else [a.config]

    if not a.mock:
        validate_env(sorted({reg.models[reg.rotation["configs"][c]["solver"]].provider
                             for c in configs}))

    tasks = load_tasks()
    if a.task:
        tasks = [t for t in tasks if t.task_id == a.task]
        if not tasks:
            print(f"no such task: {a.task}", file=sys.stderr)
            return 2
    answers = answer_key() if a.mock else None

    from core.config import EFFORTS
    efforts = list(EFFORTS) if a.sweep_effort else [a.effort]

    total = Counter()
    usd = 0.0
    for cfg_name in configs:
      for effort in efforts:
        cfg = reg.solver(cfg_name, mock=a.mock, effort=effort)
        if a.usd_budget is not None:
            cfg = dataclasses.replace(cfg, usd_budget=a.usd_budget)
        if a.max_turns is not None:
            cfg = dataclasses.replace(cfg, max_turns=a.max_turns)

        header = dict(cfg.header())
        header["simulated"] = a.mock
        live.banner(header)

        counts = Counter()
        res, skipped = run_batch(tasks, cfg, a.n, mock=a.mock, answers=answers,
                                 concurrency=a.concurrency, resume=not a.no_resume)
        for r in sorted(res, key=lambda x: (x.task_id, x.run_idx)):
            live.row(r)
            counts[r.outcome] += 1
            usd += float(r.usage.get("usd", 0.0))
        if skipped:
            print(f"  \033[2m{skipped} rollout(s) already on disk — resumed, not re-run\033[0m")
        live.footer(dict(counts), sum(float(r.usage.get("usd", 0.0)) for r in res))
        total.update(counts)

    print(f"traces -> {TRACES}")
    print("execution states (NOT grades — run scripts/grade.py):", dict(total))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
