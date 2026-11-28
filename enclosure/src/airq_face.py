"""airq_face: the airQ's shell face (Plan 3 Task 3b-1): window, panel pocket, LED slot, dot and flexure.

Everything here is a shell feature (or a part that rides in the shell). Positions are the face
parameters that `airq.py` fixed in 3a (panel_x0, panel_s0, led_f0, dot_f, ...); this module adds the
sizes the features need and cuts them. Face frame: x as the world, s up the slope from the crease
(z = lip), t into the case from the slope's outer surface (R3, `enclosure_common`).
"""
from __future__ import annotations

import math

import board_sources as B
import enclosure_common as C
import ref_epd
import ref_fpc_adapter
from sclib import Script

MAIN = B.MAIN


def slope_plane(s: Script) -> dict:
    """The sketch plane parallel to the face: x along the world x, y up the slope. The origin is
    the world origin, so a point at slope distance `sv` is at y = sv + lip * cos_t, and an offset
    of `lip * sin_t - t` is the plane `t` deep behind the face (as `enclosure_common.panel_pocket`)."""
    return {"origin": [0, 0, 0], "x_dir": [1, 0, 0], "y_dir": [0, s.v("sin_t"), s.v("cos_t")]}


def ys(sv: str) -> str:
    """Sketch y of the slope distance `sv` (an expression)."""
    return f"({sv}) + lip * cos_t"


def toff(t: str) -> str:
    """Sketch plane offset of the plane `t` deep behind the face (t negative: in front of it)."""
    return f"lip * sin_t - ({t})"


def face_pt(s: Script, x: float, sv: float, t: float = 0.0) -> list[float]:
    """World point of face coordinates (x, s, t), for edge picks."""
    sn, c, lip = s.v("sin_t"), s.v("cos_t"), s.v("lip")
    return [x, sv * sn + t * c, lip + sv * c - t * sn]


def window_params(s: Script) -> None:
    """The screen window: the panel's active area (ref_epd aa_*), 66.90 x 29.06, 3.00 from the far
    end and 3.82 from the long edges, with a crisp chamfer on its outer edge."""
    epd = ref_epd.build().v
    p = s.param
    p("aa_w", epd("aa_w"), "panel active area along the length (ref_epd aa_w)")
    p("aa_h", epd("aa_h"), "panel active area across (ref_epd aa_h)")
    p("aa_far", epd("aa_far"), "active area to the end away from the tail (ref_epd aa_far)")
    p("aa_edge", epd("aa_edge"), "active area to each long edge (ref_epd aa_edge)")
    p("win_x0", "panel_x0 + panel_l - aa_far - aa_w", "screen window: the active area's tail-side edge, x")
    p("win_x1", "win_x0 + aa_w", "screen window: far-side edge, x")
    p("win_s0", "panel_s0 + aa_edge", "screen window: lower edge, up the slope from the crease")
    p("win_s1", "win_s0 + aa_h", "screen window: upper edge")
    p("win_chamfer", 0.5, "screen window: chamfer on the outer edge (bezel is 1.0, so 0.5 leaves a 0.5 land at the panel)")


def window(s: Script) -> None:
    """The screen window through the bezel over the active area, then its crisp chamfer."""
    with s.sketch("Window outline", slope_plane(s), offset=toff("-1")) as sk:
        sk.rect("win_x0", ys("win_s0"), "win_x1", ys("win_s1"))
    s.extrude("Window", "Window outline", "bezel + 1 + 0.5", operation="cut", targets=["shell"], direction="negative")
    v = s.v
    xm, sm = (v("win_x0") + v("win_x1")) / 2, (v("win_s0") + v("win_s1")) / 2
    picks = [face_pt(s, xm, v("win_s0")), face_pt(s, xm, v("win_s1")),
             face_pt(s, v("win_x0"), sm), face_pt(s, v("win_x1"), sm)]
    s.chamfer("Window chamfer", picks, "win_chamfer", body="shell")


# --- FFC route (feature 2) -----------------------------------------------------------------------

