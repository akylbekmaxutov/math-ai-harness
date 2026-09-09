"""Reading .env, and accepting the key names people actually have.

Two small jobs, kept out of the adapters so that "where did this key come
from" has one answer.

`load_dotenv` reads a KEY=value file without a dependency, and never
overwrites a variable already set in the environment — an explicit export on
the command line beats a file, which is the behaviour everyone expects.

`canonicalise` copies a recognised alias (OPENAI_TOKEN, GROK_TOKEN, ...) into
the canonical name the adapters read, and returns what it did so the caller can
print it. It is announced rather than silent, because which credential a run
authenticated with is part of the record.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: canonical name -> names also accepted
ALIASES = {
    "OPENAI_API_KEY": ("OPENAI_TOKEN", "OPENAI_KEY"),
    "GEMINI_API_KEY": ("GOOGLE_API_KEY", "GEMINI_TOKEN", "GEMINI_KEY"),
    "XAI_API_KEY": ("XAI_TOKEN", "GROK_TOKEN", "GROK_API_KEY"),
}


def load_dotenv(path: Path | None = None) -> int:
    """Load .env into os.environ. Returns how many variables it set."""
    p = path or (ROOT / ".env")
    if not p.exists():
        return 0
    n = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.split(" #")[0].strip().strip("'\"")
        if key and val and key not in os.environ:
            os.environ[key] = val
            n += 1
    return n


def canonicalise() -> dict[str, str]:
    """Copy accepted aliases into canonical names. Returns {canonical: alias used}."""
    used = {}
    for canonical, alts in ALIASES.items():
        if os.environ.get(canonical):
            continue
        for alt in alts:
            if os.environ.get(alt):
                os.environ[canonical] = os.environ[alt]
                used[canonical] = alt
                break
    return used
