"""The airQ layout study (enclosure/src/airq_layout.py, enclosure/README.md "airQ layout").

Fast tests (pure Python, CI included): the section arithmetic behind the study's claims, so a
change to interface.yaml, a reference part or a margin that changes the conclusion fails here.
"""
import math
from dataclasses import replace

import pytest

import airq_layout as L
from sclib import interface

DEFAULT = L.Inputs()
BEST = L.Inputs(**L.BEST_CASE)


def test_face_coordinates_round_trip():
    i = DEFAULT
    for s, t in ((0, 0), (11.547, 0), (30, 1.8), (55.4, 3)):
        y, z = L.yz_of(i, s, t)
        assert L.s_of(i, y, z) == pytest.approx(s) and L.t_of(i, y, z) == pytest.approx(t)
    # the face's top edge: 48 / cos 30 up the face, at y = 48 tan 30
    assert L.yz_of(i, 48 / math.cos(math.radians(30)), 0) == pytest.approx((48 * math.tan(math.radians(30)), 48))


def test_inputs_are_read_from_interface_yaml_and_the_references():
    m = interface()["mechanical"]["main"]
    assert m["outline"] == [60.0, 30.0] and m["thickness"] == 1.6       # airq_layout.offset's frame
    pts = {(Y, Z) for Y, Z, _ in L.board_points()}
    assert (m["antenna"]["module_body"][0][1], 0.0) in pts                  # antenna strip end, -5.99
    assert (m["button"]["actuator_tip_y"], m["button"]["actuator_center_z"]) in pts
    assert (m["j_sen66"]["body"][0][1], m["max_part_height"]) in pts          # J2, the tallest part
    r = L._refs()
    assert (r["sen_w"], r["sen_h"], r["panel_w"], r["panel_t"]) == (25.6, 21.3, 36.7, 1.2)


@pytest.mark.parametrize("inputs", [DEFAULT, BEST], ids=["default", "best_case"])
def test_no_pose_fits_the_plan_envelope(inputs):
    """95 x 55 x 48 +- 1: no tilt of the main board fits with the SEN66 and the panel."""
    for a in L.ALPHAS:
        assert L.pose(replace(inputs, D=56.0), a) is None, a


@pytest.mark.parametrize("inputs", [DEFAULT, BEST], ids=["default", "best_case"])
def test_horizontal_board_needs_about_8_mm_more_depth(inputs):
    assert L.horizontal_overflow(inputs) > 7.5           # the antenna end through the rear wall at D 55
    d = L.min_depth(inputs, 0)
    assert 62.5 < d < 63.5
    p = L.pose(replace(inputs, D=d + 0.01), 0)
    assert p["zone_order"] and p["usb_rear"] and p["dot_s"] is not None


@pytest.mark.parametrize("inputs", [DEFAULT, BEST], ids=["default", "best_case"])
def test_poses_within_a_few_mm_break_the_rules(inputs):
    """Every tilt that fits within D 59 (55 + 4) puts the board below the SEN66's top (the zone
    rule), the USB-C plug through the top face, the button's push axis along the face (no dot can
    press it) and the antenna strip within 4 mm of the panel."""
    small = [a for a in L.ALPHAS if (d := L.min_depth(inputs, a)) is not None and d <= 59.0]
    assert small and min(small) >= 55
    for a in small:
        p = L.pose(replace(inputs, D=59.0), a)
        assert not p["zone_order"] and not p["usb_rear"] and p["dot_s"] is None
        assert p["antenna_behind_panel"] < 4.0


@pytest.mark.parametrize("inputs", [DEFAULT, BEST], ids=["default", "best_case"])
def test_rules_kept_need_at_least_60_5_mm(inputs):
    """The smallest depth at which a pose keeps the zone order and takes the USB-C through the
    rear wall."""
    ok = []
    for a in L.ALPHAS:
        d = L.min_depth(inputs, a)
        if d is None:
            continue
        p = L.pose(replace(inputs, D=d + 0.01), a)
        if p["zone_order"] and p["usb_rear"]:
            ok.append(d)
    assert min(ok) > 60.5


def test_face_budget():
    """The plan's face (two slot rows from the 10 mm line, the 1.2 mm LED slot, the panel pocket)
    overflows a 48 mm face; the LED line inside the top slot row fits but leaves the intake grille
    under 2x the inlets' 77.3 mm2; a 50 mm face holds it all."""
    b = L.face_budget(DEFAULT)
    assert b["lip"] == pytest.approx(10 / math.cos(math.radians(30)))
    assert b["spare"] < -1.5
    b = L.face_budget(DEFAULT, led_in_slot_row=True)
    assert b["spare"] > 0 and b["open_area"] < 154.5
    b = L.face_budget(L.Inputs(H=50.0))
    assert b["spare"] > 0.5 and b["open_area"] >= 154.5


def test_recommended_layout():
    """95 x 63.5 x 50 with the board horizontal: every rule the section answers is kept."""
    i = L.Inputs(D=63.5, H=50.0)
    p = L.pose(i, 0)
    assert p is not None and p["zone_order"] and p["usb_rear"]
    assert p["antenna_behind_panel"] > 15
    assert 0.6 < p["dot_s"] / (i.H / i.c) < 0.8                       # upper part of the face
    x = L.x_layout(i)
    assert x["sen66_to_antenna_x"] >= 15                                 # R12 in x alone
    assert x["dot_left_margin"] >= 0
    assert x["panel"][0] - L._refs()["block_out"] >= -(i.W / 2 - i.wall)  # hatched block inside
