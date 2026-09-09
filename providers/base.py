"""The common interface every adapter implements, and the honest accounting of
what each provider actually gives back.

The rest of the harness calls exactly one method:

    response = adapter.generate(prompt, reasoning_mode=ReasoningMode.HIGH)

and receives exactly one shape, `ProviderResponse`. Three different APIs sit
under that line. Nothing above it contains the word "openai".

The field that matters most here is `reasoning_exposure`. There are three
genuinely different situations and collapsing them is the mistake this
workshop is partly about:

    "summary"           the provider returned a reasoning summary it generated
                        for us. It is a description of the reasoning, produced
                        by the model. It is not the hidden chain of thought.
    "token_count_only"  we know how many reasoning tokens were billed and
                        nothing whatsoever about their content.
    "none"              the provider exposes neither.

No adapter is permitted to put model prose into `reasoning_summary` and call it
a reasoning trace. If the API did not label it as such, it is `response_text`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from harness.reasoning import ReasoningMode, UnsupportedReasoningMode

#: The three honest answers to "what reasoning information do we have?"
REASONING_EXPOSURE = ("summary", "token_count_only", "none")


class ProviderError(RuntimeError):
    """The apparatus failed. This is not the model being wrong."""


class ProviderTimeout(ProviderError):
    pass


@dataclass
class ProviderResponse:
    """One completed call, normalised. Every adapter returns this and only this."""

    text: str = ""
    #: Reasoning information the API explicitly labelled as such. Never prose
    #: we decided looked like reasoning.
    reasoning_summary: str | None = None
    reasoning_exposure: str = "none"
    input_tokens: int = 0
    #: Includes reasoning tokens where the provider counts them there. Adapters
    #: normalise to that convention so harness/pricing.py never double-charges.
    output_tokens: int = 0
    reasoning_tokens: int | None = None
    #: What the adapter actually put on the wire for the reasoning control, so
    #: the trace records the request rather than our intention.
    reasoning_request: dict = field(default_factory=dict)
    raw_meta: dict = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return int(self.input_tokens) + int(self.output_tokens)


class Provider(Protocol):
    """The whole contract. Three methods' worth of surface, deliberately."""

    name: str
    model: str
    supported_reasoning: tuple[ReasoningMode, ...]

    def generate(self, prompt: str, *, system: str, reasoning_mode: ReasoningMode,
                 max_output_tokens: int) -> ProviderResponse: ...


class BaseAdapter:
    """Shared bookkeeping: the support check, and nothing else.

    Subclasses declare `supported_reasoning` and translate. This base class
    refuses, on their behalf, to answer a question the provider cannot answer.
    """

    name: str = "base"
    model: str = ""
    supported_reasoning: tuple[ReasoningMode, ...] = ()

    def supports(self, mode: ReasoningMode) -> bool:
        return mode in self.supported_reasoning

    def require_supported(self, mode: ReasoningMode) -> None:
        """The single line that keeps an unavailable arm out of the results.

        Called by every adapter before it builds a request. Raising here is what
        produces a row marked `unsupported` instead of a row that claims to be a
        `medium` measurement and is really the provider default.
        """
        if not self.supports(mode):
            raise UnsupportedReasoningMode(self.name, self.model, mode, self.supported_reasoning)


def build(provider: str, model: str, **kw):
    """Name -> adapter instance. Imported lazily so a laptop with no SDK
    installed and no network can still run the whole workshop with --mock."""
    if provider == "openai":
        from providers.openai_adapter import OpenAIAdapter
        return OpenAIAdapter(model, **kw)
    if provider == "gemini":
        from providers.gemini_adapter import GeminiAdapter
        return GeminiAdapter(model, **kw)
    if provider == "xai":
        from providers.xai_adapter import XAIAdapter
        return XAIAdapter(model, **kw)
    if provider == "mock":
        from providers.mock_adapter import MockAdapter
        return MockAdapter(model, **kw)
    raise ProviderError(f"unknown provider {provider!r}")
