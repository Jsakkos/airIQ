"""Generate or update a board's .kicad_pcb (pure Python).

Inputs: the netlist KiCad exports from the generated schematic (`kicad-cli sch export netlist
--format kicadsexpr`), the `layout.yaml` part of the design source, the footprint libraries and
the current .kicad_pcb, if any. Working from KiCad's own netlist, as KiCad's "Update PCB from
Schematic" does, makes every pad net, value, field and schematic link (footprint `path`) match
what KiCad derives from the schematic, so DRC's schematic-parity check holds by construction.

Regeneration contract (hardware/README.md, "Toolchain"):
- owned, rebuilt on every run: the footprints (fresh from the library, placed from
  layout.yaml), the Edge.Cuts outline and cutouts of layout.yaml (recognised on the old board by
  their UUIDs, see edge_uid), the title block and page setup;
- kept from the existing board: everything else, namely tracks, arcs, vias, zones (ground
  pours, keep-outs), other drawings and text, and Edge.Cuts items drawn by hand (reported, so
  they move into layout.yaml). Routing therefore survives a re-run; tracks of a net that a
  schematic change removed show up as DRC errors to fix.
A footprint without a placement entry keeps its position on the existing board, else it is
parked beside the outline (reported, so it gets a placement entry): parked footprints are packed
in rows to the right of the outline by their courtyards, so they never overlap each other.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from gen_sch import num, uid
from kicad_lib import Libraries
from sexpr import QStr, atom, child, children, dumps, parse

PCB_VERSION = "20260206"  # what KiCad 10.0 writes
_KEPT = {"segment", "arc", "via", "zone", "gr_line", "gr_rect", "gr_circle", "gr_arc", "gr_poly",
         "gr_curve", "gr_text", "gr_text_box", "dimension", "target", "image", "group",
         "generated", "table", "barcode", "point"}
_FP_GRAPHICS = {"fp_line", "fp_rect", "fp_circle", "fp_arc", "fp_poly", "fp_curve", "fp_text",
                "fp_text_box", "image"}
_FP_DROP = {"version", "generator", "generator_version", "uuid", "at", "path", "sheetname",
            "sheetfile"}
_FP_UNSUPPORTED = {"zone", "group", "dimension"}
_LAYERS = [
    ["0", QStr("F.Cu"), "signal"], ["2", QStr("B.Cu"), "signal"],
    ["9", QStr("F.Adhes"), "user", QStr("F.Adhesive")], ["11", QStr("B.Adhes"), "user", QStr("B.Adhesive")],
    ["13", QStr("F.Paste"), "user"], ["15", QStr("B.Paste"), "user"],
    ["5", QStr("F.SilkS"), "user", QStr("F.Silkscreen")], ["7", QStr("B.SilkS"), "user", QStr("B.Silkscreen")],
    ["1", QStr("F.Mask"), "user"], ["3", QStr("B.Mask"), "user"],
    ["17", QStr("Dwgs.User"), "user", QStr("User.Drawings")], ["19", QStr("Cmts.User"), "user", QStr("User.Comments")],
    ["21", QStr("Eco1.User"), "user", QStr("User.Eco1")], ["23", QStr("Eco2.User"), "user", QStr("User.Eco2")],
    ["25", QStr("Edge.Cuts"), "user"], ["27", QStr("Margin"), "user"],
    ["31", QStr("F.CrtYd"), "user", QStr("F.Courtyard")], ["29", QStr("B.CrtYd"), "user", QStr("B.Courtyard")],
    ["35", QStr("F.Fab"), "user"], ["33", QStr("B.Fab"), "user"],
]


@dataclass
class Comp:
    """One schematic component, from the netlist."""
    ref: str
    value: str
    footprint: str
    path: str                  # /<sheet uuid>/.../<symbol uuid>: the footprint's schematic link
    sheetname: str
    sheetfile: str
    fields: dict[str, str] = field(default_factory=dict)
    dnp: bool = False
    exclude_from_bom: bool = False
    pins: dict[str, tuple[str, str, str]] = field(default_factory=dict)  # pin -> net, function, type


def read_netlist(text: str) -> list[Comp]:
    tree = parse(text)
    comps: dict[str, Comp] = {}
    for c in children(child(tree, "components") or [], "comp"):
        sp = child(c, "sheetpath")
        props = {atom(p, "name"): atom(p, "value", "") for p in children(c, "property")}
        fields = {}
        for f in children(child(c, "fields") or [], "field"):
            name = atom(f, "name")
            if name not in ("Footprint",):
                fields[name] = f[2] if len(f) > 2 and isinstance(f[2], str) else ""
        comps[atom(c, "ref")] = Comp(
            ref=atom(c, "ref"), value=atom(c, "value", ""), footprint=atom(c, "footprint", ""),
            path=atom(sp, "tstamps") + atom(c, "tstamps"), sheetname=atom(sp, "names"),
            sheetfile=props.get("Sheetfile", ""), fields=fields, dnp="dnp" in props,
            exclude_from_bom="exclude_from_bom" in props)
    for net in children(child(tree, "nets") or [], "net"):
        name = atom(net, "name")
        for node in children(net, "node"):
            comp = comps.get(atom(node, "ref"))
            if comp is not None:
                comp.pins[atom(node, "pin")] = (name, atom(node, "pinfunction", ""),
                                                atom(node, "pintype", ""))
    return list(comps.values())


def _rotated_at(at: list, rot: float) -> list:
    """`(at x y [a])` of a footprint child: KiCad stores pad and text angles board-absolute."""
    angle = (float(at[3]) if len(at) > 3 and _is_number(at[3]) else 0.0) + rot
    angle = angle % 360
    tail = [a for a in at[3:] if not _is_number(a)]  # e.g. `unlocked`
    return ["at", at[1], at[2], *([num(angle, 6)] if angle else []), *tail]


def _is_number(a) -> bool:
    try:
        float(a)
        return not isinstance(a, QStr)
    except (TypeError, ValueError):
        return False


def _property(name: str, value: str, rot: float, key: str, src: list | None) -> list:
    """A footprint property: the library's (with its position and look) or a new hidden one."""
    if src is not None:
        rest = [c for c in src[3:] if isinstance(c, list) and c[0] not in ("at", "uuid")]
        return ["property", QStr(name), QStr(value), _rotated_at(child(src, "at"), rot), *rest,
                ["uuid", key]]
    return ["property", QStr(name), QStr(value), ["at", "0", "0", *([num(rot, 6)] if rot else [])],
            ["layer", QStr("F.Fab")], ["hide", "yes"], ["uuid", key],
            ["effects", ["font", ["size", "1", "1"], ["thickness", "0.15"]]]]


