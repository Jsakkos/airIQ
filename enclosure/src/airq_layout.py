"""airQ layout study (Plan 3 Task 3a, ruling R14): the side-section arithmetic behind
enclosure/README.md "airQ layout".

Pure Python (no SolidCraft, no numpy), so the fast tests and CI can rerun it:

    uv run --with pyyaml python enclosure/src/airq_layout.py

Frame (R3): y = 0 at the shell's front bottom edge, +y to the rear; z = 0 at the bottom plane.
The front face rises from (y 0, z 0) at `tilt` from vertical. Two face coordinates are used:
s = distance up the face from its bottom edge, t = depth behind the face's outer surface
(t = wall is the front wall's inner face).

The main board is a rigid section (layout frame Y: 0 at the rear edge, 30 at the front edge;
Z from the top face, the bottom face at -1.6) placed by its tilt `alpha` (front edge down) and
the device position F of its front-bottom corner. Every constraint is a half-plane in F, so a
pose is a 2-D linear feasibility problem: rear wall, top wall, the front (behind the panel, and
behind the light guide where the LEDs and J7 face it), and the SEN66 below the board with the
zone wall between (the SEN66's front-top corner at least `zone` below the board's bottom plane).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from functools import lru_cache

from sclib import mechanical


@lru_cache(maxsize=1)
def _refs() -> dict:
    """Sizes read from the reference generators and interface.yaml (not retyped)."""
    import ref_epd
    import ref_sen66
    sen, epd, m = ref_sen66.build(), ref_epd.build(), mechanical("main")
    return {"sen_l": sen.v("L"), "sen_w": sen.v("W"), "sen_h": sen.v("H"),
            "panel_l": epd.v("panel_l"), "panel_w": epd.v("panel_w"), "panel_t": epd.v("panel_t"),
            "block_out": epd.v("block_out"), "main": m}


@dataclass(frozen=True)
class Inputs:
    """Envelope and margins. Defaults: the plan's envelope and printing rules; the margins are
    the study's (each commented)."""
    W: float = 95.0
    D: float = 55.0
    H: float = 48.0
    tilt_deg: float = 30.0
    wall: float = 1.8            # plan default (>= 1.6)
    floor: float = 2.0           # plan: base plate
    zone_wall: float = 1.8       # the zone wall, a wall like any other
    zone_gap: float = 0.3        # air gap above the SEN66 and under the board
    clr: float = 0.2             # part-to-wall gap (clr_remove)
    foam: float = 1.0            # plan: the SEN66 sits on 1 mm foam
    bezel: float = 1.0           # window lip in front of the panel
    guide_t: float = 2.0         # light guide thickness in front of the LEDs (R20 coupon bar 3 x 2)
    sen_behind: float = 5.0      # behind the SEN66: cable plug (connector face) or outlet plenum
    grille_min_z: float = 10.0   # plan: no opening's lower edge below 10 mm
    slot_w: float = 1.2          # plan default slot width
    slot_bar: float = 1.6        # bar between slot rows and slots (>= 1.6, a wall)
    slot_len: float = 8.4        # one slot's length (8 slots + 7 bars = 80 mm per row)
    slot_row_len: float = 80.0   # grille row length across the face
    led_slot_h: float = 1.2      # the LED line's slot height on the face
    face_wall: float = 1.2       # solid face between slot band, LED slot and panel pocket
    usb_overmold: float = 7.0    # USB-C plug overmold height (typical 6.5-7.5; to confirm)

    @property
    def c(self) -> float:
        return math.cos(math.radians(self.tilt_deg))

    @property
    def s(self) -> float:
        return math.sin(math.radians(self.tilt_deg))


BEST_CASE = dict(wall=1.6, zone_wall=1.6, zone_gap=0.2, clr=0.2, bezel=1.0)


def t_of(i: Inputs, y: float, z: float) -> float:
    """Depth of (y, z) behind the front face's outer surface."""
    return y * i.c - z * i.s


def s_of(i: Inputs, y: float, z: float) -> float:
    """Distance of (y, z)'s foot up the front face from its bottom edge."""
    return y * i.s + z * i.c


def yz_of(i: Inputs, s: float, t: float) -> tuple[float, float]:
    return s * i.s + t * i.c, s * i.c - t * i.s


# --- the front face, bottom to top -------------------------------------------------------

def panel_top_max(i: Inputs) -> float:
    """Highest panel top edge (s): the panel's back corner (t = bezel + panel_t) stays clr under
    the top wall's inner face."""
    r = _refs()
    return (i.H - i.wall - i.clr + (i.bezel + r["panel_t"]) * i.s) / i.c


