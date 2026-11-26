"""Layout studies for the airQ and the airQ mini (Plan 3, ruling R14): the side-section
arithmetic behind enclosure/README.md "Layout studies".

Pure Python (no SolidCraft, no numpy), so the fast tests and CI can rerun it:

    uv run --with pyyaml python enclosure/src/layout_study.py

Frame (R3): y = 0 at the shell's front bottom edge, +y to the rear; z = 0 at the bottom plane.
The front is an optional vertical lower lip of height `lip` (R15), then a slope at `tilt` from
vertical up to the top. Face coordinates on the slope: s = distance up the slope from its bottom
edge (0, lip), t = depth behind the slope's outer surface (t = wall is its inner face). f is the
distance along the whole front surface from the bottom edge (lip, then slope).

The main board is a rigid side section (layout frame Y: 0 at the rear edge, 30 at the front edge;
Z from the top face, the bottom face at -1.6) placed by its tilt `alpha` (front edge down) and the
device position F of its front-bottom corner. Every constraint is a half-plane in F, so a pose is
a 2-D linear feasibility problem, solved exactly by vertex enumeration:
- rear wall (the antenna strip may instead pass into a hood on the rear face, `hood`);
- top wall;
- front: behind the slope's inner face, behind the lip's inner face, behind the panel's back
  (airQ) and behind the light guide where the LED faces and J7 face the front;
- the SEN66 below the board with the zone wall between: the SEN66's front-top corner at least
  `zone` below the board's bottom plane, the SEN66 as far back as its cable plug or outlet
  plenum allows.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from functools import lru_cache

import board_sources as B
from sclib import mechanical


@lru_cache(maxsize=1)
def _refs() -> dict:
    """Sizes read from the reference generators and interface.yaml (not retyped)."""
    import ref_epd
    import ref_sen66
    sen, epd, m = ref_sen66.build(), ref_epd.build(), mechanical("main")
    return {"sen_l": sen.v("L"), "sen_w": sen.v("W"), "sen_h": sen.v("H"),
            "panel_l": epd.v("panel_l"), "panel_w": epd.v("panel_w"), "panel_t": epd.v("panel_t"),
            "block_out": epd.v("block_out"), "va_far": epd.v("va_far"), "va_w": epd.v("va_w"),
            "main": m}


@dataclass(frozen=True)
class Model:
    """Envelope, front and margins. The defaults are the airQ (plan Task 3); MINI below is the
    airQ mini (plan Task 4, spec section 5)."""
    name: str = "airq"
    W: float = 95.0
    D: float = 55.0
    H: float = 48.0
    tilt_deg: float = 30.0
    lip: float = 0.0             # vertical lower lip height (R15); 0: the slope starts at the bottom edge
    front: str = "panel"         # "panel": e-ink behind the face (airQ); "band": light band, no panel (mini)
    hood: bool = False           # the antenna strip may pass the rear wall into a hood on the rear face
    sen_pose: str = "standing"   # R17; "flat" (21.3 tall, ports up or down) breaks Sensirion's rule, for comparison only
    wall: float = 1.8            # plan default (>= 1.6)
    floor: float = 2.0           # plan: base plate
    zone_wall: float = 1.8       # the zone wall, a wall like any other
    zone_gap: float = 0.3        # air gap above the SEN66 and under the board
    clr: float = 0.2             # part-to-wall gap (clr_remove)
    foam: float = 1.0            # plan: the SEN66 sits on 1 mm foam
    bezel: float = 1.0           # airQ: window lip in front of the panel
    guide_t: float = 2.0         # airQ: light guide between the LED faces and the panel (R20 coupon bar 3 x 2)
    band_guide: float = 1.0      # mini: room in front of the LED faces for the guides' entry and holder
    sen_behind: float = 5.0      # behind the SEN66: cable plug (connector face) or outlet plenum
    sen_front: float = 3.0       # in front of the SEN66's port face: the inlet gasket
    tongue_d: float = 13.0       # the tongue's depth (interface.yaml tongue outline), lying in the intake air
    tongue_top: float = 14.6     # its top above z 0: on a ledge at z 10 (1.6 board + 3.0 parts)
    grille_min_z: float = 10.0   # plan: no opening's lower edge below 10 mm
    slot_w: float = 1.2          # plan default slot width
    slot_bar: float = 1.6        # bar between slot rows and between slots
    slot_len: float = 8.4        # one slot's length (8 slots + 7 bars = 80 mm per row on the airQ)
    slot_row_len: float = 80.0   # grille row length across the face
    led_slot_h: float = 1.2      # airQ: the LED line's slot height
    face_wall: float = 1.2       # solid face between slot band, LED slot / labels / band, panel pocket
    usb_overmold: float = 7.0    # USB-C plug overmold height (typical 6.5-7.5; to confirm)
    outlet_pitch: float = 3.0    # outlet grille slot pitch (1.2 slots, 1.8 bars: the coupon's straight slots)

    @property
    def c(self) -> float:
        return math.cos(math.radians(self.tilt_deg))

    @property
    def s(self) -> float:
        return math.sin(math.radians(self.tilt_deg))


AIRQ = Model()
MINI = Model(name="mini", W=66.0, D=50.0, H=42.0, tilt_deg=24.0, front="band",
             slot_row_len=56.0, slot_len=12.4)
BEST_CASE = dict(wall=1.6, zone_wall=1.6, zone_gap=0.2, clr=0.2, bezel=1.0)
WALLS_16 = dict(wall=1.6, zone_wall=1.6)
INTAKE_MIN = 154.5                # R18: 2 x the inlets' 77.3 mm2
OUTLET_MIN, OUTLET_FLOOR = 660.1, 296.0   # R18: 2 x 330.1; floor 2 x Sensirion's 148


def sen_dims(m: Model) -> tuple[float, float]:
    """The SEN66's (depth along y, height) as placed: standing on its 55.2 x 21.3 face (R17,
    port face vertical) or, for comparison only, flat on its port or connector face."""
    r = _refs()
    return (r["sen_h"], r["sen_w"]) if m.sen_pose == "standing" else (r["sen_w"], r["sen_h"])


def sen_top(m: Model) -> float:
    return m.floor + m.foam + sen_dims(m)[1]


# --- face coordinates -----------------------------------------------------------------------

def t_of(m: Model, y: float, z: float) -> float:
    """Depth of (y, z) behind the slope's outer surface."""
    return y * m.c - (z - m.lip) * m.s


