"""Read KiCad symbol and footprint libraries for the generators (stdlib only).

Only the current KiCad file format is read. Project libraries kept in an older format
(`hardware/kicad/lib/airq.*`, written by easyeda2kicad) are first copied into the build folder
with `kicad-cli sym upgrade` / `fp upgrade` (see build.py); KiCad's stock libraries are current.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sexpr import QStr, child, children, parse


@dataclass(frozen=True)
class Pin:
    number: str
    name: str
    etype: str    # KiCad electrical type: input, output, passive, power_in, unspecified, ...
    x: float      # connection point in library coordinates (mm, Y up)
    y: float
    angle: int    # direction from the connection point into the symbol body (0 = +X, 90 = +Y)


def split_lib_id(lib_id: str) -> tuple[str, str]:
    nick, sep, name = lib_id.partition(":")
    if not sep or not nick or not name:
        raise ValueError(f"library id {lib_id!r} must look like 'library:name'")
    return nick, name


def _span(text: str, start: int) -> int:
    """Index just past the list that opens at text[start] == '(' (quote-aware)."""
    depth, i, n = 0, start, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while text[i] != '"':
                i += 2 if text[i] == "\\" else 1
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced '(' in library file")


def symbol_pins(sym: list) -> list[Pin]:
    """Pins of a (single-unit) library symbol, from all its unit/body-style sub-symbols."""
    pins = []
    for sub in children(sym, "symbol"):
        unit, style = (int(v) for v in re.fullmatch(r".*_(\d+)_(\d+)", sub[1]).groups())
        if unit > 1:
            raise ValueError(f"symbol {sym[1]}: multi-unit symbols are not supported")
        if style > 1:
            continue  # alternate (De Morgan) body style: same pins
        for p in children(sub, "pin"):
            at = child(p, "at")
            pins.append(Pin(number=child(p, "number")[1], name=child(p, "name")[1], etype=p[1],
                            x=float(at[1]), y=float(at[2]), angle=int(float(at[3])) % 360))
    return pins


def is_power_symbol(sym: list) -> bool:
    """True for power symbols (GND, +3V3, PWR_FLAG): virtual parts that name a global net."""
    return child(sym, "power") is not None


def symbol_property(sym: list, name: str) -> str | None:
    for p in children(sym, "property"):
        if p[1] == name:
            return p[2]
    return None


class Libraries:
    """Library nickname -> file, for symbols (.kicad_sym) and footprints (.pretty folders).

    Nicknames missing from the maps are looked up in the stock folders as `<nick>.kicad_sym`
    and `<nick>.pretty`, like KiCad's default global library tables.
    """

    def __init__(self, symbols: dict[str, Path], footprints: dict[str, Path],
                 stock_symbols: Path | None = None, stock_footprints: Path | None = None):
        self._sym = {k: Path(v) for k, v in symbols.items()}
        self._fp = {k: Path(v) for k, v in footprints.items()}
        self._stock_sym, self._stock_fp = stock_symbols, stock_footprints
        self._sym_text: dict[Path, str] = {}
        self._sym_cache: dict[str, list] = {}
        self._fp_cache: dict[str, list] = {}

    def is_stock_symbol_lib(self, nick: str) -> bool:
        return nick not in self._sym

    def is_stock_footprint_lib(self, nick: str) -> bool:
        return nick not in self._fp

    def symbol_file(self, nick: str) -> Path:
        if nick in self._sym:
            return self._sym[nick]
        if self._stock_sym is None:
            raise FileNotFoundError(f"symbol library {nick!r}: no stock symbol folder configured")
        return self._stock_sym / f"{nick}.kicad_sym"

    def footprint_dir(self, nick: str) -> Path:
        if nick in self._fp:
            return self._fp[nick]
        if self._stock_fp is None:
            raise FileNotFoundError(f"footprint library {nick!r}: no stock footprint folder configured")
        return self._stock_fp / f"{nick}.pretty"

    def symbol(self, lib_id: str) -> list:
        """The `(symbol "NAME" ...)` tree of `lib_id` exactly as in its library."""
        if lib_id not in self._sym_cache:
            nick, name = split_lib_id(lib_id)
            path = self.symbol_file(nick)
            if path not in self._sym_text:
                self._sym_text[path] = path.read_text(encoding="utf-8")
            text = self._sym_text[path]
            m = re.search(r'\(symbol\s+"' + re.escape(name) + r'"[\s)]', text)
            if not m:
                raise KeyError(f"symbol {lib_id!r} not found in {path}")
            sym = parse(text[m.start():_span(text, m.start())])
            if child(sym, "extends") is not None:
                raise ValueError(f"symbol {lib_id!r} extends another symbol: not supported")
            self._sym_cache[lib_id] = sym
        return self._sym_cache[lib_id]

    def footprint(self, lib_id: str) -> list:
        """The parsed `(footprint "NAME" ...)` tree of `lib_id` from its .kicad_mod file."""
        if lib_id not in self._fp_cache:
            nick, name = split_lib_id(lib_id)
            path = self.footprint_dir(nick) / f"{name}.kicad_mod"
            if not path.is_file():
                raise KeyError(f"footprint {lib_id!r} not found ({path})")
            fp = parse(path.read_text(encoding="utf-8"))
            if fp[0] != "footprint":
                raise ValueError(f"{path}: old footprint format ({fp[0]}); upgrade it with "
                                 "`kicad-cli fp upgrade` first")
            self._fp_cache[lib_id] = fp
        return self._fp_cache[lib_id]


def embedded_symbol(sym: list, lib_id: str) -> list:
    """A copy of library symbol `sym` named `lib_id`, as stored in a schematic's lib_symbols."""
    return [sym[0], QStr(lib_id), *sym[2:]]
