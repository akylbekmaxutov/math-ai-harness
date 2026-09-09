"""One explanation per component of every file shown in the appendix.

deck/build.py refuses to build if a component has none. Docstrings, import
blocks, path bootstraps and `__main__` guards are described automatically by
build.py::_auto_note; everything else is written here.

    "path::component name": "explanation"
    "path::component name": ("explanation", "citation")
"""

C = {

# ======================================================================
# harness/
# ======================================================================
"harness/reasoning.py::ReasoningMode":
    "The harness's whole vocabulary for effort. A <code>str</code> subclass so it serialises "
    "into JSON as <code>\"high\"</code> with no custom encoder, while still comparing as an enum "
    "in code. <code>parse</code> is the single place a string becomes a mode, and it rejects an "
    "unknown value with the list of valid ones rather than defaulting to something plausible.",

"harness/reasoning.py::UNSUPPORTED":
    "A sentinel string rather than <code>None</code>, because <code>None</code> already reads as "
    "\"no reasoning was requested\" &mdash; which is a different and perfectly legitimate thing "
    "from \"this provider has no such setting\".",

"harness/reasoning.py::UnsupportedReasoningMode":
    "The exception that keeps an invented row out of the results table. It carries the provider, "
    "the model, the mode asked for and the modes that exist, so the stored record can say exactly "
    "what was unavailable. The runner catches it and writes <code>status: unsupported</code>; "
    "nothing anywhere substitutes a nearby effort.",

"harness/problems.py::ROOT · PROBLEMS_FILE":
    "The problem file is located relative to this module, not to the working directory, so "
    "<code>python3 -m harness.run</code> behaves the same from anywhere in the tree.",

"harness/problems.py::dataset_info":
    "The problem set's own description of itself &mdash; origin, selection criteria and how the "
    "answers were verified. Kept beside the problems rather than written into prose on "
    "a slide, so the page and the file cannot disagree about what the dataset is or where it came "
    "from. The Dataset section of this page is rendered entirely from what this returns.",

"harness/problems.py::Problem":
    "Frozen, so a problem cannot be mutated mid-study and two runs of the same id are two runs of "
    "the same problem. The important line is <code>for_solver()</code>: it returns the question "
    "and nothing else, which is why a prompt builder cannot leak the answer key by accident &mdash; "
    "it never holds it.",

"harness/problems.py::load_problems":
    "Reads the file into <code>{problem_id: Problem}</code> and raises on a duplicate id. A "
    "duplicate would silently drop one problem and quietly change every aggregate downstream. "
    "The set version is stamped onto each Problem, so a stored result records which edition of "
    "the questions produced it.",

"harness/problems.py::get":
    "One problem by id, with the known ids listed in the error. <code>KeyError: 'algebra_1'</code> "
    "alone would send you looking in the wrong file.",

"harness/answers.py::BOXED · MARKER":
    "Two patterns for the two ways a solution marks its conclusion: LaTeX <code>\\boxed{...}</code> "
    "and an explicit <code>FINAL ANSWER:</code> line. The boxed pattern allows one level of nested "
    "braces, which is what <code>\\boxed{\\frac{36}{11}}</code> needs.",

"harness/answers.py::extract_final_answer":
    "Takes the LAST marker, because a solution often restates its answer after a check. Returns "
    "<code>None</code> when nothing was marked rather than guessing from the last number on the "
    "page &mdash; a guess here would turn a formatting failure into a wrong answer, and the harness "
    "counts those separately for exactly that reason.",

"harness/answers.py::normalise":
    "Strips the presentation and keeps the value: dollar signs, <code>\\frac</code>, "
    "<code>\\text</code>, spacing macros, thousands separators, a trailing full stop. Deliberately "
    "narrow. It does not do algebra, because a checker clever enough to accept 2.4 for 12/5 is also "
    "clever enough to accept something it should not.",

"harness/answers.py::_as_fraction":
    "Parses an exact rational, or returns <code>None</code>. Notably it does NOT fall back to "
    "<code>float</code>: that is what stops <code>3.27</code> being accepted for <code>36/11</code>, "
    "which would quietly raise every model's score.",

"harness/answers.py::is_correct":
    "Exact match after normalisation, against the key and its declared aliases, with one piece of "
    "arithmetic allowed &mdash; if both sides are exact rationals they are compared as rationals, so "
    "<code>36/11</code> and <code>72/22</code> agree. This is the entire deterministic half of the "
    "evaluation, and it is boring on purpose.",

"harness/models.py::ADAPTERS":
    "Provider name to adapter class. The classes are imported at module load, which is safe because "
    "each adapter imports its SDK inside <code>__init__</code> &mdash; so the registry, the capability "
    "matrix and the whole <code>--mock</code> path work with no packages installed.",

"harness/models.py::ModelSpec":
    "What is being measured, pinned. <code>model</code> is the exact string that goes on the wire; "
    "<code>family</code> is what the judge rotation compares, so two models from the same lab could "
    "never end up judging each other's output as though they were independent.",

"harness/models.py::MODELS · SOLVERS":
    "The three models under study, in the order the website shows them. A rename is a change to this "
    "dict and therefore visible in a diff &mdash; never a silent substitution somewhere in a call site.",

"harness/models.py::get":
    "Model key to spec, naming the known keys on failure. The same pattern as "
    "<code>problems.get</code>: an error that tells you what to type next.",

"harness/models.py::supported_modes":
    "Reads <code>supported_reasoning</code> off the adapter CLASS &mdash; the same declaration that "
    "will refuse the call at runtime. One source of truth, so the grid drawn on the website and the "
    "behaviour of the harness cannot drift apart.",

"harness/models.py::capability_matrix":
    "The grid the website draws, computed with no API keys, no network and no SDK. This is the "
    "function that makes the Grok/medium cell a documented hole rather than a surprise discovered "
    "at run time.",

"harness/models.py::build_adapter":
    "Model key to a live adapter. Under <code>--mock</code> it returns the simulator but passes the "
    "real key as a label, so a rehearsal shows three different-looking models rather than one "
    "repeated three times &mdash; while <code>solver.model</code> still records "
    "<code>mock-model</code>, because that is what actually answered.",

"harness/models.py::pricing_for":
    "The price row for a model, falling back to the mock row. Small, but it means no call site has "
    "to reach into the pricing dict and decide what to do about a missing key.",

"harness/pricing.py::PRICING_VERSION · MODEL_PRICING":
    "Every price in the project, in one dict, each row carrying the date it was checked and where "
    "it came from. <code>reasoning_out</code> is a separate field defaulting to <code>None</code> "
    "(meaning \"billed at the output rate\") because assuming that costs money quietly. Bump "
    "<code>PRICING_VERSION</code> when a number changes; it is stored with every run.",

"harness/pricing.py::estimate_cost":
    "Itemised cost for one call. It RAISES on an unknown model rather than returning zero &mdash; a "
    "run silently reported as free is worse than a crash, because it survives into the summary "
    "table. <code>visible_out</code> subtracts reasoning tokens from output tokens, which is what "
    "stops them being charged twice given the adapters' normalisation.",

"harness/metrics.py::stopwatch":
    "A context manager around exactly one API call. <code>perf_counter</code> is monotonic, so a "
    "clock adjustment cannot produce a negative latency, and the <code>finally</code> means a call "
    "that raised still has a duration rather than a blank.",

"harness/metrics.py::usage_block":
    "Token counts with the unknowns preserved. <code>None</code> means \"the provider did not tell "
    "us\" and <code>0</code> means \"it told us, and the answer was none\" &mdash; collapsing them "
    "makes an average over the column silently wrong, so they stay distinct all the way to the screen.",

"harness/metrics.py::cost_block":
    "Three lines that hand the response's token counts to the pricing module. It exists so that no "
    "runner ever calls <code>estimate_cost</code> with hand-assembled arguments and gets the "
    "reasoning-token convention wrong.",

"harness/storage.py::ROOT · RESULTS · SOLVER_DIR · JUDGE_DIR · SCHEMA_VERSION":
    "Paths resolved relative to this module, and a schema version stored in every record &mdash; so "
    "when the shape changes, old files stay readable and the reader can say so instead of throwing "
    "a KeyError.",

"harness/storage.py::now_iso":
    "UTC, to the second. Timezone-aware, because a naive timestamp from a laptop in Astana and one "
    "from a CI runner in Frankfurt are not comparable and nothing in the file says so.",

"harness/storage.py::new_run_id":
    "A prefixed random id. The prefix (<code>solve_</code> / <code>judge_</code>) means a run id "
    "pasted into a chat message is self-describing.",

"harness/storage.py::solver_path":
    "The path IS the primary key: problem, model and mode are the three coordinates in the filename. "
    "\"Which runs exist\" is answerable with <code>ls</code>, re-running one cell overwrites exactly "
    "one file, and resumption is a file-existence check.",

"harness/storage.py::judge_path":
    "The same idea with five coordinates &mdash; candidate model and mode, then judge model and mode. "
    "The <code>__by__</code> separator keeps it readable when you are staring at a directory listing "
    "in front of an audience.",

"harness/storage.py::write_record":
    "Written to a temporary file and renamed, so a run interrupted mid-write leaves the previous "
    "good file in place rather than a truncated one every later command has to defend against. "
    "<code>os.replace</code> is atomic on POSIX and Windows alike.",

"harness/storage.py::read_record":
    "One record. Trivially thin, deliberately: it is the single place a stored file is decoded, so "
    "a future format change has one call site.",

"harness/storage.py::load_all":
    "Every record under a directory, sorted by path. Sorted so that a rebuild produces byte-identical "
    "output &mdash; an unsorted <code>rglob</code> would make the results file churn on every run and "
    "hide the real changes in a diff.",

"harness/storage.py::load_solver_runs":
    "The solver corpus, as a list. Named rather than inlined so the judge pipeline and the analysis "
    "both read it the same way.",

"harness/storage.py::load_judge_runs":
    "The verdict corpus. That this is a separate read from a separate directory is the structural "
    "proof that judging is a second pass over stored results, not something that happens during "
    "the experiment.",

"harness/runner.py::SYSTEM_PROMPT · DEFAULTS":
    "<code>max_output_tokens</code> must cover the thinking AND the written solution, since "
    "reasoning tokens are charged against it. On the first real study the largest run used 3182 "
    "output tokens with 2930 of them reasoning &mdash; 78% of what was then a 4096 cap, so a harder "
    "problem would have truncated. A cap costs nothing unless the tokens are generated, so it is "
    "sized with real headroom. The solver prompt is a module constant with a hash, not an f-string assembled at the call site. "
    "It asks for an explicit <code>FINAL ANSWER</code> marker and for exact form, which is what lets "
    "the answer checker stay narrow and reproducible.",

"harness/runner.py::prompt_sha":
    "Twelve hex characters of SHA-256 &mdash; short enough to read aloud, sensitive enough that any "
    "edit to the prompt is visible in every record produced after it.",

"harness/runner.py::ExperimentConfig":
    "Everything that decides what a run means, held together deliberately: a run is reproducible only "
    "if all of it is recorded, and the surest way to record all of it is for all of it to be one "
    "object that gets serialised in one place. <code>solver_block</code> renders it into the stored "
    "record, so the run and the file cannot disagree about what was configured.",

"harness/runner.py::run_one":
    "The whole of Part I: configure, call, time, collect, price, grade, store. The record is built "
    "first with <code>status: error</code> as the default, so every path out of the function returns "
    "a complete record and there is no way to fall off the end silently. The capability check happens "
    "before any call; grading happens after it, from the response text, by a checker that never "
    "touched the prompt.",

"harness/runner.py::run_and_store":
    "Runs one cell and writes it to its canonical path. Two lines, and they are the two lines that "
    "make the study resumable.",

"harness/env.py::ROOT · ALIASES":
    "The key names people actually have in their <code>.env</code>. Recognising them is a courtesy; "
    "announcing the substitution is not, because which credential a run authenticated with is part "
    "of the apparatus.",

"harness/env.py::load_dotenv":
    "Reads <code>KEY=value</code> without a dependency, and never overwrites a variable already set "
    "in the environment &mdash; an explicit export on the command line beats a file, which is what "
    "everyone expects and almost no minimal implementation does.",

"harness/env.py::canonicalise":
    "Copies a recognised alias into the canonical name and RETURNS what it did, so the caller can "
    "print it. Returning rather than printing keeps this module free of output and lets the preflight "
    "decide how to say it.",

"harness/run.py::constants":
    "The three-line path shim that lets the file run as a script as well as be imported, so a demo "
    "never fails on a packaging detail.",

"harness/run.py::summarise":
    "The one-screen report the workshop reads out loud. It prints the reasoning request that actually "
    "went on the wire, which of the three reasoning-exposure cases the run was in, "
    "<code>n/a</code> for a token count the provider withheld, and the pricing version beside the "
    "dollar figure.",

"harness/run.py::main":
    "Argument parsing, one run, one summary. The exit status treats <code>unsupported</code> as "
    "success: a cell that legitimately does not exist is not a failure of the command.",

"harness/run_all.py::constants":
    "The same path shim, for the same reason.",

"harness/run_all.py::plan":
    "Every cell of the matrix, in a stable order, computed BEFORE anything runs &mdash; which is what "
    "makes <code>--dry-run</code> print exactly what a real run would do rather than an approximation "
    "of it.",

"harness/run_all.py::main":
    "The loop. It reports how many cells will call an API and how many are unsupported before it "
    "starts, skips cells whose file already exists so a rate-limited study is finished by re-running "
    "the same command, and names the next command in the pipeline when it is done.",

"harness/check.py::constants":
    "Path shim, plus the two labels the report prints. <code>PASS</code> and <code>FAIL</code> as "
    "constants rather than literals, so the transcript embedded in the website is highlighted by a "
    "rule that cannot go stale.",

"harness/check.py::KEY_FOR":
    "Which environment variable each provider needs. Small, and it is the difference between "
    "\"missing GEMINI_API_KEY\" and an authentication error forty seconds into a batch.",

"harness/check.py::main":
    "Four checks and a bill, with no API call unless <code>--live</code> is passed. It prints the "
    "LENGTH of each key and the alias it came from, never a value; it fails on an unpriced model, "
    "because a run reported as free is worse than a crash; and it prints the exact size of the study "
    "before you commit to paying for it.",

# ======================================================================
# providers/
# ======================================================================
"providers/base.py::REASONING_EXPOSURE":
    "The three honest answers to \"what reasoning information do we have?\" &mdash; a "
    "provider-labelled summary, a token count and nothing else, or neither. Collapsing these three "
    "is the mistake this part of the workshop exists to prevent.",

"providers/base.py::ProviderError":
    "The apparatus failed. Named to make the distinction impossible to miss: this is not the model "
    "being wrong, and a study that counts it as a wrong answer has mislabelled its own failure.",

"providers/base.py::ProviderTimeout":
    "A subclass, so a caller can retry a timeout specifically while still catching every provider "
    "fault with the base class.",

"providers/base.py::ProviderResponse":
    "The one shape every adapter returns, and the place the token convention is ENFORCED rather "
    "than trusted. <code>__post_init__</code> catches an adapter that reports more reasoning "
    "tokens than output tokens — impossible if reasoning is included, as the convention requires "
    "— then corrects it and records the anomaly in the trace. This is not hypothetical: it "
    "shipped. The xAI adapter assumed the OpenAI convention and the first real call returned 313 "
    "completion tokens with 2520 reasoning tokens, understating the cost and producing a total "
    "smaller than one of its own parts. <code>reasoning_summary</code> holds only what the API "
    "explicitly labelled as reasoning; <code>reasoning_exposure</code> says which of the three cases "
    "we are in; <code>output_tokens</code> always includes reasoning tokens because the adapters "
    "normalise to that; and <code>reasoning_request</code> records what actually went on the wire "
    "rather than what we intended.",

"providers/base.py::Provider":
    "The whole contract, as a Protocol: three attributes and one method. Written down so that adding "
    "a fourth provider is a matter of satisfying an interface you can read in ten seconds, not of "
    "reverse-engineering three existing classes.",

"providers/base.py::BaseAdapter":
    "Shared bookkeeping, and deliberately nothing else. Its one real job is "
    "<code>require_supported</code>: it refuses, on every adapter's behalf, to answer a question the "
    "provider cannot answer. Enforcing that here rather than remembering it in three subclasses is "
    "what makes a fourth adapter correct by default.",

"providers/base.py::build":
    "Name to adapter, with each SDK imported inside its branch. That laziness is what lets a laptop "
    "with no packages and no network import the registry, draw the capability grid and rehearse the "
    "entire workshop.",

"providers/openai_adapter.py::EFFORT":
    "The identity map, written out anyway. The day a level is renamed on OpenAI's side, the change "
    "belongs in this dict and not in a string concatenation somewhere else.",

"providers/openai_adapter.py::OpenAIAdapter":
    "The simplest of the three translations, because the named effort maps one-to-one onto the "
    "harness's levels. <code>summary=\"auto\"</code> asks for a reasoning summary &mdash; a summary "
    "the model wrote, returned in a field the API labels as reasoning, and not the raw chain of "
    "thought. Provider exceptions are classified into timeout or error and re-raised as our own "
    "types, so the runner never sees the SDK's exception tree.",

"providers/openai_adapter.py::_reasoning_summary":
    "Reads only output items the API itself typed as <code>reasoning</code>, and returns "
    "<code>None</code> rather than an empty string when there were none &mdash; so \"the provider "
    "gave us nothing\" stays distinguishable from \"the provider gave us an empty summary\".",

"providers/gemini_adapter.py::THINKING_BUDGET":
    "Gemini takes no named effort at all; it takes a token budget. This dict is a WORKSHOP DECISION, "
    "documented as one: <code>HIGH</code> means \"effort=high\" on OpenAI and \"16k thinking tokens "
    "allowed\" here, and those are not the same physical quantity. The harness makes the arms "
    "comparable by naming them consistently; it cannot make them identical.",

"providers/gemini_adapter.py::GeminiAdapter":
    "The most interesting translation of the three. Note the token normalisation: google-genai "
    "reports thinking tokens SEPARATELY from candidate tokens, so this adapter adds them into "
    "<code>output_tokens</code> before returning &mdash; one convention, enforced at the edge, and "
    "the cost calculator never has to ask which provider it is looking at.",

"providers/gemini_adapter.py::_split_parts":
    "Separates answer parts from thought-summary parts using <code>part.thought</code>. That flag is "
    "the ONLY reason these two strings can be told apart, which is why the split happens here rather "
    "than by pattern-matching prose later.",

"providers/xai_adapter.py::BASE_URL · EFFORT":
    "xAI speaks the OpenAI chat-completions dialect, so the same SDK is pointed at a different base "
    "URL. The <code>EFFORT</code> map has TWO entries, not three: there is no middle setting, and "
    "that missing key is what eventually draws a hole in the results grid.",

"providers/xai_adapter.py::XAIAdapter":
    "The adapter that earns the abstraction its keep, because it is the one that cannot do everything "
    "the others can. Asking for MEDIUM raises before a request is built, the runner records "
    "<code>status: unsupported</code>, and the grid shows a hole &mdash; instead of a row labelled "
    "medium that is really the provider default.",

"providers/mock_adapter.py::BANNER":
    "Prefixed to every string the simulator emits, so a screenshot of simulated output taken out of "
    "context still says what it is.",

"providers/mock_adapter.py::_rng_int":
    "A stable pseudo-random integer from a string seed. Deterministic, so a rebuilt page is "
    "byte-identical and a rehearsal is repeatable &mdash; which matters more than randomness here.",

"providers/mock_adapter.py::MockAdapter":
    "A trace generator, not a model. It exists so the entire workshop can be rehearsed with no keys "
    "and no network, and so a live demo never depends on three APIs being up at once. It supports "
    "every level on purpose: the unsupported-mode path comes from the REAL adapter's declaration in "
    "<code>harness/models.py</code>, so a <code>--mock</code> rehearsal still exercises it. It also "
    "sleeps, so the latency the stopwatch records is a latency that actually elapsed rather than a "
    "number written into a field.",

"providers/mock_adapter.py::SOLUTIONS":
    "Three canned solutions per problem: one sound derivation, one that reaches the RIGHT answer by "
    "an invalid route, and one that is simply wrong. Those three cases are exactly what Part II needs "
    "on screen, and a random generator will not produce them.",

"providers/mock_adapter.py::_solution":
    "Picks one, weighted by effort so that higher effort draws the sound solution more often. A "
    "simulated tendency, not an observed one &mdash; and the page says so wherever the figure appears.",

"providers/mock_adapter.py::_mentions":
    "Identifies which canned problem is in the prompt by a distinctive phrase, because the solver "
    "prompt never carries the problem id &mdash; the simulator is subject to the same blinding as a "
    "real provider.",

"providers/mock_adapter.py::QUALITY_MARKERS · QUALITY_PROFILE":
    "How the simulated judge recognises its own canned solutions, and what it scores them. The jitter "
    "width is zero for a sound solution and two for the unjustified one, so simulated judges agree "
    "where agreement is easy and disagree exactly where the workshop needs a disagreement to point at. "
    "<code>correctness</code> never jitters, because that is a fact both judges can check.",

"providers/mock_adapter.py::_quality_of":
    "Reads the candidate solution back out of the judge prompt. This is the seam that makes the "
    "simulated verdicts coherent with the simulated solutions instead of independent noise.",

"providers/mock_adapter.py::_judge_json":
    "Emits strict JSON, so a simulated verdict is parsed by <code>judges/judge.py</code> through "
    "exactly the same code path as a real one. If the parser has a bug, the rehearsal finds it.",

# ======================================================================
# judges/
# ======================================================================
"judges/prompts.py::CRITERIA · ERROR_SEVERITY · VERDICTS · SYSTEM":
    "The rubric, and the part that matters is the written anchors: 5, 3 and 1 are described, so a 3 "
    "means the same thing to two different judges. <code>ERROR_SEVERITY</code> is ordered worst-last, "
    "which makes \"at least major\" a comparison rather than a set-membership test. The system prompt "
    "states in its second line that the judge is not told the correct answer.",

"judges/prompts.py::rubric_block":
    "Renders the rubric from the dict above, so the prompt, the parser, the agreement analysis and "
    "the website all read one definition. Adding a seventh criterion is a line in "
    "<code>CRITERIA</code>, and nothing else needs to know.",

"judges/prompts.py::output_block":
    "The exact shape required back, shown to the judge verbatim and used by the parser to validate "
    "what arrives. Writing it once means the instruction and the validation cannot disagree.",

"judges/prompts.py::build":
    "The complete judge prompt, and what matters is what is absent: no expected answer, no harness "
    "verdict, no solver identity, no reasoning mode, no token count, no cost. A judge that knows it "
    "is reading the expensive high-effort run from the famous model is not scoring the same thing as "
    "one that does not.",

"judges/judge.py::FENCE · _ANY_BACKSLASH · _CORRUPT":
    "Three patterns for the three ways a judge's JSON arrives broken. <code>FENCE</code> unwraps a "
    "fenced block &mdash; packaging, not judgement. <code>_ANY_BACKSLASH</code> separates a genuine "
    "JSON escape from a LaTeX command. <code>_CORRUPT</code> lists the control characters that can "
    "only be there because <code>\\frac</code> or <code>\\binom</code> was read as an escape, which "
    "is how a parse can succeed and still be wrong.",

"judges/judge.py::_has_corrupt_control":
    "Walks the PARSED values looking for those control characters. Checked against the values rather "
    "than their re-serialisation, because <code>json.dumps</code> turns a formfeed back into the six "
    "characters <code>\\u000c</code> and the search would never find it.",

"judges/judge.py::repair_latex_escapes":
    "The repair. A mathematical verdict fails to parse in two ways: <code>\\(x\\)</code> is an invalid "
    "escape and raises, while <code>5 \\times 7</code> is a VALID escape that parses and silently "
    "becomes a tab. The second is worse because nothing complains. So the rule is narrow and "
    "domain-specific &mdash; keep the escapes a model actually means, double every other backslash "
    "&mdash; and it is applied only after a strict parse has failed or produced a control character, "
    "with the fact recorded on the verdict. This recovered 19 of 25 lost verdicts on the first real "
    "run, at no cost, because the raw replies had been kept.",

"judges/judge.py::VerdictParseError":
    "Its own exception type, so a formatting failure is caught and recorded separately from a "
    "provider failure. The two have different causes and different fixes.",

"judges/judge.py::JudgeConfig":
    "The judge's counterpart to <code>ExperimentConfig</code>. <code>max_output_tokens</code> is the "
    "field to look at: reasoning tokens are charged against it, so a cap that seems generous for a "
    "JSON object is not generous at all once a high-effort judge has spent a thousand tokens "
    "thinking. Set to 1024 on the first real run, it truncated six verdicts mid-object and pushed "
    "18 of 96 replies right up to the limit. It is recorded with every verdict, because a cap that "
    "truncates changes what was measured. Deliberately the same shape as the solver config, because "
    "a judge run is a model run &mdash; and treating it as one is what gets it timed, priced and "
    "stored with the same rigour as the thing it is judging.",

"judges/judge.py::parse_verdict":
    "Tolerant about packaging &mdash; a fence, the whole reply, or the outermost braces &mdash; and "
    "strict about content: every criterion present, integers in 1&ndash;5, labels from the rubric's "
    "own lists. <code>4.5</code> is rejected, because a judge answering off a five-point scale has "
    "not used the rubric. <code>mean_score</code> is computed here, once, so no two places can "
    "average the rubric differently.",

"judges/judge.py::judge_one":
    "Structurally the solver runner again, with two additions specific to judging: the output must "
    "parse, and a failure to parse is stored as <code>parse_failed</code> with the raw text kept. "
    "Note <code>correct_per_harness</code> &mdash; recorded on the record for the analysis, and "
    "absent from the prompt built four lines above it.",

"judges/judge.py::judge_and_store":
    "One verdict to its canonical five-coordinate path. As with the solver, this is what makes the "
    "judging pass resumable.",

"judges/run_all.py::constants":
    "Path shim, so the module runs as a script as well as importing.",

"judges/run_all.py::DEFAULT_JUDGE_MODES":
    "Low and high &mdash; the two levels ALL THREE providers expose. Using the intersection keeps the "
    "judge sweep even; including medium would reproduce the solver grid's hole here and make the "
    "judge comparison uneven for one model only.",

"judges/run_all.py::judges_for":
    "The entire rotation: the other two models, compared on family so that two models from the same "
    "lab could never judge each other as though independent. No model is ever shown its own output, "
    "so self-preference cannot occur &mdash; a design that EXCLUDES the bias rather than measuring it "
    "and hoping it is small.",

"judges/run_all.py::candidates":
    "Only solver runs that produced text a judge could read. An unsupported cell has no solution in "
    "it, so it is skipped here and shown as a hole on the website rather than as a zero.",

"judges/run_all.py::main":
    "The judging loop, resumable on the same principle as the solver. It prints the verdict, the mean "
    "score, the reasoning score and the cost per line, so disagreement is visible in the terminal "
    "before anyone opens the website.",

# ======================================================================
# analysis/
# ======================================================================
"analysis/agreement.py::AGREEMENT_BANDS":
    "How far apart two 1&ndash;5 scores may be before we stop calling it agreement. Bands rather than "
    "a raw number, because the results interface pairs each label with an icon and a word &mdash; a "
    "status colour never carries the meaning alone.",

"analysis/agreement.py::band":
    "Difference to label. Four lines, and it is the whole of the agreement vocabulary &mdash; which is "
    "the point: every number in this module can be recomputed on a slide by hand while a room watches.",

"analysis/agreement.py::compare":
    "Two verdicts to one summary, per criterion rather than once. The last field, "
    "<code>verdict_agrees_but_scores_do_not</code>, is the reason the function exists: reporting only "
    "the verdict would call a three-point gap on completeness perfect agreement, which is the most "
    "common way judge reliability gets overstated.",

"analysis/agreement.py::judge_vs_ground_truth":
    "How often the judges' correctness score matched the deterministic check. Because the judges were "
    "never shown the answer key, this is a genuine measurement OF THE INSTRUMENT rather than of the "
    "solutions. The <code>&gt;= 4</code> threshold is stated rather than implied, and shown on screen "
    "beside the number, because the number moves if you change it.",

"analysis/agreement.py::severity_profile":
    "How often each judge reaches for each severity label. A judge that says <code>major</code> twice "
    "as often as another is a stricter instrument, and that is a property of the judge, not of the "
    "solutions it happened to be given &mdash; which is why it is reported next to the scores rather "
    "than averaged into them.",

"analysis/build_results.py::constants":
    "Path shim, so the module runs as a script.",

"analysis/build_results.py::OUT":
    "The single file the website reads. Everything upstream of it is many small files, because that "
    "is what makes a study resumable and inspectable; everything downstream wants one document.",

"analysis/build_results.py::_avg":
    "Mean over the values that exist, returning <code>None</code> when none do. This is where the "
    "null-preservation discipline from the metrics collector finally pays: an average over a column "
    "the provider never populated comes back as \"n/a\", not as zero.",

"analysis/build_results.py::slim_verdict":
    "One verdict as the page needs it. The raw text is kept ONLY when the parse failed &mdash; that is "
    "the one case where a human has to read it, and carrying it otherwise would triple the size of the "
    "inlined data for no benefit.",

"analysis/build_results.py::sample_request":
    "What actually goes on the wire for one problem. It calls the SAME constant and the SAME "
    "method the runner calls, so the request shown on the page cannot be a retyped approximation "
    "that has quietly drifted from what was really sent. The per-provider block is lifted out of "
    "the stored runs, so it is the request that genuinely happened rather than one reconstructed "
    "from the mapping table.",

"analysis/build_results.py::sample_judge_request":
    "The complete judge prompt for one real candidate, built by <code>judges/prompts.build</code> "
    "&mdash; again the real function, not a copy. Showing it in full is the fastest way to make the "
    "blinding checkable by eye: the expected answer, the harness's verdict and the solver's identity "
    "are all absent, and anyone can confirm that by reading it.",

"analysis/build_results.py::_problem_dicts":
    "Question text by id, for the judge sample above. A helper rather than an inline loop only so "
    "that <code>sample_judge_request</code> stays readable on a slide.",

"analysis/build_results.py::build":
    "The join. Verdicts are indexed by the candidate they judged and the effort they used, then "
    "attached to their solver run along with the agreement summary. The <code>simulated</code> flag is "
    "true if ANY row came from the simulator, because a mixed set is not a study and the page banners "
    "the whole section rather than individual rows.",

"analysis/build_results.py::summarise":
    "The comparison dashboard, computed once, here &mdash; not in the browser. Note the cost block: it "
    "reports solver and judge spend separately and gives the judges' share, which is the number people "
    "forget. With two judges at two efforts, evaluating usually costs more than solving did.",

"analysis/build_results.py::main":
    "Writes the file and prints what is in it &mdash; including a loud warning if the corpus is "
    "MIXED. That is the failure mode which looks most like success: <code>run_all</code> resumes "
    "from disk, so re-running it over a simulated set skips every simulated cell and the page "
    "then reports a study that never happened. It happened here on the first real run. Then: how many cells, how many verdicts, how many failed to "
    "parse, the split bill, and a banner if any of it is simulated. Then it names the next command, so "
    "the pipeline is discoverable from any point in it.",
}
