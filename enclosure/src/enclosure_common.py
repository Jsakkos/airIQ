"""Shared enclosure geometry for the airQ and the airQ mini (Plan 3 Tasks 3-4, rulings R22, R24).

Both enclosures share one construction. Each function here adds named parameters and features over
shared parameter names, so Task 4 calls the same functions with the mini's values. The
construction is:
- a vertical lower front lip that carries the intake slots, with the front face sloped at
  `tilt_deg` above it;
- the main board lying horizontal above the standing SEN66 (R17), with the zone wall between;
- the print split (R24): `shell` (sloped face, top and sides) prints face down; `base_plate`
  prints floor down. The base is the whole footprint: floor, front lip, rear wall, and the
  sensor zone's own sealed tub (side rails under the zone wall, the outlet plenum, the cradle,
  the board standoffs). Everything that must seal or locate is joined to it (review I2);
- the sensor zone (below the zone wall) is the SEN66's intake plenum. It is closed by
  construction (one print) except at the top, where the zone wall rests on the tub's rim (laps:
  the rails, the plenum plate, the rear-wall rib, the standoff collars) and a TPU strip seals the
  ledge against the lip (review I3).

The numbers that place the parts come from `layout_study` (one source for the study and the
model). Board positions come from `board_sources` (R27).

Frame R3: x = 0 at the width centre (+x to the user's right), y = 0 at the front bottom edge (+y
to the rear), z = 0 at the bottom plane, without the feet. On the slope, s is the distance up
the slope from the crease at z = lip, and t is the depth behind the slope's outer surface.
"""
from __future__ import annotations

import board_sources as B
import clearances
import layout_study as L
from sclib import Script

MAIN = B.MAIN
TONGUE = B.TONGUE
LS = "layout_study"


def yf(z) -> str:
    """y of the zone wall's slanted front face at height z (an expression)."""
    return f"(zw_tf + ({z} - lip) * sin_t) / cos_t"


def yb(z) -> str:
    """y of the zone wall's slanted back (sensor-side) face at height z."""
    return f"(zw_tf + zone_t + ({z} - lip) * sin_t) / cos_t"


def z_under(y) -> str:
    """Height of the zone wall's underside at depth y: the ledge, the slant, then the flat part."""
    return f"min(zw_z0, max(ledge_z0, lip + (({y}) * cos_t - zw_tf - zone_t) / sin_t))"


def z_slant(y) -> str:
    """Height of the zone wall's slanted underside at depth y (no ledge or flat-part clamp)."""
    return f"lip + (({y}) * cos_t - zw_tf - zone_t) / sin_t"


def under_profile(s: Script, y0: str, y1: str, zb: str) -> list[tuple[str, str]]:
    """A closed (y, z) polygon from y0 to y1 (y0 < y1), from zb up to the zone wall's underside:
    the ledge, the slant, then the flat part over the SEN66. The corners where the underside bends
    are vertices when they fall between y0 and y1 (decided at build time, like the design's other
    build-time choices)."""
    v = s.v
    knees = [(yb("ledge_z0"), "ledge_z0"), (yb("zw_z0"), "zw_z0")]

    def z_at(y):
        if v(y) >= v(knees[1][0]) - 1e-9:
            return "zw_z0"
        if v(y) <= v(knees[0][0]) + 1e-9:
            return "ledge_z0"
        return z_slant(y)
    top = [(y1, z_at(y1))] + [k for k in reversed(knees) if v(y0) + 1e-6 < v(k[0]) < v(y1) - 1e-6] + [(y0, z_at(y0))]
    return [(y0, zb), (y1, zb)] + top


def zt(y: str, t: str) -> str:
    """z of the point at depth y with depth t behind the slope's outer surface (an expression)."""
    return f"lip + (({y}) * cos_t - ({t})) / sin_t"


def add_envelope(s: Script, m: L.Model) -> None:
    """The envelope and printing parameters every enclosure shares (the names the plan fixes)."""
    p = s.param
    # final review M2: W, D, H, tilt_deg and lip are not favourites. Some geometry is fixed when the script is
    # generated (the panel pocket's sketch plane from sin_t, the profiles' knees, the slot loops' counts), so
    # change them in the generator and rebuild, not in SolidCraft's table (README "Building")
    p("W", m.W, f"outer width ({LS}; plan). Build-time: change in the generator")
    p("D", m.D, f"outer depth ({LS}; R22). Build-time: change in the generator")
    p("H", m.H, f"outer height ({LS}; R22). Build-time: change in the generator")
    p("tilt_deg", m.tilt_deg, "front slope from vertical (plan). Build-time: change in the generator", unit="deg")
    p("lip", m.lip, f"vertical lower front lip carrying the intake slots (R15, R22; {LS}). Build-time: change in the generator")
    clearances.add_params(s)          # clr_align, clr_remove, clr_snap, slot_w, wall, flex_t, flex_len, flex_gap
    p("crease_gap", 0.2, "parting line at the crease: the slope's lower edge stops this far over the lip's top (the floor is the shell's z datum). A fixed gap, not a fit (R57): it does not follow clr_remove, so the opaque paths to it and the bought crease seal keep their sizes over the coupons' window")
    p("floor_t", m.floor, "plan: floor (base plate) 2.0; named floor_t because SolidCraft reserves floor (a function)", favorite=True)
    p("grille_min_z", m.grille_min_z, "plan: no opening's lower edge below 10 mm above z = 0 (feet not counted)", favorite=True)
    p("cos_t", "cos(tilt_deg)", "derived", unit="")
    p("sin_t", "sin(tilt_deg)", "derived", unit="")
    p("y_top", "(H - lip) * sin_t / cos_t", "derived: y of the slope's top edge")
    p("inner_x", "W / 2 - wall", "derived: half the interior width (the shell's side walls' inner faces)")
    p("edge_chamfer", 0.8, "crisp chamfer on the top front edge (Paper look)")
    p("iwall", 1.6, "internal walls of the base (rails, plenum plate, pockets): the plan's minimum wall")
    p("tub_x", "inner_x - clr_remove - iwall", "derived: half width of the sensor zone, inside the base's side rails")


