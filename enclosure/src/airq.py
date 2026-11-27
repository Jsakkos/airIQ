"""airq: the airQ enclosure (Plan 3 Task 3a, rulings R22, R24-R29): body and internals.

Layout: enclosure/README.md "Layout studies" and "airQ enclosure".
- The envelope is 95 x 55 x 51: a 15 mm vertical lower lip carries the intake slots, with the
  30 deg screen face above it.
- The board lies horizontal above the standing SEN66, with the zone wall between.
Shared construction: `enclosure_common` (Task 4 reuses it). Board positions: `board_sources` (R27).

SEN66 pose (fix round 1 part B, a judgement call recorded in the README): the port face looks
to the REAR and the inlet end is on the user's right. R17 holds (port face vertical, long axis
along x).
- Outlet: it blows straight back through a TPU ring (`gasket_out`, seated in the plenum plate)
  into the outlet plenum, a box of the base behind the module, and out of the outlet grille in
  the lower rear wall. The plate is the baffle in front of the grille.
- Inlets: they draw from the sensor zone, which is the intake plenum. The intake slots in the
  lower front lip feed it, and nothing else opens into it. A TPU strip (`gasket_in`) on the port
  face between the inlets and the outlet ring separates the port groups.
- The ports-forward pose cannot keep R25's outlet path: the sensor zone in front of the module
  is under the zone wall's slant, at most about 300 mm2 in section against the 330.1 the outlet
  needs, and the module cannot move back past H1.

Bodies:
- printed: shell; base_plate (floor, lip, rear wall, side rails, boss pockets, standoffs with
  collars and spigots, the outlet plenum's plate and rib, the SEN66 cradle, the HCHO pocket's
  walls, chimney and grille, the SFA40's pins and screw holes); zone_wall (clamped by the board's
  screws); hcho_lid (closes the HCHO pocket, screwed from below through the SFA40; the tongue sits
  in a pocket in its top: the tongue mount);
- TPU 95A: gasket_out (the SEN66's rear stop), gasket_in (a wiper), and the split
  grommets grommet_zone_a/_b, grommet_j4_a/_b, grommet_tongue_a/_b;
- foam: sen66_foam, sen66_pad (presses the SEN66 onto gasket_out; fix round 2, review I3(b)),
  zone_seal and sen66_top_seal (closed-cell, black; fix round 3).

Every position Task 3b needs is a named parameter here, even where 3a does not cut the feature.
"""
from __future__ import annotations

from dataclasses import replace

import airq_face as F
import board_sources as B
import enclosure_common as C
import layout_study as L
import ref_epd
import ref_fpc_adapter
import ref_sen66
import ref_sfa40
from sclib import Script

DESIGN = "airq"
OUTPUT = "airq.sc"

# R22: the study's lip layout, rounded: lip 15 fits D 55 (needs 54.62); the face needs H 50.1 in
# the study plus about 1 mm for the zone wall's ledge between the slots and the LED slot -> H 51
# 3b-1: the LED slot is 0.9 high and 0.3 higher (its lower edge): the wall under it must be >= 1.2 of opaque path to the crease
MODEL = replace(L.AIRQ, lip=15.0, H=51.0, D=55.0, led_slot_h=0.9)