def ffc_geometry(v, s_c3: float) -> dict:
    """The FFC's seated route in the face frame (x, s, t), for the jog centre `s_c3` (the S3 run's
    centre line, up the slope from the crease). `v` evaluates the design's parameters.

    Route, as a paper model: from the adapter's FFC mouth (layer A, width up the slope) the ribbon
    runs +x to crease 1, a 45 degree fold turns it down the slope (layer B, across the strip
    between crease 1 and crease 2); crease 2 turns it +x again (layer C), which passes behind the
    D1/D2 light guide leg under the LEDs; crease 3, under J7's strip, turns it up the slope (layer
    D) and it bends (r >= ffc_r, centre line) up and over to leave horizontally into J7's mouth.
    Three creases: the contacts side ends up on the other face (see `ffc_pin_outcome`)."""
    sn, c, lip = v("sin_t"), v("cos_t"), v("lip")
    w, r, pitch = v("ffc_w"), v("ffc_r"), v("ffc_pitch")
    t_a = v("ffc_t_a")
    t_b, t_c = t_a + pitch, t_a + 2 * pitch
    t_d = t_b                                                      # crease 3 folds the flap to the front of layer C
    x_m, s_a = v("ffc_x_m"), v("adapter_s")
    x_c1, x_c3 = v("ffc_x_c1"), v("ffc_xc")
    y_m, z_m = v("board_y0"), v("ffc_z_j7")
    yz = lambda sv, tv: (sv * sn + tv * c, lip + sv * c - tv * sn)   # noqa: E731
    p_c = yz(s_c3, t_d)                                            # crease 3's centre, on layer D
    h = math.pi / 2 - v("tilt_deg")                                # the slope's heading in (y, z): 60 degrees (v gives angles in radians)
    l_h = v("ffc_lh")
    # arc 1 (CCW from the slope's heading to vertical, radius r), vertical run, arc 2 (CW to +y), run into the mouth
    k = math.radians(90) - h                                       # arc 1's turn
    a1_y = lambda b0y: b0y + r * (1 - math.sin(h))                 # noqa: E731  end of arc 1 (y), heading 90 degrees
    # B0.y from the mouth: A2.y + r = y_m - l_h, A2.y = A1.y
    b0_y = y_m - l_h - r - r * (1 - math.sin(h))
    u = (b0_y - p_c[0]) / sn                                       # crease 3 to B0 along the slope
    b0 = (b0_y, p_c[1] + u * c)
    a1 = (a1_y(b0_y), b0[1] + r * math.cos(h))
    l_v = z_m - r - a1[1]
    arc1, arc2 = r * k, r * math.pi / 2
    s1 = x_c1 - x_m
    flap = s_a - s_c3
    s3 = x_c3 - x_c1
    d_len = u + arc1 + l_v + arc2 + l_h
    creases = 3 * v("ffc_crease")
    return {"t": {"a": t_a, "b": t_b, "c": t_c, "d": t_d}, "p_c": p_c, "b0": b0, "a1": a1, "u": u, "l_v": l_v, "k": k, "h": h,
            "s1": s1, "flap": flap, "s3": s3, "d": d_len, "creases": creases,
            "centre_len": s1 + flap + s3 + d_len + creases, "s_c3": s_c3, "x_c1": x_c1, "x_c3": x_c3,
            "arc1": arc1, "arc2": arc2}


def ffc_params(s: Script) -> None:
    """The FFC's parameters and the numbers of its route (see `ffc_geometry`). The jog depth
    `ffc_s_c3` is sized so the route uses the bought length `ffc_len` (a longer jog is a longer
    route). The jog (`_jog_limits`) takes the route from 63.8 to 68.1 mm, so with 3.5 inserted an FFC of
    70.8 ... 75.1 mm fits; 73 fits at both ends of its +-1 mm and of the insertion's +-0.5 (R49), and no
    common stock length (50, 60, 70, 80, 100 mm) does."""
    epd, ad = ref_epd.build().v, ref_fpc_adapter.build().v
    p = s.param
    p("ffc_w", epd("tail_w"), "FFC width: the panel tail's narrow part, 24 x 0.5 + the margins (ref_epd tail_w)")
    p("ffc_t", 0.3, "FFC thickness (task: 12.5 wide, 0.3 thick)")
    p("ffc_r", 1.3, "FFC bend radius of the centre line: inner radius 1.15 >= 1.0 (task)")
    p("ffc_pitch", "ffc_t", "FFC layers' pitch where the ribbon is folded over itself: the layers touch (a fold has no air)")
    p("ffc_slot_h", 1.0, "FFC slot height above the board: J7 and, as a placeholder, the adapter's ZIF (hardware/README: about 1 mm above the board)")
    p("ad_pcb_t", ad("pcb_t"), "FPC adapter board thickness (ref_fpc_adapter pcb_t; placeholder)")
    p("ffc_t_a", "adapter_t - ad_pcb_t - ffc_slot_h", "FFC layer A (leaving the adapter), depth behind the face")
    p("ffc_x_m", "adapter_x + ad_l / 2", "FFC mouth on the adapter's ZIF: its +x end")
    p("ffc_xc", "(j7_x0 + j7_x1) / 2", "FFC centre line into J7: J7's centre x")
    p("ffc_x_gap", 2.0, "FFC: air from the adapter's mouth to crease 1's strip")
    p("ffc_x_c1", "ffc_x_m + ffc_w / 2 + ffc_x_gap", "FFC creases 1 and 2: the centre of their strip, x")
    p("ffc_z_j7", "board_z0 + board_t + ffc_slot_h", "FFC slot level in J7: z")
    p("ffc_lh", 1.5, "FFC horizontal run into J7's mouth after the last bend")
    p("ffc_crease", 0.5, "FFC length used by each fold (folded flat over itself)")
    p("ffc_insert", 3.5, "FFC length inserted in each connector: about 3.5 mm goes inside J7 (hardware/README.md, 'E-ink FPC fit (airQ)', the reach analysis, lines 167 and 176; FPC-05FB-24PH20 back-flip); the adapter's ZIF is taken alike")
    p("ffc_len_tol", 1.0, "FFC length tolerance, +-: the vendor's (typically +-1 mm; to confirm). The folds are made once at assembly over a jig, so the jog depth takes it up (R42, R49); no bow is needed")
    p("ffc_insert_tol", 0.5, "FFC insertion per connector, +-: the reach analysis' 'about 3.5 mm' taken as 3.0 ... 4.0 (the test's bounds); the jog takes it too")
    v = s.v
    s_c3 = ffc_fit(v, v("ffc_len"), v("ffc_insert"))
    if s_c3 is None:
        lo, hi = ffc_route_range(v)
        raise ValueError(f"the FFC's route ({v('ffc_len') - 2 * v('ffc_insert'):.1f}) is outside what the jog can take ({lo:.1f} ... {hi:.1f})")
    p("ffc_s_c3", math.ceil(s_c3 * 1000) / 1000, "FFC run C (behind the guide's legs, under the LEDs): its centre line up the slope; sized in airq_face.ffc_params so the route fits ffc_len")


