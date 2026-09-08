"""Config pinning.

A number without a pinned model string, prompt hash, temperature and tool set
is not a measurement. `config_hash` covers all four, and every trace file
carries it in its header so any reported figure can be traced to the exact
apparatus that produced it.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from core.miniyaml import load_file

ROOT = Path(__file__).resolve().parent.parent
CONFIGS = ROOT / "configs"

REQUIRED_KEYS = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "xai": "XAI_API_KEY",
    "mock": None,
}

# Names people actually have in their .env. The canonical name above is what the
# provider SDKs read, so an alias is copied into it at startup and announced —
# never silently, because "which variable was this run authenticated with" is
# part of the apparatus.
KEY_ALIASES = {
    "OPENAI_API_KEY": ("OPENAI_TOKEN", "OPENAI_KEY"),
    "GEMINI_API_KEY": ("GEMINI_TOKEN", "GOOGLE_API_KEY", "GEMINI_KEY"),
    "XAI_API_KEY": ("GROK_TOKEN", "XAI_TOKEN", "GROK_API_KEY"),
}

SOLVER_PROMPT = (
    "You are solving a competition mathematics problem.\n"
    "You have two tools: python_exec(code) to compute, and submit_answer(value, reasoning) "
    "to submit.\n"
    "The answer is an integer between 0 and 999.\n"
    "Verify your arithmetic with python_exec before submitting.\n"
    "When you are confident, call submit_answer exactly once and stop."
)


def base_config(solver_config: str) -> str:
    """`S1@high` -> `S1`. Effort arms are separate configurations for the
    purpose of keys and files, but the same rotation entry for judging."""
    return solver_config.split("@", 1)[0]


def effort_of(solver_config: str) -> str | None:
    return solver_config.split("@", 1)[1] if "@" in solver_config else None


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]


# Reasoning effort is part of the pinned apparatus, not a tuning knob you can
# change between runs and still compare the numbers. Kapoor et al. (2025) found
# higher effort REDUCED accuracy in most of their runs, which is only a
# discoverable fact if effort is recorded with every trace.
EFFORTS = ("none", "low", "medium", "high")


@dataclass(frozen=True)
class ModelSpec:
    name: str
    provider: str
    model: str
    temperature: float
    usd_per_1k_in: float
    usd_per_1k_out: float
    reasoning_effort: str | None = None


@dataclass(frozen=True)
class RunConfig:
    solver_config: str
    model: ModelSpec
    prompt: str
    tools: tuple[str, ...]
    max_turns: int
    usd_budget: float

    @property
    def config_hash(self) -> str:
        """Sensitive to model string, prompt, temperature, reasoning effort
        and tool set.

        Change any one of the four and every downstream number is a different
        measurement, so it must be a different hash.
        """
        material = json.dumps(
            {
                "model": self.model.model,
                "temperature": self.model.temperature,
                "prompt_sha": prompt_hash(self.prompt),
                "reasoning_effort": self.model.reasoning_effort,
                "tools": sorted(self.tools),
            },
            sort_keys=True,
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]

    def header(self) -> dict:
        return {
            "solver_config": self.solver_config,
            "model": self.model.model,
            "provider": self.model.provider,
            "temperature": self.model.temperature,
            "reasoning_effort": self.model.reasoning_effort,
            "prompt_sha": prompt_hash(self.prompt),
            "tools": sorted(self.tools),
            "max_turns": self.max_turns,
            "usd_budget": self.usd_budget,
            "config_hash": self.config_hash,
        }


@dataclass
class Registry:
    models: dict[str, ModelSpec] = field(default_factory=dict)
    rotation: dict = field(default_factory=dict)

    @staticmethod
    def load() -> "Registry":
        raw_m = load_file(CONFIGS / "models.yaml")["models"]
        models = {
            name: ModelSpec(
                name=name,
                provider=spec["provider"],
                model=spec["model"],
                temperature=float(spec["temperature"]),
                usd_per_1k_in=float(spec["usd_per_1k_in"]),
                usd_per_1k_out=float(spec["usd_per_1k_out"]),
                reasoning_effort=spec.get("reasoning_effort"),
            )
            for name, spec in raw_m.items()
        }
        return Registry(models=models, rotation=load_file(CONFIGS / "rotation.yaml"))

    def solver(self, solver_config: str, mock: bool = False,
               effort: str | None = None) -> RunConfig:
        rot = self.rotation["configs"][base_config(solver_config)]
        spec = self.models[rot["solver"]]
        if effort is not None:
            if effort not in EFFORTS:
                raise ValueError(f"reasoning effort {effort!r} not in {EFFORTS}")
            spec = dataclasses.replace(spec, reasoning_effort=effort)
            # An effort sweep runs the same solver on the same tasks, so the
            # rollout key must distinguish the arms or resumption will skip
            # every arm after the first and the study will quietly not happen.
            solver_config = f"{base_config(solver_config)}@{effort}"
        if mock:
            # Stand in for the real solver, keeping its price list so cost
            # metrics are exercised, but under a name nobody can mistake for a
            # real run. Traces from this path are marked simulated: true.
            spec = ModelSpec(
                name=f"mock-solver-{solver_config}",
                provider="mock",
                model=f"mock-solver-{solver_config}",
                temperature=spec.temperature,
                usd_per_1k_in=spec.usd_per_1k_in,
                usd_per_1k_out=spec.usd_per_1k_out,
                reasoning_effort=spec.reasoning_effort,
            )
        return RunConfig(
            solver_config=solver_config,
            model=spec,
            prompt=SOLVER_PROMPT,
            tools=("python_exec", "submit_answer"),
            max_turns=int(self.rotation["max_turns"]),
            usd_budget=float(self.rotation["usd_budget_per_rollout"]),
        )

    def judges(self, solver_config: str, mock: bool = False) -> list[ModelSpec]:
        names = self.rotation["configs"][base_config(solver_config)]["judges"]
        if mock:
            # Two distinguishable simulated judges, so inter-judge agreement is
            # still a real computation over two differing verdict streams.
            return [
                ModelSpec(f"mock-judge-of-{n}", "mock", f"mock-judge-of-{n}",
                          0.0, self.models[n].usd_per_1k_in, self.models[n].usd_per_1k_out)
                for n in names
            ]
        return [self.models[n] for n in names]


class MissingKey(RuntimeError):
    pass


def resolve_aliases(verbose: bool = True) -> list[str]:
    """Copy a recognised alias into the canonical variable the SDKs read.

    Returns the substitutions made, so the caller can print them. Silence here
    would be the wrong kind of convenience: which variable authenticated a run
    is part of knowing what the run was.
    """
    notes = []
    for canonical, aliases in KEY_ALIASES.items():
        if os.environ.get(canonical):
            continue
        for alt in aliases:
            if os.environ.get(alt):
                os.environ[canonical] = os.environ[alt]
                notes.append(f"{alt} -> {canonical}")
                break
    if notes and verbose:
        for n in notes:
            print(f"\033[2m  using {n}\033[0m")
    return notes


def validate_env(providers: list[str]) -> None:
    """Fail fast, naming the missing variable. Never proceed half-configured."""
    resolve_aliases()
    missing = []
    for p in providers:
        var = REQUIRED_KEYS.get(p)
        if var and not os.environ.get(var):
            alts = ", ".join(KEY_ALIASES.get(var, ()))
            hint = f"  [also accepted: {alts}]" if alts else ""
            missing.append(f"{var} (provider: {p}){hint}")
    if missing:
        raise MissingKey(
            "Missing required environment variable(s):\n  - "
            + "\n  - ".join(missing)
            + "\n\nCopy .env.example to .env and fill them in, or pass --mock to run "
            "the offline harness with no provider calls."
        )


def load_dotenv(path: Path | None = None) -> None:
    path = path or (ROOT / ".env")
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