def build() -> Script:
    m = MODEL
    s = Script(DESIGN)
    p = s.param
    C.add_envelope(s, m)
    r = L._refs()
    sen = ref_sen66.build().v
    sfa = ref_sfa40.build().v
    epd = ref_epd.build().v
    ad = ref_fpc_adapter.build().v
    main = B.MAIN

    # --- front face (Task 3b cuts these; 3a fixes them) ----------------------------------
    p("bezel", m.bezel, f"window lip in front of the panel ({C.LS})")
    p("panel_l", r["panel_l"], "panel length (ref_epd)")
    p("panel_w", r["panel_w"], "panel width, up the slope (ref_epd)")
    p("panel_t", r["panel_t"], "panel thickness (ref_epd, R16)")
    p("block_out", r["block_out"], "hatched block past the tail end (ref_epd; to confirm)")
    p("va_far", r["va_far"], "view area to the panel's far end (ref_epd va_far)")
    p("va_w", r["va_w"], "view area length (ref_epd va_w)")
    p("guide_t", m.guide_t, f"light guide thickness between the LED faces and the panel ({C.LS}, R20)")
    p("slot_bar", 1.2, "bar between the two intake slot rows on the lip, and between slots in a row")
    p("slot_row1_z", "grille_min_z", "intake slots, lower row bottom: the 10 mm line (on the lip)")
    p("slot_row2_z", "slot_row1_z + slot_w + slot_bar", "intake slots, upper row bottom (its top under the zone wall's ledge)")
    p("led_f0", 16.5, "LED slot lower edge, along the front (f): its inner edge above the ledge; 16.5 (3a: 16.2) leaves 1.2 of face wall between the slot and the crease (3b-1, light_paths)")
    p("led_h_slot", m.led_slot_h, "LED slot height on the face")
    p("led_len", 30.0, "LED line length (plan)")
    p("panel_s0", "led_f0 + led_h_slot + 1.15 - lip", "panel's lower edge, up the slope from the crease (0.95 face bar + 0.2 pocket; 3b-1: 0.25 lower than 3a so the panel's top keeps >= clr_remove under the top wall)")
    p("panel_x0", "-inner_x + clr_remove + block_out", "panel's tail end (user's left), the hatched block at the wall")
    p("window_xc", "panel_x0 + panel_l - va_far - va_w / 2", "view-area centre x: the LED line centres on it")

    # --- SEN66, zone wall, board, bosses ---------------------------------------------------
    C.add_sen66(s, m)
    C.add_zone_and_board(s, m, "bezel + panel_t + clr_remove + guide_t + clr_remove",
                         "inner_x - board_clr - board_w")
    C.add_standoffs(s)
    C.add_bosses(s)
    p("sen_x0", "-tub_x + clr_remove", "SEN66 outlet end (left), beside the left rail")
    p("sen_x1", "sen_x0 + sen_l", "SEN66 inlet end (right)")
    p("sen_y0", f"{C.yb('sen_top')} + clr_remove",
      "SEN66 connector face (front): its top front edge clr_remove behind the zone wall's slant")
    p("sen_y1", "sen_y0 + sen_d", "SEN66 port face (rear)")
    # ports from ref_sen66 (datasheet Fig. 8), module x from the inlet end, module y from the
    # square-inlet edge; turned so x -> -x (inlet end right), y -> -z (square inlet high)
    p("sen_out_x", sen("outlet_x"), "outlet centre from the inlet end (ref_sen66 outlet_x)")
    p("sen_out_y", sen("outlet_y"), "outlet centre from the square-inlet edge (ref_sen66 outlet_y)")
    p("outlet_d", sen("outlet_d"), "SEN66 outlet diameter (ref_sen66)")
    p("sen_sq_x0", sen("inlet_sq_x0"), "square inlet from the inlet end (ref_sen66)")
    p("sen_sq_x1", sen("inlet_sq_x1"), "square inlet to (ref_sen66)")
    p("sen_rd_x", sen("inlet_rd_x"), "round inlet centre from the inlet end (ref_sen66)")
    p("sen_rd_d", sen("inlet_rd_d"), "round inlet diameter (ref_sen66)")
    p("outlet_x", "sen_x1 - sen_out_x", "derived: outlet centre x")
    p("outlet_z", "sen_top - sen_out_y", "derived: outlet centre z")
    p("inlet_x0", "min(sen_x1 - sen_sq_x1, sen_x1 - sen_rd_x - sen_rd_d / 2)", "derived: the inlets' left edge")
    p("sen_plug_x0", 17.0, "SEN66 connector on its connector face, from the inlet end: scaled from datasheet Fig. 9 (README Frames); to confirm")
    p("sen_plug_x1", 29.0, "SEN66 connector to (scaled, to confirm)")
    p("plug_x0", "sen_x1 - sen_plug_x1", "derived: SEN66 plug's left edge (world)")
    p("plug_x1", "sen_x1 - sen_plug_x0", "derived: SEN66 plug's right edge (world)")

    # --- outlet plenum and the port gaskets (I3, R25) -------------------------------------
    p("port_gap", 3.0, "port face to the plenum plate: the inlets' air path (R25: 3.0 x 26.9 = 80.7 >= 77.3)")
    p("plate_y0", "sen_y1 + port_gap", "derived: plenum plate front face (the baffle in front of the outlet grille)")
    p("plate_y1", "plate_y0 + iwall", "derived: plenum plate back face; the plenum runs from here to the rear wall")
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
    p("wiper_x1", "inlet_x0 - 1.0", "blade root's right edge, in its groove in the plate: 1 mm left of the inlets (H1 is left of it)")
    p("root_w", 2.0, "inlet seal's root (a foot in the plate's slot) width (B3)")
    p("root_squeeze", 0.05, "inlet seal root's squeeze on its slot's sides and back (B3: no bypass round it, no travel to eat the preload; R9: the check sets 0)")
    p("wiper_lead", 0.8, "inlet seal tip's 45 deg lead-in at its top: the module's bottom edge pushes the tip back as it goes down (B4)")
    p("wiper_lean", "(plate_y0 - sen_y1 + wiper_squeeze) * tan(wiper_deg)", "derived: blade tip's shift to the left over the gap")

    # --- tongue, HCHO pocket (M4, R26, I2) ------------------------------------------------
    hole = B.TONGUE["mounting_hole"]
    veml = B.TONGUE["veml7700"]["window_center"]
    p("tongue_w", B.TONGUE["outline"][0], "tongue width (interface.yaml)")
    p("tongue_dp", B.TONGUE["outline"][1], "tongue depth (interface.yaml)")
    p("tongue_t", B.TONGUE["thickness"], "tongue thickness (interface.yaml)")
    p("tongue_parts_h", B.TONGUE["max_part_height"], "tongue's tallest part (interface.yaml)")
    p("tongue_hole_x", hole["center"][0], "tongue hole X (interface.yaml)")
    p("tongue_hole_y", hole["center"][1], "tongue hole Y (interface.yaml)")
    p("tongue_hole_d", hole["diameter"], "tongue hole diameter (interface.yaml)")
    p("veml_x", veml[0], "VEML7700 window centre X on the tongue (interface.yaml)")
    p("veml_z", veml[2], "VEML7700 window centre above the tongue's top face (interface.yaml)")
    p("sfa_w", sfa("board_w"), "SFA40 breakout width (ref_sfa40)")
    p("sfa_bt", sfa("board_t"), "SFA40 board thickness (ref_sfa40)")
    p("sfa_cap", sfa("sensor_top"), "SFA40 cap top above the board's bottom: the opening (ref_sfa40)")
    p("sfa_parts", sfa("qwiic_h"), "SFA40 tallest part above the board, its Qwiic connectors (ref_sfa40)")
    p("sfa_hole_in", sfa("hole_in"), "SFA40 holes from the edges (ref_sfa40)")
    p("sfa_hole_d", sfa("hole_d"), "SFA40 hole diameter (ref_sfa40)")
    p("hx0", "sen_x1 + clr_align + iwall", "derived: HCHO pocket's interior left (its left wall is the SEN66's right end stop)")
    p("sfa_x0", "hx0 + clr_align", "SFA40's left edge: it lies flat at the front right, opening up")
    p("shelf_w", 0.8, "ledge the lid rests on along the wall that rises past it (a lap), outside the SFA40 so it drops in")
    p("hx1", "sfa_x0 + sfa_w + clr_align + shelf_w", "derived: HCHO pocket's interior right")
    p("sfa_y0", "bp_y1 + clr_align", "SFA40's front edge, behind the right boss pocket (its J2 Qwiic at the front, J1 at the rear; the rear plug has hy1 - sfa_y0 - sfa_w, about 3.0, to confirm)")
    p("hy1", "sen_y1 - iwall", "derived: HCHO pocket's interior rear (the rear wall ends at the port face's plane, clear of the inlets' path)")
    p("hcho_air", 1.4, "air over the SFA40's cap under the lid (R25 HCHO path: 25.4 x 1.4 = 35.6 >= 27.4)")
    p("lid_z0", "floor_t + sfa_cap + hcho_air", "derived: HCHO lid underside")
    p("lid_t", 1.2, "HCHO lid thickness")
    p("cx0", "hx1 + iwall", "derived: HCHO chimney's interior left (right of the pocket, in front of H2)")
    p("cy0", "bp_y1", "derived: chimney front: the right boss pocket's back wall")
    p("cy1", "h2_y - standoff_d / 2 - clr_align", "derived: chimney rear: in front of H2")
    p("hg_pitch", 2.4, "HCHO grille slot pitch: 1.2 slots, 1.2 bars (R26 higher open fraction)")
    p("hg_margin", 1.2, "HCHO grille slots stop this far under the zone wall")
    p("tongue_gap", 4.6, "air between the lip and the tongue's front edge: the slots in front of it stay open (M4)")
    p("tongue_x1", "hx1 - 5.0", "tongue's right end (it lies turned 180 deg): room right of it for the air in front of it")
    p("tongue_y0", "wall + tongue_gap", "tongue's front edge (VEML7700 window toward the lip)")
    p("tongue_recess", 0.4, "the tongue's seat: a pocket this deep in the lid's top (clr_align round the board) locates it (N5)")
    p("tongue_z0", "lid_z0 + lid_t - tongue_recess", "tongue's bottom, in its pocket in the HCHO lid")

    # --- face positions on SW1, the LEDs, J7, USB-C, the tongue, the adapter (Task 3b) -------
    btn, usb, fpc = main["button"], main["usb_c"], main["fpc"]
    j7_w, _, _ = B.j7_body()
    p("sw_cx", btn["actuator_center_x"], "SW1 actuator x on the board (interface.yaml button)")
    p("sw_cz", btn["actuator_center_z"], "SW1 actuator centre above the board (interface.yaml button)")
    p("sw_x", "board_x0 + sw_cx", "SW1 actuator x: the dot and flexure axis")
    p("sw_z", "board_z0 + board_t + sw_cz", "SW1 actuator centre z")
    p("dot_f", "lip + (sw_z - lip) / cos_t", "dot centre along the front (f), on SW1's horizontal push axis")
    p("dot_d", 4.0, "orange dot diameter (top right, right of the panel pocket)")
    p("led_cz", main["leds"]["light_center_z"], "LED light centre above the board (interface.yaml leds)")
    p("led_z", "board_z0 + board_t + led_cz", "LED light centre z")
    p("j7_cx", fpc["center_x"], "J7 centre on the board (interface.yaml fpc)")
    p("j7_w", j7_w, "J7 body width (interface.yaml fpc comment, board_sources)")
    p("j7_x0", "board_x0 + j7_cx - j7_w / 2", "J7 mouth left end")
    p("j7_x1", "board_x0 + j7_cx + j7_w / 2", "J7 mouth right end")
    p("usb_cx", usb["center_x"], "USB-C centre on the board (interface.yaml usb_c)")
    p("usb_sw", usb["shell"][0], "USB-C shell width (interface.yaml usb_c)")
    p("usb_sh", usb["shell"][1], "USB-C shell height (interface.yaml usb_c)")
    p("usb_x", "board_x0 + usb_cx", "USB-C centre x")
    p("usb_z", "board_z0 + board_t + usb_sh / 2", "USB-C centre z")
    p("usb_well", "D - wall - (board_y0 + board_d)", "USB-C mouth inside the rear wall's inner face: the plug's well depth")
    p("usb_chamfer", 0.5, "USB-C opening chamfer (plan)")
    p("tail_off", epd("tail_offset"), "panel tail centre off the short end's centre (ref_epd)")
    p("fold_end", epd("fold_low") - epd("fold_out"), "folded tail's stiffened end from the panel's tail end (ref_epd fold_low - fold_out)")
    p("tail_fold_d", epd("tail_t") + epd("contact_t") - epd("fold_z"), "folded tail's depth behind the panel (ref_epd)")
    p("ad_l", ad("pcb_l"), "FPC adapter length along its signal path (ref_fpc_adapter; placeholder)")
    p("ad_h", ad("pcb_t") + ad("zif_h"), "FPC adapter height (ref_fpc_adapter pcb_t + zif_h; placeholder)")
    p("adapter_x", "panel_x0 + fold_end + ad_l / 2", "FPC adapter centre x: its tail ZIF at the folded tail's stiffened end")
    p("adapter_s", "panel_s0 + panel_w / 2 - tail_off", "FPC adapter centre up the slope: on the tail's centre line")
    p("adapter_t", "bezel + panel_t + tail_fold_d + 0.2 + ad_h", "FPC adapter's back face depth (folded tail, 0.2 air, the adapter)")
    p("ffc_len", 80.0, "FFC length bought: 24-pin 0.5 mm FFC, standard 80 mm; the seated route (centre line) + 2 insertions fills it (airq_face.ffc_params, 3b-1); to confirm with the vendor")
    p("lsw_x", "tongue_x1 - veml_x", "light-sensor window x: the tongue's VEML7700 window (tongue turned 180 deg)")
    p("lsw_z", "tongue_z0 + tongue_t + veml_z", "light-sensor window z: the VEML7700 window centre")
    p("lsw_d", 2.5, "light-sensor window diameter (on the lip, in a gap in the slot rows)")
    # intake rows (M6): both rows run between the boss pockets, with the window's gap
    p("row_x0", "-bp_x0 + slot_bar", "intake slot rows' left end (inside the left boss pocket)")
    p("row_x1", "bp_x0 - slot_bar", "intake slot rows' right end")
    p("lsw_gap_x0", "lsw_x - lsw_d / 2 - slot_bar", "gap in the slot rows for the light-sensor window: left")
    p("lsw_gap_x1", "lsw_x + lsw_d / 2 + slot_bar", "gap in the slot rows for the light-sensor window: right")
    F.window_params(s)
    F.ffc_params(s)
    F.ffc_derived_params(s)
    F.adapter_holder_params(s)
    F.guide_params(s)
    F.flex_params(s)
    cable_params(s)
    drawer_params(s)
    # --- bodies ------------------------------------------------------------------------------
    C.shell(s)
    C.panel_pocket(s)
    F.window(s)
    F.adapter_holder(s)
    F.led_slot(s)
    F.flexure(s)
    hcho_window(s)
    C.base_plate(s)
    C.rails(s)
    C.standoffs(s)
    plenum(s)
    cradle(s)
    hcho_pocket(s)
    C.standoff_pilots(s)
    C.base_screws(s)
    C.base_side_clearance(s)
    base_cuts(s)
    C.zone_wall(s)
    zone_drawer(s)
    plug_room(s)
    sliver_key(s)
    top_seal(s)
    tongue_capture(s)
    C.zone_seal(s)
    s.box("SEN66 foam", ["sen_x0", "sen_y0", "floor_t"], ["sen_l", "sen_d", "foam"], body="sen66_foam")
    gaskets(s)
    hcho_lid(s)
    grommets(s)
    F.light_guide(s)
    F.crease_seal(s)
    F.orange_dot(s)
    # outlet grille in the lower rear wall (M6, R18, R26): 1.2 slots at a 2.4 pitch from the left
    p("out_pitch", 2.4, "outlet grille slot pitch (1.2 slots, 1.2 bars: R26 higher open fraction)")
    p("out_n", 32, "outlet grille slot count: 32 x 1.2 x 17.3 = 664 mm2 >= 660.1 (R18). Whole number", unit="")
    p("out_gx0", "-tub_x + 2.0", "outlet grille's left end, 2 mm inside the plenum")
    p("out_gx1", "out_gx0 + out_n * out_pitch - (out_pitch - slot_w)", "derived: outlet grille's right end")
    p("out_gz0", "grille_min_z", "outlet grille's lower edge (10 mm rule)")
    p("out_gz1", "zw_z0 - rib_d", "outlet grille's upper edge: under the zone wall's rib seat")
    # upper-rear exhaust for the electronics zone (M6), kept apart from the outlet grille (R26)
    p("exh_x0", "usb_x + 8.0", "electronics exhaust left end: right of the USB-C opening")
    p("exh_x1", "tub_x - 2.0", "electronics exhaust right end")
    p("exh_z0", "H - wall - clr_remove - 12.0", "electronics exhaust lower edge, high on the rear wall")
    p("exh_z1", "H - wall - clr_remove - 2.0", "electronics exhaust upper edge")
    openings(s)
    return s


