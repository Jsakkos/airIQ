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


def add_envelope(s: Script, m: L.Model) -> None:
    """The envelope and printing parameters every enclosure shares (the names the plan fixes)."""
    p = s.param
    p("W", m.W, f"outer width ({LS}; plan)", favorite=True)
    p("D", m.D, f"outer depth ({LS}; R22)", favorite=True)
    p("H", m.H, f"outer height ({LS}; R22)", favorite=True)
    p("tilt_deg", m.tilt_deg, "front slope from vertical (plan)", unit="deg", favorite=True)
    p("lip", m.lip, f"vertical lower front lip carrying the intake slots (R15, R22; {LS})", favorite=True)
    clearances.add_params(s)          # clr_align, clr_remove, clr_snap, slot_w, wall, flex_t, flex_len, flex_gap
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


def add_zone_and_board(s: Script, m: L.Model, front_t_need: str, board_x0: str) -> None:
    """Zone wall over the SEN66 and the main board above it (horizontal, R22). The board's front
    edge is where its LED faces' corner meets the room the front needs (`front_t_need`, a depth
    behind the slope's outer surface): the corner that binds in `layout_study`."""
    p = s.param
    p("zone_gap", m.zone_gap, f"air gap above the SEN66 and under the board ({LS})")
    p("zone_t", m.zone_wall, "zone wall thickness, a wall")
    p("zw_z0", "sen_top + zone_gap", "derived: zone wall underside over the SEN66")
    p("zw_z1", "zw_z0 + zone_t", "derived: zone wall top")
    p("zw_tf", 7.2, "zone wall's slanted part: front face depth behind the slope, behind the adapter (t 6.95) and light guide")
    p("ledge_t", 1.2, "zone wall ledge thickness")
    p("ledge_z1", "lip", "ledge top: at the crease, under the LED slot's inner edge")
    p("ledge_z0", "ledge_z1 - ledge_t", "derived: ledge underside, above the top slot row")
    p("seal_t", 1.2, "TPU strip between the ledge's front face and the lip (zone_seal)")
    p("board_w", MAIN["outline"][0], "main board width (interface.yaml)")
    p("board_d", MAIN["outline"][1], "main board depth (interface.yaml)")
    p("board_t", MAIN["thickness"], "main board thickness (interface.yaml)")
    p("led_h", B.led_body_h(), "LED body height above the board (interface.yaml leds comment, board_sources)")
    p("antenna_out", MAIN["antenna"]["overhang"], "antenna strip past the board's rear edge (interface.yaml)")
    p("board_clr", 0.5, "board edge to the side wall")
    p("board_z0", "zw_z1 + zone_gap", "derived: board bottom")
    p("front_t_need", front_t_need, f"depth behind the slope the LED faces need ({LS} 'guide' corner)")
    p("board_y0", "(front_t_need + (board_z0 + board_t + led_h - lip) * sin_t) / cos_t",
      f"derived: board front edge, the LED corner on the front constraint ({LS})")
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
    p("rear_boss_x", "-(inner_x - boss_d / 2 + 0.5)", "rear boss x (rear left, 69 mm from the antenna; R29)")
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
    # front face (y, where the side walls end). Everywhere else it keeps clr_remove from the base:
    # its side walls end clr_remove behind the lip's inner face, and its slope stops clr_remove
    # above the lip's top (a 0.2 parting line at the crease, into the electronics zone above the
    # ledge seal, not into the sensor zone)
    s.box("Lip to the base", ["-W / 2 - wall", "-wall", "-wall"], ["W + 2 * wall", "2 * wall + clr_remove", "lip + wall + clr_remove"],
          operation="cut", targets=["shell"])
    # the slope's inner corner hangs below the crease behind the lip: trim it to the same height, so
    # it clears the lip's top and the zone wall's ledge seal
    s.box("Crease seat", ["-inner_x", "wall - 0.1", "lip - wall"], ["2 * inner_x", "wall / cos_t - wall + 0.2 + clr_remove", "wall + clr_remove"],
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


def rails(s: Script) -> None:
    """The sensor zone's side walls in the base (`Side rail L/R`): under the zone wall's profile
    from the boss pockets to the rear wall, inside the shell's side walls. The zone wall rests on
    them (a lap), so its sides need no seal, and the HCHO grille is cut in the right one.
    `Boss pocket L/R`: walls round the shell's front floor bosses, so the bosses stay outside the
    sensor zone (the zone wall's ledge is notched over them)."""
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


def standoffs(s: Script) -> None:
    """Board standoffs: posts on the floor up to the zone wall's underside, at H1 (the USB-C
    support boss, interface.yaml: 8 mm from the USB-C) and H2, each with a collar and a spigot. The
    zone wall sits on them (a lap round the spigot) and carries a pad up to the board, so the
    board's M2 screws, through the zone wall into the posts' pilots, clamp the zone wall (N5).
    Joined to base_plate: they print vertical with it. H1 also merges with the plenum plate (airq),
    which braces it up to the zone wall (M7). The pilot holes are cut at the end."""
    for name, (x, y) in (("H1", ("h1_x", "h1_y")), ("H2", ("h2_x", "h2_y"))):
        s.cylinder(f"Standoff {name}", [x, y, "floor_t - 0.5"], "standoff_d", "zw_z0 - floor_t + 0.5",
                   operation="join", targets=["base_plate"])
        s.cylinder(f"Standoff {name} collar", [x, y, "zw_z0 - collar_h"], "standoff_d + 2 * collar_w", "collar_h",
                   operation="join", targets=["base_plate"])
        s.cylinder(f"Standoff {name} spigot", [x, y, "zw_z0 - 0.5"], "spigot_d", "spigot_h + 0.5",
                   operation="join", targets=["base_plate"])


def standoff_pilots(s: Script) -> None:
    for name, (x, y) in (("H1", ("h1_x", "h1_y")), ("H2", ("h2_x", "h2_y"))):
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


def zone_wall(s: Script) -> None:
    """`zone_wall`: the wall between the sensor zone (low) and the electronics zone (high):
    - a ledge behind the lip, between the intake slots and the LED slot; its front face carries
      the TPU `zone_seal` against the lip;
    - a slanted part parallel to the slope at depth zw_tf, behind the panel, the light guide, the
      FFC and the adapter, which stay in the electronics zone;
    - a horizontal part over the SEN66 and the outlet plenum, back to the rear wall.
    It rests on the base's tub (rails, boss pockets, plenum plate, rear-wall rib, standoff
    collars): laps all round. It sits on the standoffs' spigots and the board's screws clamp it
    there (N5); the front bosses pass its notches when the shell is lowered (I1)."""
    with s.sketch("Zone wall profile", "YZ", offset="-inner_x + clr_remove") as sk:
        sk.polyline([("wall + seal_t", "ledge_z0"), (yb("ledge_z0"), "ledge_z0"), (yb("zw_z0"), "zw_z0"),
                     ("D - wall - clr_remove", "zw_z0"), ("D - wall - clr_remove", "zw_z1"), (yf("zw_z1"), "zw_z1"),
                     (yf("ledge_z1"), "ledge_z1"), ("wall + seal_t", "ledge_z1")])
    s.extrude("Zone wall", "Zone wall profile", "2 * (inner_x - clr_remove)", body="zone_wall")
    for name, (x, y) in (("H1", ("h1_x", "h1_y")), ("H2", ("h2_x", "h2_y"))):     # N5: the board's screws clamp it here
        s.cylinder(f"Zone wall pad {name}", [x, y, "zw_z1 - 0.5"], "standoff_d", "board_z0 - zw_z1 + 0.5",
                   operation="join", targets=["zone_wall"])
        s.cylinder(f"Zone wall spigot seat {name}", [x, y, "zw_z0 - 1"], "spigot_d + 2 * clr_align", "spigot_h + clr_align + 1",
                   operation="cut", targets=["zone_wall"])
        s.cylinder(f"Zone wall screw hole {name}", [x, y, "zw_z0"], "screw_d", "board_z0 - zw_z0 + 1",
                   operation="cut", targets=["zone_wall"])
    for i, sx in enumerate(("-boss_x", "boss_x"), 1):     # the shell's floor bosses pass here on the way down
        s.box(f"Zone wall boss notch {i}", [f"{sx} - boss_d / 2 - clr_remove", "-wall", "ledge_z0 - 1"],
              ["boss_d + 2 * clr_remove", "boss_y + boss_d / 2 + clr_remove + wall", "zw_z1 - ledge_z0 + 2"],
              operation="cut", targets=["zone_wall"])


def zone_seal(s: Script) -> None:
    """`zone_seal` (TPU 95A): the strip between the ledge's front face and the lip's inner face,
    between the boss pockets. The intake slots leave no room for a lap there. R9: at
    gasket_squeeze 0 it touches both."""
    s.box("Zone seal", ["-bp_x0", "wall - gasket_squeeze", "ledge_z0"], ["2 * bp_x0", "seal_t + gasket_squeeze", "ledge_t"],
          body="zone_seal")
