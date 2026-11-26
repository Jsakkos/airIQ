"""The airQ enclosure (Plan 3 Task 3a, R22): enclosure/src/airq.py and its check design.

Fast tests (CI included): the generator's names and parameters, R22's envelope, and the layout
arithmetic. That arithmetic covers the board pose (it must satisfy the layout study's
constraints), the distances the placements answer, and the 10 mm rule and area for the grille
3a cuts. SolidCraft tests (skipped without solidcraft-cli) cover the build and its bounding box,
the interference check with every reference placed, and the rebuild over wall 1.6 / 2.4 and
clr_* +-0.1.
"""
import json
import math
import subprocess

import pytest

import airq
import airq_check
import encbuild
import layout_study as L
from sclib import ENCLOSURE

S = airq.build()
V = S.v
BODIES = ["shell", "base_plate", "zone_wall", "sen66_foam", "sen66_cradle", "sen66_end_stop",
          "gasket_out", "gasket_in", "tongue_mount", "hcho_pocket", "outlet_duct", "baffle"]
# positions Task 3b needs (task-3-scope), fixed here as parameters
FACE = ["panel_x0", "panel_s0", "bezel", "window_xc", "led_f0", "led_h_slot", "led_len", "led_z", "guide_t",
        "adapter_x", "adapter_s", "adapter_t", "ffc_len", "j7_x0", "j7_x1", "sw_x", "sw_z", "dot_f", "dot_d",
        "lsw_x", "lsw_z", "lsw_d", "slot_row1_z", "slot_row2_z", "usb_x", "usb_z", "usb_well", "usb_chamfer"]


def test_bodies_and_plan_parameters():
    assert S.bodies == BODIES
    # the plan's names (Task 4 reuses them); the plan's `floor` is floor_t (SolidCraft reserves floor)
    for name in ("W", "D", "H", "tilt_deg", "wall", "floor_t", "grille_min_z", "slot_w",
                 "clr_align", "clr_remove", "clr_snap", "lip"):
        assert name in S.params, name
    for name in FACE:
        assert name in S.params, name


def test_r22_envelope():
    assert (V("W"), V("D"), V("H"), S.params["tilt_deg"].value, V("lip")) == (95.0, 55.0, 51.0, 30.0, 15.0)
    m = airq.MODEL
    assert L.min_depth(m, 0) <= V("D")                     # the lip layout fits 55 deep
    assert L.min_face_height(m) <= V("H") - 0.8            # the study's face plus the ledge's 1 mm


def test_board_pose_satisfies_the_layout_study():
    """The model's board (front-bottom corner at board_y0, board_z0) is a feasible pose of the
    study: every half-plane holds, and the LED/guide corner binds."""
    fy, fz = V("board_y0"), V("board_z0")
    for a, b, c, name in L.constraints(airq.MODEL, 0):
        assert a * fy + b * fz <= c + 1e-6, name
    front = next(c for a, b, c, n in L.constraints(airq.MODEL, 0) if n.startswith("front slope"))
    assert -V("cos_t") * fy + V("sin_t") * fz == pytest.approx(front, abs=1e-6)


def test_distances_answered_by_the_layout():
    d = airq_check.distances(S)
    assert d["antenna_to_sen66"] >= 15 and d["antenna_to_usb_plug"] >= 15          # R12
    assert d["antenna_to_bosses_and_screws"] >= 15 and d["antenna_to_standoff_screws"] >= 15
    assert d["tongue_to_u3"] >= 20 and d["tongue_to_u2"] >= 20                     # plan
    assert d["h1_to_usb_c_centre"] <= 8.0                                            # support boss within 8 mm
    assert 0 < d["antenna_end_to_rear_wall"] < 1.0
    assert d["hcho_grille_open_mm2"] >= 2 * 7.2 * 3.8                               # 2x the SFA40 opening
    assert d["hcho_grille_lower_edge_z"] >= V("grille_min_z")                       # 10 mm rule