def openings(s: Script) -> None:
    """Task 3b-2: the openings in `base_plate`, cut last (every join is done). Positions are the
    parameters above; each opening's lower edge is at least grille_min_z.
    - intake slot rows in the lower front lip (two rows, slot_w high, slots end to end with
      slot_bar bars, two spans either side of the light-sensor window's gap);
    - the light-sensor window (a round hole in the lip, in front of the tongue's VEML7700);
    - the outlet grille in the lower rear wall, behind the plenum plate;
    - the electronics exhaust in the upper rear wall;
    - the USB-C opening in the rear wall on J1's plug axis, passing the plug's overmold, with a
      0.5 chamfer on its outer edge.
    The HCHO grille is cut in `base_cuts` (3a), behind the window in the shell's side wall."""
    p = s.param
    p("in_n_l", 5, "intake slots per row in the left span (left of the light-sensor window); whole number", unit="")
    p("in_n_r", 2, "intake slots per row in the right span; whole number", unit="")
    p("in_len_l", "(lsw_gap_x0 - row_x0 - (in_n_l - 1) * slot_bar) / in_n_l", "derived: intake slot length, left span")
    p("in_len_r", "(row_x1 - lsw_gap_x1 - (in_n_r - 1) * slot_bar) / in_n_r", "derived: intake slot length, right span")
    for row, zr in ((1, "slot_row1_z"), (2, "slot_row2_z")):
        for side, n, x0, ln in (("L", "in_n_l", "row_x0", "in_len_l"), ("R", "in_n_r", "lsw_gap_x1", "in_len_r")):
            for i in range(int(s.v(n))):
                s.box(f"Intake slot {row}{side}{i + 1}", [f"{x0} + {i} * ({ln} + slot_bar)", "-wall", zr], [ln, "3 * wall", "slot_w"],
                      operation="cut", targets=["base_plate"])
    s.cylinder("Light-sensor window", ["lsw_x", "-wall", "lsw_z"], "lsw_d", "3 * wall", axis="Y", operation="cut", targets=["base_plate"])
    for i in range(int(s.v("out_n"))):
        s.box(f"Outlet slot {i + 1}", [f"out_gx0 + {i} * out_pitch", "D - 2 * wall", "out_gz0"], ["slot_w", "3 * wall", "out_gz1 - out_gz0"],
              operation="cut", targets=["base_plate"])
    p("exh_n", 14, "electronics exhaust slot count: 14 x 2.4 - 1.2 = 32.4 fits exh_x0 ... exh_x1; whole number", unit="")
    for i in range(int(s.v("exh_n"))):
        s.box(f"Exhaust slot {i + 1}", [f"exh_x0 + {i} * out_pitch", "D - 2 * wall", "exh_z0"], ["slot_w", "3 * wall", "exh_z1 - exh_z0"],
              operation="cut", targets=["base_plate"])
    p("usb_plug_w", 12.5, "USB-C plug overmold width (typical, to confirm; README Layout studies row 9)")
    p("usb_plug_h", 7.0, "USB-C plug overmold height (typical, to confirm)")
    p("usb_open_w", "usb_plug_w + 2 * clr_remove", "USB-C opening width: the overmold passes (its tip is in the wall's thickness, usb_well)")
    p("usb_open_h", "usb_plug_h + 2 * clr_remove", "USB-C opening height")
    s.box("USB-C opening", ["usb_x - usb_open_w / 2", "D - 2 * wall", "usb_z - usb_open_h / 2"], ["usb_open_w", "3 * wall", "usb_open_h"],
          operation="cut", targets=["base_plate"])
    v = s.v
    d, cx, cz = v("D"), v("usb_x"), v("usb_z")
    hw, hh = v("usb_open_w") / 2, v("usb_open_h") / 2
    s.chamfer("USB-C chamfer", [[cx, d, cz - hh], [cx, d, cz + hh], [cx - hw, d, cz], [cx + hw, d, cz]], "usb_chamfer", body="base_plate")


