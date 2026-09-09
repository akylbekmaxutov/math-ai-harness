"""Gemini adapter — google-genai.

The most interesting translation of the three, because Gemini does not take a
named effort at all. It takes a *thinking budget*: a token allowance. The
harness's three levels are therefore mapped onto three budgets, and that
mapping is a decision this workshop makes, not a fact about the API.

Say that out loud during the talk. `HIGH` means "16k thinking tokens allowed"
here and "effort=high" on OpenAI, and those are not the same quantity. The
harness makes the arms comparable by *naming* them consistently; it cannot make
them physically identical, and pretending otherwise is how cross-provider
comparisons quietly become meaningless. The budget actually sent travels into
every stored result as `reasoning_request` so a reader can check what was asked
for rather than trusting the label.

`include_thoughts=True` asks for thought summaries. What comes back is again a
summary the model produced, not its internal state.
"""
from __future__ import annotations

import os

from harness.reasoning import ReasoningMode
from providers.base import BaseAdapter, ProviderError, ProviderResponse, ProviderTimeout

#: Level -> thinking-token budget. A workshop decision, documented as one.
THINKING_BUDGET = {
    ReasoningMode.LOW: 512,
    ReasoningMode.MEDIUM: 4096,
    ReasoningMode.HIGH: 16384,
}


class GeminiAdapter(BaseAdapter):
    name = "gemini"
    supported_reasoning = (ReasoningMode.LOW, ReasoningMode.MEDIUM, ReasoningMode.HIGH)

    def __init__(self, model: str, timeout: int = 180):
        self.model, self.timeout = model, timeout
        try:
            from google import genai
        except ImportError as e:
            raise ProviderError("provider 'gemini' needs the `google-genai` package: "
                                "pip install -r requirements.txt") from e
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ProviderError("GEMINI_API_KEY is not set — see .env.example")
        self._client = genai.Client(api_key=key)

    def generate(self, prompt, *, system, reasoning_mode, max_output_tokens=4096):
        self.require_supported(reasoning_mode)
        budget = THINKING_BUDGET[reasoning_mode]
        req = {"thinking_budget": budget, "include_thoughts": True}
        cfg = {
            "system_instruction": system,
            "max_output_tokens": max_output_tokens,
            "thinking_config": req,
        }
        try:
            r = self._client.models.generate_content(
                model=self.model, contents=prompt, config=cfg,
            )
        except Exception as e:  # noqa: BLE001
            low = str(e).lower()
            if "timeout" in low or "deadline" in low:
                raise ProviderTimeout(str(e)) from e
            raise ProviderError(str(e)) from e

        text, thoughts = _split_parts(r)
        m = r.usage_metadata
        thinking = getattr(m, "thoughts_token_count", None)
        answer_tokens = int(getattr(m, "candidates_token_count", 0) or 0)
        # google-genai reports thinking tokens SEPARATELY from candidate tokens.
        # Every other adapter reports output_tokens with reasoning included, so
        # normalise here — one convention, enforced at the edge, and the cost
        # calculator never has to ask which provider it is looking at.
        return ProviderResponse(
            text=text,
            reasoning_summary=thoughts,
            reasoning_exposure="summary" if thoughts else
                               ("token_count_only" if thinking else "none"),
            input_tokens=int(getattr(m, "prompt_token_count", 0) or 0),
            output_tokens=answer_tokens + int(thinking or 0),
            reasoning_tokens=int(thinking) if thinking is not None else None,
            reasoning_request={"thinking_config": req},
            raw_meta={"api": "generate_content",
                      "finish_reason": str(getattr(r.candidates[0], "finish_reason", ""))},
        )


def _split_parts(response) -> tuple[str, str | None]:
    """Separate answer parts from thought-summary parts.

    Gemini flags a summary part with `part.thought is True`. That flag is the
    only reason these two strings can be told apart, and it is why the split
    happens here rather than by pattern-matching prose later.
    """
    answer, thought = [], []
    for cand in getattr(response, "candidates", []) or []:
        for part in getattr(cand.content, "parts", []) or []:
            txt = getattr(part, "text", None)
            if not txt:
                continue
            (thought if getattr(part, "thought", False) else answer).append(txt)
    return "".join(answer), ("\n\n".join(thought) or None)
