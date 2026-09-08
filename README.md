# How Do We Actually Know an AI Agent Is Good at Math?

A model-agnostic evaluation harness for tool-using agents, instantiated on competition
mathematics, plus the two-session workshop built on top of it.

**Instructor:** Akylbek Maxutov — Senior Data Scientist, ISSAI, Nazarbayev University, Astana

> A harness is a measurement apparatus. A judge is one instrument inside it. Harness
> engineering is what makes the measurement reproducible; judge hygiene is what makes that
> particular instrument trustworthy. Neither produces a meaningful number alone.

## The pages

| File | What it is |
|---|---|
| [`index.html`](index.html) | **Start here.** What the workshop is: both sessions, format, syllabus |
| [`about.html`](about.html) | The instructor, and selected publications |
| [`workshop.html`](workshop.html) | The workshop itself — one continuous document, 28 parts |

`workshop.html` runs as a single narrative: the 2026 news that motivates it, then the harness
built one step at a time (explanation and diagram first, then the code that implements it),
then LLM-as-a-judge, then the complete source of every file.

All three are generated. Edit `deck/*.src.html` and run:

```bash
python3 deck/build.py
```

Code shown on a page is extracted from the real module at build time, so a page cannot drift
from the code it quotes. The build **fails** if any code block or component has no
explanation — see `deck/explain.py` and `deck/components_explain.py`.

## Run it — one line

```bash
python3 scripts/pipeline.py --mock     # offline rehearsal: no keys, no network
python3 scripts/pipeline.py --smoke    # one real rollout per model, then stop
python3 scripts/pipeline.py            # the real study (asks before spending)
```

The pipeline runs the standing check, the rotation corpus, the reasoning-effort sweep,
offline grading and the report — stopping at the first failure. Each stage is the command
you would have typed, run as a subprocess, so there is no second implementation to drift.

Dial the scale with `--n` (rotation rollouts), `--sweep-n` (per effort arm), `--task`,
`--no-sweep`, `--ablation`.

The 40-trace calibration is deliberately **not** in the pipeline — it needs a human:

```bash
python3 scripts/label.py --n 40
python3 scripts/report.py --json
```

### Or stage by stage

```bash
python3 scripts/initial_check.py
python3 scripts/run.py --config all --n 10 --mock
python3 scripts/run.py --config all --n 5 --mock --sweep-effort
python3 scripts/grade.py --all --mock --ablation 120
python3 scripts/report.py
python3 display/replay.py --trace traces/S1/aime2026-07.jsonl --speed 8
```

`--mock` uses the offline simulator in `agent/providers.py`. Every trace it writes is marked
`simulated: true`, gets its own `config_hash`, and `report.py` prints a banner over any figure
derived from it. **Nothing produced this way is a measurement of a real model.**

### Keys

Canonical: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `XAI_API_KEY`. Common alternatives —
`OPENAI_TOKEN`, `GEMINI_TOKEN`, `GROK_TOKEN`, `GOOGLE_API_KEY` — are accepted and copied into
the canonical name at startup, with a line printed saying which was used.

`tasks/math/problems.jsonl` ships **placeholder problems**, brute-force verified but not AIME.
`python3 tasks/math/loader.py --sync` replaces them with the real set.

## Layout

```
core/       contracts · trace recorder · config pinning · budget
agent/      hand-written loop · tools · sandbox · providers (+ offline simulator)
runner/     rollout orchestration · seven-way outcome classifier
verifiers/  answer_match · tool_replay · process_judge (blinding) · masked_cont
metrics/    aggregate (pass@k, pass^k) · judges (agreement, severity, blinding) · cost
tasks/math/ loader · problems.jsonl        display/  live + replay, one renderer
scripts/    initial_check · run · grade · label · report
```

`grade.py` existing as a separate entry point from `run.py` is the structural proof that
the architecture is trace-first: three of the four verifiers were written after the corpus
existed and applied to all of it with zero solver calls.

## Licence

Code MIT. Workshop materials CC BY 4.0. Problems from AIME 2026 via MathArena
(CC BY-NC-SA 4.0) once synced — cite Balunović et al. (2025) and Dekoninck et al. (2026).