def add_sen66(s: Script, m: L.Model) -> None:
    """The standing SEN66's sizes (R17): long axis along x, port face vertical. Its position is
    the model's (airq.py)."""
    r = L._refs()
    p = s.param
    p("sen_l", r["sen_l"], "SEN66 length along x (ref_sen66 L, datasheet Fig. 8)")
    p("sen_d", r["sen_h"], "SEN66 depth along y, port face to connector face (ref_sen66 H)")
    p("sen_up", r["sen_w"], "SEN66 height as it stands, its 25.6 width (ref_sen66 W, R17)")
    p("foam", m.foam, "plan: the SEN66 sits on 1 mm foam")
    p("sen_top", "floor_t + foam + sen_up", "derived: SEN66 top")


ZW_TF_AIRQ = (7.2, "zone wall's slanted part: front face depth behind the slope, behind the adapter (t 6.95) and light guide")
BOARD_CLR_AIRQ = (0.5, "board edge to the side wall")


def add_zone_and_board(s: Script, m: L.Model, front_t_need: str | None, board_x0: str,
                       zw_tf: tuple = ZW_TF_AIRQ, board_clr: tuple = BOARD_CLR_AIRQ,
                       board_y0: tuple | None = None) -> None:
    """Zone wall over the SEN66 and the main board above it (horizontal, R22). The board's front
    edge is where its LED faces' corner meets the room the front needs (`front_t_need`, a depth
    behind the slope's outer surface): the corner that binds in `layout_study`.
    The mini (Task 4a) passes its own `zw_tf` and `board_clr` ((value, comment)) and `board_y0`
    ((expression, comment): the board as far back as the antenna allows); `front_t_need` is then
    derived from the board (the depth its LED corner keeps behind the slope)."""
    p = s.param
    p("zone_gap", m.zone_gap, f"air gap above the SEN66 and under the board ({LS})")
    p("zone_t", m.zone_wall, "zone wall thickness, a wall")
    p("zw_z0", "sen_top + zone_gap", "derived: zone wall underside over the SEN66")
    p("zw_z1", "zw_z0 + zone_t", "derived: zone wall top")
    p("zw_tf", zw_tf[0], zw_tf[1])
    p("ledge_t", 1.2, "zone wall ledge thickness")
    p("ledge_z1", "lip", "ledge top: at the crease, under the LED slot's inner edge")
    p("ledge_z0", "ledge_z1 - ledge_t", "derived: ledge underside, above the top slot row")
    p("seal_t", 1.2, "gap between the ledge's front face and the lip, closed by zone_seal")
    p("seal_squeeze", 0.4, "zone_seal: closed-cell foam, seal_t + 0.4 free, 25 % compressed (round 3: TPU 95A at 20 % would push hundreds of N on the lip; R9: the check sets 0)")
    p("board_w", MAIN["outline"][0], "main board width (interface.yaml)")
    p("board_d", MAIN["outline"][1], "main board depth (interface.yaml)")
    p("board_t", MAIN["thickness"], "main board thickness (interface.yaml)")
    p("led_h", B.led_body_h(), "LED body height above the board (interface.yaml leds comment, board_sources)")
    p("antenna_out", MAIN["antenna"]["overhang"], "antenna strip past the board's rear edge (interface.yaml)")
    p("board_clr", board_clr[0], board_clr[1])
    p("board_z0", "zw_z1 + zone_gap", "derived: board bottom")
    if board_y0 is None:
        p("front_t_need", front_t_need, f"depth behind the slope the LED faces need ({LS} 'guide' corner)")
        p("board_y0", "(front_t_need + (board_z0 + board_t + led_h - lip) * sin_t) / cos_t",
          f"derived: board front edge, the LED corner on the front constraint ({LS})")
    else:
        p("board_y0", board_y0[0], board_y0[1])
        p("front_t_need", "board_y0 * cos_t - (board_z0 + board_t + led_h - lip) * sin_t",
          "derived: depth of the LED faces' top corner behind the slope's outer surface (the room in front of the LEDs)")
    p("board_x0", board_x0, "board left edge")


def add_standoffs(s: Script) -> None:
    """Board standoff positions at the board's mounting holes (interface.yaml)."""
    p = s.param
    holes = MAIN["mounting_holes"]
    (h1x, h1y), (h2x, h2y) = holes["centers"]
    p("standoff_d", holes["clear_diameter"], "standoff diameter: the hole's copper-free circle (interface.yaml)")
    p("pilot_d", 1.7, "M2 self-tapping pilot hole (R10a: board to standoffs with M2 screws)")
    p("pilot_depth", 6.0, "pilot hole depth")
    p("collar_w", 1.5, "standoff collar under the zone wall: the zone wall's hole rests on it (a lap)")
    p("collar_h", 1.2, "standoff collar height")
    p("spigot_d", 3.0, "standoff spigot into the zone wall's underside: locates it (N5)")
    p("spigot_h", 1.0, "standoff spigot height above the zone wall's underside")
    p("h1_x", f"board_x0 + {h1x}", "H1 x (interface.yaml; 8 mm from the USB-C: the support boss)")
    p("h1_y", f"board_y0 + board_d - {h1y}", "H1 y (interface.yaml, layout Y from the rear edge)")
    p("h2_x", f"board_x0 + {h2x}", "H2 x (interface.yaml)")
    p("h2_y", f"board_y0 + board_d - {h2y}", "H2 y (interface.yaml)")


