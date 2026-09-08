"""The standing check. Re-run after every module is integrated.

Cumulative, per milestone. It must pass before moving on — that rule is the
only thing that keeps a two-week build from accumulating silent breakage.
Nothing here touches the network unless --online is passed.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OK, BAD, DIM, R = "\033[32m", "\033[31m", "\033[2m", "\033[0m"
_results: list[tuple[str, str, bool, str]] = []


def check(milestone: str, name: str):
    def deco(fn):
        try:
            detail = fn() or ""
            _results.append((milestone, name, True, str(detail)))
        except Exception as e:  # noqa: BLE001
            _results.append((milestone, name, False, f"{type(e).__name__}: {e}"))
        return fn
    return deco


def run(online: bool = False) -> int:
    from core.config import SOLVER_PROMPT, Registry, prompt_hash
    from core.contracts import OUTCOMES, Rollout, Task
    from core.trace import TraceRecorder, append_rollout, completed_keys, read_trace

    # ---------------- M1: contracts, trace, pinning ----------------------
    @check("M1", "Rollout round-trips through JSONL with no loss")
    def _():
        rec = TraceRecorder("t-01", 0, "S1", "abc", seed=1)
        rec.emit("model_call", n=1)
        rec.emit("tool_result", result={"stdout": "2\n"})
        r = rec.finish("submitted", final="42", usd=0.01)
        with tempfile.TemporaryDirectory() as d:
            p = append_rollout(r, {"config_hash": "abc"}, Path(d))
            hdr, back = read_trace(p)
            assert hdr["config_hash"] == "abc", "header lost"
            assert back[0].to_dict() == r.to_dict(), "round-trip differs"
        return "1 rollout, 3 events"

    @check("M1", "config_hash is sensitive to model, prompt, temperature, tools")
    def _():
        cfg = Registry.load().solver("S1")
        base = cfg.config_hash
        variants = {
            "model": dataclasses.replace(cfg, model=dataclasses.replace(cfg.model, model="x")),
            "temperature": dataclasses.replace(cfg, model=dataclasses.replace(cfg.model, temperature=0.0)),
            "prompt": dataclasses.replace(cfg, prompt=SOLVER_PROMPT + " "),
            "tools": dataclasses.replace(cfg, tools=("python_exec",)),
        }
        for what, v in variants.items():
            assert v.config_hash != base, f"changing {what} did not change config_hash"
        return f"base {base}, 4 dimensions"

    @check("M1", "Task carries no answer field")
    def _():
        names = [f.name for f in dataclasses.fields(Task)]
        assert "answer" not in names, f"Task exposes an answer: {names}"
        return f"fields {names}"

    # ---------------- M2: dataset, tools ---------------------------------
    @check("M2", "dataset loader yields tasks and a separate answer key")
    def _():
        from tasks.math.loader import answer_key, is_synthetic, load_tasks
        ts, key = load_tasks(), answer_key()
        assert ts, "no tasks"
        assert set(key) >= {t.task_id for t in ts}, "answer key missing tasks"
        return f"{len(ts)} tasks, synthetic={is_synthetic()}"

    @check("M2", "tool schemas are generated from signatures")
    def _():
        from agent.tools import schemas
        s = schemas(["python_exec", "submit_answer"])
        names = {x["function"]["name"] for x in s}
        assert names == {"python_exec", "submit_answer"}, names
        assert s[0]["function"]["parameters"]["required"] == ["code"]
        return "2 tools"

    # ---------------- M3: sandbox, outcomes ------------------------------
    @check("M3", "sandbox blocks network, enforces timeout, survives errors")
    def _():
        from agent.sandbox import run_python
        assert run_python("print(6*7)").stdout.strip() == "42"
        assert run_python("1/0").returncode != 0
        assert run_python("while True: pass", timeout_s=2).timed_out
        assert run_python("import socket; socket.socket()").returncode != 0
        return "exec / error / timeout / network"

    @check("M3", "error, timeout and max_turns classify to distinct outcomes")
    def _():
        from runner.outcomes import classify
        mk = lambda s: Rollout("t", 0, "S1", None, "h", outcome=s)  # noqa: E731
        got = {s: classify(mk(s), None) for s in ("error", "timeout", "max_turns",
                                                  "budget_exceeded", "refused")}
        assert len(set(got.values())) == 5, got
        assert classify(mk("submitted"), True) == "correct"
        assert classify(mk("submitted"), False) == "incorrect"
        return f"{len(OUTCOMES)} outcomes, all distinct"

    # ---------------- M4: orchestration ----------------------------------
    @check("M4", "resumption is idempotent; budget halts at the tool boundary")
    def _():
        from core.budget import Budget, BudgetExceeded
        from runner.rollouts import run_batch
        from tasks.math.loader import answer_key, load_tasks
        reg = Registry.load()
        cfg = reg.solver("S1", mock=True)
        tasks = load_tasks([7])
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a, _ = run_batch(tasks, cfg, 4, mock=True, answers=answer_key(), root=root)
            b, skipped = run_batch(tasks, cfg, 4, mock=True, answers=answer_key(), root=root)
            assert len(a) == 4 and len(b) == 0 and skipped == 4, (len(a), len(b), skipped)
            assert len(completed_keys(root)) == 4
        bud = Budget(usd_cap=0.0001, turn_cap=8)
        bud.charge(1000, 1000, 0.01)
        try:
            bud.check()
            raise AssertionError("budget cap did not halt")
        except BudgetExceeded:
            pass
        return "4 ran, 4 resumed, cap tripped"

    @check("M4", "re-running a key appends to the log but never double-counts")
    def _():
        from core.trace import iter_all
        from runner.rollouts import run_batch
        from tasks.math.loader import answer_key, load_tasks
        cfg = Registry.load().solver("S1", mock=True)
        tasks = load_tasks([7])
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run_batch(tasks, cfg, 3, mock=True, answers=answer_key(), root=root)
            run_batch(tasks, cfg, 3, mock=True, answers=answer_key(), root=root, resume=False)
            raw = sum(1 for _ in iter_all(root, dedupe=False))
            seen = sum(1 for _ in iter_all(root))
            assert raw == 6, f"the log should keep both attempts, got {raw}"
            assert seen == 3, f"derived views must see one row per rollout, got {seen}"
        return "6 records in the log, 3 rollouts in the view"

    @check("M4", "effort arms get distinct keys, hashes and trace files")
    def _():
        from core.config import EFFORTS, base_config, effort_of
        reg = Registry.load()
        hashes, labels = set(), set()
        for e in EFFORTS:
            c = reg.solver("S1", effort=e)
            hashes.add(c.config_hash)
            labels.add(c.solver_config)
            assert base_config(c.solver_config) == "S1"
            assert effort_of(c.solver_config) == e
            assert c.model.reasoning_effort == e
        assert len(hashes) == len(EFFORTS), f"effort does not move config_hash: {hashes}"
        assert len(labels) == len(EFFORTS), f"arms share a label: {labels}"
        return f"{len(EFFORTS)} arms, {len(hashes)} distinct hashes"

    @check("M6", "the blinding ablation is stratified, not the first N sorted")
    def _():
        import scripts.grade as g  # noqa: PLC0415
        from core.contracts import Rollout, Verdict

        def mk(cfg, i, label):
            r = Rollout("t", i, cfg, None, "h", outcome="submitted", final="1")
            return (r, None, Verdict("answer_match", "t", i, cfg, label, {}))

        checked = [mk(c, i, "correct" if i % 2 else "incorrect")
                   for c in ("S1@none", "S1@high", "S2@none", "S2@high")
                   for i in range(10)]
        picked = g._stratified_ablation(checked, 16)
        configs = {k[0] for k in picked}
        assert len(picked) == 16, len(picked)
        assert len(configs) == 4, f"ablation covered only {configs}"
        return f"16 picked across {len(configs)} arms"

    # ---------------- M5: answer verifier, metrics -----------------------
    @check("M5", "answer_match handles boxed / leading-zero / non-integer inputs")
    def _():
        from verifiers.answer_match import Escapes, normalise, verify
        assert normalise("\\boxed{608}") == 608
        assert normalise("0608") == 608
        assert normalise(" $608$ ") == 608
        assert normalise("six hundred") is None
        esc = Escapes()
        t = Task("aime2026-07", "p")
        verify(Rollout("aime2026-07", 0, "S1", None, "h", final="608",
                       outcome="submitted"), t, 608, esc)
        verify(Rollout("aime2026-07", 1, "S1", None, "h", final="nope",
                       outcome="submitted"), t, 608, esc)
        assert esc.unparsed == 1 and esc.escape_rate == 0.5, (esc.unparsed, esc.escape_rate)
        return "5 forms, escape counter increments"

    @check("M5", "pass@k / pass^k estimators agree with their definitions")
    def _():
        from metrics.aggregate import pass_at_k, pass_hat_k
        assert pass_at_k(10, 7, 1) == 0.7 and pass_hat_k(10, 7, 1) == 0.7
        assert pass_at_k(10, 7, 8) == 1.0, "pass@8 with 7/10 successes must be 1"
        assert pass_hat_k(10, 7, 8) == 0.0, "pass^8 needs at least 8 successes"
        assert pass_hat_k(10, 10, 8) == 1.0
        assert abs(pass_hat_k(10, 9, 2) - (36 / 45)) < 1e-12
        return "boundary + interior cases"

    # ---------------- M6: blinding ---------------------------------------
    @check("M6", "blinded prompt hides identifiers, outcome, metadata and the tell")
    def _():
        from verifiers.process_judge import REDACTED, render
        reg = Registry.load()
        rec = TraceRecorder("aime2026-07", 0, "S1", "deadbeef99", 0)
        rec.emit("run_start", config=reg.solver("S1").header())
        rec.emit("model_call", model="gpt-5.6-terra")
        rec.emit("model_response", text="Computing it now.")
        rec.emit("tool_call", tool="python_exec", args={"code": "print(608)"})
        rec.emit("tool_result", tool="python_exec", result={"stdout": "608\n"})
        rec.emit("final", value="608", reasoning="so 608")
        r = rec.finish("submitted", final="608", usd=0.01)
        prompt, audit = render(r, Task("aime2026-07", "P"), blinded=True,
                               model_names=[m.model for m in reg.models.values()])
        assert not audit["hard_leaks"], audit["hard_leaks"]
        for banned in ("gpt-5.6-terra", "deadbeef99", "OUTCOME:", "FINAL ANSWER:", REDACTED):
            assert banned not in prompt, f"{banned} leaked into a blinded prompt"
        un, _ = render(r, Task("aime2026-07", "P"), blinded=False, graded_outcome="correct")
        assert "OUTCOME: correct" in un, "unblinded arm must carry the graded outcome"
        return f"{len(prompt)} chars, 0 hard leaks"

    @check("M6", "a verdict without a non-empty span is rejected at parse time")
    def _():
        from verifiers.process_judge import VerdictRejected, parse_verdict
        for bad in ('{"verdict":"ESTABLISHES","span":""}',
                    '{"verdict":"ESTABLISHES"}',
                    '{"verdict":"GOOD","span":"x"}',
                    "not json at all"):
            try:
                parse_verdict(bad)
                raise AssertionError(f"accepted a bad verdict: {bad}")
            except VerdictRejected:
                pass
        ok = parse_verdict('{"verdict":"ERROR","span":"the step","justification":"j"}')
        assert ok["verdict"] == "ERROR"
        return "4 rejected, 1 accepted"

    # ---------------- M7: reporting --------------------------------------
    @check("M7", "judge metrics compute over stored verdicts")
    def _():
        from core.contracts import Verdict
        from metrics.judges import blinding_effect, cohens_kappa, inter_judge_agreement
        assert cohens_kappa(["A", "B"], ["A", "B"]) == 1.0
        vs = [Verdict("process_judge", "t", i, "S1", "ESTABLISHES", {},
                      judge_model=j, blinded=True) for i in range(5) for j in ("A", "B")]
        assert inter_judge_agreement(vs)["raw_agreement"] == 1.0
        bl = [Verdict("process_judge", "t", i, "S1", "ERROR", {}, judge_model="A",
                      blinded=True) for i in range(4)]
        bl += [Verdict("process_judge", "t", i, "S1", "ESTABLISHES", {}, judge_model="A",
                       blinded=False) for i in range(4)]
        assert blinding_effect(bl)["change_rate"] == 1.0
        return "agreement, kappa, blinding effect"

    @check("M7", "report.py runs end to end when a graded corpus exists")
    def _():
        from core.trace import TRACES, VERDICTS
        if not any(TRACES.glob("*/*.jsonl")):
            return "skipped — no corpus yet (run scripts/run.py --mock)"
        if not (VERDICTS / "outcomes.json").exists():
            return "skipped — not graded yet (run scripts/grade.py --mock)"
        import subprocess
        p = subprocess.run([sys.executable, "scripts/report.py"], capture_output=True,
                           text=True, cwd=Path(__file__).resolve().parents[1])
        assert p.returncode == 0, p.stderr[-400:]
        assert "pass^k" in p.stdout and "cost per successful solve" in p.stdout.lower()
        return f"{len(p.stdout.splitlines())} lines emitted"

    if online:
        @check("M2", "one live call per configured provider")
        def _():
            from agent.providers import build
            from core.config import load_dotenv, validate_env
            load_dotenv()
            reg = Registry.load()
            names = []
            for c in ("S1", "S2", "S3"):
                spec = reg.models[reg.rotation["configs"][c]["solver"]]
                validate_env([spec.provider])
                out = build(spec).complete([{"role": "user", "content": "Reply OK."}], [])
                assert out.text, f"{spec.model} returned nothing"
                names.append(spec.model)
            return ", ".join(names)

    # ---------------- report ---------------------------------------------
    width = max(len(n) for _, n, _, _ in _results) + 2
    cur = None
    for ms, name, ok, detail in _results:
        if ms != cur:
            print(f"\n{DIM}{ms}{R}")
            cur = ms
        mark = f"{OK}PASS{R}" if ok else f"{BAD}FAIL{R}"
        print(f"  {mark}  {name:<{width}} {DIM}{detail}{R}")
    failed = [r for r in _results if not r[2]]
    print(f"\n{len(_results) - len(failed)}/{len(_results)} checks passed")
    if failed:
        print(f"{BAD}STANDING CHECK FAILED — do not move on until this is green.{R}\n")
        return 1
    print(f"{OK}standing check green{R}\n")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="The standing check.")
    ap.add_argument("--online", action="store_true", help="also make one live call per provider")
    raise SystemExit(run(ap.parse_args().online))
