"""airq_mini: the airQ mini enclosure (Plan 3 Task 4a, owner decision 69.5 x 50 x 42, R51): body
and internals. Task 4b adds the split light band, the labels, the light-sensor window, the dot
and its flexure, the openings and the full check table on the positions fixed here.

Layout: enclosure/README.md "airQ mini (Task 4)" (`layout_study.mini_recheck(MINI_WAY_OUT,
inlet_end="left")`, place a) and "airQ mini enclosure".
- The envelope is 69.5 x 50 x 42 with the 24 deg face. The vertical lower front lip carries the
  intake slots; it is 18.0 here, not the study's 15.5 (a judgement call, README): three slot rows
  must fit under the zone wall's ledge to reach the intake's 154.5 mm2, and the SEN66's plug and
  its cable's bend must clear the slant at place a.
- The board lies horizontal above the standing SEN66 (R17), against the right wall, as far back
  as its antenna allows. The zone wall's slant hugs the slope (the mini has no panel or FFC).
Shared construction: `enclosure_common` (the airQ's, with `hand` +1 for the mirrored sensor
zone). Board positions: `board_sources` (R27).

SEN66 pose (R31, the study): the port face looks to the REAR, the inlet end on the user's LEFT
(the square inlet low). The outlet blows straight back through `gasket_out` into the outlet
plenum behind the plate; H1's post stands in the plenum, just behind the plate (place a). The
inlets draw from the sensor zone through the intake passage between the module's left end and
the left rail, then the port gap. `gasket_in` (the wiper) separates the inlets from the ring.

The tongue stands on edge in the intake passage, its board's back to the left rail, its parts
(and its VEML7700, looking forward) toward the module's left end. Its handedness puts the
VEML7700 high (z ~20.5, the board's long edge vertical): it looks forward and down to the
light-sensor window low on the lip (4b). It hangs on `tongue_mount`, a pin in the left rail
through its mounting hole; the module's end keeps it on the pin. J3 is blocked by the slope
(1.6 mm of plug room), so the tongue plugs into J4 (R30, same I2C nets).

Cables: J2 (the SEN66) and J4 (the tongue) leave the board's left edge; both cables pass the zone
wall in one drawer (a notch open to its left end) over the passage's rear, sealed by a split
grommet (`grommet_zone_a` outer, `grommet_zone_b` inner) laid round them with the plugs on.

Bodies:
- printed: shell; base_plate (floor, lip, rear wall, side rails, boss pockets risen to the slant,
  H1's standoff and its web to the plate, the plenum plate, the pad's seat, the module's left
  stop); zone_wall (clamped by the board's screw at H1, the board's H2 screw in a blind pilot in
  it: H2 lies over the module, so it has no post); tongue_mount (the tongue's pin);
- TPU 95A: gasket_out, gasket_in, grommet_zone_a/_b;
- foam: sen66_foam, sen66_pad, zone_seal, sen66_top_seal.
Felt feet are bought (positions here).

Every position Task 4b needs is a named parameter here, even where 4a does not cut the feature.
"""
from __future__ import annotations

from dataclasses import replace

import airq_face as F
import airq_mini_face as MF
import board_sources as B
import enclosure_common as C
import layout_study as L
import ref_sen66
from sclib import Script

DESIGN = "airq-mini"
OUTPUT = "airq-mini.sc"

# Owner decision (R51): the study's way out, 69.5 x 50 x 42, inlet end left, place a. Lip 18.0
# (study 15.5): three 1.2 slot rows from the 10 mm line need ledge_z0 >= 16.0 (+0.8 here), and at
# 15.5 the SEN66's plug top corner would meet the slant 0.7 deep at place a (README).
MODEL = replace(L.MINI_WAY_OUT, lip=18.0)
HAND = 1            # the sensor zone mirrored from the airQ: inlet end left (enclosure_common)
INTAKE_OPEN = "3 * in_n * in_len * slot_w"                 # the intake rows' open area (R18 >= 154.5), mm2
OUTLET_OPEN = "out_n * slot_w * (out_gz1 - out_gz0)"       # the outlet grille's open area (R18), mm2


