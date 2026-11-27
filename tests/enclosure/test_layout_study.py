"""The layout studies (enclosure/src/layout_study.py, enclosure/README.md "Layout studies").

Fast tests (pure Python, CI included): the section arithmetic behind the studies' claims for the
airQ and the airQ mini, so a change to interface.yaml, a reference part or a margin that changes
a conclusion fails here.
"""
import math
from dataclasses import replace

import pytest

import layout_study as L
from sclib import interface

AIRQ, MINI = L.AIRQ, L.MINI
AIRQ_BEST = replace(AIRQ, **L.BEST_CASE)
MINI_BEST = replace(MINI, **L.BEST_CASE)


def test_face_coordinates_round_trip():
    for m in (AIRQ, MINI, replace(MINI, lip=15.0)):
        for s, t in ((0, 0), (11.5, 0), (30, 1.8), (40, 3)):
            y, z = L.yz_of(m, s, t)
            assert L.s_of(m, y, z) == pytest.approx(s) and L.t_of(m, y, z) == pytest.approx(t)
    # the airQ face's top edge: 48 / cos 30 up the face, at y = 48 tan 30
    assert L.yz_of(AIRQ, 48 / math.cos(math.radians(30)), 0) == pytest.approx((48 * math.tan(math.radians(30)), 48))
    lip = replace(MINI, lip=15.0)
    assert L.face_length(lip) == pytest.approx(15 + 27 / math.cos(math.radians(24)))
    assert L.front_inner_y(lip, 10) == pytest.approx(lip.wall)


def test_inputs_are_read_from_interface_yaml_and_the_references():
    mech = interface()["mechanical"]
    m = mech["main"]
    assert m["outline"] == [60.0, 30.0] and m["thickness"] == 1.6       # layout_study.offset's frame
    assert AIRQ.tongue_d == mech["tongue"]["outline"][1]
    pts = {(Y, Z) for Y, Z, _ in L.board_points()}
    assert (m["antenna"]["module_body"][0][1], 0.0) in pts                  # antenna strip end, -5.99
    assert (m["button"]["actuator_tip_y"], m["button"]["actuator_center_z"]) in pts
    assert (m["j_sen66"]["body"][0][1], m["max_part_height"]) in pts          # J2, the tallest part
    r = L._refs()
    assert (r["sen_w"], r["sen_h"], r["panel_w"], r["panel_t"]) == (25.6, 21.3, 36.7, 1.2)
    assert L.sen_dims(AIRQ) == (21.3, 25.6) and L.sen_dims(replace(AIRQ, sen_pose="flat")) == (25.6, 21.3)


# --- airQ -------------------------------------------------------------------------------

@pytest.mark.parametrize("m", [AIRQ, AIRQ_BEST], ids=["default", "best_case"])
def test_airq_no_pose_fits_the_plan_envelope(m):
    """95 x 55 x 48 +- 1 with the whole front sloped: no tilt of the main board fits."""
    for a in L.ALPHAS:
        assert L.pose(replace(m, D=56.0), a) is None, a


@pytest.mark.parametrize("m", [AIRQ, AIRQ_BEST], ids=["default", "best_case"])
def test_airq_horizontal_board_needs_about_8_mm_more_depth(m):
    assert L.horizontal_overflow(m) > 7.5           # the antenna end through the rear wall at D 55
    d = L.min_depth(m, 0)
    assert 62.5 < d < 63.5
    p = L.pose(replace(m, D=d + 0.01), 0)
    assert p["zone_order"] and p["usb_rear"] and p["dot_f"] is not None


@pytest.mark.parametrize("m", [AIRQ, AIRQ_BEST], ids=["default", "best_case"])
def test_airq_poses_within_a_few_mm_break_the_rules(m):
    """Every tilt that fits within D 59 (55 + 4) puts the board below the SEN66's top (the zone
    rule), the USB-C plug through the top face, the button's push axis along the face (no dot can
    press it) and the antenna strip within 4 mm of the panel."""
    small = [a for a in L.ALPHAS if (d := L.min_depth(m, a)) is not None and d <= 59.0]
    assert small and min(small) >= 55
    for a in small:
        p = L.pose(replace(m, D=59.0), a)
        assert not p["zone_order"] and not p["usb_rear"] and p["dot_f"] is None
        assert p["antenna_behind_front"] < 4.0


@pytest.mark.parametrize("m", [AIRQ, AIRQ_BEST], ids=["default", "best_case"])
def test_airq_rules_kept_need_at_least_60_5_mm(m):
    b = L.best(m)
    assert b["min_D"] > 60.5 and b["pose"]["zone_order"] and b["pose"]["usb_rear"]


