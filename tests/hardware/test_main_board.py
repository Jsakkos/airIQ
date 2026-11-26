"""Main board: the mechanical record, the placement rules of the plan, the antenna keep-out, the pours
and the hand-routed USB pair and buck loop.

Pure Python on the committed files (no KiCad needed): hardware/src/main/layout.yaml,
hardware/interface.yaml `mechanical.main` and hardware/kicad/main/airq-main.kicad_pcb. DRC (run by
tests/hardware/test_kicad_pipeline.py) checks clearances and connectivity; these tests check what DRC
cannot know: where things are, which way they face, and that the record for the enclosure is true.
"""
import math
from pathlib import Path

import pytest
import yaml

from design import placement_entry
from sexpr import atom, child, children, parse

REPO = Path(__file__).resolve().parents[2]
LAYOUT = yaml.safe_load((REPO / "hardware/src/main/layout.yaml").read_text(encoding="utf-8"))
MECH = yaml.safe_load((REPO / "hardware/interface.yaml").read_text(encoding="utf-8"))["mechanical"]["main"]
PCB = REPO / "hardware/kicad/main/airq-main.kicad_pcb"
PLACE = {ref: placement_entry(v) for ref, v in LAYOUT["placement"].items()}   # ref -> x, y, rot, ref opt
OX, OY = LAYOUT["board"]["origin"]
W, H = LAYOUT["board"]["width"], LAYOUT["board"]["height"]

# footprint geometry (mm, footprint frame, y down), from hardware/kicad/lib/airq.pretty
USB_MOUTH = 4.97          # USB-C shell front face (the part is turned 180 degrees)
FPC_MOUTH, FPC_PIN1 = 3.88, 5.75
GH_FACE, SH_FACE = 3.05, 2.51  # mating faces of the JST GH 6 and SH 3/4 bodies (footprint +y)
LED_FACE = 1.36           # SK6812SIDE-A light face (footprint +y)
SW_TIP = 1.96             # SKRTLAE010 actuator tip (footprint +y)
WROOM_TOP, WROOM_BOTTOM, WROOM_HALF_W = -15.74, 9.76, 9.0   # module body
ANTENNA_STRIP = 6.0
ANTENNA_KEEPOUT_EDGE = 0.5   # the antenna keep-out covers the board up to y 0.5; rule areas below start there


def _at(ref):
    x, y, rot, _ = PLACE[ref]
    return x, y, rot


@pytest.fixture(scope="module")
def board():
    return parse(PCB.read_text(encoding="utf-8"))


def _rot(px, py, deg):
    a = math.radians(deg)
    return px * math.cos(a) + py * math.sin(a), -px * math.sin(a) + py * math.cos(a)


def _pads(tree):
    """{(reference, pad number): (net, x, y)} in board coordinates (pad centres)."""
    out = {}
    for fp in children(tree, "footprint"):
        ref = next(str(p[2]) for p in children(fp, "property") if p[1] == "Reference")
        at = child(fp, "at")
        fx, fy, frot = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0
        for pad in children(fp, "pad"):
            dx, dy = _rot(float(child(pad, "at")[1]), float(child(pad, "at")[2]), frot)
            net = atom(pad, "net")
            out[(ref, str(pad[1]))] = (net and str(net), fx + dx - OX, fy + dy - OY)
    return out


def _segments(tree, net=None):
    for s in children(tree, "segment"):
        if net is None or atom(s, "net") == net:
            a, b = child(s, "start"), child(s, "end")
            yield ((float(a[1]) - OX, float(a[2]) - OY), (float(b[1]) - OX, float(b[2]) - OY),
                   float(atom(s, "width")), str(atom(s, "layer")))


def _zone(tree, name):
    return next(z for z in children(tree, "zone") if atom(z, "name") == name)


def _poly(node):
    return [(float(p[1]) - OX, float(p[2]) - OY) for p in children(child(node, "pts"), "xy")]


# ---- the record for the enclosure ---------------------------------------------------------------

def test_outline_and_holes_match_the_layout():
    assert MECH["outline"] == [W, H] and W <= 60.0 and H <= 30.0
    assert MECH["thickness"] == LAYOUT["board"]["thickness"]
    assert MECH["mounting_holes"]["centers"] == [list(_at("H1")[:2]), list(_at("H2")[:2])]
    assert MECH["mounting_holes"]["diameter"] == 2.2


