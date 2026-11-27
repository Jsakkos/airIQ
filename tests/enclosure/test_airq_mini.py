"""The airQ mini enclosure (Plan 3 Task 4a, owner decision 69.5 x 50 x 42, R51): enclosure/src/airq_mini.py.

Fast tests (CI included): the generator's bodies and the plan's parameter names, the owner's
envelope, the pose against `layout_study.mini_recheck(MINI_WAY_OUT, inlet_end="left")` (place a),
the lip's judgement call (three slot rows under the ledge, the SEN66's plug under the slant), the
positions read from their sources (R27), the sensor zone's construction (H2 over the module, the
boss pockets risen to the slant, the tongue on edge in the passage, the cables' drawer), and the
positions Task 4b needs. SolidCraft tests (skipped without solidcraft-cli): the build and its
bounding box, and the check design (test_airq_mini_check.py).
"""
import math

import pytest

import airq_mini
import board_sources as B
import enclosure_common as C
import encbuild
import layout_study as L
from sclib import evaluate

S = airq_mini.build()
V = S.v
BODIES = ["shell", "base_plate", "zone_wall", "zone_seal", "sen66_foam", "gasket_out", "gasket_in", "sen66_pad", "sen66_top_seal",
          "tongue_mount", "grommet_zone_a", "grommet_zone_b", "grommet_zone_c", "light_guide_co2", "light_guide_pm", "guide_stop", "orange_dot"]
STUDY = L.mini_recheck(L.MINI_WAY_OUT, inlet_end="left")
# positions Task 4b needs (task-4-scope "Split light band", "Rules and checks"), fixed here as parameters
FACE_4B = ["d1_x", "d2_x", "d3_x", "d4_x", "div_x0", "div_x1", "led_z", "led_f", "band_half", "band_h", "band_co2_x0", "band_co2_x1",
           "band_pm_x0", "band_pm_x1", "band_gap", "band_f0", "band_f1", "divider_t", "label_h", "label_depth", "label_f0", "label_f1",
           "label_co2_x", "label_pm_x", "sw_x", "sw_z", "dot_f", "dot_d", "veml_wx", "veml_wy", "veml_wz", "lsw_x", "lsw_z", "lsw_d",
           "slot_row1_z", "slot_row2_z", "slot_row3_z", "row_x0", "row_x1", "in_n", "in_len", "slot_bar",
           "out_pitch", "out_n", "out_gx0", "out_gx1", "out_gz0", "out_gz1", "exh_x0", "exh_x1", "exh_z0", "exh_z1",
           "usb_x", "usb_z", "usb_well", "usb_chamfer", "usb_plug_w", "usb_plug_h"]


def test_bodies_and_plan_parameters():
    assert S.bodies == BODIES
    for name in ("W", "D", "H", "tilt_deg", "wall", "floor_t", "grille_min_z", "slot_w", "clr_align", "clr_remove", "clr_snap", "lip",
                 "gasket_squeeze"):
        assert name in S.params, name
    for name in FACE_4B:
        assert name in S.params, name


def test_owner_envelope():
    """R51: 69.5 x 50 x 42, the 24 deg face, the lower lip."""
    assert (V("W"), V("D"), V("H")) == (69.5, 50.0, 42.0)
    assert S.params["tilt_deg"].value == 24.0
    assert V("lip") == 18.0
    # a taller lip moves the slope forward at every height: the study's minimum for D 50 stands
    assert L.min_lip(L.MINI_WAY_OUT, 50.0) <= V("lip")


def test_pose_is_the_studys_place_a():
    """The board, the SEN66 and the plate where mini_recheck(MINI_WAY_OUT, inlet end left) puts
    them: the board against the right wall as far back as the antenna allows, at the zone rule's
    height; the SEN66 against the right rail, its inlet end left, the 6.9 passage at the left; the
    plate just in front of H1's post (place a)."""
    b = STUDY["board"]
    assert V("board_z0") == pytest.approx(b["z0"])
    assert V("board_y0") == pytest.approx(b["y0"])
    assert V("board_x0") == pytest.approx(b["x0"])
    assert (V("sen_x0"), V("sen_x1")) == pytest.approx(STUDY["sen66_x"])
    assert V("passage") == pytest.approx(STUDY["passage"])
    place = STUDY["places"]["a: H1 in the plenum"]
    assert V("sen_y0") == pytest.approx(place["sen_y0"])
    assert V("D - wall - plate_y1") == pytest.approx(place["plenum"])
    assert (V("h1_x"), V("h1_y")) == pytest.approx(STUDY["h1"])
    assert (V("outlet_x"), V("outlet_z")) == pytest.approx(STUDY["ring"][:2])
    # the zone rule: SEN66 top + gap + zone wall + gap
    assert V("board_z0") == pytest.approx(V("floor_t + foam + sen_up + zone_gap + zone_t + zone_gap"))
    # the antenna strip's end clr_remove inside the rear wall
    assert V("board_y0 + board_d + antenna_out") == pytest.approx(V("D - wall - clr_remove"))


