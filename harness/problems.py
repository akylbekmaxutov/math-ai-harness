"""The problem loader.

Loads the standardised problem set and hands the solver a view of a problem
that does NOT contain the answer.

That last point is structural, not stylistic. `Problem.for_solver()` returns
the question and nothing else, and the expected answer is reachable only
through `Problem.expected_answer`, which only the grader calls. A prompt
builder cannot leak the key by accident because it never holds it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBLEMS_FILE = ROOT / "problems" / "problems.json"


@dataclass(frozen=True)
class Problem:
    problem_id: str
    title: str
    kind: str
    question: str
    expected_answer: str
    answer_aliases: tuple[str, ...]
    answer_kind: str
    why_this_problem: str
    set_version: str

    def for_solver(self) -> str:
        """Everything the solver is allowed to see. The key is not in here."""
        return self.question


def load_problems(path: Path | None = None) -> dict[str, Problem]:
    """Read problems.json into `{problem_id: Problem}`, insertion-ordered.

    A stable `problem_id` is what lets a result written on Monday be joined to a
    judge verdict written on Friday. Matching on the question text instead works
    right up until someone fixes a typo, and then silently stops.
    """
    raw = json.loads((path or PROBLEMS_FILE).read_text(encoding="utf-8"))
    version = raw.get("problem_set_version", "unversioned")
    out: dict[str, Problem] = {}
    for p in raw["problems"]:
        pid = p["problem_id"]
        if pid in out:
            raise ValueError(f"duplicate problem_id {pid!r} — ids must be unique")
        out[pid] = Problem(
            problem_id=pid,
            title=p["title"],
            kind=p["kind"],
            question=p["question"],
            expected_answer=str(p["expected_answer"]),
            answer_aliases=tuple(str(a) for a in p.get("answer_aliases", ())),
            answer_kind=p.get("answer_kind", "string"),
            why_this_problem=p.get("why_this_problem", ""),
            set_version=version,
        )
    return out


def get(problem_id: str, path: Path | None = None) -> Problem:
    probs = load_problems(path)
    if problem_id not in probs:
        known = ", ".join(probs)
        raise KeyError(f"no problem {problem_id!r}. Known ids: {known}")
    return probs[problem_id]