def footprint_node(project: str, comp: Comp, lib_fp: list, x: float, y: float, rot: float) -> list:
    """Board instance of library footprint `lib_fp` for `comp`, at page position (x, y)."""
    ref = comp.ref
    k = 0

    def key() -> QStr:
        nonlocal k
        k += 1
        return uid(project, "fp", ref, str(k))

    node = ["footprint", QStr(comp.footprint), ["layer", QStr("F.Cu")],
            ["uuid", uid(project, "fp", ref)],
            ["at", num(x, 6), num(y, 6), *([num(rot % 360, 6)] if rot % 360 else [])]]
    values = {"Reference": ref, "Value": comp.value, **comp.fields}
    lib_props = {str(p[1]): p for p in children(lib_fp, "property")}
    props = []
    for name, p in lib_props.items():
        props.append(_property(name, values.pop(name, str(p[2])), rot, key(), p))
    for name, value in values.items():
        props.append(_property(name, value, rot, key(), None))
    head_done = False
    for item in lib_fp[2:]:
        if not isinstance(item, list) or item[0] in _FP_DROP:
            continue
        tag = item[0]
        if tag in _FP_UNSUPPORTED:
            raise ValueError(f"footprint {comp.footprint} ({ref}): `{tag}` items are not supported")
        if tag == "property":
            continue
        if not head_done and tag not in ("layer", "descr", "tags"):
            node += props
            node += [["path", QStr(comp.path)], ["sheetname", QStr(comp.sheetname)],
                     ["sheetfile", QStr(comp.sheetfile)]]
            head_done = True
        if tag == "layer":
            if str(item[1]) != "F.Cu":
                raise ValueError(f"footprint {comp.footprint}: only F.Cu footprints are supported")
            continue
        if tag == "attr":
            flags = [a for a in item[1:] if a not in ("dnp", "exclude_from_bom")]
            node.append(["attr", *flags, *(["exclude_from_bom"] if comp.exclude_from_bom else []),
                         *(["dnp"] if comp.dnp else [])])
        elif tag == "pad":
            node.append(_pad(item, comp, rot, key()))
        elif tag in _FP_GRAPHICS:
            g = [c for c in item if not (isinstance(c, list) and c[0] == "uuid")]
            if child(g, "at") is not None:
                g = [(_rotated_at(c, rot) if isinstance(c, list) and c[0] == "at" else c) for c in g]
            node.append([*g, ["uuid", key()]])
        else:
            node.append(item)
    if not head_done:
        node += props + [["path", QStr(comp.path)], ["sheetname", QStr(comp.sheetname)],
                         ["sheetfile", QStr(comp.sheetfile)]]
    return node


