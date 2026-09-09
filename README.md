# How Do We Actually Know an AI Agent Is Good at Math?

An evaluation harness and an LLM-as-a-judge pipeline, plus the workshop built on top of them.

**1st International Conference and Workshop on Mathematics and Artificial Intelligence**
**September 9–11, 2026**

**Instructor:** Akylbek Maxutov — Senior Data Scientist, ISSAI, Nazarbayev University, Astana

> A model returns 42. The answer key says 42. Almost every evaluation you will read stops
> there. Evaluating an AI agent means evaluating the entire experimental system around it —
> not merely asking whether the final answer is correct.

## The experiment

```
3 problems  ×  3 models  ×  3 reasoning modes   =  27 cells, 24 of which exist
    then every solution judged by the other two models, at two judge efforts
                                                =  96 verdicts
```

| | |
|---|---|
| Models | GPT-5.6-Terra · Gemini-3.8-Flash · Grok 4.6 |
| Reasoning modes | `low`, `medium`, `high` — Grok exposes no `medium`, so those three cells are recorded as `unsupported` rather than silently substituted |
| Judges | the other two models, never the candidate's own family |
| Judge efforts | `low` and `high` — the two levels all three providers expose |

## The pages

| File | What it is |
|---|---|
| [`index.html`](index.html) | **Start here.** What the workshop is |
| [`about.html`](about.html) | The instructor, and selected publications |
| [`workshop.html`](workshop.html) | The workshop itself — collapsible contents, both parts, the interactive results |

All three are generated. Edit `deck/*.src.html` and run:

```bash
python3 deck/build.py
```

Code shown on a page is extracted from the real module at build time, so a page cannot drift
from the code it quotes. The build **fails** if a code block or component has no explanation
(`deck/explain.py`, `deck/components_explain.py`), if a contents link points at an id that is
not in the page, or if a command shown on screen names a module that does not exist.

## Run it

### Rehearse offline — no keys, no network, no spend

```bash
python3 -m harness.run_all --mock      # 27 solver cells
python3 -m judges.run_all --mock       # 96 verdicts
python3 -m analysis.build_results      # join into results/workshop_results.json
python3 deck/build.py                  # inline it into workshop.html
```

`--mock` uses the offline simulator in `providers/mock_adapter.py`. Every record it writes is
marked `simulated: true`, and the website puts a banner over every figure derived from it.
**Nothing produced this way is a measurement of a real model.**

### The real study

```bash
pip install -r requirements.txt
cp .env.example .env                   # then fill in the three keys
python3 -m harness.check               # preflight: keys, problems, prices, capability, cost
python3 -m harness.run_all             # 24 API calls · resumable
python3 -m judges.run_all              # 96 verdicts
python3 -m analysis.build_results
python3 deck/build.py
```

Both `run_all` commands skip a cell whose file already exists, so a study interrupted by a
rate limit is finished by re-running the same command. Pass `--force` to redo everything,
`--dry-run` to see the plan without spending.

### One cell

```bash
python3 -m harness.run --problem algebra_01 --model gpt-5.6-terra --reasoning high
```

### Present

`workshop.html` opens directly from the filesystem — the results are inlined at build time,
so a presentation never depends on a server, a network or an API key. If you prefer a server:

```bash
python3 -m http.server 8000
```

## Keys

`OPENAI_API_KEY`, `GEMINI_API_KEY`, `XAI_API_KEY`. These alternatives are also accepted and
copied into the canonical name at startup, with a line printed saying which was used:
`OPENAI_TOKEN`, `GEMINI_TOKEN`, `GOOGLE_API_KEY`, `GROK_TOKEN`, `XAI_TOKEN`.

Keys are read from the environment by the provider adapters and nowhere else. They never
appear in the HTML, in JavaScript, in committed source, or in a stored result. `.env` is
gitignored; `.env.example` holds placeholders only.

## Layout

```
harness/     reasoning modes · problems · answers · models · pricing
             metrics · storage · runner · env      + run · run_all · check
providers/   base (one interface) · openai · gemini · xai · mock (offline simulator)
judges/      prompts (the rubric) · judge (call + parse) · run_all (the rotation)
analysis/    agreement · build_results
problems/    problems.json — three problems, answers brute-force verified
results/     solver/<problem>/<model>__<mode>.json
             judges/<problem>/<model>__<mode>__by__<judge>__<judgemode>.json
             workshop_results.json          <- what the website reads
deck/        build.py · outline.py · deck.css · *.src.html · explain.py
             components_explain.py · term/ (real captured transcripts)
```

Three design commitments the code is built to make checkable:

1. **The solver never sees the answer key.** `Problem.for_solver()` returns the question and
   nothing else; the key is reachable only through an attribute the grader alone reads.
2. **The judge never sees the answer key either.** It scores correctness by doing the
   mathematics itself, so the gap between its correctness score and the deterministic check
   is a real measurement of the judge — reported on the results page.
3. **An unavailable capability is recorded as unavailable.** A reasoning mode a provider does
   not expose becomes `status: "unsupported"` and a hole in the grid, never a substituted
   default wearing the wrong label.

## Licence

Code MIT. Workshop materials CC BY 4.0.