def ffc_route_range(v) -> tuple[float, float]:
    """The shortest and longest seated route (centre line) the fold jog can take: the C run at its highest
    and at its lowest place (`_jog_limits`)."""
    lo, hi = _jog_limits(v)
    return ffc_geometry(v, hi)["centre_len"], ffc_geometry(v, lo)["centre_len"]


def ffc_len_window(v) -> tuple[float, float]:
    """R57: the nominal FFC lengths to order, (shortest, longest), whose every corner (the length +- ffc_len_tol, each
    insertion +- ffc_insert_tol) the jog takes: the route's range less the tolerances. It moves with the clearances
    (the board's place follows clr_remove), so the FFC is ordered after the coupons: set ffc_len inside it."""
    r_min, r_max = ffc_route_range(v)
    lo = r_min + v("ffc_len_tol") + 2 * (v("ffc_insert") + v("ffc_insert_tol"))
    hi = r_max - v("ffc_len_tol") + 2 * (v("ffc_insert") - v("ffc_insert_tol"))
    return lo, hi


def ffc_fit(v, length: float, insert: float) -> float | None:
    """The jog centre `s_c3` that makes the seated route take an FFC of `length` inserted `insert` at each end
    (the route lengthens 2 mm per mm the jog deepens), or None if no jog inside `_jog_limits` does."""
    lo, hi = _jog_limits(v)
    target = length - 2 * insert
    r_min, r_max = ffc_route_range(v)
    if not r_min <= target <= r_max:
        return None
    a, b = lo, hi                                   # bisect: the route at a is >= target, at b <= target
    for _ in range(60):
        m = (a + b) / 2
        if ffc_geometry(v, m)["centre_len"] > target:
            a = m
        else:
            b = m
    return b


def _jog_limits(v) -> tuple[float, float]:
    """The lowest and highest centre line of the C run (up the slope): its lower edge stays 0.3 mm
    above the ledge's top (z = lip); its upper edge stays 0.3 under the LED faces' lower edge, and
    crease 3's far corner (s_c3 + ffc_w / 2, on layer D's +x edge) must not pass the line where layer D's
    bend over to J7 starts (`ffc_s_b0`): past it the fold would lie in the bend (R49; the second bound is
    the tighter, 11.96 against 17.0)."""
    sn, c, lip = v("sin_t"), v("cos_t"), v("lip")
    t_c = v("ffc_t_a") + 2 * v("ffc_pitch")
    t_d = v("ffc_t_a") + v("ffc_pitch")
    hw = v("ffc_w") / 2
    led_lo = v("board_y0") * sn + (v("led_z") - 1.0 - lip) * c      # the LED faces' lower edge, up the slope
    s_b0 = (v("board_y0") - v("ffc_lh") - v("ffc_r") * (2 - c) - t_d * c) / sn   # as the parameter ffc_s_b0
    hi = min(led_lo - 0.3 - hw, s_b0 - hw)
    lo = (0.3 + t_c * sn) / c + hw                                   # lower edge's z = lip + 0.3 (t_c deep)
    return lo, hi


def ffc_derived_params(s: Script) -> None:
    """Layer depths and where layer D's straight run ends (B0), as parameters, after `ffc_s_c3`."""
    p = s.param
    p("ffc_t_b", "ffc_t_a + ffc_pitch", "FFC layer B (between crease 1 and 2), depth behind the face")
    p("ffc_t_c", "ffc_t_b + ffc_pitch", "FFC layer C (the run under the LEDs), depth behind the face")
    p("ffc_t_d", "ffc_t_b", "FFC layer D (after crease 3, folded to the front of C), depth behind the face")
    p("ffc_service_dz", 12.0, "service lift of the shell over its seat while the FFC is plugged in J7 and in the adapter: enough to reach the adapter's ZIF with a finger (judgement, to confirm on the prototype); the shortest FFC (72 mm, 4.0 inserted) keeps 3.2 mm over the allowance (R49); the floor bosses are still in the zone wall's notches, so the shell stays guided; see airq_face.ffc_service")
    p("ffc_service_margin", 2.0, "FFC service lift: the chain must be this much longer than the straight distance (the bends and the fold's thickness)")
    p("ffc_s_b0", "(board_y0 - ffc_lh - ffc_r * (2 - cos_t) - ffc_t_d * cos_t) / sin_t",
      "FFC layer D's straight run ends here (up the slope): where the bend over to J7's mouth starts")


