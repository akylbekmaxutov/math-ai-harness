"""`python3 -m harness.show` — print a stored run. No API call, no cost.

    python3 -m harness.show --problem aime2026_08 --model gpt-5.6-terra --reasoning high

Reads the record that `harness.run` already wrote and prints it in exactly the
same format, by calling the same `summarise()`. Useful for looking at a result
again without paying for it twice, and it is how the transcript on the workshop
page is captured — from the real study, rather than from a rehearsal.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import models, problems, storage  # noqa: E402
from harness.reasoning import ReasoningMode  # noqa: E402
from harness.run import summarise  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="harness.show", description=__doc__.splitlines()[0])
    ap.add_argument("--problem", required=True,
                    help=f"one of: {', '.join(problems.load_problems())}")
    ap.add_argument("--model", required=True, help=f"one of: {', '.join(models.MODELS)}")
    ap.add_argument("--reasoning", required=True, choices=[m.value for m in ReasoningMode])
    a = ap.parse_args(argv)

    path = storage.solver_path(a.problem, a.model, a.reasoning)
    if not path.exists():
        print(f"\n  no stored run at {path.relative_to(storage.ROOT)}")
        print("  run it first:  python3 -m harness.run --problem "
              f"{a.problem} --model {a.model} --reasoning {a.reasoning}\n")
        return 1
    print()
    summarise(storage.read_record(path), path.relative_to(storage.ROOT))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
