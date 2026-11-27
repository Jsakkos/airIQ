"""The airQ mini check design (Tasks 4a, 4b): enclosure/src/airq_mini_check.py on enclosure/airq-mini.sc.

Task 4b adds fast analytic tests of the band's light (the 3-D delivery trace with every face bare, the
no-straight-path check between the guides, the dark gap, R13 against U4, the opaque paths to the light
sensor, its window and the crease) and SolidCraft tests of the face (band slots, labels, flexure) and the
openings (open areas, the 10 mm rule, the USB-C fit, the grilles' distance).

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
    for c in (K.keepouts(S) + K.air_probes(S) + K.clear_probes(S) + K.passage_slabs(S) + K.plug_probes(S) + K.low_probes(S)
              + [c for c, *_ in K.opening_probes(S)]):
        q = c["params"]
        for key in ("corner", "base"):
            for e in q.get(key, []):
                assert isinstance(e, str), (q["name"], e)
    lsw = {f"air_lsw_{k}" for k in range(K.LSW_STEPS)}       # the window's line: free boxes, not a section
    assert set(K.AIR) | lsw == {c["params"]["body_name"] for c in K.air_probes(S)}


def test_squeezes_are_the_designs():
    for n in K.SQUEEZES:
        assert n in S.params, n


def test_passage_envelope_arithmetic_is_recorded():
    """With the tongue as its 4.6 x 22 envelope, its pin's collar and the SEN66 cable, the passage
    keeps less than 77.3 on paper: the geometry run measures it with the tongue's real board."""
    d = K.distances(S)
    assert d["passage_envelope_free"] < 77.3


# --- Task 4b: the band's light (analytic and arithmetic, fast) ---------------------------------

def test_guides_deliver_light_with_every_face_bare():
    """R48 on the mini: a 3-D trace of each guide as built, every face bare (TIR at 39.6 deg, Snell and
    Fresnel at the entry and the exit): every LED delivers >= 3 % of its emission to its half's exit, part
    of it straight (no reflection: the LEDs stand level with the band). Each half's lit span is reported
    (the dim ends are an owner print item)."""
    d = K.guide_delivery(S)
    assert set(d["leds"]) == {"D1", "D2", "D3", "D4"}
    for name, led in d["leds"].items():
        assert led["fraction"] >= 0.03, (name, led)
        assert led["straight"] > 0, name
    for half, h in d["halves"].items():
        lo, hi = h["lit_x"]
        vis = h["visible"]
        assert vis[0] < lo < hi < vis[1], (half, h)
        assert sum(h["bins"]) > 0


def test_no_straight_path_between_the_guides():
    """Plan Task 4 Step 3: no straight line of air or light joins the guides. Sampled: every exposed
    face of each guide against every exposed face of the other (326k lines), each through >= the divider's
    6.8 of opaque material. Exact: the convex hull of the guides' profile lies inside the opaque profiles
    over the whole divider gap (rib, face wall, guide_stop)."""
    g = K.guide_to_guide(S)
    assert g["air"] == 0 and g["under_1_2"] == 0
    assert g["least"] >= g["slab"] - 1e-6
    assert g["hull_points"] > 10000 and g["hull_uncovered"] == 0
    assert "shell rib divider" in g["covers"]


def test_visible_gap_stays_dark():
    """The gap between the halves: from every face of either guide to its outer face, >= 1.2 of opaque
    over all but 1.2 at each slot's end (4.4 of the 6.8 gap; plan >= 4)."""
    d = K.gap_dark(S)
    assert d["least"] >= 1.2 - 1e-6 and d["dark_w"] >= 4.0


def test_ms5611_sees_no_led_or_guide():
    """R13 / R50: 0 unblocked lines from every exposed face of both guides (bars, feet, sides, ends, entry
    faces, exits) to U4's port; without guide_stop thousands would be. The LED faces emit away from U4."""
    r = K.ms5611_sight(S)
    assert r["samples"] > 20000 and r["unblocked"] == 0, r["first"]
    assert any(k.endswith(" end") for k in r["by_face"]) and any("entry" in k for k in r["by_face"])
    assert r["led_faces_facing_u4"] == 0
    assert K.ms5611_sight(S, dx=1.0, n_edge=10, n_side=10, stop=False)["unblocked"] > 0


def test_light_stays_off_the_sensor_its_window_and_the_crease():
    """Review focus 3: >= 1.2 of opaque material (the lip, the zone wall, zone_seal, the shell's wall and
    ribs, guide_stop; the crease's parting line counted as air) on every straight line from the guides and
    the LED faces to the VEML7700, the light-sensor window and the crease's front."""
    lp = K.light_paths(S)
    for name, (ln, _) in lp.items():
        assert ln >= 1.2, (name, lp[name])


def test_zone_wall_is_held_down():
    """Review I1 (analytic): the board's one clamp (H1) and the shell's four hold-down pads hold the zone wall
    against the top seal's push: every hold pushes down (the push lies 8 mm inside their polygon); as a 20 mm
    strip between the pads and H1 (the plate and the board ignored: a bound) it lifts <= 0.1 at the seal with
    the soft foam specified, the plenum plate's lap <= 0.05, and the seal keeps >= 30 % compression (>= 20 %
    with firm foam); the grommet's bottom is at contact, so nothing lifts it beside the drawer."""
    r = K.seal_forces(S)
    assert all(x > 0 for x in r["share"].values()) and r["inside_mm"] > 5
    soft, firm = r["lift"][30.0], r["lift"][100.0]
    assert soft["at_seal"] <= 0.1 and soft["at_plate_lap"] <= 0.05 and soft["seal_compression_left"] >= 0.3
    assert firm["seal_compression_left"] >= 0.2 and firm["at_plate_lap"] < 0.1
    assert r["drawer_floor_n"] == 0.0 and V("drawer_floor_squeeze") == 0


