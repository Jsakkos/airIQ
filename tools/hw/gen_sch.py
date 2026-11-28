"""Generate a board's KiCad 10 schematic files from its design source (pure Python).

`generate_schematics(design, libs)` returns {file name: text}: the root sheet
`<project>.kicad_sch`, holding one sheet symbol per source sheet, and one `<sheet>.kicad_sch` each.

Drawing style: no wires. Every pin ends in what names its net, placed exactly on the pin's
connection point and pointing away from the symbol body:
- a power symbol for nets listed in `power_symbols` (GND, +3V3, ...);
- a global label for a net used on more than one sheet, a local label otherwise;
- a no-connect flag for `NC`.
So one net name means one net across the whole board, and every connection can be read off the
source. UUIDs are uuid5 of stable names (project, reference, pin), so the output is
byte-identical for the same input.

Where a part's nets come from (resolve_design):
- its `pins` in the sheet: keyed by pin number, or by pin name (a name covers every pin that
  carries it, e.g. `GND: GND` for all of a module's ground pins), or a list for pins 1..n;
- for a part with a `Role` field, when project.yaml names the interface contract
  (hardware/interface.yaml): `connectors.<Role>` gives pins 1..n of that connector, and for
  Role `MCU`, `signals` gives the pin named IO<n>/GPIO<n> of each signal's GPIO. Those pins
  must not be repeated in the sheet, so pinouts are written once, in interface.yaml.
Stacked pins (pins of one part on the same point, as KiCad draws a module's ground pins) must
share a net; they get one marker.
"""
from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass

from design import NC, PAPERS, Design, DesignError, PartSrc, SheetSrc
from kicad_lib import Libraries, Pin, embedded_symbol, is_power_symbol, symbol_pins, symbol_property
from sexpr import QStr, child, children, dumps

SCH_VERSION = "20260306"  # what KiCad 10.0 writes
GRID = 1.27
_NS = uuid.UUID("0c6d1c52-5f43-4b0e-9a63-2b1f0f6a7e10")
_FONT = ["font", ["size", "1.27", "1.27"]]
SHOWN_FIELDS = {"Role"}   # extra fields drawn on the sheet (the others are hidden)


def uid(*parts: str) -> QStr:
    return QStr(str(uuid.uuid5(_NS, "/".join(parts))))


def num(v: float, digits: int = 4) -> str:
    s = f"{round(v, digits):.{digits}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ---- geometry: library coordinates are Y up, the schematic page is Y down ---------------------

def _mirror(x: float, y: float, mirror: str | None) -> tuple[float, float]:
    if mirror == "x":
        return x, -y
    if mirror == "y":
        return -x, y
    return x, y


def _rotate(x: float, y: float, rot: int) -> tuple[float, float]:
    """Counter-clockwise by `rot` degrees (Y up)."""
    c, s = round(math.cos(math.radians(rot))), round(math.sin(math.radians(rot)))
    return x * c - y * s, x * s + y * c


def to_sheet(px: float, py: float, at: tuple[float, float], rot: int,
             mirror: str | None) -> tuple[float, float]:
    """Page position of library point (px, py) of a symbol placed at `at` with rot/mirror.

    KiCad rotates the library drawing first, then mirrors the rotated drawing on the page
    (`mirror x` flips it top to bottom, `mirror y` left to right); checked against kicad-cli
    netlists for all 12 combinations (tests/hardware/test_kicad_pipeline.py).
    """
    x, y = _mirror(*_rotate(px, py, rot), mirror)
    return round(at[0] + x, 4), round(at[1] - y, 4)


def to_sheet_angle(angle: int, rot: int, mirror: str | None) -> int:
    """Direction `angle` (degrees CCW, Y up) of the library drawing, after rot/mirror."""
    x, y = _mirror(*_rotate(*_rotate(1, 0, angle), rot), mirror)
    return int(round(math.degrees(math.atan2(y, x)))) % 360