def test_airq_face_budget():
    """The plan's face (two slot rows from the 10 mm line, the 1.2 mm LED slot, the panel pocket)
    overflows a 48 mm face; the LED line inside the top slot row fits but leaves the intake grille
    under 2x the inlets' 77.3 mm2; a 50 mm face holds it all."""
    b = L.face_budget(AIRQ)
    assert b["f10"] == pytest.approx(10 / math.cos(math.radians(30)))
    assert b["spare"] < -1.5
    b = L.face_budget(AIRQ, led_in_slot_row=True)
    assert b["spare"] > 0 and b["open_area"] < L.INTAKE_MIN
    b = L.face_budget(replace(AIRQ, H=50.0))
    assert b["spare"] > 0.5 and b["open_area"] >= L.INTAKE_MIN
    assert 49.0 < L.min_face_height(AIRQ) < 50.0


def test_airq_lip_and_hood_variants():
    """A 14.5 mm vertical lower lip (a look change) fits 55 deep on a 50 mm face; a rear hood for
    the antenna strip fits 57.3 deep, and with a 4 mm lip 55."""
    lip = L.min_lip(AIRQ, 55.0)
    assert 14.0 < lip < 14.5
    m = replace(AIRQ, lip=14.5)
    assert L.min_depth(m, 0) <= 55.0
    assert L.min_face_height(m) < 50.5
    p = L.pose(replace(m, D=55.0), 0)
    assert p["zone_order"] and p["usb_rear"] and p["tongue_fits"] and p["dot_f"] is not None
    h = replace(AIRQ, hood=True)
    d = L.min_depth(h, 0)
    assert 57.0 < d < 57.5
    assert L.pose(replace(h, D=d + 0.01), 0)["hood_out"] == pytest.approx(6.0, abs=0.1)
    assert L.min_lip(h, 55.0) < 4.5


def test_airq_recommended_layout():
    """95 x 63.5 x 50 with the board horizontal: every rule the section answers is kept."""
    m = replace(AIRQ, D=63.5, H=50.0)
    p = L.pose(m, 0)
    assert p is not None and p["zone_order"] and p["usb_rear"] and p["tongue_fits"]
    assert p["antenna_behind_front"] > 15 and p["antenna_to_sen66"] >= 15     # R12
    assert 0.6 < p["dot_f"] / L.face_length(m) < 0.8                         # upper part of the face
    x = L.x_layout(m)
    assert x["sen66_to_antenna_x"] >= 15
    assert x["dot_left_margin"] >= 0
    assert x["panel"][0] - L._refs()["block_out"] >= -(m.W / 2 - m.wall)       # hatched block inside


def test_airq_outlet_grille_takes_the_whole_lower_rear():
    g = L.outlet_grille(AIRQ)
    assert g["meets_2x"] and g["open_area"] < L.OUTLET_MIN * 1.01


# --- airQ mini --------------------------------------------------------------------------

@pytest.mark.parametrize("m", [MINI, MINI_BEST], ids=["default", "best_case"])
def test_mini_no_lipless_pose_fits_the_hard_max(m):
    """66 x 50 x 42 with the whole front sloped: no tilt fits (R15's tilted board is not enough;
    the steepest tilts come closest, 53-54 mm, and break the zone rule)."""
    for a in L.ALPHAS:
        d = L.min_depth(m, a)
        assert d is None or d > 53.0, a
    b = L.best(m)
    assert b["alpha"] <= 5 and b["min_D"] > 55.5


def test_mini_lower_lip_fits():
    """R15's short vertical lower lip: about 15 mm lets the horizontal board fit 50 deep, with the
    tongue in front of the SEN66 and the USB-C through the rear wall."""
    lip = L.min_lip(MINI, 50.0)
    assert 14.5 < lip < 15.5
    m = replace(MINI, lip=15.5)
    assert L.min_depth(m, 0) <= 50.0
    p = L.pose(replace(m, D=50.0), 0)
    assert p["zone_order"] and p["usb_rear"] and p["tongue_fits"]
    assert p["dot_f"] / L.face_length(m) > 0.75                              # top right
    assert L.band_budget(m, band_f=p["led_f"] - 1.0)["spare"] > 0            # band at the LEDs, labels and slots below


def test_mini_hood_alone_does_not_fit():
    h = replace(MINI, hood=True)
    d = L.min_depth(h, 0)
    assert 50.0 < d < 51.0
    assert not L.pose(replace(h, D=d + 0.01), 0)["tongue_fits"]              # no room for the tongue either


