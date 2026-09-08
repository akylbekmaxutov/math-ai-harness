"""Thin provider adapters behind one interface, plus an offline simulator.

The loop below providers is model-agnostic: it sees `complete(messages, tools)`
and a `Completion`, and nothing else. Swapping a solver is a config change,
which is why "two judges from different families" is a list in a YAML file
rather than new code.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
from dataclasses import dataclass, field
from typing import Protocol

from core.config import ModelSpec


class ProviderError(RuntimeError):
    """The apparatus failed. Not an agent failure."""


class ProviderTimeout(ProviderError):
    pass


@dataclass
class Completion:
    text: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0


class Provider(Protocol):
    spec: ModelSpec

    def complete(self, messages: list[dict], tools: list[dict]) -> Completion: ...


def usd(spec: ModelSpec, tin: int, tout: int) -> float:
    return (tin / 1000) * spec.usd_per_1k_in + (tout / 1000) * spec.usd_per_1k_out


# --------------------------------------------------------------------------
# Real providers. Imported lazily so an unconfigured laptop can still run the
# offline demo; a missing SDK is reported by name rather than as an ImportError
# three frames deep.
# --------------------------------------------------------------------------
class _OpenAICompatible:
    """OpenAI and xAI both speak the chat-completions dialect."""

    base_url: str | None = None
    key_var = "OPENAI_API_KEY"

    def __init__(self, spec: ModelSpec):
        self.spec = spec
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ProviderError(
                f"provider '{spec.provider}' needs the `openai` package: uv add openai"
            ) from e
        self._client = OpenAI(api_key=os.environ[self.key_var], base_url=self.base_url)

    def complete(self, messages, tools):
        kw = {}
        if self.spec.reasoning_effort:
            # Sent as a first-class parameter, and recorded in the pinned
            # config, so two runs at different effort are never compared as
            # though they were the same apparatus.
            kw["reasoning_effort"] = self.spec.reasoning_effort
        try:
            r = self._client.chat.completions.create(
                model=self.spec.model,
                messages=messages,
                tools=tools or None,
                temperature=self.spec.temperature,
                timeout=90,
                **kw,
            )
        except Exception as e:  # noqa: BLE001 - provider faults are harness failures
            if "timeout" in str(e).lower():
                raise ProviderTimeout(str(e)) from e
            raise ProviderError(str(e)) from e
        msg = r.choices[0].message
        calls = [
            {"name": c.function.name, "args": json.loads(c.function.arguments or "{}")}
            for c in (msg.tool_calls or [])
        ]
        u = r.usage
        return Completion(msg.content or "", calls, u.prompt_tokens, u.completion_tokens)


class OpenAIProvider(_OpenAICompatible):
    key_var = "OPENAI_API_KEY"


class XAIProvider(_OpenAICompatible):
    base_url = "https://api.x.ai/v1"
    key_var = "XAI_API_KEY"


class GeminiProvider:
    def __init__(self, spec: ModelSpec):
        self.spec = spec
        try:
            from google import genai
        except ImportError as e:
            raise ProviderError(
                "provider 'gemini' needs the `google-genai` package: uv add google-genai"
            ) from e
        self._genai = genai
        self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def complete(self, messages, tools):
        sys_txt = "\n".join(m["content"] for m in messages if m["role"] == "system")
        contents = [
            {"role": "user" if m["role"] != "assistant" else "model",
             "parts": [{"text": str(m.get("content") or "")}]}
            for m in messages if m["role"] != "system"
        ]
        decls = [t["function"] for t in tools] if tools else None
        try:
            r = self._client.models.generate_content(
                model=self.spec.model,
                contents=contents,
                config={
                    "system_instruction": sys_txt,
                    "temperature": self.spec.temperature,
                    "tools": [{"function_declarations": decls}] if decls else None,
                    # Gemini expresses effort as a thinking budget rather than a
                    # named level, so the harness maps its four levels onto it.
                    "thinking_config": _THINKING.get(self.spec.reasoning_effort),
                },
            )
        except Exception as e:  # noqa: BLE001
            if "timeout" in str(e).lower() or "deadline" in str(e).lower():
                raise ProviderTimeout(str(e)) from e
            raise ProviderError(str(e)) from e
        calls, text = [], ""
        for part in (r.candidates[0].content.parts or []):
            if getattr(part, "function_call", None):
                calls.append({"name": part.function_call.name,
                              "args": dict(part.function_call.args or {})})
            elif getattr(part, "text", None):
                text += part.text
        m = r.usage_metadata
        return Completion(text, calls, m.prompt_token_count, m.candidates_token_count)


# --------------------------------------------------------------------------
# The offline simulator.
#
# This is a TRACE GENERATOR, not an agent. It exists so that the workshop has
# a corpus to grade with no keys and no network, and so a rehearsal on a plane
# is identical to the real thing except for where the bytes came from. It is
# given the answer key, which no real solver ever is; anything it produces is
# labelled `simulated: true` in the trace header and every report built from
# such a corpus carries a banner saying so.
# --------------------------------------------------------------------------
# Gemini expresses reasoning effort as a token budget.
_THINKING = {"none": {"thinking_budget": 0}, "low": {"thinking_budget": 1024},
             "medium": {"thinking_budget": 4096}, "high": {"thinking_budget": 16384}}

SKILL = {"S1": 0.72, "S2": 0.55, "S3": 0.64}

# What the simulator pretends reasoning effort buys. Note that "high" is NOT
# uniformly better: Kapoor et al. (2025) found higher effort reduced accuracy in
# most of their runs, and a simulator that hides that would teach the wrong
# lesson before the real sweep is ever run.
EFFORT_SKILL = {"none": -0.18, "low": -0.07, "medium": 0.0, "high": +0.03}
EFFORT_TOKENS = {"none": 0.6, "low": 0.85, "medium": 1.0, "high": 2.4}
FLAW_RATE = 0.22   # of correct answers, the share reached by unsound reasoning
ERR_RATE = 0.04    # provider errors  -> outcome `error`
TIMEOUT_RATE = 0.03
LOOP_RATE = 0.03   # never submits    -> outcome `max_turns`
REFUSE_RATE = 0.02


def _rng(*parts) -> random.Random:
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return random.Random(int(h[:16], 16))


# Real solutions to the shipped problem set, each with a subtly buggy variant.
# The simulator picks which one to run; the sandbox decides what it prints; the
# verifier decides downstream whether that was right. Note that the simulator
# therefore never needs the answer key to produce a wrong run — it only needs a
# worse program, which is closer to how a solver actually fails.
SOLUTIONS = {
    "aime2026-03": (
        "print(len([n for n in range(1,1001) if n%7==0 and n%11!=0]))",
        "print(len([n for n in range(1,1001) if n%7==0]))"),
    "aime2026-07": (
        "print(sum(n for n in range(1,500) if n%7==3)%1000)",
        "print(sum(n for n in range(1,501) if n%7==3)%1000)"),
    "aime2026-09": (
        "N=2**5*3**3\nprint(len([d for d in range(1,N+1) if N%d==0 and d*d<N]))",
        "N=2**5*3**2\nprint(len([d for d in range(1,N+1) if N%d==0 and d*d<N]))"),
    "aime2026-12": (
        "print(len([p for p in range(1000,10000) if str(p)==str(p)[::-1] and p%3==0]))",
        "print(len([p for p in range(1000,9999) if str(p)==str(p)[::-1] and p%3==0]))"),
    "aime2026-16": ("print(pow(7,2026,1000))", "print(pow(7,2025,1000))"),
    "aime2026-19": (
        "from itertools import combinations\n"
        "print(sum(1 for r in range(1,13) for c in combinations(range(1,13),r)"
        " if sum(c)%13==0)%1000)",
        "from itertools import combinations\n"
        "print(sum(1 for r in range(0,13) for c in combinations(range(1,13),r)"
        " if sum(c)%13==0)%1000)"),
    "aime2026-24": (
        "from math import comb, factorial\nprint((comb(6,3)**2*factorial(3))%1000)",
        "from math import comb, factorial\nprint((comb(6,3)*factorial(3))%1000)"),
    "aime2026-28": (
        "def p(x):\n    return x>1 and all(x%i for i in range(2,int(x**0.5)+1))\n"
        "print(max(k*k for k in range(1,32) if k*k<1000 and p(k*k+1)))",
        "def p(x):\n    return x>1 and all(x%i for i in range(2,int(x**0.5)+1))\n"
        "print(max(k*k for k in range(1,32) if k*k<1000 and p(k*k-1)))"),
}

FALLBACK = ("print(sum(range(1,50)))", "print(sum(range(1,49)))")


class MockSolver:
    """Deterministic given (solver_config, task_id, run_idx).

    It chooses a script, then runs either the good or the buggy program for the
    task. It is not told whether it got the answer right and does not compute
    that; correctness is assigned downstream by verifiers/answer_match.py from
    the trace, exactly as it is for a real solver.
    """

    def __init__(self, spec: ModelSpec, solver_config: str, task_id: str, run_idx: int,
                 answer: int | None = None):
        self.spec = spec
        self.task_id = task_id
        self.rng = _rng(solver_config, task_id, run_idx)
        self.turn = 0
        self.effort = spec.reasoning_effort or "medium"
        skill = min(0.95, max(0.05, SKILL.get(solver_config, 0.6)
                              + EFFORT_SKILL.get(self.effort, 0.0)))
        r = self.rng.random()
        if r < ERR_RATE:
            self.script = "error"
        elif r < ERR_RATE + TIMEOUT_RATE:
            self.script = "timeout"
        elif r < ERR_RATE + TIMEOUT_RATE + LOOP_RATE:
            self.script = "loop"
        elif r < ERR_RATE + TIMEOUT_RATE + LOOP_RATE + REFUSE_RATE:
            self.script = "refuse"
        elif self.rng.random() < skill:
            self.script = "flawed" if self.rng.random() < FLAW_RATE else "sound"
        else:
            self.script = "wrong"

    @property
    def code(self) -> str:
        good, bad = SOLUTIONS.get(self.task_id, FALLBACK)
        return bad if self.script == "wrong" else good

    def complete(self, messages, tools):
        self.turn += 1
        if self.script == "error" and self.turn == 1:
            raise ProviderError("simulated 503 from provider")
        if self.script == "timeout" and self.turn == 1:
            raise ProviderTimeout("simulated read timeout after 90s")
        if self.script == "refuse":
            return Completion("I am not able to work on this problem.", [], 900, 40)
        if self.turn == 1 or self.script == "loop":
            return Completion(
                "Let me compute this directly rather than reason about it in my head.",
                [{"name": "python_exec", "args": {"code": self.code}}],
                1100, int(120 * EFFORT_TOKENS.get(self.effort, 1.0)),
            )

        # Turn 2: narrate what the tool produced, then submit it.
        printed = _last_stdout(messages)
        value = printed if printed.isdigit() else "0"
        if self.script == "flawed":
            # The narration asserts a value the tool did not print, yet the
            # submission is the tool's value. Right answer, wrong reasoning —
            # the case beat 4 locates by grading stored runs offline.
            claimed = int(value) + 7
            reasoning = (
                f"The computation gives {claimed}, and since each candidate is counted "
                f"exactly once, that is the required total."
            )
        else:
            reasoning = (
                f"The computation gives {value}; this counts each case exactly once, "
                f"so it is the required total."
            )
        return Completion(
            reasoning,
            [{"name": "submit_answer", "args": {"value": value, "reasoning": reasoning}}],
            1400, int(160 * EFFORT_TOKENS.get(self.effort, 1.0)),
        )


def _last_stdout(messages) -> str:
    for m in reversed(messages):
        if m.get("role") == "tool":
            try:
                return str(json.loads(m["content"]).get("stdout", "")).strip()
            except Exception:  # noqa: BLE001
                return ""
    return ""


_NUM = re.compile(r"-?\d+")


class MockJudge:
    """Simulates a process judge, including its biases.

    It reads the same blinded prompt a real judge gets and looks for a genuine
    signal in it: does the narrated value match what the tool actually printed?
    On top of that it carries a severity and a noise rate so the two judges
    disagree at a realistic rate, and — when the prompt is UNBLINDED — it is
    pulled toward ESTABLISHES by the visible outcome. That last behaviour is
    the simulated form of outcome leakage.
    """

    def __init__(self, spec: ModelSpec, severity: float = 0.5, noise: float = 0.12,
                 leak: float = 0.55):
        self.spec, self.severity, self.noise, self.leak = spec, severity, noise, leak

    def verdict(self, prompt: str, key: str) -> dict:
        rng = _rng(self.spec.model, key)
        tool_vals = _NUM.findall(_section(prompt, "TOOL STDOUT"))
        claim_vals = _NUM.findall(_section(prompt, "NARRATION"))
        contradiction = bool(tool_vals and claim_vals and tool_vals[-1] != claim_vals[0])

        unblinded = "FINAL ANSWER:" in prompt or "OUTCOME:" in prompt
        outcome_correct = "OUTCOME: correct" in prompt

        v = "ERROR" if contradiction else "ESTABLISHES"
        if rng.random() < self.noise:
            v = rng.choice(["ESTABLISHES", "INCOMPLETE", "ERROR", "INDETERMINATE"])
        elif not contradiction and rng.random() < self.severity * 0.25:
            v = "INCOMPLETE"
        if unblinded and outcome_correct and v != "ESTABLISHES" and rng.random() < self.leak:
            v = "ESTABLISHES"          # rationalising a flaw because the answer was right

        span = (_section(prompt, "NARRATION").strip().splitlines() or ["(no narration)"])[0][:180]
        return {
            "verdict": v,
            "span": span,
            "justification": (
                "The narrated value does not match the value the tool produced."
                if contradiction else
                "Each step follows from the previous one and the computation is verified."
            ),
        }


def _section(prompt: str, label: str) -> str:
    out, on = [], False
    for line in prompt.splitlines():
        if line.startswith(label):
            on = True
            out.append(line[len(label):].lstrip(": "))
        elif on and re.match(r"^[A-Z][A-Z ]{2,}:", line):
            break
        elif on:
            out.append(line)
    return "\n".join(out)


def build(spec: ModelSpec, **mock_kwargs):
    if spec.provider == "mock":
        return MockSolver(spec, **mock_kwargs)
    return {"openai": OpenAIProvider, "gemini": GeminiProvider, "xai": XAIProvider}[
        spec.provider
    ](spec)