def test_sen66_keeps_r17_and_its_front_room():
    """Port face vertical (to the rear), the module's top front edge behind the slant, and in front
    of a module at the deepest the plug and the cable's bend (with the cable run) fit."""
    assert V("sen_y0") >= V(C.yb("sen_top")) + V("clr_remove") - 1e-9
    assert V("sen_y0 - sen_d_tol - sen_bend_out") >= V("wall + clr_remove")
    assert V("sen_y1") == pytest.approx(V("sen_y0 + sen_d"))
    assert V("plate_y0 - sen_y1") == V("port_gap")


def _z_under(y):
    return V(C.z_under(str(y)))


def _t(y, z):
    return y * V("cos_t") - (z - V("lip")) * V("sin_t")


def test_lip_18_keeps_three_slot_rows_and_the_plug_under_the_slant():
    """Judgement call (README): lip 18.0, not the study's 15.5.
    - three slot rows from the 10 mm line need the ledge's underside over 16.0; the rows give
      >= 154.5 mm2 (R18) between the light-sensor window and the right boss pocket;
    - at place a the deepest module's plug (top front corner) and the bend clear the zone wall's
      underside by clr_remove (at 15.5 the plug's corner would be 0.68 inside the slant)."""
    top = V("slot_row3_z + slot_w")
    assert top <= V("ledge_z0") - 0.2
    open_ = V(airq_mini.INTAKE_OPEN)
    assert open_ >= 154.5
    assert V("in_len") > 0 and V("row_x0") >= V("lsw_x + lsw_d / 2") and V("row_x1") <= V("bp_x0")
    deep = V("sen_y0 - sen_d_tol")
    corner = (deep - V("sen_plug_out"), V("sen_mid + sen_plug_h / 2"))
    bend = (deep - V("sen_bend_out"), V("sen_mid + sen_bend_top"))
    for y, z in (corner, bend):
        assert _z_under(y) - z >= V("clr_remove") - 1e-9, (y, z, _z_under(y))
    # two rows are all a 15.5 lip would take: short of R18's 154.5 (and of the 112 floor), and the plug meets the slant
    rows_155 = math.floor((15.5 - 1.2 - 0.2 - 10.0 + 1.2) / 2.4)
    assert rows_155 == 2 and rows_155 * V("in_n") * V("in_len") * V("slot_w") < 112
    lo = 15.5
    t_b = V("zw_tf + zone_t")
    t_corner = corner[0] * V("cos_t") - (corner[1] - lo) * V("sin_t")
    assert t_b - t_corner > 0.6                                                     # inside the slant at 15.5


def test_positions_are_read_from_their_sources():
    main = B.MAIN
    x0, ztop = V("board_x0"), V("board_z0 + board_t")
    yb = V("board_y0 + board_d")
    for d in main["leds"]["chain"]:
        assert V(f"{d['ref'].lower()}_x") - x0 == pytest.approx(d["center_x"])
    assert (V("div_x0") - x0, V("div_x1") - x0) == pytest.approx(tuple(main["leds"]["divider_gap"]))
    assert V("sw_x") - x0 == pytest.approx(main["button"]["actuator_center_x"])
    assert V("sw_z") - ztop == pytest.approx(main["button"]["actuator_center_z"])
    assert V("usb_x") - x0 == pytest.approx(main["usb_c"]["center_x"])
    assert V("led_z") - ztop == pytest.approx(main["leds"]["light_center_z"])
    (h1x, h1y), (h2x, h2y) = main["mounting_holes"]["centers"]
    assert (V("h1_x") - x0, yb - V("h1_y")) == pytest.approx((h1x, h1y))
    assert (V("h2_x") - x0, yb - V("h2_y")) == pytest.approx((h2x, h2y))
    assert V("j2_face_x") - x0 == pytest.approx(main["j_sen66"]["mating_face_x"])
    assert V("j4_face_x") - x0 == pytest.approx(main["j_qwiic_aux"]["mating_face_x"])
    tg = B.TONGUE
    assert (V("tongue_w"), V("tongue_dp"), V("tongue_t")) == (tg["outline"][0], tg["outline"][1], tg["thickness"])
    assert V("veml_wz") - V("tongue_z0") == pytest.approx(tg["veml7700"]["window_center"][0])
    assert V("veml_wx") - V("tongue_x0 + tongue_t") == pytest.approx(tg["veml7700"]["window_center"][2])