def test_connector_records_match_the_layout():
    x, y, rot = _at("J1")
    assert rot == 180 and MECH["usb_c"]["center_x"] == x
    assert MECH["usb_c"]["mouth_y"] == pytest.approx(y - USB_MOUTH)
    x, y, rot = _at("J7")
    assert rot == 0 and MECH["fpc"]["center_x"] == x
    assert MECH["fpc"]["mouth_y"] == pytest.approx(y + FPC_MOUTH)
    assert MECH["fpc"]["pin1_x"] == pytest.approx(x + FPC_PIN1)
    for key, ref, face in (("j_sen66", "J2", GH_FACE), ("j_qwiic_aux", "J4", SH_FACE)):
        x, y, rot = _at(ref)
        rec = MECH[key]
        assert rot == 270 and rec["edge"] == "-X" and rec["center_y"] == y, key   # mouth toward -X
        assert rec["mating_face_x"] == pytest.approx(x - face, abs=0.01), key
    for key, ref in (("j_qwiic_tongue", "J3"), ("j_led_ext", "J5")):
        x, y, rot = _at(ref)
        rec = MECH[key]
        assert rot == 0 and rec["edge"] == "+Y" and rec["center_x"] == x, key      # mouth toward +Y
        assert rec["mating_face_y"] == pytest.approx(y + SH_FACE), key


def test_connector_pin1_records_match_the_board(board):
    pads = _pads(board)
    assert pads[("J7", "1")][1] == pytest.approx(MECH["fpc"]["pin1_x"])
    assert pads[("J2", "1")][2] == pytest.approx(MECH["j_sen66"]["pin1_y"], abs=0.01)
    assert pads[("J4", "1")][2] == pytest.approx(MECH["j_qwiic_aux"]["pin1_y"], abs=0.01)
    assert pads[("J3", "1")][1] == pytest.approx(MECH["j_qwiic_tongue"]["pin1_x"], abs=0.01)
    assert pads[("J5", "1")][1] == pytest.approx(MECH["j_led_ext"]["pin1_x"], abs=0.01)
    assert pads[("J6", "1")][1:] == pytest.approx(tuple(MECH["aux_uart"]["pin1"]))


def test_led_and_button_records_match_the_layout():
    leds = MECH["leds"]
    assert [c["ref"] for c in leds["chain"]] == ["D1", "D2", "D3", "D4"]
    assert [c["index"] for c in leds["chain"]] == [0, 1, 2, 3]
    for c in leds["chain"]:
        x, y, rot = _at(c["ref"])
        assert rot == 0 and c["center_x"] == x                 # footprint +y (light) = +Y (front)
        assert leds["face_y"] == pytest.approx(y + LED_FACE)
    x, y, rot = _at("SW1")
    assert rot == 0 and MECH["button"]["actuator_center_x"] == x
    assert MECH["button"]["actuator_tip_y"] == pytest.approx(y + SW_TIP)


def test_antenna_record_matches_the_module_and_the_rule_area(board):
    x, y, rot = _at("U3")
    rec = MECH["antenna"]
    assert rot == 0                                            # antenna end toward -Y (rear)
    assert rec["module_body"] == [[x - WROOM_HALF_W, round(y + WROOM_TOP, 2)],
                                  [x + WROOM_HALF_W, round(y + WROOM_BOTTOM, 2)]]
    assert rec["overhang"] == pytest.approx(-(y + WROOM_TOP), abs=0.01)
    (x0, y0), (x1, y1) = rec["keepout"]
    pts = _poly(child(_zone(board, "ANTENNA_KEEPOUT"), "polygon"))
    assert {round(p[0], 3) for p in pts} == {x0, x1} and {round(p[1], 3) for p in pts} == {y0, y1}


# ---- the plan's placement rules ------------------------------------------------------------------

def test_rear_edge_usb_c_buck_and_module_corner():
    assert MECH["usb_c"]["mouth_y"] <= 0.1                     # USB-C mouth on the rear edge
    jx = _at("J1")[0]
    for ref in ("U2", "L1", "C1"):                             # buck next to it, along the rear edge
        x, y, _ = _at(ref)
        assert y < 8 and jx < x < MECH["antenna"]["module_body"][0][0], ref
    (mx0, my0), (mx1, _) = MECH["antenna"]["module_body"]
    assert W - mx1 <= 2.0 and my0 <= -ANTENNA_STRIP + 0.05    # rear-right corner, strip off the board
    # the USB plug (overmould up to ~12 mm wide) stays out of the antenna keep-out behind the edge
    assert MECH["usb_c"]["center_x"] + 6.0 <= MECH["antenna"]["keepout"][0][0]


