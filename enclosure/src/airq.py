"""airq: the airQ enclosure (Plan 3 Task 3a, ruling R22): body and internals.

Layout: enclosure/README.md "Layout studies", from `layout_study` with R22's front.
- The envelope is 95 x 55 x 51.
- A 15 mm vertical lower lip carries the intake slots, with the 30 deg screen face above it.
- The board lies horizontal above the standing SEN66, with the zone wall between.
Shared construction: `enclosure_common` (Task 4 reuses it).

Bodies:
- printed: shell, base_plate (the floor and the rear wall, with the board standoffs), zone_wall,
  sen66_cradle, sen66_end_stop, outlet_duct and baffle (the outlet duct's walls), hcho_pocket (its
  grille is in the rear wall), tongue_mount;
- TPU: gasket_in, gasket_out;
- foam: sen66_foam.

Every position Task 3b needs is a named parameter here, even where 3a does not cut the feature.
These are the window, the LED slot and light guide, the adapter, the FFC route and service loop,
the dot and flexure on SW1's axis, the light-sensor window, the grilles and the USB-C opening.

The SEN66 stands with its port face forward and its inlet end on the user's left. Seen from the
front, that puts the square inlet high and the round inlet low (a proper rotation of
ref_sen66's frame). The intake plenum lies in front of the inlets (left) and under the zone
wall's ledge across the lip. The outlet blows forward into the outlet ring, runs right in a
layer in front of the module, back along its right end, and into the rear plenum behind the
rear grille (the baffle's walls).
"""
from __future__ import annotations

from dataclasses import replace

import enclosure_common as C
import layout_study as L
from sclib import Script

DESIGN = "airq"
OUTPUT = "airq.sc"

# R22: the study's lip layout, rounded: lip 15 fits D 55 (needs 54.62); the face needs H 50.1 in
# the study plus about 1 mm for the zone wall's ledge between the slots and the LED slot -> H 51
MODEL = replace(L.AIRQ, lip=15.0, H=51.0, D=55.0)