def test_band_halves_and_labels():
    """The split band's halves are centred on their LED pairs (CO2 D1/D2 left, PM2.5 D3/D4 right),
    about 21 mm each, the visible gap >= 4 over the board's divider gap; the labels sit under the
    band on the slope; the dot is on SW1's axis and keeps an opaque wall off the PM2.5 half."""
    assert V("band_co2_x1 - band_co2_x0") == V("band_pm_x1 - band_pm_x0") == 20.5     # about 21 (Task 4b: 20.5, the flexure's room)
    assert V("band_gap") >= 4.0
    assert V("div_x0") < V("band_co2_x1") and V("band_pm_x0") < V("div_x1")       # the halves' ends over the LED-free gap
    assert V("band_co2_x0") > V("-inner_x") and V("band_pm_x1") < V("inner_x")
    assert V("label_f0") > V("lip") and V("band_f1") < V("lip + (H - lip) / cos_t - edge_chamfer")
    assert V("sw_x - dot_d / 2 - band_pm_x1") >= 1.2
    assert V("dot_f") == pytest.approx(V("lip + (sw_z - lip) / cos_t"))


def test_guide_fits_come_from_the_clearances():
    """Task 4b: every fit of the two guides is a clr_* parameter (no literals, no zero-gap contact):
    the tongue clr_align in its slot (sides and ends), the flange clr_align behind the wall's inner
    face, the bar clr_align in front of `guide_stop`, the feet clr_align inside the stop's windows,
    the entry faces clr_remove in front of the LED faces; the guides' ends clr_align off the ribs;
    the ribs and the stop clr_remove over the zone wall and in front of the board's edge."""
    import airq_mini_face as MF
    assert S.params["lg_tg"].expression == "clr_align" and S.params["stop_y1"].expression == "board_y0 - clr_remove"
    assert V("lg_tf - wall") == pytest.approx(V("clr_align"))
    assert V("lg_ysf - lg_yb") == pytest.approx(V("clr_align"))
    assert V("board_y0 - stop_y1") == pytest.approx(V("clr_remove")) and V("stop_y1 - lg_ye") == pytest.approx(V("lg_ein"))
    assert V("stop_t") >= 1.2 and V("end_rib_t") >= 1.2 and V("band_pm_x0 - band_co2_x1") >= V("divider_t")
    assert V("rib_z0") >= V("zw_z1 + clr_remove") - 1e-9          # the ribs and the stop come down over the zone wall
    # retention: the flange laps the wall's inner face round the slot, the stop catches the bar's back
    bar = [(V(a), V(b)) for a, b in MF.bar_profile()]
    assert bar[3][0] > V("lg_s1") + 0.5 and bar[6][0] < V("lg_s0") - 0.5
    for x0, x1, z0, z1 in MF.stop_windows():
        assert V(f"({x1}) - ({x0})") > 0 and V(z0) > V("rib_z0") and V(z1) < V("stop_z1")
        # review M3: die-cuttable webs over and under the windows, the stop under the slope's inner face
        assert V(f"stop_z1 - ({z1})") >= 1.6 - 1e-9 and V(f"({z0}) - rib_z0") >= 1.5
    assert V("stop_z1") < V("lip + (lg_ysf * cos_t - wall) / sin_t") - 0.5
    # the feet inside their LED faces (R13: a line from a foot toward U4 enters the LED body)
    for i in (1, 2, 3, 4):
        assert V(f"lg_f{i}_x0") > V(f"d{i}_x - led_face_w / 2") and V(f"lg_f{i}_x1") < V(f"d{i}_x + led_face_w / 2")
    assert V("led_z - led_face_h / 2") < V("lg_fz0") < V("lg_fz1") < V("led_z + led_face_h / 2")
    # the PM2.5 half's end rib keeps clear of the flexure's slot; >= 1.2 of face between them
    chk = MF.band_x_check(V) if "flex_x0" in S.params else None
    if chk:
        assert chk["rib_to_flex"] > 0 and chk["face_to_flex"] >= 1.2


