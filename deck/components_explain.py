"""One explanation for every component of every file shown in full.

Keyed "path::component-name", matching deck/components.py::split(). Values are
either a string, or (text, citation) where the component implements something
that comes from the literature — the citation is rendered beside the code so
the claim and its source sit together.

deck/build.py refuses to build if a component has no entry.
"""

# Citations used more than once, so the wording stays identical everywhere.
YAO = "Yao et al. (2024), τ-bench, arXiv:2406.12045"
MILLER = "Miller (2024), Adding Error Bars to Evals, arXiv:2411.00640"
KIRGIS = "Kirgis et al. (2026), Log analysis is necessary, arXiv:2605.08545"
ZHU = "Zhu et al. (2025), Agentic Benchmark Checklist, arXiv:2507.02825"
KAPOOR25 = "Kapoor et al. (2025), Holistic Agent Leaderboard, arXiv:2510.11977"
KAPOOR24 = "Kapoor et al. (2024), AI Agents That Matter, arXiv:2407.01502"
GU = "Gu et al. (2025), A Survey on LLM-as-a-Judge, arXiv:2411.15594"
SOHN = "Sohn, Lee et al. (2026), How to Correctly Report LLM-as-a-Judge, arXiv:2511.21140"
SHI = "Shi et al. (2025), Position bias in LLM-as-a-Judge, arXiv:2406.07791"
WATAOKA = "Wataoka et al. (2024), Self-Preference Bias, arXiv:2410.21819"
POMBAL = "Pombal et al. (2026), Self-Preference in Rubric-Based Evaluation, arXiv:2604.06996"
LEAK = "Li et al. (2025), Preference Leakage, arXiv:2502.01534"
CURSE = "Zheng et al. (2025), Curse of Knowledge, arXiv:2509.03419"
PROCESS = "Zheng et al. (2025), ProcessBench, arXiv:2412.06559"
VERGA = "Verga et al. (2024), Replacing Judges with Juries, arXiv:2404.18796"
HAN = "Han et al. (2025), Judge's Verdict, arXiv:2510.09738"
MATHARENA = "Balunović et al. (2025), MathArena, arXiv:2505.23281"
TAN = "Tan et al. (2025), JudgeBench, arXiv:2410.12784"

