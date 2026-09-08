"""Deterministic tool replay.

Re-executes every logged python_exec call in the sandbox and diffs the result
against what the trace recorded. This catches two things a judge would only
guess at: a hallucinated tool result, and the case where a tool produced the
answer that the narration then takes credit for.

It is possible only because the trace is complete. This verifier was written
after the corpus existed and applied to all of it with zero solver calls.
"""
from __future__ import annotations

from agent.sandbox import run_python
from core.contracts import Rollout, Task, Verdict

NAME = "tool_replay"


def logged_calls(rollout: Rollout) -> list[tuple[str, dict]]:
    out, pending = [], None
    for ev in rollout.events:
        if ev.kind == "tool_call" and ev.payload.get("tool") == "python_exec":
            pending = ev.payload["args"].get("code", "")
        elif ev.kind == "tool_result" and pending is not None:
            out.append((pending, ev.payload.get("result", {})))
            pending = None
    return out


def verify(rollout: Rollout, task: Task) -> Verdict:
    calls = logged_calls(rollout)
    if not calls:
        return Verdict(NAME, rollout.task_id, rollout.run_idx, rollout.solver_config,
                       "no_tool_calls", {"n": 0})

    diffs = []
    for i, (code, recorded) in enumerate(calls):
        fresh = run_python(code)
        if fresh.stdout.strip() != str(recorded.get("stdout", "")).strip():
            diffs.append({
                "call": i,
                "recorded": str(recorded.get("stdout", ""))[:200],
                "replayed": fresh.stdout[:200],
            })

    answer_from_tool = any(
        str(rollout.final) and str(rollout.final).strip() in str(r.get("stdout", ""))
        for _, r in calls
    )
    return Verdict(
        NAME, rollout.task_id, rollout.run_idx, rollout.solver_config,
        "mismatch" if diffs else "match",
        {"n": len(calls), "diffs": diffs, "answer_produced_by_tool": answer_from_tool},
    )
