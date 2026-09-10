"""`python3 -m judges.run_all` — every candidate solution, judged twice, at two
judge efforts.

The rotation is one rule: **a model never judges its own family.** For each
candidate run the other two models are the judges, so no model can prefer its
own output because no model is ever shown its own output. That is a design that
EXCLUDES self-preference rather than one that measures it and hopes it is small.

Judge efforts default to low and high. Those are the two levels all three
providers expose, which makes the judge sweep a clean 2x2 across every judge —
the medium hole in the solver grid would otherwise reappear here and make the
comparison uneven.

    24 candidate runs  x  2 judges  x  2 judge efforts  =  96 verdicts
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import env, models, storage  # noqa: E402
from harness.reasoning import ReasoningMode  # noqa: E402
from judges.judge import JudgeConfig, judge_and_store  # noqa: E402

DEFAULT_JUDGE_MODES = ("low", "high")


def judges_for(candidate_model_key: str) -> list[str]:
    """The other two models. Never the candidate's own family."""
    own = models.get(candidate_model_key).family
    return [k for k in models.SOLVERS if models.get(k).family != own]


def candidates() -> list[dict]:
    """Stored solver runs that produced something a judge could read.

    An unsupported cell has no solution in it, so there is nothing to judge —
    it is skipped here and shown as a hole on the website, not as a zero.
    """
    return [r for r in storage.load_solver_runs()
            if r.get("status") in ("ok", "no_answer_marked", "truncated") and (r.get("response") or {}).get("text")]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="judges.run_all", description=__doc__.splitlines()[0])
    ap.add_argument("--mock", action="store_true", help="offline simulator")
    ap.add_argument("--force", action="store_true", help="re-judge verdicts that already exist")
    ap.add_argument("--retry-failed", action="store_true",
                    help="re-run ONLY verdicts whose stored status is not ok")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-tokens", type=int, default=None,
                    help="override the judge output cap (default 8192)")
    ap.add_argument("--judge-mode", action="append", choices=[m.value for m in ReasoningMode],
                    help=f"repeatable; default {' '.join(DEFAULT_JUDGE_MODES)}")
    a = ap.parse_args(argv)

    env.load_dotenv()          # keys come from .env, never from a flag
    env.canonicalise()

    # Same guard as the solver: a rehearsal must not overwrite paid-for verdicts.
    if a.mock and not a.force:
        real = [p for p in storage.JUDGE_DIR.rglob("*.json")
                if not storage.read_record(p).get("simulated", False)]
        if real:
            print(f"\n  REFUSING: {len(real)} REAL verdict file(s) already exist in "
                  f"{storage.JUDGE_DIR.relative_to(storage.ROOT)}/.")
            print("  Move them aside first, or pass --force if you really mean it.\n")
            return 1

    jmodes = a.judge_mode or list(DEFAULT_JUDGE_MODES)
    cands = candidates()
    if not cands:
        print("\nNo judgeable solver runs found. Run `python3 -m harness.run_all` first.\n")
        return 1

    total = len(cands) * 2 * len(jmodes)
    print(f"\nJudging: {len(cands)} candidate runs x 2 judges x {len(jmodes)} judge efforts "
          f"= {total} verdicts")
    if a.mock:
        print("  --mock: offline simulator. Nothing here is a measurement.")
    if a.dry_run:
        for c in cands:
            s = c["solver"]
            print(f"    {c['problem']['problem_id']:14s} {s['model_key']:17s} {s['reasoning_mode']:7s}"
                  f"  judged by {', '.join(judges_for(s['model_key']))}")
        return 0

    counts = Counter()
    for c in cands:
        s = c["solver"]
        for jkey in judges_for(s["model_key"]):
            for jmode in jmodes:
                path = storage.judge_path(c["problem"]["problem_id"], s["model_key"],
                                          s["reasoning_mode"], jkey, jmode)
                if path.exists() and not a.force:
                    # --retry-failed re-runs the broken cells and nothing else,
                    # so fixing six truncated verdicts costs six calls.
                    stored_ok = True
                    if a.retry_failed:
                        try:
                            stored_ok = storage.read_record(path).get("status") == "ok"
                        except (OSError, ValueError):
                            stored_ok = False
                    if stored_ok:
                        counts["skipped"] += 1
                        continue
                cfg = JudgeConfig(judge_key=jkey, reasoning_mode=ReasoningMode.parse(jmode),
                                  mock=a.mock,
                                  **({"max_output_tokens": a.max_tokens} if a.max_tokens else {}))
                rec, _ = judge_and_store(c, cfg)
                counts[rec["status"]] += 1
                detail = ""
                if rec["status"] == "ok":
                    detail = (f" verdict={rec['verdict']:4s} mean={rec['mean_score']:.1f}"
                              f" reasoning={rec['scores']['reasoning']}"
                              f" ${rec['cost']['estimated_usd']:.5f}")
                elif rec["error"]:
                    detail = f" {rec['error']['message'][:60]}"
                print(f"  {rec['status']:13s} {c['problem']['problem_id']:14s} "
                      f"{s['model_key']:17s}{s['reasoning_mode']:7s} <- {jkey:17s}{jmode:5s}{detail}")

    print("\n  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(f"  verdicts in {storage.JUDGE_DIR.relative_to(storage.ROOT)}/")
    print("  next: python3 -m analysis.build_results\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
