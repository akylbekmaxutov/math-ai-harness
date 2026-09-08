"""The mathematics plugin: a task loader and an answer key.

This is the only module in the project that knows what a competition problem
is. The runner, the verifiers' interfaces and the whole metrics layer are
domain-agnostic — if the runner knew about mathematics, the harness would be
single-use.

Network is touched exactly once, by `sync()`. Everything afterwards reads
tasks/math/problems.jsonl. The Task object handed to the agent carries
`problem` and `task_id` only; `answer` is read separately, by verifiers, so
the agent code path physically cannot see it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in (None, ""):  # allow `python tasks/math/loader.py`
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.contracts import Task

HERE = Path(__file__).resolve().parent
PROBLEMS = HERE / "problems.jsonl"
DATASET = "MathArena/aime_2026"


def task_id(problem_idx: int) -> str:
    return f"aime2026-{problem_idx:02d}"


def sync(force: bool = False) -> Path:
    """Download the dataset once and cache it. Requires `datasets` + network."""
    if PROBLEMS.exists() and not force:
        return PROBLEMS
    from datasets import load_dataset  # noqa: PLC0415

    ds = load_dataset(DATASET, split="train")
    with open(PROBLEMS, "w", encoding="utf-8") as fh:
        for row in ds:
            fh.write(json.dumps({
                "task_id": task_id(int(row["problem_idx"])),
                "problem_idx": int(row["problem_idx"]),
                "problem": row["problem"],
                "answer": int(row["answer"]),
                "source": DATASET,
                "synthetic": False,
            }) + "\n")
    return PROBLEMS


def _rows() -> list[dict]:
    if not PROBLEMS.exists():
        raise FileNotFoundError(
            f"{PROBLEMS} not found. Run `uv run tasks/math/loader.py --sync` to pull "
            f"{DATASET}, or keep the shipped placeholder file for offline rehearsal."
        )
    return [json.loads(l) for l in PROBLEMS.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_tasks(idxs=None) -> list[Task]:
    """Tasks only. No answers. This is what the agent sees."""
    rows = _rows()
    if idxs:
        want = {int(i) for i in idxs}
        rows = [r for r in rows if r["problem_idx"] in want]
    return [Task(task_id=r["task_id"], problem=r["problem"]) for r in rows]


def answer_key() -> dict[str, int]:
    """Answers only. Imported by verifiers, never by agent/."""
    return {r["task_id"]: int(r["answer"]) for r in _rows()}


def is_synthetic() -> bool:
    return any(r.get("synthetic") for r in _rows())


if __name__ == "__main__":
    import sys

    if "--sync" in sys.argv:
        print("wrote", sync(force=True))
    else:
        rows = _rows()
        print(f"{len(rows)} problems · synthetic={is_synthetic()} · source={rows[0]['source']}")
