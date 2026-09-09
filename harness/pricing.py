"""One place where prices live.

Prices change. If a number is written into the module that calls the API, then
six months from now the results table is wrong and nobody can tell, because the
figure it disagrees with is buried in three files. So every price is here, each
row carries the date it was checked, and the version string travels into every
stored result — a cost is only reproducible if you know which price list
produced it.

Update the numbers, bump PRICING_VERSION, re-run `python3 -m analysis.build_results`.
Nothing else needs to change.
"""
from __future__ import annotations

#: Bump this whenever a number below changes. It is stored with every run.
PRICING_VERSION = "2026-09-08"

#: USD per 1,000,000 tokens.
#:
#: `reasoning_out` is the price of tokens the provider reports as reasoning
#: tokens. Where a provider bills them at the output rate — which is the common
#: case — this is None and the harness charges them as output. It is a separate
#: field rather than an assumption, because assuming costs money quietly.
MODEL_PRICING = {
    "gpt-5.6-terra": {
        "provider": "openai",
        "input": 1.25,
        "output": 10.00,
        "reasoning_out": None,          # billed as output tokens
        "checked": "2026-09-08",
        "source": "openai.com/api/pricing",
    },
    "gemini-3.8-flash": {
        "provider": "gemini",
        "input": 0.30,
        "output": 2.50,
        "reasoning_out": None,          # thinking tokens billed as output
        "checked": "2026-09-08",
        "source": "ai.google.dev/pricing",
    },
    "grok-4.6": {
        "provider": "xai",
        "input": 2.00,
        "output": 10.00,
        "reasoning_out": None,
        "checked": "2026-09-08",
        "source": "docs.x.ai/docs/models",
    },
    "mock-model": {
        "provider": "mock",
        "input": 0.0, "output": 0.0, "reasoning_out": None,
        "checked": "n/a", "source": "offline simulator — costs nothing, and is not a measurement",
    },
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int,
                  reasoning_tokens: int | None = None) -> dict:
    """Cost of one call, itemised.

    Returned as a breakdown rather than one float so the website can show where
    the money went — at HIGH reasoning the reasoning tokens are usually most of
    it, and that is the point the cost slide is making.

    Providers differ in whether `reasoning_tokens` is already counted inside
    `output_tokens`. The adapters normalise to "yes, it is included" before
    calling this, so the split below never double-charges.
    """
    p = MODEL_PRICING.get(model)
    if p is None:
        raise KeyError(
            f"no pricing for {model!r}. Add it to harness/pricing.py — a run with an "
            f"unknown price would otherwise be reported as costing nothing."
        )
    reasoning = int(reasoning_tokens or 0)
    visible_out = max(int(output_tokens) - reasoning, 0)
    reasoning_rate = p["output"] if p["reasoning_out"] is None else p["reasoning_out"]

    usd_in = int(input_tokens) / 1e6 * p["input"]
    usd_out = visible_out / 1e6 * p["output"]
    usd_reasoning = reasoning / 1e6 * reasoning_rate
    return {
        "usd_input": round(usd_in, 8),
        "usd_output": round(usd_out, 8),
        "usd_reasoning": round(usd_reasoning, 8),
        "estimated_usd": round(usd_in + usd_out + usd_reasoning, 8),
        "pricing_version": PRICING_VERSION,
    }
