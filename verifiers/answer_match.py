"""Deterministic answer equivalence.

This is the layer that makes competition mathematics the cleanest case for
teaching judge placement: an answer key exists, so a judge here would be the
wrong tool. Exact, free, reproducible.

Every time normalisation fails and we fall through to something fuzzier, that
is an ESCAPE. The escape rate is counted and reported, because it is the only
honest bound on how much of the final number was not decided by code.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from core.contracts import Rollout, Task, Verdict

NAME = "answer_match"

_BOXED = re.compile(r"\\boxed\s*\{([^}]*)\}")
_INT = re.compile(r"^-?\d+$")


@dataclass
class Escapes:
    exact: int = 0
    symbolic: int = 0
    unparsed: int = 0
    examples: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.exact + self.symbolic + self.unparsed

    @property
    def escape_rate(self) -> float:
        """Share of decisions NOT made by exact integer comparison."""
        return 0.0 if not self.total else (self.symbolic + self.unparsed) / self.total


def normalise(raw) -> int | None:
    """Return an integer, or None if this value needs an escape."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    s = str(raw).strip()
    m = _BOXED.search(s)
    if m:
        s = m.group(1)
    s = s.replace("$", "").replace(",", "").replace("\\!", "").replace("\\,", "")
    s = s.replace(" ", "").strip()
    s = re.sub(r"^\+", "", s)
    if _INT.match(s):
        return int(s)
    if re.match(r"^-?\d+\.0*$", s):
        return int(float(s))
    return None


def _symbolic(raw) -> int | None:
    """Last deterministic resort before a judge. Optional dependency by design."""
    try:
        import sympy  # noqa: PLC0415
    except ImportError:
        return None
    try:
        val = sympy.sympify(str(raw).replace("\\", ""))
        if val.is_Integer:
            return int(val)
        if val.is_Number and float(val).is_integer():
            return int(float(val))
    except Exception:  # noqa: BLE001
        return None
    return None


def verify(rollout: Rollout, task: Task, key: int, escapes: Escapes | None = None) -> Verdict:
    esc = escapes or Escapes()
    raw = rollout.final
    method, value = "exact", normalise(raw)
    if value is None and raw is not None:
        value, method = _symbolic(raw), "symbolic"
    if value is None:
        method = "unparsed"
        esc.unparsed += 1
        esc.examples.append(repr(raw)[:60])
    elif method == "exact":
        esc.exact += 1
    else:
        esc.symbolic += 1

    label = "correct" if (value is not None and value == key) else "incorrect"
    if rollout.outcome != "submitted":
        label = "not_submitted"
    return Verdict(
        verifier=NAME,
        task_id=rollout.task_id,
        run_idx=rollout.run_idx,
        solver_config=rollout.solver_config,
        label=label,
        detail={"raw": raw, "normalised": value, "method": method, "key": key},
    )