def test_hold_pads_stand_on_the_zone_wall():
    """Review I1: the shell's hold-down pads (under the three band ribs and one left of them) bear on the zone
    wall's flat top at contact (hold_squeeze 0), behind its front top edge, in front of the board's edge, clear
    of the left boss notch; the drawer grommet's bottom is at contact on the rail."""
    import airq_mini_face as MF
    assert V("hold_z0") == V("zw_z1") and V("hold_squeeze") == 0
    assert V("lg_ysf") < V("board_y0 - clr_remove")
    assert V("hold_lx0") > V("-boss_x + boss_d / 2 + clr_remove")
    spans = MF.hold_spans()
    assert set(spans) == {"divider", "left", "right", "left pad"}
    for x0, x1 in spans.values():
        assert V(f"({x1}) - ({x0})") >= 1.2 - 1e-9
    names = {c["params"].get("name") for c in S.commands}
    assert {f"Hold pad {n}" for n in spans} <= names


def test_drawer_grommet_split_is_pressed_shut():
    """Review round 2, M2: the drawer grommet is three pieces split across y through the two cables' axes (as the
    airQ's), so the notch's front and rear faces squeeze both splits (drawer_squeeze each): the press acts between
    two faces of the zone wall, and the shell's x float (+-0.2, screws in screw_d holes) and the zone wall's (+-0.15,
    H1's spigot in its seat) do not enter it at any corner. Every piece reaches the notch's closed end, stands on the
    rail at contact and keeps clr_remove from the shell's side wall."""
    import airq_mini
    boxes = {piece: next(c["params"] for c in S.commands if c["params"].get("name") == f"Zone grommet {piece}") for piece in "abc"}
    y = {k: (V(b["corner"][1]), V(f"{b['corner'][1]} + {b['width']}")) for k, b in boxes.items()}
    assert y["a"][1] == pytest.approx(V("gh_y")) == pytest.approx(y["b"][0])
    assert y["b"][1] == pytest.approx(V("qw_y")) == pytest.approx(y["c"][0])
    assert y["c"][1] - y["a"][0] == pytest.approx(V("dr_y1 - dr_y0 + 2 * drawer_squeeze"))      # the notch squeezes the stack
    for b in boxes.values():
        assert V(b["corner"][0]) == pytest.approx(V("-inner_x + clr_remove"))
        assert V(f"{b['corner'][0]} + {b['length']}") == pytest.approx(V("dr_x1 + drawer_squeeze"))
        assert V(b["corner"][2]) == pytest.approx(V("zw_z0"))
    # the floats: the shell's and the zone wall's x play, both larger than the press, are outside the press's path
    assert V("(screw_d - 2) / 2") > V("drawer_squeeze") and V("clr_align") > V("drawer_squeeze")
    assert [p for p, *_ in airq_mini.GROMMET_PIECES] == ["a", "b", "c"]
    assert V("drawer_floor_squeeze") == 0


def test_labels_and_light_sensor_window():
    """Task 4b: "CO2" under the left half and "PM2.5" under the right, debossed 0.4, 5 mm tall (the
    coupon's legible size); the CO2 label's subscript is a 3.5 mm "2" (strokes about 0.48 above the
    0.4 nozzle). The light-sensor window: low on the lip, left of the rows, its lower edge over the
    10 mm line; the VEML7700's line to it passes under the zone wall's ledge and the zone seal, right
    of the left boss pocket's inner wall."""
    assert V("label_h") >= 5.0 and V("label_depth") == 0.4 and 0.136 * V("label_sub_h") >= 0.45
    co_x0 = V("label_co_x - label_co_w / 2")
    sub_x1 = V("label_sub_x + label_sub_w / 2")
    assert V("band_co2_x0") < co_x0 and sub_x1 < V("band_co2_x1")
    assert (co_x0 + sub_x1) / 2 == pytest.approx(V("label_co2_x"))
    pm_w = 4.02 * V("label_h")                                         # "PM2.5" in the built-in font: 20.1 wide at 5
    assert V("band_pm_x0") < V("label_pm_x") - pm_w / 2 and V("label_pm_x") + pm_w / 2 < V("band_pm_x1")
    assert V("label_f0 - label_sub_drop") > V("lip") + 1.0 and V("label_f1") < V("band_f0")
    assert V("lsw_z - lsw_d / 2") >= V("grille_min_z")
    vw, ww = (V("veml_wy"), V("veml_wz")), (V("wall"), V("lsw_z"))
    y_seal = V("wall + seal_t")
    z_at = vw[1] + (ww[1] - vw[1]) * (vw[0] - y_seal) / (vw[0] - ww[0])
    assert z_at < V("ledge_z0")
    assert min(V("veml_wx"), V("lsw_x")) > V("-bp_x0") and V("lsw_x - lsw_d / 2") > V("-bp_x0")