def adapter_holder_params(s: Script) -> None:
    ad = ref_fpc_adapter.build().v
    p = s.param
    p("ad_w", ad("pcb_w"), "FPC adapter board across the slope (ref_fpc_adapter pcb_w; placeholder)")
    p("hold_w", 3.0, "adapter holder: arm width up the slope")
    p("hold_t0", "adapter_t - ad_pcb_t - 0.5", "adapter holder: front face, 0.5 in front of the board's front face (beside the ZIFs' root)")
    p("hold_t1", "adapter_t - 0.4", "adapter holder: back face, 0.45 in front of the zone wall's slant")
    p("hold_s0", "adapter_s + ad_w / 2 + clr_remove", "adapter holder: arm's lower edge, clr_remove over the board's upper edge")
    p("hold_s1", "hold_s0 + hold_w", "adapter holder: arm's upper edge")
    p("hold_x0", "-inner_x - 0.5", "adapter holder: the arm runs in from the side wall (joined 0.5 into it)")
    p("hold_x1", "adapter_x + ad_l / 2", "adapter holder: the arm ends over the board's -x end... its +x end (the FFC leaves below it)")


def adapter_holder(s: Script) -> None:
    """The adapter's holder, part of the shell: an arm from the left side wall over the board's upper
    long edge (clr_remove over it), behind the board's front face, along the board's whole length.
    It stops the board from sliding up the slope and turning (the ZIF and the tail locate it in x and
    hold it down the slope), and the zone wall's slant is the back stop (0.45 gap to the arm, 0.25
    to the board). It is above the cables' strip (airq cable_params fills the space under it and the
    zone wall's drawer fills the rest below), so the shell lowers past the cables with it, and there
    is no arm below the board. The arm hangs free of the face wall (the pocket has no wall behind the
    panel): it prints with support, reached from the shell's open bottom before the panel goes in."""
    with s.sketch("Holder arm outline", slope_plane(s), offset=toff("hold_t0")) as sk:
        sk.rect("hold_x0", ys("hold_s0"), "hold_x1", ys("hold_s1"))
    s.extrude("Holder arm", "Holder arm outline", "hold_t1 - hold_t0", operation="join", targets=["shell"], direction="negative")


def ffc_pin_outcome() -> dict:
    """Which face of the FFC arrives up in J7, and which end of J7 pin 1 is on, by following the
    ribbon's frame (travel d, toward pin 1 p, contacts' face n) through the route in the face frame
    (x, s, t). A fold (crease) turns the ribbon by 180 deg about its crease line in the plane: it
    mirrors d and p across the line and turns the face over (n -> -n); a bend turns all three about
    x. Start: the ZIF the panel's tail enters and the FFC leaves, both 1:1 and on the same side of the
    adapter (placeholder, to confirm): the tail folded 180 deg behind the panel arrives contacts away
    from the panel (+t), travelling +x, pin 1 on its pin-1 long edge (+s); the FFC leaves in the same
    frame. Returns {contacts_up, pin1_x, mirrored} at J7 (travel +y)."""
    import math as m
    s2 = 1 / m.sqrt(2)

    def refl(vec, u):                        # 2-D mirror of (x, s) across the line along u
        dot = vec[0] * u[0] + vec[1] * u[1]
        return (2 * dot * u[0] - vec[0], 2 * dot * u[1] - vec[1])
    d, p, n = (1.0, 0.0), (0.0, 1.0), 1.0     # d, p in (x, s); n: +1 = +t, -1 = -t
    for line in ((s2, -s2), (s2, -s2), (s2, s2)):      # crease 1: +x -> -s, crease 2: -s -> +x, crease 3: +x -> +s
        d, p, n = refl(d, line), refl(p, line), -n
    assert (round(d[0]), round(d[1])) == (0, 1)        # travelling up the slope
    # to the world (x, y, z): x -> x, s -> (0, sin, cos), t -> (0, cos, -sin); the bends turn about x
    # from the slope's heading (90 - tilt in (y, z)) to +y: by -(90 - tilt)
    tilt = math.radians(MODEL_TILT)
    sn, c = math.sin(tilt), math.cos(tilt)

    def world(xs, nn):                                  # p (x, s) and n (the +t sign) -> world vectors
        return (xs[0], xs[1] * sn - 0.0, xs[1] * c), (0.0, nn * c, -nn * sn)
    pw, nw = world(p, n)
    phi = -(math.pi / 2 - tilt)
    rot = lambda vec: (vec[0], vec[1] * math.cos(phi) - vec[2] * math.sin(phi), vec[1] * math.sin(phi) + vec[2] * math.cos(phi))  # noqa: E731
    pw, nw = rot(pw), rot(nw)
    up = nw[2] > 0.5
    pin1_x = 1 if pw[0] > 0.5 else -1
    # J7 (interface.yaml mechanical.main.fpc.pin_order): contacts up -> pin i on pin i, pin 1 at the viewer's right (+x)
    mirrored = not (up and pin1_x > 0)
    return {"creases": 3, "contacts_up": up, "pin1_x": pin1_x, "mirrored": mirrored}


MODEL_TILT = 30.0     # the face's tilt from vertical (airq.MODEL; the plan's 30 deg), for the outcome's frame turn


