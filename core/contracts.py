"""Data contracts shared by every layer.

Nothing here refers to mathematics. The maths plugin supplies a Task and an
answer key; the runner, the verifiers and the metrics layer never learn what
domain they are measuring.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Protocol, runtime_checkable

# The seven outcomes. Three describe the agent, two describe a boundary we set,
# two describe the apparatus failing. Collapsing these to a boolean is a false
# statement about the agent.
OUTCOMES = (
    "correct",
    "incorrect",
    "refused",
    "max_turns",
    "budget_exceeded",
    "error",
    "timeout",
)
AGENT_OUTCOMES = ("correct", "incorrect", "refused")
HARNESS_STOPS = ("max_turns", "budget_exceeded")
HARNESS_FAILURES = ("error", "timeout")

EVENT_KINDS = (
    "run_start",
    "model_call",
    "model_response",
    "tool_call",
    "tool_result",
    "final",
    "error",
)


@dataclass
class Event:
    t: float
    kind: str
    payload: dict

    def to_dict(self) -> dict:
        return {"t": round(self.t, 6), "kind": self.kind, "payload": self.payload}

    @staticmethod
    def from_dict(d: dict) -> "Event":
        return Event(t=float(d["t"]), kind=str(d["kind"]), payload=dict(d["payload"]))


@dataclass
class Task:
    """What the agent sees. There is deliberately no `answer` field.

    The answer key is loaded separately, by verifiers only, so the agent code
    path physically cannot reach it.
    """

    task_id: str
    problem: str

    def to_dict(self) -> dict:
        return {"task_id": self.task_id, "problem": self.problem}


@dataclass
class Rollout:
    task_id: str
    run_idx: int
    solver_config: str
    seed: int | None
    config_hash: str
    events: list[Event] = field(default_factory=list)
    final: Any = None
    outcome: str = "error"
    usage: dict = field(default_factory=dict)

    @property
    def key(self) -> tuple[str, str, int]:
        return (self.solver_config, self.task_id, self.run_idx)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "run_idx": self.run_idx,
            "solver_config": self.solver_config,
            "seed": self.seed,
            "config_hash": self.config_hash,
            "events": [e.to_dict() for e in self.events],
            "final": self.final,
            "outcome": self.outcome,
            "usage": self.usage,
        }

    @staticmethod
    def from_dict(d: dict) -> "Rollout":
        return Rollout(
            task_id=d["task_id"],
            run_idx=int(d["run_idx"]),
            solver_config=d["solver_config"],
            seed=d.get("seed"),
            config_hash=d["config_hash"],
            events=[Event.from_dict(e) for e in d.get("events", [])],
            final=d.get("final"),
            outcome=d.get("outcome", "error"),
            usage=dict(d.get("usage", {})),
        )


@dataclass
class Verdict:
    """One verifier's opinion about one rollout. Append-only, never edited."""

    verifier: str
    task_id: str
    run_idx: int
    solver_config: str
    label: str
    detail: dict = field(default_factory=dict)
    judge_model: str | None = None
    blinded: bool | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Verdict":
        return Verdict(**d)


@runtime_checkable
class Agent(Protocol):
    def run(self, task: Task, ctx: Any) -> Rollout: ...


@runtime_checkable
class Verifier(Protocol):
    name: str

    def verify(self, rollout: Rollout, task: Task) -> Verdict: ...