def test_dot_and_flexure_on_sw1s_axis():
    """Task 4b: the airQ's flexure (airq_face) on the mini's SW1: the dot top right, on SW1's push
    axis (x and z of the actuator), a beam of the wall's skin (the coupon's flex_t x flex_w x flex_len),
    the pad rod's end flex_gap in front of the actuator's tip; the hard stop is SW1's own body (the rod
    bottoms on it 0.04 after the switch has bottomed), no printed stop gap. Printable face down: the
    rod's axis (+y) is tilt_deg (24) from the face's normal, the beam is the first layers on the bed."""
    assert V("dot_s") == pytest.approx(V("dot_f - lip"))
    assert V("flex_x0 + flex_x1") / 2 == pytest.approx(V("sw_x"))
    assert V("y_pad") == pytest.approx(V("sw_tip - flex_gap"))
    assert V("flex_stop") == pytest.approx(V("board_y0 - y_pad")) and V("flex_over") > 0
    assert V("flex_stop") > V("flex_gap + sw_travel")
    assert math.degrees(V("tilt_deg")) <= 45
    assert V("sw_x - dot_d / 2") > V("band_pm_x1 + end_rib_t")          # right of the PM2.5 half and its end rib
    assert V("flex_x1 + flex_slot") < V("inner_x")                      # the U slot stays inside the side wall
    # the U slot's lowest inner edge over the 10 mm line
    assert V("lip + flex_s0 * cos_t - wall * sin_t") >= V("grille_min_z")
    names = {c["params"].get("name") for c in S.commands}
    assert {"Flex thin", "Flex slot", "Pad rod", "Flex trim", "Dot recess", "Orange dot"} <= names


def test_h2_lies_over_the_sen66_so_it_has_no_post():
    """H2 (x 30.15) is over the module (x -24.25 ... 30.95), so a post from the floor cannot stand
    there: the board's H2 screw takes a blind pilot in the zone wall's pad, 0.5 of zone wall under
    it, so the zone wall stays closed."""
    r = V("standoff_d") / 2
    assert V("sen_x0") < V("h2_x") - r and V("h2_x") < V("sen_x1") + r
    assert V("sen_y0") < V("h2_y") < V("sen_y1")
    assert V("zw_z0") < V("board_z0 - zw_pilot_depth") - 0.4
    # review M6: H2's M2 x 3 ends in its pilot, over the skin; one 1 mm longer would reach the SEN66's top
    tip = V("board_z0 + board_t - h2_screw_len")
    assert V("board_z0 - zw_pilot_depth") <= tip and tip - 1.0 <= V("sen_top")
    names = {c["params"].get("name") for c in S.commands}
    assert "Standoff H1" in names and "Standoff H2" not in names
    assert "Zone wall pilot H2" in names and "Zone wall screw hole H2" not in names


def test_board_screws_and_usb_support_boss():
    """R10a: M2 at H1 into its standoff's pilot, which is H1's post: the USB-C support boss, within
    8 mm of the USB-C's centre (interface.yaml), braced to the plate by its web."""
    usb_c = (V("usb_x"), V("board_y0 + board_d") - B.usb_len() / 2)
    assert math.hypot(V("h1_x") - usb_c[0], V("h1_y") - usb_c[1]) <= 8.0
    assert V("plate_y1") < V("h1_y - standoff_d / 2") < V("plate_y1 + 0.5")      # the web spans the gap