def plenum(s: Script) -> None:
    """The outlet plenum, part of base_plate: the plate (the baffle in front of the outlet grille,
    with the ring's seat and bore) between the side rails, from the floor to the zone wall, which
    rests on its top edge and on the rear-wall rib. H1 merges with the plate, which braces it."""
    s.box("Plenum plate", ["-tub_x - 0.5", "plate_y0", "floor_t - 0.5"], ["2 * tub_x + 1", "iwall", "zw_z0 - floor_t + 0.5"],
          operation="join", targets=["base_plate"])


def cradle(s: Script) -> None:
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
    down (B4)."""
    p = s.param
    p("pad_t", 3.2, "SEN66 front pad: foam thickness free (stuck on the module's connector face on the ring's axis; to confirm with the foam bought)")
    p("pad_w", 10.0, "pad width (x)")
    p("pad_h", 10.0, "pad height (z), centred on the outlet: its force passes through the ring's land")
    p("seat_t", 2.4, "pad seat thickness (B1)")
    p("seat_y0", "pt_yh + cable_gh_d / 2 + clr_align", "pad seat's front face: just behind the cables' riser and run")
    p("pad_y0", "seat_y0 + seat_t", "derived: the pad's seat face")
    p("pad_gap", "sen_y0 - pad_y0", "derived: pad thickness at the nominal module (44 % compressed; 28 % at 20.8 deep, 60 % at 21.8)")
    p("pad_squeeze", "pad_t - pad_gap", "derived: the pad as modelled, free, over the nominal module (R9: the check design sets 0)")
    p("seat_lead_z", "outlet_z + pad_h / 2 + 0.2", "derived: where the seat's lead-in starts, just over the pad's top")
    p("seat_slant_clr", "gasket_squeeze / sin_t + 0.2", "derived: the seat's top under the slant: under the drawer grommet's squeezed face, + 0.2")
    p("rail_h", 4.0, "cradle right rail (a guide) height above the floor")
    tb = "zw_tf + zone_t"
    # the apex where the lead-in (45 deg up and forward from the back face) meets the slant-following top
    y_apex = f"(seat_lead_z + pad_y0 + seat_slant_clr - lip + ({tb}) / sin_t) / (cos_t / sin_t + 1)"
    p("seat_apex_y", y_apex, "derived: the seat's top apex, y")
    p("seat_apex_z", "seat_lead_z + pad_y0 - seat_apex_y", "derived: the seat's top apex, z")
    pts = [("seat_y0", "floor_t - 0.5"), ("pad_y0", "floor_t - 0.5"), ("pad_y0", "seat_lead_z"), ("seat_apex_y", "seat_apex_z"),
           ("seat_y0", f"{zt('seat_y0', tb)} - seat_slant_clr")]
    with s.sketch("Pad seat profile", "YZ", offset="-tub_x - iwall") as sk:
        sk.polyline(pts)
    s.extrude("Pad seat", "Pad seat profile", "plug_x0 - 1.0 + tub_x + iwall", operation="join", targets=["base_plate"])
    s.box("Cradle front rail R", ["plug_x1 + 1.0", "sen_y0 - sen_d_tol - clr_align - iwall", "floor_t - 0.5"],
          ["sen_x1 - plug_x1 - 1.0", "iwall", "rail_h + 0.5"], operation="join", targets=["base_plate"])


def wiper_profile(c: str = "0") -> list[tuple[str, str]]:
    """The inlet seal's plan (XY): a foot in the plate's slot (root_w, squeezed root_squeeze on its
    sides and back, B3), then the blade leaning wiper_deg to the left from the plate's face to its
    tip on the port face. With `c` the outline grows by c all round (the floor groove): the
    blade's edges by c across them, its tip by c along it."""
    tip = "sen_y1 - wiper_squeeze"
    rs = "root_squeeze"
    if c == "0":
        return [(f"wiper_x1 - root_w - {rs}", f"plate_y0 + seat_d + {rs}"), (f"wiper_x1 + {rs}", f"plate_y0 + seat_d + {rs}"),
                (f"wiper_x1 + {rs}", "plate_y0"), ("wiper_x1", "plate_y0"), ("wiper_x1 - wiper_lean", tip),
                ("wiper_x1 - wiper_lean - wiper_w", tip), ("wiper_x1 - wiper_w", "plate_y0"), (f"wiper_x1 - root_w - {rs}", "plate_y0")]
    cn = f"{c} / cos(wiper_deg)"                     # across the blade
    ct = f"{c} * tan(wiper_deg)"                     # the tip moved c along the blade
    tipc = f"{tip} - {c}"
    return [(f"wiper_x1 - root_w - {rs} - {c}", f"plate_y0 + seat_d + {rs} + {c}"), (f"wiper_x1 + {rs} + {c}", f"plate_y0 + seat_d + {rs} + {c}"),
            (f"wiper_x1 + {rs} + {c}", "plate_y0"), (f"wiper_x1 + {cn}", "plate_y0"), (f"wiper_x1 - wiper_lean + {cn} - {ct}", tipc),
            (f"wiper_x1 - wiper_lean - wiper_w - {cn} - {ct}", tipc), (f"wiper_x1 - wiper_w - {cn}", "plate_y0"),
            (f"wiper_x1 - root_w - {rs} - {c}", "plate_y0")]


SFA_HOLES = ((0, 0), (1, 0), (0, 1), (1, 1))        # the SFA40's holes: (0, 0) front left ... (1, 1) rear right
SFA_SCREWS = ((0, 0), (1, 1))                       # N5: M2 screws from under the floor into the lid's posts