def _pad(pad: list, comp: Comp, rot: float, key: QStr) -> list:
    out = []
    for c in pad:
        if isinstance(c, list) and c[0] in ("uuid", "net", "pinfunction", "pintype"):
            continue
        out.append(_rotated_at(c, rot) if isinstance(c, list) and c[0] == "at" else c)
    pin = comp.pins.get(str(pad[1]))
    if pin is not None:
        net, func, ptype = pin
        out.append(["net", QStr(net)])
        if func:
            out.append(["pinfunction", QStr(func)])
        if ptype:
            out.append(["pintype", QStr(ptype)])
    out.append(["uuid", key])
    return out


def _title_block(title: str, rev: str, company: str, source: str) -> list:
    tb = ["title_block", ["title", QStr(title)]]
    if rev:
        tb.append(["rev", QStr(rev)])
    if company:
        tb.append(["company", QStr(company)])
    tb.append(["comment", "1", QStr(f"Generated from {source} by tools/hw/build.py: footprints "
                                    "and outline come from the source, routing is kept")])
    return tb


MAX_EDGE_ITEMS = 256  # generated Edge.Cuts items: the outline plus at most 255 cutouts


def edge_uid(project: str, i: int) -> QStr:
    """UUID of the i-th generated Edge.Cuts item (0 = the outline, then the cutouts)."""
    return uid(project, "outline") if i == 0 else uid(project, "outline", str(i))


@dataclass
class Board:
    text: str
    unplaced: list[str]      # references without a placement entry
    hand_edges: list[str]    # UUIDs of kept Edge.Cuts items that layout.yaml did not generate


def _existing(project: str, existing: str | None) -> tuple[list[list], dict, list[str]]:
    """Items to keep from the current board, footprint positions by reference, and the UUIDs of
    kept Edge.Cuts items drawn by hand (the generated ones are recognised by edge_uid)."""
    if not existing:
        return [], {}, []
    generated = {edge_uid(project, i) for i in range(MAX_EDGE_ITEMS)}
    tree = parse(existing)
    kept, pos, hand = [], {}, []
    for item in tree[1:]:
        if not isinstance(item, list):
            continue
        if item[0] == "footprint":
            ref = next((str(p[2]) for p in children(item, "property") if p[1] == "Reference"), None)
            at = child(item, "at")
            if ref and at:
                pos[ref] = (float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0)
        elif item[0] in _KEPT:
            if item[0].startswith("gr_") and atom(item, "layer") == "Edge.Cuts":
                if atom(item, "uuid") in generated:
                    continue  # rebuilt from layout.yaml
                hand.append(str(atom(item, "uuid")))
            kept.append(item)
    return kept, pos, hand


def _poly(points: list, ox: float, oy: float, key: QStr) -> list:
    return ["gr_poly", ["pts", *[["xy", num(ox + float(x), 6), num(oy + float(y), 6)]
                                 for x, y in points]],
            ["stroke", ["width", "0.05"], ["type", "default"]], ["fill", "no"],
            ["layer", QStr("Edge.Cuts")], ["uuid", key]]


def outline_items(project: str, board: dict) -> tuple[list[list], tuple[float, float, float, float]]:
    """Generated Edge.Cuts items (outline, then cutouts) and the outline's bounding box
    (min x, min y, max x, max y, relative to the board origin)."""
    ox, oy = (float(v) for v in board.get("origin", (100, 100)))
    if "outline" in board:
        pts = [(float(x), float(y)) for x, y in board["outline"]]
        items = [_poly(pts, ox, oy, edge_uid(project, 0))]
        box = (min(x for x, _ in pts), min(y for _, y in pts),
               max(x for x, _ in pts), max(y for _, y in pts))
    else:
        w, h = float(board["width"]), float(board["height"])
        items = [["gr_rect", ["start", num(ox, 6), num(oy, 6)], ["end", num(ox + w, 6), num(oy + h, 6)],
                  ["stroke", ["width", "0.05"], ["type", "default"]], ["fill", "no"],
                  ["layer", QStr("Edge.Cuts")], ["uuid", edge_uid(project, 0)]]]
        box = (0.0, 0.0, w, h)
    cutouts = board.get("cutouts") or []
    if len(cutouts) >= MAX_EDGE_ITEMS:
        raise ValueError(f"at most {MAX_EDGE_ITEMS - 1} cutouts")
    items += [_poly(c, ox, oy, edge_uid(project, i)) for i, c in enumerate(cutouts, 1)]
    return items, box


