"""The tool registry. Two tools, and schemas generated from the signatures.

`submit_answer` is a tool rather than a parse of the final message for two
reasons. It yields a clean parse — and, more importantly, it records what the
model *claims* its reasoning was, separately from the trace of what it
actually did. The gap between those two is the entire Session 2 demo.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable

from agent.sandbox import run_python
from core.budget import Budget

_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean"}


@dataclass
class Tool:
    name: str
    fn: Callable
    description: str

    def schema(self) -> dict:
        """Generated from the signature, so the schema cannot drift from the code."""
        sig = inspect.signature(self.fn)
        props, required = {}, []
        for pname, p in sig.parameters.items():
            if pname in ("budget", "_ctx"):
                continue
            props[pname] = {"type": _JSON_TYPES.get(p.annotation, "string")}
            if p.default is inspect.Parameter.empty:
                required.append(pname)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": props, "required": required},
            },
        }


class SubmitAnswer(Exception):
    """Control flow, not an error: the agent has finished."""

    def __init__(self, value: Any, reasoning: str):
        super().__init__(str(value))
        self.value, self.reasoning = value, reasoning


def python_exec(code: str, budget: Budget) -> dict:
    # The boundary. Checked before the call runs, not after, and not by asking
    # the model nicely in the system prompt.
    budget.check("tool")
    budget.tool_calls += 1
    return run_python(code).to_dict()


def submit_answer(value: str, reasoning: str) -> None:
    raise SubmitAnswer(value, reasoning)


REGISTRY: dict[str, Tool] = {
    "python_exec": Tool(
        "python_exec",
        python_exec,
        "Execute Python in a sandbox with no network access. Returns stdout, stderr, returncode.",
    ),
    "submit_answer": Tool(
        "submit_answer",
        submit_answer,
        "Submit the final integer answer together with the reasoning that supports it.",
    ),
}


def schemas(names) -> list[dict]:
    return [REGISTRY[n].schema() for n in names]


def call(name: str, args: dict, budget: Budget):
    if name not in REGISTRY:
        raise KeyError(f"unknown tool: {name}")
    fn = REGISTRY[name].fn
    kwargs = dict(args)
    if "budget" in inspect.signature(fn).parameters:
        kwargs["budget"] = budget
    return fn(**kwargs)