def build() -> Script:
    m = MODEL
    s = Script(DESIGN)
    p = s.param
    C.add_envelope(s, m)
    sen = ref_sen66.build().v
    main = B.MAIN

    # --- SEN66, zone wall, board, bosses ---------------------------------------------------
    C.add_sen66(s, m)
    C.add_zone_and_board(
        s, m, None, "inner_x - board_clr - board_w",
        zw_tf=("wall + clr_remove", "zone wall's slanted part hugs the slope: its front face clr_remove behind the slope's inner face (no panel or FFC in the mini; Task 4a study)"),
        board_clr=("clr_remove", "board's right edge to the right side wall: against it, so J2 and J4 on the left edge get the most plug room (Task 4a study)"),
        board_y0=("D - wall - clr_remove - antenna_out - board_d", "board front edge: as far back as the antenna strip allows, its end clr_remove inside the rear wall (Task 4a study)"))
    C.add_standoffs(s)
    C.add_bosses(s)
    p("zw_pilot_depth", 1.6, "H2: blind M2 pilot from the pad's top into the zone wall (pad 0.3 + 1.3), 0.5 of zone wall left under it; an M2 x 3 screw takes 1.4 of thread")
    p("sen_x1", "tub_x - clr_remove", "SEN66 outlet end (right), beside the right rail")
    p("sen_x0", "sen_x1 - sen_l", "SEN66 inlet end (left): the intake passage between it and the left rail")
    p("passage", "sen_x0 + tub_x", "derived: the intake passage's width (Task 4a study 6.9)")
    p("port_gap", 3.0, "port face to the plenum plate: the inlets' air path (R25: 3.0 x 26.9 = 80.7 >= 77.3)")
    p("plate_y1", "h1_y - standoff_d / 2 - clr_align", "plenum plate back face: just in front of H1's post (place a, Task 4a study); a web joins them")
    p("plate_y0", "plate_y1 - iwall", "derived: plenum plate front face (the baffle in front of the outlet grille)")
    p("sen_y1", "plate_y0 - port_gap", "derived: SEN66 port face (rear)")
    p("sen_y0", "sen_y1 - sen_d", "derived: SEN66 connector face (front)")
    C.add_sen66_ports(s, sen, hand=HAND)
    C.add_port_seals(s, hand=HAND)
    # the SEN66's plug and its cable's bend in front of the connector face (the airQ check's keep-out sizes, named)
    p("sen_plug_out", 6.0, "SEN66 plug (JST GH 6) out of the connector face; to confirm")
    p("sen_plug_h", 5.0, "SEN66 plug's height envelope, centred on the module's mid height; to confirm")
    p("sen_bend_out", 6.94, "SEN66 plug and its cable's bend down, out of the connector face (airq_check ko_sen66_bend)")
    p("sen_bend_top", 0.7, "the bend's top above the module's mid height (airq_check ko_sen66_bend)")
    p("sen_mid", "sen_top - sen_up / 2", "derived: the module's mid height (its plug's centre)")

    # --- tongue on edge in the passage, its pin (tongue_mount) -----------------------------
    tg = B.TONGUE
    hole, veml, qw = tg["mounting_hole"], tg["veml7700"]["window_center"], tg["qwiic"]
    p("tongue_w", tg["outline"][0], "tongue length, its long (VEML7700) edge: vertical here (interface.yaml)")
    p("tongue_dp", tg["outline"][1], "tongue depth along y (interface.yaml)")
    p("tongue_t", tg["thickness"], "tongue thickness (interface.yaml)")
    p("tongue_parts_h", tg["max_part_height"], "tongue's tallest part (interface.yaml)")
    p("tongue_hole_x", hole["center"][0], "tongue hole X along its long edge (interface.yaml)")
    p("tongue_hole_y", hole["center"][1], "tongue hole Y from its front edge (interface.yaml)")
    p("tongue_hole_d", hole["diameter"], "tongue hole diameter (interface.yaml)")
    p("tongue_hole_clear", hole["clear_diameter"], "tongue hole's copper-free circle (interface.yaml)")
    p("veml_x", veml[0], "VEML7700 window centre X along the long edge (interface.yaml)")
    p("veml_y", veml[1], "VEML7700 window centre Y from the front edge (interface.yaml)")
    p("veml_z", veml[2], "VEML7700 window centre above the tongue's top face (interface.yaml)")
    p("tq_x0", qw["body"][0][0], "tongue Qwiic body X from (interface.yaml)")
    p("tq_x1", qw["body"][1][0], "tongue Qwiic body X to (interface.yaml)")
    p("tq_mate", qw["mating_face_y"], "tongue Qwiic mating face Y: the plug enters from the rear (interface.yaml)")
    p("tq_h", B.connector_h("qwiic", board="tongue"), "tongue Qwiic body height (interface.yaml comment)")
    p("tongue_plug_out", 4.5, "Qwiic plug out of the tongue's mating face (airq_check ko_tongue_plug); to confirm")
    p("cable_gh_d", 3.0, "SEN66 cable (JST GH, 6 wires) bundle diameter; to confirm")
    p("cable_qw_d", 2.4, "Qwiic cable diameter; to confirm")
    p("tongue_x0", "sen_x0 - clr_remove - clr_align - tongue_t - tongue_parts_h",
      "tongue board's back face (toward the left rail); its parts face the module's left end, clr_remove + clr_align from it")
    p("tongue_y0", "bp_y1 + clr_align + cable_gh_d + clr_align",
      "tongue's front edge (VEML7700 forward): behind the SEN66 cable's drop at the passage's front, which is behind the left boss pocket")
    p("tongue_z0", "floor_t + clr_align", "tongue's bottom (its long edge vertical, X = 0 down): clr_align over the floor, which stops it turning on its pin")
    p("tongue_top", "tongue_z0 + tongue_w", "derived: tongue's top edge (the SEN66 cable passes over it)")
    p("veml_wx", "tongue_x0 + tongue_t + veml_z", "derived: VEML7700 window centre x")
    p("veml_wy", "tongue_y0 + veml_y", "derived: VEML7700 window centre y")
    p("veml_wz", "tongue_z0 + veml_x", "derived: VEML7700 window centre z")
    p("tm_y", "tongue_y0 + tongue_hole_y", "derived: the tongue's pin, y")
    p("tm_z", "tongue_z0 + tongue_hole_x", "derived: the tongue's pin, z")
    p("tm_pin_d", "tongue_hole_d - 2 * clr_align", "tongue pin (tongue_mount) diameter: through the tongue's hole and into the rail")
    p("tm_collar_d", "tongue_hole_clear - 2 * clr_remove", "tongue pin collar diameter: inside the hole's copper-free circle")
    p("tm_hole_depth", 1.0, "the pin's blind hole in the left rail (0.6 of rail behind it: no leak to the outside of the tub)")
    p("tm_out", 0.6, "the pin past the tongue board's top face: it stays in the hole if the tongue slides to the module (clr_remove + clr_align)")

    # --- the zone wall's cable drawer over the passage's rear (J2 and J4) -------------------
    p("cab_x", "-tub_x + cable_gh_d / 2 + clr_align", "cables' line through the drawer, x: left of the board's edge, right of the rail")
    p("tq_plug_y1", "tongue_y0 + tq_mate + tongue_plug_out", "derived: the tongue's Qwiic plug's rear end")
    p("qw_y", "tq_plug_y1 + clr_align + cable_qw_d / 2", "J4 Qwiic cable through the drawer, y: just behind the tongue's plug")
    p("gh_y", "qw_y - cable_qw_d / 2 - 0.8 - cable_gh_d / 2", "SEN66 cable through the drawer, y: in front of the Qwiic, 0.8 of TPU between")
    p("dr_y0", "gh_y - cable_gh_d / 2 - 0.8", "drawer notch's front face: 0.8 of TPU in front of the SEN66 cable")
    p("dr_y1", "qw_y + cable_qw_d / 2 + 0.8", "drawer notch's rear face")
    p("dr_x1", "cab_x + cable_gh_d / 2 + 0.8", "drawer notch's closed end (right), under the board's left edge")
    p("groove_d", 0.6, "drawer grooves' depth into the notch's faces (along y)")
    p("groove_w", 0.8, "drawer grooves' height, centred in the zone wall's thickness")
    p("drawer_squeeze", 0.05, "TPU squeeze of the drawer grommet's faces (the airQ's B6 value; R9: the check sets 0)")
    p("bore_squeeze", 0.2, "grommet bores under the cable's diameter (they hug the cable; R9: the check sets 0)")
    cable_params(s)

    # --- the cradle, the stop, the plenum -------------------------------------------------
    p("stop_l", 2.0, "the module's left-end stop at its rear-left corner, along y")
    p("stop_h", 4.0, "the left-end stop's height above the floor (under the tongue's plug)")
    p("h1_web_w", 2.0, "web from the plate's back face to H1's post (braces the post, M7)")

    # --- bodies ------------------------------------------------------------------------------
    C.shell(s)
    C.base_plate(s)
    # --- face and openings: positions Task 4b needs (after base_plate: its screw and rib sizes) --
    face_params(s)
    opening_params(s)
    feet_params(s)
    C.rails(s, slant_front=True)
    C.standoffs(s, ("H1",))
    C.plenum(s)
    s.box("H1 web", ["h1_x - h1_web_w / 2", "plate_y1 - 0.5", "floor_t - 0.5"], ["h1_web_w", "h1_y - plate_y1 + 0.5", "zw_z0 - floor_t + 0.5"],
          operation="join", targets=["base_plate"])
    p("pad_gap_nom", 1.8, "the pad's thickness at the nominal module: 44 % of pad_t, as the airQ's")
    C.cradle(s, seat_y0=("sen_y0 - pad_gap_nom - seat_t", "pad seat's front face: the pad at 44 % at the nominal module (as the airQ's)"),
             seat_slant_clr=("clr_remove", "derived: the seat's top clr_remove under the slant"),
             seat_x=("plug_x1 + 1.0", "bp_x0 + iwall - plug_x1 - 1.0"), front_rail=False)
    s.box("Left stop", ["sen_x0 - clr_remove - iwall", "sen_y1 - stop_l", "floor_t - 0.5"], ["iwall", "stop_l", "stop_h + 0.5"],
          operation="join", targets=["base_plate"])
    C.standoff_pilots(s, ("H1",))
    C.base_screws(s)
    C.base_side_clearance(s)
    base_cuts(s)
    C.zone_wall(s, blind=("H2",))
    zone_drawer(s)
    C.zone_seal(s)
    s.box("SEN66 foam", ["sen_x0", "sen_y0", "floor_t"], ["sen_l", "sen_d", "foam"], body="sen66_foam")
    C.gaskets(s, hand=HAND)
    C.top_seal(s, hand=HAND)
    tongue_mount(s)
    grommets(s)
    # --- Task 4b: the split light band (airq_mini_face) ---------------------------------------
    MF.guide_params(s)
    MF.band_slots(s)
    MF.band_ribs(s)
    MF.light_guides(s)
    MF.guide_stop(s)
    MF.label_params(s)
    MF.labels(s)
    # the dot on SW1's push axis and its flexure: the airQ's (airq_face), on the mini's sw_x, sw_z, dot_f
    F.flex_params(s)
    F.flexure(s)
    F.orange_dot(s)
    openings(s)
    return s