def add_bosses(s: Script) -> None:
    """The shell's insert bosses (R10b) and the base's pockets round the front ones."""
    p = s.param
    p("boss_d", 6.0, "insert boss diameter (coupon R20)")
    p("boss_h", 6.8, "insert boss height above the floor")
    p("insert_d", 3.2, "M2 heat-set insert hole: coupon middle size, to confirm (R20)")
    p("insert_depth", 4.0, "insert hole depth (coupon R20)")
    p("boss_in", 1.0, "front boss centre this far inside the side wall's inner face less its radius: the boss joins the wall")
    p("boss_x", "inner_x - boss_d / 2 + boss_in", "derived: front floor bosses' |x|")
    p("boss_y", "wall + 3.0", "front floor bosses' y: behind the lip (the lip's inner face is recessed clr_remove round them, review N1)")
    p("bp_x0", "boss_x - boss_d / 2 - clr_remove - iwall", "derived: |x| of the boss pocket's inner wall (base)")
    p("bp_y1", "boss_y + boss_d / 2 + clr_remove + iwall", "derived: y of the boss pocket's back wall's rear face; the side rails start here")
    p("rear_boss_len", 6.0, "rear insert boss length along y")
    p("rear_boss_x", "-(inner_x - boss_d / 2 + 0.5)", "rear boss x (rear left, at the far end from the antenna: 69 mm on the airQ, 41.25 on the mini; R29)")
    p("rear_boss_z", "H - wall - boss_d / 2 + 0.5", "rear boss z, under the top wall")


def shell(s: Script) -> None:
    """`shell`: the sloped face, top and both sides in one part that prints face down on textured
    PEI. The base closes its front lip, floor and rear (R24): the side walls stand on the base's
    floor (a horizontal lap at z = floor_t, clamped by the screws) and end against the base's
    full-width rear wall. The front floor bosses take the screws from underneath (R10b); their
    axis is vertical in use, inclined in print (Task 2 M7 note: confirmed at the first shell
    print). The rear boss takes one M2 screw through the rear wall (R29)."""
    with s.sketch("Envelope profile", "YZ", offset="-W / 2") as sk:
        sk.polyline([(0, 0), ("D", 0), ("D", "H"), ("y_top", "H"), (0, "lip")])
    s.extrude("Envelope", "Envelope profile", "W", body="shell")
    v = s.v
    s.chamfer("Edge chamfers", [[0, v("y_top"), v("H")]], "edge_chamfer", body="shell")
    s.shell("Shell walls", [[0, v("D") / 2, 0], [0, v("D"), v("H") / 2]], "wall")
    # R24: the lower front lip belongs to the base; the shell is lowered onto the base along -z.
    # Review N1: the shell's datums are the floor (z, where the screws clamp it) and the rear wall's
    # front face (y, where the side walls end). Everywhere else it keeps clear of the base: its side
    # walls end clr_remove behind the lip's inner face, and its slope stops crease_gap above the
    # lip's top (the 0.2 parting line at the crease, into the electronics zone above the ledge
    # seal, not into the sensor zone; a fixed gap since R57, not clr_remove)
    s.box("Lip to the base", ["-W / 2 - wall", "-wall", "-wall"], ["W + 2 * wall", "2 * wall + clr_remove", "lip + wall + crease_gap"],
          operation="cut", targets=["shell"])
    # the slope's inner corner hangs below the crease behind the lip: trim it to the same height, so
    # it clears the lip's top and the zone wall's ledge seal
    s.box("Crease seat", ["-inner_x", "wall - 0.1", "lip - wall"], ["2 * inner_x", "wall / cos_t - wall + 0.2 + crease_gap", "wall + crease_gap"],
          operation="cut", targets=["shell"])
    s.box("Floor seat", ["-W / 2 - wall", "-wall", "-wall"], ["W + 2 * wall", "D + 2 * wall", "floor_t + wall"], operation="cut",
          targets=["shell"])
    s.box("Rear wall seat", ["-W / 2 - wall", "D - wall", "-wall"], ["W + 2 * wall", "2 * wall", "H"], operation="cut",
          targets=["shell"])
    for i, sx in enumerate(("-boss_x", "boss_x"), 1):
        s.cylinder(f"Insert boss {i}", [sx, "boss_y", "floor_t"], "boss_d", "boss_h", operation="join", targets=["shell"])
        s.cylinder(f"Insert hole {i}", [sx, "boss_y", "floor_t - 0.5"], "insert_d", "insert_depth + 0.5",
                   operation="cut", targets=["shell"])
    s.cylinder("Rear insert boss", ["rear_boss_x", "D - wall - clr_remove - rear_boss_len", "rear_boss_z"], "boss_d",
               "rear_boss_len", axis="Y", operation="join", targets=["shell"])
    s.cylinder("Rear insert hole", ["rear_boss_x", "D - wall - clr_remove - insert_depth", "rear_boss_z"], "insert_d",
               "insert_depth + 0.5", axis="Y", operation="cut", targets=["shell"])


def panel_pocket(s: Script) -> None:
    """The panel's pocket in the slope (airQ), so the panel sits behind its window lip `bezel`.
    The window, holder and FFC path are Task 3b's. The pocket also takes the hatched block at the
    tail end."""
    s.param("pocket_x0", "panel_x0 - block_out - clr_remove", "derived: pocket left end (the hatched block)")
    s.param("pocket_x1", "panel_x0 + panel_l + clr_remove", "derived: pocket right end")
    plane = {"origin": [0, 0, 0], "x_dir": [1, 0, 0], "y_dir": [0, s.v("sin_t"), s.v("cos_t")]}
    with s.sketch("Panel pocket outline", plane, offset="lip * sin_t - bezel") as sk:
        sk.rect("pocket_x0", "panel_s0 - clr_remove + lip * cos_t",
                "pocket_x1", "panel_s0 + panel_w + clr_remove + lip * cos_t")
    s.extrude("Panel pocket", "Panel pocket outline", "wall - bezel + 2", operation="cut",
              targets=["shell"], direction="negative")


def base_plate(s: Script) -> None:
    """`base_plate`: the whole footprint's floor, the full-width front lip and the full-width rear
    wall (a U printed floor down, R24). The shell's side walls stand on the floor and end against
    the rear wall, so the base-to-shell joint is lapped: no slit from the bottom plane or the rear
    into the case (review I3). The rear-wall rib is the zone wall's seat over the outlet plenum."""
    p = s.param
    p("screw_d", 2.4, "M2 screw clearance hole")
    p("head_d", 4.4, "M2 screw head counterbore, under a felt foot")
    p("head_depth", 0.4, "counterbore depth: leaves floor_t - 0.4 = 1.6 under the head (the felt foot covers it)")
    p("rib_d", 1.6, "rib on the rear wall's inner face: the zone wall's seat over the outlet plenum (a lap)")
    s.box("Floor", ["-W / 2", 0, 0], ["W", "D", "floor_t"], body="base_plate")
    s.box("Front lip", ["-W / 2", 0, 0], ["W", "wall", "lip"], operation="join", targets=["base_plate"])
    s.box("Rear wall", ["-W / 2", "D - wall", 0], ["W", "wall", "H - wall - clr_remove"], operation="join",
          targets=["base_plate"])
    s.box("Rear wall rib", ["-tub_x - 0.5", "D - wall - rib_d", "zw_z0 - rib_d"], ["2 * tub_x + 1", "rib_d + 0.5", "rib_d"],
          operation="join", targets=["base_plate"])


