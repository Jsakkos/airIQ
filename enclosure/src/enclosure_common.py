"""Shared enclosure geometry for the airQ and the airQ mini (Plan 3 Tasks 3-4, ruling R22).

Both enclosures share one construction. Each function here adds named parameters and features over
shared parameter names, so Task 4 calls the same functions with the mini's values. The
construction is:
- a vertical lower front lip that carries the intake slots;
- a front face sloped at `tilt_deg` above the lip;
- the main board lying horizontal above the standing SEN66 (R17), with the zone wall between;
- the same print split: `shell` (lip, face, top and sides) prints face down, and `base_plate`
  (the floor and the rear wall, one L-shaped part) prints floor down.

The numbers that place the parts come from `layout_study` (one source for the study and the
model). Where a position follows another parameter, it is written here as an expression with the
same formula the study solves (for example the board's front edge, set by the LED faces' guide
room under the slope).

Frame R3: x = 0 at the width centre (+x to the user's right), y = 0 at the front bottom edge (+y
to the rear), z = 0 at the bottom plane, without the feet. On the slope, s is the distance up
the slope from the crease at z = lip, and t is the depth behind the slope's outer surface.
"""
from __future__ import annotations

import clearances
import layout_study as L
from sclib import Script, mechanical

MAIN = mechanical("main")
TONGUE = mechanical("tongue")
LS = "layout_study"


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
    p("inner_x", "W / 2 - wall", "derived: half the interior width")
    p("edge_chamfer", 0.8, "crisp chamfer on the crease and the top front edge (Paper look)")


def add_sen66(s: Script, m: L.Model, sen_x0: str, sen_y0: float, sen_y0_note: str = "") -> None:
    """The standing SEN66 (R17): long axis along x, port face vertical, facing the front."""
    r = L._refs()
    p = s.param
    p("sen_l", r["sen_l"], "SEN66 length along x (ref_sen66, datasheet Fig. 8)")
    p("sen_d", r["sen_h"], "SEN66 depth along y, port face to connector face (ref_sen66)")
    p("sen_up", r["sen_w"], "SEN66 height as it stands, its 25.6 width (ref_sen66, R17)")
    p("foam", m.foam, "plan: the SEN66 sits on 1 mm foam")
    p("sen_x0", sen_x0, "SEN66 inlet end (left), against the left wall")
    p("sen_y0", sen_y0, f"SEN66 port face (front); {LS} places it behind the tongue and inlet gasket{sen_y0_note}")
    p("sen_top", "floor_t + foam + sen_up", "derived: SEN66 top")
    p("gasket_t", 2.0, f"outlet ring depth in front of the port face (within {LS} sen_front 3.0; its top clears the zone wall)")


def add_zone_and_board(s: Script, m: L.Model, front_t_need: str, board_x0: str) -> None:
    """Zone wall over the SEN66 and the main board above it (horizontal, R22). The board's front
    edge is where its LED faces' corner meets the room the front needs (`front_t_need`, a depth
    behind the slope's outer surface): the corner that binds in `layout_study`."""
    p = s.param
    p("zone_gap", m.zone_gap, f"air gap above the SEN66 and under the board ({LS})")
    p("zone_t", m.zone_wall, "zone wall thickness, a wall")
    p("zw_z0", "sen_top + zone_gap", "derived: zone wall underside over the SEN66")
    p("zw_z1", "zw_z0 + zone_t", "derived: zone wall top")
    p("board_w", MAIN["outline"][0], "main board width (interface.yaml)")
    p("board_d", MAIN["outline"][1], "main board depth (interface.yaml)")
    p("board_t", MAIN["thickness"], "main board thickness (interface.yaml)")
    p("led_h", 2.0, "LED body height above the board (interface.yaml leds comment)")
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
    p("h1_x", "board_x0 + " + str(h1x), "H1 x (interface.yaml; 8 mm from the USB-C: the support boss)")
    p("h1_y", f"board_y0 + board_d - {h1y}", "H1 y (interface.yaml, layout Y from the rear edge)")
    p("h2_x", "board_x0 + " + str(h2x), "H2 x (interface.yaml)")
    p("h2_y", f"board_y0 + board_d - {h2y}", "H2 y (interface.yaml)")


