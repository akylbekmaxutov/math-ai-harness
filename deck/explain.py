"""One explanation per code block, keyed by "path|selector".

deck/build.py refuses to build if a code block on the page has no entry here.
That is the mechanism behind the rule: nothing goes on screen unexplained.

    lead    — one sentence: what this code is for
    points  — (token, explanation) pairs; the token is something visible in
              the snippet, so the audience can find what is being described
    kind    — "judge" tints the block amber, for the Part II material
"""

EXPLAIN = {

# ------------------------------------------------------------- Part I
"harness/problems.py|Problem": dict(
    lead="Everything the harness knows about one problem &mdash; and a method that hands out <b>only the part the solver may see</b>.",
    points=[
        ("problem_id", "A stable name. A run written today has to join a judge verdict written on Friday; matching on question text works right up until someone fixes a typo, and then silently stops."),
        ("for_solver()", "Returns the question and nothing else. This is the only thing that ever reaches a prompt."),
        ("expected_answer", "Present on the object, but reachable only through this attribute &mdash; which only the grader reads. A prompt builder cannot leak the key by accident because it never holds it."),
        ("answer_aliases", "The forms the same value legitimately takes. Declared per problem rather than inferred, so the checker stays boring and reproducible."),
        ("frozen=True", "A problem cannot be mutated mid-study. Two runs of the same id are two runs of the same problem."),
    ]),

"harness/problems.py|load_problems": dict(
    lead="Reads the problem file into <code>{problem_id: Problem}</code>, and <b>refuses a duplicate id</b>.",
    points=[
        ("duplicate problem_id", "Raises. A duplicated id would silently drop one problem and quietly change every aggregate computed downstream."),
        ("version", "The problem-set version is stamped onto every Problem, so a stored result records which edition of the questions produced it."),
        ("insertion-ordered", "The dict preserves file order, so the website's problem order is the file's order and never surprises you mid-talk."),
    ]),

"harness/runner.py|ExperimentConfig": dict(
    lead="Everything that decides what a run <i>means</i>, in <b>one object</b>.",
    points=[
        ("held together", "A run is reproducible only if all of this is recorded, and the surest way to record all of it is for all of it to be one thing that gets serialised in one place."),
        ("reasoning_mode", "An arm of the study, not a tuning knob. Two runs at different effort are two different apparatuses and must never be pooled."),
        ("system_prompt", "Carried on the config, hashed into the record. Change one character and every number downstream means something else."),
        ("solver_block", "Renders the config into the stored record. One method, so the run and the file cannot disagree about what was configured."),
        ("mock", "Swaps in the offline simulator while keeping the model key, so a rehearsal exercises the same code path as the real thing."),
    ]),

"harness/runner.py|SYSTEM_PROMPT": dict(
    lead="The solver prompt, pinned as a <b>constant with a hash</b> rather than an f-string assembled at the call site.",
    points=[
        ("FINAL ANSWER", "An explicit marker. Without one, extracting the answer means guessing at the last number on the page &mdash; which turns a formatting failure into a wrong answer, and those are different faults."),
        ("exact form", "Asks for a fraction rather than a decimal, so the answer checker never has to decide whether 3.27 is close enough to 36/11. It is not."),
        ("prompt_sha", "Twelve hex characters of SHA-256, stored with every run. Short enough to read aloud, sensitive enough that any edit is visible."),
    ]),

"harness/runner.py|run_one": dict(
    lead="The whole of Part I in one function: configure, call, time, collect, price, grade, store &mdash; and it <b>never crashes the study</b>.",
    points=[
        ("record = {...}", "The record is built FIRST, with status 'error' as the default. Every path out of this function therefore returns a complete record; there is no way to fall off the end silently."),
        ("supported_modes", "The capability check happens before any call, from the adapter class. An unsupported cell costs nothing and is still recorded."),
        ("for attempt in", "One retry on a transport fault, and the attempt count is stored &mdash; 'it worked on the third try' is data."),
        ("else:", "The for/else. If the loop never broke, every attempt failed, and the error is recorded rather than raised."),
        ("is_correct(final, ...)", "Grading happens here, AFTER the call, from the response text, by a checker that never touched the prompt."),
        ('"no_answer_marked"', "A response with no marked answer is a formatting failure, not a wrong answer. Counted separately, because conflating them flatters or punishes a model for the wrong reason."),
    ]),

"providers/base.py|ProviderResponse": dict(
    lead="The <b>one shape every adapter returns</b>. Three different APIs go in; this comes out.",
    points=[
        ("reasoning_exposure", "The most important field on the page. It says which of three situations we are in: the provider returned a labelled summary, it returned only a token count, or it returned neither."),
        ("reasoning_summary", "Only what the API explicitly labelled as reasoning. No adapter is permitted to put model prose here and call it a trace."),
        ("output_tokens", "Includes reasoning tokens, because that is the convention the adapters normalise to &mdash; so the cost calculator never has to ask which provider it is looking at."),
        ("reasoning_request", "What the adapter actually put on the wire, not what we intended. The trace records the request, so a reader can check it rather than trusting the label."),
        ("total_tokens", "Derived, not stored, so it cannot drift from its two inputs."),
    ]),

"providers/base.py|BaseAdapter.require_supported": dict(
    lead="The single line that <b>keeps an invented row out of the results table</b>.",
    points=[
        ("supported_reasoning", "Declared per adapter as a class attribute, so the capability grid on the website reads the same declaration that will refuse the call."),
        ("raise", "Raising is the whole point. The alternatives &mdash; sending a nearby effort, or sending nothing and letting the provider default decide &mdash; both produce a row labelled 'medium' that is not a medium measurement."),
        ("called by every adapter", "Enforced in the base class rather than remembered in three subclasses, so a fourth adapter gets the behaviour for free."),
    ]),

"providers/base.py|build": dict(
    lead="Name &rarr; adapter instance, with the SDK imported <b>lazily</b>.",
    points=[
        ("from providers.x import", "Inside the branch, not at module top. A laptop with no packages installed and no network can still import the registry, draw the capability grid, and run the whole workshop with --mock."),
        ('provider == "mock"', "The simulator is a provider like any other, so the rehearsal path is the real path with one class swapped."),
        ("raise ProviderError", "An unknown provider is named in the error. 'unknown provider xai2' is a bug report; a KeyError three frames deep is a mystery."),
    ]),

"providers/openai_adapter.py|OpenAIAdapter.generate": dict(
    lead="The entire OpenAI translation. <b>Ten lines of request-shaping</b>, and the rest is normalising what comes back.",
    points=[
        ('{"effort": ..., "summary": "auto"}', "The named effort maps one-to-one onto the harness's levels. `summary: auto` asks for a reasoning summary &mdash; a summary the model wrote, returned in a field the API labels as reasoning. Not the raw chain of thought."),
        ("require_supported", "First line of the method, before any request is built."),
        ("except Exception", "A provider fault is a HARNESS failure, not a model failure. It is classified into timeout or error and re-raised as our own type, so the runner never has to know about the SDK's exception tree."),
        ("output_tokens_details", "Where the reasoning token count lives. Already counted inside output_tokens, which is the convention, so nothing is added here."),
        ('"summary" if summary else "token_count_only"', "The honesty branch. If no summary came back we say what we actually have &mdash; a number &mdash; rather than leaving the field looking populated."),
    ]),

"providers/openai_adapter.py|_reasoning_summary": dict(
    lead="Collects the summary parts of the reasoning output items, and returns <b><code>None</code> rather than <code>&quot;&quot;</code></b> when there were none.",
    points=[
        ('type != "reasoning"', "Only items the API itself labelled as reasoning are read. Everything else is response text and is stored as response text."),
        ("return ... or None", "The load-bearing detail. Empty string would make 'the provider gave us nothing' indistinguishable from 'the provider gave us an empty summary', and those are different facts about the provider."),
    ]),

"harness/reasoning.py|ReasoningMode": dict(
    lead="Three levels, and <b>one vocabulary the whole harness speaks</b>.",
    points=[
        ("str, Enum", "A str subclass, so a mode serialises into JSON as 'high' without a custom encoder, and still compares as an enum in code."),
        ("parse", "The only place a string becomes a mode. An unknown value is rejected with the list of valid ones, rather than defaulting to something plausible."),
        ("LOW / MEDIUM / HIGH", "Deliberately generic. Nothing above the adapters knows that OpenAI takes a name and Gemini takes a token budget."),
    ]),

"providers/gemini_adapter.py|THINKING_BUDGET": dict(
    lead="Gemini takes no named effort at all &mdash; it takes a <b>token budget</b>. This dict is where our three levels become three budgets.",
    points=[
        ("512 / 4096 / 16384", "A workshop decision, documented as one. HIGH means 'effort=high' on OpenAI and '16k thinking tokens allowed' here, and those are not the same physical quantity."),
        ("say this out loud", "The harness makes the arms comparable by NAMING them consistently. It cannot make them identical, and pretending otherwise is how cross-provider comparisons quietly stop meaning anything."),
        ("reasoning_request", "The budget actually sent travels into every stored result, so a reader can check what was asked for instead of trusting the label."),
    ]),

"providers/xai_adapter.py|EFFORT": dict(
    lead="Two entries, not three. xAI exposes <b>low and high, and no middle setting</b> &mdash; and this is the dict that says so.",
    points=[
        ("MEDIUM is absent", "Which makes `supported_reasoning` two long, which makes the runner write `status: unsupported`, which makes the grid draw a hole. One missing dict key, propagated honestly all the way to the screen."),
        ("the alternative", "Send 'low' instead, or send nothing and let the default decide. Either produces a row labelled medium that is not a medium measurement, and no one reading the table could ever tell."),
    ]),

"harness/metrics.py|usage_block": dict(
    lead="Token counts, with <b>the unknowns preserved as unknowns</b>.",
    points=[
        ("None if ... is None", "`null` means 'this provider did not tell us'. `0` means 'it told us, and the answer was none'. Collapsing them makes an average over the column silently wrong."),
        ("reasoning_share", "How much of the output was reasoning &mdash; the number the effort comparison is actually about. Also null when the provider did not break it out, rather than 0."),
        ("int(...)", "Coerced once, here, so nothing downstream has to defend against a string that came back from an SDK."),
    ]),

"harness/metrics.py|stopwatch": dict(
    lead="Wall-clock latency around <b>exactly one API call</b>, and nothing else.",
    points=[
        ("perf_counter", "Monotonic, so a clock adjustment mid-run cannot produce a negative latency."),
        ("finally:", "The elapsed time is recorded even when the call raised, so a timeout has a duration rather than a blank."),
        ("wall clock", "Not the provider's own timing. What the experiment compares is what a user would wait for, queueing and all."),
    ]),

"harness/pricing.py|MODEL_PRICING": dict(
    lead="<b>One place where prices live</b>, each row carrying the date it was checked.",
    points=[
        ("reasoning_out", "A separate field, defaulting to None &mdash; meaning 'billed at the output rate', which is the common case. It is a field rather than an assumption because assuming costs money quietly."),
        ("checked / source", "Per row. Six months from now, this is what tells you which number to distrust."),
        ("PRICING_VERSION", "Stored with every run. A cost is only reproducible if you know which price list produced it."),
        ("mock-model", "Priced at zero and labelled. The simulator is charged against the real model's list so the cost views can be rehearsed &mdash; but the row exists so nothing is ever unpriced."),
    ]),

"harness/pricing.py|estimate_cost": dict(
    lead="The cost of one call, <b>itemised</b> &mdash; and it refuses a model it has no price for.",
    points=[
        ("raise KeyError", "An unpriced model raises rather than costing zero. A run silently reported as free is worse than a crash, because it survives into the summary table."),
        ("visible_out", "Output minus reasoning. Adapters normalise so reasoning tokens are always INSIDE output_tokens, so this subtraction is what stops them being charged twice."),
        ("returned as a breakdown", "Not one float, so the page can show where the money went. At high effort the reasoning tokens are usually most of it."),
        ("pricing_version", "Returned with the numbers, so the version travels wherever the cost travels."),
    ]),

"harness/storage.py|solver_path": dict(
    lead="<b>The path is the primary key.</b> One function, and the entire join is decided.",
    points=[
        ("problem_id / model__mode", "Three coordinates in a filename. 'Which runs exist' is answerable with `ls`, and re-running one cell overwrites exactly one file."),
        ("__", "A double underscore, because model keys contain single hyphens and dots. A separator that cannot occur in either coordinate is what keeps the filename parseable."),
        ("resumption", "The runner skips a cell whose file exists, so a study interrupted by a rate limit is finished by re-running the same command."),
    ]),

"harness/storage.py|write_record": dict(
    lead="Writes one record <b>atomically</b>, so an interrupted run never leaves a truncated file behind.",
    points=[
        ("with_suffix('.tmp')", "Written beside the target, on the same filesystem, so the rename is atomic."),
        ("os.replace", "Atomic on POSIX and Windows. Either the old good file is there or the new good file is there; there is no third state for later commands to defend against."),
        ("indent=2", "Readable. A workshop audience can open one in an editor, and a file that is readable is a file that gets checked."),
        ("ensure_ascii=False", "Mathematics contains non-ASCII characters. Escaping them would make the stored file unreadable for no benefit."),
    ]),

# ------------------------------------------------------------- Part II
"judges/prompts.py|build": dict(
    kind="judge",
    lead="The complete judge prompt for one candidate. <b>Note what is absent.</b>",
    points=[
        ("no expected answer", "The judge does the mathematics itself. This costs accuracy on criterion 1 and buys the other five: a judge told the answer was right rationalises the route that reached it."),
        ("no harness verdict", "The outcome is the single most contaminating thing you can show a judge, because it leaks into every criterion, not just the correctness one."),
        ("no solver identity", "No model name, no reasoning mode, no token count, no cost. 'This is the expensive high-effort run from the famous model' is not evidence about the argument."),
        ("claimed_answer", "The judge IS shown what the solution concludes &mdash; it has to be, to score whether the conclusion follows. It is not shown whether that was right."),
        ("one function", "Everything assembled in one place, so 'what was the judge asked?' has a single answer that fits on a slide."),
    ]),

"judges/prompts.py|CRITERIA": dict(
    kind="judge",
    lead="Six criteria, and the part that matters is the <b>written anchors</b>.",
    points=[
        ("5 = / 3 = / 1 =", "The anchors. Without them a 3 means whatever each judge felt like, two judges cannot be compared, and a disagreement cannot be located."),
        ("correctness vs reasoning", "Separated deliberately. The whole workshop turns on a solution that scores 5 on the first and 1 on the second."),
        ("efficiency", "Scored, but never used as a tie-break on validity. It is here because 'the model wandered for 3000 tokens' is a real property worth recording."),
        ("a dict", "Adding a seventh criterion is a line here. The prompt, the parser, the agreement analysis and the website all read this dict, so they cannot disagree about what the rubric is."),
    ]),

"judges/judge.py|parse_verdict": dict(
    kind="judge",
    lead="<b>Tolerant about packaging, strict about content.</b> A verdict that does not parse is nothing, not a low score.",
    points=[
        ("candidates = [...]", "A fenced block, the whole reply, then the outermost braces. Packaging is a formatting quirk and not a judgement, so three shapes are accepted."),
        ("missing criterion", "Rejected. A verdict with five of six criteria would otherwise average differently from every other verdict in the study."),
        ("float(raw) == int(...)", "4 and 4.0 are accepted; 4.5 is not. A judge answering off a five-point scale has not used the rubric."),
        ("ERROR_SEVERITY / VERDICTS", "Labels are checked against the rubric's own lists, so an invented severity cannot enter the severity profile."),
        ("mean_score", "Computed here, once, from validated numbers &mdash; so no two places in the codebase can average the rubric differently."),
    ]),

"judges/run_all.py|judges_for": dict(
    kind="judge",
    lead="The entire rotation: <b>the other two models, never the candidate's own family</b>.",
    points=[
        ("family", "Compared on family rather than model key, so two models from the same lab could never end up judging each other's output as though they were independent."),
        ("excludes rather than measures", "No model is ever shown its own output, so self-preference cannot occur. That is a stronger claim than measuring the bias and hoping it is small."),
        ("three lines", "A design decision this important should be short enough to read aloud and check."),
    ]),

"analysis/agreement.py|compare": dict(
    kind="judge",
    lead="Two verdicts for the same candidate &rarr; one agreement summary. <b>The last field is the slide.</b>",
    points=[
        ("per_criterion", "Agreement is computed per criterion, not once. Two judges can agree on the verdict and be three points apart on completeness."),
        ("band()", "Maps a difference onto a word: exact, close, moderate, low. Words, because the results interface pairs each one with an icon &mdash; a status colour never carries the meaning alone."),
        ("severity_distance", "Uses the ordered severity scale, so 'none vs minor' and 'none vs incorrect_conclusion' are not the same disagreement."),
        ("verdict_agrees_but_scores_do_not", "The flag this function exists for. Reporting only the verdict would call that case perfect agreement, which is the most common way judge reliability gets overstated."),
        ("comparable: False", "When one judge failed, the pair is marked not comparable rather than silently scored against a default."),
    ]),

"analysis/agreement.py|judge_vs_ground_truth": dict(
    kind="judge",
    lead="How often the judges' correctness score matched the deterministic check &mdash; <b>a real measurement of the instrument</b>.",
    points=[
        ("never told the answer", "Which is what makes this number meaningful. If the judge had been shown the key, this would measure its reading comprehension."),
        (">= 4 counts as correct", "A stated threshold rather than an implied one. It is on screen next to the number, because the number moves if you change it."),
        ("correct_per_harness", "Recorded on the judge record but absent from the judge prompt &mdash; the two facts that make this comparison both possible and honest."),
        ("n = 0", "Returns a count rather than a rate when there is nothing to measure. A rate over zero verdicts is a divide by zero dressed as a finding."),
    ]),

# ------------------------------------------------------------- terminals
"deck/term/run_one.txt": dict(
    lead="One cell of the matrix, exactly as the command prints it. <b>A real captured transcript, not a mock-up.</b>",
    points=[
        ("requested:", "The literal reasoning control that went on the wire, not just the level we asked for."),
        ("reasoning info exposed", "Which of the three cases this run was in: a provider-labelled summary, a token count only, or nothing."),
        ("prices 2026-09-08", "The pricing version. A dollar figure without it is not a figure."),
        ("SIMULATED", "Printed on every simulated run. The offline simulator is for rehearsal, and nothing it produces is a measurement of a real model."),
    ]),

"deck/term/run_all.txt": dict(
    lead="The whole solver matrix. <b>27 cells, 24 calls, 27 files.</b>",
    points=[
        ("24 will call an API", "Computed before anything runs, from the adapter classes. You know the size and shape of the study before you spend anything."),
        ("--", "The unsupported cells. Grok exposes no medium effort, so those three rows are written without a call being made."),
        ("skip (exists)", "Resumption. A study interrupted by a rate limit is finished by re-running the same command."),
    ]),

"deck/term/check.txt": dict(
    lead="The preflight. Everything that would otherwise fail forty seconds into a batch, checked <b>before a single call</b>.",
    points=[
        ("taken from OPENAI_TOKEN", "An accepted alias was copied into the canonical name, and the substitution is ANNOUNCED. Which credential a run authenticated with is part of the apparatus."),
        ("set (164 chars)", "The length, never the value. No command in this repository prints a key."),
        ("CAPABILITY MATRIX", "Read from the adapter classes, so this table and the runtime behaviour cannot disagree."),
        ("STUDY SIZE", "The bill, before you commit to it."),
    ]),

"deck/term/build.txt": dict(
    lead="The join: many small files into the one document the website reads.",
    points=[
        ("judges are 70% of it", "Falls straight out of the data. Two judges at two efforts is four calls per candidate, and evaluating usually costs more than solving &mdash; a fact most evaluation reports never mention."),
        ("SIMULATED DATA", "Propagated from the runs into the results file, and from there into a banner over every figure on the page."),
        ("next: python3 deck/build.py", "Each command names the next one, so the pipeline is discoverable from any point in it."),
    ]),
}