def rails(s: Script, slant_front: bool = False) -> None:
    """The sensor zone's side walls in the base (`Side rail L/R`): under the zone wall's profile
    from the boss pockets to the rear wall, inside the shell's side walls. The zone wall rests on
    them (a lap), so its sides need no seal, and the HCHO grille is cut in the right one.
    `Boss pocket L/R`: walls round the shell's front floor bosses, so the bosses stay outside the
    sensor zone (the zone wall's ledge is notched over them).
    `slant_front` (the mini, Task 4a): the zone wall's slant hugs the slope, so its ledge ends in
    front of the boss pockets' back walls. The rails then start on the slant (their front top under
    it), and the pockets' inner and back walls rise to the slant's underside: the slant laps on them,
    so the pockets (open to the electronics zone through the zone wall's boss notches) stay sealed
    from the sensor zone."""
    if slant_front:
        pts = under_profile(s, "bp_y1 - 0.5", "D - wall + 0.5", "floor_t - 0.5")
    else:
        pts = [("bp_y1 - 0.5", "floor_t - 0.5"), ("D - wall + 0.5", "floor_t - 0.5"), ("D - wall + 0.5", "zw_z0"),
               (yb("zw_z0"), "zw_z0"), (yb("ledge_z0"), "ledge_z0"), ("bp_y1 - 0.5", "ledge_z0")]
    for side, off in (("R", "tub_x"), ("L", "-tub_x - iwall")):
        with s.sketch(f"Side rail {side} profile", "YZ", offset=off) as sk:
            sk.polyline(pts)
        s.extrude(f"Side rail {side}", f"Side rail {side} profile", "iwall", operation="join", targets=["base_plate"])
    for side, sgn in (("R", ""), ("L", "-")):
        x_in = "bp_x0" if sgn == "" else "-bp_x0 - iwall"
        s.box(f"Boss pocket {side} inner wall", [x_in, "wall - 0.5", "floor_t - 0.5"], ["iwall", "bp_y1 - wall + 0.5", "ledge_z0 - floor_t + 0.5"],
              operation="join", targets=["base_plate"])
        x_b = "bp_x0" if sgn == "" else "-tub_x - iwall"
        s.box(f"Boss pocket {side} back wall", [x_b, "bp_y1 - iwall", "floor_t - 0.5"],
              ["tub_x + iwall - bp_x0", "iwall", "ledge_z0 - floor_t + 0.5"], operation="join", targets=["base_plate"])
        if slant_front:
            # up to the slant's underside, behind the ledge (a lap): the inner wall along y, the back wall across x
            prof = under_profile(s, yb("ledge_z0"), "bp_y1", "ledge_z0 - 0.5")
            with s.sketch(f"Boss pocket {side} inner rise profile", "YZ", offset=x_in) as sk:
                sk.polyline(prof)
            s.extrude(f"Boss pocket {side} inner rise", f"Boss pocket {side} inner rise profile", "iwall", operation="join",
                      targets=["base_plate"])
            prof = under_profile(s, "bp_y1 - iwall", "bp_y1", "ledge_z0 - 0.5")
            with s.sketch(f"Boss pocket {side} back rise profile", "YZ", offset=x_b) as sk:
                sk.polyline(prof)
            s.extrude(f"Boss pocket {side} back rise", f"Boss pocket {side} back rise profile", "tub_x + iwall - bp_x0",
                      operation="join", targets=["base_plate"])


HOLES = (("H1", ("h1_x", "h1_y")), ("H2", ("h2_x", "h2_y")))


def standoffs(s: Script, holes: tuple = ("H1", "H2")) -> None:
    """Board standoffs: posts on the floor up to the zone wall's underside, at H1 (the USB-C
    support boss, interface.yaml: 8 mm from the USB-C) and H2, each with a collar and a spigot. The
    zone wall sits on them (a lap round the spigot) and carries a pad up to the board, so the
    board's M2 screws, through the zone wall into the posts' pilots, clamp the zone wall (N5).
    Joined to base_plate: they print vertical with it. H1 also merges with the plenum plate (airq),
    which braces it up to the zone wall (M7). The pilot holes are cut at the end. `holes`: the
    mini has a post at H1 only (H2 lies over its SEN66)."""
    for name, (x, y) in [h for h in HOLES if h[0] in holes]:
        s.cylinder(f"Standoff {name}", [x, y, "floor_t - 0.5"], "standoff_d", "zw_z0 - floor_t + 0.5",
                   operation="join", targets=["base_plate"])
        s.cylinder(f"Standoff {name} collar", [x, y, "zw_z0 - collar_h"], "standoff_d + 2 * collar_w", "collar_h",
                   operation="join", targets=["base_plate"])
        s.cylinder(f"Standoff {name} spigot", [x, y, "zw_z0 - 0.5"], "spigot_d", "spigot_h + 0.5",
                   operation="join", targets=["base_plate"])


def standoff_pilots(s: Script, holes: tuple = ("H1", "H2")) -> None:
    for name, (x, y) in [h for h in HOLES if h[0] in holes]:
        s.cylinder(f"Standoff {name} pilot", [x, y, "board_z0 - pilot_depth"], "pilot_d", "pilot_depth + 1",
                   operation="cut", targets=["base_plate"])