PARK_GAP = 2.0     # mm between the courtyards of parked footprints
PARK_ROW = 100.0   # mm: parked footprints start a new row past this width


def footprint_bbox(fp: list) -> tuple[float, float, float, float]:
    """(min x, min y, max x, max y) of a library footprint at rotation 0: its F.CrtYd drawing
    and its pads (some EasyEDA courtyards follow the body and leave the pads out)."""
    pts: list[tuple[float, float]] = []
    for g in fp[2:]:
        if not (isinstance(g, list) and g[0] in _FP_GRAPHICS and atom(g, "layer") == "F.CrtYd"):
            continue
        for tag in ("start", "mid", "end", "center"):
            c = child(g, tag)
            if c is not None:
                pts.append((float(c[1]), float(c[2])))
        if child(g, "pts") is not None:
            pts += [(float(xy[1]), float(xy[2])) for xy in children(child(g, "pts"), "xy")]
        if g[0] == "fp_circle":
            (cx, cy), (ex, ey) = ((float(child(g, t)[1]), float(child(g, t)[2]))
                                  for t in ("center", "end"))
            r = math.hypot(ex - cx, ey - cy)
            pts += [(cx - r, cy - r), (cx + r, cy + r)]
    for pad in children(fp, "pad"):
        at, size = child(pad, "at"), child(pad, "size")
        r = math.hypot(float(size[1]), float(size[2])) / 2   # any pad rotation
        pts += [(float(at[1]) - r, float(at[2]) - r), (float(at[1]) + r, float(at[2]) + r)]
    if not pts:
        return 0.0, 0.0, 0.0, 0.0
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    return min(xs), min(ys), max(xs), max(ys)


def generate_board(project: str, title: str, rev: str, company: str, source: str,
                   comps: list[Comp], layout: dict, libs: Libraries,
                   existing: str | None) -> Board:
    """The .kicad_pcb text, plus what the caller should report."""
    board = layout.get("board") or {}
    ox, oy = (float(v) for v in board.get("origin", (100, 100)))
    edges, (x0, _, x1, y1) = outline_items(project, board)
    placement = layout.get("placement") or {}
    kept, old_pos, hand_edges = _existing(project, existing)
    unplaced = []
    fps = []
    park_x = park_y = row_h = 0.0   # packing cursor, relative to (outline right + 10, top)
    for comp in sorted(comps, key=lambda c: _natural(c.ref)):
        lib_fp = libs.footprint(comp.footprint)
        if comp.ref in placement:
            px, py, *r = placement[comp.ref]
            x, y, rot = ox + float(px), oy + float(py), float(r[0]) if r else 0.0
        elif comp.ref in old_pos:
            x, y, rot = old_pos[comp.ref]
            unplaced.append(comp.ref)
        else:
            bx0, by0, bx1, by1 = footprint_bbox(lib_fp)
            if park_x > 0 and park_x + (bx1 - bx0) > PARK_ROW:
                park_x, park_y, row_h = 0.0, park_y + row_h + PARK_GAP, 0.0
            x, y, rot = ox + x1 + 10 + park_x - bx0, oy + park_y - by0, 0.0
            park_x += bx1 - bx0 + PARK_GAP
            row_h = max(row_h, by1 - by0)
            unplaced.append(comp.ref)
        fps.append(footprint_node(project, comp, lib_fp, x, y, rot))
    node = ["kicad_pcb", ["version", PCB_VERSION], ["generator", QStr("pcbnew")],
            ["generator_version", QStr("10.0")],
            ["general", ["thickness", num(float(board.get("thickness", 1.6)))],
             ["legacy_teardrops", "no"]],
            ["paper", QStr("A4")], _title_block(title, rev, company, source),
            ["layers", *_LAYERS],
            ["setup", ["pad_to_mask_clearance", "0"],
             ["allow_soldermask_bridges_in_footprints", "no"],
             ["aux_axis_origin", num(ox + x0, 6), num(oy + y1, 6)],
             ["grid_origin", num(ox, 6), num(oy, 6)]],
            *fps, *edges, *kept, ["embedded_fonts", "no"]]
    return Board(dumps(node) + "\n", unplaced, hand_edges)


def _natural(ref: str) -> tuple:
    head = ref.rstrip("0123456789")
    tail = ref[len(head):]
    return head, int(tail) if tail else -1
