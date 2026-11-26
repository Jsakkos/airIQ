"""Sense tongue: the mechanical record, the milled slot and the SHT45's copper clearance.

Pure Python on the committed files (no KiCad needed): hardware/src/tongue/layout.yaml,
hardware/interface.yaml `mechanical.tongue` and hardware/kicad/tongue/airq-tongue.kicad_pcb.
DRC enforces most of the isolation (a rule area bans vias and pours, a custom rule bans other
parts' pads); what DRC cannot say, that every track near the SHT45 is one of its own, is checked here.
"""
import math
from pathlib import Path

import pytest
import yaml

from design import placement_entry
from sexpr import atom, child, children, parse

REPO = Path(__file__).resolve().parents[2]
LAYOUT = yaml.safe_load((REPO / "hardware/src/tongue/layout.yaml").read_text(encoding="utf-8"))
MECH = yaml.safe_load((REPO / "hardware/interface.yaml").read_text(encoding="utf-8"))["mechanical"]["tongue"]
PCB = REPO / "hardware/kicad/tongue/airq-tongue.kicad_pcb"
PLACE = {ref: list(placement_entry(v)[:3]) for ref, v in LAYOUT["placement"].items()}  # x, y, rot
OX, OY = LAYOUT["board"]["origin"]
SHT45_HALF = 0.75          # SHT45 body: 1.5 x 1.5 mm
CLEAR = 1.5                # global constraint: no other copper within 1.5 mm of it
VEML_FRONT = 1.85          # VEML7700 footprint: window face at footprint y = -1.85 (lib README)
JLC_MIN_SLOT = 1.0         # "Min. Non-Plated Slots", jlcpcb.com/capabilities/pcb-capabilities


def _inside(pt, poly) -> bool:
    x, y = pt
    hit = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def test_mechanical_record_matches_the_layout():
    board = LAYOUT["board"]
    assert MECH["outline"] == [board["width"], board["height"]]
    assert MECH["outline"][0] <= 22.0 and MECH["outline"][1] <= 14.0
    assert MECH["thickness"] == board["thickness"]
    assert MECH["mounting_hole"]["center"] == PLACE["H1"][:2]
    assert MECH["sht45"]["center"] == PLACE["U1"][:2]
    assert MECH["sht45"]["slot"] == board["cutouts"][0]
    x, y, rot = PLACE["U2"]
    assert rot == 0 and MECH["veml7700"]["faces"] == "-Y"       # footprint -Y (window) kept as -Y
    assert MECH["veml7700"]["window_center"][:2] == [x, round(y - VEML_FRONT, 3)]
    assert 0 <= MECH["veml7700"]["window_center"][1] <= 0.5     # window face just behind the edge
    assert PLACE["J1"][2] == 0 and MECH["qwiic"]["cable_entry"] == "+Y"   # mating face +Y
    assert MECH["qwiic"]["center_x"] == PLACE["J1"][0]


def test_arrangement_follows_the_front_edge():
    """Ruling R34: the front edge is the long edge opposite the cable entry (-Y, the top edge).
    The VEML7700 looks out of it at the end opposite the SHT45, and the SHT45 sits near it."""
    w, h = MECH["outline"]
    assert w > h and MECH["front_edge"] == "-Y" and MECH["qwiic"]["cable_entry"] == "+Y"
    assert MECH["veml7700"]["faces"] == MECH["front_edge"]
    sht_x, sht_y = MECH["sht45"]["center"]
    veml_x = MECH["veml7700"]["window_center"][0]
    assert sht_x < w / 2 < veml_x                               # opposite ends
    assert sht_y < h / 2                                        # front half, behind the intake lip


@pytest.mark.parametrize("direction", [(-1, 0), (0, -1), (0, 1)], ids=["left", "top", "bottom"])
def test_slot_surrounds_the_sht45_on_three_sides(direction):
    """Walking out from the SHT45 to the left, top and bottom crosses the slot, at least JLCPCB's
    minimum non-plated slot width of 1.0 mm wide; toward the neck (+X) there is no slot."""
    slot = [tuple(p) for p in LAYOUT["board"]["cutouts"][0]]
    cx, cy = PLACE["U1"][:2]
    step = 0.01
    hits = [i for i in range(1, 600)
            if _inside((cx + direction[0] * i * step, cy + direction[1] * i * step), slot)]
    width = (hits[-1] - hits[0] + 1) * step if hits else 0.0
    assert width >= JLC_MIN_SLOT - 1e-9
    assert len(hits) == hits[-1] - hits[0] + 1          # one continuous slot
    assert not any(_inside((cx + i * step, cy), slot) for i in range(1, 600))


