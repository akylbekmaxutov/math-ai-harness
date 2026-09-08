"""The turn loop, written by hand.

A framework would have supplied this in three lines. Writing it once is what
makes it possible to say, on stage, exactly what a framework would have bought
— retries, schema plumbing, a message-history abstraction — and why none of it
was needed here.

Note what this function does NOT do: it never decides whether the answer was
correct. It has no answer key and cannot get one. It records what happened and
stops. Correctness is assigned downstream, from the trace, by a verifier.
"""
from __future__ import annotations

import json

from agent import tools as toolmod
from agent.providers import Completion, ProviderError, ProviderTimeout
from core.budget import Budget, BudgetExceeded
from core.config import RunConfig
from core.contracts import Rollout, Task
from core.trace import TraceRecorder

REFUSAL_MARKERS = ("i am not able", "i cannot", "i can't help", "i won't")


def run_rollout(task: Task, cfg: RunConfig, provider, run_idx: int,
                seed: int | None = None) -> Rollout:
    rec = TraceRecorder(task.task_id, run_idx, cfg.solver_config, cfg.config_hash, seed)
    budget = Budget(usd_cap=cfg.usd_budget, turn_cap=cfg.max_turns)
    schemas = toolmod.schemas(cfg.tools)

    messages = [
        {"role": "system", "content": cfg.prompt},
        {"role": "user", "content": task.problem},
    ]
    rec.emit("run_start", task_id=task.task_id, run_idx=run_idx, config=cfg.header())

    while True:
        try:
            budget.check("turn")
        except BudgetExceeded as e:
            rec.emit("error", fault=e.kind, message=str(e))
            return _stop(rec, "max_turns" if e.kind == "turn" else "budget_exceeded", budget)

        rec.emit("model_call", n_messages=len(messages), model=cfg.model.model)
        try:
            comp: Completion = provider.complete(messages, schemas)
        except ProviderTimeout as e:
            # A harness failure. Not a wrong answer.
            rec.emit("error", fault="timeout", message=str(e))
            return _stop(rec, "timeout", budget)
        except ProviderError as e:
            rec.emit("error", fault="provider", message=str(e))
            return _stop(rec, "error", budget)

        budget.turns_used += 1
        from agent.providers import usd as _usd
        budget.charge(comp.tokens_in, comp.tokens_out,
                      _usd(cfg.model, comp.tokens_in, comp.tokens_out))
        rec.emit("model_response", text=comp.text,
                 tool_calls=[c["name"] for c in comp.tool_calls],
                 tokens_in=comp.tokens_in, tokens_out=comp.tokens_out)

        if not comp.tool_calls:
            low = (comp.text or "").lower()
            if any(m in low for m in REFUSAL_MARKERS):
                return _stop(rec, "refused", budget, final=None)
            # No tool call and no refusal: nudge once, then let the turn cap bite.
            messages.append({"role": "assistant", "content": comp.text})
            messages.append({"role": "user",
                             "content": "Call a tool, or submit_answer if you are done."})
            continue

        messages.append({"role": "assistant", "content": comp.text or None,
                         "tool_calls": comp.tool_calls})

        for tc in comp.tool_calls:
            rec.emit("tool_call", tool=tc["name"], args=tc["args"])
            try:
                result = toolmod.call(tc["name"], tc["args"], budget)
            except toolmod.SubmitAnswer as s:
                rec.emit("final", value=s.value, reasoning=s.reasoning)
                return _stop(rec, "submitted", budget, final=s.value)
            except BudgetExceeded as e:
                # The trip kind matters: hitting the turn cap is `max_turns`,
                # hitting the spend cap is `budget_exceeded`. Flattening the two
                # would lose the distinction the taxonomy exists to make.
                rec.emit("error", fault=e.kind, message=str(e))
                return _stop(rec, "max_turns" if e.kind == "turn" else "budget_exceeded",
                             budget)
            except Exception as e:  # noqa: BLE001
                result = {"error": f"{type(e).__name__}: {e}"}
            rec.emit("tool_result", tool=tc["name"], result=result)
            messages.append({"role": "tool", "name": tc["name"],
                             "content": json.dumps(result)})


def _stop(rec: TraceRecorder, outcome: str, budget: Budget, final=None) -> Rollout:
    return rec.finish(outcome, final=final, **budget.snapshot())