def s_of(m: Model, y: float, z: float) -> float:
    """Distance of (y, z)'s foot up the slope from the slope's bottom edge."""
    return y * m.s + (z - m.lip) * m.c


def yz_of(m: Model, s: float, t: float) -> tuple[float, float]:
    return s * m.s + t * m.c, m.lip + s * m.c - t * m.s


def front_inner_y(m: Model, z: float) -> float:
    """y of the front's inner face (lip or slope) at height z."""
    return max(m.wall, (m.wall + (z - m.lip) * m.s) / m.c)


def front_f(m: Model, z: float) -> float:
    """Distance along the front surface, from its bottom edge, of the point at height z."""
    return z if z <= m.lip else m.lip + (z - m.lip) / m.c


def face_length(m: Model) -> float:
    return front_f(m, m.H)


def slot_open(m: Model, row_len: float) -> float:
    """Open length of one grille row of slot_len slots with slot_bar bars."""
    n = math.floor((row_len + m.slot_bar) / (m.slot_len + m.slot_bar))
    return n * m.slot_len


def panel_top_max(m: Model) -> float:
    """Highest panel top edge (s on the slope): its back corner (t = bezel + panel_t) stays clr
    under the top wall's inner face."""
    r = _refs()
    return (m.H - m.lip - m.wall - m.clr + (m.bezel + r["panel_t"]) * m.s) / m.c


def face_budget(m: Model, rows: int = 2, led_in_slot_row: bool = False) -> dict:
    """airQ front, bottom to top along f: slots (rows of slot_w at slot_w + slot_bar pitch from
    the 10 mm line), the LED slot, the panel pocket and the panel (on the slope). spare < 0: does
    not fit. With led_in_slot_row the LED line takes the middle 30 mm of the top slot row."""
    r = _refs()
    f10 = front_f(m, m.grille_min_z)
    band_top = f10 + rows * m.slot_w + (rows - 1) * m.slot_bar
    if led_in_slot_row:
        led = (band_top - m.slot_w, band_top)
        pocket = band_top + m.face_wall
    else:
        led = (band_top + m.face_wall, band_top + m.face_wall + m.led_slot_h)
        pocket = led[1] + m.face_wall
    p0 = max(pocket + m.clr, m.lip + m.clr)          # the panel lies on the slope
    panel = (p0, p0 + r["panel_w"])
    top = m.lip + panel_top_max(m)
    per_row = slot_open(m, m.slot_row_len)
    per_side = slot_open(m, (m.slot_row_len - 30.0 - 2 * m.slot_bar) / 2)
    open_len = (rows - 1) * per_row + 2 * per_side if led_in_slot_row else rows * per_row
    return {"face": face_length(m), "f10": f10, "slot_band": (f10, band_top), "led": led,
            "panel": panel, "panel_top_max": top, "spare": top - panel[1],
            "open_area": open_len * m.slot_w}