def test_shell_lowers_onto_the_base():
    """I1, R24: the shell goes on from above along -z, after the base, zone wall, SEN66 and board
    (assembly order, plan Task 5): its floor bosses pass the zone wall's notches, clear of the
    board's footprint, and the rear boss stays above and left of the board."""
    assert airq_check.insertion_probe(S) == []


def test_screw_heads_leave_a_floor():
    assert V("floor_t") - V("head_depth") >= 1.6                                   # M5: >= 1.6 under the head


def test_face_positions_follow_their_parts():
    assert V("dot_f") == pytest.approx(V("lip") + (V("sw_z") - V("lip")) / V("cos_t"))   # on SW1's push axis
    assert V("sw_x") - V("dot_d") / 2 > V("panel_x0") + V("panel_l") + V("clr_remove") + 1.2   # right of the pocket
    assert V("slot_row1_z") >= V("grille_min_z")
    assert V("slot_row2_z") + V("slot_w") <= V("ledge_z0")                           # slots under the ledge
    led_inner_z = V("lip") + (V("led_f0") - V("lip")) * V("cos_t") - V("wall") * V("sin_t")
    assert led_inner_z >= V("ledge_z1")                                             # LED slot above the ledge
    s_top = V("panel_s0") + V("panel_w")
    assert V("lip") + s_top * V("cos_t") - (V("bezel") + V("panel_t")) * V("sin_t") <= V("H") - V("wall")
    assert V("adapter_t") <= V("zw_tf")                                             # adapter in front of the zone wall
    assert V("tongue_z0") + V("tongue_t") + 3.0 <= V("ledge_z0")                    # tongue under the ledge
    assert V("lsw_z") - V("lsw_d") / 2 >= V("grille_min_z")                         # window: 10 mm rule


# --- SolidCraft --------------------------------------------------------------------------

def test_build_and_bounding_box(cli):
    r = encbuild.build("airq", cli, commit=False)
    box = encbuild.union(r["bodies"].values())
    assert box["min"] == pytest.approx([-47.5, 0.0, 0.0], abs=0.01)
    assert box["max"] == pytest.approx([47.5, 55.0, 51.0], abs=0.01)
    assert not r["warnings"]


def test_no_interference_with_the_references(cli):
    r = airq_check.run(cli)
    inter = r["interference"]
    assert inter["count"] == 0, [(p["a"], p["b"], p["volume_mm3"]) for p in inter["interferences"]]
    assert not inter["unchecked"]
    assert inter["checked"] > 300                                   # ref_main's 308 bodies included


def test_rebuilds_over_wall_and_clearances(cli, tmp_path):
    """check_parameters: wall 1.6 and 2.4, every clr_* +-0.1, each back to its default."""
    states = [{"wall": "1.6 mm"}, {"wall": "2.4 mm"}, {"wall": "1.8 mm"}]
    for n in ("clr_align", "clr_remove", "clr_snap"):
        d = V(n)
        states += [{n: f"{d - 0.1:.2f} mm"}, {n: f"{d + 0.1:.2f} mm"}, {n: f"{d:.2f} mm"}]
    steps = []
    for st in states:
        steps += [{"command": "parameters.change", "params": {"changes": st}},
                  {"command": "document.inspect", "params": {"measure": True, "sketches": False, "timeline": "summary"}}]
    script = tmp_path / "walk.json"
    script.write_text(json.dumps({"commands": steps}), encoding="utf-8")
    out = tmp_path / "walk.out.json"
    proc = subprocess.run([cli, "run", str(script), "--in", str(ENCLOSURE / airq.OUTPUT), "--results", "--quiet",
                           "--json-out", str(out)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    vols = []
    for st, ins in zip(states, res[1::2]):
        bad = [f for f in ins["timeline"] if f.get("error") or f.get("warning")]
        assert not bad, (st, bad)
        assert len(ins["bodies"]) == len(BODIES), st
        vols.append(sum(b["volume_mm3"] for b in ins["bodies"]))
    assert vols[1] > vols[2] > vols[0]                              # thicker walls, more material
    assert all(math.isclose(v, vols[2], rel_tol=1e-9) for v in vols[2::3])   # each back to the default
