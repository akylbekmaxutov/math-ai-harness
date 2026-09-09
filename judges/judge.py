"""Running one judge over one candidate solution.

Structurally this is the solver runner again — configure, call, time, price,
store — with two additions that are specific to judging.

**Parsing is a first-class outcome.** A judge that returns something other than
the required JSON has not returned a low score; it has returned nothing. That
is recorded as `status: "parse_failed"` with the raw text kept, and it is
counted on the website. A pipeline that silently drops unparseable verdicts
reports the agreement rate of the subset of cases the judges found easy to
format, which is not the agreement rate.

**Scores are validated, not trusted.** Out-of-range numbers, invented severity
labels and missing criteria are rejected here rather than propagating into an
average that looks fine.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from harness import metrics, models, storage
from harness.reasoning import UNSUPPORTED, ReasoningMode, UnsupportedReasoningMode
from harness.runner import prompt_sha
from judges import prompts
from providers.base import ProviderError, ProviderTimeout

FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class VerdictParseError(ValueError):
    """The judge's reply was not a usable verdict."""


@dataclass
class JudgeConfig:
    judge_key: str
    reasoning_mode: ReasoningMode
    max_output_tokens: int = 1024
    max_attempts: int = 2
    mock: bool = False


def parse_verdict(text: str) -> dict:
    """Text -> a validated verdict, or raise.

    Tolerant about packaging — a fenced block or a JSON object embedded in prose
    is accepted, because that is a formatting quirk and not a judgement. Strict
    about content: every criterion must be present and in range, and the labels
    must be ones the rubric defines. `int(4.0)` is accepted, `"4"` is accepted,
    `4.5` is not: the rubric is a five-point scale, and a judge that answers off
    the scale has not used the rubric.
    """
    if not text or not text.strip():
        raise VerdictParseError("judge returned empty text")
    blob = None
    m = FENCE.search(text)
    candidates = [m.group(1)] if m else []
    candidates.append(text)
    # Fall back to the outermost braces, for a verdict wrapped in commentary.
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        candidates.append(brace.group(0))
    for c in candidates:
        try:
            blob = json.loads(c.strip())
            break
        except (json.JSONDecodeError, TypeError):
            continue
    if not isinstance(blob, dict):
        raise VerdictParseError("no JSON object found in the judge's reply")

    scores = {}
    for key in prompts.CRITERIA:
        if key not in blob:
            raise VerdictParseError(f"missing criterion {key!r}")
        raw = blob[key]
        try:
            val = int(raw) if float(raw) == int(float(raw)) else None
        except (TypeError, ValueError):
            val = None
        if val is None or not 1 <= val <= 5:
            raise VerdictParseError(f"{key}={raw!r} is not an integer 1-5")
        scores[key] = val

    sev = str(blob.get("error_severity", "")).strip().lower()
    if sev not in prompts.ERROR_SEVERITY:
        raise VerdictParseError(f"error_severity={sev!r} is not one of {prompts.ERROR_SEVERITY}")
    verdict = str(blob.get("verdict", "")).strip().lower()
    if verdict not in prompts.VERDICTS:
        raise VerdictParseError(f"verdict={verdict!r} is not one of {prompts.VERDICTS}")

    return {
        "scores": scores,
        "error_severity": sev,
        "verdict": verdict,
        "explanation": str(blob.get("explanation", "")).strip(),
        "mean_score": round(sum(scores.values()) / len(scores), 3),
    }


def judge_one(candidate: dict, config: JudgeConfig) -> dict:
    """Judge one stored solver run. Returns the judge record."""
    spec = models.get(config.judge_key)
    cand_sol, cand_resp = candidate["solver"], (candidate.get("response") or {})
    prompt = prompts.build(
        question=candidate["problem"]["question"],
        solution_text=cand_resp.get("text", ""),
        claimed_answer=cand_resp.get("final_answer"),
    )
    record = {
        "schema_version": storage.SCHEMA_VERSION,
        "run_id": storage.new_run_id("judge"),
        "kind": "judge_run",
        "timestamp": storage.now_iso(),
        "simulated": config.mock,
        "candidate": {
            "run_id": candidate["run_id"],
            "problem_id": candidate["problem"]["problem_id"],
            "model_key": cand_sol["model_key"],
            "display": cand_sol["display"],
            "reasoning_mode": cand_sol["reasoning_mode"],
            "final_answer": cand_resp.get("final_answer"),
            # Recorded for the analysis, NOT shown to the judge. The judge
            # prompt is built above and this field is not in it.
            "correct_per_harness": candidate.get("correct"),
        },
        "judge": {
            "model_key": config.judge_key,
            "display": spec.display,
            "provider": "mock" if config.mock else spec.provider,
            "model": "mock-model" if config.mock else spec.model,
            "family": spec.family,
            "reasoning_mode": config.reasoning_mode.value,
            "reasoning_request": {},
            "prompt_sha": prompt_sha(prompts.SYSTEM + prompt),
            "rubric_criteria": list(prompts.CRITERIA),
        },
        "status": "error", "error": None, "attempts": 0,
        "scores": None, "verdict": None, "error_severity": None,
        "explanation": None, "mean_score": None,
        "raw_text": None, "usage": None, "timing": None, "cost": None,
    }

    if config.reasoning_mode not in models.supported_modes(config.judge_key):
        record["status"] = UNSUPPORTED
        record["error"] = {"type": "UnsupportedReasoningMode",
                           "message": f"{spec.display} does not expose "
                                      f"{config.reasoning_mode.value!r} reasoning"}
        return record

    adapter = models.build_adapter(config.judge_key, mock=config.mock)
    last = None
    for attempt in range(1, config.max_attempts + 1):
        record["attempts"] = attempt
        try:
            with metrics.stopwatch() as clock:
                response = adapter.generate(prompt, system=prompts.SYSTEM,
                                            reasoning_mode=config.reasoning_mode,
                                            max_output_tokens=config.max_output_tokens)
            break
        except UnsupportedReasoningMode as e:
            record["status"] = UNSUPPORTED
            record["error"] = {"type": type(e).__name__, "message": str(e)}
            return record
        except (ProviderTimeout, ProviderError) as e:
            last = e
            continue
    else:
        record["error"] = {"type": type(last).__name__, "message": str(last)}
        return record

    record["judge"]["reasoning_request"] = response.reasoning_request
    record["usage"] = metrics.usage_block(response)
    record["timing"] = {"latency_seconds": clock["latency_seconds"]}
    record["cost"] = metrics.cost_block(config.judge_key, response)
    record["raw_text"] = response.text
    record["reasoning_exposure"] = response.reasoning_exposure

    try:
        parsed = parse_verdict(response.text)
    except VerdictParseError as e:
        # Kept, counted, and visible on the website. Not silently dropped.
        record["status"] = "parse_failed"
        record["error"] = {"type": "VerdictParseError", "message": str(e)}
        return record

    record.update(parsed)
    record["status"] = "ok"
    return record


def judge_and_store(candidate: dict, config: JudgeConfig):
    record = judge_one(candidate, config)
    path = storage.judge_path(
        candidate["problem"]["problem_id"],
        candidate["solver"]["model_key"], candidate["solver"]["reasoning_mode"],
        config.judge_key, config.reasoning_mode.value,
    )
    storage.write_record(path, record)
    return record, path
