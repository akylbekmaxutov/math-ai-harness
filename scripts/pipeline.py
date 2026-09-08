"""The whole study, in one command.

Runs the standing check, the rotation corpus, the reasoning-effort sweep,
offline grading and the report — in that order, stopping at the first failure.
Every stage is exactly the command you would have typed, run as a subprocess,
so nothing here is a second implementation that can drift from the real one.

    python3 scripts/pipeline.py --mock         # offline, no keys, no network
    python3 scripts/pipeline.py --smoke        # one real rollout per model
    python3 scripts/pipeline.py                # the real study

Calibration is deliberately NOT included: `scripts/label.py` needs a human, and
a pipeline that pretended otherwise would produce judge numbers with nothing
behind them.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
B, DIM, R, G, Y, RED = "\033[1m", "\033[2m", "\033[0m", "\033[32m", "\033[33m", "\033[31m"


def stage(n: int, total: int, title: str, cmd: list[str]) -> float:
    print(f"\n{B}[{n}/{total}] {title}{R}")
    print(f"{DIM}    $ {' '.join(cmd[1:])}{R}\n")
    t0 = time.time()
    rc = subprocess.run([sys.executable, *cmd[1:]], cwd=ROOT).returncode
    dt = time.time() - t0
    if rc != 0:
        print(f"\n{RED}stage {n} failed (exit {rc}). Stopping — later stages would "
              f"build on a corpus that is not there.{R}\n")
        raise SystemExit(rc)
    print(f"{DIM}    ok in {dt:.1f}s{R}")
    return dt


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the whole study in one command.")
    ap.add_argument("--mock", action="store_true", help="offline simulator; no keys, no network")
    ap.add_argument("--n", type=int, default=10, help="rollouts per task for the rotation corpus")
    ap.add_argument("--sweep-n", type=int, default=5, help="rollouts per task per effort arm")
    ap.add_argument("--ablation", type=int, default=120, help="traces also judged unblinded")
    ap.add_argument("--task", default=None, help="restrict every stage to one task_id")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--no-sweep", action="store_true", help="skip the reasoning-effort arms")
    ap.add_argument("--no-check", action="store_true", help="skip the standing check")
    ap.add_argument("--smoke", action="store_true",
                    help="one rollout per model at high effort, then stop")
    ap.add_argument("--yes", "-y", action="store_true", help="do not ask before spending money")
    a = ap.parse_args()

    mock = ["--mock"] if a.mock else []
    task = ["--task", a.task] if a.task else []

    if a.smoke:
        print(f"\n{B}Smoke test{R} — one rollout per model, real providers, then stop.")
        for cfg in ("S1", "S2", "S3"):
            stage(1, 1, f"smoke {cfg} @ high",
                  ["py", "scripts/run.py", "--config", cfg, "--n", "1", "--effort", "high",
                   "--no-resume", *(task or ["--task", "aime2026-07"]), *mock])
        print(f"\n{G}Smoke test done.{R} Read the USD column above, multiply by the rollout "
              f"count you plan, and decide before running the full study.\n")
        return 0

    plan = [("standing check", ["py", "scripts/initial_check.py"])] if not a.no_check else []
    plan.append(("rotation corpus", ["py", "scripts/run.py", "--config", "all",
                                     "--n", str(a.n), "--concurrency", str(a.concurrency),
                                     *task, *mock]))
    if not a.no_sweep:
        plan.append(("reasoning-effort sweep", ["py", "scripts/run.py", "--config", "all",
                                                "--n", str(a.sweep_n), "--sweep-effort",
                                                "--concurrency", str(a.concurrency),
                                                *task, *mock]))
    plan.append(("offline grading", ["py", "scripts/grade.py", "--all",
                                     "--ablation", str(a.ablation), *mock]))
    plan.append(("report", ["py", "scripts/report.py", "--json"]))

    n_tasks = 1 if a.task else 8
    rollouts = 3 * n_tasks * a.n + (0 if a.no_sweep else 3 * 4 * n_tasks * a.sweep_n)
    print(f"\n{B}math-eval-harness — full study{R}")
    print(f"{DIM}  rotation      3 configs x {n_tasks} tasks x {a.n} rollouts{R}")
    if not a.no_sweep:
        print(f"{DIM}  effort sweep  3 configs x 4 efforts x {n_tasks} tasks x "
              f"{a.sweep_n} rollouts{R}")
    print(f"{DIM}  total         ~{rollouts} solver rollouts, then ~2 judge calls "
          f"per submitted trace{R}")

    if not a.mock and not a.yes:
        print(f"\n{Y}This calls real providers and costs real money.{R}")
        print(f"{DIM}  Run `python3 scripts/pipeline.py --smoke` first to measure one rollout, "
              f"or pass --mock to rehearse offline.{R}")
        try:
            if input("\n  type 'run' to continue: ").strip().lower() != "run":
                print("  cancelled.\n")
                return 1
        except (KeyboardInterrupt, EOFError):
            print("\n  cancelled.\n")
            return 1

    t0 = time.time()
    for i, (title, cmd) in enumerate(plan, 1):
        stage(i, len(plan), title, cmd)

    print(f"\n{G}{B}pipeline complete in {time.time() - t0:.1f}s{R}")
    print(f"{DIM}  traces/   verdicts/   reports/report.json{R}")
    print(f"\n{B}Not done automatically:{R} the 40-trace calibration needs a human.")
    print(f"{DIM}  python3 scripts/label.py --n 40   then re-run report.py{R}")
    print(f"{DIM}  Until those labels exist, every process number is an assertion "
          f"rather than a calibrated result.{R}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