def base_screws(s: Script) -> None:
    """The screw holes for the shell's bosses (cut after every join), and the lip's recess in front
    of each front boss: the boss keeps clr_remove from the lip's inner face (review N1)."""
    for i, sx in enumerate(("-boss_x", "boss_x"), 1):
        s.box(f"Boss clearance {i}", [f"{sx} - boss_d / 2 - clr_remove", "wall - clr_remove", "floor_t"],
              ["boss_d + 2 * clr_remove", "clr_remove + 0.01", "boss_h + clr_remove"], operation="cut", targets=["base_plate"])
        s.cylinder(f"Screw hole {i}", [sx, "boss_y", "-head_depth"], "screw_d", "floor_t + 2 * head_depth", operation="cut",
                   targets=["base_plate"])
        s.cylinder(f"Screw head {i}", [sx, "boss_y", "-head_depth"], "head_d", "2 * head_depth", operation="cut",
                   targets=["base_plate"])
    s.cylinder("Rear screw hole", ["rear_boss_x", "D - wall - 1", "rear_boss_z"], "screw_d", "wall + 2", axis="Y",
               operation="cut", targets=["base_plate"])
    s.cylinder("Rear screw head", ["rear_boss_x", "D - head_depth", "rear_boss_z"], "head_d", "2 * head_depth", axis="Y",
               operation="cut", targets=["base_plate"])


def base_side_clearance(s: Script) -> None:
    """Nothing of the base may stand outside the rails behind the boss pockets: the shell's side
    walls come down there (I1)."""
    for side, x0 in (("R", "tub_x + iwall"), ("L", "-W / 2 - 1")):
        s.box(f"Side clearance {side}", [x0, "bp_y1", "floor_t"], ["W / 2 + 1 - tub_x - iwall", "D - wall - bp_y1", "H"],
              operation="cut", targets=["base_plate"])


def zone_wall(s: Script, blind: tuple = ()) -> None:
    """`zone_wall`: the wall between the sensor zone (low) and the electronics zone (high):
    - a ledge behind the lip, between the intake slots and the LED slot; its front face carries
      the TPU `zone_seal` against the lip;
    - a slanted part parallel to the slope at depth zw_tf, behind the panel, the light guide, the
      FFC and the adapter, which stay in the electronics zone;
    - a horizontal part over the SEN66 and the outlet plenum, back to the rear wall.
    It rests on the base's tub (rails, boss pockets, plenum plate, rear-wall rib, standoff
    collars): laps all round. It sits on the standoffs' spigots and the board's screws clamp it
    there (N5); the front bosses pass its notches when the shell is lowered (I1).
    `blind` names the holes with no standoff under them (the mini's H2, over its SEN66): the board's
    screw goes into a blind pilot in the pad and the zone wall (no spigot seat, no hole through)."""
    with s.sketch("Zone wall profile", "YZ", offset="-inner_x + clr_remove") as sk:
        sk.polyline([("wall + seal_t", "ledge_z0"), (yb("ledge_z0"), "ledge_z0"), (yb("zw_z0"), "zw_z0"),
                     ("D - wall - clr_remove", "zw_z0"), ("D - wall - clr_remove", "zw_z1"), (yf("zw_z1"), "zw_z1"),
                     (yf("ledge_z1"), "ledge_z1"), ("wall + seal_t", "ledge_z1")])
    s.extrude("Zone wall", "Zone wall profile", "2 * (inner_x - clr_remove)", body="zone_wall")
    # final review M1: its ends stand clr_remove inside the shell's side walls; a shell lowered off-centre in x
    # meets a chamfer on the end's top edges (the flat top's and the slant's), not a square edge, and slides home
    s.param("zw_end_chamfer", 0.3, "zone wall: 45 deg chamfer on its ends' top edges (the shell's side walls slide past them; final review M1)")
    v = s.v
    xe = v("inner_x - clr_remove")
    y_top = (v(yf("zw_z1")) + v("D - wall - clr_remove")) / 2
    y_sl, z_sl = (v(yf("ledge_z1")) + v(yf("zw_z1"))) / 2, (v("ledge_z1") + v("zw_z1")) / 2
    s.chamfer("Zone wall end chamfers", [[sx * xe, y_top, v("zw_z1")] for sx in (-1, 1)] + [[sx * xe, y_sl, z_sl] for sx in (-1, 1)],
              "zw_end_chamfer", body="zone_wall")
    for name, (x, y) in HOLES:     # N5: the board's screws clamp it here
        s.cylinder(f"Zone wall pad {name}", [x, y, "zw_z1 - 0.5"], "standoff_d", "board_z0 - zw_z1 + 0.5",
                   operation="join", targets=["zone_wall"])
        if name in blind:
            s.cylinder(f"Zone wall pilot {name}", [x, y, "board_z0 - zw_pilot_depth"], "pilot_d", "zw_pilot_depth + 1",
                       operation="cut", targets=["zone_wall"])
            continue
        s.cylinder(f"Zone wall spigot seat {name}", [x, y, "zw_z0 - 1"], "spigot_d + 2 * clr_align", "spigot_h + clr_align + 1",
                   operation="cut", targets=["zone_wall"])
        s.cylinder(f"Zone wall screw hole {name}", [x, y, "zw_z0"], "screw_d", "board_z0 - zw_z0 + 1",
                   operation="cut", targets=["zone_wall"])
    for i, sx in enumerate(("-boss_x", "boss_x"), 1):     # the shell's floor bosses pass here on the way down
        s.box(f"Zone wall boss notch {i}", [f"{sx} - boss_d / 2 - clr_remove", "-wall", "ledge_z0 - 1"],
              ["boss_d + 2 * clr_remove", "boss_y + boss_d / 2 + clr_remove + wall", "zw_z1 - ledge_z0 + 2"],
              operation="cut", targets=["zone_wall"])


def zone_seal(s: Script) -> None:
    """`zone_seal` (closed-cell foam, black, adhesive-backed): the strip between the ledge's front
    face and the lip's inner face, between the boss pockets. The intake slots leave no room for a
    lap there. It is foam, 25 % compressed, so it pushes the slotted lip with a few N (round 3).
    R9: at seal_squeeze 0 it touches both."""
    s.box("Zone seal", ["-bp_x0", "wall - seal_squeeze", "ledge_z0"], ["2 * bp_x0", "seal_t + seal_squeeze", "ledge_t"],
          body="zone_seal")


