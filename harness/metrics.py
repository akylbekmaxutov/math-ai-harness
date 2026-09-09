"""The metrics collector.

Turns one provider response into the `usage`, `timing` and `cost` blocks of the
stored record — and, just as importantly, records what was NOT available.

`reasoning_tokens: null` and `reasoning_tokens: 0` mean different things. Null
is "this provider did not tell us"; zero is "it told us, and the answer was
none". Collapsing them would make an average over the column silently wrong, so
they stay distinct all the way to the website, which prints `n/a` for one and
`0` for the other.
"""
from __future__ import annotations

import time
from contextlib import contextmanager

from harness.pricing import estimate_cost


@contextmanager
def stopwatch():
    """Wall-clock latency around a single API call.

    Wall clock rather than the provider's own timing: what the experiment is
    comparing is what a user would wait for, queueing and all.
    """
    t0 = time.perf_counter()
    box = {"latency_seconds": None}
    try:
        yield box
    finally:
        box["latency_seconds"] = round(time.perf_counter() - t0, 3)


def usage_block(response) -> dict:
    """Token counts, with the unknowns preserved as null."""
    return {
        "input_tokens": int(response.input_tokens),
        "output_tokens": int(response.output_tokens),
        "reasoning_tokens": (None if response.reasoning_tokens is None
                             else int(response.reasoning_tokens)),
        "total_tokens": int(response.total_tokens),
        # How much of the output was reasoning — the number the effort slides
        # are actually about. None when the provider did not break it out.
        "reasoning_share": (None if not response.output_tokens or response.reasoning_tokens is None
                            else round(response.reasoning_tokens / response.output_tokens, 4)),
    }


def cost_block(model_key: str, response) -> dict:
    return estimate_cost(
        model_key,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        reasoning_tokens=response.reasoning_tokens,
    )