def shell(s: Script, bosses: list[tuple[str, str]], rear_boss: tuple[str, str] | None = None) -> None:
    """`shell`: lip, sloped face, top and both sides in one part that prints face down on
    textured PEI. Its rear and bottom are open: `base_plate` (floor and rear wall) closes both.
    The insert bosses for the screws from underneath (R10b) stand on the base plate's top face and
    join the side walls. Their axis is vertical in use, inclined in print (Task 2 M7 note:
    confirmed at the first shell print)."""
    p = s.param
    p("boss_d", 6.0, "insert boss diameter (coupon R20)")
    p("boss_h", 6.8, "insert boss height above the floor")
    p("insert_d", 3.2, "M2 heat-set insert hole: coupon middle size, to confirm (R20)")
    p("insert_depth", 4.0, "insert hole depth (coupon R20)")
    with s.sketch("Envelope profile", "YZ", offset="-W / 2") as sk:
        sk.polyline([(0, 0), ("D", 0), ("D", "H"), ("y_top", "H"), (0, "lip")])
    s.extrude("Envelope", "Envelope profile", "W", body="shell")
    v = s.v
    # the top front edge only: the top rear edge borders the rear face the shell removes (its
    # inward offset would meet the rear wall), and the crease is now the seam to the base's lip
    s.chamfer("Edge chamfers", [[0, v("y_top"), v("H")]], "edge_chamfer", body="shell")
    s.shell("Shell walls", [[0, v("D") / 2, 0], [0, v("D"), v("H") / 2]], "wall")
    # R24: the lower front lip belongs to the base (a U printed floor down); the shell keeps the
    # sloped face, the top and the sides, and is lowered onto the base from above (+z down)
    s.box("Lip to the base", ["-W / 2 - 1", -1, -1], ["W + 2", "wall + 1", "lip + 1"], operation="cut", targets=["shell"])
    for i, (bx, by) in enumerate(bosses, 1):
        s.cylinder(f"Insert boss {i}", [bx, by, "floor_t"], "boss_d", "boss_h", operation="join", targets=["shell"])
        s.cylinder(f"Insert hole {i}", [bx, by, "floor_t - 0.5"], "insert_d", "insert_depth + 0.5",
                   operation="cut", targets=["shell"])
    if rear_boss:
        # a boss under the top wall at a rear corner, its insert entered from the rear: one M2
        # screw through the base's rear wall (the rear face may show a fastener; front and
        # sides may not)
        bx, bz = rear_boss
        s.param("rear_boss_len", 6.0, "rear insert boss length along y")
        s.cylinder("Rear insert boss", [bx, "D - wall - clr_remove - rear_boss_len", bz], "boss_d", "rear_boss_len",
                   axis="Y", operation="join", targets=["shell"])
        s.cylinder("Rear insert hole", [bx, "D - wall - clr_remove - insert_depth", bz], "insert_d",
                   "insert_depth + 0.5", axis="Y", operation="cut", targets=["shell"])


def panel_pocket(s: Script) -> None:
    """The panel's pocket in the slope (airQ), so the panel sits behind its window lip `bezel`.
    The window, holder and FFC path are Task 3b's. The pocket also takes the hatched block at the
    tail end."""
    s.param("pocket_x0", "panel_x0 - block_out - clr_remove", "derived: pocket left end (the hatched block)")
    s.param("pocket_x1", "panel_x0 + panel_l + clr_remove", "derived: pocket right end")
    # plane parallel to the slope at depth t = bezel: sketch x = world x, sketch y up the slope
    # (sketch y = s + lip cos_t on this plane), normal outward
    plane = {"origin": [0, 0, 0], "x_dir": [1, 0, 0], "y_dir": [0, s.v("sin_t"), s.v("cos_t")]}
    with s.sketch("Panel pocket outline", plane, offset="lip * sin_t - bezel") as sk:
        sk.rect("pocket_x0", "panel_s0 - clr_remove + lip * cos_t",
                "pocket_x1", "panel_s0 + panel_w + clr_remove + lip * cos_t")
    s.extrude("Panel pocket", "Panel pocket outline", "wall - bezel + 2", operation="cut",
              targets=["shell"], direction="negative")