def pin_end(pin: Pin, part: PartSrc) -> tuple[float, float]:
    return to_sheet(pin.x, pin.y, part.at, part.rot, part.mirror)


def pin_outward(pin: Pin, part: PartSrc) -> int:
    """Direction pointing away from the body at the pin's connection point (0/90/180/270)."""
    return to_sheet_angle((pin.angle + 180) % 360, part.rot, part.mirror)


def pin_stub(pin: Pin, part: PartSrc) -> float:
    """The wire length out of `pin`: its own `stub` entry (by number, then name), else the part's."""
    return part.pin_stubs.get(pin.number, part.pin_stubs.get(pin.name, part.stub))


def label_point(pin: Pin, part: PartSrc) -> tuple[float, float]:
    """Where the pin's label or power symbol goes: its stub length out from its connection point."""
    x, y = pin_end(pin, part)
    a = math.radians(pin_outward(pin, part))
    s = pin_stub(pin, part)
    return round(x + s * round(math.cos(a)), 4), round(y - s * round(math.sin(a)), 4)


def _on_grid(v: float) -> bool:
    return abs(v / GRID - round(v / GRID)) < 1e-6


# ---- resolved parts ---------------------------------------------------------------------------

@dataclass
class Placed:
    sheet: SheetSrc
    src: PartSrc
    sym: list
    pins: list[Pin]
    nets: dict[str, str]   # pin number -> net name or NC
    power: bool            # a virtual power symbol (PWR_FLAG ...): no footprint, no BOM line


_GPIO_PIN = re.compile(r"(?:gp)?io(\d+)", re.IGNORECASE)   # as tools/hw/check_netlist.py


def _pin_nets(where: str, p: PartSrc, pins: list[Pin], interface: dict | None,
              problems: list[str]) -> dict[str, str] | None:
    """Pin number -> net for part `p`, from its sheet `pins` and, by Role, the interface."""
    numbers = list(dict.fromkeys(pin.number for pin in pins))
    by_name: dict[str, list[str]] = {}
    for pin in pins:
        if pin.number not in by_name.setdefault(pin.name, []):
            by_name[pin.name].append(pin.number)
    nets: dict[str, str] = {}
    source: dict[str, str] = {}

    def assign(number: str, net: str, what: str) -> None:
        if number in nets:
            problems.append(f"{where}: pin {number} gets a net from both {source[number]} and "
                            f"{what}: give it once")
            return
        nets[number], source[number] = net, what

    if isinstance(p.pins, list):
        if p.pins and numbers != [str(i) for i in range(1, len(numbers) + 1)]:
            problems.append(f"{where}: pins given as a list, but {p.symbol} pins are not "
                            f"numbered 1..n ({', '.join(numbers)}): use a mapping")
            return None
        for i, net in enumerate(p.pins, 1):
            if str(i) not in numbers:
                problems.append(f"{where}: {p.symbol} has no pin {i}")
                continue
            assign(str(i), net, "the sheet")
    else:
        for key, net in p.pins.items():
            named = by_name.get(key, [])
            if key in numbers and named and named != [key]:
                problems.append(f"{where}: pin key {key} is ambiguous: pin number {key} and the "
                                f"name of pin(s) {', '.join(named)}; use the pin number")
                continue
            targets = [key] if key in numbers else named
            if not targets:
                problems.append(f"{where}: {p.symbol} has no pin {key}")
            for n in targets:
                assign(n, net, f"the sheet ({key})" if key != n else "the sheet")
    role = p.fields.get("Role")
    if role and interface is not None:
        if role == "MCU":
            for signal, gpio in interface["signals"].items():
                n = int(gpio[len("GPIO"):])
                found = [pin.number for pin in pins
                         if (m := _GPIO_PIN.fullmatch(pin.name)) and int(m.group(1)) == n]
                if not found:
                    problems.append(f"{where}: {p.symbol} has no pin IO{n} for signal {signal} "
                                    "(interface.yaml signals)")
                for number in dict.fromkeys(found):
                    assign(number, signal, f"interface.yaml signals.{signal}")
        elif role in interface["connectors"]:
            for i, net in enumerate(interface["connectors"][role], 1):
                if str(i) not in numbers:
                    problems.append(f"{where}: {p.symbol} has no pin {i} for connectors.{role} "
                                    "(interface.yaml)")
                    continue
                assign(str(i), net, f"interface.yaml connectors.{role}")
        else:
            problems.append(f"{where}: Role {role} is neither MCU nor a connector in "
                            "interface.yaml")
    for n in sorted(set(numbers) - set(nets)):
        problems.append(f"{where}: pin {n} of {p.symbol} has no net (write NC if unused)")
    return nets


