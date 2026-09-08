"""Replay stored traces through the live renderer.

Indistinguishable from the live run except for speed, which is the point:
beats 1 and 2 have a fallback that does not look like a fallback.
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.trace import read_trace
from display import live


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay a stored trace file.")
    ap.add_argument("--trace", required=True, help="path to traces/<config>/<task>.jsonl")
    ap.add_argument("--speed", type=float, default=1.0, help="playback multiplier")
    ap.add_argument("--outcomes", default="", help="optional graded outcomes json from grade.py")
    a = ap.parse_args()

    header, rollouts = read_trace(Path(a.trace))
    if not rollouts:
        print(f"no rollouts in {a.trace}", file=sys.stderr)
        return 1

    graded = {}
    if a.outcomes:
        import json
        graded = {tuple(k.split("|")): v
                  for k, v in json.loads(Path(a.outcomes).read_text())["outcomes"].items()}

    live.banner(header)
    counts, usd = Counter(), 0.0
    for r in sorted(rollouts, key=lambda x: x.run_idx):
        o = graded.get((r.solver_config, r.task_id, str(r.run_idx)), r.outcome)
        wall = float(r.usage.get("wall_s", 0.4))
        if a.speed > 0:
            time.sleep(min(wall / a.speed, 1.5))
        live.row(r, o)
        counts[o] += 1
        usd += float(r.usage.get("usd", 0.0))
    live.footer(dict(counts), usd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
