"""OpenAI adapter — /v1/responses.

Reasoning models are asked for effort by name, which maps one-to-one onto the
harness's three levels, so this is the simplest of the three translations.

Two details are worth pointing at during the workshop:

`summary="auto"` asks the API for a summary of the reasoning. What comes back
is a summary the model wrote, returned in a field the API labels as reasoning.
It is not the raw chain of thought, and this adapter does not pretend otherwise
— it sets `reasoning_exposure="summary"` and the website says exactly that.

`reasoning_tokens` arrives inside `output_tokens_details`. They are already
counted in `output_tokens`, which is the convention harness/pricing.py assumes,
so nothing is added here.
"""
from __future__ import annotations

import os

from harness.reasoning import ReasoningMode
from providers.base import BaseAdapter, ProviderError, ProviderResponse, ProviderTimeout

#: OpenAI takes the level by name, so the map is the identity. It is written
#: out anyway: the day a level is renamed on their side, the change belongs in
#: this dict and not in a string concatenation somewhere else.
EFFORT = {
    ReasoningMode.LOW: "low",
    ReasoningMode.MEDIUM: "medium",
    ReasoningMode.HIGH: "high",
}


class OpenAIAdapter(BaseAdapter):
    name = "openai"
    supported_reasoning = (ReasoningMode.LOW, ReasoningMode.MEDIUM, ReasoningMode.HIGH)

    def __init__(self, model: str, timeout: int = 180):
        self.model, self.timeout = model, timeout
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ProviderError("provider 'openai' needs the `openai` package: "
                                "pip install -r requirements.txt") from e
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ProviderError("OPENAI_API_KEY is not set — see .env.example")
        self._client = OpenAI(api_key=key)

    def generate(self, prompt, *, system, reasoning_mode, max_output_tokens=4096):
        self.require_supported(reasoning_mode)
        req = {"effort": EFFORT[reasoning_mode], "summary": "auto"}
        try:
            r = self._client.responses.create(
                model=self.model,
                instructions=system,
                input=prompt,
                reasoning=req,
                max_output_tokens=max_output_tokens,
                timeout=self.timeout,
            )
        except Exception as e:  # noqa: BLE001 — a provider fault is a harness fault
            if "timeout" in str(e).lower():
                raise ProviderTimeout(str(e)) from e
            raise ProviderError(str(e)) from e

        summary = _reasoning_summary(r)
        u = r.usage
        details = getattr(u, "output_tokens_details", None)
        rtok = getattr(details, "reasoning_tokens", None) if details else None
        return ProviderResponse(
            text=r.output_text or "",
            reasoning_summary=summary,
            # Token counts alone are still information; saying so is the point.
            reasoning_exposure="summary" if summary else "token_count_only",
            input_tokens=int(u.input_tokens),
            output_tokens=int(u.output_tokens),      # reasoning tokens included
            reasoning_tokens=int(rtok) if rtok is not None else None,
            reasoning_request={"reasoning": req},
            raw_meta={"response_id": getattr(r, "id", None),
                      "status": getattr(r, "status", None),
                      # "incomplete" plus reason "max_output_tokens" is the
                      # authoritative truncation signal here, not a token count.
                      "incomplete_reason": getattr(
                          getattr(r, "incomplete_details", None), "reason", None),
                      "api": "responses"},
        )


def _reasoning_summary(response) -> str | None:
    """Collect the summary parts of any `reasoning` output items.

    Returns None — not "" — when the API returned no summary, so that
    "the provider gave us nothing" stays distinguishable from
    "the provider gave us an empty summary".
    """
    chunks = []
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) != "reasoning":
            continue
        for part in getattr(item, "summary", []) or []:
            txt = getattr(part, "text", None)
            if txt:
                chunks.append(txt)
    return "\n\n".join(chunks) or None
