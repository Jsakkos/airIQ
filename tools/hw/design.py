"""Load and check the YAML design source of a board (hardware/src/<board>/), see hardware/README.md.

Files in the source folder:
    project.yaml   project name, title block, sheet order, power symbols, libraries, ERC rules
    <sheet>.yaml   one per schematic sheet: its parts, where they sit on the page, pin -> net
    layout.yaml    board outline, design rules, net classes, DRC rules, footprint placement

This module checks structure and spelling only (unknown keys, types, angles); the generators
check everything that needs the libraries (pin numbers, footprints).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

NC = "NC"
_NET_RE = re.compile(r"[^\s/{}\[\]\"]+")


class DesignError(ValueError):
    """Every problem found in the design source, one per line."""

    def __init__(self, problems: list[str]):
        super().__init__("\n".join(problems))
        self.problems = problems


@dataclass
class PartSrc:
    ref: str
    symbol: str
    at: tuple[float, float]
    rot: int = 0
    mirror: str | None = None
    stub: float = 0.0          # wire length between each pin and its label / power symbol
    value: str | None = None
    footprint: str | None = None
    lcsc: str | None = None
    dnp: bool = False
    fields: dict[str, str] = field(default_factory=dict)
    pins: dict[str, str] | list[str] = field(default_factory=dict)


@dataclass
class Note:
    text: str
    at: tuple[float, float]
    size: float = 1.27


@dataclass
class SheetSrc:
    name: str
    title: str
    paper: str
    parts: list[PartSrc]
    source: Path
    notes: list[Note] = field(default_factory=list)


@dataclass
class Design:
    name: str
    title: str
    company: str
    rev: str
    sheets: list[SheetSrc]
    power_symbols: dict[str, str]
    symbol_libs: dict[str, Path]
    footprint_libs: dict[str, Path]
    out_dir: Path
    erc_severities: dict[str, str]
    layout: dict
    src_dir: Path

    def rel(self, path: Path) -> str:
        """`path` relative to the repository root (the source folder is hardware/src/<board>)."""
        try:
            return Path(path).resolve().relative_to(self.src_dir.parents[2]).as_posix()
        except (ValueError, IndexError):
            return Path(path).name


_PROJECT_KEYS = {"project", "title", "company", "rev", "sheets", "power_symbols", "libraries",
                 "output", "erc_severities"}
_SHEET_KEYS = {"title", "paper", "parts", "notes"}
_NOTE_KEYS = {"text", "at", "size"}
_PART_KEYS = {"symbol", "at", "rot", "mirror", "stub", "value", "footprint", "lcsc", "dnp",
              "fields", "pins"}
_LAYOUT_KEYS = {"board", "rules", "netclasses", "drc_severities", "custom_rules", "placement"}
_BOARD_KEYS = {"width", "height", "outline", "cutouts", "origin", "thickness"}
PAPERS = {"A4": (297.0, 210.0), "A3": (420.0, 297.0)}


def valid_net_name(name: str) -> bool:
    return bool(_NET_RE.fullmatch(name)) and not name.startswith("unconnected-")


def _load_yaml(path: Path, problems: list[str]) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        problems.append(f"{path}: cannot read: {e}")
        return {}
    if not isinstance(data, dict):
        problems.append(f"{path}: expected a mapping at the top level")
        return {}
    return data


def _unknown(data: dict, allowed: set[str], where: str, problems: list[str]) -> None:
    for k in data:
        if k not in allowed:
            problems.append(f"{where}: unknown key {k!r} (allowed: {', '.join(sorted(allowed))})")


def _number_pair(v, where: str, problems: list[str]) -> tuple[float, float]:
    if (isinstance(v, list) and len(v) == 2
            and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in v)):
        return float(v[0]), float(v[1])
    problems.append(f"{where}: expected [x, y] in mm, got {v!r}")
    return 0.0, 0.0


def _net(v, where: str, problems: list[str]) -> str:
    if not isinstance(v, str):  # YAML turns NO/ON/yes into booleans and 1 into an int
        problems.append(f"{where}: net {v!r} is not a string (quote it in the YAML)")
        return NC
    if v != NC and not valid_net_name(v):
        problems.append(f"{where}: invalid net name {v!r} (no spaces, '/', brackets or quotes)")
    return v


def _part(ref: str, d, where: str, problems: list[str]) -> PartSrc | None:
    if not isinstance(d, dict):
        problems.append(f"{where}: part {ref} must be a mapping")
        return None
    _unknown(d, _PART_KEYS, f"{where}: part {ref}", problems)
    if not isinstance(d.get("symbol"), str):
        problems.append(f"{where}: part {ref} needs `symbol: library:name`")
        return None
    rot = d.get("rot", 0)
    if rot not in (0, 90, 180, 270):
        problems.append(f"{where}: part {ref}: rot must be 0, 90, 180 or 270, got {rot!r}")
        rot = 0
    mirror = d.get("mirror")
    if mirror not in (None, "x", "y"):
        problems.append(f"{where}: part {ref}: mirror must be x or y, got {mirror!r}")
        mirror = None
    stub = d.get("stub", 0)
    if not isinstance(stub, (int, float)) or isinstance(stub, bool) or stub < 0:
        problems.append(f"{where}: part {ref}: stub must be a length in mm, got {stub!r}")
        stub = 0
    raw_pins = d.get("pins", {})
    if isinstance(raw_pins, dict):
        pins = {str(k): _net(v, f"{where}: {ref} pin {k}", problems) for k, v in raw_pins.items()}
    elif isinstance(raw_pins, list):
        pins = [_net(v, f"{where}: {ref} pin {i}", problems) for i, v in enumerate(raw_pins, 1)]
    else:
        problems.append(f"{where}: part {ref}: pins must be a mapping or a list")
        pins = {}
    fields = d.get("fields") or {}
    if not isinstance(fields, dict):
        problems.append(f"{where}: part {ref}: fields must be a mapping")
        fields = {}
    opt = {k: (None if d.get(k) is None else str(d[k])) for k in ("value", "footprint", "lcsc")}
    return PartSrc(ref=ref, symbol=d["symbol"],
                   at=_number_pair(d.get("at"), f"{where}: part {ref} at", problems),
                   rot=rot, mirror=mirror, stub=float(stub), dnp=bool(d.get("dnp", False)),
                   fields={str(k): str(v) for k, v in fields.items()}, pins=pins, **opt)


def _polygon(v, where: str, problems: list[str]) -> None:
    if not isinstance(v, list) or len(v) < 3:
        problems.append(f"{where}: expected a list of at least 3 [x, y] points")
        return
    for i, p in enumerate(v):
        _number_pair(p, f"{where} point {i}", problems)


def _check_board(board, problems: list[str]) -> None:
    """layout.yaml `board`: a width x height rectangle or an `outline` polygon, plus cutouts."""
    if not isinstance(board, dict):
        problems.append("layout.yaml: `board` must be a mapping")
        return
    _unknown(board, _BOARD_KEYS, "layout.yaml: board", problems)
    rect = "width" in board or "height" in board
    if rect == ("outline" in board):
        problems.append("layout.yaml: board needs either `width` and `height` or `outline`")
    elif rect and not all(isinstance(board.get(k), (int, float)) for k in ("width", "height")):
        problems.append("layout.yaml: board `width` and `height` must both be numbers (mm)")
    elif not rect:
        _polygon(board["outline"], "layout.yaml: board outline", problems)
    for i, c in enumerate(board.get("cutouts") or []):
        _polygon(c, f"layout.yaml: board cutout {i + 1}", problems)


def _sheet(name: str, path: Path, problems: list[str]) -> SheetSrc:
    data = _load_yaml(path, problems)
    _unknown(data, _SHEET_KEYS, str(path), problems)
    paper = data.get("paper", "A4")
    if paper not in PAPERS:
        problems.append(f"{path}: paper must be one of {', '.join(PAPERS)}")
        paper = "A4"
    parts = []
    for ref, d in (data.get("parts") or {}).items():
        p = _part(str(ref), d, str(path), problems)
        if p is not None:
            parts.append(p)
    notes = []
    for i, n in enumerate(data.get("notes") or [], 1):
        if not isinstance(n, dict) or not isinstance(n.get("text"), str):
            problems.append(f"{path}: note {i} needs `text:` and `at:`")
            continue
        _unknown(n, _NOTE_KEYS, f"{path}: note {i}", problems)
        notes.append(Note(text=n["text"], at=_number_pair(n.get("at"), f"{path}: note {i} at",
                                                          problems),
                          size=float(n.get("size", 1.27))))
    return SheetSrc(name=name, title=str(data.get("title", name)), paper=paper, parts=parts,
                    source=path, notes=notes)


def load_design(src_dir: Path) -> Design:
    """Read `src_dir`/project.yaml, its sheets and layout.yaml; raise DesignError on problems."""
    src_dir = Path(src_dir)
    problems: list[str] = []
    proj = _load_yaml(src_dir / "project.yaml", problems)
    _unknown(proj, _PROJECT_KEYS, "project.yaml", problems)
    for k in ("project", "output", "sheets"):
        if k not in proj:
            problems.append(f"project.yaml: missing `{k}`")
    if problems:
        raise DesignError(problems)
    sheets = [_sheet(n, src_dir / f"{n}.yaml", problems) for n in proj["sheets"]]
    refs: dict[str, str] = {}
    for s in sheets:
        for p in s.parts:
            if p.ref in refs:
                problems.append(f"{s.source.name}: reference {p.ref} is also used in {refs[p.ref]}")
            refs[p.ref] = s.source.name
    power = {str(k): str(v) for k, v in (proj.get("power_symbols") or {}).items()}
    libs = proj.get("libraries") or {}
    layout_path = src_dir / "layout.yaml"
    layout = _load_yaml(layout_path, problems) if layout_path.exists() else {}
    _unknown(layout, _LAYOUT_KEYS, "layout.yaml", problems)
    if "board" in layout:
        _check_board(layout["board"], problems)
    if problems:
        raise DesignError(problems)
    return Design(
        name=str(proj["project"]), title=str(proj.get("title", proj["project"])),
        company=str(proj.get("company", "")), rev=str(proj.get("rev", "")), sheets=sheets,
        power_symbols=power,
        symbol_libs={k: (src_dir / v).resolve() for k, v in (libs.get("symbols") or {}).items()},
        footprint_libs={k: (src_dir / v).resolve() for k, v in (libs.get("footprints") or {}).items()},
        out_dir=(src_dir / proj["output"]).resolve(),
        erc_severities={str(k): str(v) for k, v in (proj.get("erc_severities") or {}).items()},
        layout=layout, src_dir=src_dir.resolve())
