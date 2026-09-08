"""A deliberately small YAML reader for this project's config subset.

PyYAML is used when it is installed. This fallback exists so the harness runs
with an empty environment during a live demo, which is the only reason to
hand-roll a parser at all. It supports exactly what configs/ uses: nested
mappings by indentation, block lists, inline lists, comments, and scalars.
"""
from __future__ import annotations

import re

_NUM = re.compile(r"^-?\d+(\.\d+)?$")


def _scalar(tok: str):
    tok = tok.strip()
    if tok.startswith("#"):
        return None
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in "\"'":
        return tok[1:-1]
    low = tok.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~", ""):
        return None
    if _NUM.match(tok):
        return float(tok) if "." in tok else int(tok)
    return tok


def _strip_comment(line: str) -> str:
    out, quote = [], None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _inline(tok: str):
    tok = tok.strip()
    if tok.startswith("[") and tok.endswith("]"):
        body = tok[1:-1].strip()
        return [] if not body else [_scalar(p) for p in body.split(",")]
    return _scalar(tok)


def loads(text: str):
    lines = []
    for raw in text.splitlines():
        body = _strip_comment(raw)
        if body.strip():
            lines.append((len(body) - len(body.lstrip()), body.strip()))

    def parse(i: int, indent: int):
        if i < len(lines) and lines[i][1].startswith("- "):
            items = []
            while i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("- "):
                rest = lines[i][1][2:].strip()
                if ":" in rest and not rest.startswith(("[", '"', "'")):
                    sub, i = parse_map_from_inline(rest, i, indent)
                    items.append(sub)
                else:
                    items.append(_inline(rest))
                    i += 1
            return items, i
        out = {}
        while i < len(lines) and lines[i][0] >= indent:
            if lines[i][0] > indent:
                raise ValueError(f"bad indent at {lines[i][1]!r}")
            key, _, rest = lines[i][1].partition(":")
            key, rest = key.strip(), rest.strip()
            if rest:
                out[key] = _inline(rest)
                i += 1
            else:
                i += 1
                if i < len(lines) and lines[i][0] > indent:
                    out[key], i = parse(i, lines[i][0])
                else:
                    out[key] = None
        return out, i

    def parse_map_from_inline(rest: str, i: int, indent: int):
        # "- key: value" opens a mapping whose siblings are indented under it
        sub = {}
        key, _, val = rest.partition(":")
        sub[key.strip()] = _inline(val.strip())
        i += 1
        child = indent + 2
        while i < len(lines) and lines[i][0] >= child and not lines[i][1].startswith("- "):
            k, _, v = lines[i][1].partition(":")
            sub[k.strip()] = _inline(v.strip())
            i += 1
        return sub, i

    data, _ = parse(0, lines[0][0] if lines else 0)
    return data


def load_file(path):
    text = open(path, "r", encoding="utf-8").read()
    try:
        import yaml  # noqa: PLC0415
        return yaml.safe_load(text)
    except ImportError:
        return loads(text)