def _resolve(sheet: SheetSrc, p: PartSrc, libs: Libraries, interface: dict | None,
             problems: list[str]) -> Placed | None:
    where = f"{sheet.source.name}: {p.ref}"
    try:
        sym = libs.symbol(p.symbol)
        pins = symbol_pins(sym)
    except (KeyError, ValueError, OSError) as e:
        problems.append(f"{where}: {e}")
        return None
    nets = _pin_nets(where, p, pins, interface, problems)
    if nets is None:
        return None
    known = {str(prop[1]) for prop in children(sym, "property")} | set(p.fields) | {"LCSC"}
    for name in sorted(set(p.fields_at) - known):
        problems.append(f"{where}: fields_at.{name}: the part has no field {name}")
    pin_keys = {pin.number for pin in pins} | {pin.name for pin in pins}
    for key in sorted(set(p.pin_stubs) - pin_keys):
        problems.append(f"{where}: stub.{key}: {p.symbol} has no pin {key}")
    power = is_power_symbol(sym)
    if power and not p.ref.startswith("#"):
        problems.append(f"{where}: power symbol references must start with '#'")
    if not power and p.ref.startswith("#"):
        problems.append(f"{where}: only power symbols may have a '#' reference")
    if not power:
        footprint = p.footprint or symbol_property(sym, "Footprint")
        if not footprint:
            problems.append(f"{where}: no footprint (set `footprint:`)")
        else:  # a misspelt footprint is reported here, not as a crash in gen_pcb
            try:
                libs.footprint(footprint)
            except (KeyError, ValueError, OSError) as e:
                problems.append(f"{where}: {e}")
    return Placed(sheet, p, sym, pins, nets, power)


def resolve_design(design: Design, libs: Libraries) -> list[Placed]:
    """All parts with their library symbols; raise DesignError listing every problem."""
    problems: list[str] = []
    placed = [r for s in design.sheets for p in s.parts
              if (r := _resolve(s, p, libs, design.interface, problems)) is not None]
    for lib_id in design.power_symbols.values():
        try:
            libs.symbol(lib_id)
        except (KeyError, ValueError, OSError) as e:
            problems.append(f"project.yaml power_symbols: {e}")
    for s in design.sheets:
        seen: dict[tuple[float, float], tuple[str, str, str | None]] = {}  # point -> who, ref, net
        for pl in (x for x in placed if x.sheet is s):
            for pin in pl.pins:
                who = f"{pl.src.ref} pin {pin.number}"
                net = pl.nets.get(pin.number)
                for end in dict.fromkeys((pin_end(pin, pl.src), label_point(pin, pl.src))):
                    if not (_on_grid(end[0]) and _on_grid(end[1])):
                        problems.append(f"{s.source.name}: {who} ends off the 1.27 mm grid at "
                                        f"{end}: move the part or change its stub")
                    other = seen.get(end)
                    stacked = other is not None and other[1:] == (pl.src.ref, net)
                    if other is not None and other[0] != who and not stacked:
                        problems.append(f"{s.source.name}: {who} and {other[0]} meet at {end}: "
                                        "move one part, they would be connected")
                    seen.setdefault(end, (who, pl.src.ref, net))
    if problems:
        raise DesignError(problems)
    return placed


