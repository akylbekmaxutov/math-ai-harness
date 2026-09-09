"""`python3 -m harness.check` — the preflight.

Run this before spending money. It checks, without making a single API call,
the four things that otherwise fail forty seconds into a batch:

    keys        every provider the study needs has its variable set — named
    problems    the problem file parses and every id is unique
    pricing     every model in the registry has a price, so no run is silently
                reported as free
    capability  which (model, reasoning mode) cells exist, and which do not

It prints the plan and the exact size of the study, and it never prints a key.
`--live` adds one real one-token call per provider, which is the only way to
find out that a key is present but wrong.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import env, models, problems  # noqa: E402
from harness.pricing import PRICING_VERSION  # noqa: E402
from harness.reasoning import ReasoningMode  # noqa: E402

KEY_FOR = {"openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY", "xai": "XAI_API_KEY"}

OK, BAD = "PASS", "FAIL"





def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="harness.check", description=__doc__.splitlines()[0])
    ap.add_argument("--live", action="store_true", help="also make one tiny real call per provider")
    a = ap.parse_args(argv)
    fails = 0

    loaded = env.load_dotenv()
    aliased = env.canonicalise()
    print(f"\n  ENVIRONMENT\n    {loaded} variable(s) read from .env")
    for canonical, alt in aliased.items():
        print(f"    {canonical} taken from {alt}")

    print("\n  KEYS")
    for provider, var in KEY_FOR.items():
        have = bool(os.environ.get(var))
        fails += not have
        # The value is never printed. Its presence and length are enough.
        detail = f"set ({len(os.environ.get(var, ''))} chars)" if have else "MISSING — see .env.example"
        print(f"    {OK if have else BAD}  {var:16s} {provider:8s} {detail}")

    print("\n  PROBLEMS")
    probs = problems.load_problems()
    for p in probs.values():
        print(f"    {OK}  {p.problem_id:14s} {p.kind:32s} expected {p.expected_answer}")
    print(f"          set version {next(iter(probs.values())).set_version}")

    print("\n  PRICING")
    for key in models.MODELS:
        p = models.pricing_for(key)
        priced = p.get("provider") != "mock"      # the mock row is the fallback
        fails += not priced
        print(f"    {OK if priced else BAD}  {key:17s} "
              + (f"in ${p['input']}/M  out ${p['output']}/M  checked {p['checked']}"
                 if priced else "NO PRICE — a run would be reported as costing nothing"))
    print(f"          pricing version {PRICING_VERSION}")

    print("\n  CAPABILITY MATRIX")
    matrix = models.capability_matrix()
    modes = [m.value for m in ReasoningMode]
    print(" " * 21 + "".join(f"{m:>10s}" for m in modes))
    calls = 0
    for key, row in matrix.items():
        cells = "".join(f"{('yes' if row[m] else 'NO'):>10s}" for m in modes)
        calls += sum(row.values())
        print(f"    {key:17s}{cells}")
    print(f"\n  STUDY SIZE")
    print(f"    {len(probs)} problems x {calls} supported (model, mode) cells "
          f"= {len(probs) * calls} solver calls")
    print(f"    + {len(probs) * calls} x 2 judges x 2 judge efforts "
          f"= {len(probs) * calls * 4} judge calls")

    if a.live:
        print("\n  LIVE PROBE  (one minimal call per provider)")
        for key in models.MODELS:
            try:
                adapter = models.build_adapter(key)
                r = adapter.generate("Reply with the digit 1 and nothing else.",
                                     system="Answer with one character.",
                                     reasoning_mode=adapter.supported_reasoning[0],
                                     max_output_tokens=16)
                print(f"    {OK}  {key:17s} {r.total_tokens} tokens, "
                      f"reasoning info: {r.reasoning_exposure}")
            except Exception as e:  # noqa: BLE001 — reporting is the point
                fails += 1
                print(f"    {BAD}  {key:17s} {type(e).__name__}: {str(e)[:70]}")

    print(f"\n  {'ALL CHECKS PASS' if not fails else f'{fails} CHECK(S) FAILED'}\n")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
