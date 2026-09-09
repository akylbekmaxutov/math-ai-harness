"""The experiment runner: one cell of the matrix, start to finish.

`run_one(problem, model, mode)` is the whole of Part I in one function —
configure, call, time, collect, price, grade, store. Everything above it is a
loop over cells; everything below it is provider dialect.

Three properties are worth naming during the workshop.

It never crashes the study. An unsupported mode, a timeout, a refusal — each
becomes a stored record with a `status` that is not "ok", so a nine-cell grid
with two failures still produces nine files and the website can draw the two
holes honestly.

It grades AFTER the fact, from the response text, using a checker that never
touched the prompt. The solver cannot see the key because the key is not in the
object it was handed.

It pins the apparatus. The system prompt, its hash, the temperature, the token
cap, the exact reasoning request that went on the wire, the pricing version and
a UTC timestamp all travel into the record. A number without those is a number
nobody can reproduce.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from harness import metrics, models, storage
from harness.answers import extract_final_answer, is_correct
from harness.problems import Problem
from harness.reasoning import UNSUPPORTED, ReasoningMode, UnsupportedReasoningMode
from providers.base import ProviderError, ProviderTimeout

#: The solver prompt, pinned. Changing a character of it changes what every
#: number in the study means, which is why it is a constant with a hash and not
#: an f-string assembled at the call site.
SYSTEM_PROMPT = (
    "You are solving a mathematics problem.\n"
    "Work through it step by step, showing the reasoning that justifies each step.\n"
    "Then state the final answer on its own last line in the form: "
    "FINAL ANSWER: \\boxed{...}\n"
    "Give the answer in exact form (a fraction rather than a decimal where applicable)."
)

# Reasoning tokens are charged against this cap, so it has to cover the thinking
# AND the written solution. Measured on the first real study: the largest run was
# Grok at high effort, 3182 output tokens of which 2930 were reasoning — 78% of a
# 4096 cap. A harder problem would have truncated. Sized with real headroom
# instead: a cap costs nothing unless the tokens are actually generated.
DEFAULTS = {"max_output_tokens": 16384, "max_attempts": 2}


def prompt_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


@dataclass
class ExperimentConfig:
    """Everything that decides what a run MEANS, in one object.

    Held together deliberately: a run is reproducible only if all of this is
    recorded, and the surest way to record all of it is for all of it to be one
    thing that gets serialised in one place.
    """

    model_key: str
    reasoning_mode: ReasoningMode
    max_output_tokens: int = DEFAULTS["max_output_tokens"]
    max_attempts: int = DEFAULTS["max_attempts"]
    system_prompt: str = SYSTEM_PROMPT
    mock: bool = False

    def solver_block(self, spec, reasoning_request: dict) -> dict:
        return {
            "model_key": self.model_key,
            "model": "mock-model" if self.mock else spec.model,
            "display": spec.display,
            "provider": "mock" if self.mock else spec.provider,
            "family": spec.family,
            "reasoning_mode": self.reasoning_mode.value,
            "reasoning_request": reasoning_request,
            "max_output_tokens": self.max_output_tokens,
            "system_prompt_sha": prompt_sha(self.system_prompt),
        }


def run_one(problem: Problem, config: ExperimentConfig) -> dict:
    """Execute one (problem x model x reasoning mode) cell and return its record."""
    spec = models.get(config.model_key)
    record = {
        "schema_version": storage.SCHEMA_VERSION,
        "run_id": storage.new_run_id("solve"),
        "kind": "solver_run",
        "timestamp": storage.now_iso(),
        "simulated": config.mock,
        "problem": {
            "problem_id": problem.problem_id,
            "title": problem.title,
            "kind": problem.kind,
            "question": problem.question,
            "expected_answer": problem.expected_answer,
            "set_version": problem.set_version,
        },
        "solver": config.solver_block(spec, {}),
        "status": "error",
        "attempts": 0,
        "error": None,
        "response": None,
        "usage": None,
        "timing": None,
        "cost": None,
        "correct": None,
    }

    # The capability check comes from the adapter class, before any call is
    # made, so an unsupported cell costs nothing and is still recorded.
    if config.reasoning_mode not in models.supported_modes(config.model_key):
        record["status"] = UNSUPPORTED
        record["error"] = {
            "type": "UnsupportedReasoningMode",
            "message": (f"{spec.display} does not expose "
                        f"{config.reasoning_mode.value!r} reasoning"),
            "supported": [m.value for m in models.supported_modes(config.model_key)],
        }
        return record

    adapter = models.build_adapter(config.model_key, mock=config.mock)
    last_error = None
    for attempt in range(1, config.max_attempts + 1):
        record["attempts"] = attempt
        try:
            with metrics.stopwatch() as clock:
                response = adapter.generate(
                    problem.for_solver(),
                    system=config.system_prompt,
                    reasoning_mode=config.reasoning_mode,
                    max_output_tokens=config.max_output_tokens,
                )
            break
        except UnsupportedReasoningMode as e:
            # Belt and braces: the adapter refuses too, in case a registry entry
            # and an adapter ever disagree.
            record["status"] = UNSUPPORTED
            record["error"] = {"type": type(e).__name__, "message": str(e)}
            return record
        except (ProviderTimeout, ProviderError) as e:
            last_error = e
            continue                       # a transport fault is worth one retry
    else:
        record["error"] = {"type": type(last_error).__name__, "message": str(last_error)}
        return record

    final = extract_final_answer(response.text)
    record["solver"] = config.solver_block(spec, response.reasoning_request)
    record["response"] = {
        "text": response.text,
        "final_answer": final,
        # Only what the API labelled as reasoning. See providers/base.py.
        "reasoning_summary": response.reasoning_summary,
        "reasoning_exposure": response.reasoning_exposure,
    }
    record["usage"] = metrics.usage_block(response)
    record["timing"] = {"latency_seconds": clock["latency_seconds"]}
    # Priced against the REAL model's list even in a simulated run, so the cost
    # views can be rehearsed. `simulated: true` above is what stops that number
    # being read as a measurement — the page banners every simulated row.
    record["cost"] = metrics.cost_block(config.model_key, response)
    record["correct"] = is_correct(final, problem.expected_answer, problem.answer_aliases)
    # A response with no marked answer is a formatting failure, not a wrong
    # answer, and the two are counted separately on the results page.
    record["status"] = "ok" if final is not None else "no_answer_marked"
    record["provider_meta"] = response.raw_meta
    return record


def run_and_store(problem: Problem, config: ExperimentConfig):
    """Run one cell and write it to its canonical path. Returns (record, path)."""
    record = run_one(problem, config)
    path = storage.solver_path(problem.problem_id, config.model_key,
                               config.reasoning_mode.value)
    storage.write_record(path, record)
    return record, path