# ---- schematic items --------------------------------------------------------------------------

def _effects(justify: list[str] | None = None, hide: bool = False) -> list:
    e = ["effects", _FONT]
    if justify:
        e.append(["justify", *justify])
    if hide:
        e.append(["hide", "yes"])
    return e


def _instances(design: Design, path: str, ref: str) -> list:
    return ["instances", ["project", QStr(design.name),
                          ["path", QStr(path), ["reference", QStr(ref)], ["unit", "1"]]]]


def _placed_fields(pl: Placed, ref: str) -> list[list]:
    """Instance properties: the library fields (moved with the symbol) with this part's values."""
    p, sym = pl.src, pl.sym
    values = {"Reference": ref}
    if p.value is not None:
        values["Value"] = p.value
    if p.footprint is not None:
        values["Footprint"] = p.footprint
    extra = dict(p.fields)
    if p.lcsc is not None:
        extra["LCSC"] = p.lcsc
    out = []
    value_at = p.at
    # field text angles are stored in the symbol's own frame: this one reads horizontally on the page
    flat = "90" if p.rot in (90, 270) else "0"
    for prop in children(sym, "property"):
        name = str(prop[1])
        if name.startswith("ki_"):
            continue
        val = values[name] if name in values else extra.pop(name, prop[2])
        at = child(prop, "at")
        x, y = to_sheet(float(at[1]), float(at[2]), p.at, p.rot, p.mirror)
        if name in p.fields_at:
            x, y = p.at[0] + p.fields_at[name][0], p.at[1] + p.fields_at[name][1]
        if name == "Value":
            value_at = (x, y)
        rest = [c for c in prop[3:] if isinstance(c, list) and c[0] not in ("at", "id")]
        angle = flat if name in p.fields_at else (at[3] if len(at) > 3 else "0")
        out.append(["property", QStr(name), QStr(val), ["at", num(x), num(y), angle], *rest])
    for name, val in extra.items():
        if name in SHOWN_FIELDS:
            # shown, so the reader can tell same-part connectors apart (J_QWIIC_TONGUE vs AUX)
            dx, dy = p.fields_at.get(name, (value_at[0] - p.at[0], value_at[1] - p.at[1] + 2.54))
            out.append(["property", QStr(name), QStr(val),
                        ["at", num(p.at[0] + dx), num(p.at[1] + dy), flat], _effects()])
            continue
        out.append(["property", QStr(name), QStr(val), ["at", num(p.at[0]), num(p.at[1]), "0"],
                    ["hide", "yes"], _effects()])
    return out


def _symbol(design: Design, path: str, pl: Placed, ref: str, key: str) -> list:
    p = pl.src
    node = ["symbol", ["lib_id", QStr(p.symbol)], ["at", num(p.at[0]), num(p.at[1]), str(p.rot)]]
    if p.mirror:
        node.append(["mirror", p.mirror])
    flags = {k: (child(pl.sym, k) or [k, "yes"])[1] for k in ("in_bom", "on_board")}
    node += [["unit", "1"], ["exclude_from_sim", "no"], ["in_bom", flags["in_bom"]],
             ["on_board", flags["on_board"]], ["dnp", "yes" if p.dnp else "no"],
             ["uuid", uid(design.name, "sym", key)]]
    node += _placed_fields(pl, ref)
    for n in dict.fromkeys(pin.number for pin in pl.pins):
        node.append(["pin", QStr(n), ["uuid", uid(design.name, "sym", key, "pin", n)]])
    node.append(_instances(design, path, ref))
    return node