def band_budget(m: Model, text_h: float = 5.0, band_h: float = 2.0, top_margin: float = 1.5,
                band_f: float | None = None) -> dict:
    """Mini front, bottom to top along f: slot rows from the 10 mm line (as many as the intake's
    154.5 mm2 needs), the debossed labels (text_h, the coupons' legible 0.4 mm deboss height),
    then the light band. band_f puts the band's lower edge there (straight guides from the LED
    faces), else as low as the labels allow. The dot and the light-sensor window sit beside the
    band (top right, top left), as in the owner's mockup."""
    f10 = front_f(m, m.grille_min_z)
    per_row = slot_open(m, m.slot_row_len) * m.slot_w
    rows = math.ceil(INTAKE_MIN / per_row)
    slots = (f10, f10 + rows * m.slot_w + (rows - 1) * m.slot_bar)
    labels = (slots[1] + m.face_wall, slots[1] + m.face_wall + text_h)
    lo = labels[1] + 1.0
    b0 = lo if band_f is None else band_f
    band = (b0, b0 + band_h)
    return {"face": face_length(m), "f10": f10, "rows": rows, "slots": slots, "open_area": rows * per_row,
            "labels": labels, "band": band, "band_fits": b0 >= lo,
            "spare": face_length(m) - top_margin - band[1]}


def outlet_grille(m: Model) -> dict:
    """The largest outlet grille on the lower rear: across the inner width (2 mm margins each
    side) from the 10 mm line to the zone wall's underside, slots slot_w at outlet_pitch."""
    h = sen_top(m) + m.zone_gap - m.grille_min_z
    w = m.W - 2 * m.wall - 4.0
    area = w * h * m.slot_w / m.outlet_pitch
    return {"width": w, "height": h, "open_area": area, "meets_2x": area >= OUTLET_MIN,
            "meets_floor": area >= OUTLET_FLOOR}


# --- R25 / R26 (fix round 1): the outlet path and the HCHO pocket against the outlet grille ----

ZW_TF = 7.2        # the zone wall's slanted part: front face depth behind the slope (airq zw_tf)
SLAB = 1.2         # the zone wall's ledge (airq ledge_t)
RIB = 1.6          # the zone wall's seat on the rear wall over the outlet plenum (airq rib_d)
PORT_OUTLET = 330.1


def _z_under(m: Model, y: float) -> float:
    """The zone wall's underside at depth y: the ledge, the slant, the flat part over the SEN66."""
    zw_z0 = sen_top(m) + m.zone_gap
    return min(zw_z0, max(m.lip - SLAB, m.lip + (y * m.c - ZW_TF - m.zone_wall) / m.s))


def front_layer(m: Model, y_port: float, under_ledge: bool = False, step: float = 0.01) -> float:
    """The ports-forward pose (3a before fix round 1): the section, normal to x, of the sensor zone
    in front of the SEN66's port face (at y_port) under the zone wall. That is the most an outlet
    duct running along the module's front, to its end and back, can have (R25 needs 330.1).
    under_ledge: also take the strip under the ledge, which is the intake slots' plenum."""
    y0 = m.wall if under_ledge else (ZW_TF + m.zone_wall - SLAB * m.s) / m.c       # the ledge's back edge
    n = int((y_port - y0) / step)
    return sum((_z_under(m, y0 + (i + 0.5) * step) - m.floor) * step for i in range(n))


