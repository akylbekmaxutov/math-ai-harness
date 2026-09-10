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
    ap.add_argument("--retry-failed", action="store_true",
                    help="re-run ONLY cells whose stored status is an error")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and stop")
    ap.add_argument("--max-tokens", type=int, default=None,
                    help="override the solver output cap (default 16384)")
    ap.add_argument("--problem", action="append", help="restrict to these problem ids")
    ap.add_argument("--model", action="append", help="restrict to these models")
    a = ap.parse_args(argv)

    env.load_dotenv()          # keys come from .env, never from a flag
    env.canonicalise()

    # A simulated run must never destroy a real one. Rehearsing with --mock over
    # a corpus that contains real measurements silently replaces paid-for results
    # with invented ones, and a study still running alongside it then SKIPS those
    # cells because the files now exist. That happened once; it does not need to
    # be possible.
    if a.mock and not a.force:
        real = [p for p in storage.SOLVER_DIR.rglob("*.json")
                if not storage.read_record(p).get("simulated", False)]
        if real:
            print(f"\n  REFUSING: {len(real)} REAL result file(s) are already in "
                  f"{storage.SOLVER_DIR.relative_to(storage.ROOT)}/.")
            print("  A --mock run would overwrite measurements with simulated data.")
            print("  Move them aside first, or pass --force if you really mean it:")
            for p in real[:5]:
                print(f"      {p.relative_to(storage.ROOT)}")
            if len(real) > 5:
                print(f"      ... and {len(real) - 5} more")
            print()
            return 1

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
            # Resumption skips by existence, so without this a cell that failed
            # stays failed forever: re-running the command steps straight over
            # it. --retry-failed re-runs exactly the broken ones.
            stored = None
            if a.retry_failed:
                try:
                    stored = storage.read_record(path).get("status")
                except (OSError, ValueError):
                    stored = "error"
            if not a.retry_failed or stored != "error":
                counts["skipped"] += 1
                print(f"  skip  {pid:14s} {mkey:17s} {mode:7s} (exists)")
                continue
        cfg = ExperimentConfig(model_key=mkey, reasoning_mode=ReasoningMode.parse(mode),
                               mock=a.mock,
                               **({"max_output_tokens": a.max_tokens} if a.max_tokens else {}))
        rec, _ = run_and_store(probs[pid], cfg)
        counts[rec["status"]] = counts.get(rec["status"], 0) + 1
        mark = {"ok": "OK ", "unsupported": "-- ", "error": "ERR",
                "truncated": "CAP", "no_answer_marked": "?? "}.get(rec["status"], "?? ")
        extra = ""
        if rec["status"] in ("ok", "no_answer_marked", "truncated"):
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
