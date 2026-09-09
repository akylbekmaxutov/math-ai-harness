"""Do the two judges agree — and about what?

Deliberately simple arithmetic. Every number here can be recomputed on a slide
by hand from two verdicts, which matters more in a 40-minute workshop than a
better statistic nobody can check in real time. Cohen's kappa is the right tool
for a paper; it is the wrong tool for a room.

The distinction the whole section rests on: two judges agreeing on the VERDICT
while differing by two points on REASONING is not agreement. It is two judges
who happened to land on the same side of a threshold, and reporting only the
verdict would hide that completely.
"""
from __future__ import annotations

from statistics import mean

from judges.prompts import CRITERIA, ERROR_SEVERITY

#: How far apart two 1-5 scores have to be before we stop calling it agreement.
AGREEMENT_BANDS = ((0, "exact"), (1, "close"), (2, "moderate"), (4, "low"))


def band(delta: float) -> str:
    for limit, label in AGREEMENT_BANDS:
        if delta <= limit:
            return label
    return "low"


def compare(verdict_a: dict, verdict_b: dict) -> dict:
    """Two judge records for the same candidate -> one agreement summary."""
    ok = [v for v in (verdict_a, verdict_b) if v and v.get("status") == "ok"]
    if len(ok) < 2:
        return {"comparable": False,
                "reason": "at least one judge did not return a usable verdict"}

    a, b = verdict_a, verdict_b
    per_criterion = {}
    for key in CRITERIA:
        sa, sb = a["scores"][key], b["scores"][key]
        per_criterion[key] = {
            "a": sa, "b": sb, "abs_diff": abs(sa - sb),
            "agreement": band(abs(sa - sb)),
        }
    diffs = [c["abs_diff"] for c in per_criterion.values()]
    sev_a, sev_b = a["error_severity"], b["error_severity"]
    return {
        "comparable": True,
        "verdict_agreement": a["verdict"] == b["verdict"],
        "verdicts": [a["verdict"], b["verdict"]],
        "severity_agreement": sev_a == sev_b,
        "severities": [sev_a, sev_b],
        # How many severity steps apart, using the ordered scale from the rubric.
        "severity_distance": abs(ERROR_SEVERITY.index(sev_a) - ERROR_SEVERITY.index(sev_b)),
        "per_criterion": per_criterion,
        "mean_abs_diff": round(mean(diffs), 3),
        "max_abs_diff": max(diffs),
        "mean_judge_score": round(mean([a["mean_score"], b["mean_score"]]), 3),
        "overall": band(max(diffs)),
        # The headline for the slide: agreeing on the verdict is not the same
        # as agreeing on the reasoning, and this says which one happened.
        "verdict_agrees_but_scores_do_not": (a["verdict"] == b["verdict"]
                                             and max(diffs) >= 2),
    }


def judge_vs_ground_truth(verdicts: list[dict]) -> dict:
    """How often the judges' correctness score matched the deterministic check.

    The judges are never told the answer, so this is a real measurement of the
    instrument: a judge that scores correctness 5 on a solution the answer key
    marks wrong has made an error the rest of its scores should be read in the
    light of.
    """
    rows = [v for v in verdicts if v.get("status") == "ok"
            and v["candidate"].get("correct_per_harness") is not None]
    if not rows:
        return {"n": 0}
    hits = 0
    for v in rows:
        judged_correct = v["scores"]["correctness"] >= 4
        hits += int(judged_correct == bool(v["candidate"]["correct_per_harness"]))
    return {
        "n": len(rows),
        "agree": hits,
        "rate": round(hits / len(rows), 4),
        "note": "judge's correctness score (>=4 counts as 'correct') vs the "
                "deterministic answer check the judge never saw",
    }


def severity_profile(verdicts: list[dict]) -> dict:
    """How often each judge reaches for each severity label.

    A judge that says `major` twice as often as the other is a stricter
    instrument, and that difference is a property of the judge, not of the
    solutions it happened to be given.
    """
    out: dict[str, dict[str, int]] = {}
    for v in verdicts:
        if v.get("status") != "ok":
            continue
        row = out.setdefault(v["judge"]["model_key"], {s: 0 for s in ERROR_SEVERITY})
        row[v["error_severity"]] += 1
    return out
