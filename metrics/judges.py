"""Judge metrics — reported as headline numbers, not footnotes.

If the instrument disagrees with itself, a process score without that number
attached is not a result. Everything here is computed over stored verdicts;
none of it calls a model.
"""
from __future__ import annotations

from collections import Counter, defaultdict

ANCHORS = ("ESTABLISHES", "INCOMPLETE", "ERROR", "INDETERMINATE")


def _key(v) -> tuple:
    return (v.solver_config, v.task_id, v.run_idx)


def pair_up(verdicts) -> dict[tuple, dict[str, str]]:
    """(config, task, run) -> {judge_model: verdict}. Blinded verdicts only."""
    out: dict[tuple, dict[str, str]] = defaultdict(dict)
    for v in verdicts:
        if v.blinded is False:
            continue
        out[_key(v)][v.judge_model or "?"] = v.label
    return out


def cohens_kappa(a: list[str], b: list[str]) -> float:
    """Agreement above chance. Reported alongside raw agreement because raw
    agreement on a skewed label distribution flatters every judge."""
    n = len(a)
    if n == 0:
        return float("nan")
    obs = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    exp = sum((ca[l] / n) * (cb[l] / n) for l in set(a) | set(b))
    return 1.0 if exp == 1 else (obs - exp) / (1 - exp)


def inter_judge_agreement(verdicts) -> dict:
    paired = pair_up(verdicts)
    a, b, per_cfg = [], [], defaultdict(lambda: [0, 0])
    for (cfg, _, _), byjudge in paired.items():
        if len(byjudge) != 2:
            continue
        (_, va), (_, vb) = sorted(byjudge.items())
        a.append(va)
        b.append(vb)
        per_cfg[cfg][1] += 1
        per_cfg[cfg][0] += int(va == vb)
    return {
        "n_pairs": len(a),
        "raw_agreement": (sum(x == y for x, y in zip(a, b)) / len(a)) if a else float("nan"),
        "cohens_kappa": cohens_kappa(a, b),
        "per_config": {c: (hit / tot if tot else float("nan")) for c, (hit, tot) in per_cfg.items()},
        "confusion": Counter((x, y) for x, y in zip(a, b) if x != y).most_common(5),
    }


def severity(verdicts) -> dict:
    """Each judge's rate of NOT saying ESTABLISHES, across both of its roles.
    A consistently harsh model shows up in both."""
    tot, harsh = Counter(), Counter()
    roles = defaultdict(set)
    for v in verdicts:
        if v.blinded is False:
            continue
        j = v.judge_model or "?"
        tot[j] += 1
        harsh[j] += int(v.label != "ESTABLISHES")
        roles[j].add(v.solver_config)
    return {
        j: {"n": tot[j], "unsound_rate": harsh[j] / tot[j], "judging_roles": sorted(roles[j])}
        for j in sorted(tot)
    }


def blinding_effect(verdicts) -> dict:
    """The direct measurement of outcome leakage: on the SAME traces, how often
    does the verdict change when the judge is allowed to see the answer?"""
    blinded, unblinded = {}, {}
    for v in verdicts:
        slot = blinded if v.blinded else unblinded
        slot[(_key(v), v.judge_model)] = v.label
    common = set(blinded) & set(unblinded)
    if not common:
        return {"n": 0}
    changed = [(blinded[k], unblinded[k]) for k in common if blinded[k] != unblinded[k]]
    to_establishes = sum(1 for b, u in changed if u == "ESTABLISHES" and b != "ESTABLISHES")
    from_establishes = sum(1 for b, u in changed if b == "ESTABLISHES" and u != "ESTABLISHES")
    return {
        "n": len(common),
        "change_rate": len(changed) / len(common),
        "flipped_to_establishes": to_establishes,
        "flipped_from_establishes": from_establishes,
        "net_leniency": (to_establishes - from_establishes) / len(common),
        "blinded_unsound_rate": sum(1 for k in common if blinded[k] != "ESTABLISHES") / len(common),
        "unblinded_unsound_rate": sum(1 for k in common if unblinded[k] != "ESTABLISHES") / len(common),
    }


def human_agreement(verdicts, human_labels: dict[tuple, str]) -> dict:
    """Agreement with the instructor's labels on the calibration traces.

    Described on stage as single-annotator calibration, not an annotation
    study — because that is what it is.
    """
    per = defaultdict(lambda: [0, 0])
    for v in verdicts:
        if v.blinded is False:
            continue
        k = _key(v)
        if k not in human_labels:
            continue
        j = v.judge_model or "?"
        per[j][1] += 1
        per[j][0] += int(v.label == human_labels[k])
    return {
        "n_labelled": len(human_labels),
        "per_judge": {j: {"n": tot, "agreement": hit / tot if tot else float("nan")}
                      for j, (hit, tot) in sorted(per.items())},
    }


def right_answer_wrong_reasoning(answer_verdicts, judge_verdicts) -> dict:
    """Of the runs that got the right answer, what share had reasoning that at
    least one blinded judge called unsound? The number that makes the case for
    a process axis at all."""
    correct = {_key(v) for v in answer_verdicts if v.label == "correct"}
    flagged = defaultdict(list)
    for v in judge_verdicts:
        if v.blinded is False:
            continue
        if _key(v) in correct:
            flagged[_key(v)].append(v.label)
    any_unsound = sum(1 for ls in flagged.values() if any(l != "ESTABLISHES" for l in ls))
    both_unsound = sum(1 for ls in flagged.values()
                       if len(ls) == 2 and all(l != "ESTABLISHES" for l in ls))
    n = len(flagged)
    return {
        "n_correct_judged": n,
        "any_judge_unsound": any_unsound,
        "both_judges_unsound": both_unsound,
        "rate_any": any_unsound / n if n else float("nan"),
        "rate_both": both_unsound / n if n else float("nan"),
    }