def test_boss_pockets_rise_to_the_slant():
    """The zone wall's slant hugs the slope, so its ledge (to yb(ledge_z0)) ends in front of the
    boss pockets' back walls: their inner and back walls rise to the slant's underside, and the
    rails start under it."""
    assert V(C.yb("ledge_z0")) < V("bp_y1 - iwall")
    names = {c["params"].get("name") for c in S.commands}
    for side in "LR":
        assert {f"Boss pocket {side} inner rise", f"Boss pocket {side} back rise"} <= names
    pts = C.under_profile(S, "bp_y1 - iwall", "bp_y1", "ledge_z0 - 0.5")
    tops = [(V(y), V(z)) for y, z in pts[2:]]
    for y, z in tops:
        assert z == pytest.approx(_z_under(y))


def test_tongue_on_edge_in_the_passage():
    """The tongue stands in the passage, its parts toward the module's left end (clr_remove +
    clr_align), its board's back clr off the pin's collar, its front behind the SEN66 cable's
    drop; the VEML7700 high (the tongue's handedness, README); in the intake air; >= 20 from U3
    and U2 (the airQ's arithmetic, boxes)."""
    assert V("tongue_x0") > V("-tub_x")
    assert V("sen_x0 - (tongue_x0 + tongue_t + tongue_parts_h)") == pytest.approx(V("clr_remove + clr_align"))
    assert V("tongue_top") < V("zw_z0") and V("tongue_z0") > V("floor_t")
    assert V("tongue_y0 + tongue_dp") < V("sen_y1")
    assert V("veml_wz") > V("ledge_z0")                     # high: the window is below it (4b)
    # the pin through the hole, inside the passage; the shank stays in the hole with the tongue against the module
    assert V("tm_out") > V("clr_remove + clr_align")        # slid against the module, the board is still on the shank
    # review M4: the pin's tip clr_remove from the module's end, so the pin stays in its blind hole: at most
    # tm_travel out (tip gap, the module's float to the right rail, a 0.4 short module) of tm_hole_depth
    pin = next(c["params"] for c in S.commands if c["params"].get("name") == "Tongue pin")
    assert V(f"{pin['base'][0]} + {pin['height']}") == pytest.approx(V("sen_x0 - clr_remove"))
    assert V("tm_travel") == pytest.approx(V("2 * clr_remove + sen_l_short"))
    assert V("tm_hole_depth - tm_travel") >= 0.15
    assert V("tm_collar_d") <= V("tongue_hole_clear") and V("tm_pin_d") < V("tongue_hole_d")
    assert V("-tub_x - tm_hole_depth") > V("-tub_x - iwall")  # the pin's hole is blind: the rail is not opened
    d = mini_distances()
    assert d["tongue_to_u3"] >= 20 and d["tongue_to_u2"] >= 20


def test_plug_room_and_drawer():
    """J2 and J4 have the study's room past a 5.0 plug envelope; both cables pass the zone wall in
    one drawer over the passage's rear, left of the board's edge, in front of the plate, behind the
    tongue's plug; the grommet's halves split on the cables' line."""
    assert V("j2_face_x + inner_x - clr_remove") == pytest.approx(STUDY["plugs"]["j_sen66"])
    assert V("j4_face_x + inner_x - clr_remove") == pytest.approx(STUDY["plugs"]["j_qwiic_aux"])
    assert V("j2_room") > 0 and V("j4_room") > 0
    assert V("cab_x + cable_gh_d / 2") < V("board_x0") and V("cab_x - cable_gh_d / 2") > V("-tub_x")
    assert V("dr_y1") < V("plate_y0") and V("dr_y0") > V("tongue_y0 + tq_mate")
    assert V("qw_y - cable_qw_d / 2") > V("tq_plug_y1")
    assert V("dr_x1") <= V("board_x0 + 0.1")
    assert V("j2_y0") < V("gh_y") + 5 and V("qw_y") < V("j4_y1")


def test_grilles_r18_and_10_mm_rule():
    """R18: the intake >= 154.5; the outlet 498 (< 660.1, >= 296: owner item); the openings' lower
    edges on or above the 10 mm line; the exhaust over the zone wall's top."""
    assert V(airq_mini.OUTLET_OPEN) == pytest.approx(STUDY["grille"]["open"])
    assert 296 <= V(airq_mini.OUTLET_OPEN) < 660.1
    assert V("out_gx1") <= V("tub_x - 1.9")
    for name in ("slot_row1_z", "out_gz0"):
        assert V(name) >= V("grille_min_z")
    assert V("lsw_z - lsw_d / 2") >= V("grille_min_z")
    assert V("exh_z0") > V("zw_z1")


