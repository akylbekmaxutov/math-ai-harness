"""`python3 -m harness.sync_problems` — fetch the real problem set.

    python3 -m harness.sync_problems              # AIME 2026 I, problems 1, 8, 15
    python3 -m harness.sync_problems --indices 3,11,14

Writes problems/problems.json from MathArena/aime_2026. The problem text and the
answers come from the dataset and are never retyped here, because a competition
problem transcribed by hand is a different problem.

WHICH THREE, AND WHY: AIME orders its problems by intended difficulty, so taking
1, 8 and 15 of AIME 2026 I spans the contest's own difficulty curve — an opening
problem, a middle one, and the final one. It is a stated rule applied before
looking at any model's performance, which is what stops the selection being a
choice about which problems make the results look interesting.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.problems import PROBLEMS_FILE  # noqa: E402

DATASET = "MathArena/aime_2026"
DEFAULT_INDICES = (1, 8, 15)

#: AIME 2026 I is problems 1-15 of this dataset; II is 16-30.
CONTEST_OF = {True: "AIME 2026 I", False: "AIME 2026 II"}


def position_note(idx: int) -> str:
    within = idx if idx <= 15 else idx - 15
    contest = CONTEST_OF[idx <= 15]
    where = ("the opening problem" if within == 1 else
             "the final and hardest problem" if within == 15 else
             f"problem {within} of 15")
    return (f"{contest}, problem {within}. AIME orders its problems by intended "
            f"difficulty, so this is {where} of that contest.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="harness.sync_problems",
                                 description=__doc__.splitlines()[0])
    ap.add_argument("--indices", default=",".join(str(i) for i in DEFAULT_INDICES),
                    help=f"comma-separated problem_idx values (default {DEFAULT_INDICES})")
    ap.add_argument("--out", default=str(PROBLEMS_FILE))
    a = ap.parse_args(argv)
    want = [int(x) for x in a.indices.split(",") if x.strip()]

    try:
        from datasets import load_dataset
    except ImportError:
        print("\nThis command needs the `datasets` package:\n    pip install datasets\n")
        return 1

    print(f"\n  fetching {DATASET} ...")
    ds = load_dataset(DATASET, split="train")
    rows = {int(r["problem_idx"]): r for r in ds}
    missing = [i for i in want if i not in rows]
    if missing:
        print(f"  problem_idx {missing} not in the dataset (it has "
              f"{min(rows)}..{max(rows)})")
        return 1

    problems = []
    for i in want:
        r = rows[i]
        answer = str(r["answer"]).strip()
        if not (answer.isdigit() and 0 <= int(answer) <= 999):
            print(f"  problem {i}: answer {answer!r} is not an AIME integer 0-999")
            return 1
        problems.append({
            "problem_id": f"aime2026_{i:02d}",
            "title": f"AIME 2026 · Problem {i if i <= 15 else i - 15}"
                     f"{' (II)' if i > 15 else ''}",
            "kind": "AIME competition problem",
            "difficulty": position_note(i),
            "question": r["problem"],
            "expected_answer": answer,
            # AIME answers are integers 0-999, so there are no alternative
            # spellings to declare. The grader still normalises presentation.
            "answer_aliases": [answer],
            "answer_kind": "integer",
            "source": DATASET,
            "source_problem_idx": i,
            "why_this_problem": position_note(i),
        })

    payload = {
        "schema_version": "1.0",
        "problem_set_version": f"{DATASET}@{len(want)}:{'-'.join(map(str, want))}",
        "note": ("Fetched from MathArena, never retyped. Re-run "
                 "python3 -m harness.sync_problems to reproduce this file."),
        "dataset": {
            "name": "AIME 2026 (via MathArena)",
            "size": len(problems),
            "origin": DATASET,
            "public_benchmark": True,
            "homepage": "https://huggingface.co/datasets/MathArena/aime_2026",
            "licence": "CC BY-NC-SA 4.0 — cite MathArena when reporting results.",
            "summary": (
                "The American Invitational Mathematics Examination, 2026. Every answer is "
                "an integer from 0 to 999, which makes the deterministic check trivial and "
                "throws the entire question of solution quality onto Part II: a model can "
                "land on a three-digit integer for reasons that do not survive inspection."
            ),
            "selection_criteria": [
                "Taken from a real competition, not written for this workshop.",
                "Problems 1, 8 and 15 of AIME 2026 I — AIME orders by intended difficulty, "
                "so the three span the contest's own easy / middle / hard range.",
                "The rule was fixed before any model was run, so the selection is not a "
                "choice about which problems make the results look interesting.",
                "Answers are official contest answers, taken from the dataset verbatim.",
            ],
            "verification": (
                "The answers are the official AIME answers as published in the MathArena "
                "dataset. They are NOT independently re-derived here, and this workshop "
                "does not claim to have checked them — the sync command asserts only that "
                "each is an integer in 0-999, the form AIME guarantees."
            ),
            "answer_format": (
                "Every AIME answer is an integer from 0 to 999. The grader normalises "
                "presentation (LaTeX, $, thousands separators) and compares exactly."
            ),
            "contamination": (
                "AIME 2026 was held in early 2026 and published immediately, and the models "
                "under test were released afterwards. Whether these problems and their "
                "solutions were in their training data is NOT KNOWN, and cannot be "
                "established from this side of the API. Treat the accuracy column as "
                "possibly optimistic; it is one reason the reasoning scores matter more "
                "than the pass/fail count."
            ),
            "swapping_it_out": (
                "python3 -m harness.sync_problems --indices 3,11,14 rewrites this file with "
                "different problems. Everything downstream reads problem ids from it."
            ),
        },
        "problems": problems,
    }
    out = Path(a.out)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  wrote {out} — {len(problems)} problems from {DATASET}")
    for p in problems:
        print(f"    {p['problem_id']}  answer {p['expected_answer']:>3s}  {p['difficulty']}")
    print("\n  the problems ARE the experiment — re-run the study:")
    print("    rm -rf results/solver results/judges")
    print("    python3 -m harness.run_all && python3 -m judges.run_all")
    print("    python3 -m analysis.build_results && python3 deck/build.py\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