def ffc_path(v, g: dict, n_arc: int = 8) -> list[tuple[float, float, float]]:
    """The centre line of layer D's bend over to J7 in (y, z) with its tangent angle: from B0
    (heading `h`), arc 1 CCW to vertical, the vertical run, arc 2 CW to +y, then the run into the
    mouth. Samples (y, z, angle)."""
    r, h, k = v("ffc_r"), g["h"], g["k"]
    pts = [(g["b0"][0], g["b0"][1], h)]
    c1 = (g["b0"][0] - r * math.sin(h), g["b0"][1] + r * math.cos(h))
    for i in range(1, n_arc + 1):
        th = h + k * i / n_arc
        pts.append((c1[0] + r * math.sin(th), c1[1] - r * math.cos(th), th))
    a1 = pts[-1]
    a2 = (a1[0], a1[1] + g["l_v"], math.pi / 2)
    pts.append(a2)
    c2 = (a2[0] + r, a2[1])
    for i in range(1, n_arc + 1):
        th = math.pi / 2 * (1 - i / n_arc)
        pts.append((c2[0] - r * math.sin(th), c2[1] + r * math.cos(th), th))
    e = pts[-1]
    pts.append((v("board_y0") - 0.01, e[1], 0.0))
    return pts


def ffc_service(v, g: dict, dz: float, length: float | None = None, insert: float | None = None) -> dict:
    """The FFC with the shell lifted `dz` along +z while the FFC stays plugged in J7: the straight
    distance from crease 3's centre (which stays near J7) to the adapter's mouth lifted by dz, against
    the chain's length (S1, the flap, S3, creases 1 and 2) plus the spare the bought length leaves.
    `length` and `insert` default to ffc_len and ffc_insert (pass a tolerance end, with its jog `g`)."""
    length = v("ffc_len") if length is None else length
    insert = v("ffc_insert") if insert is None else insert
    sn, c, lip = v("sin_t"), v("cos_t"), v("lip")
    yz = lambda sv, tv: (sv * sn + tv * c, lip + sv * c - tv * sn)   # noqa: E731
    m0 = yz(v("adapter_s"), g["t"]["a"])
    c3 = yz(g["s_c3"], g["t"]["d"])
    mouth = (v("ffc_x_m"), m0[0], m0[1] + dz)
    crease = (g["x_c3"], c3[0], c3[1])
    d = math.dist(mouth, crease)
    spare = length - 2 * insert - g["centre_len"]
    chain = g["s1"] + g["flap"] + g["s3"] + 2 * v("ffc_crease") + spare
    return {"d_lift": d, "chain": chain, "spare": spare, "ok": d + v("ffc_service_margin") <= chain}


# --- LED slot, light guide, crease seal (feature 3) --------------------------------------------

def yz(sv: str, tv: str) -> tuple[str, str]:
    """World (y, z) of the face point (s, t), as expressions."""
    return f"({sv}) * sin_t + ({tv}) * cos_t", f"lip + ({sv}) * cos_t - ({tv}) * sin_t"


def guide_params(s: Script) -> None:
    """The LED line's slot, the clear light guide behind it and the foam strip that plugs the crease's
    parting line (the shell lands at z = lip + crease_gap over the lip's top at z = lip)."""
    leds = MAIN["leds"]["chain"]
    p = s.param
    p("led_x0", "window_xc - led_len / 2", "LED slot: tail-side end, x (the 30 mm line centred on the window)")
    p("led_x1", "window_xc + led_len / 2", "LED slot: far end, x")
    p("led_s0", "led_f0 - lip", "LED slot: lower edge, up the slope from the crease")
    p("led_s1", "led_s0 + led_h_slot", "LED slot: upper edge")
    p("led_face_w", B.led_body_w(), "LED light face width (interface.yaml leds comment, board_sources)")
    p("led_face_h", B.led_body_h(), "LED light face height (interface.yaml leds comment: the LED's body height)")
    for i, led in enumerate(leds, 1):
        p(f"led_d{i}_x", f"board_x0 + {led['center_x']}", f"D{i} light face centre, x (interface.yaml leds chain)")
    p("gd_clr", "clr_remove", "light guide: air between its entry faces and the LED faces (it comes down with the shell past them) and to the shell (clr_remove)")
    p("gd_t0", "bezel + panel_t + gd_pad", "light guide: front face, the adhesive pad (gd_pad) behind the panel's back face")
    p("gd_t1", "gd_t0 + guide_t", "light guide: back face (guide_t thick, the coupon's 2 mm bar)")
    p("gd_sg", "(0.4 + gd_t0 * sin_t) / cos_t", "light guide: where its bottom turning facet starts on the front face: its lowest point, 0.4 above the lip's top")
    p("gd_s0", "gd_sg + guide_t", "light guide: where the bottom 45 degree facet meets the back face (TIR: light going down the leg turns toward the slot)")
    p("gd_top_z", "led_z + led_face_h / 2", "light guide: its top, at the LED faces' top edge (no surface above it sees over the LEDs)")
    p("gd_s_up", 7.0, "light guide: the bar's top; the legs go on from here")
    p("gd_y_e", "board_y0 - gd_clr", "light guide: entry faces' plane, gd_clr in front of the LED faces")
    p("gd_tb", "(gd_y_e - (gd_top_z - lip) * sin_t / cos_t) * cos_t", "light guide foot: depth of the entry plane at the faces' top edge")
    p("gd_sb", "(gd_top_z - lip + gd_tb * sin_t) / cos_t", "light guide foot: slope position there")
    p("gd_sf", "gd_sb - (gd_tb - gd_t0) * cos_t / sin_t", "light guide foot: where the front face turns into the turning facet (a plane at the tilt to the slope: light from the LED, going -t and -s, meets it at 60 degrees, over PETG's 39.6 critical angle, and turns down the leg)")
    p("gd_tc", "(gd_y_e - (led_z - led_face_h / 2 - lip) * sin_t / cos_t) * cos_t", "light guide foot: depth of the entry plane at the faces' lower edge")
    p("gd_sc", "(led_z - led_face_h / 2 - lip + gd_tc * sin_t) / cos_t", "light guide foot: slope position there")
    p("gd_l2x0", "led_d3_x - led_face_w / 2 - gd_clr", "LED mask over D3 and D4 (R45): tail-side face")
    p("gd_l2x1", "led_d4_x + led_face_w / 2 + gd_clr", "LED mask over D3 and D4: far face")
    p("mask_mz", 0.6, "LED mask: beyond the LED faces' top and lower edges")
    p("gd_win_xm", 0.4, "light guide: each foot (its bare entry face) starts this far inside its LED face's tail-side (-x) edge (a line to U4, at -x, drifts that way over the 0.2 gap and the LED's depth)")
    p("gd_win_xp", 0.2, "light guide: each foot stops this far inside its LED face's far (+x) edge")
    p("gd_l1x0", "led_d1_x - led_face_w / 2 + gd_win_xm", "light guide: D1/D2 leg, tail-side face: inside D1's face by gd_win_xm, so a line from the leg toward U4 (at -x) enters D1's body")
    p("gd_l1x1", "led_d2_x + led_face_w / 2 - gd_win_xp", "light guide: D1/D2 leg, far face: inside D2's face by gd_win_xp")
    p("gd_la_x1", "led_d1_x + led_face_w / 2 - gd_win_xp", "light guide: D1 foot's far face")
    p("gd_lb_x0", "led_d2_x - led_face_w / 2 + gd_win_xm", "light guide: D2 foot's tail-side face (no guide face over the gap between D1 and D2, where a line to U4 would pass between the LEDs)")
    p("stop_s0", "gd_sf - 3", "gap stop (R50): its lower end up the slope, 3 below the D2 foot's facet (the lines to U4 it stops leave the D2 foot's tail-side face above gd_sf)")
    p("gd_tg", "clr_align", "light guide: the tongue's clearance to the slot on each side (clr_align: located part)")
    p("gd_rec", "clr_remove + 0.1", "light guide: the tongue's front face is this far behind the face")
    p("crease_y0", 0.12, "crease seal: front edge, flush with the shell's outer face at its lower edge (the foam plugs the parting line over the lip's top from the outside: 1.7 of foam)")
    p("crease_squeeze", 0.1, "crease seal: foam tape crease_gap + this thick before it is pressed (R9: the check sets 0)")