# --- the SEN66's sealed zone (moved from airq.py in Task 4a; `hand` mirrors it) -------------------
# hand -1: the airQ (inlet end right, the inlet seal's blade leans to the left, away from the
# inlets); hand +1: the mini (inlet end left, the blade leans to the right). The expressions for
# hand -1 are the airQ's exactly, so its design does not change.

def plenum(s: Script) -> None:
    """The outlet plenum, part of base_plate: the plate (the baffle in front of the outlet grille,
    with the ring's seat and bore) between the side rails, from the floor to the zone wall, which
    rests on its top edge and on the rear-wall rib. H1 merges with the plate, which braces it."""
    s.box("Plenum plate", ["-tub_x - 0.5", "plate_y0", "floor_t - 0.5"], ["2 * tub_x + 1", "iwall", "zw_z0 - floor_t + 0.5"],
          operation="join", targets=["base_plate"])


SEAT_Y0_AIRQ = ("max(pt_yh + cable_gh_d / 2 + clr_align, sen_y0 - pad_gap_max - seat_t)",
                "pad seat's front face: just behind the cables' riser and run, and no further forward than leaves the pad pad_gap_max at the nominal module (R57: a looser clr_remove moves the module back, the seat follows)")
SEAT_CLR_AIRQ = ("gasket_squeeze / sin_t + 0.2", "derived: the seat's top under the slant: under the drawer grommet's squeezed face, + 0.2")
SEAT_X_AIRQ = ("-tub_x - iwall", "plug_x0 - 1.0 + tub_x + iwall")


def cradle(s: Script, seat_y0: tuple = SEAT_Y0_AIRQ, seat_slant_clr: tuple = SEAT_CLR_AIRQ, seat_x: tuple = SEAT_X_AIRQ,
           front_rail: bool = True) -> None:
    """The SEN66 cradle, part of base_plate (I3(b)). The module's port face rests on the outlet
    ring's land (its rear stop); `sen66_pad`, foam stuck on its connector face on the ring's axis,
    presses it there from the pad's seat, so the module's 21.3 +-0.5 depth goes into the pad, not
    into the seals. The low right rail is a guide only: it stays clr_align in front of a module at
    the deepest. The module's left end lies against the left side rail, its right end against the
    HCHO pocket's left wall.
    The pad's seat (review round 3, B1) is a seat_t plate from the floor, joined to the left side
    rail along its height (a plate held on two edges, not a free cantilever), just behind the
    cables' riser and run. Its top follows the zone wall's slant (under the drawer's grommet) and
    has a 45 deg lead-in on its back edge, so the pad is squeezed gradually as the module goes
    down (B4).
    The mini (Task 4a) passes its seat's front face, its clearance under the slant and its x span
    (sketch offset, length: from right of the plug to the right rail, round the ring's axis), and
    no front rail (its SEN66 cable runs there)."""
    p = s.param
    p("pad_t", 3.2, "SEN66 front pad: foam thickness free (stuck on the module's connector face on the ring's axis; to confirm with the foam bought)")
    p("pad_w", 10.0, "pad width (x)")
    p("pad_h", 10.0, "pad height (z), centred on the outlet: its force passes through the ring's land")
    p("seat_t", 2.4, "pad seat thickness (B1)")
    if "pad_gap_max" in seat_y0[0]:
        p("pad_gap_max", 1.8, "the pad's gap at the nominal module, at most (44 %; R57): the seat follows the module back when clr_remove grows, so the pad keeps >= 25 % at 20.8 deep with the seat's give")
    p("seat_y0", seat_y0[0], seat_y0[1])
    p("pad_y0", "seat_y0 + seat_t", "derived: the pad's seat face")
    p("pad_gap", "sen_y0 - pad_y0", "derived: pad thickness at the nominal module (44 % compressed; 28 % at 20.8 deep, 60 % at 21.8)")
    p("pad_squeeze", "pad_t - pad_gap", "derived: the pad as modelled, free, over the nominal module (R9: the check design sets 0)")
    p("seat_lead_z", "outlet_z + pad_h / 2 + 0.2", "derived: where the seat's lead-in starts, just over the pad's top")
    p("seat_slant_clr", seat_slant_clr[0], seat_slant_clr[1])
    if front_rail:
        p("rail_h", 4.0, "cradle right rail (a guide) height above the floor")
    tb = "zw_tf + zone_t"
    # the apex where the lead-in (45 deg up and forward from the back face) meets the slant-following top
    y_apex = f"(seat_lead_z + pad_y0 + seat_slant_clr - lip + ({tb}) / sin_t) / (cos_t / sin_t + 1)"
    if s.v(y_apex) > s.v("seat_y0"):
        p("seat_apex_y", y_apex, "derived: the seat's top apex, y")
        p("seat_apex_z", "seat_lead_z + pad_y0 - seat_apex_y", "derived: the seat's top apex, z")
        pts = [("seat_y0", "floor_t - 0.5"), ("pad_y0", "floor_t - 0.5"), ("pad_y0", "seat_lead_z"), ("seat_apex_y", "seat_apex_z"),
               ("seat_y0", f"{zt('seat_y0', tb)} - seat_slant_clr")]
    else:
        # (the mini) the lead-in reaches the seat's front face under the slant: the seat's top is the lead-in
        p("seat_top_z", "seat_lead_z + seat_t", "derived: the seat's top at its front face (the lead-in's end), under the slant")
        pts = [("seat_y0", "floor_t - 0.5"), ("pad_y0", "floor_t - 0.5"), ("pad_y0", "seat_lead_z"), ("seat_y0", "seat_top_z")]
    with s.sketch("Pad seat profile", "YZ", offset=seat_x[0]) as sk:
        sk.polyline(pts)
    s.extrude("Pad seat", "Pad seat profile", seat_x[1], operation="join", targets=["base_plate"])
    if front_rail:
        s.box("Cradle front rail R", ["plug_x1 + 1.0", "sen_y0 - sen_d_tol - clr_align - iwall", "floor_t - 0.5"],
              ["sen_x1 - plug_x1 - 1.0", "iwall", "rail_h + 0.5"], operation="join", targets=["base_plate"])


