"""Load and check the YAML design source of a board (hardware/src/<board>/), see hardware/README.md.

Files in the source folder:
    project.yaml   project name, title block, sheet order, power symbols, libraries, ERC rules,
                   and the interface contract (`interface:`, normally hardware/interface.yaml)
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
_GPIO_RE = re.compile(r"GPIO(\d+)")


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
    # per-pin wire lengths (pin number or name -> mm) when `stub` is given as a mapping
    pin_stubs: dict[str, float] = field(default_factory=dict)
    value: str | None = None
    footprint: str | None = None
    lcsc: str | None = None
    dnp: bool = False
    fields: dict[str, str] = field(default_factory=dict)
    pins: dict[str, str] | list[str] = field(default_factory=dict)
    # page offsets (mm, from `at`, Y down) of field texts: {Reference: (dx, dy), Role: ...}
    fields_at: dict[str, tuple[float, float]] = field(default_factory=dict)


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
    # hardware/interface.yaml (`signals`, `connectors`) when project.yaml names it: the generator
    # then wires the MCU (Role MCU) and every Role-tagged connector from it, see gen_sch.py
    interface: dict | None = None

    def rel(self, path: Path) -> str:
        """`path` relative to the repository root (the source folder is hardware/src/<board>)."""
        try:
            return Path(path).resolve().relative_to(self.src_dir.parents[2]).as_posix()
        except (ValueError, IndexError):
            return Path(path).name


_PROJECT_KEYS = {"project", "title", "company", "rev", "sheets", "power_symbols", "libraries",
                 "output", "erc_severities", "interface"}
_SHEET_KEYS = {"title", "paper", "parts", "notes"}
_NOTE_KEYS = {"text", "at", "size"}
_PART_KEYS = {"symbol", "at", "rot", "mirror", "stub", "value", "footprint", "lcsc", "dnp",
              "fields", "fields_at", "pins"}
_LAYOUT_KEYS = {"board", "rules", "netclasses", "drc_severities", "custom_rules", "placement"}
_BOARD_KEYS = {"width", "height", "outline", "cutouts", "origin", "thickness"}
# KiCad 10 board constraints (.kicad_pro board.design_settings.rules): numbers in mm, or booleans
_RULE_KEYS = {"min_clearance", "min_track_width", "min_via_diameter", "min_through_hole_diameter",
              "min_via_annular_width", "min_copper_edge_clearance", "min_hole_to_hole",
              "min_hole_clearance", "min_microvia_diameter", "min_microvia_drill",
              "min_silk_clearance", "min_text_height", "min_text_thickness", "min_connection",
              "min_groove_width", "min_resolved_spokes", "solder_mask_to_copper_clearance",
              "max_error"}
_RULE_FLAGS = {"allow_blind_buried_vias", "allow_microvias", "use_height_for_length_calcs"}
_NETCLASS_KEYS = {"clearance", "track_width", "via_diameter", "via_drill", "microvia_diameter",
                  "microvia_drill", "diff_pair_width", "diff_pair_gap", "diff_pair_via_gap", "nets"}
_SEVERITIES = {"error", "warning", "ignore"}
_PLACEMENT_KEYS = {"at", "ref"}
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
    dnp = d.get("dnp", False)
    if not isinstance(dnp, bool):  # a quoted "no" would otherwise read as true
        problems.append(f"{where}: part {ref}: dnp must be true or false, got {dnp!r}")
        dnp = False
    stub = d.get("stub", 0)
    pin_stubs: dict[str, float] = {}
    if isinstance(stub, dict):   # per pin: {pin number or name: length}
        for k, v in stub.items():
            if not _is_num(v) or v < 0:
                problems.append(f"{where}: part {ref}: stub.{k} must be a length in mm, got {v!r}")
            else:
                pin_stubs[str(k)] = float(v)
        stub = 0
    elif not isinstance(stub, (int, float)) or isinstance(stub, bool) or stub < 0:
        problems.append(f"{where}: part {ref}: stub must be a length in mm (or a mapping pin: "
                        f"length), got {stub!r}")
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
    fields_at = d.get("fields_at") or {}
    if not isinstance(fields_at, dict):
        problems.append(f"{where}: part {ref}: fields_at must be a mapping field: [dx, dy]")
        fields_at = {}
    fields_at = {str(k): _number_pair(v, f"{where}: part {ref} fields_at.{k}", problems)
                 for k, v in fields_at.items()}
    opt = {k: (None if d.get(k) is None else str(d[k])) for k in ("value", "footprint", "lcsc")}
    return PartSrc(ref=ref, symbol=d["symbol"],
                   at=_number_pair(d.get("at"), f"{where}: part {ref} at", problems),
                   rot=rot, mirror=mirror, stub=float(stub), pin_stubs=pin_stubs, dnp=dnp,
                   fields={str(k): str(v) for k, v in fields.items()}, pins=pins,
                   fields_at=fields_at, **opt)


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
    if "origin" in board:
        _number_pair(board["origin"], "layout.yaml: board origin", problems)
    if "thickness" in board and not _is_num(board["thickness"]):
        problems.append("layout.yaml: board thickness must be a number (mm)")


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def placement_entry(value) -> tuple[float, float, float, object]:
    """(x, y, rotation, reference option) of a layout.yaml `placement` value, which is either
    `[x, y]` / `[x, y, rot]` or a mapping `{at: [x, y, rot], ref: ...}`. The reference option
    is None (the library's position), "hide", or (dx, dy, angle): the reference text centre
    `dx, dy` mm from the part's origin in board axes (X right, Y down), upright at `angle`."""
    at, ref = (value.get("at"), value.get("ref")) if isinstance(value, dict) else (value, None)
    x, y, *r = at
    if isinstance(ref, list):
        ref = (float(ref[0]), float(ref[1]), float(ref[2]) if len(ref) > 2 else 0.0)
    return float(x), float(y), float(r[0]) if r else 0.0, ref


def _check_placement(placement, refs: set[str], problems: list[str]) -> None:
    if not isinstance(placement, dict):
        problems.append("layout.yaml: `placement` must be a mapping REF: [x, y, rotation]")
        return
    for ref, value in placement.items():
        where = f"layout.yaml: placement {ref}"
        if str(ref) not in refs:
            problems.append(f"{where}: no part {ref} in the schematic sheets")
        at, opt = value, None
        if isinstance(value, dict):
            _unknown(value, _PLACEMENT_KEYS, where, problems)
            at, opt = value.get("at"), value.get("ref")
        if not (isinstance(at, list) and len(at) in (2, 3) and all(_is_num(v) for v in at)):
            problems.append(f"{where}: expected [x, y] or [x, y, rotation] in mm / degrees, "
                            f"got {at!r}")
        if opt is not None and opt != "hide" and not (
                isinstance(opt, list) and len(opt) in (2, 3) and all(_is_num(v) for v in opt)):
            problems.append(f"{where}: ref must be `hide`, [dx, dy] or [dx, dy, angle], got {opt!r}")


def _check_layout(layout: dict, refs: set[str], problems: list[str]) -> None:
    """Nested layout.yaml keys and value types (a typo would otherwise be silently ignored)."""
    _unknown(layout, _LAYOUT_KEYS, "layout.yaml", problems)
    if "board" in layout:
        _check_board(layout["board"], problems)
    rules = layout.get("rules") or {}
    if not isinstance(rules, dict):
        problems.append("layout.yaml: `rules` must be a mapping")
        rules = {}
    _unknown(rules, _RULE_KEYS | _RULE_FLAGS, "layout.yaml: rules", problems)
    for k, v in rules.items():
        if k in _RULE_KEYS and not _is_num(v) or k in _RULE_FLAGS and not isinstance(v, bool):
            problems.append(f"layout.yaml: rules.{k} must be a "
                            f"{'number (mm)' if k in _RULE_KEYS else 'boolean'}, got {v!r}")
    classes = layout.get("netclasses") or {}
    if not isinstance(classes, dict):
        problems.append("layout.yaml: `netclasses` must be a mapping")
        classes = {}
    for name, spec in classes.items():
        where = f"layout.yaml: netclasses.{name}"
        if not isinstance(spec, dict):
            problems.append(f"{where} must be a mapping")
            continue
        _unknown(spec, _NETCLASS_KEYS, where, problems)
        for k, v in spec.items():
            if k == "nets":
                if name == "Default":
                    problems.append(f"{where}: the Default class takes every other net; "
                                    "it has no `nets`")
                elif not (isinstance(v, list) and all(isinstance(n, str) for n in v)):
                    problems.append(f"{where}.nets must be a list of net names or patterns")
            elif k in _NETCLASS_KEYS and not _is_num(v):
                problems.append(f"{where}.{k} must be a number (mm), got {v!r}")
    sev = layout.get("drc_severities") or {}
    if not isinstance(sev, dict):
        problems.append("layout.yaml: `drc_severities` must be a mapping")
        sev = {}
    for k, v in sev.items():
        if v not in _SEVERITIES:
            problems.append(f"layout.yaml: drc_severities.{k} must be one of "
                            f"{', '.join(sorted(_SEVERITIES))}, got {v!r}")
    if not isinstance(layout.get("custom_rules") or "", str):
        problems.append("layout.yaml: `custom_rules` must be text (KiCad rule syntax)")
    if "placement" in layout:
        _check_placement(layout["placement"] or {}, refs, problems)


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


def _interface(path: Path, problems: list[str]) -> dict:
    """The parts of the interface contract the generator uses: `signals` (net -> GPIO<n>) and
    `connectors` (interface key -> net per pin, in pin order)."""
    data = _load_yaml(path, problems)
    where = path.name
    signals = data.get("signals") or {}
    connectors = data.get("connectors") or {}
    if not isinstance(signals, dict) or not isinstance(connectors, dict):
        problems.append(f"{where}: `signals` and `connectors` must be mappings")
        return {"signals": {}, "connectors": {}}
    for name, gpio in signals.items():
        _net(name, f"{where}: signals.{name}", problems)
        if not (isinstance(gpio, str) and _GPIO_RE.fullmatch(gpio)):
            problems.append(f"{where}: signals.{name} must be GPIO<n>, got {gpio!r}")
    for key, nets in connectors.items():
        if not isinstance(nets, list):
            problems.append(f"{where}: connectors.{key} must be a list of nets in pin order")
            continue
        for i, n in enumerate(nets, 1):
            _net(n, f"{where}: connectors.{key} pin {i}", problems)
    return {"signals": {str(k): str(v) for k, v in signals.items()},
            "connectors": {str(k): list(v) for k, v in connectors.items() if isinstance(v, list)}}


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
    _check_layout(layout, set(refs), problems)
    interface = _interface(src_dir / proj["interface"], problems) if proj.get("interface") else None
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
        layout=layout, src_dir=src_dir.resolve(), interface=interface)
