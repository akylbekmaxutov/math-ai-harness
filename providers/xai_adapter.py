"""xAI adapter — the OpenAI-compatible chat-completions dialect at api.x.ai.

This is the adapter that earns the abstraction its keep, because xAI is the
provider that does NOT offer all three levels: reasoning effort is `low` or
`high`, and there is no middle setting.

`supported_reasoning` therefore lists two modes, and asking for MEDIUM raises
`UnsupportedReasoningMode`. The runner records that cell as `unsupported` and
the results grid draws it as a hole. That hole is the honest rendering of the
experiment: the alternative — quietly sending `low`, or sending nothing and
letting the provider default decide — produces a `medium` row that is not a
medium measurement, and no one reading the table could ever tell.
"""
from __future__ import annotations

import os

from harness.reasoning import ReasoningMode
from providers.base import BaseAdapter, ProviderError, ProviderResponse, ProviderTimeout

BASE_URL = "https://api.x.ai/v1"

#: MEDIUM is deliberately absent. See the module docstring.
EFFORT = {
    ReasoningMode.LOW: "low",
    ReasoningMode.HIGH: "high",
}


class XAIAdapter(BaseAdapter):
    name = "xai"
    supported_reasoning = (ReasoningMode.LOW, ReasoningMode.HIGH)

    def __init__(self, model: str, timeout: int = 180):
        self.model, self.timeout = model, timeout
        try:
            from openai import OpenAI          # xAI speaks the same wire format
        except ImportError as e:
            raise ProviderError("provider 'xai' needs the `openai` package: "
                                "pip install -r requirements.txt") from e
        key = os.environ.get("XAI_API_KEY")
        if not key:
            raise ProviderError("XAI_API_KEY is not set — see .env.example")
        self._client = OpenAI(api_key=key, base_url=BASE_URL)

    def generate(self, prompt, *, system, reasoning_mode, max_output_tokens=4096):
        self.require_supported(reasoning_mode)
        req = {"reasoning_effort": EFFORT[reasoning_mode]}
        try:
            r = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": prompt}],
                max_tokens=max_output_tokens,
                timeout=self.timeout,
                **req,
            )
        except Exception as e:  # noqa: BLE001
            if "timeout" in str(e).lower():
                raise ProviderTimeout(str(e)) from e
            raise ProviderError(str(e)) from e

        msg = r.choices[0].message
        u = r.usage
        details = getattr(u, "completion_tokens_details", None)
        rtok = getattr(details, "reasoning_tokens", None) if details else None
        # Some xAI reasoning models return the trace on the message; when the
        # field is absent we say `token_count_only` rather than inventing one.
        summary = getattr(msg, "reasoning_content", None) or None
        return ProviderResponse(
            text=msg.content or "",
            reasoning_summary=summary,
            reasoning_exposure="summary" if summary else
                               ("token_count_only" if rtok else "none"),
            input_tokens=int(u.prompt_tokens),
            output_tokens=int(u.completion_tokens),
            reasoning_tokens=int(rtok) if rtok is not None else None,
            reasoning_request=req,
            raw_meta={"response_id": getattr(r, "id", None), "api": "chat_completions"},
        )