def _power_symbol(design: Design, path: str, libs: Libraries, lib_id: str, ref: str,
                  end: tuple[float, float], outward: int, key: str) -> list:
    """Power symbol `lib_id` with its pin on `end`, its body pointing `outward`."""
    sym = libs.symbol(lib_id)
    (pin,) = symbol_pins(sym)
    rot = (outward - pin.angle) % 360
    src = PartSrc(ref=ref, symbol=lib_id, at=end, rot=rot)
    node = _symbol(design, path, Placed(None, src, sym, [pin], {}, True), ref, key)
    if rot in (90, 270):
        # Keep the net name horizontal beside a sideways symbol: field angles and justification
        # are stored in the symbol's own frame, so "vertical" there reads horizontal on the
        # page, and the text is justified to run from the field anchor along the symbol body.
        value = next(p for p in children(node, "property") if p[1] == "Value")
        child(value, "at")[3] = "90"
        effects = child(value, "effects")
        effects[:] = [e for e in effects if not (isinstance(e, list) and e[0] == "justify")]
        effects.append(["justify", "left" if pin.angle == 90 else "right"])
    return node


_LABEL_JUSTIFY = {0: ["left", "bottom"], 90: ["left", "bottom"],
                  180: ["right", "bottom"], 270: ["right", "bottom"]}
_GLOBAL_JUSTIFY = {0: ["left"], 90: ["left"], 180: ["right"], 270: ["right"]}


def _label(net: str, end, outward: int, is_global: bool, key: str, design: Design) -> list:
    at = ["at", num(end[0]), num(end[1]), str(outward)]
    if not is_global:
        return ["label", QStr(net), at, _effects(_LABEL_JUSTIFY[outward]),
                ["uuid", uid(design.name, "label", key)]]
    return ["global_label", QStr(net), ["shape", "passive"], at, ["fields_autoplaced", "yes"],
            _effects(_GLOBAL_JUSTIFY[outward]), ["uuid", uid(design.name, "label", key)],
            ["property", QStr("Intersheetrefs"), QStr("${INTERSHEET_REFS}"),
             ["at", num(end[0]), num(end[1]), "0"], _effects(_GLOBAL_JUSTIFY[outward], hide=True)]]


def _title_block(design: Design, title: str, source: str) -> list:
    tb = ["title_block", ["title", QStr(title)]]
    if design.rev:
        tb.append(["rev", QStr(design.rev)])
    if design.company:
        tb.append(["company", QStr(design.company)])
    tb.append(["comment", "1", QStr(f"Generated from {source} by tools/hw/build.py: "
                                    "edit the source, not this file")])
    return tb


def _file(uuid_: QStr, paper: str, title_block: list, lib_symbols: list, items: list,
          root: bool) -> str:
    node = ["kicad_sch", ["version", SCH_VERSION], ["generator", QStr("eeschema")],
            ["generator_version", QStr("10.0")], ["uuid", uuid_], ["paper", QStr(paper)],
            title_block, ["lib_symbols", *lib_symbols], *items]
    if root:
        node.append(["sheet_instances", ["path", QStr("/"), ["page", QStr("1")]]])
    node.append(["embedded_fonts", "no"])
    return dumps(node) + "\n"