def openings(s: Script) -> None:
    """Task 4b: the openings in `base_plate`, cut last (every join is done), at the positions 4a fixed;
    each opening's lower edge is at least grille_min_z (the shell's band slots and the flexure's U slot
    are higher still).
    - the intake rows in the lower front lip: three rows of in_n slots, slot_w high, slot_bar bars,
      from right of the light-sensor window to the right boss pocket, under the zone wall's ledge;
    - the light-sensor window: a round hole in the lip in front of the tongue's VEML7700, low and left
      of the rows, so the sensor's line to it (about 30 deg down: the tongue's handedness puts the
      VEML7700 high) passes under the ledge and the zone seal;
    - the outlet grille in the lower rear wall, behind the plenum plate (R18: 498 mm2, the study's
      shortfall against 660.1, over the 296 floor; owner item);
    - the electronics exhaust in the upper rear wall, over the zone wall's top: into the electronics
      zone only, apart from the outlet (R26);
    - the USB-C opening in the rear wall on J1's plug axis, passing the plug's overmold, with a 0.5
      chamfer on its outer edge; H1's post is its support boss (4a)."""
    p = s.param
    for row in (1, 2, 3):
        for i in range(int(s.v("in_n"))):
            s.box(f"Intake slot {row}.{i + 1}", [f"row_x0 + {i} * (in_len + slot_bar)", "-wall", f"slot_row{row}_z"], ["in_len", "3 * wall", "slot_w"],
                  operation="cut", targets=["base_plate"])
    s.cylinder("Light-sensor window", ["lsw_x", "-wall", "lsw_z"], "lsw_d", "3 * wall", axis="Y", operation="cut", targets=["base_plate"])
    for i in range(int(s.v("out_n"))):
        s.box(f"Outlet slot {i + 1}", [f"out_gx0 + {i} * out_pitch", "D - 2 * wall", "out_gz0"], ["slot_w", "3 * wall", "out_gz1 - out_gz0"],
              operation="cut", targets=["base_plate"])
    p("exh_n", 13, "electronics exhaust slot count: 13 x 2.4 - 1.2 = 30.0 fits exh_x0 ... exh_x1 (31.95); whole number", unit="")
    p("exh_gx1", "exh_x0 + exh_n * out_pitch - (out_pitch - slot_w)", "derived: the exhaust's last slot's right edge")
    for i in range(int(s.v("exh_n"))):
        s.box(f"Exhaust slot {i + 1}", [f"exh_x0 + {i} * out_pitch", "D - 2 * wall", "exh_z0"], ["slot_w", "3 * wall", "exh_z1 - exh_z0"],
              operation="cut", targets=["base_plate"])
    p("usb_open_w", "usb_plug_w + 2 * clr_remove", "USB-C opening width: the overmold passes (its tip is in the wall's thickness, usb_well)")
    p("usb_open_h", "usb_plug_h + 2 * clr_remove", "USB-C opening height")
    s.box("USB-C opening", ["usb_x - usb_open_w / 2", "D - 2 * wall", "usb_z - usb_open_h / 2"], ["usb_open_w", "3 * wall", "usb_open_h"],
          operation="cut", targets=["base_plate"])
    v = s.v
    d, cx, cz = v("D"), v("usb_x"), v("usb_z")
    hw, hh = v("usb_open_w") / 2, v("usb_open_h") / 2
    s.chamfer("USB-C chamfer", [[cx, d, cz - hh], [cx, d, cz + hh], [cx - hw, d, cz], [cx + hw, d, cz]], "usb_chamfer", body="base_plate")