def base_plate(s: Script, screw_xy: list[tuple[str, str]], rear_screw: tuple[str, str] | None = None) -> None:
    """`base_plate`: the floor and the rear wall, one L-shaped part, inset in the shell by
    clr_remove. It prints floor down, so its bosses and posts are vertical (coupons R20/M7) and
    its rear grilles are vertical slots. Screws go up through it into the shell's inserts, under
    the felt feet."""
    p = s.param
    p("screw_d", 2.4, "M2 screw clearance hole")
    p("head_d", 4.4, "M2 screw head counterbore, under a felt foot")
    p("head_depth", 0.4, "counterbore depth: leaves floor_t - 0.4 = 1.6 under the head (the felt foot covers it)")
    s.box("Floor", ["-inner_x + clr_remove", "wall / 2", 0],
          ["2 * (inner_x - clr_remove)", "D - 1.5 * wall", "floor_t"], body="base_plate")
    s.box("Front lip", ["-W / 2", 0, 0], ["W", "wall", "lip"], operation="join", targets=["base_plate"])
    s.box("Rear wall", ["-inner_x + clr_remove", "D - wall", 0],
          ["2 * (inner_x - clr_remove)", "wall", "H - wall - clr_remove"], operation="join", targets=["base_plate"])
    for i, (x, y) in enumerate(screw_xy, 1):
        s.cylinder(f"Screw hole {i}", [x, y, "-head_depth"], "screw_d", "floor_t + 2 * head_depth", operation="cut",
                   targets=["base_plate"])
        s.cylinder(f"Screw head {i}", [x, y, "-head_depth"], "head_d", "2 * head_depth", operation="cut", targets=["base_plate"])
    if rear_screw:
        x, z = rear_screw
        s.cylinder("Rear screw hole", [x, "D - wall - 1", z], "screw_d", "wall + 2", axis="Y", operation="cut",
                   targets=["base_plate"])
        s.cylinder("Rear screw head", [x, "D - head_depth", z], "head_d", "2 * head_depth", axis="Y", operation="cut",
                   targets=["base_plate"])


def standoffs(s: Script) -> None:
    """Board standoffs: posts on the floor up through the zone wall to the board's bottom, at H1
    (the USB-C support boss, interface.yaml: 8 mm from the USB-C) and H2. Joined to base_plate:
    they print vertical with it. The zone wall braces them where they pass through it."""
    for name, (x, y) in (("H1", ("h1_x", "h1_y")), ("H2", ("h2_x", "h2_y"))):
        s.cylinder(f"Standoff {name}", [x, y, "floor_t - 0.5"], "standoff_d", "board_z0 - floor_t + 0.5",
                   operation="join", targets=["base_plate"])
        s.cylinder(f"Standoff {name} pilot", [x, y, "board_z0 - pilot_depth"], "pilot_d", "pilot_depth + 1",
                   operation="cut", targets=["base_plate"])


def zone_wall(s: Script, boss_xy: list[tuple[str, str]] = ()) -> None:
    """`zone_wall`: the wall between the sensor zone (low) and the electronics zone (high). It
    has three parts:
    - a ledge behind the lip, between the intake slots and the LED slot;
    - a slanted part parallel to the slope at depth zw_tf, behind the panel, the light guide,
      the FFC and the adapter, which stay in the electronics zone;
    - a horizontal part over the SEN66, back to the rear wall.
    It spans the interior between the side walls. The standoffs pass through it."""
    p = s.param
    p("zw_tf", 7.2, "slanted part's front face depth behind the slope: behind the adapter (t 6.95) and light guide")
    p("ledge_t", 1.2, "ledge thickness")
    p("ledge_z1", "lip", "ledge top: at the crease, under the LED slot's inner edge")
    p("ledge_z0", "ledge_z1 - ledge_t", "derived: ledge underside, above the top slot row")

    def yf(z):     # y of the slanted part's front face at height z
        return f"(zw_tf + ({z} - lip) * sin_t) / cos_t"

    def yb(z):     # its back face
        return f"(zw_tf + zone_t + ({z} - lip) * sin_t) / cos_t"
    with s.sketch("Zone wall profile", "YZ", offset="-inner_x + clr_remove") as sk:
        sk.polyline([("wall + clr_remove", "ledge_z0"), (yb("ledge_z0"), "ledge_z0"), (yb("zw_z0"), "zw_z0"),
                     ("D - wall - clr_remove", "zw_z0"), ("D - wall - clr_remove", "zw_z1"), (yf("zw_z1"), "zw_z1"),
                     (yf("ledge_z1"), "ledge_z1"), ("(wall + clr_remove + (ledge_z1 - lip) * sin_t) / cos_t", "ledge_z1")])
    s.extrude("Zone wall", "Zone wall profile", "2 * (inner_x - clr_remove)", body="zone_wall")
    for name, (x, y) in (("H1", ("h1_x", "h1_y")), ("H2", ("h2_x", "h2_y"))):
        s.cylinder(f"Zone wall hole {name}", [x, y, "zw_z0 - 1"], "standoff_d + 2 * clr_align", "zone_t + 2",
                   operation="cut", targets=["zone_wall"])
    for i, (x, y) in enumerate(boss_xy, 1):     # the shell's floor bosses pass here on the way down
        s.box(f"Zone wall boss notch {i}", [f"{x} - boss_d / 2 - clr_remove", 0, "ledge_z0 - 1"],
              ["boss_d + 2 * clr_remove", f"{y} + boss_d / 2 + clr_remove", "zw_z1 - ledge_z0 + 2"],
              operation="cut", targets=["zone_wall"])


