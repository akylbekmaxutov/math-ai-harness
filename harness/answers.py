"""Extracting the final answer, and deciding whether it is correct.

Two jobs, deliberately kept apart from everything else:

`extract_final_answer` reads the model's own \\boxed{...} / "FINAL ANSWER:"
marker out of the response text. If the model never marked one, this returns
None rather than guessing from the last number on the page — a guess here would
turn a formatting failure into a wrong answer, and those are different faults.

`is_correct` is exact-match after normalisation, and normalisation is
deliberately narrow: whitespace, LaTeX wrappers, thousands separators, and the
declared aliases. It does not do algebra. A checker clever enough to accept
`2.4` for `12/5` is also clever enough to accept something it should not, and
the whole workshop rests on this number being boring and reproducible.

This is also the module that sets up Part II: everything here decides whether
the ANSWER is right. Nothing here can tell you whether the REASONING was.
"""
from __future__ import annotations

import re
from fractions import Fraction

BOXED = re.compile(r"\\boxed\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}")
MARKER = re.compile(r"(?:final\s+answer|answer)\s*[:=]\s*(.+?)\s*$",
                    re.IGNORECASE | re.MULTILINE)


def extract_final_answer(text: str) -> str | None:
    """The last \\boxed{...}, else the last explicit `FINAL ANSWER:` line."""
    if not text:
        return None
    boxes = BOXED.findall(text)
    if boxes:
        return boxes[-1].strip()
    marks = MARKER.findall(text)
    if marks:
        return marks[-1].strip().rstrip(".")
    return None


def normalise(raw: str) -> str:
    """Strip the presentation, keep the value."""
    s = str(raw).strip()
    s = re.sub(r"^\$+|\$+$", "", s).strip()                    # $ ... $
    s = re.sub(r"\\(?:d?frac)\s*\{([^{}]+)\}\s*\{([^{}]+)\}", r"\1/\2", s)
    s = re.sub(r"\\(?:text|mathrm|mbox)\s*\{([^{}]*)\}", r"\1", s)
    s = s.replace("\\!", "").replace("\\,", "").replace("\\ ", " ")
    s = s.replace("\\left", "").replace("\\right", "")
    s = re.sub(r"[,\s]", "", s)                                # 1,024 -> 1024
    s = s.rstrip(".")
    return s.lower()


def _as_fraction(s: str):
    try:
        return Fraction(s)
    except (ValueError, ZeroDivisionError):
        return None


def is_correct(submitted: str | None, expected: str, aliases=()) -> bool:
    """Exact match after normalisation, against the key and its declared aliases.

    The one piece of arithmetic allowed: if both sides parse as exact rationals,
    compare them as rationals, so `36/11` and `72/22` agree. Floats are NOT
    accepted for a rational key — `3.27` is a rounding of the answer, not the
    answer, and accepting it would quietly raise every model's score.
    """
    if submitted is None:
        return False
    sub = normalise(submitted)
    for candidate in (expected, *aliases):
        cand = normalise(candidate)
        if sub == cand:
            return True
        fs, fc = _as_fraction(sub), _as_fraction(cand)
        if fs is not None and fc is not None and fs == fc:
            return True
    return False