def test_opaque_walls():
    w = K.walls(S)
    assert w["divider"] >= V("divider_t") >= 1.2 and w["end_ribs"] >= 1.2 and w["guide_stop"] >= 1.2
    assert w["pm_to_flexure"] >= 1.2 and w["visible_gap"] >= 4.0


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
            "airq-tongue_PCB", "sen66_body", "gco2_up_32", "gpm_up_32", "gstop_up_32", "air_slots_front", "air_lsw_0"} <= names
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
    assert K.nudge_faults(check["nudge"], S) == []
    met = {p["a"] if p["a"] in A.NUDGES else p["b"] for p in check["nudge"]["interferences"]}
    assert met == set(K.NUDGE_DATUMS)
    hit = {(p["a"], p["b"]) if p["a"] in A.NUDGES else (p["b"], p["a"]) for p in check["nudge"]["interferences"]}
    assert ("shell_nz_m", "zone_wall") in hit                          # review I1: the pads bear on the zone wall's top


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


def test_face_probes(check):
    """The band slots open over their length and height and exactly their size (a 0.05 ring round each
    meets the wall's ring); each label debossed exactly label_depth (the solid 0.05 under it is all shell)
    with the letters' area; the flexure's beam is its flex_t skin, the pad rod ends flex_gap in front of
    SW1's actuator."""
    got = {(p["b"] if p["a"] in K.SHELL_PARTS else p["a"]): p["volume_mm3"] for p in check["face"]["interferences"]}
    for h in ("co2", "pm"):
        assert f"fp_slot_{h}" not in got
        ring = (V(f"band_{h}_x1 - band_{h}_x0") + 0.1) * (V("band_h") + 0.1) - V(f"band_{h}_x1 - band_{h}_x0") * V("band_h")
        assert got[f"fp_ring_{h}"] == pytest.approx(ring * V("wall - 0.1"), rel=1e-3)
    for h, x0, x1 in K.LABEL_BOXES:
        area = V(f"({x1}) - ({x0})") * V("label_f1 - label_f0 + label_sub_drop + 2")
        assert got[f"fp_label_{h}_floor"] == pytest.approx(area * 0.05, rel=1e-3)
        letters = (area * V("label_depth") - got[f"fp_label_{h}"]) / V("label_depth")
        assert letters > 15, (h, letters)
    assert got["fp_beam"] == pytest.approx(V("flex_w - 1") * 1.0 * V("flex_t"), rel=1e-3)
    assert got["fp_pad_end"] == pytest.approx(0.1, rel=1e-3) and "fp_pad_gap" not in got


def test_openings_measured_open_areas(check):
    """R18 on the geometry: intake >= 154.5 (every slot faces free air: air_slots_front is free), the
    outlet 498 (< 660.1, >= the 296 floor: owner item), the window, the exhaust; each as drawn."""
    areas = K.opening_areas(S, check["openings"])
    for name, (got, exp) in areas.items():
        assert got == pytest.approx(exp, rel=1e-3), name
    assert areas["op_intake"][0] >= 154.5
    assert 296 <= areas["op_outlet"][0] < 660.1


def test_nothing_opens_below_the_10_mm_line(check):
    """Slabs z 0 ... 10 over the lip, the rear wall, both rails and both shell side walls are all material
    (the left rail less the tongue pin's blind hole, which does not go through)."""
    got = {}
    for p in check["openings"]["interferences"]:
        a, b = (p["a"], p["b"]) if p["a"].startswith("low_") else (p["b"], p["a"])
        if a.startswith("low_"):
            got[(a, b)] = got.get((a, b), 0.0) + p["volume_mm3"]
    for c in K.low_probes(S):
        n = c["params"]["body_name"]
        full = A._volume(c, S)
        vol = got[(n, K.LOW_PARTS[n])]
        if n == "low_rail_l":
            pin = math.pi / 4 * V("tm_pin_d + 2 * clr_align") ** 2 * V("tm_hole_depth")
            assert vol == pytest.approx(full - pin, rel=1e-3)
        else:
            assert vol == pytest.approx(full, rel=1e-4), n


def test_usb_opening_fit_and_chamfer(check):
    got = {}
    for p in check["openings"]["interferences"]:
        a, b = (p["a"], p["b"]) if p["a"].startswith("usb_") else (p["b"], p["a"])
        if a.startswith("usb_"):
            got[a] = got.get(a, 0.0) + p["volume_mm3"]
    exp = A.usb_expect(S)
    assert "usb_in" not in got
    assert got["usb_out"] == pytest.approx(exp["usb_out"], rel=1e-3)
    assert got["usb_cham"] == pytest.approx(exp["usb_cham"], rel=2e-3)


def test_intake_and_outlet_apart(check):
    assert check["clearance"]["intake_to_outlet"] >= 20
