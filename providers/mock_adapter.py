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
# Simulated solutions.
#
# The simulator LOOKS THE ANSWER UP. It is a trace generator, not a model: it
# is not solving anything, it is not blind, and nothing it produces is evidence
# about any real system. Reading the key is what lets an offline rehearsal show
# a realistic mix of outcomes on whatever problem set is loaded — including a
# competition set nobody could canned-solve in advance.
#
# Three classes are produced, because those three are exactly what Part II needs
# on screen: a sound derivation, one that reaches the RIGHT answer by an invalid
# route, and one that is simply wrong.
# --------------------------------------------------------------------------
QUALITY_TEXT = {
    "sound": (
        "Set up the standard reduction for this problem and carry it through.\n"
        "Each step follows from the previous one, and the boundary cases are checked.\n"
        "The derivation closes and gives the value below.\n"
        "\nFINAL ANSWER: \\boxed{{{answer}}}"
    ),
    "unjustified": (
        "The setup suggests the usual reduction. Assuming the standard proportion\n"
        "carries over here without checking it, the count follows directly.\n"
        "That assumption feels right for a problem of this shape.\n"
        "\nFINAL ANSWER: \\boxed{{{answer}}}"
    ),
    "wrong": (
        "Apply the reduction, but treat the excluded cases as though they were\n"
        "included; the correction term is dropped as negligible.\n"
        "\nFINAL ANSWER: \\boxed{{{answer}}}"
    ),
}


def _expected_answer(prompt: str) -> str | None:
    """The key, looked up by matching the question text.

    Deliberately reaching for something a real provider could never see. The
    simulator is the one component allowed to, because it is not a measurement
    and every record it writes says so.
    """
    try:
        from harness.problems import load_problems
    except Exception:  # noqa: BLE001 — the simulator must never break a rehearsal
        return None
    for prob in load_problems().values():
        head = " ".join(prob.question.split())[:100]
        if head and head in " ".join(prompt.split()):
            return prob.expected_answer
    return None


def _wrong_answer(answer: str, seed: str) -> str:
    """A plausible near miss: same shape, different value."""
    if answer.isdigit():
        n = int(answer)
        off = _rng_int(seed + "w", 1, 9)
        return str(max(0, n + (off if n + off <= 999 else -off)))
    return "0"


def _solution(prompt: str, mode: ReasoningMode, seed: str) -> tuple[str, str]:
    """Pick a simulated solution. Higher effort draws the sound one more often —
    a simulated tendency, not an observed one."""
    answer = _expected_answer(prompt)
    if answer is None:
        return ("The simulator has no key for this problem.\n\nFINAL ANSWER: \\boxed{0}",
                "unknown")
    weights = {ReasoningMode.LOW: (25, 40, 100),
               ReasoningMode.MEDIUM: (55, 85, 100),
               ReasoningMode.HIGH: (75, 95, 100)}[mode]
    roll = _rng_int(seed + "q", 1, 100)
    quality = "sound" if roll <= weights[0] else (
        "unjustified" if roll <= weights[1] else "wrong")
    shown = answer if quality != "wrong" else _wrong_answer(answer, seed)
    return QUALITY_TEXT[quality].format(answer=shown), quality


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
#: Phrases the generator above writes, one per quality class. The simulated
#: judge reads the candidate back out of the judge prompt and classifies it from
#: these, so simulated verdicts stay coherent with the simulated solutions
#: instead of being independent noise.
QUALITY_MARKERS = {
    "sound": ("Each step follows from the previous one",),
    "unjustified": ("without checking it", "feels right for a problem of this shape"),
    "wrong": ("treat the excluded cases", "dropped as negligible"),
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
    points = {
        "sound": ["every stated step follows from the previous one",
                  "the boundary cases are checked rather than assumed",
                  "the final value is derived, not asserted"],
        "unjustified": ["the final value matches the expected form",
                        "the central proportion is assumed, never established",
                        "no case analysis is offered for the assumption"],
        "wrong": ["the excluded cases are treated as included",
                  "the correction term is dropped without justification",
                  "the final value therefore does not follow"],
        "unknown": ["the solution states a final value",
                    "the intermediate steps are not verifiable here",
                    "no explicit error is identifiable"],
    }[quality]
    return _json.dumps({
        **scores,
        "error_severity": severity,
        "verdict": verdict,
        "explanation": (f"{BANNER} Simulated verdict for a solution the simulator "
                        f"classified as '{quality}'."
                        + (" This judge read the unsupported step generously."
                           if swung and scores["reasoning"] >= 4 else "")),
        # The rubric demands exactly three; the simulator obeys the same contract
        # a real judge does, so the parser is exercised identically.
        "key_points": [f"[simulated] {t}" for t in points],
    })
