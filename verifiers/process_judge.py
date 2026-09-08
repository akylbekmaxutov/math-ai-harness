"""The process judge, and the blinding function that feeds it.

This is the pedagogically most important module in the project. A process
judge that can see the final answer was correct will rationalise flawed
reasoning as sound, so the judge is shown the problem, the reasoning and the
tool interactions — and nothing else.

Two things are worth saying out loud about the assertion below.

It is a HARD failure for anything the harness controls: model identifiers,
the outcome, the answer key, run metadata, the submitted value. If any of
those survive into a rendered prompt, rendering raises.

What it does NOT do is scrub the value the reasoning concludes with. An
earlier version of this module did, and it was wrong in an instructive way:
the substitution only fired when the narrated value matched the submission —
which is exactly when the narration was faithful. The marker therefore
appeared on sound traces and not on flawed ones, and a judge could read the
verdict straight off the presence of a placeholder. Blinding that introduces
a tell is worse than no blinding, because it looks careful.

So the rule is narrower and holds up: remove the SUBMISSION — the value, its
post-hoc reasoning field, the outcome, the metadata, the identifiers — and
leave the reasoning intact, including whatever number it argues its way to.
The judge can then see WHAT the run concluded. It still cannot see WHETHER
that was right, because the answer key never enters this module at all.

That is the honest limit of prompt-level blinding on a trace whose tool
computed the answer, and it is why the blinded-versus-unblinded ablation —
not the redaction — is the measurement that bounds outcome leakage.
"""
from __future__ import annotations

import json
import re

from core.contracts import Rollout, Task, Verdict

NAME = "process_judge"

ANCHORS = ("ESTABLISHES", "INCOMPLETE", "ERROR", "INDETERMINATE")

SYSTEM = (
    "You are evaluating whether a chain of mathematical reasoning establishes a "
    "conclusion. You are not being asked whether the conclusion is correct, and you "
    "will not be told what the correct answer is."
)

TASK_BLOCK = """TASK:
Choose exactly one verdict:
  ESTABLISHES     the reasoning is sufficient to determine the conclusion
  INCOMPLETE      no error, but gaps remain before a conclusion follows
  ERROR           the reasoning contains a specific mistake
  INDETERMINATE   the reasoning supports no determinate conclusion

Quote the single span of the reasoning that is the basis for your verdict.
Give one sentence of justification.

OUTPUT strict JSON: {"verdict": ..., "span": ..., "justification": ...}"""

REDACTED = "[REDACTED]"


class BlindingLeak(AssertionError):
    """Raised when something the harness controls survived into the prompt."""


class VerdictRejected(ValueError):
    """A verdict without a non-empty span is rejected at parse time."""


def _identifiers(rollout: Rollout, extra=()) -> list[str]:
    ids = {rollout.solver_config, rollout.config_hash, *extra}
    for ev in rollout.events:
        if ev.kind == "run_start":
            cfg = ev.payload.get("config", {})
            ids.update(str(v) for k, v in cfg.items()
                       if k in ("model", "provider", "solver_config", "config_hash"))
        if ev.kind == "model_call":
            ids.add(str(ev.payload.get("model", "")))
    return sorted(i for i in ids if i and len(str(i)) > 1)


def render(rollout: Rollout, task: Task, *, blinded: bool = True,
           model_names=(), graded_outcome: str | None = None) -> tuple[str, dict]:
    """Build the judge prompt. Returns (prompt, audit).

    `blinded=False` is the SAME function with a flag: it leaves the final
    answer and the GRADED outcome in. The diff between the two prompts is the
    slide, and `graded_outcome` is the part that does the damage — telling a
    judge the answer was right is what makes it rationalise the reasoning.
    Passing the raw execution state instead would leak nothing, and the
    ablation would silently measure noise.
    """
    submitted = "" if rollout.final is None else str(rollout.final).strip()
    ids = _identifiers(rollout, model_names)

    parts = [SYSTEM, "", f"PROBLEM:\n{task.problem}", ""]
    for ev in rollout.events:
        if ev.kind == "model_response":
            text = (ev.payload.get("text") or "").strip()
            if not text:
                continue
            parts.append(f"NARRATION:\n{text}\n")
        elif ev.kind == "tool_call" and ev.payload.get("tool") == "python_exec":
            parts.append(f"TOOL CODE:\n{ev.payload['args'].get('code','')}\n")
        elif ev.kind == "tool_result":
            res = ev.payload.get("result", {})
            parts.append(f"TOOL STDOUT:\n{str(res.get('stdout','')).strip()}\n")
        # `final`, `run_start`, `model_call` and `error` events are never rendered:
        # they carry the submission, the pinned config and provider error strings.

    if not blinded:
        parts.append(f"FINAL ANSWER: {submitted}")
        parts.append(f"OUTCOME: {graded_outcome or rollout.outcome}")

    parts.append(TASK_BLOCK)
    prompt = "\n".join(parts)

    audit = _audit(prompt, rollout, submitted, ids, blinded)
    if blinded and audit["hard_leaks"]:
        raise BlindingLeak(
            "blinding failed; these must never reach a blinded judge: "
            + ", ".join(audit["hard_leaks"])
        )
    return prompt, audit


