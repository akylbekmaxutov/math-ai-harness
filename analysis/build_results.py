"""`python3 -m analysis.build_results` — join everything into one file the
website reads.

Runs and verdicts are written as many small files because that is what makes a
study resumable and inspectable. A browser wants one document. This is the
seam: it reads `results/solver/` and `results/judges/`, joins them on
(problem, model, reasoning mode), computes the agreement and the comparison
tables, and writes

    results/workshop_results.json

`python3 deck/build.py` then inlines that file into workshop.html, so the
presentation runs from a local file with no server, no network and no API keys.
Re-run these two commands after any experiment and the website is current.

Nothing is computed in the browser. Every number on the page was produced here,
by code that can be re-run and diffed.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis import agreement  # noqa: E402
from harness import models, problems, storage  # noqa: E402
from harness.pricing import MODEL_PRICING, PRICING_VERSION  # noqa: E402
from harness.reasoning import ReasoningMode  # noqa: E402
from judges.prompts import CRITERIA, ERROR_SEVERITY, SYSTEM as JUDGE_SYSTEM  # noqa: E402
from judges.run_all import DEFAULT_JUDGE_MODES  # noqa: E402
from harness.runner import SYSTEM_PROMPT  # noqa: E402

OUT = storage.RESULTS / "workshop_results.json"


def _avg(values):
    vals = [v for v in values if v is not None]
    return round(mean(vals), 4) if vals else None


def slim_verdict(v: dict) -> dict:
    """One judge verdict, as the page needs it. Raw text is kept only when the
    parse failed — that is the one case where a human has to read it."""
    return {
        "judge_key": v["judge"]["model_key"],
        "display": v["judge"]["display"],
        "provider": v["judge"]["provider"],
        "reasoning_mode": v["judge"]["reasoning_mode"],
        "reasoning_request": v["judge"].get("reasoning_request"),
        "status": v["status"],
        "scores": v.get("scores"),
        "mean_score": v.get("mean_score"),
        "verdict": v.get("verdict"),
        "error_severity": v.get("error_severity"),
        "explanation": v.get("explanation"),
        "usage": v.get("usage"),
        "timing": v.get("timing"),
        "cost": v.get("cost"),
        "simulated": v.get("simulated", False),
        "error": v.get("error"),
        "raw_text": v.get("raw_text") if v["status"] == "parse_failed" else None,
    }


def build() -> dict:
    solver_runs = storage.load_solver_runs()
    judge_runs = storage.load_judge_runs()

    # Verdicts, indexed by the candidate they judged and the effort they used.
    by_candidate = defaultdict(lambda: defaultdict(list))
    for v in judge_runs:
        c = v["candidate"]
        key = (c["problem_id"], c["model_key"], c["reasoning_mode"])
        by_candidate[key][v["judge"]["reasoning_mode"]].append(v)

    runs = []
    for r in solver_runs:
        s = r["solver"]
        key = (r["problem"]["problem_id"], s["model_key"], s["reasoning_mode"])
        resp = r.get("response") or {}
        verdicts = {jm: sorted(vs, key=lambda v: v["judge"]["model_key"])
                    for jm, vs in by_candidate.get(key, {}).items()}
        runs.append({
            "key": "|".join(key),
            "run_id": r["run_id"],
            "timestamp": r["timestamp"],
            "simulated": r.get("simulated", False),
            "problem_id": key[0],
            "model_key": s["model_key"],
            "display": s["display"],
            "provider": s["provider"],
            "model": s["model"],
            "reasoning_mode": s["reasoning_mode"],
            "reasoning_request": s.get("reasoning_request"),
            "system_prompt_sha": s.get("system_prompt_sha"),
            "status": r["status"],
            "attempts": r.get("attempts"),
            "error": r.get("error"),
            "correct": r.get("correct"),
            "expected_answer": r["problem"]["expected_answer"],
            "final_answer": resp.get("final_answer"),
            "response_text": resp.get("text"),
            "reasoning_summary": resp.get("reasoning_summary"),
            "reasoning_exposure": resp.get("reasoning_exposure", "none"),
            "usage": r.get("usage"),
            "timing": r.get("timing"),
            "cost": r.get("cost"),
            "judges": {jm: [slim_verdict(v) for v in vs] for jm, vs in verdicts.items()},
            "agreement": {
                jm: agreement.compare(vs[0], vs[1]) if len(vs) == 2 else
                    {"comparable": False, "reason": f"{len(vs)} verdict(s) stored"}
                for jm, vs in verdicts.items()
            },
        })

    return {
        "schema_version": storage.SCHEMA_VERSION,
        "built_at": storage.now_iso(),
        # True if ANY row came from the offline simulator. The page banners the
        # whole results section when this is set — a mixed set is not a study.
        "simulated": any(r["simulated"] for r in runs) or any(
            v.get("simulated") for v in judge_runs),
        "pricing_version": PRICING_VERSION,
        "solver_system_prompt": SYSTEM_PROMPT,
        "judge_system_prompt": JUDGE_SYSTEM,
        "reasoning_modes": [m.value for m in ReasoningMode],
        "judge_modes": list(DEFAULT_JUDGE_MODES),
        "rubric": {k: {"title": t, "anchors": a} for k, (t, a) in CRITERIA.items()},
        "error_severity_scale": list(ERROR_SEVERITY),
        "capability_matrix": models.capability_matrix(),
        "models": [
            {"key": k, "display": s.display, "provider": s.provider, "family": s.family,
             "pricing": MODEL_PRICING.get(k)}
            for k, s in models.MODELS.items()
        ],
        "problems": [
            {"problem_id": p.problem_id, "title": p.title, "kind": p.kind,
             "question": p.question, "expected_answer": p.expected_answer,
             "why_this_problem": p.why_this_problem, "set_version": p.set_version}
            for p in problems.load_problems().values()
        ],
        "runs": runs,
        "summary": summarise(runs, judge_runs),
    }


def summarise(runs: list[dict], judge_runs: list[dict]) -> dict:
    """The comparison dashboard, computed once, here."""
    graded = [r for r in runs if r["status"] in ("ok", "no_answer_marked")]

    def cell(rows):
        if not rows:
            return None
        jr = [v for r in rows for vs in r["judges"].values() for v in vs
              if v["status"] == "ok"]
        agree = [a for r in rows for a in r["agreement"].values() if a.get("comparable")]
        return {
            "n": len(rows),
            "n_correct": sum(1 for r in rows if r["correct"]),
            "accuracy": round(sum(1 for r in rows if r["correct"]) / len(rows), 4),
            "mean_total_tokens": _avg([r["usage"]["total_tokens"] for r in rows]),
            "mean_reasoning_tokens": _avg([r["usage"]["reasoning_tokens"] for r in rows]),
            "mean_latency_s": _avg([r["timing"]["latency_seconds"] for r in rows]),
            "total_cost_usd": round(sum(r["cost"]["estimated_usd"] for r in rows), 6),
            "judge_mean_score": _avg([v["mean_score"] for v in jr]),
            "judge_reasoning_score": _avg([v["scores"]["reasoning"] for v in jr]),
            "judge_pass_rate": (round(sum(1 for v in jr if v["verdict"] == "pass") / len(jr), 4)
                                if jr else None),
            "verdict_agreement_rate": (round(sum(1 for a in agree if a["verdict_agreement"])
                                             / len(agree), 4) if agree else None),
            "mean_score_gap": _avg([a["mean_abs_diff"] for a in agree]),
            "judge_cost_usd": round(sum(v["cost"]["estimated_usd"] for v in jr), 6),
        }

    by_model_mode = {}
    for r in graded:
        by_model_mode.setdefault(f'{r["model_key"]}|{r["reasoning_mode"]}', []).append(r)
    by_model = {}
    for r in graded:
        by_model.setdefault(r["model_key"], []).append(r)
    by_mode = {}
    for r in graded:
        by_mode.setdefault(r["reasoning_mode"], []).append(r)
    by_problem = {}
    for r in graded:
        by_problem.setdefault(r["problem_id"], []).append(r)

    solver_cost = sum(r["cost"]["estimated_usd"] for r in graded)
    judge_cost = sum(v["cost"]["estimated_usd"] for v in judge_runs
                     if v.get("cost") and v["status"] in ("ok", "parse_failed"))
    ok_v = [v for v in judge_runs if v["status"] == "ok"]
    return {
        "by_model_mode": {k: cell(v) for k, v in sorted(by_model_mode.items())},
        "by_model": {k: cell(v) for k, v in by_model.items()},
        "by_mode": {k: cell(v) for k, v in by_mode.items()},
        "by_problem": {k: cell(v) for k, v in by_problem.items()},
        "judge_vs_ground_truth": agreement.judge_vs_ground_truth(judge_runs),
        "judge_severity_profile": agreement.severity_profile(judge_runs),
        "counts": {
            "solver_cells": len(runs),
            "solver_ok": len(graded),
            "solver_unsupported": sum(1 for r in runs if r["status"] == "unsupported"),
            "solver_error": sum(1 for r in runs if r["status"] == "error"),
            "verdicts": len(judge_runs),
            "verdicts_ok": len(ok_v),
            "verdicts_parse_failed": sum(1 for v in judge_runs if v["status"] == "parse_failed"),
        },
        "cost": {
            # The number people forget: evaluating cost money too, and with two
            # judges at two efforts it is usually MORE than the solving did.
            "solver_usd": round(solver_cost, 6),
            "judge_usd": round(judge_cost, 6),
            "total_usd": round(solver_cost + judge_cost, 6),
            "judge_share": (round(judge_cost / (solver_cost + judge_cost), 4)
                            if solver_cost + judge_cost else None),
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="analysis.build_results",
                                 description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)

    data = build()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    c, cost = data["summary"]["counts"], data["summary"]["cost"]
    print(f"\n  {c['solver_cells']} solver cells "
          f"({c['solver_ok']} ok, {c['solver_unsupported']} unsupported, {c['solver_error']} error)")
    print(f"  {c['verdicts']} verdicts "
          f"({c['verdicts_ok']} ok, {c['verdicts_parse_failed']} unparseable)")
    print(f"  solver ${cost['solver_usd']:.4f}  +  judges ${cost['judge_usd']:.4f}"
          f"  =  ${cost['total_usd']:.4f}   "
          f"(judges are {100 * (cost['judge_share'] or 0):.0f}% of it)")
    if data["simulated"]:
        print("  SIMULATED DATA — the website will banner every figure derived from it.")
    print(f"  wrote {out.relative_to(storage.ROOT)}  {out.stat().st_size:,} bytes")
    print("  next: python3 deck/build.py\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