def hcho_pocket(s: Script) -> None:
    """The SFA40's sealed pocket at the front right, part of base_plate (R26: off the rear wall,
    which the outlet grille needs whole). The SFA40 lies flat on pins through its holes, opening
    up. The lid closes the pocket (laps on the walls' tops, the lip rib and a shelf); the tongue
    lies on the lid. A chimney in front of H2 takes the air to the HCHO grille, cut in the right
    rail behind a window in the shell's side wall."""
    s.box("HCHO pocket left wall", ["sen_x1 + clr_align", "wall - 0.5", "floor_t - 0.5"],
          ["iwall", "hy1 + iwall - wall + 0.5", "lid_z0 - floor_t + 0.5"], operation="join", targets=["base_plate"])
    s.box("HCHO pocket rear wall", ["sen_x1 + clr_align", "hy1", "floor_t - 0.5"], ["cx0 - sen_x1 - clr_align", "iwall", "lid_z0 - floor_t + 0.5"],
          operation="join", targets=["base_plate"])
    s.box("HCHO lid front rib", ["sen_x1 + clr_align", "wall - 0.5", "lid_z0 - shelf_w"], ["bp_x0 - sen_x1 - clr_align", "shelf_w + 0.5", "shelf_w"],
          operation="join", targets=["base_plate"])
    # the chimney's left wall: from the lip to the pocket's rear, up to the zone wall's underside
    pts = [("bp_y1 - iwall", "floor_t - 0.5"), ("hy1 + iwall", "floor_t - 0.5"), ("hy1 + iwall", "zw_z0"),
           (C.yb("zw_z0"), "zw_z0"), (C.yb("ledge_z0"), "ledge_z0"), ("bp_y1 - iwall", "ledge_z0")]
    with s.sketch("HCHO chimney wall profile", "YZ", offset="hx1") as sk:
        sk.polyline(pts)
    s.extrude("HCHO chimney wall", "HCHO chimney wall profile", "iwall", operation="join", targets=["base_plate"])
    # the lid's shelves: along the chimney wall, along the boss pocket's back wall and its inner wall
    s.box("HCHO lid shelf", ["hx1 - shelf_w", "bp_y1 - 0.5", "lid_z0 - shelf_w"], ["shelf_w + 0.5", "hy1 - bp_y1 + 0.5", "shelf_w"],
          operation="join", targets=["base_plate"])
    s.box("HCHO lid shelf back", ["bp_x0 - shelf_w", "bp_y1 - 0.5", "lid_z0 - shelf_w"], ["hx1 - bp_x0 + shelf_w", "shelf_w + 0.5", "shelf_w"],
          operation="join", targets=["base_plate"])
    s.box("HCHO lid shelf front", ["bp_x0 - shelf_w", "wall - 0.5", "lid_z0 - shelf_w"], ["shelf_w + 0.5", "bp_y1 - wall + 0.5", "shelf_w"],
          operation="join", targets=["base_plate"])
    s.box("HCHO chimney rear wall", ["cx0 - 0.5", "cy1", "floor_t - 0.5"], ["tub_x - cx0 + 1", "iwall", "zw_z0 - floor_t + 0.5"],
          operation="join", targets=["base_plate"])
    for i, (dx, dy) in enumerate(SFA_HOLES, 1):
        if (dx, dy) in SFA_SCREWS:
            continue                       # these two holes take the lid's screws from under the floor (N5)
        x = f"sfa_x0 + sfa_hole_in + {dx} * (sfa_w - 2 * sfa_hole_in)"
        y = f"sfa_y0 + sfa_hole_in + {dy} * (sfa_w - 2 * sfa_hole_in)"
        s.cylinder(f"SFA40 pin {i}", [x, y, "floor_t - 0.5"], "sfa_hole_d - 2 * clr_align", "sfa_bt + 0.5",
                   operation="join", targets=["base_plate"])


def base_cuts(s: Script) -> None:
    """Cuts in base_plate after every join: the gaskets' seats and the outlet bore, the window from
    the HCHO pocket into its chimney, and the HCHO grille."""
    for i, (dx, dy) in enumerate(SFA_HOLES, 1):
        if (dx, dy) not in SFA_SCREWS:
            continue
        x = f"sfa_x0 + sfa_hole_in + {dx} * (sfa_w - 2 * sfa_hole_in)"
        y = f"sfa_y0 + sfa_hole_in + {dy} * (sfa_w - 2 * sfa_hole_in)"
        s.cylinder(f"SFA40 screw hole {i}", [x, y, "-head_depth"], "screw_d", "floor_t + 2 * head_depth", operation="cut",
                   targets=["base_plate"])
        s.cylinder(f"SFA40 screw head {i}", [x, y, "-head_depth"], "head_d", "2 * head_depth", operation="cut",
                   targets=["base_plate"])
    s.cylinder("Outlet ring seat", ["outlet_x", "plate_y0 - 0.5", "outlet_z"], "ring_od + 2 * clr_align", "seat_d + 0.5",
               axis="Y", operation="cut", targets=["base_plate"])
    s.cylinder("Outlet bore", ["outlet_x", "plate_y0 - 1", "outlet_z"], "ring_bore", "iwall + 2", axis="Y",
               operation="cut", targets=["base_plate"])
    # H1 is braced by the plate; below its pilot hole its back is trimmed to the plate, so the
    # plenum keeps its section behind it (R25)
    s.param("h1_trim_z", "board_z0 - pilot_depth - 1.0", "derived: top of H1's trim in the plenum (below its pilot hole)")
    s.box("H1 plenum trim", ["h1_x - standoff_d / 2 - 0.5", "plate_y1 + 0.6", "floor_t"],
          ["standoff_d + 1", "h1_y + standoff_d / 2 + 0.5 - plate_y1 - 0.6", "h1_trim_z - floor_t"], operation="cut", targets=["base_plate"])
    # the inlet seal's grooves: its root through the plate's height, its blade in the floor
    s.box("Inlet seal groove", ["wiper_x1 - root_w", "plate_y0 - 0.5", "floor_t - seat_d"],
          ["root_w", "seat_d + 0.5", "zw_z0 - floor_t + seat_d + 0.5"],
          operation="cut", targets=["base_plate"])
    with s.sketch("Inlet seal floor groove outline", "XY", offset="floor_t - seat_d") as sk:
        sk.polyline(wiper_profile("clr_align"))
    s.extrude("Inlet seal floor groove", "Inlet seal floor groove outline", "seat_d", operation="cut", targets=["base_plate"])
    s.box("HCHO chimney window", ["hx1 - 0.5", "cy0 + 0.8", "floor_t"], ["iwall + 1", "cy1 - cy0 - 1.6", "lid_z0 - shelf_w - floor_t"],
          operation="cut", targets=["base_plate"])
    for i in range(5):
        y = f"cy0 + 0.6 + {i} * hg_pitch"
        s.box(f"HCHO grille slot {i + 1}", ["tub_x - 0.5", y, "grille_min_z"],
              ["iwall + 1", "slot_w", f"{C.z_under(y)} - hg_margin - grille_min_z"], operation="cut", targets=["base_plate"])


HCHO_SLOTS = 5


def window_steps() -> list[tuple[str, str, str]]:
    """The HCHO window's steps (review N2): (y from, y to, top) per grille slot, expressions. Each
    step spans its slot and half a bar each side, and stops 0.6 over its slot's top, so behind
    every point of the window stands the base's right rail or the zone wall's end face (whose
    underside the rail follows): nothing of the electronics zone above the zone wall shows."""
    out = []
    for i in range(HCHO_SLOTS):
        y_lo = f"cy0 + {i} * hg_pitch"
        y_hi = "cy1" if i == HCHO_SLOTS - 1 else f"cy0 + {i + 1} * hg_pitch"
        top = f"{C.z_under(f'cy0 + 0.6 + {i} * hg_pitch')} - hg_margin + 0.6"
        out.append((y_lo, y_hi, top))
    return out


def hcho_window(s: Script) -> None:
    """The window in the shell's right side wall in front of the HCHO grille (the grille's slots
    are in the base's right rail behind it). Its lower edge is on the 10 mm line; its top steps
    up with the slots (N2), under the zone wall's slanted underside."""
    steps = window_steps()
    pts = [("cy0", "grille_min_z"), ("cy1", "grille_min_z")]
    for y_lo, _, top in reversed(steps):
        pts += [(pts[-1][0], top), (y_lo, top)]
    with s.sketch("HCHO window outline", "YZ", offset="inner_x - 0.5") as sk:
        sk.polyline(pts)
    s.extrude("HCHO window", "HCHO window outline", "wall + 1", operation="cut", targets=["shell"])