C = {

# ======================================================== core/contracts.py
"core/contracts.py::OUTCOMES · AGENT_OUTCOMES · HARNESS_STOPS · HARNESS_FAILURES · EVENT_KINDS":
    ("The seven outcomes, named once and split into three groups the rest of the harness reasons "
     "about: what the agent did, what boundary we hit, and where the apparatus failed. "
     "<code>EVENT_KINDS</code> is the closed vocabulary of the trace — a kind not on this list "
     "cannot be recorded, which keeps the log parseable years later.", ZHU),
"core/contracts.py::Event":
    "One thing that happened, with a timestamp relative to the start of the rollout. "
    "<code>payload</code> is a free-form dict on purpose: the schema of a tool result is the "
    "tool's business, not the recorder's. <code>to_dict</code>/<code>from_dict</code> are "
    "explicit rather than automatic so the on-disk format is a decision, not an accident of "
    "whatever dataclass library is installed.",
"core/contracts.py::Task":
    "Everything the agent is allowed to see. The important line is the one that is not here: "
    "there is no <code>answer</code> field, so the agent code path cannot reach the key even by "
    "mistake. A structural guarantee, not a careful convention.",
"core/contracts.py::Rollout":
    "One complete attempt: the events, the submission, the execution state and the usage. "
    "<code>key</code> is the identity used everywhere for resumption and joins — "
    "<code>(solver_config, task_id, run_idx)</code>. Note that <code>outcome</code> holds an "
    "execution state at write time; the grade is assigned later, downstream.",
"core/contracts.py::Verdict":
    "One verifier's opinion about one rollout. <code>judge_model</code> and <code>blinded</code> "
    "are nullable because a deterministic verifier has neither — but a judged verdict without "
    "both recorded is unreproducible, so they live in the contract rather than in a detail dict.",
"core/contracts.py::Agent":
    "A Protocol, not a base class, so anything with a <code>run</code> method qualifies. The "
    "harness never imports a concrete agent; it is handed one.",
"core/contracts.py::Verifier":
    ("The reason \"two judges from different families\" is a config list rather than new code: a "
     "judge is a Verifier like any other, parameterised by a model. Swapping the panel touches "
     "no Python.", VERGA),

# ============================================================ core/trace.py
"core/trace.py::ROOT · TRACES · VERDICTS":
    "The two stores, resolved relative to this file rather than the working directory, so the "
    "scripts behave the same whether run from the repo root or anywhere else.",
"core/trace.py::trace_path":
    "One file per <code>(solver_config, task_id)</code>. Sharding this way means a rollout can be "
    "appended without reading or locking anything else, which is what makes bounded concurrency "
    "safe here.",
"core/trace.py::TraceRecorder":
    "Collects events for one rollout and holds no opinion about correctness — it cannot, it has "
    "no key. <code>emit</code> stamps time relative to the start; <code>finish</code> seals the "
    "rollout with an execution state and the usage totals.",
"core/trace.py::append_rollout":
    ("Append mode always; the pinned config header written exactly once on file creation; "
     "<code>fsync</code> so a run killed mid-batch loses nothing it had already reported. "
     "This is the function the whole architecture rests on.", KIRGIS),
"core/trace.py::read_trace":
    "Reads a trace file back into the header and its rollouts. Skips blank lines and tolerates a "
    "file that is being appended to, because the demo reads files that a background run is still "
    "writing.",
"core/trace.py::iter_all":
    "Every stored rollout, with last-write-wins deduplication by key. The log keeps every "
    "attempt, including one superseded by a re-run; derived views see one row per rollout. Pass "
    "<code>dedupe=False</code> to audit the raw log.",
"core/trace.py::completed_keys":
    "Resumption in one line: ask the store what it already has. There is no separate bookkeeping "
    "table that could disagree with the data — the log is the state.",
"core/trace.py::append_verdicts":
    "Verdicts get the same treatment as traces: one append-only file per verifier. Re-grading "
    "adds; it never overwrites, so an earlier verifier's opinion survives its own replacement.",
"core/trace.py::read_verdicts":
    "The read side. Imported inside the function to avoid a circular import with contracts — a "
    "small ugliness kept local rather than restructuring the module around it.",

# =========================================================== core/config.py
"core/config.py::ROOT · CONFIGS · REQUIRED_KEYS · KEY_ALIASES · SOLVER_PROMPT":
    "<code>REQUIRED_KEYS</code> maps a provider to the environment variable it needs, which is "
    "what lets the startup check name the missing one. <code>SOLVER_PROMPT</code> lives here, not "
    "in the agent, because it is part of the pinned configuration — change it and every number "
    "downstream describes a different experiment. <code>KEY_ALIASES</code> lists the other "
    "names people actually have in their .env; they are copied into the canonical variable "
    "at startup and the substitution is printed, because which variable authenticated a run "
    "is part of knowing what the run was.",
"core/config.py::prompt_hash":
    "The prompt is hashed rather than embedded in the fingerprint, so the config hash stays short "
    "but still moves if a single character of the prompt changes.",
"core/config.py::ModelSpec":
    ("A pinned model: provider, exact model string, temperature and the price list. Frozen, so a "
     "spec cannot be mutated halfway through a batch. Prices live here because cost per "
     "successful solve is a first-class reported number, not an afterthought.", KAPOOR24),
"core/config.py::RunConfig":
    "The apparatus for one solver configuration, and <code>config_hash</code> is its fingerprint: "
    "model string, temperature, prompt hash and sorted tool set, serialised canonically. "
    "<code>header()</code> is what gets written at the top of every trace file and printed on "
    "screen during the demo.",
"core/config.py::Registry":
    ("Loads the two YAML files and hands out solver and judge configurations. The <code>mock</code> "
     "flag returns a simulator spec that keeps the real price list but carries a name nobody can "
     "mistake for a real model — and therefore a different config hash.", KAPOOR25),
"core/config.py::MissingKey":
    "Its own exception type, so a missing key is distinguishable from any other RuntimeError by "
    "a caller that wants to offer the offline path instead.",
"core/config.py::validate_env":
    "Collects every missing variable rather than failing on the first, names the provider that "
    "needs each, and points at the way out. Failing fast only helps if it says what to do next.",
"core/config.py::load_dotenv":
    "A four-line .env reader. Uses <code>setdefault</code>, so a variable already exported in the "
    "shell wins over the file — the usual precedence, and the one people expect when overriding "
    "a key for a single run.",

# =========================================================== core/budget.py
"core/budget.py::BudgetExceeded":
    "Carries the trip <code>kind</code>. That single field is what lets the caller record "
    "<code>max_turns</code> and <code>budget_exceeded</code> as different outcomes instead of "
    "flattening two different facts into one.",
"core/budget.py::Budget":
    ("Two caps in one object, checked by one method. <code>check()</code> runs immediately before "
     "a tool executes and before each turn — before the spending, not after it. Instructions in a "
     "prompt are a request; this is a limit.", KAPOOR25),

# ========================================================= core/miniyaml.py
"core/miniyaml.py::_NUM":
    "The one regex needed to tell an integer or float scalar from a bare string.",
"core/miniyaml.py::_scalar":
    "Converts a YAML scalar to a Python value: quoted strings, booleans in their several "
    "spellings, nulls, numbers, and otherwise a plain string.",
"core/miniyaml.py::_strip_comment":
    "Removes a trailing comment while respecting quotes, so a <code>#</code> inside a string "
    "survives. The reason this is a character loop rather than a regex.",
"core/miniyaml.py::_inline":
    "Handles the inline list form — <code>[a, b, c]</code> — which is the only compound value the "
    "config files use on one line.",
"core/miniyaml.py::loads":
    "Indentation-driven parse of the subset the configs actually use: nested mappings, block and "
    "inline lists, comments, scalars. Deliberately small — this exists so the harness runs with "
    "an empty environment during a live demo, not to be a YAML implementation.",
"core/miniyaml.py::load_file":
    "Prefers PyYAML when it is installed and falls back to the parser above when it is not. The "
    "fallback is the tested path on a machine with no dependencies, which is exactly the machine "
    "a rehearsal happens on.",

# ============================================================ agent/loop.py
"agent/loop.py::REFUSAL_MARKERS":
    "The strings that turn a tool-less reply into <code>refused</code> rather than a nudge. Crude "
    "and openly so — a refusal classifier is its own project, and pretending otherwise would hide "
    "an assumption inside a number.",
"agent/loop.py::run_rollout":
    ("The whole tool-calling loop. Note what it does not do: it never decides whether the answer "
     "was correct. It has no key and cannot get one, so it records what happened and stops. "
     "Timeouts are caught separately from other faults so they get their own outcome.", ZHU),
"agent/loop.py::_stop":
    "Every exit path funnels through here, so there is no route by which something happens and no "
    "trace is written.",

# ======================================================= agent/providers.py
"agent/providers.py::ProviderError":
    "The apparatus failed. Naming this separately from a Python error is what makes "
    "\"harness failure, not agent failure\" expressible in code rather than only on a slide.",
"agent/providers.py::ProviderTimeout":
    "A subclass, so a caller can catch timeouts specifically or all provider faults generally. "
    "The loop catches it first, which is why a timeout becomes <code>timeout</code>.",
"agent/providers.py::Completion":
    "The one shape every provider returns: text, tool calls, and token counts. Everything above "
    "this line is model-agnostic because everything below it converts to this.",
"agent/providers.py::Provider":
    "The interface, as a Protocol. Two methods' worth of surface is the entire coupling between "
    "the harness and any model vendor.",
"agent/providers.py::usd":
    ("Cost for one call from the pinned price list. Computed at the call site and recorded in the "
     "trace, so cost per successful solve is a fact about the run rather than an estimate made "
     "afterwards.", KAPOOR24),
"agent/providers.py::_OpenAICompatible":
    "OpenAI and xAI speak the same chat-completions dialect, so one adapter serves both and the "
    "difference is a base URL and a key name. Provider exceptions are translated into the "
    "harness's own types here, at the boundary.",
"agent/providers.py::OpenAIProvider":
    "The default base URL, and <code>OPENAI_API_KEY</code>.",
"agent/providers.py::XAIProvider":
    "The same adapter pointed at x.ai, with <code>XAI_API_KEY</code>. Two lines, because the "
    "abstraction above was drawn in the right place.",
"agent/providers.py::GeminiProvider":
    "Gemini's API differs enough to need its own adapter: system instructions are separate, "
    "roles are named differently, and tool calls arrive as parts of a candidate. All of that "
    "asymmetry is absorbed here so the loop never sees it.",
"agent/providers.py::_THINKING · SKILL · EFFORT_SKILL · EFFORT_TOKENS · FLAW_RATE · ERR_RATE · TIMEOUT_RATE · LOOP_RATE · REFUSE_RATE":
    ("The simulator's parameters, in one block so they can be read and argued with. "
     "<code>FLAW_RATE</code> is the share of correct answers reached by unsound reasoning — the "
     "phenomenon the judging half of the workshop exists to measure. "
     "<code>EFFORT_SKILL</code> deliberately does <b>not</b> make 'high' uniformly best: higher "
     "reasoning effort reduced accuracy in most of the runs in the study cited beside this, and "
     "a simulator that hid that would teach the wrong lesson before the real sweep is ever run. "
     "<code>_THINKING</code> maps the four named levels onto Gemini's token budget, since not "
     "every provider expresses effort the same way.", KAPOOR25),
"agent/providers.py::_rng":
    "A random generator seeded by hashing its arguments, so every simulated rollout is a pure "
    "function of <code>(config, task, run_idx)</code>. The rehearsal you ran yesterday is the "
    "rehearsal you get today.",
"agent/providers.py::SOLUTIONS · FALLBACK":
    "Real solutions to the shipped problems, each with a subtly buggy variant. The simulator "
    "picks which program to run; the sandbox decides what it prints; a verifier decides later "
    "whether that was right. So the simulator never needs the answer key to produce a wrong run — "
    "it needs a worse program, which is closer to how a solver actually fails.",
"agent/providers.py::MockSolver":
    "A trace generator, not an agent. It exists so the workshop has a corpus with no keys and no "
    "network. Everything it writes is marked <code>simulated: true</code> and carries its own "
    "config hash, and every report built from it prints a banner.",
"agent/providers.py::_last_stdout":
    "Reads the most recent tool result out of the message list, so the simulator narrates what "
    "the sandbox actually printed rather than what it intended to print.",
"agent/providers.py::_NUM":
    "Integer matcher, used to compare what a trace's narration claims against what its tool "
    "produced.",
"agent/providers.py::MockJudge":
    ("Simulates a process judge including its biases. It reads a genuine signal from the blinded "
     "prompt — does the narrated value match the tool output — then adds severity and noise so "
     "the two judges disagree realistically, and is pulled toward ESTABLISHES when the prompt is "
     "unblinded. That last behaviour is simulated outcome leakage.", CURSE),
"agent/providers.py::_section":
    "Pulls a labelled section out of a rendered prompt. Shared by the simulated judge and the "
    "masked-continuation check, so both read the prompt the same way a real model would.",
"agent/providers.py::build":
    "The factory. One line decides simulator or real provider, and it is the only place in the "
    "codebase that knows the difference.",

# ========================================================= agent/sandbox.py
"agent/sandbox.py::PREAMBLE · DEFAULT_TIMEOUT_S · DEFAULT_MEM_MB · DEFAULT_CPU_S":
    "The preamble disables sockets and the network-reaching import paths before any submitted "
    "code runs. Prepended to the source rather than installed as a policy, because a subprocess "
    "that never had the capability is easier to reason about than one that gave it up.",
"agent/sandbox.py::ExecResult":
    "Execution outcome as data — stdout, stderr, return code, and whether the wall clock ran out. "
    "<code>timed_out</code> is separate from a non-zero return code because they are different "
    "failures and the outcome taxonomy needs to tell them apart.",
"agent/sandbox.py::_limits":
    "Best-effort resource caps set in the child before exec. Not every limit is enforceable "
    "everywhere — macOS refuses to start a CPython child under <code>RLIMIT_AS</code> — so a "
    "limit that cannot be set is skipped rather than fatal, and the wall-clock timeout is the "
    "backstop that always holds.",
"agent/sandbox.py::run_python":
    "A fresh isolated interpreter per call, with a timeout, a trimmed environment, and truncated "
    "output. Never raises on user error: a traceback from submitted code is a result to record, "
    "not an exception to propagate.",

# =========================================================== agent/tools.py
"agent/tools.py::_JSON_TYPES":
    "The Python-annotation to JSON-schema-type mapping. Small on purpose — a tool needing a type "
    "outside this set is a signal to reconsider the tool.",
"agent/tools.py::Tool":
    "A name, a function, a description, and a schema generated from the signature. Because the "
    "schema is derived, it cannot drift from the code; hand-written schemas silently describe "
    "last month's function. Harness-injected parameters are filtered out — the model is offered "
    "<code>code</code>, and the budget is none of its business.",
"agent/tools.py::SubmitAnswer":
    "Control flow, not an error. Submission is the one tool call that ends the loop, and raising "
    "is how a nested call site unwinds to the loop without a return-value convention threaded "
    "through every layer.",
"agent/tools.py::python_exec":
    "The enforcement point. <code>budget.check()</code> runs before the sandbox call, not after — "
    "a check that runs after the work is an accounting entry, not a limit.",
"agent/tools.py::submit_answer":
    "Takes the value and the reasoning. The reasoning field is the point: it records what the "
    "model <i>claims</i> its reasoning was, separately from the trace of what it actually did. "
    "The gap between those two is the whole of Session 2.",
"agent/tools.py::REGISTRY":
    "Two tools, and the descriptions the model sees. Keeping the registry this small is a "
    "deliberate scope decision — no side-effecting tools, so no permission model and no undo.",
"agent/tools.py::schemas":
    "Builds the tool-schema list handed to a provider. One line, because the work is in "
    "<code>Tool.schema</code>.",
"agent/tools.py::call":
    "Dispatch. Injects <code>budget</code> only into tools whose signature asks for it, so the "
    "enforcement dependency is explicit per tool rather than ambient.",

# ======================================================= runner/outcomes.py
"runner/outcomes.py::EXECUTION_STATES":
    "What the loop can know on its own, before any verifier runs. <code>submitted</code> appears "
    "here and not in OUTCOMES, because it is not a grade — it is the state of having produced an "
    "answer that nobody has checked yet.",
"runner/outcomes.py::classify":
    ("Combines the recorded execution state with the deterministic answer check. Raising when a "
     "submitted rollout has no answer check makes it impossible to silently default a missing "
     "grade to <code>incorrect</code> — which is the specific bug that deflates a reported "
     "accuracy.", ZHU),
"runner/outcomes.py::is_harness_failure":
    "The predicate the reporting layer uses to compute an error rate. Named, so the definition "
    "lives in one place rather than being re-derived at each call site.",
"runner/outcomes.py::is_agent_outcome":
    "Its counterpart: the outcomes that actually say something about the agent.",
"runner/outcomes.py::bucket":
    "Groups the seven into agent / stop / harness — the three-way split the slides use, computed "
    "from the same constants the code uses so the deck cannot disagree with the harness.",
"runner/outcomes.py::tally":
    ("Counts by outcome and returns the error rate alongside. Both numbers together, always, "
     "because accuracy without an error rate does not say whether the denominator was a "
     "measurement or an outage.", KIRGIS),

# ======================================================= runner/rollouts.py
"runner/rollouts.py::MAX_ATTEMPTS · BASE_BACKOFF_S":
    "Retry parameters for the narrow case below. Small numbers, because the thing being retried "
    "is rare and the thing not being retried is most of it.",
"runner/rollouts.py::_with_backoff":
    ("Exponential backoff with jitter, for faults that escape the loop entirely — where no trace "
     "was obtained at all. What it refuses to retry is the point: a provider error the loop "
     "caught stays in the corpus as <code>error</code> or <code>timeout</code>, because "
     "re-rolling failures until they succeed is exactly how a reported accuracy gets inflated.", ZHU),
"runner/rollouts.py::run_batch":
    ("n runs across tasks with bounded concurrency, resuming from whatever is already on disk and "
     "recording a rollout even for a job that raised. The header records <code>simulated</code>, "
     "so a corpus can always say what produced it.", KAPOOR25),

# ==================================================== verifiers/answer_match
"verifiers/answer_match.py::NAME · _BOXED · _INT":
    "The verifier's name as it appears in the verdict store, and the two patterns that do most of "
    "the normalisation work.",
"verifiers/answer_match.py::Escapes":
    ("The disclosure counter: exact, symbolic, unparsed, and the escape rate over them. This is "
     "the number that bounds how much of a headline figure was decided by something fuzzier than "
     "code — and it keeps the failing strings, because an escape rate you cannot inspect is one "
     "you cannot act on.", ZHU),
"verifiers/answer_match.py::normalise":
    ("Turns a submission into an integer or admits it cannot. Handles <code>\\boxed{}</code>, "
     "currency marks, thousands separators, LaTeX spacing, leading zeros and integer-valued "
     "floats — every one a real submission format. Returning None is the honest failure: it does "
     "not guess, it escalates to a path that gets counted.", MATHARENA),
"verifiers/answer_match.py::_symbolic":
    "The last deterministic resort before a judge. Optional by design — sympy is not a hard "
    "dependency, and a missing sympy shows up as an escape rather than a crash.",
"verifiers/answer_match.py::verify":
    "Runs the ladder, records which rung decided it, and returns the verdict. Rollouts that never "
    "submitted are labelled <code>not_submitted</code> rather than <code>incorrect</code>, "
    "because a timeout did not get the answer wrong.",

# ===================================================== verifiers/tool_replay
"verifiers/tool_replay.py::NAME":
    "The verifier's name in the verdict store.",
"verifiers/tool_replay.py::logged_calls":
    "Walks the trace pairing each <code>tool_call</code> with the <code>tool_result</code> that "
    "followed it. Only possible because the log records both — a summary would have kept the "
    "result and lost the code.",
"verifiers/tool_replay.py::verify":
    ("Re-executes every logged call now, offline, and diffs against what was recorded. Catches "
     "hallucinated tool results and non-determinism, and flags the case where a tool produced the "
     "answer the narration then takes credit for. No model is involved, which is what makes it a "
     "control on the judges rather than another one of them.", KIRGIS),

# ==================================================== verifiers/process_judge
"verifiers/process_judge.py::NAME · ANCHORS · SYSTEM · TASK_BLOCK · REDACTED":
    ("The rubric: four discrete anchors, a mandatory quoted span, one line of justification. Not "
     "a 1–10 scale, because models do not use the middle of numeric scales consistently and "
     "scores stop being comparable across items. The same block is used for the human calibration "
     "labels — score the human on a different instrument and the agreement number means nothing.", GU),
"verifiers/process_judge.py::BlindingLeak":
    "Raised when something the harness controls survived into a blinded prompt. An exception "
    "rather than a warning, because a leaked prompt produces a verdict that looks exactly like a "
    "valid one.",
"verifiers/process_judge.py::VerdictRejected":
    ("A verdict without a non-empty span is rejected at parse time, not coerced into a default. "
     "This is the rule that removes hallucinated criticism: a judge that cannot point at the step "
     "it objects to has not found one.", PROCESS),
"verifiers/process_judge.py::_identifiers":
    ("Collects every string that could reveal which model produced the trace — from the pinned "
     "header, the model-call events, and the configuration. Provenance blinding has to be "
     "family-level, because verdicts are inflated when judge and generator are merely related.", LEAK),
"verifiers/process_judge.py::render":
    ("The blinding function, and the most important code in the project. It assembles the prompt "
     "from the event log — narration, tool code, tool output, in order — and skips the events "
     "that carry the submission, the pinned config and provider error strings. The unblinded arm "
     "is the same function with a flag, adding two lines; those two lines are the whole "
     "experiment.", CURSE),
"verifiers/process_judge.py::_audit":
    ("The assertion. Hard failure for anything the harness controls: identifiers, outcome, answer "
     "key, metadata, and the redaction marker whose earlier presence was itself a tell. One soft "
     "flag for what it cannot control — that the judge could reconstruct <i>what</i> was answered "
     "from tool output, true of 100% of our traces. That is not outcome leakage, and saying so "
     "precisely is the difference between a caveat and a claim.", SOHN),
"verifiers/process_judge.py::_blocks":
    "Extracts all blocks carrying a given label from a rendered prompt. Used by the audit to "
    "check narration and tool output separately, since the two need different rules.",
"verifiers/process_judge.py::parse_verdict":
    "Accepts only the four anchors and only with a non-empty span. Raising rather than defaulting "
    "means a rejected verdict is visible in the counts instead of quietly becoming data.",
"verifiers/process_judge.py::judge":
    ("Renders, calls, parses, and records the judge model and blinding condition on the verdict. "
     "Pinning the judge's configuration exactly as the system under test is pinned is what makes "
     "any judge-derived number reproducible.", GU),

# ==================================================== verifiers/masked_cont
"verifiers/masked_cont.py::NAME · PROMPT · _NUM":
    "The prompt asks for a value, not an opinion — which is what separates this check from the "
    "judges it is meant to control.",
"verifiers/masked_cont.py::MockContinuer":
    "The offline stand-in. It reads what the narration actually committed to rather than "
    "guessing, so the check exercises the same signal a real continuation would.",
"verifiers/masked_cont.py::verify":
    ("Strips the submission, hands over the reasoning through the same blinding function the "
     "judges get, and compares where the reasoning lands to what was submitted. A disagreement "
     "means the reasoning argued for one number and the run submitted another — regardless of "
     "which was right.", PROCESS),

# ======================================================= metrics/aggregate.py
"metrics/aggregate.py::pass_at_k":
    ("The probability that at least one of k attempts succeeds, estimated unbiasedly from n "
     "trials and c successes without re-running anything. It rises toward 1 for almost any agent, "
     "which is why it never appears without pass^k beside it.", YAO),
"metrics/aggregate.py::pass_hat_k":
    ("The probability that all k succeed — the reliability number. Zero, exactly, when there are "
     "fewer than k successes. The gap between this curve and pass@k is the whole compounding-"
     "reliability story.", YAO),
"metrics/aggregate.py::majority_at_k":
    "Estimates the chance that the modal answer of k samples is correct, by resampling the "
    "observed answers. Ties are broken at random rather than by first-seen, so the estimate does "
    "not inherit the order the rollouts happened to finish in.",
"metrics/aggregate.py::bootstrap_ci":
    ("A percentile interval — and the choice of what to resample is the methodological point. The "
     "values are per-<i>task</i> rates, not per-rollout outcomes: ten rollouts of one problem are "
     "correlated, and treating them as ten independent samples yields an interval far too "
     "narrow.", MILLER),
"metrics/aggregate.py::per_task_rates":
    "Collapses (task, success) rows into a per-task rate. The unit of clustering, made explicit "
    "so the interval above is computed over the right thing.",
"metrics/aggregate.py::summarise":
    ("Every reliability number for one solver, with the denominator stated in the output rather "
     "than assumed by the reader. The curve is emitted for every k so the pass@k / pass^k "
     "divergence can be drawn rather than asserted.", YAO),

# ========================================================== metrics/cost.py
"metrics/cost.py::summarise":
    ("Cost per run and cost per <i>successful</i> solve. The second is the number that matters: "
     "cost per run rewards an agent that fails cheaply, while cost per successful solve says what "
     "the capability actually costs to obtain. Infinity when nothing succeeded, which is the "
     "honest value.", KAPOOR24),

# ======================================================== metrics/judges.py
"metrics/judges.py::ANCHORS":
    "The same four anchors as the rubric, restated here so the metrics layer can be read without "
    "importing the judge.",
"metrics/judges.py::_key":
    "The join key across verdict streams: config, task, run. Every metric below is a group-by on "
    "this.",
"metrics/judges.py::pair_up":
    "Groups blinded verdicts by trace so the two judges' opinions sit side by side. Unblinded "
    "verdicts are excluded here — mixing conditions would measure the ablation instead of the "
    "agreement.",
"metrics/judges.py::cohens_kappa":
    ("Agreement above chance. Reported alongside raw agreement because raw agreement on a skewed "
     "label distribution flatters every judge — two judges that both say ESTABLISHES most of the "
     "time will agree often while sharing no information.", TAN),
"metrics/judges.py::inter_judge_agreement":
    ("Raw agreement, kappa, per-configuration breakdown, and the top disagreement pairs. Reported "
     "as a headline number, not a footnote: presenting a process score while the instrument "
     "disagrees with itself is the failure this exists to prevent.", VERGA),
"metrics/judges.py::severity":
    ("Each judge's rate of not saying ESTABLISHES, across both of its judging roles. The rotation "
     "is what makes this comparable — a consistently harsh model shows up in both of its roles, "
     "over two independent solver populations.", POMBAL),
"metrics/judges.py::blinding_effect":
    ("The direct measurement of outcome leakage: the same traces, keyed by trace <i>and</i> judge, "
     "judged both ways. Direction is counted separately from magnitude, because noise flips both "
     "ways and leniency flips one.", CURSE),
"metrics/judges.py::human_agreement":
    ("Each judge's agreement with the instructor's labels, per judge and never averaged into one "
     "figure. Reported with n attached, because forty is a small number and the audience is "
     "entitled to know that before believing a percentage.", HAN),
"metrics/judges.py::right_answer_wrong_reasoning":
    ("Of the runs that reached the right answer, the share whose reasoning at least one blinded "
     "judge called unsound — reported both as 'any judge' and 'both judges'. This is the number "
     "that makes the case for having a process axis at all.", PROCESS),

# ======================================================= tasks/math/loader.py
"tasks/math/loader.py::path bootstrap":
    "Lets the file be run directly as well as imported, without a package install step.",
"tasks/math/loader.py::HERE · PROBLEMS · DATASET":
    ("The dataset is a recurring competition set, chosen so the problems postdate the models' "
     "training data. Evaluating on widely available problems measures memorisation as much as "
     "reasoning.", MATHARENA),
"tasks/math/loader.py::task_id":
    "The naming convention, in one function, so a trace filename and a problem index can always "
    "be reconciled.",
"tasks/math/loader.py::sync":
    "The only function in the project that touches the network, and it runs once. Everything "
    "afterwards reads the cached JSONL.",
"tasks/math/loader.py::_rows":
    "Reads the cache, with an error that names the command to populate it rather than a bare "
    "FileNotFoundError.",
"tasks/math/loader.py::load_tasks":
    "Tasks only, no answers. This is what the agent sees, and the split between this function and "
    "the next is the whole isolation mechanism.",
"tasks/math/loader.py::answer_key":
    "Answers only. Imported by verifiers, never by anything under <code>agent/</code> — the "
    "separation is enforced by which module calls which, and asserted in the standing check.",
"tasks/math/loader.py::is_synthetic":
    "Says whether the shipped placeholder problems are still in place. Surfaced in the standing "
    "check so a corpus built on placeholders cannot be mistaken for one built on the real set.",
"tasks/math/loader.py::__main__":
    "Running the file prints what is cached; <code>--sync</code> replaces it with the real "
    "dataset.",

# ========================================================== display/live.py
"display/live.py::COLS · _C":
    "Six columns, never seven. A table wider than this is unreadable past row four from the back "
    "of an auditorium, and that is the most common way a good demo fails.",
"display/live.py::banner":
    "Prints the pinned configuration at the top of every run, so the room sees the apparatus was "
    "pinned rather than being told it was — and prints a loud warning when the corpus is "
    "simulated.",
"display/live.py::row":
    "One rollout, one line, with the outcome colour-coded. Takes an optional graded outcome so "
    "the same renderer can show execution states live and grades on replay.",
"display/live.py::footer":
    "Totals by outcome and the spend. The counts are printed even when a category is zero-free, "
    "so the seven-outcome taxonomy is visible on screen rather than only in the slides.",

# ======================================================== display/replay.py
"display/replay.py::path bootstrap":
    "Lets the replay tool run as a script from anywhere in the repo.",
"display/replay.py::main":
    "Replays a stored trace through the <i>same</i> renderer the live run uses, at a configurable "
    "speed. That sharing is the point: if the network dies, the fallback does not look like a "
    "fallback, and nobody in the room can tell which they are watching.",
"display/replay.py::__main__":
    "Standard entry point.",

# ==================================================== scripts/initial_check.py
"scripts/initial_check.py::path bootstrap":
    "Runs from anywhere without an install step.",
"scripts/initial_check.py::_results":
    "Colours and the results accumulator. The check reports everything it ran, passes included, "
    "because a green list is the artifact — a silent success proves nothing was checked.",
"scripts/initial_check.py::check":
    "A decorator that runs a check immediately and records the outcome instead of aborting on the "
    "first failure. One run tells you everything that is broken, not the first thing.",
"scripts/initial_check.py::run":
    ("The cumulative standing check, milestone by milestone. These are not tests of implementation "
     "detail — they are the claims of the workshop asserted in code: Task carries no answer field, "
     "the seven outcomes are distinct, a verdict without a span is rejected, a blinded prompt "
     "leaks nothing. Offline unless <code>--online</code> is passed.", ZHU),
"scripts/initial_check.py::__main__":
    "Entry point, with the one flag that turns on live provider calls.",

# ============================================================ scripts/run.py
"scripts/run.py::path bootstrap":
    "Runs from anywhere without an install step.",
"scripts/run.py::main":
    ("The only entry point that calls a solver. It executes rollouts and records traces, and "
     "grades nothing — the fact that the last line prints execution states and points at "
     "grade.py is the architecture refusing to blur the seam.", KIRGIS),
"scripts/run.py::__main__":
    "Entry point.",

# ========================================================== scripts/grade.py
"scripts/grade.py::path bootstrap":
    "Runs from anywhere without an install step.",
"scripts/grade.py::_providers":
    "Builds the judge panel for a configuration — two simulated judges with different severity "
    "offline, the two real cross-family judges otherwise.",
"scripts/grade.py::main":
    ("Runs the whole verifier stack over stored traces with zero solver calls. This script "
     "existing separately from run.py is the structural proof that the architecture is "
     "trace-first: three of these four verifiers were written after the corpus existed and "
     "applied to all of it for nothing.", KIRGIS),
"scripts/grade.py::__main__":
    "Entry point.",
"scripts/grade.py::ROOT":
    "Repo root, resolved from this file.",

# ========================================================== scripts/label.py
"scripts/label.py::path bootstrap":
    "Runs from anywhere without an install step.",
"scripts/label.py::ROOT · OUT":
    "Where the labels are written. Append-only JSONL, like everything else derived by hand or by "
    "machine.",
"scripts/label.py::stratified":
    ("Samples across the three solver configurations <i>and</i> across correct and incorrect "
     "outcomes, round-robin, under a fixed seed. Sample only from the strongest solver, or only "
     "from runs that succeeded, and every judge–human agreement figure downstream is measured on "
     "the easy half of the corpus.", SOHN),
"scripts/label.py::main":
    ("Presents the same blinded prompt a judge receives, on the same anchors, and refuses to "
     "record a label without a span — the human is held to the rule the judges are held to. "
     "Progress is saved after each label so the evening can be interrupted.", HAN),
"scripts/label.py::__main__":
    "Entry point.",

# ========================================================= scripts/report.py
"scripts/report.py::path bootstrap":
    "Runs from anywhere without an install step.",
"scripts/report.py::ROOT · REPORTS":
    "Output location and the terminal styling. Yellow is reserved for the simulated-corpus "
    "banner and for missing calibration, which are the two things a reader must not miss.",
"scripts/report.py::h":
    "Section heading helper. Cosmetic, but the report is read aloud from a stage and structure "
    "matters.",
"scripts/report.py::main":
    ("Every number used in either session, from one command, over stored traces and verdicts — "
     "outcomes with the error rate, reliability with intervals, the escape rate, judge agreement "
     "and severity, the blinding effect, calibration, and cost per successful solve. Nothing here "
     "calls a model. If a figure cannot be produced by this script, it does not go in the deck.", KAPOOR25),
"scripts/report.py::__main__":
    "Entry point.",

# ============================================================== configs/
"configs/models.yaml::models.yaml":
    "The pinned model strings and their price lists. A rename must surface as an error rather "
    "than a silent substitution, which is why the exact string lives in configuration and is "
    "recorded in every trace header.",
"configs/rotation.yaml::rotation.yaml":
    ("The whole rotation design, in seventeen lines. Each configuration names one solver and two "
     "judges from different families, and no solver appears in its own judge list — so "
     "\"no model judges itself\" is a property of the data rather than a promise. Changing the "
     "panel never touches a Python file.", WATAOKA),

"core/config.py::EFFORTS":
    ("The four reasoning-effort levels, named once. Effort is part of the <b>pinned apparatus</b>, "
     "not a knob you turn between runs and still compare the numbers — which is why it feeds the "
     "config hash below and is printed with every run. It has to be recorded for the finding "
     "beside this to be discoverable at all: higher effort reduced accuracy in most runs.", KAPOOR25),
"core/config.py::base_config":
    "<code>S1@high</code> → <code>S1</code>. An effort sweep runs the same solver on the same "
    "tasks, so each arm needs its own rollout key or resumption skips every arm after the first "
    "and the study quietly does not happen. The arms are separate configurations for keys and "
    "files, but the same rotation entry when it comes to who judges them.",
"core/config.py::effort_of":
    "The inverse: recovers which effort arm a stored configuration label belongs to, so the "
    "report can group the sweep without re-deriving it from the header.",
"scripts/grade.py::_stratified_ablation":
    ("Chooses which traces to <i>also</i> judge unblinded. Taking the first n in sorted order "
     "looks harmless and is not: with several solver configurations — an effort sweep produces "
     "twelve — the whole ablation lands inside whichever one sorts first, and the blinding effect "
     "gets measured on one arm and reported as though it covered the study. Round-robin across "
     "(configuration, correct/incorrect) buckets under a fixed seed, so the sample cannot be "
     "accidentally all-easy or all-one-model.", SOHN),
"core/config.py::resolve_aliases":
    "Copies a recognised alias into the canonical variable the provider SDKs read, and returns "
    "what it substituted so the caller can say so out loud. Forgiving about the name, never "
    "silent about the substitution — a run authenticated by a variable nobody mentioned is a run "
    "you cannot fully describe afterwards.",
"scripts/pipeline.py::ROOT":
    "Repo root, so every stage runs from the same place regardless of where the command was typed.",
"scripts/pipeline.py::stage":
    "Runs one stage as a subprocess and stops the pipeline if it fails. Each stage is literally "
    "the command you would have typed — nothing here is a second implementation that could drift "
    "from the real one — and a failure halts rather than continuing, because every later stage "
    "builds on a corpus the failed one was supposed to produce.",
"scripts/pipeline.py::main":
    ("The whole study in one command: standing check, rotation corpus, reasoning-effort sweep, "
     "offline grading, report. It prints the planned rollout count before anything runs and, for "
     "a real run, refuses to start until you type <code>run</code> — the money is yours and the "
     "confirmation is cheap. Calibration is deliberately excluded: label.py needs a human, and a "
     "pipeline that pretended otherwise would emit judge numbers with nothing behind them.", SOHN),
"scripts/pipeline.py::__main__":
    "Entry point.",
}
