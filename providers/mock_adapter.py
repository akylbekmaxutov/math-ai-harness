"""The offline simulator.

It exists so the entire workshop — every command, every page, the whole results
interface — can be rehearsed on a plane with no keys and no network, and so a
live demo never depends on three APIs being up at once.

It is a TRACE GENERATOR, not a model. Everything it writes is stamped
`simulated: true`, every simulated run carries a banner in the results
interface, and the text it emits says so in its own first line. Nothing
produced here is a measurement of GPT, Gemini or Grok, and the website is not
allowed to imply that it is.

Its output is a deterministic function of (model, mode, problem), so a rebuilt
page is byte-identical and a rehearsal is repeatable.
"""
from __future__ import annotations

import hashlib
import re
import time

from harness.reasoning import ReasoningMode
from providers.base import BaseAdapter, ProviderResponse

BANNER = "[SIMULATED OUTPUT — generated offline by providers/mock_adapter.py, not a model]"


def _rng_int(seed: str, lo: int, hi: int) -> int:
    """Stable pseudo-random integer in [lo, hi] from a string seed."""
    h = hashlib.sha256(seed.encode("utf-8")).digest()
    return lo + int.from_bytes(h[:8], "big") % (hi - lo + 1)


class MockAdapter(BaseAdapter):
    name = "mock"
    #: The simulator supports every level, so that a `--mock` rehearsal still
    #: exercises the unsupported-mode path: that comes from the REAL adapter's
    #: declaration in harness/models.py, not from whether a call can be made.
    supported_reasoning = (ReasoningMode.LOW, ReasoningMode.MEDIUM, ReasoningMode.HIGH)

    def __init__(self, model: str = "mock-model", timeout: int = 0, label: str = ""):
        self.model = model
        # The model this run stands in for. It seeds the simulation, so a
        # rehearsal shows three different-looking models rather than one
        # repeated three times — while `solver.model` still records
        # "mock-model", because that is what actually answered.
        self.label = label or model

    def generate(self, prompt, *, system, reasoning_mode, max_output_tokens=4096):
        seed = f"{self.label}|{reasoning_mode.value}|{prompt[:400]}"
        if "RUBRIC" in prompt:                       # this is a judge call
            return self._judge(prompt, reasoning_mode, seed)
        body, quality = _solution(prompt, reasoning_mode, seed)
        text = f"{BANNER}\n\n{body}"
        # Effort costs tokens here too, so the reasoning-mode slides have a
        # shape to show. The numbers are invented and the page says so.
        scale = {ReasoningMode.LOW: 1, ReasoningMode.MEDIUM: 3, ReasoningMode.HIGH: 7}
        rtok = _rng_int(seed + "r", 120, 400) * scale[reasoning_mode]
        # A real pause, so the latency the stopwatch records is a latency that
        # actually elapsed. Invented, and short — but not a fabricated number
        # written straight into the timing field.
        time.sleep(_rng_int(seed + "t", 4, 26) / 100 * scale[reasoning_mode] ** 0.5)
        return ProviderResponse(
            text=text,
            reasoning_summary=f"{BANNER} Simulated reasoning summary: {quality}.",
            reasoning_exposure="summary",
            input_tokens=_rng_int(seed + "i", 180, 320),
            output_tokens=rtok + _rng_int(seed + "o", 200, 520),
            reasoning_tokens=rtok,
            reasoning_request={"simulated_mode": reasoning_mode.value},
            raw_meta={"simulated": True},
        )

    def _judge(self, prompt, reasoning_mode, seed) -> ProviderResponse:
        """A judge call returns strict JSON, so judges/judge.py parses the
        simulated verdict through exactly the same code path as a real one."""
        scale = {ReasoningMode.LOW: 1, ReasoningMode.MEDIUM: 3, ReasoningMode.HIGH: 7}
        rtok = _rng_int(seed + "jr", 60, 180) * scale[reasoning_mode]
        time.sleep(_rng_int(seed + "jt", 3, 14) / 100 * scale[reasoning_mode] ** 0.5)
        return ProviderResponse(
            text=_judge_json(prompt, seed),
            reasoning_summary=None,
            reasoning_exposure="token_count_only",
            input_tokens=_rng_int(seed + "ji", 700, 1400),
            output_tokens=rtok + _rng_int(seed + "jo", 90, 220),
            reasoning_tokens=rtok,
            reasoning_request={"simulated_mode": reasoning_mode.value},
            raw_meta={"simulated": True},
        )