def zt(y: str, t: str) -> str:
    """z of the point at depth y with depth t behind the slope's outer surface (an expression)."""
    return f"lip + (({y}) * cos_t - ({t})) / sin_t"


def tongue_capture(s: Script) -> None:
    """N5: the tongue is located by its pocket in the lid and held down by a pad under the zone
    wall's ledge over its VEML7700's top, clr_align above it (the zone wall is clamped by the
    board's screws). The pad shades the sensor from above too."""
    (vx0, vy0), (vx1, vy1) = B.TONGUE["veml7700"]["body"]
    p = s.param
    p("veml_bx0", vx0, "VEML7700 body x from (tongue frame, interface.yaml)")
    p("veml_bx1", vx1, "VEML7700 body x to (interface.yaml)")
    p("veml_by0", vy0, "VEML7700 body y from (interface.yaml)")
    p("veml_by1", vy1, "VEML7700 body y to (interface.yaml)")
    s.box("Tongue hold-down", ["tongue_x1 - veml_bx1 + 0.5", "tongue_y0 + veml_by0 + 0.35", "tongue_z0 + tongue_t + tongue_parts_h + clr_align"],
          ["veml_bx1 - veml_bx0 - 1.0", "veml_by1 - veml_by0 - 0.7", "ledge_z0 + 0.5 - (tongue_z0 + tongue_t + tongue_parts_h + clr_align)"],
          operation="join", targets=["zone_wall"])


def cable_params(s: Script) -> None:
    """The cables and plug envelopes the routes use (I2), to confirm against the cables bought.
    A plug is taken no larger than the receptacle body it enters (interface.yaml)."""
    p = s.param
    j4, j2 = B.MAIN["j_qwiic_aux"]["body"], B.MAIN["j_sen66"]["body"]
    p("cable_gh_d", 3.0, "SEN66 cable (JST GH, 6 wires) bundle diameter; to confirm")
    p("cable_qw_d", 2.4, "Qwiic cable diameter; to confirm")
    p("qw_plug_w", j4[1][1] - j4[0][1], "Qwiic plug (JST SH 4) width envelope: J4's body width (interface.yaml); to confirm")
    p("qw_plug_t", max(B.connector_h("j_qwiic_aux"), B.connector_h("qwiic", board="tongue")),
      "Qwiic plug thickness envelope: the taller Qwiic body (interface.yaml comments); to confirm")
    p("gh_plug_w", j2[1][1] - j2[0][1], "SEN66 plug (JST GH 6) width envelope: J2's body width (interface.yaml); to confirm")
    p("gh_plug_t", B.connector_h("j_sen66"), "SEN66 plug thickness envelope: J2's body height (interface.yaml); to confirm")


def sliver_key(s: Script) -> None:
    """Review round 3, B6: between the left boss notch and the drawer the zone wall is a 2.3 mm
    sliver, which the drawer grommet's front half pushes forward. A ridge on the left boss pocket's
    back wall top sits in a groove in the sliver's underside and takes that push."""
    p = s.param
    p("key_w", 1.4, "sliver key ridge width along y (on the left boss pocket's back wall top)")
    p("key_h", 0.5, "sliver key ridge height")
    x0, x1 = "-tub_x - iwall + 0.5", "-bp_x0 - 1.5"
    s.box("Sliver key", [x0, "bp_y1 - iwall", "ledge_z0 - 0.5"], [f"{x1} - ({x0})", "key_w", "key_h + 0.5"],
          operation="join", targets=["base_plate"])
    s.box("Sliver key groove", [f"{x0} - clr_align", "bp_y1 - iwall - 1", "ledge_z0 - 1"],
          [f"{x1} - ({x0}) + 2 * clr_align", "key_w + clr_align + 1", "key_h + clr_align + 1"], operation="cut", targets=["zone_wall"])


def top_seal(s: Script) -> None:
    """Review round 3 (the space beside the ring): `sen66_top_seal`, a foam strip stuck across the
    module's top at the inlet wiper's tip, from its port face to its connector face, closes the
    0.3 gap over the module there, so the space between the ring and the wiper no longer joins the
    inlets' side over the module's top-rear edge (a 5 mm path round the wiper); it joins only the
    front plenum, 21 mm forward through 0.2-0.3 slits, far from the inlets."""
    p = s.param
    p("top_seal_t", 0.6, "foam strip on the SEN66's top, free (0.2-0.5 gap over the module's +0.1/-0.2 height: 17-67 %)")
    p("top_seal_squeeze", "top_seal_t - zone_gap", "derived: the strip as modelled, free (R9: the check sets 0)")
    p("top_seal_x0", "wiper_x1 - wiper_lean - wiper_w - 1.0", "top seal's left end: 1 mm past the wiper's tip")
    p("top_seal_x1", "wiper_x1 - wiper_lean + 1.0", "top seal's right end")
    s.box("SEN66 top seal", ["top_seal_x0", "sen_y0", "sen_top"], ["top_seal_x1 - top_seal_x0", "sen_d", "zone_gap + top_seal_squeeze"],
          body="sen66_top_seal")


def plug_room(s: Script) -> None:
    """Review round 3, B2: a shallow pocket in the slant's underside over the SEN66's plug and its
    cable's bend, so the plug of a 21.8 deep module (its connector face sen_d_tol further forward,
    the port face on the ring) still clears the zone wall by clr_remove. The slant keeps
    zone_t - plug_room_d there."""
    p = s.param
    p("plug_room_d", 0.6, "pocket depth into the slant's underside over the SEN66's plug (B2)")
    p("plug_room_z0", "sen_top - sen_up / 2 - 0.3", "pocket's lower edge (on the slant's underside)")
    p("plug_room_z1", "sen_top - sen_up / 2 + 3.2", "pocket's upper edge, over the plug's envelope")
    tb = "zw_tf + zone_t"
    y = lambda tt, z: f"(({tt}) + ({z} - lip) * sin_t) / cos_t"     # noqa: E731
    pts = [(y(f"{tb} + 0.5", "plug_room_z0"), "plug_room_z0"), (y(f"{tb} + 0.5", "plug_room_z1"), "plug_room_z1"),
           (y(f"{tb} - plug_room_d", "plug_room_z1"), "plug_room_z1"), (y(f"{tb} - plug_room_d", "plug_room_z0"), "plug_room_z0")]
    with s.sketch("Plug room profile", "YZ", offset="plug_x0 - 0.5") as sk:
        sk.polyline(pts)
    s.extrude("Plug room", "Plug room profile", "plug_x1 - plug_x0 + 1", operation="cut", targets=["zone_wall"])


def drawer_params(s: Script) -> None:
    """The zone wall's cable drawer and the cables' line through it (zone_drawer)."""
    p = s.param
    p("groove_d", 0.6, "drawer grooves' depth into the notch's faces (along y)")
    p("groove_w", 0.8, "drawer grooves' width across the zone wall (along t), centred in its thickness")
    p("pt_x0", "-tub_x + 0.3", "cables' riser left end (inside the left rail)")
    p("gh_x", "pt_x0 + cable_gh_d / 2", "SEN66 cable through the drawer: x")
    p("qw_x", "gh_x + cable_gh_d / 2 + 0.8 + cable_qw_d / 2", "J4 Qwiic cable through the drawer: x")
    p("pt_x1", "qw_x + cable_qw_d / 2 + 0.8", "drawer notch's closed end (right)")
    p("strip_x1", "adapter_x - ad_l / 2 - clr_align", "cables' strip behind the folded tail: right end, left of the adapter")
    p("pt_y0", f"{C.yb('ledge_z0')} + groove_d", "drawer notch's front face: its groove stays in the slant, behind the ledge")
    p("pt_y1", "pt_y0 + cable_gh_d + 1.6", "drawer notch's rear face: 0.8 of TPU round the SEN66 cable")
    p("pt_yh", "(pt_y0 + pt_y1) / 2", "derived: the cables' line, the grommet's split")
    p("pt_z0", f"{zt('pt_yh - cable_gh_d / 2', 'zw_tf + zone_t')} - 1.0", "cables' riser top, under the grommet")
    p("pt_z1", "ledge_z1 + 10.5", "cables' strip bottom, over the grommet")


