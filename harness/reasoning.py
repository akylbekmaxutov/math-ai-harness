"""Reasoning modes, as one internal vocabulary the whole harness speaks.

The harness asks for LOW, MEDIUM or HIGH. Nothing above the provider adapters
knows that OpenAI takes a named effort, that Gemini takes a token budget, or
that xAI accepts only two of the three levels — that translation is the
adapter's job and lives nowhere else.

The rule this module exists to enforce: a mode a provider does not offer is
recorded as UNSUPPORTED and the run is not made up. Silently substituting the
provider default would put a row in the results table that claims to be a
`medium` measurement and is not.
"""
from __future__ import annotations

from enum import Enum


class ReasoningMode(str, Enum):
    """The three levels the experiment is designed around."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @classmethod
    def parse(cls, raw: str) -> "ReasoningMode":
        try:
            return cls(str(raw).strip().lower())
        except ValueError as e:
            opts = ", ".join(m.value for m in cls)
            raise ValueError(f"unknown reasoning mode {raw!r}; expected one of: {opts}") from e


#: What a provider returns when the harness asks for a mode it does not expose.
#: A sentinel rather than None, because None reads as "no reasoning requested"
#: and that is a different — and legitimate — thing.
UNSUPPORTED = "unsupported"


class UnsupportedReasoningMode(Exception):
    """Raised by an adapter asked for a mode its provider does not expose.

    Caught by the runner, which writes a row marked `unsupported` instead of
    quietly falling back to the provider default and mislabelling the arm.
    """

    def __init__(self, provider: str, model: str, mode: ReasoningMode, supported):
        self.provider, self.model, self.mode = provider, model, mode
        self.supported = tuple(supported)
        have = ", ".join(m.value for m in self.supported) or "none"
        super().__init__(
            f"{provider}/{model} does not expose reasoning mode {mode.value!r} "
            f"(it exposes: {have})"
        )