def build() -> Script:
    m = MODEL
    s = Script(DESIGN)
    p = s.param
    C.add_envelope(s, m)
    r = L._refs()

    # --- front face (Task 3b cuts these; 3a fixes them) ----------------------------------
    p("bezel", m.bezel, f"window lip in front of the panel ({C.LS})")
    p("panel_l", r["panel_l"], "panel length (ref_epd)")
    p("panel_w", r["panel_w"], "panel width, up the slope (ref_epd)")
    p("panel_t", r["panel_t"], "panel thickness (ref_epd, R16)")
    p("block_out", r["block_out"], "hatched block past the tail end (ref_epd; to confirm)")
    p("guide_t", m.guide_t, f"light guide thickness between the LED faces and the panel ({C.LS}, R20)")
    p("slot_bar", 1.2, "bar between the two intake slot rows on the lip")
    p("slot_row1_z", "grille_min_z", "intake slots, lower row bottom: the 10 mm line (on the lip)")
    p("slot_row2_z", "slot_row1_z + slot_w + slot_bar", "intake slots, upper row bottom (its top under the zone wall's ledge)")
    p("led_f0", 16.2, "LED slot lower edge, along the front (f): its inner edge above the ledge")
    p("led_h_slot", m.led_slot_h, "LED slot height on the face")
    p("led_len", 30.0, "LED line length (plan)")
    p("panel_s0", "led_f0 + led_h_slot + 1.4 - lip", "panel's lower edge, up the slope from the crease (1.2 face + 0.2 pocket)")
    p("panel_x0", "-inner_x + clr_remove + block_out", "panel's tail end (user's left), the hatched block at the wall")
    p("window_xc", "panel_x0 + panel_l - 2.70 - 67.50 / 2", "view-area centre x (ref_epd va_far, va_w): the LED line centres on it")

    # --- SEN66, zone wall, board ------------------------------------------------------------
    C.add_sen66(s, m, "-inner_x + clr_remove", 20.0)
    s.params["sen_y0"].comment += "; 1.8 behind the study's 18.2 so the high square inlet keeps a 3.4 mm path under the zone wall"
    p("outlet_d", 20.5, "SEN66 outlet diameter (ref_sen66)")
    p("outlet_x", "sen_x0 + 42.4", "outlet centre x (ref_sen66 outlet_x, inlet end left)")
    p("outlet_z", "sen_top - 12.8", "outlet centre z (ref_sen66 outlet_y, module y down)")
    C.add_zone_and_board(s, m, "bezel + panel_t + clr_remove + guide_t + clr_remove",
                         "inner_x - board_clr - board_w")
    C.add_standoffs(s)

    # --- face positions on SW1, the LEDs, J7, the tongue (Task 3b) ---------------------------
    p("sw_x", "board_x0 + 57.0", "SW1 actuator x (interface.yaml button): the dot and flexure axis")
    p("sw_z", "board_z0 + board_t + 1.7", "SW1 actuator centre z (interface.yaml button)")
    p("dot_f", "lip + (sw_z - lip) / cos_t", "dot centre along the front (f), on SW1's horizontal push axis")
    p("dot_d", 4.0, "orange dot diameter (top right, right of the panel pocket)")
    p("led_z", "board_z0 + board_t + 1.0", "LED light centre z (interface.yaml leds light_center_z)")
    p("j7_x0", "board_x0 + 28.8 - 7.75", "J7 mouth left end (interface.yaml fpc)")
    p("j7_x1", "board_x0 + 28.8 + 7.75", "J7 mouth right end")
    p("usb_x", "board_x0 + 16.2", "USB-C centre x (interface.yaml usb_c)")
    p("usb_z", "board_z0 + board_t + 3.16 / 2", "USB-C centre z")
    p("usb_well", "D - wall - (board_y0 + board_d)", "USB-C mouth inside the rear wall's inner face: the plug's well depth")
    p("usb_chamfer", 0.5, "USB-C opening chamfer (plan)")
    p("adapter_x", "panel_x0 + 10.0", "FPC adapter centre x: its tail ZIF takes the folded tail's stiffened end")
    p("adapter_s", "panel_s0 + 17.75", "FPC adapter centre up the slope: on the tail's centre line (ref_epd)")
    p("adapter_t", "bezel + panel_t + 1.55 + 0.2 + 3.0", "FPC adapter bottom face depth (folded tail 1.55, adapter 3.0)")
    p("ffc_len", 100.0, "FFC length: route about 45 (adapter to J7) + service loop about 50 to open the shell beside the base; a standard length")

    # --- tongue, HCHO pocket, ducts ----------------------------------------------------------
    p("baffle_x0", "outlet_x - 13.9", "outlet layer's left wall: right of the intake plenum, left of the outlet ring")
    p("duct_d", 4.0, "outlet layer depth between its front wall and the outlet ring")
    p("sfa_x0", "-inner_x + clr_remove + 1.5", "SFA40 board's left edge (standing, facing the rear wall)")
    p("sfa_y0", "D - wall - 0.3 - 4.5", "SFA40 board's back face (4.5 deep with its parts)")
    p("sfa_z0", "floor_t + 0.5", "SFA40 board's lower edge")
    p("hcho_x1", "sfa_x0 + 25.4 + 5.2", "HCHO pocket's right wall: room for the Qwiic plug at J1")

    # --- bodies -------------------------------------------------------------------------------
    inner = "inner_x - boss_d / 2 + 0.5"
    C.shell(s, [(f"-({inner})", "wall + 3.0"), (inner, "wall + 3.0"), (inner, "D - wall - 4.5")])
    C.panel_pocket(s)
    C.base_plate(s, [(f"-({inner})", "wall + 3.0"), (inner, "wall + 3.0"), (inner, "D - wall - 4.5")])
    C.standoffs(s)
    # HCHO pocket's own grille: vertical slots in the rear wall, in front of the SFA40's opening
    p("hcho_slot_h", 14.0, "HCHO grille slot length (z)")
    p("hcho_slot_x", "sfa_x0 + 6.5", "first HCHO grille slot x")
    for i in range(4):
        s.box(f"HCHO grille slot {i + 1}", [f"hcho_slot_x + {i} * 3.0", "D - wall - 1", "grille_min_z + 1"],
              ["slot_w", "wall + 2", "hcho_slot_h"], operation="cut", targets=["base_plate"])
    C.zone_wall(s)
    C.sen66_cradle(s)
    C.gasket_out(s, "outlet_x", "outlet_z")
    C.gasket_in(s, "sen_x0", "baffle_x0 - wall")
    C.tongue_mount(s, "baffle_x0 - wall - 0.2", "wall + 0.4", "floor_t + 7.0")
    p("lsw_x", "tongue_x1 - 18.35", "light-sensor window x: the tongue's VEML7700 window (interface.yaml; tongue turned 180 deg)")
    p("lsw_z", "tongue_z0 + tongue_t + 1.95", "light-sensor window z: the VEML7700 window centre (interface.yaml)")
    p("lsw_d", 2.5, "light-sensor window diameter (on the lip, left of the slots)")
    hcho_pocket(s)
    baffle(s)
    return s