def cable_params(s: Script) -> None:
    """The plugs on the board's left edge (interface.yaml): their envelopes for the routes."""
    p = s.param
    j2, j4 = B.MAIN["j_sen66"], B.MAIN["j_qwiic_aux"]
    p("j2_y0", f"board_y0 + board_d - {j2['body'][1][1]}", "J2 (SEN66) body's front end, y (interface.yaml)")
    p("j2_y1", f"board_y0 + board_d - {j2['body'][0][1]}", "J2 body's rear end, y (interface.yaml)")
    p("j4_y0", f"board_y0 + board_d - {j4['body'][1][1]}", "J4 (tongue Qwiic) body's front end, y (interface.yaml)")
    p("j4_y1", f"board_y0 + board_d - {j4['body'][0][1]}", "J4 body's rear end, y (interface.yaml)")
    p("j2_face_x", f"board_x0 + {j2['mating_face_x']}", "J2 mating face x (interface.yaml; faces -x)")
    p("j4_face_x", f"board_x0 + {j4['mating_face_x']}", "J4 mating face x (interface.yaml; faces -x)")
    p("j2_h", B.connector_h("j_sen66"), "J2 body height (interface.yaml comment)")
    p("j4_h", B.connector_h("j_qwiic_aux"), "J4 body height (interface.yaml comment)")
    p("plug_out", 5.0, "a side-entry plug and its cable's bend out of the mating face (the airQ's ko_j2_plug / ko_j4_plug); to confirm")
    p("j2_room", "j2_face_x - plug_out - (-inner_x + clr_remove)", "derived: J2's room left after its plug (Task 4a study 5.85 - 5.0)")
    p("j4_room", "j4_face_x - plug_out - (-inner_x + clr_remove)", "derived: J4's room left after its plug (study 6.14 - 5.0)")