def wiper_profile(c: str = "0", hand: int = -1) -> list[tuple[str, str]]:
    """The inlet seal's plan (XY): a foot in the plate's slot (root_w, squeezed root_squeeze on its
    sides and back, B3), then the blade leaning wiper_deg away from the inlets from the plate's face
    to its tip on the port face. With `c` the outline grows by c all round (the floor groove): the
    blade's edges by c across them, its tip by c along it. wiper_x1 is the foot's edge on the
    inlets' side; `hand` -1 (airQ): the inlets right, the blade leans left; +1 (mini): mirrored."""
    tip = "sen_y1 - wiper_squeeze"
    rs = "root_squeeze"
    m, q = ("-", "+") if hand < 0 else ("+", "-")       # m: away from the inlets, q: toward them
    if c == "0":
        return [(f"wiper_x1 {m} root_w {m} {rs}", f"plate_y0 + seat_d + {rs}"), (f"wiper_x1 {q} {rs}", f"plate_y0 + seat_d + {rs}"),
                (f"wiper_x1 {q} {rs}", "plate_y0"), ("wiper_x1", "plate_y0"), (f"wiper_x1 {m} wiper_lean", tip),
                (f"wiper_x1 {m} wiper_lean {m} wiper_w", tip), (f"wiper_x1 {m} wiper_w", "plate_y0"), (f"wiper_x1 {m} root_w {m} {rs}", "plate_y0")]
    cn = f"{c} / cos(wiper_deg)"                     # across the blade
    ct = f"{c} * tan(wiper_deg)"                     # the tip moved c along the blade
    tipc = f"{tip} - {c}"
    return [(f"wiper_x1 {m} root_w {m} {rs} {m} {c}", f"plate_y0 + seat_d + {rs} + {c}"), (f"wiper_x1 {q} {rs} {q} {c}", f"plate_y0 + seat_d + {rs} + {c}"),
            (f"wiper_x1 {q} {rs} {q} {c}", "plate_y0"), (f"wiper_x1 {q} {cn}", "plate_y0"), (f"wiper_x1 {m} wiper_lean {q} {cn} {m} {ct}", tipc),
            (f"wiper_x1 {m} wiper_lean {m} wiper_w {m} {cn} {m} {ct}", tipc), (f"wiper_x1 {m} wiper_w {m} {cn}", "plate_y0"),
            (f"wiper_x1 {m} root_w {m} {rs} {m} {c}", "plate_y0")]


def top_seal(s: Script, hand: int = -1) -> None:
    """Review round 3 (the space beside the ring): `sen66_top_seal`, a foam strip stuck across the
    module's top at the inlet wiper's tip, from its port face to its connector face, closes the
    0.3 gap over the module there, so the space between the ring and the wiper no longer joins the
    inlets' side over the module's top-rear edge (a 5 mm path round the wiper); it joins only the
    front plenum, 21 mm forward through 0.2-0.3 slits, far from the inlets."""
    p = s.param
    p("top_seal_t", 0.6, "foam strip on the SEN66's top, free (0.2-0.5 gap over the module's +0.1/-0.2 height: 17-67 %)")
    p("top_seal_squeeze", "top_seal_t - zone_gap", "derived: the strip as modelled, free (R9: the check sets 0)")
    if hand < 0:
        p("top_seal_x0", "wiper_x1 - wiper_lean - wiper_w - 1.0", "top seal's left end: 1 mm past the wiper's tip")
        p("top_seal_x1", "wiper_x1 - wiper_lean + 1.0", "top seal's right end")
    else:
        p("top_seal_x0", "wiper_x1 + wiper_lean - 1.0", "top seal's left end: 1 mm short of the wiper's tip")
        p("top_seal_x1", "wiper_x1 + wiper_lean + wiper_w + 1.0", "top seal's right end: 1 mm past the wiper's tip")
    s.box("SEN66 top seal", ["top_seal_x0", "sen_y0", "sen_top"], ["top_seal_x1 - top_seal_x0", "sen_d", "zone_gap + top_seal_squeeze"],
          body="sen66_top_seal")


def gaskets(s: Script, hand: int = -1) -> None:
    """`gasket_out` (TPU 95A): the outlet ring, from the port face round the outlet into its seat
    in the plate; its land is the module's rear stop (I3(b)), pressed by the pad. `gasket_in`
    (TPU 95A): the blade on the port face between the inlets and the ring, from its groove in the
    floor to the zone wall, its root in its groove in the plate; a soft wiper (well under 2 N), so
    it cannot tip the module off the ring. They separate the port groups (I3). At ring_preload,
    wiper_squeeze and pad_squeeze 0 their faces touch the module (R9). `sen66_pad` (foam)."""
    s.cylinder("Outlet ring", ["outlet_x", "sen_y1 - ring_preload", "outlet_z"], "ring_od",
               "port_gap + seat_d + ring_preload", axis="Y", body="gasket_out")
    s.cylinder("Outlet ring bore", ["outlet_x", "sen_y1 - ring_preload - 1", "outlet_z"], "ring_bore",
               "port_gap + seat_d + ring_preload + 2", axis="Y", operation="cut", targets=["gasket_out"])
    with s.sketch("Inlet seal outline", "XY", offset="floor_t - seat_d") as sk:
        sk.polyline(wiper_profile(hand=hand))
    s.extrude("Inlet seal", "Inlet seal outline", "zw_z0 - floor_t + seat_d", body="gasket_in")
    tip = "sen_y1 - wiper_squeeze"
    lead_x = "wiper_x1 - wiper_lean - wiper_w - 1" if hand < 0 else "wiper_x1 - 1"
    with s.sketch("Inlet seal lead-in profile", "YZ", offset=lead_x) as sk:
        sk.polyline([(f"{tip} - 1", "zw_z0 - wiper_lead - 1"), (f"{tip} + wiper_lead + 1", "zw_z0 + 1"), (f"{tip} - 1", "zw_z0 + 1")])
    s.extrude("Inlet seal lead-in", "Inlet seal lead-in profile", "wiper_lean + wiper_w + 2", operation="cut", targets=["gasket_in"])
    s.box("SEN66 pad", ["outlet_x - pad_w / 2", "pad_y0", "outlet_z - pad_h / 2"], ["pad_w", "pad_gap + pad_squeeze", "pad_h"],
          body="sen66_pad")


