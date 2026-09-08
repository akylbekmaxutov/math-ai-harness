"""Masked continuation — a quasi-mechanical cross-check on the judges.

Strip the submitted answer, hand the reasoning to a model, and ask what value
that reasoning determines. If the reasoning genuinely establishes the
submitted answer, the continuation lands on it. If the narration asserted
something the tool never produced, the continuation lands somewhere else.

It is a cross-check on the judges because it does not ask for an opinion. It
asks for a consequence.
"""
from __future__ import annotations

import re

from core.contracts import Rollout, Task, Verdict
from verifiers.process_judge import render

NAME = "masked_cont"

PROMPT = (
    "Below is a partial chain of mathematical reasoning with its tool output. "
    "The final answer has been removed. Continue the reasoning and state only the "
    "single integer it determines. Reply with that integer and nothing else."
)

_NUM = re.compile(r"-?\d+")


class MockContinuer:
    """Reads what the narration actually committed to, rather than guessing."""

    def __init__(self, spec):
        self.spec = spec

    def complete(self, messages, tools):
        from agent.providers import Completion
        from verifiers.process_judge import _blocks

        body = messages[-1]["content"]
        narration = _blocks(body, "NARRATION")
        nums = _NUM.findall(narration[-1]) if narration else []
        if not nums:
            nums = _NUM.findall("\n".join(_blocks(body, "TOOL STDOUT")))
        return Completion(nums[-1] if nums else "", [], 800, 8)


def verify(rollout: Rollout, task: Task, provider) -> Verdict:
    if rollout.outcome != "submitted":
        return Verdict(NAME, rollout.task_id, rollout.run_idx, rollout.solver_config,
                       "not_submitted", {})
    body, _ = render(rollout, task, blinded=True)
    out = provider.complete(
        [{"role": "system", "content": PROMPT}, {"role": "user", "content": body}], []
    ).text
    nums = _NUM.findall(out or "")
    landed = nums[-1] if nums else None
    submitted = str(rollout.final).strip()
    if landed is None:
        label = "indeterminate"
    else:
        label = "match" if landed == submitted else "mismatch"
    return Verdict(NAME, rollout.task_id, rollout.run_idx, rollout.solver_config, label,
                   {"landed": landed, "submitted": submitted})