def face_params(s: Script) -> None:
    """Positions on the sloped face Task 4b needs (spec section 6.5): the split light band over
    the LED pairs (CO2: D1/D2, PM2.5: D3/D4, `mechanical.main.leds.chain`), the divider between
    the halves, the labels under them, the dot on SW1's axis. f is the distance along the front
    from the bottom edge (the lip, then up the slope)."""
    p = s.param
    main = B.MAIN
    chain = {d["ref"]: d for d in main["leds"]["chain"]}
    for ref in ("D1", "D2", "D3", "D4"):
        p(f"{ref.lower()}_x", f"board_x0 + {chain[ref]['center_x']}", f"{ref} centre x ({chain[ref]['half']} half; interface.yaml leds.chain)")
    g0, g1 = main["leds"]["divider_gap"]
    p("div_x0", f"board_x0 + {g0}", "divider gap's left end: no LED between here and div_x1 (interface.yaml leds.divider_gap)")
    p("div_x1", f"board_x0 + {g1}", "divider gap's right end (interface.yaml)")
    p("led_cz", main["leds"]["light_center_z"], "LED light centre above the board (interface.yaml leds)")
    p("led_z", "board_z0 + board_t + led_cz", "LED light centre z")
    p("led_f", "lip + (led_z - lip) / cos_t", "LED light centre's height along the front (f): the band's centre line")
    p("band_half", 20.5, "each half's visible length (plan: about 21 mm; 20.5 so the PM2.5 half's end rib and 1.35 of opaque face stand between it and the flexure's slot, Task 4b)")
    p("band_h", 2.0, "the band's visible height along the slope")
    p("band_co2_x0", "(d1_x + d2_x) / 2 - band_half / 2", "CO2 half, left end: centred on D1/D2")
    p("band_co2_x1", "(d1_x + d2_x) / 2 + band_half / 2", "CO2 half, right end")
    p("band_pm_x0", "(d3_x + d4_x) / 2 - band_half / 2", "PM2.5 half, left end: centred on D3/D4")
    p("band_pm_x1", "(d3_x + d4_x) / 2 + band_half / 2", "PM2.5 half, right end")
    p("band_gap", "band_pm_x0 - band_co2_x1", "derived: the visible gap between the halves (plan >= 4)")
    p("band_f0", "led_f - band_h / 2", "band's lower edge along the front")
    p("band_f1", "led_f + band_h / 2", "band's upper edge along the front")
    p("divider_t", 1.2, "opaque divider between the halves' guides (plan >= 1.2)")
    p("label_h", 5.0, "label text height (Task 2 coupon: >= 5 mm legible at 0.4 deboss)")
    p("label_depth", 0.4, "label deboss depth (plan)")
    p("label_f1", "band_f0 - 1.2", "labels' top along the front: 1.2 of face under the band")
    p("label_f0", "label_f1 - label_h", "labels' baseline along the front")
    p("label_co2_x", "(band_co2_x0 + band_co2_x1) / 2", "'CO2' label centre x, under the left half")
    p("label_pm_x", "(band_pm_x0 + band_pm_x1) / 2", "'PM2.5' label centre x, under the right half")
    btn = main["button"]
    p("sw_cx", btn["actuator_center_x"], "SW1 actuator x on the board (interface.yaml button)")
    p("sw_cz", btn["actuator_center_z"], "SW1 actuator centre above the board (interface.yaml button)")
    p("sw_x", "board_x0 + sw_cx", "SW1 actuator x: the dot and flexure axis")
    p("sw_z", "board_z0 + board_t + sw_cz", "SW1 actuator centre z")
    p("dot_f", "lip + (sw_z - lip) / cos_t", "dot centre along the front (f), on SW1's horizontal push axis")
    p("dot_d", 4.0, "orange dot diameter (top right, right of the PM2.5 half)")


