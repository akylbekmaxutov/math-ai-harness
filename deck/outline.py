"""The workshop's table of contents, in one place.

The sidebar is generated from this list and `deck/build.py` then checks that
every href it produced has a matching `id` in the finished page. A nav link
that goes nowhere is a build failure, not something to discover on stage.

Each entry is (anchor id, label, children). Two levels, which is as deep as a
sidebar should go when someone is reading it from the back of a lecture hall.
"""
from __future__ import annotations

OUTLINE = [
    ("introduction", "Introduction", []),
    ("question", "The Experimental Question", []),
    ("dataset", "The Dataset", [
        ("problem-set", "The Three Problems"),
        ("prompt-sample", "What the Model Receives"),
    ]),
    ("harness", "Part I · Harness Engineering", [
        ("what-is-a-harness", "What is a Harness?"),
        ("harness-architecture", "Harness Architecture"),
        ("problem-loader", "Problem Loader"),
        ("experiment-config", "Experiment Configuration"),
        ("model-adapter", "Model Adapter"),
        ("reasoning-config", "Reasoning Configuration"),
        ("model-execution", "Model Execution"),
        ("trace-collector", "Trace Collector"),
        ("metrics-collector", "Metrics Collector"),
        ("cost-calculator", "Cost Calculator"),
        ("result-store", "Result Store"),
    ]),
    ("matrix", "The Experiment Matrix", []),
    ("running", "Running the Experiment", [
        ("one-run", "One Complete Run"),
        ("commands", "Every Command"),
    ]),
    ("judge", "Part II · LLM-as-a-Judge", [
        ("what-is-judge", "What is LLM-as-a-Judge?"),
        ("judge-architecture", "Judge Architecture"),
        ("candidate-output", "Candidate Output"),
        ("judge-prompt", "Judge Prompt"),
        ("rubric", "The Rubric"),
        ("structured-output", "Structured Output"),
        ("two-judges", "Two Judges"),
        ("judge-modes", "Judge Reasoning Modes"),
        ("agreement", "Judge Agreement"),
        ("limitations", "Advantages & Limitations"),
    ]),
    ("pipeline", "The Full Pipeline", []),
    ("results", "Results", [
        ("explorer", "Run Explorer"),
        ("judge-compare", "Judge Comparison"),
        ("failures", "What Went Wrong"),
        ("all-runs", "Every Run & Trace"),
        ("all-verdicts", "Every Judge Verdict"),
        ("dashboard", "Model Comparison"),
        ("dimensions", "What We Are Measuring"),
    ]),
    ("reproducibility", "Reproducibility", [
        ("schema", "Data Schema"),
        ("security", "Keys & Security"),
        ("errors", "Error Handling"),
    ]),
    ("conclusions", "Conclusions", []),
    ("appendix", "Appendix · Full Source", []),
]


def anchors() -> list[str]:
    """Every id the sidebar will link to, parents and children alike."""
    out = []
    for pid, _, kids in OUTLINE:
        out.append(pid)
        out.extend(kid for kid, _ in kids)
    return out


def render() -> str:
    """The sidebar markup. Parents with children are toggles; parents without
    are plain links, so a section never pretends to have subsections."""
    import html

    items = []
    for i, (pid, label, kids) in enumerate(OUTLINE, start=1):
        num = f"{i:02d}"
        if not kids:
            items.append(
                f'<li class="nav__item"><a class="nav__link nav__link--top" href="#{pid}" '
                f'data-anchor="{pid}"><span class="nav__num">{num}</span>'
                f'<span class="nav__label">{html.escape(label)}</span></a></li>'
            )
            continue
        sub = "".join(
            f'<li><a class="nav__link nav__link--sub" href="#{kid}" data-anchor="{kid}">'
            f'{html.escape(klabel)}</a></li>'
            for kid, klabel in kids
        )
        items.append(
            f'<li class="nav__item nav__item--group">'
            f'<div class="nav__row">'
            f'<a class="nav__link nav__link--top" href="#{pid}" data-anchor="{pid}">'
            f'<span class="nav__num">{num}</span>'
            f'<span class="nav__label">{html.escape(label)}</span></a>'
            f'<button class="nav__toggle" type="button" aria-expanded="true" '
            f'aria-controls="sub-{pid}" '
            f'aria-label="Collapse {html.escape(label)}"></button>'
            f'</div>'
            f'<ul class="nav__sub" id="sub-{pid}">{sub}</ul></li>'
        )
    return '<ul class="nav__list">' + "".join(items) + "</ul>"
