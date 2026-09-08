"""Offline grading over stored traces. No solver is ever called from here.

This script existing separately from run.py is the structural proof that the
architecture is trace-first. Three of the four verifiers below were written
after the corpus existed, and were applied to all of it without spending a
cent on the system under test.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import ModelSpec, Registry, load_dotenv, validate_env
from core.trace import VERDICTS, append_verdicts, iter_all
from runner.outcomes import classify
from tasks.math.loader import answer_key, load_tasks
from verifiers import answer_match, masked_cont, process_judge, tool_replay


def _providers(reg: Registry, cfg: str, mock: bool):
    specs = reg.judges(cfg, mock=mock)
    if mock:
        from agent.providers import MockJudge
        # Two simulated judges with different severity, so agreement is a real
        # computation over two genuinely different verdict streams.
        return [MockJudge(specs[0], severity=0.35, noise=0.10),
                MockJudge(specs[1], severity=0.70, noise=0.16)]
    from agent.providers import build
    return [build(s) for s in specs]


def _stratified_ablation(checked, n: int) -> set:
    """Pick the traces to ALSO judge unblinded.

    Taking the first n in sorted order looks harmless and is not: with several
    solver configurations — an effort sweep produces twelve — the whole
    ablation lands inside whichever one sorts first, and the blinding effect
    gets measured on one arm and reported as if it covered the study. So the
    sample is round-robin across (solver_config, correct/incorrect) buckets,
    under a fixed seed.
    """
    if n <= 0:
        return set()
    buckets = defaultdict(list)
    for r, _task, v in checked:
        if r.outcome != "submitted":
            continue
        buckets[(r.solver_config, v.label)].append(r)
    rng = random.Random(20260908)
    for v in buckets.values():
        rng.shuffle(v)
    keys = sorted(buckets)
    picked, i = set(), 0
    while len(picked) < n and any(buckets[k] for k in keys):
        k = keys[i % len(keys)]
        if buckets[k]:
            picked.add(buckets[k].pop().key)
        i += 1
    return picked


def main() -> int:
    ap = argparse.ArgumentParser(description="Grade stored traces. Offline.")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--config", default=None)
    ap.add_argument("--mock", action="store_true", help="simulated judges; no keys needed")
    ap.add_argument("--ablation", type=int, default=60,
                    help="how many traces to also judge UNBLINDED (0 to skip)")
    ap.add_argument("--fresh", action="store_true", help="clear verdicts/ first")
    a = ap.parse_args()

    load_dotenv()
    reg = Registry.load()
    tasks = {t.task_id: t for t in load_tasks()}
    key = answer_key()

    if a.fresh:
        for p in VERDICTS.glob("*.jsonl"):
            p.unlink()

    rollouts = [r for _, r in iter_all()]
    if a.config:
        rollouts = [r for r in rollouts if r.solver_config == a.config]
    if not rollouts:
        print("no traces found — run scripts/run.py first", file=sys.stderr)
        return 1

    if not a.mock:
        validate_env(sorted({m.provider for c in {r.solver_config for r in rollouts}
                             for m in reg.judges(c)}))

    t0 = time.time()
    esc = answer_match.Escapes()
    am, tr, pj, mc = [], [], [], []
    model_names = [m.model for m in reg.models.values()]
    leaks = Counter()
    recoverable = [0, 0]
    outcomes: dict[str, str] = {}

    judges_by_cfg = {c: _providers(reg, c, a.mock)
                     for c in sorted({r.solver_config for r in rollouts})}
    cont = masked_cont.MockContinuer(ModelSpec("mc", "mock", "mock-continuer", 0, 0, 0)) \
        if a.mock else _providers(reg, rollouts[0].solver_config, False)[0]

    # Pass 1: the deterministic answer check for everything. Cheap, offline, and
    # it is what the ablation needs in order to stratify on outcome.
    checked = []
    for r in rollouts:
        task = tasks.get(r.task_id)
        if task is None:
            continue
        v = answer_match.verify(r, task, key[r.task_id], esc)
        am.append(v)
        outcomes["|".join([r.solver_config, r.task_id, str(r.run_idx)])] = classify(
            r, v.label == "correct" if r.outcome == "submitted" else None)
        checked.append((r, task, v))

    ablate = _stratified_ablation(checked, a.ablation)

    for r, task, v in checked:

        tr.append(tool_replay.verify(r, task))

        if r.outcome == "submitted":
            for jp in judges_by_cfg[r.solver_config]:
                try:
                    verdict = process_judge.judge(r, task, jp, blinded=True,
                                                  model_names=model_names)
                except process_judge.BlindingLeak as e:
                    leaks[str(e)[:60]] += 1
                    continue
                except process_judge.VerdictRejected:
                    leaks["verdict rejected at parse time"] += 1
                    continue
                pj.append(verdict)
                if verdict.detail.get("answer_recoverable_from_tool_output"):
                    recoverable[0] += 1
                recoverable[1] += 1
                if r.key in ablate:
                    # The unblinded arm is told the grade. That is the leak
                    # under test; without it the ablation measures nothing.
                    pj.append(process_judge.judge(
                        r, task, jp, blinded=False, model_names=model_names,
                        graded_outcome=v.label))
            mc.append(masked_cont.verify(r, task, cont))

    append_verdicts("answer_match", am)
    append_verdicts("tool_replay", tr)
    append_verdicts("process_judge", pj)
    append_verdicts("masked_cont", mc)
    Path(VERDICTS / "outcomes.json").write_text(
        json.dumps({"outcomes": outcomes, "escape_rate": esc.escape_rate,
                    "escapes": {"exact": esc.exact, "symbolic": esc.symbolic,
                                "unparsed": esc.unparsed}}, indent=1))

    dt = time.time() - t0
    print(f"\ngraded {len(rollouts)} stored rollouts in {dt:.1f}s "
          f"with \033[1m0 solver calls\033[0m")
    print(f"  answer_match  {len(am):4d}   escape rate {esc.escape_rate:.3f}")
    print(f"  tool_replay   {len(tr):4d}   mismatches "
          f"{sum(1 for v in tr if v.label == 'mismatch')}")
    print(f"  process_judge {len(pj):4d}   "
          f"({sum(1 for v in pj if v.blinded)} blinded / "
          f"{sum(1 for v in pj if v.blinded is False)} unblinded ablation)")
    print(f"  masked_cont   {len(mc):4d}   mismatches "
          f"{sum(1 for v in mc if v.label == 'mismatch')}")
    print("\n  blinding audit:")
    print(f"    {leaks.total() if hasattr(leaks, 'total') else sum(leaks.values()):4d}  "
          f"hard leaks (identifiers / outcome / metadata / submitted value)")
    for k, n in leaks.most_common():
        print(f"          {n:4d}  {k}")
    if recoverable[1]:
        print(f"    {recoverable[0] / recoverable[1]:4.0%}  of blinded prompts let the judge "
              f"RECONSTRUCT the submitted answer from tool output")
        print("          (not outcome leakage — the key is never rendered; it means the "
              "redaction alone buys little,")
        print("           which is why the blinded/unblinded ablation is the measurement "
              "that matters)")
    print(f"\nverdicts -> {VERDICTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
