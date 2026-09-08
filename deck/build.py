"""Assemble the workshop decks.

Code shown on a slide is EXTRACTED FROM THE REAL FILE at build time, never
retyped. If a module changes and a slide would go stale, this script is what
keeps them in step — rebuild and the slide is correct again.

    python3 deck/build.py

Placeholders understood in deck/*.src.html:
    {{LOGO}}                       the ISSAI symbol definition (once per file)
    {{CODE|path|symbol|caption}}   a function/class pulled by name
    {{CODE|path|L12-40|caption}}   an explicit line range
"""
from __future__ import annotations

import ast
import html
import io
import keyword
import pathlib
import re
import sys
import textwrap
import tokenize

ROOT = pathlib.Path(__file__).resolve().parent.parent
DECK = ROOT / "deck"

sys.path.insert(0, str(DECK))
from explain import EXPLAIN  # noqa: E402
from components import split  # noqa: E402
from components_explain import C as COMPONENTS  # noqa: E402

_KW = set(keyword.kwlist) | {"self", "cls"}
_SOFT = {"match", "case", "type"}


def highlight(src: str) -> str:
    """Tokenise real Python and wrap tokens in spans. Build-time, so the page
    needs no highlighting library and works with the network unplugged."""
    out, prev_row, prev_col = [], 1, 0
    lines = src.splitlines(keepends=True)
    nlines = len(lines)

    def line(i: int) -> str:
        return lines[i - 1] if 1 <= i <= nlines else ""

    prev_name = None
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError):
        return html.escape(src)

    for tok in toks:
        srow, scol = tok.start
        erow, ecol = tok.end
        # emit whatever whitespace sat between the last token and this one
        if srow > prev_row:
            out.append(html.escape(line(prev_row)[prev_col:]))
            for r in range(prev_row + 1, srow):
                out.append(html.escape(line(r)))
            out.append(html.escape(line(srow)[:scol]))
        elif scol > prev_col:
            out.append(html.escape(line(srow)[prev_col:scol]))

        text = html.escape(tok.string)
        cls = None
        if tok.type == tokenize.COMMENT:
            cls = "c"
        elif tok.type == tokenize.STRING:
            cls = "s"
        elif tok.type == tokenize.NUMBER:
            cls = "n"
        elif tok.type == tokenize.NAME:
            if tok.string in _KW or (tok.string in _SOFT and prev_name in (None, "")):
                cls = "k"
            elif prev_name in ("def", "class"):
                cls = "d"
        elif tok.type == tokenize.OP and tok.string == "@" and scol == 0:
            cls = "at"

        out.append(f'<span class="{cls}">{text}</span>' if cls else text)
        if tok.type == tokenize.NAME:
            prev_name = tok.string
        elif tok.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT):
            prev_name = None
        prev_row, prev_col = erow, ecol
    return "".join(out)


def extract(path: pathlib.Path, selector: str) -> str:
    src = path.read_text(encoding="utf-8")
    m = re.fullmatch(r"L(\d+)-(\d+)", selector)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return "\n".join(src.splitlines()[a - 1:b])
    if selector in ("", "*"):
        return src
    tree = ast.parse(src)
    wanted = selector.split(".")
    node, scope = None, tree.body
    for part in wanted:
        node = next((n for n in scope
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                       ast.Assign, ast.AnnAssign))
                     and (getattr(n, "name", None) == part
                          or any(getattr(t, "id", None) == part
                                 for t in getattr(n, "targets", [])))), None)
        if node is None:
            raise KeyError(f"{selector!r} not found in {path.name}")
        scope = getattr(node, "body", [])
    start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    return "\n".join(src.splitlines()[start - 1:node.end_lineno])


def explain_block(key: str) -> str:
    """Render the explanation that must accompany every code block.

    Missing entries are a build error, not a silently plain slide — that is
    how "explain everything on screen" stops being a good intention.
    """
    e = EXPLAIN.get(key)
    if e is None:
        raise SystemExit(
            f"no explanation for {key!r}. Add an entry to deck/explain.py — "
            f"nothing goes on a slide unexplained."
        )
    cls = "explain explain--judge" if e.get("kind") == "judge" else "explain"
    pts = "".join(
        f"<li><code>{html.escape(tok)}</code><span>{body}</span></li>"
        for tok, body in e.get("points", [])
    )
    return (f'<div class="{cls}"><p class="explain__lead">{e["lead"]}</p>'
            f'<ul class="explain__pts">{pts}</ul></div>')


def code_block(spec: str) -> str:
    parts = spec.split("|")
    relpath, selector = parts[1], parts[2]
    caption = parts[3] if len(parts) > 3 else ""
    path = ROOT / relpath
    # Methods and nested defs come out indented; dedent so the snippet is
    # valid Python on its own and tokenises cleanly.
    body = highlight(textwrap.dedent(extract(path, selector)).rstrip())
    what = f'<span class="code__what">{html.escape(caption)}</span>' if caption else ""
    return (f'<div class="code"><div class="code__bar">'
            f'<span class="code__file">{html.escape(relpath)}</span>{what}</div>'
            f"<pre><code>{body}</code></pre></div>"
            + explain_block(f"{relpath}|{selector}"))