def generate_schematics(design: Design, libs: Libraries) -> dict[str, str]:
    """{file name: text} for the root sheet and every source sheet."""
    placed = resolve_design(design, libs)
    sheets_of: dict[str, set[str]] = {}
    for pl in placed:
        for net in pl.nets.values():
            sheets_of.setdefault(net, set()).add(pl.sheet.name)
    root_uuid = uid(design.name, "root")
    files: dict[str, str] = {}
    pwr_count = 0
    root_items = []
    for page, sheet in enumerate(design.sheets, 2):
        sheet_uuid = uid(design.name, "sheet", sheet.name)
        path = f"/{root_uuid}/{sheet_uuid}"
        items, lib_ids = [], set()
        for pl in (x for x in placed if x.sheet is sheet):
            ref = pl.src.ref
            lib_ids.add(pl.src.symbol)
            items.append(_symbol(design, path, pl, ref, ref))
            marked: set[tuple[float, float]] = set()
            for pin in pl.pins:
                net, end, out = pl.nets[pin.number], pin_end(pin, pl.src), pin_outward(pin, pl.src)
                if end in marked:
                    continue  # a stacked pin: the first pin on this point carries the marker
                marked.add(end)
                key = f"{ref}/{pin.number}"
                if net == NC:
                    items.append(["no_connect", ["at", num(end[0]), num(end[1])],
                                  ["uuid", uid(design.name, "nc", key)]])
                    continue
                if pin_stub(pin, pl.src):
                    tip = label_point(pin, pl.src)
                    items.append(["wire", ["pts", ["xy", num(end[0]), num(end[1])],
                                           ["xy", num(tip[0]), num(tip[1])]],
                                  ["stroke", ["width", "0"], ["type", "default"]],
                                  ["uuid", uid(design.name, "wire", key)]])
                    end = tip
                if net in design.power_symbols:
                    pwr_count += 1
                    lib_id = design.power_symbols[net]
                    lib_ids.add(lib_id)
                    items.append(_power_symbol(design, path, libs, lib_id, f"#PWR{pwr_count:03d}",
                                               end, out, f"pwr/{key}"))
                else:
                    items.append(_label(net, end, out, len(sheets_of[net]) > 1, key, design))
        for i, note in enumerate(sheet.notes, 1):
            items.append(["text", QStr(note.text), ["exclude_from_sim", "no"],
                          ["at", num(note.at[0]), num(note.at[1]), "0"],
                          ["effects", ["font", ["size", num(note.size), num(note.size)]],
                           ["justify", "left", "bottom"]],
                          ["uuid", uid(design.name, "note", sheet.name, str(i))]])
        lib_symbols = [embedded_symbol(libs.symbol(i), i) for i in sorted(lib_ids)]
        title = f"{design.title}: {sheet.title}"
        files[f"{sheet.name}.kicad_sch"] = _file(
            uid(design.name, "sheetfile", sheet.name), sheet.paper,
            _title_block(design, title, design.rel(sheet.source)), lib_symbols, items, False)
        root_items += _sheet_symbol(design, sheet, sheet_uuid, root_uuid, page)
    root_title = _title_block(design, design.title, design.rel(design.src_dir / "project.yaml"))
    files[f"{design.name}.kicad_sch"] = _file(root_uuid, "A4", root_title, [], root_items, True)
    return files


def _sheet_symbol(design: Design, sheet: SheetSrc, sheet_uuid: QStr, root_uuid: QStr,
                  page: int) -> list[list]:
    i = page - 2
    x, y, w, h = 25.4 + (i % 4) * 63.5, 38.1 + (i // 4) * 50.8, 45.72, 25.4
    box = ["sheet", ["at", num(x), num(y)], ["size", num(w), num(h)],
           ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"],
           ["stroke", ["width", "0.1524"], ["type", "solid"]], ["fill", ["color", "0", "0", "0", "0"]],
           ["uuid", sheet_uuid],
           ["property", QStr("Sheetname"), QStr(sheet.name), ["at", num(x), num(y - 0.7116), "0"],
            _effects(["left", "bottom"])],
           ["property", QStr("Sheetfile"), QStr(f"{sheet.name}.kicad_sch"),
            ["at", num(x), num(y + h + 0.5846), "0"], _effects(["left", "top"])],
           ["instances", ["project", QStr(design.name),
                          ["path", QStr(f"/{root_uuid}"), ["page", QStr(str(page))]]]]]
    note = ["text", QStr(sheet.title), ["exclude_from_sim", "no"],
            ["at", num(x + 1.27), num(y + h / 2), "0"], _effects(["left"]),
            ["uuid", uid(design.name, "sheetnote", sheet.name)]]
    return [box, note]