def opening_params(s: Script) -> None:
    """Positions of the openings Task 4b cuts: the intake rows on the lip (three rows under the
    zone wall's ledge), the light-sensor window at the lip's left end (in front of the tongue's
    VEML7700), the outlet grille in the lower rear wall behind the plate, the upper-rear exhaust
    over the zone wall, and the USB-C opening on J1's axis."""
    p = s.param
    usb = B.MAIN["usb_c"]
    p("slot_bar", 1.2, "bar between the intake slot rows, and between slots in a row")
    p("slot_row1_z", "grille_min_z", "intake slots, lower row bottom: the 10 mm line (on the lip)")
    p("slot_row2_z", "slot_row1_z + slot_w + slot_bar", "intake slots, middle row bottom")
    p("slot_row3_z", "slot_row2_z + slot_w + slot_bar", "intake slots, upper row bottom (its top under the zone wall's ledge)")
    p("lsw_d", 2.0, "light-sensor window diameter (a hole in the lip, left of the slot rows)")
    p("lsw_x", "-bp_x0 + lsw_d / 2 + 0.4", "light-sensor window x: just right of the left boss pocket's inner wall, in front of the VEML7700 (veml_wx)")
    p("lsw_z", "grille_min_z + 4.0", "light-sensor window z: low enough that the VEML7700's line to it passes under the zone wall's ledge (4b checks)")
    p("row_x0", "lsw_x + lsw_d / 2 + slot_bar", "intake rows' left end: right of the light-sensor window")
    p("row_x1", "bp_x0 - slot_bar", "intake rows' right end: inside the right boss pocket")
    p("in_n", 4, "intake slots per row: 3 rows x 4 x (row - 3 bars) / 4 x 1.2 = 158 mm2 >= 154.5 (R18); whole number", unit="")
    p("in_len", "(row_x1 - row_x0 - (in_n - 1) * slot_bar) / in_n", "derived: intake slot length")
    p("out_pitch", 2.4, "outlet grille slot pitch (1.2 slots, 1.2 bars: R26 higher open fraction)")
    p("out_n", 24, "outlet grille slot count: 24 x 1.2 x 17.3 = 498 mm2 (R18: < 660.1, >= the 296 floor; owner item); whole number", unit="")
    p("out_gx0", "-tub_x + 2.0", "outlet grille's left end, 2 mm inside the plenum")
    p("out_gx1", "out_gx0 + out_n * out_pitch - (out_pitch - slot_w)", "derived: outlet grille's right end")
    p("out_gz0", "grille_min_z", "outlet grille's lower edge (10 mm rule)")
    p("out_gz1", "zw_z0 - rib_d", "outlet grille's upper edge: under the zone wall's rib seat")
    p("usb_cx", usb["center_x"], "USB-C centre on the board (interface.yaml usb_c)")
    p("usb_sw", usb["shell"][0], "USB-C shell width (interface.yaml usb_c)")
    p("usb_sh", usb["shell"][1], "USB-C shell height (interface.yaml usb_c)")
    p("usb_x", "board_x0 + usb_cx", "USB-C centre x")
    p("usb_z", "board_z0 + board_t + usb_sh / 2", "USB-C centre z")
    p("usb_well", "D - wall - (board_y0 + board_d)", "USB-C mouth inside the rear wall's inner face: the plug's well depth")
    p("usb_chamfer", 0.5, "USB-C opening chamfer (plan)")
    p("usb_plug_w", 12.5, "USB-C plug overmold width (typical, to confirm; the airQ's)")
    p("usb_plug_h", 7.0, "USB-C plug overmold height (typical, to confirm)")
    p("exh_x0", "usb_x + usb_plug_w / 2 + 2.0", "electronics exhaust left end: right of the USB-C opening")
    p("exh_x1", "tub_x - 2.0", "electronics exhaust right end")
    p("exh_z0", "zw_z1 + 1.0", "electronics exhaust lower edge: over the zone wall's top, into the electronics zone only")
    p("exh_z1", "H - wall - clr_remove - 1.0", "electronics exhaust upper edge, under the top wall")


