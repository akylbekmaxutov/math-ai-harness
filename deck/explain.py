"""One explanation per code block, keyed by "path|selector".

deck/build.py refuses to build if a code block on a slide has no entry here.
That is the mechanism behind the rule: nothing is shown on screen without
being explained.

    lead    — one sentence: what this code is for
    points  — (token, explanation) pairs; the token is something visible in
              the snippet, so the audience can find what is being described
    kind    — "judge" tints the block amber, for the Session 2 material
"""

EXPLAIN = {

# ---------------------------------------------------------------- Session 1
"core/contracts.py|Task": dict(
    lead="This is <b>everything the agent is allowed to see</b> about a problem.",
    points=[
        ("task_id", "A stable name for the problem, so a trace can be matched to it later without matching on the problem text."),
        ("problem", "The LaTeX statement. This is the only content that reaches the model."),
        ("no answer field", "The important line is the one that is not here. The key lives in a separate function that only verifiers call, so the agent code path cannot reach it even by accident. A structural guarantee beats a careful convention."),
    ]),

"core/trace.py|append_rollout": dict(
    lead="Writes one finished rollout to disk. <b>Append-only</b> — nothing is ever rewritten in place.",
    points=[('open(p, "a")', "Append mode, always. A corpus you can rewrite is a corpus you will eventually rewrite, usually at 2am before a talk."),
        ("if new:", "The pinned config header is written exactly once, when the file is created. Every rollout in the file was produced under it."),
        ("os.fsync", "Forces the write to the physical disk. A run killed mid-batch loses nothing it had already reported, which is what makes resumption trustworthy."),
    ]),

"core/config.py|RunConfig.config_hash": dict(
    lead="Turns the four things that decide what a run <i>means</i> into one short, comparable fingerprint.",
    points=[
        ("model / temperature", "The obvious two. Change either and you are measuring a different system."),
        ("prompt_sha", "The prompt is hashed rather than embedded, so the fingerprint stays short but still moves if a single character of the prompt changes."),
        ("sorted(self.tools)", "Sorted, so the same tool set always hashes the same way regardless of declaration order. Unsorted here would produce spurious hash changes and destroy comparability."),
        ("sort_keys=True", "Same reason, one level up: the JSON serialisation must be canonical or the hash is not a function of the config."),
    ]),

"core/config.py|validate_env": dict(
    lead="Checks every key the run will need <b>before</b> the run starts, and names the missing one.",
    points=[
        ("missing.append", "Collects all missing keys rather than failing on the first. You fix them in one pass instead of three."),
        ("provider: {p}", "Says which provider needs the variable. 'Missing GEMINI_API_KEY' is a bug report; 'authentication failed' forty seconds into a batch is a mystery."),
        ("or pass --mock", "The error also names the way out. Failing fast is only helpful if it tells you what to do next."),
    ]),

"runner/outcomes.py|classify": dict(
    lead="Combines what the harness <i>recorded</i> with what the deterministic check <i>decided</i>, to produce one of the seven outcomes.",
    points=[
        ("state != submitted", "If the run never submitted an answer, the execution state already is the outcome — a timeout is a timeout, and no grading is involved or possible."),
        ("answer_correct is None", "A submitted rollout cannot be classified without the answer check. Raising here makes it impossible to silently default a missing grade to 'incorrect'."),
        ("correct / incorrect", "These two, and only these two, are produced by grading. Everything else came from execution."),
        ("where this lives", "In runner/, not in agent/. The loop has no answer key, so it literally cannot compute this — which is the architecture enforcing itself."),
    ]),

"agent/loop.py|run_rollout": dict(
    lead="The whole tool-calling loop. Roughly fifty lines, no framework — and it never decides whether the answer was right.",
    points=[
        ("budget.check", "First thing each turn. The stop condition is checked before spending, not after."),
        ("except ProviderTimeout", "Caught separately from other provider errors, so a timeout becomes the outcome <code>timeout</code> and not a generic failure. Distinct causes get distinct names."),
        ("if not comp.tool_calls", "A reply with no tool call is not automatically a refusal. The loop nudges once, then lets the turn cap decide — a crude stop condition, deliberately visible as such."),
        ("except SubmitAnswer", "Submission arrives as an exception because it is control flow, not an error: it is the one tool call that ends the loop."),
        ("return _stop(...)", "Every exit path returns a recorded rollout. There is no path where something happens and no trace is written."),
    ]),

"core/budget.py|Budget.check": dict(
    lead="The limit itself. Called immediately before a tool executes and before each turn.",
    points=[
        ("usd_spent >= usd_cap", "Spend cap. Checked against what has already been charged, so the cap is never exceeded by the call that trips it."),
        ("turns_used >= turn_cap", "Turn cap. The same function guards both, which is why a single call site covers both failure modes."),
        ('BudgetExceeded(..., "turn")', "The trip <b>kind</b> is carried in the exception. That is what lets the caller record <code>max_turns</code> and <code>budget_exceeded</code> as different outcomes instead of flattening them."),
        ("self.trips.append", "Records that a cap fired, so the run report can say how often boundaries were the binding constraint."),
    ]),

"agent/tools.py|python_exec": dict(
    lead="The enforcement point — three lines, and the only thing standing between a bug and a bill.",
    points=[
        ("budget.check(...)", "Before <code>run_python</code>, not after. A check that runs after the work is an accounting entry, not a limit."),
        ("budget.tool_calls += 1", "Counted here rather than inferred from the trace later, so the number is right even for a rollout that crashed."),
        ("run_python(code)", "All the sandboxing — timeout, resource caps, no network — lives one layer down, so this function stays small enough to audit at a glance."),
    ]),

"agent/tools.py|Tool.schema": dict(
    lead="Generates the JSON schema the model sees <b>from the Python signature</b>, so the two cannot drift apart.",
    points=[
        ("inspect.signature", "The single source of truth is the function itself. Rename a parameter and the schema follows; hand-written schemas silently describe last month's function."),
        ('pname in ("budget",)', "Harness-injected parameters are filtered out. The model is offered <code>code</code>; the budget is supplied by us and is none of the model's business."),
        ("required.append", "A parameter with no default is required. The rule is read off the code rather than restated in prose that can go stale."),
    ]),

"runner/rollouts.py|_with_backoff": dict(
    lead="Retries only the case where <b>no trace was obtained at all</b>. Read the docstring — what it refuses to retry is the point.",
    points=[
        ("2 ** i", "Exponential backoff with jitter, so a batch of concurrent workers does not synchronise and hammer a recovering endpoint."),
        ("NOT retried", "A provider error the loop caught is recorded as <code>error</code> or <code>timeout</code> and left in the corpus. Re-rolling it until it succeeds is exactly how a reported accuracy gets inflated."),
        ("the error rate is a result", "It describes how reliable the apparatus was that afternoon. That is information, not noise to be cleaned up."),
    ]),

"core/trace.py|completed_keys": dict(
    lead="Resumption in one line: ask the store what it already has.",
    points=[
        ("r.key", "The identity of a rollout is <code>(solver_config, task_id, run_idx)</code>. Anything already carrying that key does not need running again."),
        ("iter_all", "Reads the traces themselves. There is no separate bookkeeping table that could disagree with the data — the log is the state."),
        ("set", "Membership is what the runner needs, so it gets a set. Restarting a killed batch is one read and a filter."),
    ]),

"metrics/aggregate.py|pass_at_k": dict(
    lead="The probability that <b>at least one</b> of k attempts succeeds — estimated from n trials and c successes, without re-running anything.",
    points=[
        ("comb(n - c, k)", "Counts the ways to draw k attempts that are all failures. One minus that share is the chance of at least one success."),
        ("if n - c < k", "If there are fewer failures than k, every possible draw contains a success, so the answer is exactly 1."),
        ("what it hides", "This number rises toward 1 as k grows for almost any agent. On its own it flatters everything, which is why it never appears without the next function beside it."),
    ]),

"metrics/aggregate.py|pass_hat_k": dict(
    lead="The probability that <b>all</b> k attempts succeed. This is the reliability number.",
    points=[
        ("comb(c, k) / comb(n, k)", "The share of all k-subsets that consist entirely of successes. Unbiased from the trials you already have."),
        ("if c < k", "Fewer than k successes means no such subset exists, so the value is 0 — not a small number, exactly zero."),
        ("why it matters", "pass@k answers 'can it'. pass^k answers 'will it'. The gap between the two curves is the whole compounding-reliability story."),
    ]),

"metrics/aggregate.py|bootstrap_ci": dict(
    lead="A percentile confidence interval — and the choice of <i>what</i> to resample is the entire methodological point.",
    points=[
        ("values[rng.randrange(m)]", "Resamples with replacement to build the sampling distribution of the statistic."),
        ("resample the CLUSTER", "The values passed in are per-<b>task</b> rates, not per-rollout outcomes. Ten rollouts of the same problem are correlated; treating them as ten independent samples produces an interval that is far too narrow."),
        ("8 problems", "With a task set this small, an interval is not optional decoration. It is the difference between an honest report and an overclaim."),
    ]),

# ---------------------------------------------------------------- Session 2
"verifiers/answer_match.py|normalise": dict(
    lead="Turns whatever the model submitted into an integer, or admits it cannot. Exact, free, reproducible — and the reason a judge here would be the wrong tool.",
    kind="judge",
    points=[
        ("_BOXED.search", "Pulls the value out of <code>\\boxed{...}</code>, the single most common way a maths answer arrives wrapped."),
        ("replace / re.sub", "Strips currency marks, thousands separators, LaTeX spacing and leading plus signs. Each of these is a real submission format, not a hypothetical one."),
        ('^-?\\d+\\.0*$', "Accepts <code>608.0</code> as 608. Rejecting an integer for being spelled as a float would mark a right answer wrong."),
        ("return None", "The honest failure. It does not guess — it hands the decision to the escape path, where it will be counted."),
    ]),

"verifiers/answer_match.py|Escapes": dict(
    lead="The disclosure counter. Every decision the exact check could not make is counted as an <b>escape</b>.",
    kind="judge",
    points=[
        ("exact / symbolic / unparsed", "Three tiers, each less reproducible than the one above. Knowing the mix matters more than knowing the total."),
        ("escape_rate", "The share of decisions not made by exact integer comparison. This is the number that bounds how much of your headline figure was decided by something fuzzier than code."),
        ("examples", "Keeps the actual strings that failed. An escape rate you cannot inspect is a number you cannot act on."),
    ]),

"verifiers/tool_replay.py|verify": dict(
    lead="Re-executes every logged tool call and diffs the result against what the trace recorded. No model is involved.",
    kind="judge",
    points=[
        ("run_python(code)", "Runs the same code again, now, in the same sandbox. If the recorded output was hallucinated or the computation was not deterministic, the diff shows it."),
        ("diffs.append", "Keeps the recorded and replayed output side by side, so a mismatch is a piece of evidence rather than a flag."),
        ("answer_produced_by_tool", "Notes whether the submitted answer appears in the tool output. This is how you find the run where a tool did the work and the narration took the credit."),
        ("why it is possible", "Only because the trace records the tool call <i>and</i> its result. This verifier was written after the corpus existed and applied to all of it for nothing."),
    ]),

"verifiers/masked_cont.py|verify": dict(
    lead="Removes the submission, hands over the reasoning, and asks what value it determines. It asks for a <b>consequence</b>, not an opinion.",
    kind="judge",
    points=[
        ("render(..., blinded=True)", "Reuses the same blinding function the judges get, so the continuation sees exactly what a judge sees."),
        ("landed != submitted", "If the reasoning argues its way to one number and the run submitted another, the two disagree — regardless of which is correct."),
        ("28 of 210", "In our corpus, that is how many submitted runs landed somewhere other than their own submission."),
        ("not an opinion", "This is what makes it a control on the judges rather than a third judge: nothing here is asked to form a view about quality."),
    ]),

"verifiers/process_judge.py|render": dict(
    lead="The blinding function. It builds the judge prompt from the trace and decides what the judge is <b>not</b> allowed to know.",
    kind="judge",
    points=[
        ("for ev in rollout.events", "The prompt is assembled from the event log, not from a summary. What the judge reads is what actually happened."),
        ("elif tool_result", "Narration, tool code and tool output are interleaved in the order they occurred, so the reasoning can be followed step by step."),
        ("never rendered", "<code>final</code>, <code>run_start</code>, <code>model_call</code> and <code>error</code> events are skipped — they carry the submission, the pinned config, and provider error strings that would identify the model."),
        ("if not blinded", "The unblinded arm is the <b>same function with a flag</b>, adding two lines. Those two lines are the entire experiment in beat 6."),
        ("graded_outcome", "The unblinded arm is told the <i>grade</i>, not the raw execution state. Passing 'submitted' would leak nothing and the ablation would silently measure noise."),
    ]),

"verifiers/process_judge.py|_audit": dict(
    lead="The assertion. It fails loudly on anything the harness controls, and reports honestly on the one thing it does not.",
    kind="judge",
    points=[
        ("(?<![\\w-])...(?![\\w-])", "Word-boundary matching for identifiers, so 'S1' inside a longer token is not a false positive while a real model name is always caught."),
        ("for token in (...)", "Outcome, answer key, config hash and usage are all banned strings in a blinded prompt. Any of them appearing raises rather than warns."),
        ("REDACTED in prompt", "Guards against reintroducing the tell we removed: a placeholder that only appears on faithful narrations tells the judge the answer without it reading anything."),
        ("residual", "The <b>soft</b> flag. It reports that the judge could reconstruct <i>what</i> was answered from tool output — true of 100% of our traces. It is not outcome leakage, because the key never enters this module, and it is why the ablation is the real measurement."),
    ]),

"verifiers/process_judge.py|parse_verdict": dict(
    lead="Rejects a malformed verdict at parse time, rather than coercing it into something usable.",
    kind="judge",
    points=[
        ("verdict not in ANCHORS", "Only the four named anchors are accepted. A judge that invents a fifth category has not followed the rubric, and its answer is not comparable to the others."),
        ("if not span", "No quoted evidence, no verdict. This is the rule that removes hallucinated criticism — a judge that cannot point at the step it objects to has not found one."),
        ("raise VerdictRejected", "Raising rather than returning a default. A rejected verdict is visible in the counts; a silently defaulted one becomes data."),
    ]),

"verifiers/process_judge.py|TASK_BLOCK": dict(
    lead="The rubric itself — four discrete anchors, a mandatory span, one line of justification.",
    kind="judge",
    points=[
        ("four anchors", "Not a 1–10 scale. Models do not use the middle of numeric scales consistently, so a 7 from one judge is not a 7 from another and scores stop being comparable across items."),
        ("ESTABLISHES vs INCOMPLETE", "The distinction is between 'the reasoning gets there' and 'nothing is wrong but it does not get there yet'. Collapsing them hides the most common real failure."),
        ("Quote the single span", "Forces the judge to locate its objection. A lightweight version of ProcessBench's 'identify the earliest erroneous step'."),
        ("same block for humans", "The calibration labels are collected on this exact rubric. Score the human on a different instrument and the agreement number means nothing."),
    ]),

"configs/rotation.yaml|": dict(
    lead="The whole rotation design is a config file, because a judge is a <code>Verifier</code> parameterised by a model — not new code.",
    kind="judge",
    points=[
        ("solver / judges", "Each configuration names one solver and two judges. The solver never appears in its own judge list, which is what makes 'no self-judging' a property of the data rather than a promise."),
        ("different families", "The two judges are from different providers. Preference leakage inflates verdicts across a whole model family, so two judges from one family is barely better than one."),
        ("problem_idx", "The eight problems are a list here, so swapping in harder problems when a set saturates is a config change, not a code change."),
        ("what this buys", "Changing the panel — three judges, a different rotation, a different solver — never touches a Python file."),
    ]),

"metrics/judges.py|blinding_effect": dict(
    lead="The direct measurement of outcome leakage: the <b>same traces</b>, judged both ways, differing in one flag.",
    kind="judge",
    points=[
        ("set(blinded) & set(unblinded)", "Only traces judged in both conditions are compared, keyed by trace <i>and</i> judge. It is a paired comparison, not two independent samples."),
        ("flipped_to_establishes", "Counts verdicts that became more forgiving once the judge could see the answer was right. Direction matters — noise flips both ways, leakage flips one."),
        ("net_leniency", "The asymmetry. In our corpus, unsound verdicts fell from 23% to 13% when the outcome was visible: seeing the right answer made the judge ten points more forgiving of the reasoning."),
    ]),

"scripts/label.py|stratified": dict(
    lead="Chooses which forty traces get hand-labelled. Sampling badly here quietly invalidates every judge number downstream.",
    kind="judge",
    points=[
        ("strata[(config, outcome)]", "Six buckets: three solver configurations × correct/incorrect. The calibration set cannot come out all-easy or all from the strongest model."),
        ("keys[i % len(keys)]", "Round-robins across the buckets, so the set stays balanced even when one bucket runs out."),
        ("seed=20260907", "Fixed seed. Which forty traces were labelled is part of the apparatus and has to be reproducible like everything else."),
    ]),

"metrics/judges.py|human_agreement": dict(
    lead="The number that turns every process figure in the deck from an assertion into a calibrated result.",
    kind="judge",
    points=[
        ("if v.blinded is False", "Only blinded verdicts are compared against the labels, because the human labelled a blinded prompt. Comparing across conditions would measure the ablation, not the judge."),
        ("per_judge", "Reported per judge, never averaged into one figure. 'The judges agree with me 76% of the time' hides that one of them agrees 82% and the other 71%."),
        ("n_labelled", "Reported alongside, because forty is a small number and the audience is entitled to know that before believing the percentage."),
    ]),

# ---------------------------------------------------------------- terminals
"deck/term/replay.txt": dict(
    lead="Ten stored rollouts of one problem, replayed through the <b>same renderer</b> the live run uses.",
    points=[
        ("config_hash", "Printed at the top of every run, so the room sees the configuration was pinned rather than being told it was."),
        ("ANSWER column", "Rows disagree with each other. Same problem, same configuration, ten attempts — this is beat 2, and it is the whole argument for repetition."),
        ("submitted", "Not 'correct'. At replay time the harness reports execution state; correctness is a grade and grades come from grade.py."),
        ("SIMULATED banner", "Every offline trace announces itself. Nothing generated without a provider can be mistaken for a measurement."),
    ]),

"deck/term/grade.txt": dict(
    lead="The trace-first architecture paying for itself, out loud.",
    points=[
        ("0 solver calls", "Four verifiers, 240 traces, 520 verdicts, and not one call to the system under test. Three of these verifiers were written after the corpus existed."),
        ("escape rate 0.125", "12.5% of answer decisions could not be made by exact comparison. Reported, not buried."),
        ("420 blinded / 100 unblinded", "The ablation arm, on the same traces, is what makes beat 6 a measurement instead of an anecdote."),
        ("blinding audit", "Zero hard leaks; 100% of prompts still let a judge reconstruct the submitted answer from tool output. Both facts are printed every time."),
    ]),

"deck/term/report.txt": dict(
    lead="Every judge number in Session 2, from one command, over stored verdicts.",
    points=[
        ("inter-judge agreement", "Raw agreement <i>and</i> Cohen's kappa. Raw agreement on a skewed label distribution flatters every judge; kappa is what survives that."),
        ("judge severity", "Each model's rate of not saying ESTABLISHES, across both of its judging roles — so a consistently harsh model shows up twice."),
        ("blinding effect", "23% unsound blinded, 13% unblinded. Ten points of leniency bought purely by letting the judge see the outcome."),
        ("top disagreements", "Where the judges part company: mostly ESTABLISHES against INCOMPLETE, which is a threshold disagreement rather than a factual one."),
    ]),

"deck/term/check.txt": dict(
    lead="The standing check. Cumulative by milestone, and it must be green before anything moves on.",
    points=[
        ("Task carries no answer field", "These are not tests of implementation detail. They are the <b>claims of the workshop</b>, asserted in code."),
        ("M4 re-running a key", "The log keeps both attempts; derived views see one row. Append-only and correct metrics are not in conflict, but only if someone checks."),
        ("M6 blinded prompt", "Asserts that no identifier, outcome, metadata or redaction marker survives into a blinded prompt."),
        ("offline by default", "Nothing here touches the network unless <code>--online</code> is passed. The check runs on a plane."),
    ]),
"core/contracts.py|Event": dict(
    lead="One thing that happened, with a timestamp relative to the start of the rollout.",
    points=[
        ("kind", "Drawn from a closed vocabulary — model_call, model_response, tool_call, tool_result, final, error. A kind that is not on the list cannot be recorded, which keeps the log parseable years from now."),
        ("payload", "A free-form dict on purpose: the shape of a tool result is the tool's business, not the recorder's."),
        ("to_dict / from_dict", "Written by hand rather than derived, so the on-disk format is a decision you can defend rather than a side effect of whichever library is installed."),
    ]),

"core/contracts.py|Rollout": dict(
    lead="One complete attempt at one problem: the events, the submission, the execution state, and what it cost.",
    points=[
        ("key", "The identity used for resumption and for every join downstream: <code>(solver_config, task_id, run_idx)</code>."),
        ("outcome", "Holds an <i>execution state</i> at write time — <code>submitted</code>, <code>timeout</code>, <code>max_turns</code>. The grade is assigned later, by a verifier, from this record."),
        ("usage", "Tokens, dollars, wall time and turns. Recorded per rollout so cost per successful solve is a fact about the run rather than an estimate made afterwards."),
    ]),

"core/config.py|EFFORTS": dict(
    lead="The four reasoning-effort levels — and the reason effort belongs in the <b>pinned</b> configuration.",
    points=[
        ("part of config_hash", "Two runs at different effort are not the same apparatus. If effort is not in the hash, the report will happily average them together."),
        ("printed every run", "Effort appears in the trace header and on screen, alongside model and temperature."),
        ("not a tuning knob", "Kapoor et al. (2025) found higher reasoning effort <i>reduced</i> accuracy in most of their runs. That is only discoverable if effort was recorded with every trace — otherwise it looks like noise."),
    ]),

"agent/sandbox.py|run_python": dict(
    lead="Executes submitted code in a fresh, isolated interpreter, and never raises on the code's own errors.",
    points=[
        ('"-I", "-S"', "Isolated mode with no site packages, so the environment the model gets is the same on every machine."),
        ("PREAMBLE + code", "Sockets and the network-reaching imports are disabled before a single line of submitted code runs. A subprocess that never had the capability is easier to reason about than one that gave it up."),
        ("preexec_fn=_limits", "CPU and file-size caps in the child. Best effort — a limit the platform refuses is skipped, and the wall-clock timeout is the backstop that always holds."),
        ("TimeoutExpired", "A timeout returns a result with <code>timed_out=True</code>, not an exception. It is something that happened and must be recorded, not an error to propagate."),
    ]),

"runner/rollouts.py|run_batch": dict(
    lead="Runs n rollouts across the task set with bounded concurrency, resuming from whatever is already on disk.",
    points=[
        ("done = completed_keys", "Resumption is a read of the trace store. There is no bookkeeping table that could drift out of step with the data."),
        ("header[simulated]", "Every trace records whether a provider was actually called. A corpus can always say what produced it."),
        ("except Exception", "A job that raised still gets a rollout written, with outcome <code>error</code>. There is no path where something happens and nothing is recorded."),
        ("ThreadPoolExecutor", "Concurrency is bounded, not unlimited — the provider is a shared resource and a batch that trips rate limits measures the rate limiter."),
    ]),

"metrics/cost.py|summarise": dict(
    lead="Cost per run, and cost per <b>successful</b> solve.",
    points=[
        ("usd_per_run", "The number most reports give. It rewards an agent that fails cheaply."),
        ("usd_per_successful_solve", "Total spend divided by solves. This is what the capability actually costs to obtain, and it is the one that changes decisions."),
        ("float('inf')", "When nothing succeeded, the honest value is infinity — not zero, and not a blank cell."),
    ]),

"verifiers/process_judge.py|SYSTEM": dict(
    lead="The judge's system prompt. Three sentences, and every clause is doing work.",
    kind="judge",
    points=[
        ("whether ... establishes", "The task is framed as a question about <i>sufficiency of the argument</i>, not about correctness of the conclusion."),
        ("not being asked whether the conclusion is correct", "Said explicitly, because a model handed a maths problem will otherwise default to solving it and grading its own answer."),
        ("will not be told the correct answer", "Sets the expectation that the absence of a key is deliberate, so the judge does not treat it as missing context to be inferred."),
    ]),

"metrics/judges.py|inter_judge_agreement": dict(
    lead="How often the two judges agree — reported as a headline number, never a footnote.",
    kind="judge",
    points=[
        ("len(byjudge) != 2", "Only traces carrying both verdicts are counted. A trace one judge rejected at parse time is excluded rather than silently treated as agreement."),
        ("raw_agreement", "The share of items where the two labels match. Easy to read and easy to over-trust."),
        ("cohens_kappa", "Agreement above chance. On a skewed label distribution — where both judges say ESTABLISHES most of the time — raw agreement is high while the judges share almost no information. Kappa is what survives that."),
        ("confusion", "Which pairs of labels they disagree on. Mostly ESTABLISHES against INCOMPLETE is a threshold disagreement; ESTABLISHES against ERROR is a factual one, and far more serious."),
    ]),

"verifiers/process_judge.py|judge": dict(
    lead="Renders, calls, parses, records. The four lines that make a judged number reproducible.",
    kind="judge",
    points=[
        ("hasattr(..., 'verdict')", "One branch for the offline simulator, one for a real provider. Everything else about the judging path is identical, so a rehearsal exercises the real code."),
        ("judge_model=", "The judge's exact model string is stored on the verdict. The judge is part of the apparatus and is pinned exactly as the system under test is."),
        ("blinded=", "The condition is stored too, which is the only reason the blinded/unblinded ablation can be computed later from the verdict store."),
    ]),
}