def led_slot(s: Script) -> None:
    """The LED slot through the face wall: the 30 mm line under the screen."""
    with s.sketch("LED slot outline", slope_plane(s), offset=toff("-1")) as sk:
        sk.rect("led_x0", ys("led_s0"), "led_x1", ys("led_s1"))
    s.extrude("LED slot", "LED slot outline", "wall + 1 + 0.2", operation="cut", targets=["shell"], direction="negative")


def _guide_poly(s: Script, name: str, pts, x0: str, x1: str, first: bool) -> None:
    """A guide piece: a polygon in the face's (s, t) plane (expressions), extruded along x from x0 to x1."""
    with s.sketch(f"{name} profile", "YZ", offset=x0) as sk:
        sk.polyline([yz(sv, tv) for sv, tv in pts])
    if first:
        s.extrude(name, f"{name} profile", f"({x1}) - ({x0})", body="light_guide")
    else:
        s.extrude(name, f"{name} profile", f"({x1}) - ({x0})", operation="join", targets=["light_guide"])


def guide_profile_pts() -> dict:
    """The guide's cross-section pieces in (s, t) as expressions, one source for the build and the
    checks: `tongue` (in the slot, continuous with the bar's bottom), `low` (the bar with its bottom
    turning facet), `leg` (up to the foot with its turning facet and the entry plane)."""
    tr, tl = "led_s1 - gd_tg", "led_s0 + gd_tg"
    return {
        "tongue": [(tl, "gd_rec"), (tr, "gd_rec"), (tr, "gd_t0 + 0.1"), ("gd_sg", "gd_t0 + 0.1")],
        "low": [("gd_sg", "gd_t0"), ("gd_s_up", "gd_t0"), ("gd_s_up", "gd_t1"), ("gd_s0", "gd_t1")],
        "leg": [("gd_s_up - 0.1", "gd_t0"), ("gd_sf", "gd_t0"), ("gd_sb", "gd_tb"), ("gd_sc", "gd_tc"), ("gd_sc", "gd_t1"), ("gd_s_up - 0.1", "gd_t1")],
    }


def guide_pieces() -> list[tuple[str, str, str, str]]:
    """The guide's pieces as built: (feature name, `guide_profile_pts` key, x0, x1), each a prism of its
    (s, t) profile along x. One source for the build and the checks (`airq_check.guide_delivery`,
    `airq_check.guide_surface_sight`)."""
    x0, x1 = "led_x0 + gd_tg", "led_x1 - gd_tg"
    return [("Guide tongue", "tongue", x0, x1), ("Guide low", "low", x0, x1),
            ("Guide leg 1", "leg", "gd_l1x0", "gd_la_x1"), ("Guide leg 2", "leg", "gd_lb_x0", "gd_l1x1")]