# --------------------------------------------------------------------------
# The three canned solutions. Each problem gets one sound derivation, one that
# reaches the RIGHT answer by an invalid route, and one that is simply wrong —
# because those three cases are exactly what Part II needs on screen.
# --------------------------------------------------------------------------
SOLUTIONS = {
    "36/11": (
        ("sound",
         "Rates add. A fills 1/6 of the tank per hour, B fills 1/4, the drain removes 1/9.\n"
         "Net rate = 1/6 + 1/4 - 1/9 = 6/36 + 9/36 - 4/36 = 11/36 tank per hour.\n"
         "Time = 1 / (11/36) = 36/11 hours.\n\nFINAL ANSWER: \\boxed{36/11}"),
        ("right answer, invalid route",
         "Combine the times directly: 6 + 4 - 9 = 1, so the tank fills in about 1 hour.\n"
         "That seems too fast, so scale by the number of inputs: 36/11 hours.\n"
         "\nFINAL ANSWER: \\boxed{36/11}"),
        ("wrong",
         "Net rate = 1/6 + 1/4 + 1/9 = 19/36 (the drain also moves water).\n"
         "Time = 36/19 hours.\n\nFINAL ANSWER: \\boxed{36/19}"),
    ),
    "42": (
        ("sound",
         "If p is the smallest prime factor of n, the second-largest divisor is n/p.\n"
         "So n/p = 21, i.e. n = 21p. For 21 to be the second-largest divisor, p must be\n"
         "the smallest prime factor of n, forcing p = 2 (p = 3 or 7 would make 3 | n with a\n"
         "smaller cofactor). n = 42 = 2 x 3 x 7 has (1+1)^3 = 8 divisors. Checks out.\n"
         "\nFINAL ANSWER: \\boxed{42}"),
        ("right answer, unjustified",
         "The second-largest divisor is 21, so n is a small multiple of 21. Doubling gives 42.\n"
         "42 feels right for a divisor-counting problem.\n\nFINAL ANSWER: \\boxed{42}"),
        ("wrong",
         "n must be 21 x 3 = 63 so that 21 is the second-largest divisor.\n"
         "63 = 3^2 x 7 has 6 divisors, close enough to 8.\n\nFINAL ANSWER: \\boxed{63}"),
    ),
    "58": (
        ("sound",
         "3x + 4y = 0 (mod 7). Since 4 = -3 (mod 7), this is 3x - 3y = 0, and 3 is invertible\n"
         "mod 7, so x = y (mod 7).\nAmong 1..20 the residues 1..6 each occur 3 times and\n"
         "residue 0 occurs twice (7 and 14). Pairs = 6 x 3^2 + 1 x 2^2 = 54 + 4 = 58.\n"
         "\nFINAL ANSWER: \\boxed{58}"),
        ("right answer, hand-waved count",
         "The condition reduces to x = y mod 7. Roughly one in seven pairs qualifies,\n"
         "so 400/7 is about 57, and rounding up gives 58.\n\nFINAL ANSWER: \\boxed{58}"),
        ("wrong",
         "x = y (mod 7). Each of the 7 residues holds 3 values of x in 1..20,\n"
         "so the count is 7 x 3^2 = 63.\n\nFINAL ANSWER: \\boxed{63}"),
    ),
}