def face_budget(i: Inputs, rows: int = 2, led_in_slot_row: bool = False) -> dict:
    """Slots (rows of slot_w at slot_w + slot_bar pitch from the 10 mm line), the LED slot and
    the panel pocket, bottom to top. Returns the s positions, the spare length (< 0: does not
    fit) and the grille's open area. With led_in_slot_row the LED line takes the middle 30 mm of
    the top slot row (slots left and right of it), so the band holds both."""
    r = _refs()
    face = i.H / i.c
    lip = i.grille_min_z / i.c
    band_top = lip + rows * i.slot_w + (rows - 1) * i.slot_bar
    if led_in_slot_row:
        led = (band_top - i.slot_w, band_top)
        pocket = band_top + i.face_wall
    else:
        led = (band_top + i.face_wall, band_top + i.face_wall + i.led_slot_h)
        pocket = led[1] + i.face_wall
    panel = (pocket + i.clr, pocket + i.clr + r["panel_w"])
    per_row = i.slot_len * math.floor((i.slot_row_len + i.slot_bar) / (i.slot_len + i.slot_bar))
    side = (i.slot_row_len - 30.0 - 2 * i.slot_bar) / 2           # beside the 30 mm LED line
    per_side = i.slot_len * math.floor((side + i.slot_bar) / (i.slot_len + i.slot_bar))
    if led_in_slot_row:
        open_len = (rows - 1) * per_row + 2 * per_side
    else:
        open_len = rows * per_row
    return {"face": face, "lip": lip, "slot_band": (lip, band_top), "led": led, "panel": panel,
            "panel_top_max": panel_top_max(i), "spare": panel_top_max(i) - panel[1],
            "open_area": open_len * i.slot_w}


# --- the main board's section ------------------------------------------------------------