def test_mini_antenna_cannot_reach_15_mm():
    """R12: the 60 mm board fills the 62.4 mm interior, so the antenna strip stands over the
    SEN66's end; record the distance and flag it (owner item, RSSI check)."""
    p = L.pose(replace(MINI, lip=15.5, D=50.0), 0)
    assert p["antenna_to_sen66"] < 6.0 and p["antenna_to_sen66_max"] < 15.0
    assert L.x_layout(MINI)["sen66_to_antenna_x"] == 0.0


def test_mini_outlet_grille_short_of_2x():
    g = L.outlet_grille(MINI)
    assert not g["meets_2x"] and g["meets_floor"]                             # R18: flag, owner item


def test_mini_front_budget_and_plan_view():
    b = L.band_budget(MINI)
    assert b["open_area"] >= L.INTAKE_MIN and b["rows"] == 3 and b["band_fits"] and b["spare"] > 0
    x = L.x_layout(MINI)
    assert x["board_side_gap"] == pytest.approx((1.2, 1.2))
    assert x["band_gap"] >= 4.0                                              # the plan's gap
    assert x["dot_to_band"] >= MINI.face_wall                                # opaque wall to the dot


# --- the owner's questions ---------------------------------------------------------------

@pytest.mark.parametrize("m,depth", [(AIRQ, 55.0), (MINI, 50.0)], ids=["airq", "mini"])
def test_what_the_questions_buy(m, depth):
    a = {r["name"]: r for r in L.answers(m, depth)}
    plan = a["as planned"]
    flat = a["SEN66 lying flat (breaks Sensirion's rule)"]
    walls = a["walls 1.6 everywhere"]
    assert 1.5 < plan["horizontal_D"] - flat["horizontal_D"] < 3.0          # flat SEN66: about 2-2.5 mm
    assert flat["horizontal_D"] > depth                                      # and still does not fit
    assert 0.0 < plan["horizontal_D"] - walls["horizontal_D"] < 0.6          # 1.6 walls: under 0.6 mm
    if m is AIRQ:
        tilt = a["tilt 25 deg"]
        assert 3.5 < plan["horizontal_D"] - tilt["horizontal_D"] < 4.5       # 25 deg: about 4 mm
        assert tilt["face_H"] > 51.0                                         # but a taller face


# --- fix round 1 (R25, R26) ----------------------------------------------------------------

def test_ports_forward_front_layer_cannot_carry_the_outlet():
    """R25: with the ports facing the front (3a before fix round 1), an outlet duct along the
    module's front has at most the sensor zone in front of it: under 330.1 even with the strip
    under the ledge, and the module cannot move back (H1 stands behind it)."""
    m = replace(AIRQ, lip=15.0, H=51.0)
    assert 200 < L.front_layer(m, 20.0) < 230
    assert L.front_layer(m, 20.0, under_ledge=True) < L.PORT_OUTLET
    assert L.front_layer(m, 25.0) > L.PORT_OUTLET          # it would take the module 5 mm further back


def test_hcho_alternatives_by_slot_count():
    """R26: grille areas count whole 1.2 mm slots (a 3.0 pitch is 40 %, 2.4 is 50 %)."""
    rows = L.hcho_alternatives(replace(AIRQ, lip=15.0, H=51.0))
    built = rows[0]
    assert built["open_40"] == pytest.approx(18 * 1.2 * 18.9) and built["open_40"] < L.OUTLET_MIN
    assert all(not r["meets"] for r in rows[:-1]) and rows[-1]["meets"]


# --- Task 4a: the mini re-checked with the airQ's construction (README "airQ mini (Task 4)") ----------

def test_mini_task4_board_pose_and_sensor_zone():
    r = L.mini_recheck()
    lo, hi = r["board"]["y_range"]
    # the zone rule: SEN66 top 2.0 + 1.0 + 25.6, gaps 0.3, zone wall 1.8
    assert r["board"]["z0"] == pytest.approx(2.0 + 1.0 + 25.6 + 0.3 + 1.8 + 0.3)
    assert lo <= r["board"]["y0"] == pytest.approx(hi)
    assert r["board"]["antenna_end"] == pytest.approx(50 - 1.8 - 0.2, abs=0.02)      # the antenna strip binds at the rear wall
    # the tub: 66 - 2 x (1.8 + 0.2 + 1.6) = 58.8 wide; the SEN66 (55.2) leaves a 3.4 passage at its inlet end
    assert r["passage"] == pytest.approx(58.8 - 0.2 - 55.2)
    assert r["port_gap_section"] == pytest.approx(3.0 * 26.9) and r["port_gap_section"] >= 77.3


