"""Cost. Reported per SUCCESSFUL solve, not per run.

Cost per run rewards an agent that fails cheaply. Cost per successful solve is
the number that tells you what the capability actually costs to obtain.
"""
from __future__ import annotations

from collections import defaultdict


def summarise(rollouts, outcomes: dict[tuple, str]) -> dict:
    by_cfg = defaultdict(lambda: {"usd": 0.0, "n": 0, "correct": 0, "tokens_in": 0,
                                  "tokens_out": 0, "wall_s": 0.0})
    for r in rollouts:
        d = by_cfg[r.solver_config]
        d["usd"] += float(r.usage.get("usd", 0.0))
        d["n"] += 1
        d["tokens_in"] += int(r.usage.get("tokens_in", 0))
        d["tokens_out"] += int(r.usage.get("tokens_out", 0))
        d["wall_s"] += float(r.usage.get("wall_s", 0.0))
        d["correct"] += int(outcomes.get((r.solver_config, r.task_id, r.run_idx)) == "correct")

    out = {}
    for cfg, d in sorted(by_cfg.items()):
        out[cfg] = {
            **d,
            "usd_per_run": d["usd"] / d["n"] if d["n"] else 0.0,
            "usd_per_successful_solve": (d["usd"] / d["correct"]) if d["correct"] else float("inf"),
        }
    return out