@lru_cache(maxsize=1)
def board_points() -> tuple:
    """(Y, Z, kind) corners of the board's side section (max over x), layout frame, from
    interface.yaml mechanical.main. kind: 'guide' = an LED or J7 face (the light guide and the
    FFC pass in front of it), 'panel' = must clear the panel's back, 'wall' = beside the panel
    (SW1 stands right of the panel, under the dot), 'bottom' = the board's bottom face."""
    m = _refs()["main"]
    board_d = m["outline"][1]          # 30: the front edge is at Y = board_d
    th = m["thickness"]
    mod = m["antenna"]["module_body"]
    j2, j3, j5 = m["j_sen66"]["body"], m["j_qwiic_tongue"]["body"], m["j_led_ext"]["body"]
    usb = m["usb_c"]
    btn = m["button"]
    mod_h, qwiic_h, led_h, fpc_h, sw_h, usb_len = 3.1, 2.9, 2.0, 2.0, 3.3, 7.35   # interface.yaml comments
    return (
        (mod[0][1], 0.0, "panel"), (mod[0][1], mod_h, "panel"), (mod[1][1], mod_h, "panel"),
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


def constraints(i: Inputs, alpha_deg: float) -> list[tuple[float, float, float, str]]:
    """Half-planes a_y * Fy + a_z * Fz <= b over the front-bottom corner F, named."""
    r = _refs()
    pts = [(offset(alpha_deg, Y, Z), kind) for Y, Z, kind in board_points()]
    tpb = i.bezel + r["panel_t"]
    need = {"guide": tpb + i.clr + i.guide_t + i.clr, "panel": tpb + i.clr,
            "wall": i.wall + i.clr, "bottom": i.wall + i.clr}
    out = [(1.0, 0.0, i.D - i.wall - i.clr - max(o[0] for o, _ in pts), "rear wall"),
           (0.0, 1.0, i.H - i.wall - i.clr - max(o[1] for o, _ in pts), "top wall")]
    # t(F + o) >= need  <=>  -c Fy + s Fz <= -(need - (o_y c - o_z s))
    k = max(need[kind] - (o[0] * i.c - o[1] * i.s) for o, kind in pts)
    out.append((-i.c, i.s, -k, "front (panel, light guide)"))
    # SEN66 at the rear, its front-top corner C at least `zone` below the board's bottom plane:
    # (C - F) . (-n) >= zone, n = (-sin a, cos a)
    a = math.radians(alpha_deg)
    sen_top = i.floor + i.foam + r["sen_w"]
    y_s0 = i.D - i.wall - i.sen_behind - r["sen_h"]
    zone = 2 * i.zone_gap + i.zone_wall
    # (y_s0 - Fy) sin a - (sen_top - Fz) cos a >= zone  <=>  Fy sin a - Fz cos a <= y_s0 sin a - sen_top cos a - zone
    out.append((math.sin(a), -math.cos(a), y_s0 * math.sin(a) - sen_top * math.cos(a) - zone, "SEN66 + zone wall"))
    return out


def feasible_region(i: Inputs, alpha_deg: float, eps: float = 1e-9) -> list[tuple[float, float]]:
    """Vertices of the feasible set of F (empty: no pose at this tilt)."""
    cons = constraints(i, alpha_deg)
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


def pose(i: Inputs, alpha_deg: float) -> dict | None:
    """The feasible pose with the highest front edge (the button highest on the face), and what
    it gives: front edge, button, USB-C plug axis, antenna end, lowest board point."""
    verts = feasible_region(i, alpha_deg)
    if not verts:
        return None
    fy, fz = max(verts, key=lambda v: (v[1], -v[0]))
    m = _refs()["main"]
    a = math.radians(alpha_deg)

    def dev(Y, Z):
        o = offset(alpha_deg, Y, Z)
        return fy + o[0], fz + o[1]

    btn = dev(m["button"]["actuator_tip_y"], m["button"]["actuator_center_z"])
    # SW1 is pushed along the board's -Y. A pusher reaching it from the face travels along
    # (-cos a, -sin a); its angle to the face's outward normal is alpha + tilt. At 90 deg the
    # axis runs along the face and no dot on the face can press the button.
    push_angle = alpha_deg + i.tilt_deg
    cos_push = math.cos(math.radians(push_angle))
    if cos_push > 0.5:                      # within 60 deg of the normal: a dot on the axis
        k = t_of(i, *btn) / cos_push
        dot = (btn[0] - k * math.cos(a), btn[1] - k * math.sin(a))
        dot_s, dot_gap = s_of(i, *dot), k - i.wall / cos_push
    else:
        dot_s = dot_gap = None
    mouth = dev(0.0, m["usb_c"]["shell"][1] / 2)
    # the plug comes in along +Y (toward the front): its axis runs back along (cos a, sin a)
    if math.cos(a) > 1e-9:
        kz = (i.D - mouth[0]) / math.cos(a)
        usb_exit_z = mouth[1] + kz * math.sin(a)
    else:
        usb_exit_z = math.inf
    pts = [dev(Y, Z) for Y, Z, _ in board_points()]
    ant = [dev(Y, Z) for Y in (m["antenna"]["module_body"][0][1], 0.0) for Z in (0.0, 3.1)]
    sen_top = i.floor + i.foam + _refs()["sen_w"]
    lowest = min(p[1] for p in pts)
    return {"alpha": alpha_deg, "F": (fy, fz), "front_edge": dev(30.0, 0.0),
            "button": btn, "push_angle": push_angle, "dot_s": dot_s, "dot_gap": dot_gap,
            "usb_mouth": mouth, "usb_exit_z": usb_exit_z,
            "usb_rear": usb_exit_z + i.usb_overmold / 2 <= i.H - i.wall,
            "antenna_end": dev(m["antenna"]["module_body"][0][1], 0.0),
            # depth of the antenna strip behind the panel's back face (t), where it is behind the panel
            "antenna_behind_panel": min(t_of(i, *p) for p in ant) - (i.bezel + _refs()["panel_t"]),
            "lowest_z": lowest, "sen_top": sen_top,
            # electronics zone high: no part of the board below the SEN66's top
            "zone_order": lowest >= sen_top}


def min_depth(i: Inputs, alpha_deg: float, lo: float = 50.0, hi: float = 80.0) -> float | None:
    """Smallest D (to 0.01 mm) at which a pose at this tilt exists."""
    if pose(replace(i, D=hi), alpha_deg) is None:
        return None
    while hi - lo > 0.01:
        mid = (lo + hi) / 2
        if pose(replace(i, D=mid), alpha_deg) is None:
            lo = mid
        else:
            hi = mid
    return hi


def horizontal_overflow(i: Inputs) -> float:
    """Horizontal board (alpha 0) as low as the zone wall allows and as far forward as the panel
    and light guide allow: how far its antenna end stands past the rear wall's inner face
    (> 0: through the wall)."""
    cons = {name: (a, b, c) for a, b, c, name in constraints(replace(i, D=200.0), 0.0)}
    sen_top = i.floor + i.foam + _refs()["sen_w"]
    fz = sen_top + 2 * i.zone_gap + i.zone_wall
    a, b, c = cons["front (panel, light guide)"]
    fy = (c - b * fz) / a                     # front constraint as an equality
    ant = fy + offset(0.0, _refs()["main"]["antenna"]["module_body"][0][1], 0.0)[0]
    return ant + i.clr - (i.D - i.wall)


def x_layout(i: Inputs, board_clr: float = 0.5, dot_d: float = 4.0) -> dict:
    """Plan view across x (any pose): the panel's tail end on the user's left with its hatched
    block at the side wall (the dot needs the room right of the panel); the board against the
    right wall (board_clr), so SW1, and the dot in front of it, sit right of the panel pocket;
    the SEN66 against the left wall, away from the antenna at the board's right rear.
    dot_left_margin < 0 means the dot (diameter dot_d) would cut into the panel pocket's wall."""
    import ref_epd
    r, e = _refs(), ref_epd.build()
    m = r["main"]
    inner = i.W / 2 - i.wall
    panel = (-inner + i.clr + r["block_out"], -inner + i.clr + r["block_out"] + r["panel_l"])
    window_c = panel[1] - e.v("va_far") - e.v("va_w") / 2
    x0 = inner - board_clr - m["outline"][0]
    dot = x0 + m["button"]["actuator_center_x"]
    ant = (x0 + m["antenna"]["module_body"][0][0], x0 + m["antenna"]["module_body"][1][0])
    sen = (-inner + i.clr, -inner + i.clr + r["sen_l"])
    return {"panel": panel, "window_centre": window_c, "dot": dot, "board": (x0, x0 + m["outline"][0]),
            "dot_left_margin": dot - dot_d / 2 - (panel[1] + i.clr + i.face_wall),
            "leds": [x0 + d["center_x"] for d in m["leds"]["chain"]],
            "j7": (x0 + m["fpc"]["center_x"] - 7.75, x0 + m["fpc"]["center_x"] + 7.75),
            "usb": x0 + m["usb_c"]["center_x"], "antenna": ant, "sen66": sen,
            "sen66_to_antenna_x": ant[0] - sen[1]}


ALPHAS = (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60)


def study(i: Inputs = Inputs()) -> list[dict]:
    """Per tilt: the minimum depth, and the pose there (button, USB-C, lowest board point)."""
    rows = []
    for a in ALPHAS:
        d = min_depth(i, a)
        p = pose(replace(i, D=d + 0.01), a) if d is not None else None
        rows.append({"alpha": a, "min_D": d, "pose": p})
    return rows


if __name__ == "__main__":
    for name, inp in (("default margins", Inputs()), ("best case (walls 1.6, gaps 0.2)", Inputs(**BEST_CASE))):
        print(f"== {name}: horizontal board's antenna end past the rear wall at D 55: "
              f"{horizontal_overflow(inp):.2f} mm")
        for r in study(inp):
            p = r["pose"]
            if p is None:
                print(f"alpha {r['alpha']:2d}: no pose up to D 80")
                continue
            dot = f"dot s {p['dot_s']:.1f}" if p["dot_s"] is not None else "no dot on the push axis"
            print(f"alpha {r['alpha']:2d}: D >= {r['min_D']:.2f}  front edge y {p['front_edge'][0]:.1f} z {p['front_edge'][1]:.1f}"
                  f"  push {p['push_angle']:.0f} deg, {dot}  USB exit z {p['usb_exit_z']:.1f} {'rear' if p['usb_rear'] else 'TOP'}"
                  f"  lowest board z {p['lowest_z']:.1f} {'ok' if p['zone_order'] else 'BELOW'} SEN66 top"
                  f"  antenna {p['antenna_behind_panel']:.1f} behind panel")
    rec = Inputs(D=63.5, H=50.0)
    p = pose(rec, 0)
    print(f"== recommended: 95 x {rec.D} x {rec.H}, horizontal board: F {p['F']}, button {p['button']}, "
          f"dot s {p['dot_s']:.2f} gap {p['dot_gap']:.2f}, USB mouth {p['usb_mouth']}, antenna end {p['antenna_end']}")
    print("   x layout:", {k: (tuple(round(v, 2) for v in val) if isinstance(val, (tuple, list)) else round(val, 2))
                          for k, val in x_layout(rec).items()})
    for H in (48.0, 50.0):
        for led_row in (False, True):
            b = face_budget(Inputs(H=H), led_in_slot_row=led_row)
            print(f"face H {H}: LED in slot row {led_row}: panel s {b['panel'][0]:.2f}..{b['panel'][1]:.2f} "
                  f"(max {b['panel_top_max']:.2f}, spare {b['spare']:.2f}); intake open {b['open_area']:.1f} mm2")