def _solution(prompt: str, mode: ReasoningMode, seed: str) -> tuple[str, str]:
    """Pick a canned solution. Higher effort draws the sound one more often —
    a simulated tendency, not an observed one."""
    key = next((k for k in SOLUTIONS if _mentions(prompt, k)), None)
    if key is None:
        return (f"No canned solution for this prompt.\n\nFINAL ANSWER: \\boxed{{0}}", "unknown")
    weights = {ReasoningMode.LOW: (25, 40, 100),
               ReasoningMode.MEDIUM: (55, 85, 100),
               ReasoningMode.HIGH: (75, 95, 100)}[mode]
    roll = _rng_int(seed + "q", 1, 100)
    idx = 0 if roll <= weights[0] else (1 if roll <= weights[1] else 2)
    quality, body = SOLUTIONS[key][idx]
    return body, quality


def _mentions(prompt: str, key: str) -> bool:
    """Which canned problem is this? Matched on a distinctive phrase, not the id,
    because the solver prompt never carries the id."""
    marks = {"36/11": "drain at the bottom", "42": "second-largest divisor",
             "58": "3x + 4y"}
    return re.search(re.escape(marks[key]), prompt, re.IGNORECASE) is not None


# --------------------------------------------------------------------------
# The simulated judge.
#
# Part II needs three things on screen that a random number generator will not
# give you: broad agreement on a sound solution, broad agreement on a wrong
# one, and REAL disagreement on the solution that reaches the right answer by
# an invalid route. So the simulator reads which of its own canned solutions it
# is looking at and scores accordingly, with per-judge jitter that is widest on
# exactly the case the workshop is about.
#
# It is still a simulation. Every verdict it writes is stamped simulated.
# --------------------------------------------------------------------------
QUALITY_MARKERS = {
    "sound": ("Rates add.", "If p is the smallest prime factor", "Since 4 = -3 (mod 7)"),
    "unjustified": ("Combine the times directly", "feels right", "Roughly one in seven"),
    "wrong": ("the drain also moves water", "close enough to 8", "so the count is 7 x 3^2"),
}

#: (base scores, severity, verdict, jitter width per criterion)
QUALITY_PROFILE = {
    "sound":       (dict(correctness=5, reasoning=5, completeness=5, efficiency=4, clarity=5),
                    "none", "pass", 0),
    # The interesting row: the answer is right, so `correctness` is stable and
    # every judge agrees on it — while `reasoning` and `completeness` swing by
    # up to two points depending on which judge read it.
    "unjustified": (dict(correctness=5, reasoning=3, completeness=2, efficiency=4, clarity=3),
                    "major", "fail", 2),
    "wrong":       (dict(correctness=1, reasoning=2, completeness=2, efficiency=3, clarity=4),
                    "incorrect_conclusion", "fail", 1),
    "unknown":     (dict(correctness=3, reasoning=3, completeness=3, efficiency=3, clarity=3),
                    "minor", "fail", 1),
}


def _quality_of(prompt: str) -> str:
    for quality, marks in QUALITY_MARKERS.items():
        if any(m.lower() in prompt.lower() for m in marks):
            return quality
    return "unknown"


def _judge_json(prompt: str, seed: str) -> str:
    import json as _json

    quality = _quality_of(prompt)
    base, severity, verdict, jitter = QUALITY_PROFILE[quality]
    scores, swung = {}, False
    for i, (k, v) in enumerate(base.items()):
        # Jitter only the process criteria; correctness is a fact both judges
        # can check, so simulated judges are not made to disagree about it.
        width = 0 if k == "correctness" else jitter
        delta = 0 if not width else _rng_int(f"{seed}|{k}", -width, width)
        scores[k] = max(1, min(5, v + delta))
        swung = swung or (delta != 0 and k == "reasoning")
    # A judge that scored the reasoning generously flips its verdict with it,
    # so verdict disagreement and score disagreement stay coherent.
    if quality == "unjustified" and scores["reasoning"] >= 4:
        verdict, severity = "pass", "minor"
    return _json.dumps({
        **scores,
        "error_severity": severity,
        "verdict": verdict,
        "explanation": (f"{BANNER} Simulated verdict for a solution the simulator "
                        f"classified as '{quality}'."
                        + (" This judge read the unsupported step generously."
                           if swung and scores["reasoning"] >= 4 else "")),
    })