def test_front_edge_leds_fpc_led_socket_and_button():
    xs = [c["center_x"] for c in MECH["leds"]["chain"]]
    assert xs == sorted(xs)                                    # chain order left -> right
    assert MECH["leds"]["face_y"] == pytest.approx(H, abs=0.05)
    gap = MECH["leds"]["divider_gap"]
    assert gap[0] == pytest.approx(xs[1] + 2.0) and gap[1] == pytest.approx(xs[2] - 2.0)
    assert gap[1] - gap[0] >= 4.0                              # room for the light-guide divider
    assert gap[0] < MECH["fpc"]["center_x"] < gap[1]
    assert MECH["fpc"]["mouth_y"] == pytest.approx(H, abs=0.05)
    assert MECH["j_led_ext"]["mating_face_y"] >= H - 1.0
    assert MECH["button"]["actuator_center_x"] > W - 5 and MECH["button"]["actuator_tip_y"] >= H


def test_sen66_and_qwiic_toward_the_front_left():
    """J_SEN66 on the left edge's front half, the tongue socket in the front-left corner facing the
    front (the tongue sits behind the intake lip), the spare Qwiic socket further back on the left edge."""
    sen, aux, tongue = MECH["j_sen66"], MECH["j_qwiic_aux"], MECH["j_qwiic_tongue"]
    assert sen["edge"] == "-X" and sen["mating_face_x"] <= 0.7 and sen["center_y"] > H / 2
    assert aux["edge"] == "-X" and aux["mating_face_x"] <= 0.7 and aux["center_y"] < sen["center_y"]
    assert tongue["edge"] == "+Y" and tongue["mating_face_y"] >= H - 1.0
    assert tongue["center_x"] < MECH["leds"]["chain"][0]["center_x"] - 5      # left of the LEDs


def test_every_part_is_placed_inside_the_outline():
    for ref, (x, y, _, _) in PLACE.items():
        assert 0 < x < W and 0 < y < H, ref


# ---- copper --------------------------------------------------------------------------------------

def _inside(pt, poly):
    x, y = pt
    hit = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def test_antenna_keepout_bans_all_copper_and_holds_none(board):
    zone = _zone(board, "ANTENNA_KEEPOUT")
    assert {str(l) for l in child(zone, "layers")[1:]} == {"F.Cu", "B.Cu"}
    ko = child(zone, "keepout")
    for what in ("tracks", "vias", "pads", "copperpour"):
        assert atom(ko, what) == "not_allowed", what
    pts = _poly(child(zone, "polygon"))
    assert len(pts) == 4                                       # a rectangle: test strictly inside it
    eps = 0.01                                                 # (the pours end exactly on its border)
    x0, y0 = min(p[0] for p in pts) + eps, min(p[1] for p in pts) + eps
    x1, y1 = max(p[0] for p in pts) - eps, max(p[1] for p in pts) - eps
    area = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    for net, x, y in _pads(board).values():
        assert not _inside((x, y), area)
    for a, b, *_ in _segments(board):
        assert not any(_inside(((a[0] * (10 - k) + b[0] * k) / 10, (a[1] * (10 - k) + b[1] * k) / 10), area)
                       for k in range(11))
    for v in children(board, "via"):
        assert not _inside((float(child(v, "at")[1]) - OX, float(child(v, "at")[2]) - OY), area)
    for z in children(board, "zone"):
        for fp in children(z, "filled_polygon"):
            assert not any(_inside(p, area) for p in _poly(fp)), atom(z, "name")


def test_ground_pours_cover_both_layers(board):
    for name, layer in (("GND_TOP", "F.Cu"), ("GND_BOTTOM", "B.Cu")):
        z = _zone(board, name)
        assert atom(z, "net") == "GND" and atom(z, "layer") == layer
        pts = _poly(child(z, "polygon"))
        assert {round(p[0], 3) for p in pts} == {0, W} and {round(p[1], 3) for p in pts} == {0, H}
        assert children(z, "filled_polygon"), f"{name} is not filled"


# ---- the bottom layer under the module is ground ------------------------------------------------

def _module_box():
    """U3's body over the board (the antenna strip beyond the rear edge left out): x0, y0, x1, y1."""
    (x0, y0), (x1, y1) = MECH["antenna"]["module_body"]
    return x0, max(y0, 0.0), x1, y1


def _length_inside(a, b, box):
    """Length of the segment a-b inside an axis-aligned box (Liang-Barsky clipping)."""
    (ax, ay), (bx, by) = a, b
    x0, y0, x1, y1 = box
    dx, dy = bx - ax, by - ay
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
        if p == 0:
            if q < 0:
                return 0.0
            continue
        t0, t1 = (max(t0, q / p), t1) if p < 0 else (t0, min(t1, q / p))
    return max(0.0, t1 - t0) * math.hypot(dx, dy)