def _audit(prompt: str, rollout: Rollout, submitted: str, ids, blinded: bool) -> dict:
    hard = []
    for ident in ids:
        if re.search(rf"(?<![\w-]){re.escape(str(ident))}(?![\w-])", prompt):
            hard.append(f"identifier:{ident}")
    if blinded:
        for token in ("OUTCOME:", "FINAL ANSWER:", "ANSWER KEY", "config_hash", "usd"):
            if token in prompt:
                hard.append(f"metadata:{token}")
        if REDACTED in prompt:
            # Guards against reintroducing the tell described in the docstring.
            hard.append("redaction_marker_present")

    body = "\n".join(_blocks(prompt, "TOOL STDOUT") + _blocks(prompt, "NARRATION"))
    residual = bool(submitted and re.search(rf"\b{re.escape(submitted)}\b", body))
    return {
        "hard_leaks": hard,
        # NOT a leak of the outcome: the judge can see WHAT was answered, never
        # whether it was right. Reported as a corpus property, not a failure.
        "answer_recoverable_from_tool_output": residual,
        "blinded": blinded,
        "chars": len(prompt),
    }


def _blocks(prompt: str, label: str) -> list[str]:
    out, cur, on = [], [], False
    for line in prompt.splitlines():
        if line.startswith(label + ":"):
            if on:
                out.append("\n".join(cur))
            on, cur = True, []
        elif on and re.match(r"^[A-Z][A-Z ]{2,}:", line):
            out.append("\n".join(cur))
            on, cur = False, []
        elif on:
            cur.append(line)
    if on:
        out.append("\n".join(cur))
    return out


def parse_verdict(raw: str | dict) -> dict:
    """Reject at parse time, not later. No quoted span, no verdict."""
    if isinstance(raw, str):
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            raise VerdictRejected("no JSON object in judge response")
        raw = json.loads(m.group(0))
    verdict = str(raw.get("verdict", "")).strip().upper()
    span = str(raw.get("span", "") or "").strip()
    if verdict not in ANCHORS:
        raise VerdictRejected(f"verdict {verdict!r} is not one of {ANCHORS}")
    if not span:
        raise VerdictRejected("verdict arrived without a non-empty evidence span")
    return {"verdict": verdict, "span": span,
            "justification": str(raw.get("justification", "")).strip()}


def judge(rollout: Rollout, task: Task, judge_provider, *, blinded: bool = True,
          model_names=(), graded_outcome: str | None = None) -> Verdict:
    prompt, audit = render(rollout, task, blinded=blinded, model_names=model_names,
                           graded_outcome=graded_outcome)
    key = f"{rollout.solver_config}|{rollout.task_id}|{rollout.run_idx}|{blinded}"
    if hasattr(judge_provider, "verdict"):          # simulated judge
        raw = judge_provider.verdict(prompt, key)
    else:                                           # real provider
        raw = judge_provider.complete(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}], []
        ).text
    parsed = parse_verdict(raw)
    return Verdict(
        verifier=NAME,
        task_id=rollout.task_id,
        run_idx=rollout.run_idx,
        solver_config=rollout.solver_config,
        label=parsed["verdict"],
        detail={**parsed, **audit},
        judge_model=judge_provider.spec.model,
        blinded=blinded,
    )