def feet_params(s: Script) -> None:
    """Felt feet (bought): the front two cover the shell's screw heads (R10b), all four stay on the
    bottom face."""
    p = s.param
    p("head_h", 1.6, "M2 pan head height (ISO 7045): it stands head_h - head_depth under the floor")
    p("foot_t", 2.0, "felt feet thickness (bought; to confirm): more than the screw heads stand out")
    p("foot_d", 7.5, "felt feet diameter: covers the 4.4 screw head; the front feet stay inside the side and front faces (W / 2 - boss_x = 3.8)")
    p("foot_rx", "W / 2 - foot_d / 2 - 1.0", "rear feet |x|")
    p("foot_ry", "D - foot_d / 2 - 1.0", "rear feet y")


def base_cuts(s: Script) -> None:
    """Cuts in base_plate after every join: the outlet ring's seat and bore in the plate, the inlet
    seal's grooves (its root in the plate, its blade in the floor), and the tongue pin's blind
    hole in the left rail."""
    s.cylinder("Outlet ring seat", ["outlet_x", "plate_y0 - 0.5", "outlet_z"], "ring_od + 2 * clr_align", "seat_d + 0.5",
               axis="Y", operation="cut", targets=["base_plate"])
    s.cylinder("Outlet bore", ["outlet_x", "plate_y0 - 1", "outlet_z"], "ring_bore", "iwall + 2", axis="Y",
               operation="cut", targets=["base_plate"])
    s.box("Inlet seal groove", ["wiper_x1", "plate_y0 - 0.5", "floor_t - seat_d"],
          ["root_w", "seat_d + 0.5", "zw_z0 - floor_t + seat_d + 0.5"], operation="cut", targets=["base_plate"])
    with s.sketch("Inlet seal floor groove outline", "XY", offset="floor_t - seat_d") as sk:
        sk.polyline(C.wiper_profile("clr_align", hand=HAND))
    s.extrude("Inlet seal floor groove", "Inlet seal floor groove outline", "seat_d", operation="cut", targets=["base_plate"])
    s.cylinder("Tongue pin hole", ["-tub_x - tm_hole_depth", "tm_y", "tm_z"], "tm_pin_d + 2 * clr_align", "tm_hole_depth + 0.5",
               axis="X", operation="cut", targets=["base_plate"])