def zone_drawer(s: Script) -> None:
    """The cable pass-through in the zone wall's slant at the left (I2), for the SEN66 cable (J2)
    and the SFA40's Qwiic cable (J4): a notch open to the zone wall's left end, so the cables are
    laid in from the side with both plugs on, and no plug passes it. Its two y faces carry grooves
    (along x) for the ribs of the split grommet, which slides in from the left over the left rail
    and is held there by the shell's side wall (with clr_remove)."""
    tf, tb = "zw_tf", "zw_tf + zone_t"
    x0 = "-inner_x + clr_remove - 1"
    s.box("Drawer notch", [x0, "pt_y0", f"{zt('pt_y0', tb)} - 0.5"], [f"pt_x1 - ({x0})", "pt_y1 - pt_y0",
          f"{zt('pt_y1', tf)} - ({zt('pt_y0', tb)}) + 1"], operation="cut", targets=["zone_wall"])
    tm0, tm1 = "zw_tf + zone_t / 2 - groove_w / 2", "zw_tf + zone_t / 2 + groove_w / 2"
    for name, ya, yb in (("front", "pt_y0 - groove_d", "pt_y0"), ("rear", "pt_y1", "pt_y1 + groove_d")):
        pts = [(ya, zt(ya, tm0)), (yb, zt(yb, tm0)), (yb, zt(yb, tm1)), (ya, zt(ya, tm1))]
        with s.sketch(f"Drawer groove {name} profile", "YZ", offset=x0) as sk:
            sk.polyline(pts)
        s.extrude(f"Drawer groove {name}", f"Drawer groove {name} profile", f"pt_x1 - ({x0})", operation="cut", targets=["zone_wall"])


def gaskets(s: Script) -> None:
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
        sk.polyline(wiper_profile())
    s.extrude("Inlet seal", "Inlet seal outline", "zw_z0 - floor_t + seat_d", body="gasket_in")
    tip = "sen_y1 - wiper_squeeze"
    with s.sketch("Inlet seal lead-in profile", "YZ", offset="wiper_x1 - wiper_lean - wiper_w - 1") as sk:
        sk.polyline([(f"{tip} - 1", "zw_z0 - wiper_lead - 1"), (f"{tip} + wiper_lead + 1", "zw_z0 + 1"), (f"{tip} - 1", "zw_z0 + 1")])
    s.extrude("Inlet seal lead-in", "Inlet seal lead-in profile", "wiper_lean + wiper_w + 2", operation="cut", targets=["gasket_in"])
    s.box("SEN66 pad", ["outlet_x - pad_w / 2", "pad_y0", "outlet_z - pad_h / 2"], ["pad_w", "pad_gap + pad_squeeze", "pad_h"],
          body="sen66_pad")


def hcho_lid(s: Script) -> None:
    """`hcho_lid`: closes the HCHO pocket and seats the tongue (the plan's tongue mount: a pocket
    in its top). It rests on the pocket's walls, the lip rib and the shelves; four posts on its
    underside press the SFA40 down; two M2 screws from under the floor, through the SFA40's front
    left and rear right holes, go into two of the posts and clamp the board and the lid to the
    base (N5). Its top is flat but for the pocket and the cable hole, so it prints top face down,
    posts up (N6)."""
    p = s.param
    p("lid_pilot_depth", 3.5, "M2 self-tapping pilot depth in the lid's screw posts")
    p("sfa_screw_l", 6.0, "SFA40 screws: M2 x 6 self-tapping pan head, from the counterbore's floor (B5: x 8 would come through the lid)")
    p("head_h", 1.6, "M2 pan head height (ISO 7045): it stands head_h - head_depth under the floor")
    p("foot_t", 2.0, "felt feet thickness (bought; to confirm): more than the screw heads stand out")
    p("foot_d", 10.0, "felt feet diameter: the front two cover the shell's screws")
    p("foot_rx", "W / 2 - foot_d / 2 - 1.0", "rear feet |x|")
    p("foot_ry", "D - foot_d / 2 - 1.0", "rear feet y")
    with s.sketch("HCHO lid outline", "XY", offset="lid_z0") as sk:
        sk.polyline([("sen_x1 + clr_align", "wall + clr_remove"), ("bp_x0 - clr_remove", "wall + clr_remove"),
                     ("bp_x0 - clr_remove", "bp_y1 + clr_remove"), ("hx1 - clr_remove", "bp_y1 + clr_remove"),
                     ("hx1 - clr_remove", "hy1 + iwall"), ("sen_x1 + clr_align", "hy1 + iwall")])
    s.extrude("HCHO lid", "HCHO lid outline", "lid_t", body="hcho_lid")
    for i, (dx, dy) in enumerate(SFA_HOLES, 1):
        x = f"sfa_x0 + sfa_hole_in + {dx} * (sfa_w - 2 * sfa_hole_in)"
        y = f"sfa_y0 + sfa_hole_in + {dy} * (sfa_w - 2 * sfa_hole_in)"
        s.cylinder(f"SFA40 hold-down {i}", [x, y, "floor_t + sfa_bt"], "sfa_hole_d + 1.4", "lid_z0 - floor_t - sfa_bt + 0.5",
                   operation="join", targets=["hcho_lid"])
        if (dx, dy) in SFA_SCREWS:
            s.cylinder(f"SFA40 hold-down {i} pilot", [x, y, "floor_t + sfa_bt - 0.5"], "pilot_d", "lid_pilot_depth + 0.5",
                       operation="cut", targets=["hcho_lid"])
    s.box("Tongue seat", ["tongue_x1 - tongue_w - clr_align", "tongue_y0 - clr_align", "lid_z0 + lid_t - tongue_recess"],
          ["tongue_w + 2 * clr_align", "tongue_dp + 2 * clr_align", "tongue_recess + 0.5"], operation="cut", targets=["hcho_lid"])
    # I2: the hole passes the Qwiic plug of the SFA40's cable to the tongue (the lid goes on over it)
    s.param("lid_hole_l", "qw_plug_w + 2 * clr_remove", "lid cable hole along x: passes the Qwiic plug's width")
    s.param("lid_hole_w", "qw_plug_t + 2 * clr_remove", "lid cable hole along y: passes the Qwiic plug's thickness")
    s.param("lh_x", "sfa_x0 + sfa_w / 2", "lid cable hole centre x, over the SFA40's rear Qwiic (J1)")
    s.param("lh_y0", "hy1 - lid_hole_w - 0.6", "lid cable hole front edge (0.6 in front of the pocket's rear wall)")
    s.box("Lid cable hole", ["lh_x - lid_hole_l / 2", "lh_y0", "lid_z0 - 0.5"], ["lid_hole_l", "lid_hole_w", "lid_t + 1"],
          operation="cut", targets=["hcho_lid"])