def _slant_z(y: str) -> str:
    """Height where the zone wall's slanted back face is at depth y."""
    return f"lip + ({y} * cos_t - zw_tf - zone_t) / sin_t"


def baffle(s: Script) -> None:
    """The outlet duct's walls, in two printed pieces.
    - `outlet_duct`: the front layer's walls. They take the outlet air from the outlet ring,
      right along the module's front, to its right end, and seal it from the intake plenum (in
      front and on the left).
    - `baffle`: the wall in front of the rear outlet grille. With a wall beside the cable bay
      behind the module, it closes the rear plenum (outlet grille behind a baffle, plan). The air
      reaches the rear plenum along the module's right end."""
    fy0, fy1 = "sen_y0 - gasket_t - duct_d - wall", "sen_y0 - gasket_t - duct_d"
    with s.sketch("Duct front wall profile", "YZ", offset="baffle_x0 - wall") as sk:
        sk.polyline([(fy0, "floor_t"), (fy1, "floor_t"), (fy1, _slant_z(fy1)), (fy0, _slant_z(fy0))])
    s.extrude("Duct front wall", "Duct front wall profile", "inner_x - clr_remove - (baffle_x0 - wall)", body="outlet_duct")
    with s.sketch("Duct left wall profile", "YZ", offset="baffle_x0 - wall") as sk:
        sk.polyline([(fy1, "floor_t"), ("sen_y0", "floor_t"), ("sen_y0", "zw_z0"),
                     ("(zw_tf + zone_t + (zw_z0 - lip) * sin_t) / cos_t", "zw_z0"), (fy1, _slant_z(fy1))])
    s.extrude("Duct left wall", "Duct left wall profile", "wall", operation="join", targets=["outlet_duct"])
    s.box("Rear plenum front wall", ["hcho_x1", "hcho_y0 - wall", "floor_t"],
          ["sen_x0 + sen_l + clr_align + rail_t + wall - hcho_x1", "wall", "zw_z0 - floor_t"], body="baffle")
    s.box("Cable bay right wall", ["sen_x0 + sen_l + clr_align + rail_t", "sen_y0 + sen_d", "floor_t"],
          ["wall", "hcho_y0 - (sen_y0 + sen_d)", "zw_z0 - floor_t"], operation="join", targets=["baffle"])


def hcho_pocket(s: Script) -> None:
    """`hcho_pocket`: the SFA40's sealed pocket at the rear left, in the sensor zone (airQ only).
    The SFA40 stands with its opening facing its own grille in the rear wall. The zone wall above,
    the floor, the left side wall and the rear wall close it."""
    s.param("hcho_y0", "sfa_y0 - clr_remove", "derived: HCHO pocket's front wall back face")
    s.box("HCHO pocket front wall", ["-inner_x + clr_remove", "hcho_y0 - wall", "floor_t"],
          ["hcho_x1 - (-inner_x + clr_remove)", "wall", "zw_z0 - floor_t"], body="hcho_pocket")
    s.box("HCHO pocket side wall", ["hcho_x1 - wall", "hcho_y0", "floor_t"],
          ["wall", "D - wall - clr_remove - hcho_y0", "zw_z0 - floor_t"], operation="join", targets=["hcho_pocket"])
