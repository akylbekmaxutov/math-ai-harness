"""`python3 -m harness.run` — one cell of the experiment matrix.

    python3 -m harness.run --problem aime2026_08 --model gpt-5.6-terra --reasoning high

The smallest unit the study is made of. Run it alone to demonstrate one
execution live; `harness.run_all` is a loop over exactly this.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import env, models, problems, storage  # noqa: E402
from harness.reasoning import ReasoningMode  # noqa: E402
from harness.runner import ExperimentConfig, run_and_store  # noqa: E402


def summarise(record: dict, path) -> None:
    """The one-screen report the workshop reads out loud."""
    s, r = record["solver"], record.get("usage") or {}
    print(f"  problem   {record['problem']['problem_id']}  ({record['problem']['title']})")
    print(f"  model     {s['display']}  [{s['provider']}/{s['model']}]")
    print(f"  reasoning {s['reasoning_mode']}   requested: {s['reasoning_request'] or '—'}")
    print(f"  status    {record['status']}")
    if record["status"] in ("ok", "no_answer_marked", "truncated"):
        exp = record["problem"]["expected_answer"]
        mark = "CORRECT" if record["correct"] else "INCORRECT"
        print(f"  answer    {record['response']['final_answer']}   expected {exp}   -> {mark}")
        print(f"  reasoning info exposed: {record['response']['reasoning_exposure']}")
        rt = r.get("reasoning_tokens")
        print(f"  tokens    in {r['input_tokens']}  out {r['output_tokens']}  "
              f"reasoning {'n/a' if rt is None else rt}  total {r['total_tokens']}")
        print(f"  latency   {record['timing']['latency_seconds']}s")
        print(f"  cost      ${record['cost']['estimated_usd']:.6f}  "
              f"(prices {record['cost']['pricing_version']})")
    else:
        print(f"  error     {record['error']['message']}")
    if record["simulated"]:
        print("  SIMULATED — offline simulator output. NOT a measurement of a real model.")
    print(f"  stored    {path}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="harness.run", description=__doc__.splitlines()[0])
    ap.add_argument("--problem", required=True,
                    help=f"one of: {', '.join(problems.load_problems())}")
    ap.add_argument("--model", required=True, help=f"one of: {', '.join(models.MODELS)}")
    ap.add_argument("--reasoning", required=True, choices=[m.value for m in ReasoningMode])
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--mock", action="store_true",
                    help="offline simulator: no keys, no network, marked simulated")
    a = ap.parse_args(argv)

    env.load_dotenv()          # keys come from .env, never from a flag
    env.canonicalise()

    problem = problems.get(a.problem)
    cfg = ExperimentConfig(model_key=a.model,
                           reasoning_mode=ReasoningMode.parse(a.reasoning),
                           max_output_tokens=a.max_tokens, mock=a.mock)
    record, path = run_and_store(problem, cfg)
    print()
    summarise(record, path.relative_to(storage.ROOT))
    print()
    return 0 if record["status"] in ("ok", "unsupported", "no_answer_marked", "truncated") else 1


if __name__ == "__main__":
    raise SystemExit(main())