def _board():
    return parse(PCB.read_text(encoding="utf-8"))


def _rot(px, py, deg):
    a = math.radians(deg)
    return px * math.cos(a) + py * math.sin(a), -px * math.sin(a) + py * math.cos(a)


def _pads(tree):
    """(reference, number, net, centre x, centre y, half-size x, half-size y), board-relative mm."""
    out = []
    for fp in children(tree, "footprint"):
        ref = next(str(p[2]) for p in children(fp, "property") if p[1] == "Reference")
        at = child(fp, "at")
        fx, fy, frot = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0
        for pad in children(fp, "pad"):
            pat, size = child(pad, "at"), child(pad, "size")
            dx, dy = _rot(float(pat[1]), float(pat[2]), frot)
            w, h = float(size[1]) / 2, float(size[2]) / 2
            if round(frot) % 180 == 90:
                w, h = h, w
            net = atom(pad, "net")
            out.append((ref, str(pad[1]), net and str(net), fx + dx - OX, fy + dy - OY, w, h))
    return out


def _keepout():
    cx, cy = PLACE["U1"][:2]
    r = SHT45_HALF + CLEAR
    return cx - r, cy - r, cx + r, cy + r


def _overlaps(box, x0, y0, x1, y1) -> bool:
    return box[0] < x1 and x0 < box[2] and box[1] < y1 and y0 < box[3]


def test_no_other_pad_via_or_pour_within_1_5_mm_of_the_sht45():
    tree, k = _board(), _keepout()
    for ref, num, _, x, y, w, h in _pads(tree):
        if ref != "U1":
            assert not _overlaps(k, x - w, y - h, x + w, y + h), f"{ref} pad {num}"
    for v in children(tree, "via"):
        at, size = child(v, "at"), float(atom(v, "size")) / 2
        x, y = float(at[1]) - OX, float(at[2]) - OY
        assert not _overlaps(k, x - size, y - size, x + size, y + size), "via"
    for z in children(tree, "zone"):
        for fp in children(z, "filled_polygon"):
            pts = [(float(p[1]) - OX, float(p[2]) - OY) for p in children(child(fp, "pts"), "xy")]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            assert not _overlaps(k, min(xs), min(ys), max(xs), max(ys)), f"zone {atom(z, 'name')}"


def _segment_hits_box(seg, box) -> bool:
    (x0, y0), (x1, y1), half = seg
    n = 200
    return any(_overlaps(box, x - half, y - half, x + half, y + half)
               for x, y in ((x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n + 1)))


def test_tracks_near_the_sht45_are_its_own():
    """Every track within 1.5 mm of the SHT45 is on F.Cu and reaches one of its pads through other
    such tracks (so no other net's trace, and no trace of a shared net, merely passes by)."""
    tree, k = _board(), _keepout()
    segs = []
    for s in children(tree, "segment"):
        a, b = child(s, "start"), child(s, "end")
        segs.append(((round(float(a[1]) - OX, 4), round(float(a[2]) - OY, 4)),
                     (round(float(b[1]) - OX, 4), round(float(b[2]) - OY, 4)),
                     float(atom(s, "width")) / 2, str(atom(s, "layer"))))
    near = [s for s in segs if _segment_hits_box(s[:3], k)]
    assert near, "the SHT45 has no traces"
    assert all(s[3] == "F.Cu" for s in near)
    reached = {(round(x, 4), round(y, 4)) for ref, _, _, x, y, _, _ in _pads(tree) if ref == "U1"}
    todo, done = set(range(len(near))), set()
    while True:
        new = {i for i in todo - done if near[i][0] in reached or near[i][1] in reached}
        if not new:
            break
        done |= new
        reached |= {p for i in new for p in near[i][:2]}
    assert done == todo, [near[i][:2] for i in sorted(todo - done)]