def test_mini_task4_ports_forward_cannot_take_the_outlet_back():
    """R25: with the ports forward the outlet (330.1) would have to pass the module to the rear: beside
    it (the 3.4 passage) or over it (the 0.3 gap under the zone wall)."""
    f = L.mini_recheck()["ports_forward"]
    assert f["beside"] == pytest.approx(3.4 * 26.9) and f["over"] == pytest.approx(0.3 * 55.2)
    assert max(f["beside"], f["over"]) < 330.1


def test_mini_task4_tongue_has_no_place_at_66_x_50():
    """The tongue (22 x 13, its Qwiic plug 4.5 out of its rear edge's mating face at 12.36) lying flat in
    front of the SEN66 needs 17.56 from the lip; the most any place of the SEN66 leaves is 12.77, with H1
    ignored. On edge in the intake passage it blocks 4.6 x 22 of a 3.4 x 26.9 section."""
    r = L.mini_recheck()
    tg = interface()["mechanical"]["tongue"]
    assert r["tongue_flat_need"] == pytest.approx(0.5 + tg["qwiic"]["mating_face_y"] + 4.5 + 0.2)
    # place b by hand: H1 at the board's front edge 12.01 + 30 - 2.6; the plate centred on it
    h1_y = 12.01 + 30 - 2.6
    assert r["places"]["b: H1 boss over the plate"]["front_room"] == pytest.approx(h1_y - 0.8 - 3.0 - 21.3 - 0.5 - 2.0, abs=0.01)
    assert all(pl["tongue_flat_short"] > 4.5 for pl in r["places"].values())
    for end in ("right", "left"):
        e = L.mini_recheck(inlet_end=end)["edge"]
        assert e["passage_free"] == pytest.approx(3.4 * 26.9 - 4.6 * 22) and e["passage_free"] < e["need"]
    assert L.mini_recheck()["edge"]["to_u3"] < 20                    # and at the right end it would sit under U3


def test_mini_task4_left_edge_plugs_have_no_room_at_66():
    """J2 (the SEN66's cable) and J4 come out of the board's left edge; with the board against the right
    wall (clr_remove 0.2) J2's mating face is 66 / 2 - 1.8 - 0.2 - 60 + 0.35 from the centre, 2.35 from
    the shell's side wall less clr_remove. J3 (front edge) faces the slope at 1.57."""
    m = interface()["mechanical"]["main"]
    p = L.mini_recheck()["plugs"]
    x0 = 66 / 2 - 1.8 - 0.2 - 60
    assert p["j_sen66"] == pytest.approx(x0 + m["j_sen66"]["mating_face_x"] - (-(66 / 2 - 1.8) + 0.2))
    assert max(p.values()) < 3.0 < L.PLUG_OUT
    assert L.mini_recheck(board_right=False)["plugs"]["j_sen66"] == pytest.approx(p["j_sen66"] - 1.0)
    # not a margin question: even a 3.0 plug-and-bend envelope needs a case wider than 66
    assert L.mini_recheck(plug_out=3.0)["envelopes"]["W_for_plugs"] > 66.5


def test_mini_task4_envelopes_and_the_way_out():
    env = L.mini_recheck()["envelopes"]
    assert env["D_for_tongue_flat"] == pytest.approx(50 + 5.75, abs=0.02)
    assert env["W_for_plugs"] == pytest.approx(2 * 1.8 + 2 * 0.2 + 60 + 5.0 - 0.35)
    assert env["W_for_tongue_on_edge"] == pytest.approx(2 * 3.6 + 0.4 + 55.2 + (77.25 + 4.6 * 22) / 26.9)
    # 69.5 x 50 x 42, the SEN66's inlet end left, H1 in the plenum, the tongue on edge in the passage
    r = L.mini_recheck(L.MINI_WAY_OUT, inlet_end="left")
    a = r["places"]["a: H1 in the plenum"]
    assert a["slant_ok"] and a["plenum_ok"] and a["front_room"] >= r["sen_front_need"]
    e = r["edge"]
    assert e["passage_free"] >= e["need"] and min(e["to_u3"], e["to_u2"]) >= 20 and e["h1_section"] >= e["h1_need"]
    assert e["h1_meets_inlets"]                                        # so H1 must stand in the plenum (place a)
    assert min(r["plugs"]["j_sen66"], r["plugs"]["j_qwiic_aux"]) >= L.PLUG_OUT and r["plugs"]["j_qwiic_tongue"] < 3.0
    assert L.OUTLET_FLOOR <= r["grille"]["open"] < L.OUTLET_MIN        # R18 shortfall: owner item
    assert a["antenna_to_sen66"] < 15                                   # R12: owner item
