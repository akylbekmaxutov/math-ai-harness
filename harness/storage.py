"""The result store.

Every execution becomes one JSON file on disk. Not a database, not a pickle:
a workshop audience can open one in an editor, and a file that is readable is a
file that gets checked.

The layout is the join key made visible —

    results/solver/<problem_id>/<model>__<mode>.json
    results/judges/<problem_id>/<candidate>__<mode>__by__<judge>__<judge_mode>.json

so "which runs exist" is answerable with `ls`, and re-running one cell
overwrites exactly one file.

`SCHEMA_VERSION` is stored in every record. When the shape changes, old files
stay readable and the reader can say so instead of throwing a KeyError.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
SOLVER_DIR = RESULTS / "solver"
JUDGE_DIR = RESULTS / "judges"

SCHEMA_VERSION = "1.0"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def solver_path(problem_id: str, model_key: str, mode: str) -> Path:
    return SOLVER_DIR / problem_id / f"{model_key}__{mode}.json"


def judge_path(problem_id: str, model_key: str, mode: str,
               judge_key: str, judge_mode: str) -> Path:
    return JUDGE_DIR / problem_id / f"{model_key}__{mode}__by__{judge_key}__{judge_mode}.json"


def write_record(path: Path, record: dict) -> Path:
    """Write one record, atomically.

    Written to a temporary file and renamed, so a run interrupted mid-write
    leaves the previous good file in place rather than a truncated one that
    every later command has to defend against.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def read_record(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_all(directory: Path) -> list[dict]:
    """Every record under a directory, sorted by path so output is stable."""
    d = Path(directory)
    if not d.exists():
        return []
    return [read_record(p) for p in sorted(d.rglob("*.json"))]


def load_solver_runs() -> list[dict]:
    return load_all(SOLVER_DIR)


def load_judge_runs() -> list[dict]:
    return load_all(JUDGE_DIR)
