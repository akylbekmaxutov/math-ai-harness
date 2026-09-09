"""The model registry, and the capability matrix derived from it.

Two things live here.

`MODELS` pins what is being measured: the exact model string, the provider that
serves it, the display name for the website. A rename must be a change to this
file, never a silent substitution somewhere in a call site.

`capability_matrix()` answers "which (model, reasoning mode) cells actually
exist?" — and answers it by reading `supported_reasoning` off the adapter
classes themselves, so the grid the website draws cannot disagree with what the
adapters will do. Adapter modules import their SDK inside `__init__`, so this
works with no packages installed, no API keys, and no network.
"""
from __future__ import annotations

from dataclasses import dataclass

from harness.pricing import MODEL_PRICING
from harness.reasoning import ReasoningMode
from providers.gemini_adapter import GeminiAdapter
from providers.mock_adapter import MockAdapter
from providers.openai_adapter import OpenAIAdapter
from providers.xai_adapter import XAIAdapter

ADAPTERS = {
    "openai": OpenAIAdapter,
    "gemini": GeminiAdapter,
    "xai": XAIAdapter,
    "mock": MockAdapter,
}


@dataclass(frozen=True)
class ModelSpec:
    key: str            # what you type on the command line
    display: str        # what the website prints
    provider: str
    model: str          # the exact string that goes on the wire
    family: str         # used by the judge rotation: a model never judges its own family


MODELS = {
    "gpt-5.6-terra": ModelSpec("gpt-5.6-terra", "GPT-5.6-Terra", "openai",
                               "gpt-5.6-terra", "openai"),
    "gemini-3.8-flash": ModelSpec("gemini-3.8-flash", "Gemini-3.8-Flash", "gemini",
                                  "gemini-3.8-flash", "google"),
    "grok-4.6": ModelSpec("grok-4.6", "Grok 4.6", "xai", "grok-4.6", "xai"),
}

#: The three models under study, in the order the website shows them.
SOLVERS = tuple(MODELS)


def get(model_key: str) -> ModelSpec:
    if model_key not in MODELS:
        raise KeyError(f"unknown model {model_key!r}. Known: {', '.join(MODELS)}")
    return MODELS[model_key]


def supported_modes(model_key: str) -> tuple[ReasoningMode, ...]:
    """The reasoning modes this model's provider actually exposes.

    Read from the adapter class, which is also what will refuse the call. One
    source of truth, so the grid on screen and the runtime behaviour cannot
    drift apart.
    """
    return tuple(ADAPTERS[get(model_key).provider].supported_reasoning)


def capability_matrix() -> dict:
    """`{model_key: {mode: True|False}}` for every model and all three modes.

    This is what the website's experiment grid is drawn from, and it is why the
    Grok/medium cell is a hole rather than a number.
    """
    return {
        key: {m.value: m in supported_modes(key) for m in ReasoningMode}
        for key in MODELS
    }


def build_adapter(model_key: str, *, mock: bool = False, timeout: int = 180):
    """Model key -> a live adapter. `mock=True` swaps in the offline simulator
    while keeping the model key, so a rehearsal exercises the same code path."""
    spec = get(model_key)
    if mock:
        return MockAdapter("mock-model", timeout=timeout, label=spec.key)
    return ADAPTERS[spec.provider](spec.model, timeout=timeout)


def pricing_for(model_key: str) -> dict:
    return MODEL_PRICING["mock-model" if model_key not in MODEL_PRICING else model_key]
