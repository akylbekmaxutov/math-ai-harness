"""The judge prompt and the rubric, in one place.

Everything the judge is shown is assembled here, so "what was the judge asked?"
has a single answer that fits on a slide. Three decisions in this file carry
most of the weight.

**The rubric has six named criteria, not one question.** "Is this answer good?"
returns a number that means whatever the model felt like. Six criteria with
written anchors return six numbers you can disagree with specifically — and
disagreement you can locate is the only kind worth measuring.

**The judge is NOT given the expected answer.** It scores final-answer
correctness on its own mathematics. This costs accuracy on criterion 1 and buys
the other five: a judge told the answer was right rationalises the route that
reached it, and a judge told it was wrong finds faults in reasoning that is
sound. The harness already knows the truth deterministically
(`harness/answers.py`), so handing it to the judge would purchase nothing and
contaminate everything. The gap between the judge's correctness score and the
deterministic check is then a real measurement of the judge, reported on the
website.

**Output is strict JSON.** A judge that writes prose is a judge whose scores
have to be read by a human, which is the cost the whole method exists to avoid.
"""
from __future__ import annotations

#: The five 1-5 criteria, with the anchors that make a 3 mean the same thing to
#: two different judges. Anchors are the difference between a rubric and a vibe.
CRITERIA = {
    "correctness": (
        "Final answer correctness",
        "5 = the final answer is correct. 3 = correct in form but misstated, "
        "mis-simplified, or ambiguous. 1 = the final answer is wrong.",
    ),
    "reasoning": (
        "Reasoning correctness",
        "5 = every intermediate step is valid and follows from the last. "
        "3 = one questionable or unjustified step, conclusion still supported. "
        "1 = contains a definite mathematical error, or the conclusion does not "
        "follow from the steps given.",
    ),
    "completeness": (
        "Completeness",
        "5 = the reasoning fully justifies the result; nothing load-bearing is "
        "assumed without argument. 3 = a necessary case, check or justification "
        "is skipped. 1 = the result is asserted rather than derived.",
    ),
    "efficiency": (
        "Efficiency",
        "5 = direct, no redundant work. 3 = noticeable detours or repetition "
        "that do not affect validity. 1 = mostly wandering, backtracking or "
        "restating.",
    ),
    "clarity": (
        "Clarity",
        "5 = a reader can follow every step without reconstructing it. "
        "3 = followable with effort. 1 = the argument cannot be followed as written.",
    ),
}

#: Ordered worst-last, so "at least minor" is a prefix test rather than a set.
ERROR_SEVERITY = ("none", "minor", "major", "incorrect_conclusion")

VERDICTS = ("pass", "fail")

SYSTEM = (
    "You are evaluating a written mathematical solution against a fixed rubric.\n"
    "You are NOT told the correct answer. Judge correctness by doing the "
    "mathematics yourself.\n"
    "Score each criterion on the rubric's own anchors, not on how confident or "
    "how long the solution sounds.\n"
    "Reply with a single JSON object and nothing else — no prose, no code fence."
)


def rubric_block() -> str:
    lines = ["RUBRIC — score each 1-5 using these anchors:"]
    for key, (title, anchors) in CRITERIA.items():
        lines.append(f"  {key} ({title}): {anchors}")
    lines += [
        "",
        "error_severity — classify the worst error present, one of:",
        "  none                  no error",
        "  minor                 a slip that does not affect the conclusion",
        "  major                 a reasoning error that undermines the argument",
        "  incorrect_conclusion  the solution reaches a wrong final answer",
        "",
        "verdict — 'pass' if the solution both reaches the right answer AND "
        "justifies it; otherwise 'fail'.",
        "explanation — two sentences. Quote the specific step you scored on.",
    ]
    return "\n".join(lines)


def output_block() -> str:
    """The exact shape required back. Shown to the judge verbatim, and used by
    judges/judge.py to validate what comes back."""
    return (
        'OUTPUT — exactly this JSON object:\n'
        '{"correctness": 1-5, "reasoning": 1-5, "completeness": 1-5, '
        '"efficiency": 1-5, "clarity": 1-5, '
        '"error_severity": "none|minor|major|incorrect_conclusion", '
        '"verdict": "pass|fail", "explanation": "..."}'
    )


def build(question: str, solution_text: str, claimed_answer: str | None) -> str:
    """The complete judge prompt for one candidate solution.

    Note what is absent: the expected answer, the harness's correctness
    verdict, the solver's identity, its reasoning mode, its token count and its
    cost. A judge that knows it is reading the expensive high-effort run from
    the famous model is not scoring the same thing as one that does not.
    """
    return "\n\n".join([
        "PROBLEM:\n" + question,
        "CANDIDATE SOLUTION:\n" + (solution_text or "(the model returned no text)"),
        "The solution states its final answer as: "
        + (claimed_answer if claimed_answer is not None else "(no final answer was marked)"),
        rubric_block(),
        output_block(),
    ])