def _fill_coverage(zone, layer, box, step=0.1):
    """Share of a box covered by a zone's fill on one layer: even-odd test of the filled polygons at the
    centres of a `step` grid."""
    edges = []
    for fp in children(zone, "filled_polygon"):
        if atom(fp, "layer") == layer:
            pts = _poly(fp)
            edges += list(zip(pts, pts[1:] + pts[:1]))
    x0, y0, x1, y1 = box
    nx, ny = round((x1 - x0) / step), round((y1 - y0) / step)
    hit = 0
    for j in range(ny):
        y = y0 + (j + 0.5) * step
        xs = sorted(ax + (y - ay) * (bx - ax) / (by - ay) for (ax, ay), (bx, by) in edges if (ay > y) != (by > y))
        for i in range(nx):
            x = x0 + (i + 0.5) * step
            hit += sum(1 for xc in xs if xc > x) % 2
    return hit / (nx * ny)


def test_no_bottom_layer_signals_under_the_module(board):
    """The bottom layer under U3 is the module's RF ground and the path for its heat (the EPAD's thermal
    vias): signals leave the module on the top layer. A rule area keeps B.Cu tracks out, and no signal
    track or via is inside the module's body (owner gate: it had grown to 199 mm of B.Cu signal track)."""
    box = _module_box()
    zone = _zone(board, "U3_NO_BOTTOM_TRACKS")
    layers = child(zone, "layers")                  # KiCad writes a one-layer rule area as (layer ...)
    assert ([str(l) for l in layers[1:]] if layers else [str(atom(zone, "layer"))]) == ["B.Cu"]
    assert atom(child(zone, "keepout"), "tracks") == "not_allowed"
    pts = _poly(child(zone, "polygon"))
    assert min(p[0] for p in pts) <= box[0] + 1e-6 and max(p[0] for p in pts) >= box[2] - 1e-6
    assert min(p[1] for p in pts) <= ANTENNA_KEEPOUT_EDGE + 1e-6 and max(p[1] for p in pts) >= box[3] - 1e-6
    inside = 0.0
    for s in children(board, "segment"):
        if atom(s, "layer") == "B.Cu" and atom(s, "net") != "GND":
            a, b = child(s, "start"), child(s, "end")
            inside += _length_inside((float(a[1]) - OX, float(a[2]) - OY), (float(b[1]) - OX, float(b[2]) - OY), box)
    assert inside <= 1.0, f"{inside:.1f} mm of B.Cu signal track under the module"
    for v in children(board, "via"):
        x, y = float(child(v, "at")[1]) - OX, float(child(v, "at")[2]) - OY
        inside_box = box[0] <= x <= box[2] and box[1] <= y <= box[3]
        assert not inside_box or atom(v, "net") == "GND", f"signal via under the module at {x:.2f}, {y:.2f}"


def test_bottom_ground_under_the_module_and_its_epad_is_solid(board):
    """GND_BOTTOM fills >= 90 % of the module's on-board body and >= 95 % of the 6 x 6 mm square round its
    EPAD (the EPAD's pads connect solid, layout.yaml custom rule), on a 0.1 mm grid."""
    zone = _zone(board, "GND_BOTTOM")
    assert _fill_coverage(zone, "B.Cu", _module_box()) >= 0.90
    epad = [(x, y) for (ref, num), (_, x, y) in _pads(board).items() if ref == "U3" and 30 <= int(num) <= 37]
    cx = (min(x for x, _ in epad) + max(x for x, _ in epad)) / 2
    cy = (min(y for _, y in epad) + max(y for _, y in epad)) / 2
    assert _fill_coverage(zone, "B.Cu", (cx - 3, cy - 3, cx + 3, cy + 3)) >= 0.95


def test_usb_pair_runs_side_by_side_to_the_module(board):
    """D- and D+ leave the ESD part together and run parallel, 0.45 mm apart, on the top layer."""
    def longest(net):
        return max((s for s in _segments(board, net) if s[3] == "F.Cu"),
                   key=lambda s: math.dist(s[0], s[1]))
    dn, dp = longest("USB_DN"), longest("USB_DP")
    assert math.dist(*dn[:2]) > 15 and math.dist(*dp[:2]) > 15
    assert dn[0][1] == pytest.approx(dn[1][1]) and dp[0][1] == pytest.approx(dp[1][1])  # both along X
    assert abs(dp[0][1] - dn[0][1]) == pytest.approx(0.45, abs=0.01)
    assert sum(1 for v in children(board, "via") if atom(v, "net") == "USB_DN") == 0