def hcho_alternatives(m: Model, sfa: float = 25.4, plug: float = 5.2, plug_up: float = 5.0) -> list[dict]:
    """R26: the HCHO pocket and the outlet grille, alternatives worked with numbers (m: the R22
    lip model as built, lip 15, H 51). The grille runs on the rear wall from the 10 mm line up to
    the zone wall (or its seat, as built), 2 mm in from the ends, 1.2 slots at a 3.0 pitch
    (40 %, the coupon's) or a 2.4 pitch (50 %). R18 asks 660.1 open."""
    inner = m.W / 2 - m.wall - m.clr                      # 45.5: the base's parts inside the shell
    h = sen_top(m) + m.zone_gap - m.grille_min_z          # 18.9: 10 mm line to the zone wall
    sfa_x0 = -inner + 1.5                                 # 3a: the SFA40 1.5 from the left wall
    rows = []

    def row(name, x0, x1, height, notes, fits=True):
        w = x1 - x0
        n40, n50 = math.floor((w + 1.8) / 3.0), math.floor((w + 1.2) / 2.4)     # 1.2 slots, 1.8 / 1.2 bars
        out = {"name": name, "grille": (x0, x1), "height": height, "slots_40": n40, "slots_50": n50,
               "open_40": n40 * m.slot_w * height, "open_50": n50 * m.slot_w * height, "fits": fits, "notes": notes}
        out["meets"] = fits and max(out["open_40"], out["open_50"]) >= 2 * PORT_OUTLET
        rows.append(out)

    row("3a as built: SFA40 standing at the rear left, facing its grille in the rear wall",
        sfa_x0 + sfa + plug + m.wall, inner - 2.0, h, "the pocket and its plug room take the rear wall's left 34 mm")
    row("narrower pocket, the plug leaving upward", sfa_x0 + sfa + m.clr + m.wall, inner - 2.0, h,
        f"the board stands {sfa} tall and the plug needs {plug_up} above it: {sfa + plug_up:.1f} > "
        f"{h + m.grille_min_z - m.floor:.1f} from the floor to the zone wall, so it does not fit",
        fits=sfa + plug_up <= h + m.grille_min_z - m.floor)
    row("upper-rear exhaust kept separate (no outlet grille above the zone wall)", sfa_x0 + sfa + plug + m.wall,
        inner - 2.0, h, "the rear wall above the zone wall is the electronics zone's exhaust: joining it to the outlet "
        "would open the SEN66's outlet path to the case air (plan), so it adds nothing")
    row("SFA40 along the right side wall, low side grille; ports forward (the pose of 3a)", -inner + 2.0, inner - 2.0, h,
        "the rear wall is free (40 % by slot count is short too), but the SFA40 (25.4 x 25.4 standing, y 18-43) meets H2's standoff (y 21.6-26.0 at the "
        "right wall), and with the ports forward the outlet duct in front of the module has at most "
        f"{front_layer(m, 20.0, under_ledge=True):.0f} mm2 (R25: 330.1)", fits=False)
    tub = inner - 1.6                                    # 43.9: inside the base's side rails
    row("chosen: ports to the rear; SFA40 flat at the front right under the tongue, its grille in the right side",
        -tub + 2.0, -tub + 2.0 + 32 * 2.4 - 1.2, h - RIB,
        "the outlet plenum spans the rear behind the module; 50 % open (32 slots) reaches R18; 40 % over the "
        f"plenum's {2 * tub - 4:.1f} mm would give {math.floor((2 * tub - 4 + 1.8) / 3.0) * m.slot_w * (h - RIB):.0f}")
    return rows


# --- the main board's section ------------------------------------------------------------

@lru_cache(maxsize=1)
def board_points() -> tuple:
    """(Y, Z, kind) corners of the board's side section (max over x), layout frame, from
    interface.yaml mechanical.main. kind: 'guide' = an LED or J7 face (the light guide, and on
    the airQ the FFC, pass in front of it), 'panel' = must clear the panel's back (airQ) or the
    front wall, 'wall' = beside the panel (SW1 stands under the dot, right of the panel), 'bottom'
    = the board's bottom face, 'antenna' = the strip past the rear edge."""
    m = _refs()["main"]
    board_d = m["outline"][1]          # 30: the front edge is at Y = board_d
    th = m["thickness"]
    mod = m["antenna"]["module_body"]
    j2, j3, j5 = m["j_sen66"]["body"], m["j_qwiic_tongue"]["body"], m["j_led_ext"]["body"]
    usb = m["usb_c"]
    btn = m["button"]
    # interface.yaml gives these only in comments: board_sources reads them (R27, not retyped)
    mod_h, qwiic_h, led_h, fpc_h, sw_h, usb_len = (B.module_h(), B.connector_h("j_qwiic_tongue"), B.led_body_h(),
                                                   B.j7_body()[2], B.sw_body_h(), B.usb_len())
    return (
        (mod[0][1], 0.0, "antenna"), (mod[0][1], mod_h, "antenna"), (mod[1][1], mod_h, "panel"),
        (0.0, usb["shell"][1], "panel"), (usb_len, usb["shell"][1], "panel"),
        (j2[0][1], m["max_part_height"], "panel"), (j2[1][1], m["max_part_height"], "panel"),
        (j3[1][1], qwiic_h, "panel"), (j5[1][1], qwiic_h, "panel"),
        (m["leds"]["face_y"] - 1.6, led_h, "guide"), (m["leds"]["face_y"], led_h, "guide"),
        (m["fpc"]["mouth_y"], fpc_h, "guide"),
        (btn["actuator_tip_y"], btn["actuator_center_z"], "wall"), (29.98, sw_h, "wall"),
        (0.0, -th, "bottom"), (board_d, -th, "bottom"), (board_d, 0.0, "panel"),
    )


def offset(alpha_deg: float, Y: float, Z: float) -> tuple[float, float]:
    """Device offset of board point (Y, Z) from the front-bottom corner F (Y 30, Z -1.6)."""
    a = math.radians(alpha_deg)
    return ((30 - Y) * math.cos(a) - (Z + 1.6) * math.sin(a),
            (30 - Y) * math.sin(a) + (Z + 1.6) * math.cos(a))