def term_block(spec: str) -> str:
    """Embed a REAL captured terminal transcript. Never a mock-up of one."""
    parts = spec.split("|")
    relpath, cmd = parts[1], parts[2]
    lines = (ROOT / relpath).read_text(encoding="utf-8").rstrip("\n").splitlines()
    keep = parts[3] if len(parts) > 3 else ""
    if keep:
        a, b = (int(x) for x in keep.split("-"))
        lines = lines[a - 1:b]
    body = []
    for ln in lines:
        e = html.escape(ln)
        low = ln.strip()
        if low.startswith("PASS") or "green" in low or "0 solver calls" in low:
            e = f'<span class="g">{e}</span>'
        elif low.startswith("FAIL") or low.startswith("SIMULATED") or "NOT measurements" in low:
            e = f'<span class="y">{e}</span>'
        elif set(low) <= set("-=") and low:
            e = f'<span class="dimtxt">{e}</span>'
        body.append(e)
    return (f'<div class="term"><div class="term__bar">'
            f'<span class="term__dot"></span><span class="term__dot"></span>'
            f'<span class="term__dot"></span>'
            f'<span class="term__cmd">$ {html.escape(cmd)}</span></div>'
            f'<pre>{chr(10).join(body)}</pre></div>'
            + explain_block(relpath))


# --------------------------------------------------------------------------
# Whole-file rendering. The deck shows complete modules, split into components,
# every one of them explained. components.split() asserts the components tile
# the file, so "all the code is here" is checked rather than claimed.
# --------------------------------------------------------------------------
KIND_LABEL = {
    "docstring": "module docstring", "imports": "imports", "const": "constants",
    "class": "class", "def": "function", "main": "entry point",
    "bootstrap": "bootstrap", "file": "file",
}


def _auto_note(kind: str, name: str, src: str, relpath: str) -> str | None:
    """Explanations that are better computed than written by hand."""
    if kind == "docstring":
        return ("The module's own statement of intent. It is the first thing to read: it says "
                "what the file is for, and in several cases what it deliberately refuses to do.")
    if kind == "imports":
        mods = set()
        for line in src.splitlines():
            line = line.strip()
            if line.startswith("import "):
                mods.add(line.split()[1].split(".")[0])
            elif line.startswith("from "):
                mods.add(line.split()[1].split(".")[0])
        internal = {"core", "agent", "runner", "verifiers", "metrics", "tasks", "display"}
        own = sorted(m for m in mods if m in internal)
        ext = sorted(m for m in mods if m not in internal and m != "__future__")
        third = [m for m in ext if m in {"openai", "google", "yaml", "datasets", "sympy", "numpy"}]
        bits = []
        if ext:
            bits.append("Standard library only" if not third
                        else "Third-party: " + ", ".join(f"<code>{m}</code>" for m in third))
        if own:
            bits.append("depends on " + ", ".join(f"<code>{m}</code>" for m in own)
                        + " inside the project")
        else:
            bits.append("depends on no other module in the project")
        return ". ".join(bits) + "."
    if kind == "bootstrap":
        return ("Lets this file run as a script as well as be imported, without an install step. "
                "Three lines, so a demo never fails on a packaging detail.")
    return None


def full_file(spec: str) -> str:
    parts = spec.split("|")
    relpath = parts[1]
    path = ROOT / relpath
    comps = split(path)
    total = sum(1 for _ in open(path, encoding="utf-8"))

    out = [f'<div class="filehead"><span class="filehead__p">{html.escape(relpath)}</span>'
           f'<span class="filehead__m">{len(comps)} components &middot; {total} lines &middot; '
           f'shown in full</span></div>']

    for kind, name, a, b, src in comps:
        key = f"{relpath}::{name}"
        entry = COMPONENTS.get(key)
        if entry is None:
            entry = _auto_note(kind, name, src, relpath)
        if entry is None:
            raise SystemExit(
                f"no explanation for component {key!r} ({kind}). "
                f"Add it to deck/components_explain.py — every component is explained."
            )
        text, cite = entry if isinstance(entry, tuple) else (entry, None)

        lang_ok = path.suffix == ".py"
        body = highlight(textwrap.dedent(src)) if lang_ok else html.escape(src)
        cref = (f'<p class="cite"><span>cited</span>{html.escape(cite)}</p>') if cite else ""
        out.append(
            f'<section class="comp comp--{kind}">'
            f'<header class="comp__h">'
            f'<span class="comp__kind">{KIND_LABEL.get(kind, kind)}</span>'
            f'<span class="comp__name">{html.escape(name)}</span>'
            f'<span class="comp__lines">L{a}&ndash;{b}</span></header>'
            f'<div class="code code--comp"><pre><code>{body}</code></pre></div>'
            f'<div class="comp__x"><p>{text}</p>{cref}</div>'
            f"</section>"
        )
    return '<div class="fullfile">' + "".join(out) + "</div>"


def build(name: str) -> pathlib.Path:
    src = (DECK / f"{name}.src.html").read_text(encoding="utf-8")
    src = src.replace("{{LOGO}}", (DECK / "issai-symbol.svg").read_text(encoding="utf-8"))
    src = src.replace("{{CSS}}", (DECK / "deck.css").read_text(encoding="utf-8"))
    src = re.sub(r"\{\{CODE\|[^}]+\}\}", lambda m: code_block(m.group(0)[2:-2]), src)
    src = re.sub(r"\{\{TERM\|[^}]+\}\}", lambda m: term_block(m.group(0)[2:-2]), src)
    src = re.sub(r"\{\{FULL\|[^}]+\}\}", lambda m: full_file(m.group(0)[2:-2]), src)
    left = re.findall(r"\{\{[A-Z]+[^}]*\}\}", src)
    if left:
        raise SystemExit(f"unresolved placeholder(s) in {name}: {left[:3]}")
    out = ROOT / f"{name}.html"
    out.write_text(src, encoding="utf-8")
    return out


if __name__ == "__main__":
    for n in ("index", "about", "workshop"):
        p = build(n)
        print(f"wrote {p.relative_to(ROOT)}  {p.stat().st_size:,} bytes")
