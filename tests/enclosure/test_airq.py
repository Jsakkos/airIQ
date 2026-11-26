"""The airQ enclosure (Plan 3 Task 3a, R22, R24-R29): enclosure/src/airq.py and its check design.

Fast tests (CI included): the generator's names and parameters, R22's envelope, the board pose
against the layout study, the SEN66's pose (R17, R12), the positions read from their sources
(R27), the grille and air-path arithmetic (R18, R25, R26, M4), and the shell's insertion
arithmetic. SolidCraft tests (skipped without solidcraft-cli) cover the build and its bounding
box; the check design (interference 0 with every reference, the cables' keep-outs, the air
probes and the shell's sweep; the measured air sections; the gaskets touching what they seal);
and the rebuild over wall 1.6 / 2.4 and clr_* +-0.1.
"""
import json
import math
import re
import subprocess
from dataclasses import replace

import pytest
import yaml

import airq
import airq_check
import board_sources as B
import encbuild
import layout_study as L
import ref_epd
import ref_sen66
import ref_sfa40
from sclib import ENCLOSURE, REPO, interface

S = airq.build()
V = S.v
BODIES = ["shell", "base_plate", "zone_wall", "zone_seal", "sen66_foam", "gasket_out", "gasket_in", "hcho_lid",
          "grommet_zone", "grommet_j4", "grommet_tongue"]
TPU = ["gasket_out", "gasket_in", "zone_seal", "grommet_zone", "grommet_j4", "grommet_tongue"]
# positions Task 3b needs (task-3-scope, M6), fixed here as parameters
FACE = ["panel_x0", "panel_s0", "bezel", "window_xc", "pocket_x0", "pocket_x1", "led_f0", "led_h_slot", "led_len", "led_z",
        "guide_t", "adapter_x", "adapter_s", "adapter_t", "ffc_len", "j7_x0", "j7_x1", "sw_x", "sw_z", "dot_f", "dot_d",
        "lsw_x", "lsw_z", "lsw_d", "slot_row1_z", "slot_row2_z", "row_x0", "row_x1", "lsw_gap_x0", "lsw_gap_x1",
        "out_gx0", "out_gx1", "out_gz0", "out_gz1", "out_pitch", "out_n", "exh_x0", "exh_x1", "exh_z0", "exh_z1",
        "usb_x", "usb_z", "usb_well", "usb_chamfer"]


def test_bodies_and_plan_parameters():
    assert S.bodies == BODIES
    # the plan's names (Task 4 reuses them); the plan's `floor` is floor_t (SolidCraft reserves floor)
    for name in ("W", "D", "H", "tilt_deg", "wall", "floor_t", "grille_min_z", "slot_w",
                 "clr_align", "clr_remove", "clr_snap", "lip", "gasket_squeeze"):
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


def test_sen66_pose_keeps_r17_and_the_zone_rule():
    """The module stands (long axis along x, port face vertical, R17), its port face to the rear
    (the placement maps the module's port normal, -z, to +y) and its top under the zone wall."""
    m = airq_check.placements(S)[0]["matrix"]
    rot = [row[:3] for row in m]
    assert [rot[i][2] for i in range(3)] == [0, -1, 0]        # module +z -> world -y: ports (-z) face +y
    assert [rot[i][0] for i in range(3)] == [-1, 0, 0]        # long axis along x
    det = (rot[0][0] * (rot[1][1] * rot[2][2] - rot[1][2] * rot[2][1]) - rot[0][1] * (rot[1][0] * rot[2][2] - rot[1][2] * rot[2][0])
           + rot[0][2] * (rot[1][0] * rot[2][1] - rot[1][1] * rot[2][0]))
    assert det == 1
    assert V("sen_top") + V("zone_gap") == pytest.approx(V("zw_z0"))
    assert V("board_z0") >= V("zw_z1")                         # the zone rule: electronics above
    y_slant = (V("zw_tf") + V("zone_t") + (V("sen_top") - V("lip")) * V("sin_t")) / V("cos_t")
    assert V("sen_y0") >= y_slant                              # its front top edge behind the slant
    assert V("sen_x0") >= -V("tub_x") and V("sen_x1") <= V("hx0") - V("iwall")


