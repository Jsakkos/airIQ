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