def sen66_cradle(s: Script) -> None:
    """`sen66_foam` (the plan's 1 mm foam, its own body), `sen66_cradle` (a rear rail on the
    floor) and `sen66_end_stop` (at the module's right end), which locate the module. The gaskets press it back against the rail,
    which stops short of the H1 standoff."""
    p = s.param
    p("rail_t", 1.6, "cradle rail thickness")
    p("rail_h", 4.0, "cradle rail height above the floor")
    s.box("SEN66 foam", ["sen_x0", "sen_y0", "floor_t"], ["sen_l", "sen_d", "foam"], body="sen66_foam")
    s.box("Cradle rear rail", ["sen_x0", "sen_y0 + sen_d + clr_align", "floor_t"],
          ["h1_x - standoff_d / 2 - clr_remove - sen_x0", "rail_t", "rail_h"], body="sen66_cradle")
    s.box("Cradle end stop", ["sen_x0 + sen_l + clr_align", "sen_y0", "floor_t"],
          ["rail_t", "sen_d + clr_align + rail_t", "rail_h"], body="sen66_end_stop")


def gasket_out(s: Script, outlet_x: str, outlet_z: str) -> None:
    """`gasket_out` (TPU 95A): a ring on the port face round the outlet, gasket_t deep, which
    seals it into the outlet duct (R9: its back face touches the module; no squeeze modelled)."""
    p = s.param
    p("ring_w", 1.5, "outlet ring wall")
    p("ring_clr", 0.25, "outlet ring inside the port's edge")
    s.cylinder("Outlet ring", [outlet_x, "sen_y0 - gasket_t", outlet_z], "outlet_d + 2 * ring_clr + 2 * ring_w",
               "gasket_t", axis="Y", body="gasket_out")
    s.cylinder("Outlet ring bore", [outlet_x, "sen_y0 - gasket_t - 1", outlet_z], "outlet_d + 2 * ring_clr",
               "gasket_t + 2", axis="Y", operation="cut", targets=["gasket_out"])


def gasket_in(s: Script, x0: str, x1: str) -> None:
    """`gasket_in` (TPU 95A): a wedge that seals the intake plenum along the SEN66's top front
    edge, between the port face and the zone wall's slanted back face. It closes the gap through
    which intake air would bypass the inlets over the module."""
    p = s.param
    p("wedge_h", 2.5, "seal height down the port face, above the high square inlet")

    def yb(z):
        return f"(zw_tf + zone_t + ({z} - lip) * sin_t) / cos_t"
    with s.sketch("Inlet seal profile", "YZ", offset=x0) as sk:
        sk.polyline([(yb("sen_top - wedge_h"), "sen_top - wedge_h"), ("sen_y0", "sen_top - wedge_h"),
                     ("sen_y0", "zw_z0"), (yb("zw_z0"), "zw_z0")])
    s.extrude("Inlet seal", "Inlet seal profile", f"{x1} - ({x0})", body="gasket_in")


def tongue_mount(s: Script, x1: str, y0: str, z0: str) -> None:
    """`tongue_mount`: a pedestal under the tongue's rear part, in the intake air behind the lip.
    It carries a locating pin through the tongue's M2 hole. The tongue lies turned 180 deg about
    z, so its front edge (VEML7700 window) faces the lip."""
    p = s.param
    hole = TONGUE["mounting_hole"]
    p("tongue_w", TONGUE["outline"][0], "tongue width (interface.yaml)")
    p("tongue_dp", TONGUE["outline"][1], "tongue depth (interface.yaml)")
    p("tongue_t", TONGUE["thickness"], "tongue thickness (interface.yaml)")
    p("tongue_x1", x1, "tongue right end (it lies turned 180 deg)")
    p("tongue_y0", y0, "tongue front edge, behind the lip")
    p("tongue_z0", z0, "tongue bottom, on the pedestal")
    p("tongue_hole_x", hole["center"][0], "tongue hole X (interface.yaml)")
    p("tongue_hole_y", hole["center"][1], "tongue hole Y (interface.yaml)")
    p("tongue_hole_d", hole["diameter"], "tongue hole diameter (interface.yaml)")
    p("pedestal_y0", 6.0, "pedestal starts this far behind the tongue's front edge (clear of the front insert boss)")
    s.box("Tongue pedestal", ["tongue_x1 - tongue_w", "tongue_y0 + pedestal_y0", "floor_t"],
          ["tongue_w", "tongue_dp - pedestal_y0", "tongue_z0 - floor_t"], body="tongue_mount")
    s.cylinder("Tongue pin", ["tongue_x1 - tongue_hole_x", "tongue_y0 + tongue_hole_y", "tongue_z0 - 0.5"],
               "tongue_hole_d - 2 * clr_align", "tongue_t + 1.5", operation="join", targets=["tongue_mount"])