def light_guide(s: Script) -> None:
    """`light_guide`: clear PETG, one part, every fit from clr_align / clr_remove. Light from a LED
    enters a foot's entry plane (gd_clr in front of the LED face, its height) going toward the panel
    and down the slope, meets the foot's front facet at 60 degrees (total internal reflection, PETG's
    critical angle 39.6) and goes down the leg by TIR at its faces, along the bar, to the bar's bottom
    45 degree facet (TIR) which turns it toward the slot; the tongue, continuous with the bar's bottom,
    fills the slot (clr_align each side) and shows the line. No straight line runs from an entry face
    to the exit: delivery needs at least two reflections, and the evidence is the 3-D trace
    `airq_check.guide_delivery` (R48). The legs are the only parts in the FFC's row; the bar sits gd_clr
    behind the panel (the adhesive pad's gap). No face is coated or clad (R45): every face is bare PETG
    facing air (the pad on the bar's front is the one contact). D3 and D4 do not feed it: `led_mask`
    covers them; `gap_stop` fills the gap between the D1 and D2 feet (R13)."""
    pc = guide_profile_pts()
    for i, (name, key, x0, x1) in enumerate(guide_pieces()):
        _guide_poly(s, name, pc[key], x0, x1, i == 0)


def foam_stops() -> dict:
    """The black foam stops by the LEDs, {body: ((s, t) profile, x0, x1)} as expressions, one source for the build
    and the checks: `led_mask` over D3 and D4 (R45) and `gap_stop` over the gap between the D1 and D2 feet (R50).
    Each is stuck on the panel's back (its front at gd_t0: the 0.2 adhesive pad's gap) and ends gd_clr in front of
    the LED faces (its back in the entry plane y = gd_y_e)."""
    zt, zb = "(led_z + led_face_h / 2 + mask_mz)", "(led_z - led_face_h / 2 - mask_mz)"
    tt = f"((gd_y_e - ({zt} - lip) * sin_t / cos_t) * cos_t)"
    tb = f"((gd_y_e - ({zb} - lip) * sin_t / cos_t) * cos_t)"
    st = f"(({zt} - lip + {tt} * sin_t) / cos_t)"
    sb = f"(({zb} - lip + {tb} * sin_t) / cos_t)"
    return {
        "led_mask": ([(sb, "gd_t0"), (sb, tb), (st, tt), (st, "gd_t0")], "gd_l2x0", "gd_l2x1"),
        "gap_stop": ([("stop_s0", "gd_t0"), ("gd_sf", "gd_t0"), ("gd_sb", "gd_tb"), ("gd_sc", "gd_tc"), ("gd_sc", "gd_t1"), ("stop_s0", "gd_t1")],
                     "gd_la_x1 + gd_clr", "gd_lb_x0 - gd_clr"),
    }


def _foam(s: Script, body: str, feature: str) -> None:
    pts, x0, x1 = foam_stops()[body]
    with s.sketch(f"{feature} profile", "YZ", offset=x0) as sk:
        sk.polyline([yz(sv, tv) for sv, tv in pts])
    s.extrude(feature, f"{feature} profile", f"({x1}) - ({x0})", body=body)


def led_mask(s: Script) -> None:
    """`led_mask` (R45): black closed-cell foam in front of D3 and D4, stuck to the panel's back (the 0.2 adhesive
    pad's gap), gd_clr from their faces: their light is stopped there. It covers the faces' outline by gd_clr
    across and mask_mz up and down, so about 2 % of D3's and D4's emission passes its edges through the 0.2 gap
    into the case (`airq_check.mask_leak`); no straight line from there reaches the light sensor, the lip's
    window or the crease through less than 1.2 of opaque material (`airq_check.light_paths`), nor U4 (the faces
    emit away from it). The line is lit by D1 and D2 only (firmware unchanged)."""
    _foam(s, "led_mask", "LED mask")


def gap_stop(s: Script) -> None:
    """`gap_stop` (R50): black closed-cell foam between the D1 and D2 feet (gd_clr air to each foot's side face, so
    their total internal reflection stays), from stop_s0 up to the entry plane, stuck to the panel's back like
    `led_mask`. It stops every straight line from the D2 foot's tail-side face through the gap between D1 and D2
    to U4 (R13, `airq_check.guide_surface_sight`)."""
    _foam(s, "gap_stop", "Gap stop")


def crease_seal(s: Script) -> None:
    """`crease_seal`: black closed-cell foam tape on the lip's top, full width, that fills the 0.2 parting
    line between the shell's lower edge and the lip from crease_y0 to the lip's inner face (1.4 of
    foam): the light guide's light cannot run out along the crease."""
    s.box("Crease seal", ["-W / 2", "crease_y0", "lip"], ["W", "wall - crease_y0", "crease_gap + crease_squeeze"], body="crease_seal")


# --- orange dot and button flexure (feature 4) -----------------------------------------------------