def constraints(m: Model, alpha_deg: float) -> list[tuple[float, float, float, str]]:
    """Half-planes a_y * Fy + a_z * Fz <= b over the front-bottom corner F, named."""
    r = _refs()
    pts = [(offset(alpha_deg, Y, Z), kind) for Y, Z, kind in board_points()]
    if m.front == "panel":
        tpb = m.bezel + r["panel_t"]
        need = {"guide": tpb + m.clr + m.guide_t + m.clr, "panel": tpb + m.clr}
    else:
        need = {"guide": m.wall + m.clr + m.band_guide, "panel": m.wall + m.clr}
    need.update(wall=m.wall + m.clr, bottom=m.wall + m.clr, antenna=need["panel"])
    rear = [o for o, kind in pts if not (m.hood and kind == "antenna")]
    out = [(1.0, 0.0, m.D - m.wall - m.clr - max(o[0] for o in rear), "rear wall"),
           (0.0, 1.0, m.H - m.wall - m.clr - max(o[1] for o, _ in pts), "top wall")]
    # slope: t(F + o) = (Fy + oy) c - (Fz + oz - lip) s >= need
    #   <=>  -c Fy + s Fz <= oy c - oz s + lip s - need, the tightest point binding
    k = max(need[kind] - (o[0] * m.c - o[1] * m.s) for o, kind in pts)
    out.append((-m.c, m.s, m.lip * m.s - k, "front slope (panel, light guide)"))
    if m.lip > 0:
        out.append((-1.0, 0.0, -max(m.wall + m.clr - o[0] for o, _ in pts), "front lip"))
    # SEN66 at the rear, its front-top corner C at least `zone` below the board's bottom plane:
    # (y_s0 - Fy) sin a - (top - Fz) cos a >= zone
    a = math.radians(alpha_deg)
    depth, _ = sen_dims(m)
    y_s0 = m.D - m.wall - m.sen_behind - depth
    zone = 2 * m.zone_gap + m.zone_wall
    out.append((math.sin(a), -math.cos(a), y_s0 * math.sin(a) - sen_top(m) * math.cos(a) - zone,
                "SEN66 + zone wall"))
    return out