def _graph(board, net):
    """Track graph of a net: {point: {neighbour point: length}}, points rounded to 0.01 mm (track
    ends, vias joining the layers at the same point)."""
    g = {}
    for a, b, *_ in _segments(board, net):
        a, b = (round(a[0], 2), round(a[1], 2)), (round(b[0], 2), round(b[1], 2))
        g.setdefault(a, {})[b] = g.setdefault(b, {})[a] = math.dist(a, b)
    return g


def _node(g, xy):
    """The graph point on a pad (a track ending within 0.3 mm of its centre)."""
    p = min(g, key=lambda q: math.dist(q, xy))
    assert math.dist(p, xy) < 0.3, xy
    return p


def _reach(g, start):
    """Shortest track length from `start` to every point it reaches (Dijkstra)."""
    import heapq
    dist, todo = {start: 0.0}, [(0.0, start)]
    while todo:
        d, p = heapq.heappop(todo)
        if d > dist[p]:
            continue
        for q, w in g[p].items():
            if d + w < dist.get(q, math.inf):
                dist[q] = d + w
                heapq.heappush(todo, (d + w, q))
    return dist


@pytest.mark.parametrize("net,contacts,esd_in,esd_out,mcu", [
    ("USB_DP", ("A6", "B6"), "6", "1", "14"),
    ("USB_DN", ("A7", "B7"), "4", "3", "13"),
])
def test_usb_contacts_go_through_the_esd_part(board, net, contacts, esd_in, esd_out, mcu):
    """Both connector contacts of each line reach the USBLC6's flow-through input pin and nothing else;
    its output pin alone reaches the module, so the line passes through the ESD part (no stub)."""
    pads, g = _pads(board), _graph(board, net)
    node = lambda ref, pad: _node(g, pads[(ref, pad)][1:])  # noqa: E731
    starts = [node("J1", c) for c in contacts]
    assert all(node("U3", mcu) in _reach(g, s) for s in starts)
    for pin in (esd_in, esd_out):            # every path from a contact to the module crosses both pins
        cut = {p: {q: w for q, w in nb.items() if q != node("U1", pin)}
               for p, nb in g.items() if p != node("U1", pin)}
        assert all(node("U3", mcu) not in _reach(cut, s) for s in starts), pin
    # and the contacts reach the input pin before the output pin: the input side holds no output pad
    cut = {p: {q: w for q, w in nb.items() if q != node("U1", esd_in)}
           for p, nb in g.items() if p != node("U1", esd_in)}
    assert all(node("U1", esd_out) not in _reach(cut, s) for s in starts)


def test_usb_pair_lengths_match(board):
    """ESD output to module pin: D+ and D- within 0.5 mm of each other (USB full speed needs far less)."""
    pads = _pads(board)
    length = {}
    for net, esd_out, mcu in (("USB_DP", "1", "14"), ("USB_DN", "3", "13")):
        g = _graph(board, net)
        length[net] = _reach(g, _node(g, pads[("U1", esd_out)][1:]))[_node(g, pads[("U3", mcu)][1:])]
    assert 25 < length["USB_DP"] < 35
    assert abs(length["USB_DP"] - length["USB_DN"]) <= 0.5, length


def test_buck_hot_loop_is_tight(board):
    """TPS562201: C1 straddles VIN (pin 3) and GND (pin 1); SW (pin 2) runs straight to L1."""
    pads = _pads(board)
    d = lambda a, b: math.dist(pads[a][1:], pads[b][1:])  # noqa: E731
    assert pads[("U2", "3")][0] == "+5V" and pads[("U2", "1")][0] == "GND"
    assert d(("U2", "3"), ("C1", "1")) < 2.0 and d(("U2", "1"), ("C1", "2")) < 2.0
    assert d(("U2", "2"), ("L1", "1")) < 4.0


def test_buck_switch_node_is_small(board):
    """The SW node is the short run pin 2 -> L1 plus the bootstrap cap's stub west of the GND pin: no
    second path round the hot-loop ground (pin 1, C1-, its vias) and little dv/dt copper."""
    segs = list(_segments(board, "/power/BUCK_SW"))
    assert sum(math.dist(a, b) for a, b, *_ in segs) <= 8.0
    gnd_pin_x = _pads(board)[("U2", "1")][1]                  # 25.95
    for a, b, *_ in segs:
        for x, y in (a, b):
            assert y <= 4.0 or x < gnd_pin_x - 0.5, (a, b)    # below the SW row only on the C4 stub