def zone_drawer(s: Script) -> None:
    """The cable pass-through in the zone wall's flat part over the passage's rear (J2 and J4): a
    notch open to the zone wall's left end, so both cables are laid in from the side with their
    plugs on (no plug passes it). Its front and rear faces carry grooves along x for the split
    grommet's ribs; the grommet's halves slide in from the left over the left rail, the shell's
    side wall stops them (clr_remove)."""
    x0 = "-inner_x + clr_remove - 1"
    s.box("Drawer notch", [x0, "dr_y0", "zw_z0 - 1"], [f"dr_x1 - ({x0})", "dr_y1 - dr_y0", "zone_t + 2"],
          operation="cut", targets=["zone_wall"])
    zm0 = "zw_z0 + zone_t / 2 - groove_w / 2"
    for name, ya in (("front", "dr_y0 - groove_d"), ("rear", "dr_y1")):
        s.box(f"Drawer groove {name}", [x0, ya, zm0], [f"dr_x1 - ({x0})", "groove_d", "groove_w"], operation="cut", targets=["zone_wall"])


def grommets(s: Script) -> None:
    """`grommet_zone_a` (outer) and `grommet_zone_b` (inner), TPU 95A, split along the cables'
    line (x = cab_x) so they go round both cables with the plugs on. Each fills the notch between
    its faces with drawer_squeeze on the front and rear faces (and on the closed end for the inner
    half); ribs in the notch's grooves hold them in z. The outer half sits on the left rail's top
    (drawer_squeeze into it); the shell's side wall keeps it in. Bores hug the cables (bore_squeeze)."""
    sq, c = "drawer_squeeze", "clr_align"
    zm0, zm1 = f"zw_z0 + zone_t / 2 - groove_w / 2 + {c}", f"zw_z0 + zone_t / 2 + groove_w / 2 - {c}"
    rib = f"groove_d - {c}"
    for half, xa, xb, z0 in (("a", "-inner_x + clr_remove", "cab_x", f"zw_z0 - {sq}"), ("b", "cab_x", f"dr_x1 + {sq}", "zw_z0")):
        body = f"grommet_zone_{half}"
        s.box(f"Zone grommet {half}", [xa, f"dr_y0 - {sq}", z0], [f"{xb} - ({xa})", f"dr_y1 - dr_y0 + 2 * {sq}", f"zw_z1 - ({z0})"], body=body)
        s.box(f"Zone grommet {half} rib front", [xa, f"dr_y0 - {sq} - ({rib})", zm0], [f"{xb} - ({xa})", f"{rib} + 0.5", f"{zm1} - ({zm0})"],
              operation="join", targets=[body])
        s.box(f"Zone grommet {half} rib rear", [xa, f"dr_y1 + {sq} - 0.5", zm0], [f"{xb} - ({xa})", f"{rib} + 0.5", f"{zm1} - ({zm0})"],
              operation="join", targets=[body])
    for name, y, d in (("GH", "gh_y", "cable_gh_d"), ("Qwiic", "qw_y", "cable_qw_d")):
        s.cylinder(f"Zone grommet hole {name}", ["cab_x", y, "zw_z0 - 1"], f"{d} - bore_squeeze", "zone_t + 2", operation="cut",
                   targets=["grommet_zone_a", "grommet_zone_b"])


def tongue_mount(s: Script) -> None:
    """`tongue_mount`: the tongue's pin, printed standing. Its spigot sits in the blind hole in the
    left rail, its collar spaces the tongue's back clr_align off it, its shank goes through the
    tongue's mounting hole and tm_out past the tongue's parts face. The module's left end, clr_remove
    + clr_align from the tongue's parts, keeps the tongue on the shank; the floor under its bottom
    edge (clr_align) stops it turning about the pin."""
    s.cylinder("Tongue pin", ["-tub_x - tm_hole_depth", "tm_y", "tm_z"], "tm_pin_d",
               "tm_hole_depth + tongue_x0 + tub_x + tongue_t + tm_out", axis="X", body="tongue_mount")
    s.cylinder("Tongue pin collar", ["-tub_x", "tm_y", "tm_z"], "tm_collar_d", "tongue_x0 - clr_align + tub_x", axis="X",
               operation="join", targets=["tongue_mount"])
