"""Stdlib-only S-expression reader for KiCad files (.kicad_pcb, netlists).

`parse` returns nested lists of ``str``: ``(a (b "c d"))`` -> ``["a", ["b", "c d"]]``.
Quoted strings and bare atoms both become plain ``str`` (the distinction is not needed here).
"""
import re

_WS = " \t\r\n"


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
                atom = "".join(buf)
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
