"""The seven-way outcome classifier.

`error` and `timeout` are harness failures, not agent failures. Counting them
as `incorrect` deflates accuracy by however unreliable the provider was that
afternoon; silently retrying inflates it. They get their own names, the error
rate is reported alongside accuracy, and every report states whether errored
rollouts sit in the denominator.

Classification happens HERE, downstream of the trace, and not in the loop —
because deciding `correct` requires the answer key, and the agent code path
must never be able to reach it.
"""
from __future__ import annotations

from core.contracts import (
    AGENT_OUTCOMES,
    HARNESS_FAILURES,
    HARNESS_STOPS,
    OUTCOMES,
    Rollout,
)

# What the loop can know on its own, before any verifier runs.
EXECUTION_STATES = ("submitted", "max_turns", "budget_exceeded", "error", "timeout", "refused")


def classify(rollout: Rollout, answer_correct: bool | None) -> str:
    """Combine the recorded execution state with the deterministic answer check."""
    state = rollout.outcome
    if state != "submitted":
        if state not in OUTCOMES and state not in EXECUTION_STATES:
            raise ValueError(f"unknown execution state: {state}")
        return state
    if answer_correct is None:
        raise ValueError("a submitted rollout cannot be classified without an answer check")
    return "correct" if answer_correct else "incorrect"


def is_harness_failure(outcome: str) -> bool:
    return outcome in HARNESS_FAILURES


def is_agent_outcome(outcome: str) -> bool:
    return outcome in AGENT_OUTCOMES


def bucket(outcome: str) -> str:
    if outcome in AGENT_OUTCOMES:
        return "agent"
    if outcome in HARNESS_STOPS:
        return "stop"
    if outcome in HARNESS_FAILURES:
        return "harness"
    return "unknown"


def tally(outcomes) -> dict:
    counts = {o: 0 for o in OUTCOMES}
    for o in outcomes:
        counts[o] = counts.get(o, 0) + 1
    n = sum(counts.values()) or 1
    harness = sum(counts[o] for o in HARNESS_FAILURES)
    return {
        "counts": counts,
        "n": sum(counts.values()),
        "error_rate": harness / n,
        "graded_n": sum(counts[o] for o in AGENT_OUTCOMES) + sum(counts[o] for o in HARNESS_STOPS),
    }