def feasible_region(m: Model, alpha_deg: float, eps: float = 1e-9) -> list[tuple[float, float]]:
    """Vertices of the feasible set of F (empty: no pose at this tilt)."""
    cons = constraints(m, alpha_deg)
    verts = []
    for p in range(len(cons)):
        for q in range(p + 1, len(cons)):
            a1, b1, c1, _ = cons[p]
            a2, b2, c2, _ = cons[q]
            det = a1 * b2 - a2 * b1
            if abs(det) < 1e-12:
                continue
            fy, fz = (c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det
            if all(a * fy + b * fz <= c + eps for a, b, c, _ in cons):
                verts.append((fy, fz))
    return verts


def _hit(m: Model, p: tuple[float, float], alpha_deg: float) -> tuple[float, float, float] | None:
    """Where the line from p toward the front along (-cos a, -sin a) meets the front's outer
    surface: (f, distance, angle to that surface's normal in degrees), or None if it never does."""
    a = math.radians(alpha_deg)
    d = (-math.cos(a), -math.sin(a))
    cos_slope = math.cos(math.radians(alpha_deg + m.tilt_deg))
    if cos_slope > 1e-9:
        k = t_of(m, *p) / cos_slope
        z = p[1] + k * d[1]
        if z >= m.lip:
            return m.lip + s_of(m, p[0] + k * d[0], z), k, alpha_deg + m.tilt_deg
    if m.lip > 0 and math.cos(a) > 1e-9:
        k = p[0] / math.cos(a)
        z = p[1] + k * d[1]
        if 0 <= z <= m.lip:
            return z, k, alpha_deg
    return None


def _box_gap(a: tuple, b: tuple) -> float:
    """Distance between two axis-aligned boxes ((x0, x1), (y0, y1), (z0, z1))."""
    return math.sqrt(sum(max(0.0, lo2 - hi1, lo1 - hi2) ** 2 for (lo1, hi1), (lo2, hi2) in zip(a, b)))


def pose(m: Model, alpha_deg: float) -> dict | None:
    """The feasible pose with the highest front edge, and what it gives: front edge, button and
    dot, USB-C plug axis, antenna end, lowest board point, antenna-to-SEN66 distance."""
    verts = feasible_region(m, alpha_deg)
    if not verts:
        return None
    fy, fz = max(verts, key=lambda v: (v[1], -v[0]))
    r = _refs()
    mb = r["main"]
    a = math.radians(alpha_deg)

    def dev(Y, Z):
        o = offset(alpha_deg, Y, Z)
        return fy + o[0], fz + o[1]

    btn = dev(mb["button"]["actuator_tip_y"], mb["button"]["actuator_center_z"])
    # SW1 is pushed along the board's -Y: a pusher from the front travels along (-cos a, -sin a).
    # A dot can press it if that axis meets the front within 60 deg of the surface's normal
    # (on the slope the angle is alpha + tilt; at 90 deg the axis runs along the face).
    hit = _hit(m, btn, alpha_deg)
    if hit is not None and hit[2] <= 60.0:
        dot_f, dot_gap = hit[0], hit[1] - m.wall / math.cos(math.radians(hit[2]))
    else:
        dot_f = dot_gap = None
    push_angle = alpha_deg + m.tilt_deg
    led = dev(mb["leds"]["face_y"], mb["leds"]["light_center_z"])
    led_hit = _hit(m, led, alpha_deg)          # where a straight guide from the LED faces reaches the front
    led_f = led_hit[0] if led_hit else None
    mouth = dev(0.0, mb["usb_c"]["shell"][1] / 2)
    if math.cos(a) > 1e-9:
        usb_exit_z = mouth[1] + (m.D - mouth[0]) / math.cos(a) * math.sin(a)
    else:
        usb_exit_z = math.inf
    pts = [dev(Y, Z) for Y, Z, _ in board_points()]
    ant = [dev(Y, Z) for Y in (mb["antenna"]["module_body"][0][1], 0.0) for Z in (0.0, B.module_h())]
    ant_end = dev(mb["antenna"]["module_body"][0][1], 0.0)
    tpb = (m.bezel + r["panel_t"]) if m.front == "panel" else m.wall
    lowest = min(p[1] for p in pts)
    # antenna strip vs SEN66 (R12). The SEN66 may sit anywhere from the rear (y_rear) forward to
    # where its front-top corner meets the front (inlet gasket in front) and, with the tongue in
    # the intake air in front of its ports, where the tongue behind the lower front still fits.
    x = x_layout(m)
    depth, _ = sen_dims(m)
    top = sen_top(m)
    y_rear = m.D - m.wall - m.sen_behind - depth
    y_corner = max(m.wall + m.clr + m.sen_front, front_inner_y(m, top) + m.clr + m.sen_front)
    y_tongue = front_inner_y(m, m.tongue_top) + m.clr + m.tongue_d + m.clr + m.sen_front
    if alpha_deg:     # the board's bottom plane must stay `zone` above the corner
        zone = 2 * m.zone_gap + m.zone_wall
        y_corner = max(y_corner, fy + (zone + (top - fz) * math.cos(a)) / math.sin(a))
    ant_box = (x["antenna"], (min(p[0] for p in ant), max(p[0] for p in ant)), (min(p[1] for p in ant), max(p[1] for p in ant)))

    def sen_box(ys):
        return (x["sen66"], (ys, ys + depth), (m.floor + m.foam, top))
    ys = min(max(y_corner, y_tongue), y_rear)
    return {"alpha": alpha_deg, "F": (fy, fz), "front_edge": dev(30.0, 0.0), "button": btn,
            "push_angle": push_angle, "dot_f": dot_f, "dot_gap": dot_gap, "led": led, "led_f": led_f,
            "usb_mouth": mouth, "usb_exit_z": usb_exit_z,
            "usb_rear": usb_exit_z + m.usb_overmold / 2 <= m.H - m.wall,
            "usb_well": m.D - m.wall - mouth[0],
            "antenna_end": ant_end, "hood_out": max(0.0, ant_end[0] + m.clr + m.wall - m.D),
            "antenna_behind_front": min(t_of(m, *p) for p in ant) - tpb,
            # the tongue in front of the SEN66 (the layout); the SEN66 as far forward as it can go
            # with the tongue elsewhere; the SEN66 at the rear
            "antenna_to_sen66": _box_gap(ant_box, sen_box(ys)), "sen66_y": (ys, ys + depth),
            "tongue_fits": y_tongue <= y_rear,
            "antenna_to_sen66_max": _box_gap(ant_box, sen_box(min(y_corner, y_rear))),
            "antenna_to_sen66_rear": _box_gap(ant_box, sen_box(y_rear)),
            "lowest_z": lowest, "sen_top": top, "zone_order": lowest >= top - 1e-6}


def min_depth(m: Model, alpha_deg: float, lo: float = 40.0, hi: float = 90.0) -> float | None:
    """Smallest D (to 0.01 mm) at which a pose at this tilt exists."""
    if pose(replace(m, D=hi), alpha_deg) is None:
        return None
    while hi - lo > 0.01:
        mid = (lo + hi) / 2
        if pose(replace(m, D=mid), alpha_deg) is None:
            lo = mid
        else:
            hi = mid
    return hi


def horizontal_overflow(m: Model) -> float:
    """How much deeper than m.D the horizontal board needs the case to be (> 0: it does not fit;
    without a hood this is how far the antenna end stands past the rear wall's inner face, the
    0.2 clearance included)."""
    return min_depth(m, 0) - m.D


def x_layout(m: Model, board_clr: float = 0.5, dot_d: float = 4.0) -> dict:
    """Plan view across x.
    airQ: the panel's tail end on the user's left with its hatched block at the side wall (the
    dot needs the room right of the panel); the board against the right wall, so SW1, and the dot
    in front of it, sit right of the panel pocket; the SEN66 against the left wall, away from the
    antenna at the board's right rear. dot_left_margin < 0: the dot would cut the pocket's wall.
    Mini: the 60 mm board centred in the 62.4 mm interior; the SEN66 against the left wall; the
    light band's halves centred on their LED pairs."""
    r = _refs()
    mb = r["main"]
    inner = m.W / 2 - m.wall
    sen = (-inner + m.clr, -inner + m.clr + r["sen_l"])
    out = {"sen66": sen}
    if m.front == "panel":
        panel = (-inner + m.clr + r["block_out"], -inner + m.clr + r["block_out"] + r["panel_l"])
        x0 = inner - board_clr - mb["outline"][0]
        out.update(panel=panel, window_centre=panel[1] - r["va_far"] - r["va_w"] / 2)
    else:
        x0 = -mb["outline"][0] / 2
    dot = x0 + mb["button"]["actuator_center_x"]
    leds = [x0 + d["center_x"] for d in mb["leds"]["chain"]]
    ant = (x0 + mb["antenna"]["module_body"][0][0], x0 + mb["antenna"]["module_body"][1][0])
    out.update(board=(x0, x0 + mb["outline"][0]), board_side_gap=(x0 + inner, inner - x0 - mb["outline"][0]),
               dot=dot, leds=leds, usb=x0 + mb["usb_c"]["center_x"], antenna=ant,
               j7=(x0 + mb["fpc"]["center_x"] - 7.75, x0 + mb["fpc"]["center_x"] + 7.75),
               sen66_to_antenna_x=max(0.0, ant[0] - sen[1]))
    if m.front == "panel":
        out["dot_left_margin"] = dot - dot_d / 2 - (out["panel"][1] + m.clr + m.face_wall)
    else:
        half = 21.0
        co2 = ((leds[0] + leds[1]) / 2 - half / 2, (leds[0] + leds[1]) / 2 + half / 2)
        pm = ((leds[2] + leds[3]) / 2 - half / 2, (leds[2] + leds[3]) / 2 + half / 2)
        out.update(band_co2=co2, band_pm=pm, band_gap=pm[0] - co2[1],
                   dot_to_band=dot - dot_d / 2 - pm[1],          # >= face_wall: opaque wall between
                   window_room=co2[0] - (-inner) - 1.0)           # left of the CO2 half, 1 mm from the side wall
    return out


ALPHAS = (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60)


def study(m: Model = AIRQ) -> list[dict]:
    """Per tilt: the minimum depth, and the pose there."""
    rows = []
    for a in ALPHAS:
        d = min_depth(m, a)
        p = pose(replace(m, D=d + 0.01), a) if d is not None else None
        rows.append({"alpha": a, "min_D": d, "pose": p})
    return rows


def best(m: Model, rules: bool = True) -> dict | None:
    """The tilt with the smallest depth (rules: only poses that keep the zone order and take the
    USB-C through the rear wall)."""
    ok = [r for r in study(m) if r["pose"] is not None
          and (not rules or (r["pose"]["zone_order"] and r["pose"]["usb_rear"]))]
    return min(ok, key=lambda r: r["min_D"]) if ok else None


def min_lip(m: Model, depth: float, alpha_deg: float = 0, hi: float = 30.0) -> float | None:
    """Smallest vertical lower lip (to 0.01 mm) with which a pose at this tilt fits `depth`."""
    if (d := min_depth(replace(m, lip=hi), alpha_deg)) is None or d > depth:
        return None
    lo = 0.0
    while hi - lo > 0.01:
        mid = (lo + hi) / 2
        d = min_depth(replace(m, lip=mid), alpha_deg)
        if d is not None and d <= depth:
            hi = mid
        else:
            lo = mid
    return hi


def min_face_height(m: Model) -> float:
    """Smallest H (to 0.01 mm) whose front holds the airQ face (two slot rows, the LED slot, the
    panel) or the mini's (slots, labels, band)."""
    def fits(h):
        mm = replace(m, H=h)
        return (face_budget(mm) if m.front == "panel" else band_budget(mm))["spare"] >= 0
    lo, hi = 20.0, 80.0
    while hi - lo > 0.01:
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if fits(mid) else (mid, hi)
    return hi


def _fmt(p: dict, d: float) -> str:
    dot = f"dot f {p['dot_f']:.1f}" if p["dot_f"] is not None else "no dot on the push axis"
    return (f"D >= {d:.2f}  front edge y {p['front_edge'][0]:.1f} z {p['front_edge'][1]:.1f}  push {p['push_angle']:.0f} deg, {dot}"
            f"  USB z {p['usb_exit_z']:.1f} {'rear' if p['usb_rear'] else 'TOP'} well {p['usb_well']:.1f}"
            f"  lowest z {p['lowest_z']:.1f} {'ok' if p['zone_order'] else 'BELOW'} SEN66 top {p['sen_top']:.1f}"
            f"  antenna: {p['antenna_behind_front']:.1f} behind the front, {p['antenna_to_sen66']:.1f} from SEN66"
            + (f", hood {p['hood_out']:.1f} out" if p["hood_out"] > 0 else ""))


def options(m: Model, depth: float) -> list[dict]:
    """The minimum envelope for each kind of layout (the envelope's H is the larger of the model's
    H and the height its face needs). depth: the model's target depth, for the lip search."""
    out = []

    def row(name, mm, a):
        d = min_depth(mm, a)
        if d is None:
            out.append({"name": name, "alpha": a, "lip": mm.lip, "D": None})
            return
        p = pose(replace(mm, D=d + 0.01), a)
        h = max(mm.H, min_face_height(replace(mm, D=d)))
        out.append({"name": name, "alpha": a, "lip": mm.lip, "hood": mm.hood, "D": d, "H": h, "pose": p})

    row("horizontal", m, 0)
    b = best(m)
    row(f"tilted {b['alpha']} deg (smallest that keeps the rules)", m, b["alpha"])
    lip = min_lip(m, depth)
    if lip is not None:
        lip = math.ceil(lip * 2) / 2                     # rounded up to 0.5 mm
        row(f"lower lip {lip:g}, horizontal", replace(m, lip=lip), 0)
    row("rear antenna hood, horizontal", replace(m, hood=True), 0)
    lip = min_lip(replace(m, hood=True), depth)
    if lip is not None and lip > 0.01:
        lip = math.ceil(lip * 2) / 2
        row(f"hood + lower lip {lip:g}, horizontal", replace(m, hood=True, lip=lip), 0)
    return out


QUESTIONS = (("SEN66 lying flat (breaks Sensirion's rule)", dict(sen_pose="flat")),
             ("walls 1.6 everywhere", WALLS_16))


def answers(m: Model, depth: float) -> list[dict]:
    """What the owner's three questions buy: the horizontal and the best rule-keeping depth, the
    lower lip that would fit `depth` with a horizontal board, and the face's height."""
    qs = QUESTIONS + ((("tilt 25 deg", dict(tilt_deg=25.0)),) if m.front == "panel" else ())
    out = []
    for name, kw in (("as planned", {}),) + qs:
        mm = replace(m, **kw)
        b = best(mm)
        out.append({"name": name, "horizontal_D": min_depth(mm, 0), "best_alpha": b["alpha"] if b else None,
                    "best_D": b["min_D"] if b else None, "lip": min_lip(mm, depth), "face_H": min_face_height(mm)})
    return out


if __name__ == "__main__":
    for m, depth in ((AIRQ, 55.0), (MINI, 50.0)):
        print(f"######## {m.name}: {m.W} x {m.D} x {m.H}, tilt {m.tilt_deg}; face needs H >= {min_face_height(m):.2f}")
        for r in study(m):
            p = r["pose"]
            print(f"alpha {r['alpha']:2d}: " + (_fmt(p, r["min_D"]) if p else "no pose"))
        print("-- minimum envelopes")
        for o in options(m, depth):
            if o["D"] is None:
                print(f"{o['name']}: none")
                continue
            p = o["pose"]
            print(f"{o['name']}: {m.W:g} x {o['D']:.2f} x {o['H']:.2f}  " + _fmt(p, o["D"])
                  + f"  led f {p['led_f'] if p['led_f'] is None else round(p['led_f'], 1)}"
                  + f"  ant-SEN66 max {p['antenna_to_sen66_max']:.1f} rear {p['antenna_to_sen66_rear']:.1f} tongue fits {p['tongue_fits']}")
        print("-- questions")
        for a in answers(m, depth):
            print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in a.items()})
        print("outlet grille:", outlet_grille(m))
    for H in (48.0, 50.0):
        for kw in (dict(), dict(led_in_slot_row=True)):
            b = face_budget(replace(AIRQ, H=H), **kw)
            print(f"airq face H {H} {kw}: panel f {b['panel'][0]:.2f}..{b['panel'][1]:.2f} top {b['panel_top_max']:.2f} spare {b['spare']:.2f} open {b['open_area']:.1f}")
    print("mini band:", {k: (tuple(round(v, 2) for v in val) if isinstance(val, tuple) else (round(val, 2) if isinstance(val, float) else val)) for k, val in band_budget(MINI).items()})
    print("mini x:", {k: (tuple(round(v, 2) for v in val) if isinstance(val, (tuple, list)) else round(val, 2)) for k, val in x_layout(MINI).items()})
