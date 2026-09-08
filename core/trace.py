"""Append-only trace store.

This is the seam. Everything downstream of execution is a pure function of
what is written here, which is why grade.py can exist as a separate entry
point from run.py and why new verifiers can be applied to old runs with no
model calls.

One file per (solver_config, task_id). Line 0 is the pinned config header;
every subsequent line is one rollout. Nothing is ever rewritten in place.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from core.contracts import Event, Rollout

ROOT = Path(__file__).resolve().parent.parent
TRACES = ROOT / "traces"
VERDICTS = ROOT / "verdicts"


def trace_path(solver_config: str, task_id: str, root: Path | None = None) -> Path:
    return (root or TRACES) / solver_config / f"{task_id}.jsonl"


class TraceRecorder:
    """Collects events for one rollout. Holds no opinion about correctness."""

    def __init__(self, task_id: str, run_idx: int, solver_config: str, config_hash: str,
                 seed: int | None = None):
        self.rollout = Rollout(
            task_id=task_id,
            run_idx=run_idx,
            solver_config=solver_config,
            seed=seed,
            config_hash=config_hash,
        )
        self._t0 = time.time()

    def emit(self, kind: str, **payload) -> Event:
        ev = Event(t=time.time() - self._t0, kind=kind, payload=payload)
        self.rollout.events.append(ev)
        return ev

    def finish(self, outcome: str, final=None, **usage) -> Rollout:
        r = self.rollout
        r.outcome = outcome
        r.final = final
        usage.setdefault("wall_s", round(time.time() - self._t0, 3))
        usage.setdefault("turns", sum(1 for e in r.events if e.kind == "model_call"))
        r.usage.update(usage)
        return r


def append_rollout(rollout: Rollout, header: dict, root: Path | None = None) -> Path:
    """Append one rollout. Writes the pinned header once, on file creation."""
    p = trace_path(rollout.solver_config, rollout.task_id, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    new = not p.exists()
    with open(p, "a", encoding="utf-8") as fh:
        if new:
            fh.write(json.dumps({"_header": header}, sort_keys=True) + "\n")
        fh.write(json.dumps(rollout.to_dict()) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return p


def read_trace(path: Path) -> tuple[dict, list[Rollout]]:
    header, rollouts = {}, []
    if not path.exists():
        return header, rollouts
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if "_header" in d:
                header = d["_header"]
            else:
                rollouts.append(Rollout.from_dict(d))
    return header, rollouts


def iter_all(root: Path | None = None, dedupe: bool = True):
    """Every stored rollout, with the header it was recorded under.

    The store is append-only, so re-running a key that is already on disk
    (`run.py --no-resume`) leaves two records for it rather than replacing
    one. That is the correct behaviour for a log — the earlier attempt really
    did happen — but a derived view must not count it twice. So the default
    here is last-write-wins per (solver_config, task_id, run_idx): the log
    keeps everything, metrics see one row per rollout.

    Pass dedupe=False to audit the raw log, including superseded records.
    """
    base = root or TRACES
    records = []
    for path in sorted(base.glob("*/*.jsonl")):
        header, rollouts = read_trace(path)
        records.extend((header, r) for r in rollouts)
    if not dedupe:
        yield from records
        return
    latest: dict[tuple, tuple] = {}
    for header, r in records:
        latest[r.key] = (header, r)          # later lines win
    for header, r in latest.values():
        yield header, r


def completed_keys(root: Path | None = None) -> set[tuple[str, str, int]]:
    """Used for resumption: (solver_config, task_id, run_idx) already on disk."""
    return {r.key for _, r in iter_all(root)}


def append_verdicts(name: str, verdicts, root: Path | None = None) -> Path:
    p = (root or VERDICTS) / f"{name}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        for v in verdicts:
            fh.write(json.dumps(v.to_dict()) + "\n")
    return p


def read_verdicts(name: str, root: Path | None = None):
    from core.contracts import Verdict

    p = (root or VERDICTS) / f"{name}.jsonl"
    if not p.exists():
        return []
    out = []
    with open(p, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out.append(Verdict.from_dict(json.loads(line)))
    return out