def grommets(s: Script) -> None:
    """TPU 95A grommets where the cables pass a sealed wall (I2, N4). Each is split in two along
    its cables, so it goes round cables with both plugs on; each is sized at contact plus
    gasket_squeeze on the faces it seals, and is held in place:
    - grommet_zone_a/_b in the zone wall's drawer (front and rear halves): ribs in the notch's
      grooves hold them across the wall; they bear on the left rail's top and the notch's end; the
      shell's side wall stops them sliding out (clr_remove);
    - grommet_j4_a/_b in the HCHO pocket's left wall (lower and upper halves): a notch open at
      the wall's top, so the SFA40's cable to J4 is laid in from above (no plug passes); the halves
      straddle the wall with flanges, the floor under them, the lid over them;
    - grommet_tongue_a/_b in the lid (left and right halves): the hole passes the Qwiic plug of
      the SFA40's cable to the tongue (the lid goes on over it); a flange on the lid and a barb
      under it hold each half."""
    p = s.param
    p("grommet_squeeze", 0.1, "TPU squeeze of the J4 and lid grommets' sealing faces (B6: 4 %, tens of N, not hundreds; R9: the check sets 0)")
    p("drawer_squeeze", 0.05, "TPU squeeze of the drawer grommet's faces (B6: low, the front half bears on the zone wall's sliver at the boss notch, which a key on the boss pocket holds)")
    p("bore_squeeze", 0.2, "grommet bores under the cable's diameter (B6: they hug the cable; sleeve the GH wires round; R9: the check sets 0)")
    sq = "drawer_squeeze"
    c = "clr_align"
    # zone wall drawer: (y, t) profiles, extruded along x from the zone wall's left end
    tf, tb = "zw_tf", f"zw_tf + zone_t + {sq}"
    rw0, rw1 = f"zw_tf + zone_t / 2 - groove_w / 2 + {c}", f"zw_tf + zone_t / 2 + groove_w / 2 - {c}"
    x0 = "-inner_x + clr_remove"
    for half, yf, yr, sgn in (("a", "pt_y0", "pt_yh", "-"), ("b", "pt_y1", "pt_yh", "+")):
        face = f"{yf} {sgn} {sq}"
        rib = f"{yf} {sgn} ({sq} + groove_d - {c})"        # B6: the rib stands groove_d - c proud of the printed face
        prof = [(yr, tf), (face, tf), (face, rw0), (rib, rw0), (rib, rw1), (face, rw1), (face, tb), (yr, tb)]
        with s.sketch(f"Zone grommet {half} profile", "YZ", offset=x0) as sk:
            sk.polyline([(y, zt(y, tt)) for y, tt in prof])
        s.extrude(f"Zone grommet {half}", f"Zone grommet {half} profile", f"pt_x1 + {sq} - ({x0})", body=f"grommet_zone_{half}")
    for name, x, d in (("GH", "gh_x", "cable_gh_d"), ("Qwiic", "qw_x", "cable_qw_d")):
        s.cylinder(f"Zone grommet hole {name}", [x, "pt_yh", "pt_z0"], f"{d} - bore_squeeze", "pt_z1 - pt_z0", operation="cut",
                   targets=["grommet_zone_a", "grommet_zone_b"])
    # J4: the HCHO pocket's left wall, a notch open at its top
    p("j4n_y0", "wall + 1.6", "J4 notch's front face in the HCHO pocket's left wall (its flanges clear the lid's front rib)")
    p("j4n_w", "cable_qw_d + 1.6", "J4 notch's width: 0.8 of TPU round the cable")
    p("j4n_yc", "j4n_y0 + j4n_w / 2", "derived: J4 cable's y through the wall")
    p("j4n_zc", "floor_t + 0.8 + cable_qw_d / 2", "derived: J4 cable's z through the wall, the grommet's split")
    p("j4_fl", 0.8, "J4 grommet's flanges on each face of the wall")
    sq = "grommet_squeeze"
    wx0, wx1 = "sen_x1 + clr_align", "sen_x1 + clr_align + iwall"
    s.box("J4 notch", [f"{wx0} - 0.5", "j4n_y0", "floor_t"], ["iwall + 1", "j4n_w", "lid_z0 - floor_t + 0.5"],
          operation="cut", targets=["base_plate"])
    # B6: the halves' stack meets the floor and the lid at contact (no squeeze that would lift the lid)
    for half, z0, z1, zc0, zc1 in (("a", "floor_t", "j4n_zc", "floor_t", "j4n_zc"),
                                   ("b", "j4n_zc", "lid_z0", "j4n_zc", "lid_z0")):
        body = f"grommet_j4_{half}"
        s.box(f"J4 grommet {half}", [wx0, f"j4n_y0 - {sq}", zc0], ["iwall", f"j4n_w + 2 * {sq}", f"{zc1} - ({zc0})"], body=body)
        for side, xs in (("out", f"{wx0} - j4_fl"), ("in", wx1)):
            s.box(f"J4 grommet {half} flange {side}", [xs, "j4n_y0 - j4_fl", z0], ["j4_fl", "j4n_w + 2 * j4_fl", f"{z1} - {z0}"],
                  operation="join", targets=[body])
    s.cylinder("J4 grommet hole", [f"{wx0} - j4_fl - 1", "j4n_yc", "j4n_zc"], "cable_qw_d - bore_squeeze", "iwall + 2 * j4_fl + 2", axis="X",
               operation="cut", targets=["grommet_j4_a", "grommet_j4_b"])
    # tongue: the lid's hole, split at its centre
    p("tg_fl", 0.8, "tongue grommet's flange over the lid, past the hole")
    p("tg_fl_t", 0.6, "tongue grommet's flange thickness")
    p("tg_barb", 0.5, "tongue grommet's barb under the lid, past the hole's ends")
    p("tg_barb_t", 0.4, "tongue grommet's barb thickness, over the SFA40's Qwiic plug (0.4 + 0.09 above it)")
    top = "lid_z0 + lid_t"
    for half, xa, sgn in (("a", "lh_x - lid_hole_l / 2", "-"), ("b", "lh_x + lid_hole_l / 2", "+")):
        body = f"grommet_tongue_{half}"

        def span(xo, xa=xa, sgn=sgn):
            return (xo, "lh_x") if sgn == "-" else ("lh_x", xo)
        lo, hi = span(f"{xa} {sgn} {sq}")
        s.box(f"Tongue grommet {half}", [lo, f"lh_y0 - {sq}", "lid_z0"], [f"({hi}) - ({lo})", f"lid_hole_w + 2 * {sq}", "lid_t"], body=body)
        lo, hi = span(f"{xa} {sgn} tg_fl")
        s.box(f"Tongue grommet {half} flange", [lo, "lh_y0 - tg_fl", top], [f"({hi}) - ({lo})", "lid_hole_w + 2 * tg_fl", "tg_fl_t"],
              operation="join", targets=[body])
        lo, hi = (f"{xa} - tg_barb", f"{xa} + 0.6") if sgn == "-" else (f"{xa} - 0.6", f"{xa} + tg_barb")
        s.box(f"Tongue grommet {half} barb", [lo, "lh_y0", "lid_z0 - tg_barb_t"], [f"({hi}) - ({lo})", "lid_hole_w", "tg_barb_t"],
              operation="join", targets=[body])
        lo, hi = (xa, f"{xa} + 0.6") if sgn == "-" else (f"{xa} - 0.6", xa)
        s.box(f"Tongue grommet {half} neck", [lo, "lh_y0", "lid_z0 - tg_barb_t"], [f"({hi}) - ({lo})", "lid_hole_w", "tg_barb_t + lid_t / 2"],
              operation="join", targets=[body])
    s.cylinder("Tongue grommet hole", ["lh_x", "lh_y0 + lid_hole_w / 2", "lid_z0 - 1"], "cable_qw_d - bore_squeeze", "lid_t + tg_fl_t + 2",
               operation="cut", targets=["grommet_tongue_a", "grommet_tongue_b"])