def flex_params(s: Script) -> None:
    """SW1's push axis, the flexure beam in the face wall and its hard stop. The dot sits on the beam's
    free end, top right on the face; a rod from the beam's inner face to SW1's actuator carries the push
    along the actuator's axis (+y, horizontal). `flex_t`, `flex_len` and `flex_gap` are the coupon's
    (clearances.py)."""
    btn = MAIN["button"]
    p = s.param
    p("sw_travel", B.sw_travel(), "SW1 travel (interface.yaml button comment, board_sources)")
    p("sw_force", B.sw_force(), "SW1 operating force, N (interface.yaml button comment, board_sources)", unit="")
    p("sw_aw", btn["actuator_width"], "SW1 actuator width (interface.yaml button)")
    p("sw_tip", f"board_y0 + board_d - {btn['actuator_tip_y']}", "SW1 actuator tip y at rest: 0.24 past the front edge (interface.yaml button)")
    p("dot_s", "dot_f - lip", "orange dot centre: up the slope from the crease (SW1's push axis meets the face here)")
    p("dot_depth", 0.6, "orange dot: its depth, flush with the face (an AMS colour region: it prints first, on the bed, face down)")
    p("flex_w", 4.9, "flexure beam width (the coupon's 1.0 x 4.9 x 12 cantilever, clearances.py flex_t comment)")
    p("flex_slot", 0.5, "slots round the flexure beam (cut through its skin)")
    p("flex_s0", "dot_s - flex_len", "flexure beam: its root's slope position (the beam runs up the slope from the solid wall)")
    p("flex_s1", "dot_s + dot_d / 2 + 0.5", "flexure beam: its free end")
    p("flex_x0", "sw_x - flex_w / 2", "flexure beam: tail-side edge")
    p("flex_x1", "sw_x + flex_w / 2", "flexure beam: far edge")
    p("y_pad", "sw_tip - flex_gap", "pad rod: its end face, flex_gap in front of the actuator's tip")
    p("flex_stop", "board_y0 - y_pad", "hard stop: the pad rod's end bottoms on SW1's body face (flush with the board's front edge) after this much travel along y; no printed stop gap (review I4)")
    p("flex_over", "flex_stop - flex_gap - sw_travel", "hard stop: the rod can still move this far after the switch has bottomed: the switch's own stop takes the push, the beam is soft (about 1.5 N/mm)")
    p("rod_d", 2.4, "pad rod diameter (the actuator is 2.0 wide)")
    p("rod_y0", "(sw_z - lip) * sin_t / cos_t + 0.3", "pad rod: where it starts, 0.3 behind the face's outer surface on the axis (the rod's front corner is trimmed flush)")


def flexure(s: Script) -> None:
    """The button flexure in the shell's face wall (clearances.py `flex_*`): a beam of the wall's skin (flex_t
    thick, flex_len long from its root up the slope to the dot), cut free by a U slot, the wall's inner
    part cut away over it. A rod from the beam's inner face carries the push to the actuator and its end
    bottoms on SW1's body (the hard stop: a bed-plane-free stop, no printed gap). The face-wall skin
    keeps its outer surface: the dot's colour region is cut in it by `orange_dot`."""
    sl = "flex_slot"
    x0, x1 = f"flex_x0 - {sl}", f"flex_x1 + {sl}"
    top = "flex_s1 + flex_slot"
    with s.sketch("Flex thin outline", slope_plane(s), offset=toff("flex_t")) as sk:
        sk.rect(x0, ys("flex_s0"), x1, ys(top))
    s.extrude("Flex thin", "Flex thin outline", "wall - flex_t + 0.3", operation="cut", targets=["shell"], direction="negative")
    pts = [(x0, "flex_s0"), ("flex_x0", "flex_s0"), ("flex_x0", "flex_s1"), ("flex_x1", "flex_s1"), ("flex_x1", "flex_s0"),
           (x1, "flex_s0"), (x1, top), (x0, top)]
    with s.sketch("Flex slot outline", slope_plane(s), offset=toff("-1")) as sk:
        sk.polyline([(x, ys(y)) for x, y in pts])
    s.extrude("Flex slot", "Flex slot outline", "1 + flex_t + 0.2", operation="cut", targets=["shell"], direction="negative")
    s.cylinder("Pad rod", ["sw_x", "rod_y0", "sw_z"], "rod_d", "y_pad - rod_y0", axis="Y", operation="join", targets=["shell"])
    # the rod's front corner would stand proud of the face: trim everything in front of the face over the beam
    with s.sketch("Flex trim outline", slope_plane(s), offset=toff("0")) as sk:
        sk.rect("flex_x0", ys("dot_s - 3"), "flex_x1", ys("dot_s + 3"))
    s.extrude("Flex trim", "Flex trim outline", "dot_d / 2", operation="cut", targets=["shell"])


def orange_dot(s: Script) -> None:
    """`orange_dot`: an AMS colour region of the shell's print, a disc flush with the face on the beam's free
    end, on SW1's push axis, top right (right of the pocket). It is a separate body in the same job: cut
    from the shell and filled by this body, which touches it everywhere (no clearance)."""
    with s.sketch("Dot outline", slope_plane(s), offset=toff("0")) as sk:
        n = 32                                   # a 32-gon: a sketch circle would add an unnamed dimension parameter
        sk.polyline([(f"sw_x + dot_d / 2 * {math.cos(2 * math.pi * i / n):.6f}", ys(f"dot_s + dot_d / 2 * {math.sin(2 * math.pi * i / n):.6f}"))
                     for i in range(n)])
    s.extrude("Dot recess", "Dot outline", "dot_depth", operation="cut", targets=["shell"], direction="negative")
    s.extrude("Orange dot", "Dot outline", "dot_depth", body="orange_dot", direction="negative")
