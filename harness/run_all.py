"""`python3 -m harness.run_all` — the whole solver matrix.

    3 problems  x  3 models  x  3 reasoning modes  =  27 cells

Two of which do not exist: Grok exposes no medium effort, so those cells are
written with `status: "unsupported"` and no call is made. 25 API calls, 27
files. The grid on the website is drawn from those files, holes included.

Resumable by default: a cell whose file already exists is skipped, so a study
interrupted by a rate limit is finished by re-running the same command. Pass
`--force` to re-run everything.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import env, models, problems, storage  # noqa: E402
from harness.reasoning import ReasoningMode  # noqa: E402
from harness.runner import ExperimentConfig, run_and_store  # noqa: E402


def plan(problem_ids, model_keys, modes):
    """Every cell of the matrix, in a stable order. Computed before anything
    runs, so `--dry-run` prints exactly what a real run would do."""
    return [(p, m, r) for p in problem_ids for m in model_keys for r in modes]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="harness.run_all", description=__doc__.splitlines()[0])
    ap.add_argument("--mock", action="store_true", help="offline simulator")
    ap.add_argument("--force", action="store_true", help="re-run cells that already exist")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and stop")
    ap.add_argument("--problem", action="append", help="restrict to these problem ids")
    ap.add_argument("--model", action="append", help="restrict to these models")
    a = ap.parse_args(argv)

    env.load_dotenv()          # keys come from .env, never from a flag
    env.canonicalise()

    probs = problems.load_problems()
    pids = a.problem or list(probs)
    mkeys = a.model or list(models.SOLVERS)
    modes = [m.value for m in ReasoningMode]
    cells = plan(pids, mkeys, modes)

    print(f"\nSolver matrix: {len(pids)} problems x {len(mkeys)} models x "
          f"{len(modes)} modes = {len(cells)} cells")
    live = sum(1 for _, m, r in cells
               if ReasoningMode.parse(r) in models.supported_modes(m))
    print(f"  {live} will call an API, {len(cells) - live} are unsupported cells")
    if a.mock:
        print("  --mock: offline simulator. Nothing here is a measurement.")
    if a.dry_run:
        for p, m, r in cells:
            ok = ReasoningMode.parse(r) in models.supported_modes(m)
            print(f"    {p:14s} {m:17s} {r:7s} {'call' if ok else 'UNSUPPORTED'}")
        return 0

    counts = {"ok": 0, "unsupported": 0, "error": 0, "skipped": 0, "no_answer_marked": 0}
    for pid, mkey, mode in cells:
        path = storage.solver_path(pid, mkey, mode)
        if path.exists() and not a.force:
            counts["skipped"] += 1
            print(f"  skip  {pid:14s} {mkey:17s} {mode:7s} (exists)")
            continue
        cfg = ExperimentConfig(model_key=mkey, reasoning_mode=ReasoningMode.parse(mode),
                               mock=a.mock)
        rec, _ = run_and_store(probs[pid], cfg)
        counts[rec["status"]] = counts.get(rec["status"], 0) + 1
        mark = {"ok": "OK ", "unsupported": "-- ", "error": "ERR",
                "no_answer_marked": "?? "}.get(rec["status"], "?? ")
        extra = ""
        if rec["status"] in ("ok", "no_answer_marked"):
            extra = (f" {'correct' if rec['correct'] else 'wrong  '}"
                     f" {rec['usage']['total_tokens']:>6} tok"
                     f" {rec['timing']['latency_seconds']:>6.2f}s"
                     f" ${rec['cost']['estimated_usd']:.5f}")
        print(f"  {mark}  {pid:14s} {mkey:17s} {mode:7s}{extra}")

    print("\n  " + "  ".join(f"{k}={v}" for k, v in counts.items() if v))
    print(f"  results in {storage.SOLVER_DIR.relative_to(storage.ROOT)}/")
    print("  next: python3 -m judges.run_all" + (" --mock" if a.mock else "") + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
