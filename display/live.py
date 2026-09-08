"""The terminal renderer. Six columns, because seven is unreadable from row
four of an auditorium.

live.py and replay.py share this renderer exactly. That is the whole point:
if the network dies, the fallback looks identical to the demo, and nobody in
the room can tell which one they are watching.
"""
from __future__ import annotations

import sys

COLS = [("RUN", 5), ("TURNS", 6), ("TOOLS", 6), ("ANSWER", 8), ("OUTCOME", 16), ("USD", 9)]

_C = {
    "correct": "\033[32m", "incorrect": "\033[31m", "refused": "\033[33m",
    "max_turns": "\033[33m", "budget_exceeded": "\033[33m",
    "error": "\033[35m", "timeout": "\033[35m", "submitted": "\033[36m",
}
_R, _DIM, _B = "\033[0m", "\033[2m", "\033[1m"


def banner(header: dict, out=sys.stdout) -> None:
    """Printed at the top of every run so the room sees the config was pinned."""
    sim = header.get("simulated")
    out.write(f"\n{_B}config {header.get('solver_config','?')}{_R}"
              f"   model {_B}{header.get('model','?')}{_R}"
              f"   temp {header.get('temperature','?')}"
              f"   prompt {header.get('prompt_sha','?')}\n")
    out.write(f"{_DIM}config_hash {header.get('config_hash','?')}"
              f"   tools {','.join(header.get('tools',[]))}"
              f"   max_turns {header.get('max_turns','?')}"
              f"   cap ${header.get('usd_budget','?')}{_R}\n")
    if sim:
        out.write("\033[33m*** SIMULATED CORPUS — no provider was called ***\033[0m\n")
    out.write(_DIM + "-" * sum(w + 2 for _, w in COLS) + _R + "\n")
    out.write(_DIM + "".join(f"{c:<{w}}  " for c, w in COLS) + _R + "\n")


def row(rollout, outcome: str | None = None, out=sys.stdout) -> None:
    o = outcome or rollout.outcome
    u = rollout.usage
    cells = [
        str(rollout.run_idx),
        str(u.get("turns", "")),
        str(u.get("tool_calls", "")),
        "-" if rollout.final is None else str(rollout.final)[:8],
        o,
        f"{u.get('usd', 0.0):.4f}",
    ]
    line = ""
    for (name, w), val in zip(COLS, cells):
        colour = _C.get(o, "") if name == "OUTCOME" else ""
        line += f"{colour}{val:<{w}}{_R if colour else ''}  "
    out.write(line + "\n")
    out.flush()


def footer(counts: dict, usd: float, out=sys.stdout) -> None:
    out.write(_DIM + "-" * sum(w + 2 for _, w in COLS) + _R + "\n")
    parts = [f"{k} {v}" for k, v in counts.items() if v]
    out.write(f"{_B}{sum(counts.values())} rollouts{_R}   " + "   ".join(parts)
              + f"   {_B}${usd:.4f}{_R}\n\n")