def test_positions_are_read_from_their_sources():
    """R27: every board and reference position the design uses equals its source."""
    main, tongue = interface()["mechanical"]["main"], interface()["mechanical"]["tongue"]
    sen, sfa, epd = ref_sen66.build().v, ref_sfa40.build().v, ref_epd.build().v
    x0, ztop = V("board_x0"), V("board_z0") + V("board_t")
    assert V("sw_x") - x0 == main["button"]["actuator_center_x"]
    assert V("sw_z") - ztop == pytest.approx(main["button"]["actuator_center_z"])
    assert V("led_z") - ztop == pytest.approx(main["leds"]["light_center_z"])
    assert (V("j7_x0") + V("j7_x1")) / 2 - x0 == pytest.approx(main["fpc"]["center_x"])
    assert V("j7_x1") - V("j7_x0") == pytest.approx(float(re.search(r"body ([\d.]+) wide", (REPO / "hardware/interface.yaml").read_text()).group(1)))
    assert V("usb_x") - x0 == pytest.approx(main["usb_c"]["center_x"])
    assert V("usb_z") - ztop == pytest.approx(main["usb_c"]["shell"][1] / 2)
    assert V("tongue_x1") - V("lsw_x") == pytest.approx(tongue["veml7700"]["window_center"][0])
    assert V("lsw_z") - V("tongue_z0") - V("tongue_t") == pytest.approx(tongue["veml7700"]["window_center"][2])
    assert V("sen_x1") - V("outlet_x") == pytest.approx(sen("outlet_x"))
    assert V("sen_top") - V("outlet_z") == pytest.approx(sen("outlet_y"))
    assert V("outlet_d") == sen("outlet_d")
    assert V("panel_x0") + V("panel_l") - V("window_xc") == pytest.approx(epd("va_far") + epd("va_w") / 2)
    assert V("sfa_w") == sfa("board_w") and V("sfa_cap") == pytest.approx(sfa("sensor_top"))
    h = main["mounting_holes"]["centers"]
    assert (V("h1_x") - x0, V("board_y0") + V("board_d") - V("h1_y")) == pytest.approx(tuple(h[0]))
    # U2 (buck): layout.yaml placement and its footprint's courtyard (interface.yaml has no U2)
    place = yaml.safe_load((REPO / "hardware/src/main/layout.yaml").read_text())["placement"]
    u2 = B.layout_part("U2")
    assert u2["center"] == tuple(place["U2"]["at"][:2])
    (bx0, by0), (bx1, by1) = u2["box"]
    assert bx0 < u2["center"][0] < bx1 and by0 < u2["center"][1] < by1
    assert B.layout_part("U4")["center"] == tuple(place["U4"]["at"][:2])


BOARD_NUMBERS = {57.0, 42.4, 12.8, 20.5, 18.35, 1.95, 28.8, 7.75, 24.6, 3.16, 8.94, 7.35, 67.5, 2.7, 25.4, 4.25, 2.95,
                 12.36, 8.55, 57.4, 22.8, 5.99}


def _code_numbers(path):
    """Numbers in a generator's code: numeric literals and the numbers inside expression strings,
    leaving out docstrings and the comments given to parameters (the third argument of p(...))."""
    import ast
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(node, (ast.Module, ast.FunctionDef)) and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant):
            skip.add(id(body[0].value))
        if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) in ("p", "param"):
            for a in node.args[2:3]:
                skip.add(id(a))
                skip.update(id(n) for n in ast.walk(a))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and id(node) not in skip:
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                out.append(float(node.value))
            elif isinstance(node.value, str):
                out += [float(x) for x in re.findall(r"(?<![\w.])\d+\.\d+(?![\w.])", node.value)]
    return out


def test_generator_retypes_no_board_numbers():
    """R27: the generators' code carries no copies of the boards' or references' numbers."""
    for f in ("airq.py", "airq_check.py", "enclosure_common.py"):
        found = BOARD_NUMBERS & set(_code_numbers(ENCLOSURE / "src" / f))
        assert not found, (f, found)


def test_distances_answered_by_the_layout():
    d = airq_check.distances(S)
    assert d["antenna_to_sen66"] >= 15 and d["antenna_to_usb_plug"] >= 15          # R12
    assert d["antenna_to_bosses_and_screws"] >= 15 and d["antenna_to_standoff_screws"] >= 15
    assert d["antenna_to_sfa40"] >= 15                                              # metal kept out of the 15 mm too
    assert d["tongue_to_u3"] >= 20 and d["tongue_to_u2"] >= 20                     # plan
    assert d["h1_to_usb_c_centre"] <= 8.0                                            # support boss within 8 mm
    assert d["h1_free_above_plenum"] <= 2.5                                         # M7: braced to 2.1 under the board
    assert 0 < d["antenna_end_to_rear_wall"] < 1.0


def test_grilles_r18_and_10_mm_rule():
    d = airq_check.distances(S)
    assert d["outlet_grille_open_mm2"] >= 660.1                                     # R18: 2 x 330.1
    assert d["intake_open_mm2"] >= 154.5                                            # R18: 2 x 77.3
    sfa = ref_sfa40.build().v
    assert d["hcho_grille_open_mm2"] >= 2 * sfa("opening_l") * sfa("opening_w")     # 2 x the SFA40's opening
    assert min(d["hcho_grille_lower_edge_z"], d["outlet_grille_lower_edge_z"], V("slot_row1_z"),
               V("lsw_z") - V("lsw_d") / 2, V("exh_z0")) >= V("grille_min_z")       # 10 mm rule
    assert V("out_gx1") <= V("tub_x") - 2.0                                          # the grille stays in the plenum
    assert V("exh_z0") > V("zw_z1") + 2.0                                            # the exhaust stays apart (R26)


