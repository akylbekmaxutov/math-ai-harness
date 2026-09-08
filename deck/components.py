"""Split a source file into components, covering every line exactly once.

The deck shows whole files, not excerpts. This is what makes that claim
checkable: `split()` asserts that the components it returns tile the file
completely, so a component nobody wrote an explanation for cannot quietly
vanish from the slide.
"""
from __future__ import annotations

import ast
import pathlib

IMPORTISH = (ast.Import, ast.ImportFrom)
DEFISH = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _name(node) -> str:
    if isinstance(node, DEFISH):
        return node.name
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name):
                return t.id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    if isinstance(node, ast.If):
        return "__main__"
    return ""


def _start(node) -> int:
    return min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])


def split(path: pathlib.Path):
    """-> [(kind, name, first_line, last_line, source_text)] covering the file."""
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines()
    if path.suffix in (".yaml", ".yml"):
        return [("file", path.name, 1, len(lines), src.rstrip("\n"))]

    tree = ast.parse(src)
    body = tree.body
    if not body:
        return [("file", path.name, 1, len(lines), src.rstrip("\n"))]

    groups: list[tuple[str, str, int, int]] = []
    i = 0
    # module docstring
    if (isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        groups.append(("docstring", "module docstring", 1, body[0].end_lineno))
        i = 1

    while i < len(body):
        node = body[i]
        if isinstance(node, IMPORTISH):
            j = i
            while j + 1 < len(body) and isinstance(body[j + 1], IMPORTISH):
                j += 1
            groups.append(("imports", "imports", _start(node), body[j].end_lineno))
            i = j + 1
        elif isinstance(node, DEFISH):
            kind = "class" if isinstance(node, ast.ClassDef) else "def"
            groups.append((kind, node.name, _start(node), node.end_lineno))
            i += 1
        elif isinstance(node, ast.If):
            # `if __name__ == "__main__"` is an entry point; any other
            # top-level `if` is a bootstrap (e.g. the sys.path shim that lets
            # a script be run directly as well as imported).
            t = node.test
            is_main = (isinstance(t, ast.Compare) and isinstance(t.left, ast.Name)
                       and t.left.id == "__name__")
            groups.append(("main" if is_main else "bootstrap",
                           "__main__" if is_main else "path bootstrap",
                           _start(node), node.end_lineno))
            i += 1
        else:
            j = i
            while (j + 1 < len(body)
                   and not isinstance(body[j + 1], DEFISH + IMPORTISH + (ast.If,))):
                j += 1
            nm = " · ".join(filter(None, (_name(body[k]) for k in range(i, j + 1)))) or "constants"
            groups.append(("const", nm, _start(node), body[j].end_lineno))
            i = j + 1

    # Extend each group backwards to absorb the blank lines and standalone
    # comments that precede it, so nothing between components is dropped.
    out = []
    prev_end = 0
    for kind, name, a, b in groups:
        out.append((kind, name, prev_end + 1, b))
        prev_end = b
    if prev_end < len(lines):                       # trailing lines
        kind, name, a, b = out[-1]
        out[-1] = (kind, name, a, len(lines))

    covered = []
    for kind, name, a, b in out:
        covered.extend(range(a, b + 1))
    assert covered == list(range(1, len(lines) + 1)), (
        f"{path}: components do not tile the file "
        f"({len(covered)} lines covered of {len(lines)})")

    return [(k, n, a, b, "\n".join(lines[a - 1:b]).rstrip()) for k, n, a, b in out]


if __name__ == "__main__":
    import sys
    root = pathlib.Path(__file__).resolve().parent.parent
    files = sorted(
        p for d in ("core", "agent", "runner", "verifiers", "metrics",
                    "tasks/math", "display", "scripts", "configs")
        for p in (root / d).iterdir()
        if p.suffix in (".py", ".yaml") and p.name != "__init__.py"
    )
    total = 0
    for f in files:
        comps = split(f)
        total += len(comps)
        print(f"\n{f.relative_to(root)}  ({len(comps)} components)")
        for k, n, a, b, _ in comps:
            print(f"    {k:10s} {n:34s} L{a}-{b}")
    print(f"\n{len(files)} files, {total} components")
