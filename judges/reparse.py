"""`python3 -m judges.reparse` — re-parse stored verdicts. No API calls.

The point of keeping every judge's raw reply is that a better parser can be
applied to a corpus you have already paid for. When the LaTeX-escape repair was
added, 25 of 96 verdicts had been discarded as unparseable — the judges had
answered correctly and the parser was wrong. Recovering them cost nothing but
this command.

    python3 -m judges.reparse            # report what would change
    python3 -m judges.reparse --apply    # rewrite the records in place

Only the parsed fields are rewritten. The raw reply, the usage, the timing and
the cost are exactly as they were recorded at call time, because those are
measurements and this is not a re-measurement.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import storage  # noqa: E402
from judges.judge import VerdictParseError, parse_verdict  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="judges.reparse", description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="write the recovered verdicts to disk")
    a = ap.parse_args(argv)

    paths = sorted(storage.JUDGE_DIR.rglob("*.json"))
    if not paths:
        print("\nNo stored verdicts. Run `python3 -m judges.run_all` first.\n")
        return 1

    counts = Counter()
    changes = []
    for p in paths:
        rec = storage.read_record(p)
        raw = rec.get("raw_text")
        if not raw:
            counts["no raw reply stored"] += 1
            continue
        try:
            parsed = parse_verdict(raw)
        except VerdictParseError as e:
            counts["still unparseable"] += 1
            if rec["status"] == "ok":
                counts["REGRESSION — was ok, now fails"] += 1
            continue
        was = rec["status"]
        if was == "ok" and rec.get("scores") == parsed["scores"] \
                and rec.get("verdict") == parsed["verdict"]:
            counts["unchanged"] += 1
            continue
        counts["recovered" if was != "ok" else "changed"] += 1
        changes.append((p, rec, parsed, was))

    for p, rec, parsed, was in changes:
        rec.update(parsed)
        rec["status"] = "ok"
        rec["error"] = None
        rec["reparsed"] = True
        if a.apply:
            storage.write_record(p, rec)

    print()
    for k, v in counts.most_common():
        print(f"  {v:3d}  {k}")
    print(f"  {len(changes):3d}  {'recovered/changed and WRITTEN' if a.apply else 'would change (dry run)'}")
    for p, rec, parsed, was in changes[:6]:
        print(f"        {was:13s} -> ok   {p.name}  verdict={parsed['verdict']} "
              f"mean={parsed['mean_score']}")
    if len(changes) > 6:
        print(f"        ... and {len(changes) - 6} more")
    if not a.apply and changes:
        print("\n  Nothing was written. Re-run with --apply.\n")
    elif a.apply:
        print("\n  next: python3 -m analysis.build_results\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