def test_r26_alternatives_worked():
    """R26: the HCHO pocket's alternatives with numbers; only the chosen one keeps 660.1."""
    rows = L.hcho_alternatives(airq.MODEL)
    assert [r["meets"] for r in rows] == [False, False, False, False, True]
    assert rows[-1]["open_50"] == pytest.approx(airq_check.distances(S)["outlet_grille_open_mm2"])
    assert not rows[1]["fits"] and not rows[3]["fits"]
    # the reason the ports turned to the rear: the front layer cannot reach 330.1 (R25)
    assert L.front_layer(airq.MODEL, 20.0, under_ledge=True) < 330.1


def test_air_paths_by_their_parameters():
    """R25 from the parameters (the check design measures the same on the geometry)."""
    assert V("port_gap") * (V("zw_z0") - V("floor_t")) >= 77.3                       # inlets: the gap
    assert math.pi * V("ring_bore") ** 2 / 4 >= 330.1                                # outlet: the ring's bore
    assert V("ring_bore") > V("outlet_d")
    sfa = ref_sfa40.build().v
    assert V("sfa_w") * V("hcho_air") >= sfa("opening_l") * sfa("opening_w")         # HCHO: over the cap


def test_tongue_leaves_the_intake_rows_open():
    """M4: the tongue is set back from the lip; the slots in front of it feed a channel whose
    side exits pass at least their open area."""
    exits = 2 * V("tongue_gap") * (V("ledge_z0") - V("tongue_z0"))
    span = V("tongue_x1") - max(V("tongue_x1") - V("tongue_w"), V("lsw_gap_x1"))
    in_front = 2 * V("slot_w") * (span - V("slot_bar"))
    assert exits >= in_front
    assert V("tongue_z0") + V("tongue_t") + V("tongue_parts_h") <= V("ledge_z0")     # under the ledge


def test_shell_lowers_onto_the_base():
    """I1, R24 (arithmetic; the check design sweeps it): the shell goes on from above along -z:
    its floor bosses pass the zone wall's notches, clear of the board's footprint, and the rear
    boss stays above and left of the board."""
    assert airq_check.insertion_probe(S) == []


def test_screw_heads_leave_a_floor():
    assert V("floor_t") - V("head_depth") >= 1.6                                   # M5: >= 1.6 under the head


def test_gaskets_have_a_squeeze_and_seats():
    """I3/R9: the TPU parts are sized at contact plus gasket_squeeze; the check runs at 0."""
    assert V("gasket_squeeze") > 0 and V("seat_d") > 0
    assert "gasket_squeeze" in json.dumps(airq_check.check_script()["commands"][6])


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
    assert V("row_x0") < V("lsw_gap_x0") < V("lsw_x") < V("lsw_gap_x1") < V("row_x1")


# --- SolidCraft --------------------------------------------------------------------------

def test_build_and_bounding_box(cli):
    r = encbuild.build("airq", cli, commit=False)
    box = encbuild.union(r["bodies"].values())
    assert box["min"] == pytest.approx([-47.5, 0.0, 0.0], abs=0.01)
    assert box["max"] == pytest.approx([47.5, 55.0, 51.0], abs=0.01)
    assert not r["warnings"]


@pytest.fixture(scope="module")
def check(cli):
    return airq_check.run(cli)


def test_no_interference_with_the_references(check):
    """R9: no shared volume between the enclosure, the references (ref_main included), the
    cables' keep-outs, the air probes and the shell's sweep along -z (I1)."""
    inter = check["interference"]
    assert inter["count"] == 0, [(p["a"], p["b"], p["volume_mm3"]) for p in inter["interferences"]]
    assert not inter["unchecked"]
    names = {b["name"] for b in check["measure"]["bodies"]}
    assert {"ko_sen66_plug", "ko_strip", "ko_j2_plug", "ko_j4_plug", "ko_tongue_plug", "shell_up_32", "sweep_boss_1"} <= names
    assert inter["checked"] > 380                                    # ref_main's 308 bodies included


def test_air_paths_are_free_sections(check):
    """R25 on the geometry: each probe is free air (interference 0) and its section is at least
    the port area its path serves; the plenum's branches carry their share of the outlet grille."""
    sec = airq_check.sections(check["measure"])
    for name, (_, need, _) in airq_check.AIR.items():
        if need:
            assert sec[name] >= need, (name, sec[name])
    for name, (got, need) in airq_check.branches(S, sec).items():
        assert got >= need, (name, got, need)


def test_gaskets_touch_what_they_seal(check):
    """I3: at gasket_squeeze 0 the TPU faces touch (interference 0); at a small squeeze each
    overlaps its counterpart by its contact area times the squeeze, so there was no gap."""
    vols = airq_check.touch_volumes(check["touch"])
    q = airq_check.TOUCH_SQUEEZE
    ring = math.pi / 4 * (V("ring_od") ** 2 - V("ring_bore") ** 2) * q
    strip = V("seal_w") * V("sen_up") * q
    lip = 2 * V("bp_x0") * V("ledge_t") * q
    assert vols[("gasket_out", "sen66_body")] == pytest.approx(ring, rel=0.05)
    assert vols[("gasket_in", "sen66_body")] == pytest.approx(strip, rel=0.05)
    assert vols[("zone_seal", "base_plate")] == pytest.approx(lip, rel=0.05)


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