def add_sen66_ports(s: Script, sen, hand: int = -1) -> None:
    """The SEN66's ports and connector in the enclosure frame (moved from airq.py in Task 4a).
    `sen` is ref_sen66's value function. hand -1 (airQ): the inlet end right, the square inlet
    high (module x -> -x, y -> -z); +1 (mini): the inlet end left, the square inlet low (module
    x -> +x, y -> +z: the same proper rotation turned 180 deg about y)."""
    p = s.param
    # ports from ref_sen66 (datasheet Fig. 8), module x from the inlet end, module y from the
    # square-inlet edge; turned so x -> -x (inlet end right), y -> -z (square inlet high)
    p("sen_out_x", sen("outlet_x"), "outlet centre from the inlet end (ref_sen66 outlet_x)")
    p("sen_out_y", sen("outlet_y"), "outlet centre from the square-inlet edge (ref_sen66 outlet_y)")
    p("outlet_d", sen("outlet_d"), "SEN66 outlet diameter (ref_sen66)")
    p("sen_sq_x0", sen("inlet_sq_x0"), "square inlet from the inlet end (ref_sen66)")
    p("sen_sq_x1", sen("inlet_sq_x1"), "square inlet to (ref_sen66)")
    p("sen_rd_x", sen("inlet_rd_x"), "round inlet centre from the inlet end (ref_sen66)")
    p("sen_rd_d", sen("inlet_rd_d"), "round inlet diameter (ref_sen66)")
    if hand < 0:
        p("outlet_x", "sen_x1 - sen_out_x", "derived: outlet centre x")
        p("outlet_z", "sen_top - sen_out_y", "derived: outlet centre z")
        p("inlet_x0", "min(sen_x1 - sen_sq_x1, sen_x1 - sen_rd_x - sen_rd_d / 2)", "derived: the inlets' left edge")
    else:
        p("outlet_x", "sen_x0 + sen_out_x", "derived: outlet centre x (inlet end left)")
        p("outlet_z", "floor_t + foam + sen_out_y", "derived: outlet centre z (square inlet low)")
        p("inlet_x1", "max(sen_x0 + sen_sq_x1, sen_x0 + sen_rd_x + sen_rd_d / 2)", "derived: the inlets' right edge")
    p("sen_plug_x0", 17.0, "SEN66 connector on its connector face, from the inlet end: scaled from datasheet Fig. 9 (README Frames); to confirm")
    p("sen_plug_x1", 29.0, "SEN66 connector to (scaled, to confirm)")
    if hand < 0:
        p("plug_x0", "sen_x1 - sen_plug_x1", "derived: SEN66 plug's left edge (world)")
        p("plug_x1", "sen_x1 - sen_plug_x0", "derived: SEN66 plug's right edge (world)")
    else:
        p("plug_x0", "sen_x0 + sen_plug_x0", "derived: SEN66 plug's left edge (world)")
        p("plug_x1", "sen_x0 + sen_plug_x1", "derived: SEN66 plug's right edge (world)")


def add_port_seals(s: Script, hand: int = -1) -> None:
    """The port seals' and the outlet ring's sizes (moved from airq.py in Task 4a; plate_y0 and
    sen_y1 come first). hand as for add_sen66_ports."""
    p = s.param
    p("seat_d", 1.0, "gasket seat depth: the TPU gaskets sit this deep in grooves in the plate and the floor")
    p("gasket_squeeze", 0.3, "TPU squeeze of the static seals and grommets as printed (R9: the check design sets 0, so the faces touch)")
    # I3(b): the SEN66 is 21.3 +-0.5 deep (datasheet Fig. 8). Its port face is the datum: the pad at
    # its front presses it back onto the outlet ring's land, a hard stop, at any depth; the pad
    # takes the tolerance (the seal does not), and its force acts on the ring's axis (no tipping)
    p("sen_d_tol", 0.5, "SEN66 depth tolerance, +- (datasheet Fig. 8: 21.3 +-0.5)")
    p("ring_preload", 0, "outlet ring land in front of the port face: 0, the ring is the module's rear stop (the pad's force is its seal load)")
    p("ring_w", 1.5, "outlet ring wall (gasket_out)")
    p("ring_clr", 0.25, "outlet ring bore over the port's edge")
    p("ring_bore", "outlet_d + 2 * ring_clr", "derived: outlet ring bore (R25: its area is the outlet path's narrowest)")
    p("ring_od", "ring_bore + 2 * ring_w", "derived: outlet ring outside diameter")
    p("wiper_t", 0.8, "inlet seal (gasket_in) blade thickness: a TPU wiper between the inlets and the ring, leaning away from the inlets")
    p("wiper_deg", 55, "inlet seal blade lean from the y axis: long and soft, so its push stays far under the pad's (B1)", unit="deg")
    p("wiper_squeeze", 0.5, "inlet seal blade preload on the port face (the port face is fixed by the ring; R9: the check sets 0)")
    p("wiper_w", "wiper_t / cos(wiper_deg)", "derived: blade width along x")
    if hand < 0:
        p("wiper_x1", "inlet_x0 - 1.0", "blade root's right edge, in its groove in the plate: 1 mm left of the inlets (H1 is left of it)")
    else:
        p("wiper_x1", "inlet_x1 + 1.0", "blade root's left edge (the inlets' side), in its groove in the plate: 1 mm right of the inlets")
    p("root_w", 2.0, "inlet seal's root (a foot in the plate's slot) width (B3)")
    p("root_squeeze", 0.05, "inlet seal root's squeeze on its slot's sides and back (B3: no bypass round it, no travel to eat the preload; R9: the check sets 0)")
    p("wiper_lead", 0.8, "inlet seal tip's 45 deg lead-in at its top: the module's bottom edge pushes the tip back as it goes down (B4)")
    p("wiper_lean", "(plate_y0 - sen_y1 + wiper_squeeze) * tan(wiper_deg)", "derived: blade tip's shift to the left over the gap")
