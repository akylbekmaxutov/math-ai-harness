"""The calibration labelling helper.

Presents the SAME blinded input a judge receives, on the SAME four anchors,
with the SAME span requirement, and records the label. Forty of these is what
converts every process number in the workshop from an assertion into a
calibrated result.

Say what it is on stage: single-annotator calibration, not an annotation study.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.trace import VERDICTS, iter_all
from tasks.math.loader import load_tasks
from verifiers.process_judge import ANCHORS, render

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "calibration" / "human_labels.jsonl"


def stratified(rollouts, outcomes, n: int, seed: int = 20260907):
    """Stratified across the three solver configs AND across correct/incorrect,
    so the calibration set cannot be accidentally all-easy."""
    strata = defaultdict(list)
    for r in rollouts:
        o = outcomes.get((r.solver_config, r.task_id, r.run_idx))
        if o in ("correct", "incorrect"):
            strata[(r.solver_config, o)].append(r)
    rng = random.Random(seed)
    for v in strata.values():
        rng.shuffle(v)
    picked, i = [], 0
    keys = sorted(strata)
    while len(picked) < n and any(strata[k] for k in keys):
        k = keys[i % len(keys)]
        if strata[k]:
            picked.append(strata[k].pop())
        i += 1
    return picked


def main() -> int:
    ap = argparse.ArgumentParser(description="Label traces for judge calibration.")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--show-only", action="store_true", help="print one sample and exit")
    a = ap.parse_args()

    op = VERDICTS / "outcomes.json"
    if not op.exists():
        print("run scripts/grade.py first", file=sys.stderr)
        return 1
    graded = json.loads(op.read_text())["outcomes"]
    outcomes = {tuple(k.split("|")[:2] + [int(k.split("|")[2])]): v for k, v in graded.items()}

    tasks = {t.task_id: t for t in load_tasks()}
    rollouts = [r for _, r in iter_all() if r.outcome == "submitted"]

    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            if line.strip():
                d = json.loads(line)
                done.add((d["solver_config"], d["task_id"], int(d["run_idx"])))

    sample = [r for r in stratified(rollouts, outcomes, a.n) if r.key not in done]
    if not sample:
        print(f"{len(done)} labels already recorded in {OUT}. Nothing left to do.")
        return 0

    print(f"\n{len(done)} labelled so far · {len(sample)} to go · Ctrl-C to stop "
          f"(progress is saved after each)\n")
    OUT.parent.mkdir(exist_ok=True)

    for n, r in enumerate(sample, 1):
        prompt, _ = render(r, tasks[r.task_id], blinded=True)
        print("=" * 76)
        print(f"  {n}/{len(sample)}")
        print("=" * 76)
        print(prompt.split("TASK:")[0])
        print("-" * 76)
        for i, anc in enumerate(ANCHORS, 1):
            print(f"  {i}) {anc}")
        if a.show_only:
            return 0
        try:
            choice = input("\nverdict [1-4]: ").strip()
            label = ANCHORS[int(choice) - 1]
            span = input("quoted span (required): ").strip()
            while not span:
                span = input("a verdict without a span is rejected. span: ").strip()
            just = input("one-line justification: ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\nstopped. {n - 1} new labels saved to {OUT}")
            return 0
        except (ValueError, IndexError):
            print("  skipped (unparseable choice)")
            continue

        with OUT.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "solver_config": r.solver_config, "task_id": r.task_id,
                "run_idx": r.run_idx, "label": label, "span": span,
                "justification": just, "annotator": "instructor",
            }) + "\n")
        print(f"  recorded {label}\n")

    print(f"done. labels in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
