"""The airQ mini check design (Task 4a): enclosure/src/airq_mini_check.py on enclosure/airq-mini.sc.

Fast tests: the check design's placements and probes follow the design's parameters. SolidCraft
tests (skipped without solidcraft-cli): interference 0 with every reference (ref_main included),
the shell's sweep and nudges, the drawer's way out, the SEN66 at its depth extremes, the R25
sections (probes, and slabs across the passage with the tongue's real board in it), the seals
touching what they seal, R12 and the tongue's distances measured, and the rebuild over wall 1.6 /
2.4 and clr_* +-0.1.
"""
import json
import math
import subprocess

import pytest

import airq_check as A
import airq_mini
import airq_mini_check as K
from sclib import ENCLOSURE

S = airq_mini.build()
V = S.v


def _det(m):
    r = [row[:3] for row in m]
    return (r[0][0] * (r[1][1] * r[2][2] - r[1][2] * r[2][1]) - r[0][1] * (r[1][0] * r[2][2] - r[1][2] * r[2][0])
            + r[0][2] * (r[1][0] * r[2][1] - r[1][1] * r[2][0]))


def test_placements_are_rigid_and_follow_the_parameters():
    pls = K.placements(S)
    assert [p["path"].name for p in pls] == ["sen66.sc", "airq-tongue.sc", "airq-main.sc"]
    for p in pls:
        assert _det(p["matrix"]) == 1
        for row in p["matrix"]:
            assert isinstance(row[3], str) and V(row[3]) == V(row[3])


def test_probes_are_parameter_expressions():
    for c in K.keepouts(S) + K.air_probes(S) + K.clear_probes(S) + K.passage_slabs(S) + K.plug_probes(S):
        q = c["params"]
        for key in ("corner", "base"):
            for e in q.get(key, []):
                assert isinstance(e, str), (q["name"], e)
    assert set(K.AIR) == {c["params"]["body_name"] for c in K.air_probes(S)}


def test_squeezes_are_the_designs():
    for n in K.SQUEEZES:
        assert n in S.params, n


def test_passage_envelope_arithmetic_is_recorded():
    """With the tongue as its 4.6 x 22 envelope, its pin's collar and the SEN66 cable, the passage
    keeps less than 77.3 on paper: the geometry run measures it with the tongue's real board."""
    d = K.distances(S)
    assert d["passage_envelope_free"] < 77.3


# --- SolidCraft --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def check(cli):
    return K.run(cli)


def test_no_interference_with_the_references(check):
    inter = check["interference"]
    assert inter["count"] == 0, [(p["a"], p["b"], p["volume_mm3"]) for p in inter["interferences"]]
    assert not inter["unchecked"]
    names = {b["name"] for b in check["measure"]["bodies"]}
    assert {"ko_sen66_plug", "ko_cable_over", "ko_j2_plug", "ko_j4_plug", "ko_tongue_plug", "shell_up_32", "sweep_boss_1",
            "airq-tongue_PCB", "sen66_body"} <= names
    assert inter["checked"] > 350                                     # ref_main's 308 bodies included


def test_air_paths_are_free_sections(check):
    sec = A.sections(check["measure"], K.AIR)
    for name, (_, need, _) in K.AIR.items():
        if need:
            assert sec[name] >= need, (name, sec[name])
    for name, (got, need) in K.branches(S, sec).items():
        assert got >= need, (name, got, need)


def test_passage_keeps_r25_with_the_real_tongue_in_it(check):
    """Slabs across the passage at the tongue, its pin, its plug, the Qwiic cable's turn and the
    left stop: the free section, measured on the tongue's STEP, its pin and the cables' keep-outs,
    is at least the inlets' 77.3 everywhere."""
    sec = K.passage_sections(S, check["passage"])
    assert set(sec) == set(K.passage_slab_ys(S))
    assert "airq-tongue_PCB" in check["passage_near"] and "tongue_mount" in check["passage_near"]
    for name, a in sec.items():
        assert a >= 77.3, (name, a)


def test_seals_touch_what_they_seal(check):
    vols = A.touch_volumes(check["touch"], K.TOUCHES)
    q = A.TOUCH_SQUEEZE
    assert vols[("gasket_out", "sen66_body")] == pytest.approx(math.pi / 4 * (V("ring_od") ** 2 - V("ring_bore") ** 2) * q, rel=0.05)
    assert vols[("zone_seal", "base_plate")] == pytest.approx(2 * V("bp_x0") * V("ledge_t") * q, rel=0.05)
    assert vols[("sen66_pad", "sen66_body")] == pytest.approx(V("pad_w") * V("pad_h") * q, rel=0.05)
    assert vols[("sen66_top_seal", "zone_wall")] == pytest.approx(V("top_seal_x1 - top_seal_x0") * V("sen_d") * q, rel=0.05)
    for pair, vol in vols.items():
        assert vol > 0, pair


def test_sen66_at_its_depth_extremes(check):
    """With the port face on the ring, a 21.8 module's front (and its plug and bend) meets only the
    pad; a 20.8 module still meets the free pad."""
    reach = A.extreme_reach(check["extremes"])
    assert set(reach) == {("ext_max_plinth", "sen66_pad"), ("ext_min_plinth", "sen66_pad")}, reach
    assert reach[("ext_max_plinth", "sen66_pad")] == pytest.approx(V("pad_t - pad_gap + sen_d_tol"), abs=0.01)
    assert reach[("ext_min_plinth", "sen66_pad")] == pytest.approx(V("pad_t - pad_gap - sen_d_tol"), abs=0.01)


def test_drawer_opens_to_the_side(check):
    assert check["plugs"]["count"] == 0
    assert check["plugs"]["checked"] == len(K.OPEN_EDGES) + 1


def test_shell_nudged_meets_the_base_only_on_its_datums(check):
    assert A.nudge_faults(check["nudge"], S) == []
    met = {p["a"] if p["a"] in A.NUDGES else p["b"] for p in check["nudge"]["interferences"]}
    assert met == set(A.NUDGE_DATUMS)


def test_distances_on_the_geometry(check):
    """R12 measured (owner item: 10.35, the study's place a); the USB plug, the inserts and the
    screws >= 15 from the antenna strip; the tongue >= 20 from U3 and U2."""
    c = check["clearance"]
    assert c["antenna_to_sen66"] == pytest.approx(K.distances(S)["antenna_to_sen66"], abs=0.05)
    assert c["antenna_to_usb_plug"] >= 15 and c["antenna_to_inserts"] >= 15 and c["antenna_to_screws"] >= 15
    assert c["tongue_to_u3"] >= 20 and c["tongue_to_u2"] >= 20


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
    proc = subprocess.run([cli, "run", str(script), "--in", str(ENCLOSURE / airq_mini.OUTPUT), "--results", "--quiet",
                           "--json-out", str(out)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    vols = []
    for st, ins in zip(states, res[1::2]):
        bad = [f for f in ins["timeline"] if f.get("error") or f.get("warning")]
        assert not bad, (st, bad)
        assert len(ins["bodies"]) == len(S.bodies), st
        vols.append(sum(b["volume_mm3"] for b in ins["bodies"]))
    assert vols[1] > vols[2] > vols[0]
    assert all(math.isclose(v, vols[2], rel_tol=1e-9) for v in vols[2::3])