def test_openings_are_cut_where_the_parameters_say():
    """Task 4b: 3 x in_n intake slots, the window, out_n outlet slots, exh_n exhaust slots and the USB-C
    opening with its chamfer, all cut in base_plate; the exhaust right of the USB-C opening, over the
    zone wall, under the top wall; the USB-C opening passes the overmold with clr_remove a side."""
    cuts = [c["params"] for c in S.commands if c["params"].get("operation") == "cut" and c["params"].get("targets") == ["base_plate"]]
    names = [c["name"] for c in cuts]
    assert sum(n.startswith("Intake slot ") for n in names) == 3 * V("in_n")
    assert sum(n.startswith("Outlet slot ") for n in names) == V("out_n")
    assert sum(n.startswith("Exhaust slot ") for n in names) == V("exh_n")
    assert {"Light-sensor window", "USB-C opening"} <= set(names)
    assert "USB-C chamfer" in {c["params"].get("name") for c in S.commands}
    assert V("exh_gx1") <= V("exh_x1") and V("exh_x0") > V("usb_x + usb_open_w / 2")
    assert V("exh_z0") > V("zw_z1") and V("exh_z1") < V("H - wall")
    assert V("usb_open_w - usb_plug_w") == pytest.approx(2 * V("clr_remove"))
    assert V("usb_z - usb_open_h / 2") >= V("grille_min_z")
    assert V("row_x0 + in_n * in_len + (in_n - 1) * slot_bar") == pytest.approx(V("row_x1"))


def test_feet_cover_the_screw_heads():
    """R10b: the front felt feet cover the shell's screw heads and stand taller than them, and all
    four stay on the bottom face (the airQ's R35 deferred minor: its front feet overhang)."""
    r = V("foot_d") / 2
    assert V("foot_d") >= V("head_d") + 1.0
    assert V("foot_t") > V("head_h - head_depth")
    assert V("boss_x") + r <= V("W / 2") and V("boss_y") - r >= 0
    assert V("foot_rx") + r <= V("W / 2") and V("foot_ry") + r <= V("D")


def test_inlet_seal_mirrors_the_airqs():
    """The wiper's outline is the airQ's mirrored about its root's inner edge (hand +1)."""
    a = C.wiper_profile(hand=-1)
    b = C.wiper_profile(hand=1)
    x1 = V("wiper_x1")
    for (xa, ya), (xb, yb) in zip(a, b):
        assert V(xb) - x1 == pytest.approx(-(V(xa) - x1))
        assert V(yb) == pytest.approx(V(ya))
    assert V("wiper_x1") > V("inlet_x1") and V("wiper_x1 + wiper_lean + wiper_w") < V("outlet_x - ring_od / 2")


def mini_distances():
    import airq_mini_check
    return airq_mini_check.distances(S)


def test_distances_answered_by_the_layout():
    """R12 (owner item: maximised, recorded) and the 15 mm rule for the USB plug, the inserts and
    the screws, from the parameters and the boards' sources."""
    d = mini_distances()
    assert d["antenna_to_sen66"] == pytest.approx(STUDY["places"]["a: H1 in the plenum"]["antenna_to_sen66"])
    assert d["antenna_to_usb_plug"] >= 15 and d["antenna_to_bosses"] >= 15 and d["antenna_to_screws"] >= 15


# --- SolidCraft --------------------------------------------------------------------------

def test_build_and_bounding_box(cli):
    r = encbuild.build("airq-mini", cli, commit=False)
    box = encbuild.union(r["bodies"].values())
    assert box["min"] == pytest.approx([-34.75, 0.0, 0.0], abs=0.01)
    assert box["max"] == pytest.approx([34.75, 50.0, 42.0], abs=0.01)
    assert not r["warnings"]
    assert sorted(r["bodies"]) == sorted(BODIES)


def test_readme_check_table_labels_every_row():
    """Task 4a: the README's "Check table (airQ mini)" says how each value was got: measured,
    analytic or arithmetic, in bold."""
    from sclib import ENCLOSURE
    text = (ENCLOSURE / "README.md").read_text(encoding="utf-8")
    table = text.split("### Check table (airQ mini)", 1)[1].split("\n### ", 1)[0]
    rows = [r for r in table.splitlines() if r.startswith("| ") and not r.startswith("| Check") and not r.startswith("|---")]
    assert len(rows) >= 20
    for r in rows:
        cells = r.split(" | ")
        assert any(f"**{k}**" in cells[3] for k in ("measured", "analytic", "arithmetic")), r
