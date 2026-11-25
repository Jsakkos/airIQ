"""Stdlib-only S-expression reader and writer for KiCad files (.kicad_pcb, .kicad_sch, netlists).

`parse` returns nested lists of ``str``: ``(a (b "c d"))`` -> ``["a", ["b", "c d"]]``.
Quoted strings come back as ``QStr``, a ``str`` subclass, so readers can ignore the distinction
(``QStr("c d") == "c d"``) while `dumps` can write the tree back with the same quoting: KiCad reads
keywords only when bare (``(type solid)``) and names only when quoted when they contain spaces.
"""
import re

_WS = " \t\r\n"


class QStr(str):
    """A string atom written in double quotes (``"F.Cu"``), as opposed to a bare keyword or number."""

    __slots__ = ()


def parse(text: str) -> list:
    """Parse the first top-level form of ``text`` into nested lists of str."""
    stack: list[list] = []
    result = None
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in _WS:
            i += 1
        elif c == "(":
            stack.append([])
            i += 1
        elif c == ")":
            if not stack:
                raise ValueError(f"unbalanced ')' at offset {i}")
            done = stack.pop()
            if stack:
                stack[-1].append(done)
            elif result is None:
                result = done
            i += 1
        else:
            if c == '"':
                i += 1
                buf = []
                while True:
                    if i >= n:
                        raise ValueError("unterminated string")
                    c = text[i]
                    if c == "\\" and i + 1 < n:
                        nxt = text[i + 1]
                        buf.append({"n": "\n", "t": "\t", "r": "\r"}.get(nxt, nxt))
                        i += 2
                    elif c == '"':
                        i += 1
                        break
                    else:
                        buf.append(c)
                        i += 1
                atom = QStr("".join(buf))
            else:
                j = i
                while j < n and text[j] not in _WS and text[j] not in '()"':
                    j += 1
                atom = text[i:j]
                i = j
            if stack:
                stack[-1].append(atom)
            elif result is None:
                result = atom  # a bare top-level atom is returned as-is
    if stack:
        raise ValueError("unbalanced '(': missing ')'")
    if result is None:
        raise ValueError("empty input")
    return result


_ESCAPES = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\t": "\\t", "\r": "\\r"}


def _write_atom(a) -> str:
    if isinstance(a, QStr):
        return '"' + "".join(_ESCAPES.get(c, c) for c in a) + '"'
    s = str(a)
    if not s or any(c in s for c in _WS + '()"'):
        raise ValueError(f"bare atom {s!r} needs quoting: build it as QStr")
    return s


def dumps(node, level: int = 0) -> str:
    """Write a tree from `parse` (or built from lists, str and QStr) as KiCad-style text.

    A list whose items are all atoms stays on one line; otherwise each child list starts a new
    line indented by one tab. KiCad accepts any layout, so this only aims at readable diffs.
    """
    if not isinstance(node, list):
        return _write_atom(node)
    pad = "\t" * (level + 1)
    out = "(" + " ".join(_write_atom(a) for a in _leading_atoms(node))
    rest = node[len(_leading_atoms(node)):]
    for item in rest:
        out += "\n" + pad + dumps(item, level + 1)
    if any(isinstance(item, list) for item in rest):
        out += "\n" + "\t" * level
    return out + ")"


def _leading_atoms(node: list) -> list:
    n = 0
    while n < len(node) and not isinstance(node[n], list):
        n += 1
    return node[:n]


def children(node: list, name: str) -> list[list]:
    """All direct child lists of ``node`` whose head is ``name``."""
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def child(node: list, name: str) -> list | None:
    """First direct child list of ``node`` whose head is ``name``, else None."""
    for c in node:
        if isinstance(c, list) and c and c[0] == name:
            return c
    return None


def atom(node: list, name: str, default: str | None = None) -> str | None:
    """The first atom after the head of child ``name``: ``(name VALUE ...)`` -> VALUE."""
    c = child(node, name)
    if c is not None and len(c) > 1 and isinstance(c[1], str):
        return c[1]
    return default


_PREFIX_EXP = {"p": -12, "n": -9, "u": -6, "m": -3, "R": 0, "k": 3, "K": 3, "M": 6, "G": 9}
_VALUE_RE = re.compile(r"(\d*)(?:\.(\d+))?\s*([^\d.\s]*)(\d*)")


def parse_value(s: str) -> float:
    """Parse a KiCad-style component value into a float in base units.

    "5.1k" -> 5100.0, "4k7" -> 4700.0 (SI suffix as decimal mark), "2R2" -> 2.2,
    "10u" -> 1e-5, "100n" -> 1e-7, "10uF", "5.1kΩ", "4.7kohm" (trailing unit ignored),
    "µ" is read as "u". The decimal string is built with its exponent and converted by a
    single ``float()`` call, so results equal the matching literal exactly (no float multiplies).
    """
    t = s.strip().replace("µ", "u").replace("μ", "u")
    m = _VALUE_RE.fullmatch(t)
    if not m or not (m.group(1) or m.group(2)):
        raise ValueError(f"cannot parse component value {s!r}")
    whole, frac, letters, tail = m.groups()
    # strip a trailing unit: ohm word / symbol first, then farad / henry
    low = letters.lower()
    for unit in ("ohms", "ohm", "Ω".lower()):
        if low.endswith(unit):
            letters = letters[: -len(unit)]
            break
    else:
        if letters.endswith(("F", "H")):  # upper-case only: lower-case f would be femto
            letters = letters[:-1]
    if len(letters) > 1 or (letters and letters not in _PREFIX_EXP):
        raise ValueError(f"cannot parse component value {s!r}")
    if tail and not letters:
        raise ValueError(f"cannot parse component value {s!r}")
    exp = _PREFIX_EXP.get(letters, 0)
    digits = f"{whole or '0'}.{frac or ''}{tail}"
    return float(f"{digits}e{exp}")
