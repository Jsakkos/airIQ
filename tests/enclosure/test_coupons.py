"""The print-test coupons (Plan 3 Task 2, ruling R20).

Fast tests check the generator and the committed exports (the 3MF is plain XML, so its parts and
their bounding boxes are read without SolidCraft). SolidCraft tests (skipped where solidcraft-cli
is missing, as in CI) reopen the exports, rebuild the design across the clearance range and check
the design builds clean.
"""
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from itertools import combinations

import pytest

import coupons
import encbuild
from sclib import ENCLOSURE, evaluate, interface, names_in

S = coupons.build()
V = S.v
TOL = 0.01
THREE_MF = ENCLOSURE / "export" / "coupons.3mf"
STEP = ENCLOSURE / "export" / "coupons.step"
BODIES = ["coupon_clr_pegs", "coupon_clr_holes", "coupon_grille", "coupon_insert",
          "coupon_flexure", "coupon_lg_body", "coupon_lg_bar_lit", "coupon_lg_bar_dark"]


def feature(name):
    """The generated command of a named feature."""
    return next(c["params"] for c in S.commands if c["params"].get("name") == name)


def val(expr):
    return evaluate(expr, S.values())


# --- the values the owner's results will change ------------------------------------------------

def test_plan_defaults_and_tested_values():
    assert (V("clr_align"), V("clr_remove"), V("clr_snap"), V("slot_w"), V("wall")) == (0.15, 0.20, 0.25, 1.2, 1.8)
    tested = [V(f"clr_t{i}") for i in range(1, 6)]
    assert tested == [0.10, 0.15, 0.20, 0.25, 0.30]
    assert {V("clr_align"), V("clr_remove"), V("clr_snap")} <= set(tested)    # every default is tested
    assert (V("slot_w_narrow"), V("slot_w"), V("slot_w_wide")) == (1.0, 1.2, 1.5)
    assert (V("insert_hole_a"), V("insert_hole_b"), V("insert_hole_c")) == (3.1, 3.2, 3.3)
    assert (V("insert_depth"), V("insert_od")) == (4.0, 6.0)
    assert V("insert_depth") < V("insert_h")                                    # a floor under the hole


def test_tolerance_parameters_are_commented():
    for name in ("clr_align", "clr_remove", "clr_snap", "slot_w", "insert_hole_a", "insert_hole_b", "insert_hole_c"):
        assert S.params[name].comment.strip()
    for name in ("insert_hole_a", "insert_hole_b", "insert_hole_c"):
        assert "TO CONFIRM" in S.params[name].comment


# --- fits: a hole or slot is the peg or tab plus 2 * clr (per-side gaps, R20) ----------------------

@pytest.mark.parametrize("i", range(1, 6))
def test_hole_is_peg_plus_two_clearances(i):
    clr = V(f"clr_t{i}")
    assert val(feature(f"Round hole {i}")["diameter"]) == pytest.approx(V("peg_d") + 2 * clr)
    slot = feature(f"Tab slot {i}")
    assert val(slot["length"]) == pytest.approx(V("tab_w") + 2 * clr)
    assert val(slot["width"]) == pytest.approx(V("tab_t") + 2 * clr)
    peg, tab = feature(f"Peg {i}"), feature(f"Tab {i}")
    assert val(peg["diameter"]) == V("peg_d")
    assert (val(tab["length"]), val(tab["width"])) == (V("tab_w"), V("tab_t"))
    # the hole is centred on its peg, the slot on its tab (same x; the plates differ by lay_holes_y)
    assert val(feature(f"Round hole {i}")["base"][0]) == val(peg["base"][0])
    assert val(slot["corner"][0]) + val(slot["length"]) / 2 == pytest.approx(val(tab["corner"][0]) + V("tab_w") / 2)
    assert val(slot["corner"][1]) + val(slot["width"]) / 2 - V("lay_holes_y") == pytest.approx(V("fit_rect_y"))


def test_holes_go_through_and_fit_the_plate():
    assert val(feature("Round hole 1")["base"][2]) < 0
    assert val(feature("Round hole 1")["height"]) > V("fit_t")
    # five fits in a row, each hole clear of its neighbours by at least 2 mm
    widest = V("tab_w") + 2 * V("clr_t5")
    assert V("fit_pitch") - widest >= 2.0
    assert V("fit_round_y") + (V("peg_d") + 2 * V("clr_t5")) / 2 < V("fit_rect_y") - (V("tab_t") + 2 * V("clr_t5")) / 2


# --- grille ----------------------------------------------------------------------------------------

def test_grille_slots_and_louvres():
    lines, current = {}, None
    for c in S.commands:
        if c["command"] == "sketch.create":
            current = c["params"]["name"]
        elif c["command"] == "sketch.line":
            lines.setdefault(current, []).append(c["params"])
    louvres, straight = lines["Louvre slots sketch"], lines["Straight slots sketch"]
    assert len(louvres) == 9
    for pts in (c["points"] for c in louvres):
        (ax, ay), (bx, by), (cx, cy), (dx, dy) = ([val(e) for e in p] for p in pts)
        assert ay == by and cy == dy
        dz = ay - cy                                        # sketch y = -z
        assert dz == pytest.approx(V("wall") + 2 * V("cut_over"))
        assert dx - ax == pytest.approx(dz)                 # 45 degrees: sideways shift = depth
        assert cx - dx == pytest.approx(bx - ax)            # a parallelogram
        assert (bx - ax) / 2 ** 0.5 in [pytest.approx(w) for w in (1.0, 1.2, 1.5)]    # width square to the slats
    assert sorted({round(val(c["points"][1][0]) - val(c["points"][0][0]), 6) for c in straight}) == [1.0, 1.2, 1.5]
    assert len(straight) == 9
    assert V("wall") == 1.8 and val(feature("Grille plate")["height"]) == 1.8
    # slats between louvres stay at least 1.3 mm thick (square to the slats); straight webs at least 1.5
    assert (V("louvre_pitch") - V("slot_w_wide") * 2 ** 0.5) / 2 ** 0.5 >= 1.3
    assert V("slot_pitch") - V("slot_w_wide") >= 1.5


# --- insert boss -----------------------------------------------------------------------------------

def test_insert_bosses():
    for j, hole in enumerate(("insert_hole_a", "insert_hole_b", "insert_hole_c"), 1):
        boss, h = feature(f"Boss {j}"), feature(f"Insert hole {j}")
        assert val(boss["diameter"]) == 6.0 and val(h["diameter"]) == V(hole)
        assert val(h["base"][0]) == val(boss["base"][0]) and val(h["base"][1]) == val(boss["base"][1])
        top = val(boss["base"][2]) + val(boss["height"])
        assert top - val(h["base"][2]) == pytest.approx(4.0)          # 4.0 mm deep from the boss top
        assert V("insert_od") - V(hole) >= 2.6                        # at least 1.3 mm of wall


# --- button flexure --------------------------------------------------------------------------------

def test_flexure_follows_interface_yaml_and_stops_before_overpress():
    b = interface()["mechanical"]["main"]["button"]
    assert (V("sw_act_w"), V("sw_act_z")) == (b["actuator_width"], b["actuator_center_z"])
    assert V("sw_tip") == pytest.approx(b["actuator_tip_y"] - interface()["mechanical"]["main"]["outline"][1])
    assert (V("sw_tip"), V("sw_travel")) == (0.24, 0.20)
    # the hard stop engages when the actuator is fully pressed (rest gap + travel), not after
    assert V("flex_stop") == pytest.approx(V("flex_gap") + V("sw_travel"))
    assert V("flex_stop_y") == pytest.approx(V("sw_tip") + V("flex_gap") - V("flex_stop"))
    assert V("flex_stop_y") == pytest.approx(V("sw_tip") - V("sw_travel"))     # the pressed tip position
    stub = feature("Actuator stub A")
    assert val(stub["height"]) < V("sw_h") and val(stub["length"]) == V("sw_act_w")
    assert val(stub["corner"][2]) >= V("board_t")
    assert "Actuator stub B" not in S.features                                  # B is the free unit
    # a cantilever of this beam in PETG (E about 1.5 GPa) stays under a switch's own 1.6 N at full stroke
    e_gpa, i = 1.5, V("flex_h") * V("flex_t") ** 3 / 12
    force = 3 * e_gpa * 1000 * i * V("flex_stop") / V("flex_len") ** 3
    assert force < 1.6
    assert 1.5 * V("flex_t") * V("flex_stop") / V("flex_len") ** 2 < 0.02       # root strain below 2 %


# --- light guide ------------------------------------------------------------------------------------

def test_light_guide_pocket_divider_and_bars():
    assert (V("lg_bar_w"), V("lg_bar_h")) == (3.0, 2.0)
    assert (V("lg_led_w"), V("lg_led_d"), V("lg_led_h")) == (4.0, 1.6, 2.0)
    assert V("divider") == 1.2
    pocket, lit, dark = feature("LED pocket"), feature("Lit slot"), feature("Dark slot")
    assert val(pocket["length"]) == pytest.approx(V("lg_led_d") + 2 * V("clr_align"))
    assert val(pocket["width"]) == pytest.approx(V("lg_led_w") + 2 * V("clr_align"))
    assert val(lit["width"]) == pytest.approx(V("lg_bar_w") + 2 * V("clr_align"))
    # the lit slot is centred on the pocket, so the LED's light face meets the bar's end
    assert val(lit["corner"][1]) + val(lit["width"]) / 2 == pytest.approx(val(pocket["corner"][1]) + val(pocket["width"]) / 2)
    assert val(lit["corner"][0]) == pytest.approx(val(pocket["corner"][0]) + val(pocket["length"]))
    # 1.2 mm of opaque material between the pocket and the dark slot, and behind and beside the pocket
    assert val(dark["corner"][1]) - (val(pocket["corner"][1]) + val(pocket["width"])) == pytest.approx(1.2)
    assert val(dark["corner"][0]) == val(lit["corner"][0])
    assert val(pocket["corner"][0]) - V("lay_col2_x") == pytest.approx(1.2)
    assert val(pocket["corner"][1]) - V("lay_lg_y") == pytest.approx(1.2)
    assert V("lg_w") == pytest.approx(1.2 + 4.3 + 1.2 + 3.3 + 1.2)
    assert V("lg_h") == V("lg_floor") + V("lg_led_h")
    # the bars lie beside the body (print position), each 3 wide, 2 high: they drop into the slots
    for bar in ("Lit bar", "Dark bar"):
        f = feature(bar)
        assert (val(f["width"]), val(f["height"])) == (3.0, 2.0)
        assert val(f["width"]) < val(lit["width"]) and val(f["height"]) <= V("lg_led_h")
    assert val(feature("Lit bar")["length"]) == V("lg_bar_len") and val(lit["length"]) > V("lg_bar_len")


# --- labels, layout, printing -------------------------------------------------------------------------

def test_every_tested_value_is_labelled():
    labels = [c["params"] for c in S.commands if c["command"] == "sketch.text"]
    expr = [c["text_expression"] for c in labels if "text_expression" in c]
    assert len(labels) == 5 + 5 + 6 + 3 + 2
    for clr in range(1, 6):
        assert expr.count(f"number(clr_t{clr}, 2)") == 2                       # on the peg and the hole plate
    for w in ("slot_w_narrow", "slot_w", "slot_w_wide"):
        assert f"number({w}, 1)" in expr and f"'L' + number({w}, 1)" in expr     # straight, louvre
    for h in ("insert_hole_a", "insert_hole_b", "insert_hole_c"):
        assert f"number({h}, 1)" in expr
    # every parameter a label names exists, so the label follows the value
    for e in expr:
        assert (names_in(e) - {"number", "L"}) <= set(S.params)
    assert {c["text"] for c in labels if "text" in c} == {"A", "B"}


def rects():
    return {n: (b[0][:2], b[1][:2]) for n, b in coupons.expected_bboxes(S).items()}


def test_coupons_are_laid_out_flat_on_the_bed_and_apart():
    boxes = coupons.expected_bboxes(S)
    assert list(boxes) == BODIES
    for name, (lo, hi) in boxes.items():
        assert lo[2] == 0, f"{name} must stand on the bed (z = 0) for a support-free print"
    for (na, (alo, ahi)), (nb, (blo, bhi)) in combinations(rects().items(), 2):
        gap = max(blo[0] - ahi[0], alo[0] - bhi[0], blo[1] - ahi[1], alo[1] - bhi[1])
        assert gap >= V("bed_gap") - 1e-6, f"{na} and {nb} are {gap:.2f} mm apart"
    sheet = [max(h[i] for _, h in rects().values()) for i in (0, 1)]
    assert sheet[0] < 130 and sheet[1] < 110                                  # fits any printer's bed


def test_flexure_stands_on_the_bed_without_overhangs_and_anchors_both_beams():
    # beam and pad start at the bed (nothing under them) and no joined piece floats
    for tag in "AB":
        assert val(feature(f"Beam {tag}")["corner"][2]) == 0 and val(feature(f"Pad {tag}")["corner"][2]) == 0
    assert S.params["flex_h"].value == pytest.approx(4.9)


def test_exports_are_registered():
    assert encbuild.exports_of("coupons") == ["export/coupons.3mf", "export/coupons.step"]
    assert encbuild.exports_of("sen66") == []


# --- the committed exports ---------------------------------------------------------------------------------

def parts_of_3mf(path):
    """{object name: (min, max)} from the 3MF's meshes."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("3D/3dmodel.model"))
    ns = {"m": root.tag[root.tag.index("{") + 1:root.tag.index("}")]}
    parts = {}
    for obj in root.findall(".//m:object", ns):
        pts = [(float(v.get("x")), float(v.get("y")), float(v.get("z"))) for v in obj.findall(".//m:vertex", ns)]
        parts[obj.get("name")] = (tuple(min(p[i] for p in pts) for i in range(3)),
                                  tuple(max(p[i] for p in pts) for i in range(3)))
    return parts


def test_committed_3mf_has_one_part_per_coupon_body():
    parts = parts_of_3mf(THREE_MF)
    assert list(parts) == BODIES
    for name, (lo, hi) in coupons.expected_bboxes(S).items():
        for got, want in zip(parts[name][0] + parts[name][1], lo + hi):
            assert got == pytest.approx(want, abs=TOL), (name, parts[name], (lo, hi))


def test_committed_step_holds_every_body():
    text = STEP.read_text(encoding="utf-8", errors="replace")
    assert text.startswith("ISO-10303-21;")
    for name in BODIES:
        assert f"'{name}'" in text, name


def test_committed_design_has_the_documented_bodies():
    with zipfile.ZipFile(ENCLOSURE / "coupons.sc") as z:
        d = json.loads(z.read("document.json"))
    assert [p["name"] for p in d["params"]][:4] == ["clr_align", "clr_remove", "clr_snap", "clr_t1"]
    assert not re.search(r"Sketch\d+", json.dumps([f["name"] for f in d["features"]]))


# --- SolidCraft ------------------------------------------------------------------------------------------

def run_json(cli, args, out):
    import subprocess
    proc = subprocess.run([cli, *args, "--quiet", "--json-out", str(out)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(out.read_text(encoding="utf-8"))


def test_design_builds_clean_and_measures(cli, tmp_path):
    d = run_json(cli, ["eval", str(ENCLOSURE / "coupons.sc")], tmp_path / "d.json")
    assert not [f for f in d["timeline"] if f["error"] or f.get("warning")]
    assert all(sk["dof"] == 0 and sk["status"] == "solved" for sk in d["sketches"])
    bodies = {b["name"]: b for b in d["bodies"]}
    assert list(bodies) == BODIES and all(b["closed"] for b in bodies.values())
    for name, (lo, hi) in coupons.expected_bboxes(S).items():
        for side, want in (("min", lo), ("max", hi)):
            for got, w in zip(bodies[name]["bbox"][side], want):
                assert got == pytest.approx(w, abs=TOL), (name, side)
    # volumes: plates less their cuts, written out from the parameters
    fit = V("fit_w") * V("fit_d") * V("fit_t")
    pegs = bodies["coupon_clr_pegs"]["volume_mm3"]
    assert pegs == pytest.approx(fit + 5 * (3.14159265 * 9 * 5 + 8 * 2 * 5), rel=0.01)     # less label glyphs
    holes = bodies["coupon_clr_holes"]["volume_mm3"]
    cut = sum(3.14159265 * (V("peg_d") / 2 + V(f"clr_t{i}")) ** 2 + (V("tab_w") + 2 * V(f"clr_t{i}")) * (V("tab_t") + 2 * V(f"clr_t{i}"))
              for i in range(1, 6)) * V("fit_t")
    assert holes == pytest.approx(fit - cut, rel=0.01)


def test_3mf_reopens_with_every_part(cli, tmp_path):
    """Plan Task 2 Step 1: reopen the 3MF, the expected part count imports (the MCP `open` of the
    same file lands on the same importer)."""
    parts = encbuild.eval_bodies(THREE_MF, cli, tmp_path / "p.json")
    assert list(parts) == BODIES
    for name, (lo, hi) in coupons.expected_bboxes(S).items():
        for got, want in zip(parts[name]["min"] + parts[name]["max"], lo + hi):
            assert got == pytest.approx(want, abs=TOL), name
    step = encbuild.eval_bodies(STEP, cli, tmp_path / "s.json")
    assert len(step) == len(BODIES)


def test_committed_exports_are_what_the_build_writes(cli):
    r = encbuild.build("coupons", cli, commit=False)
    assert [e["parts"] is not None for e in r["exports"]] == [True, False]
    for e, committed in zip(r["exports"], (THREE_MF, STEP)):
        assert e["file"].read_bytes() == committed.read_bytes(), committed.name


@pytest.mark.parametrize("override", [
    {"peg_d": "4 mm"}, {"peg_d": "8 mm"},
    {"clr_t1": "0.05 mm", "clr_t5": "0.40 mm"},
    {"slot_w": "1.4 mm", "wall": "1.6 mm"},
    {"sw_travel": "0.3 mm", "flex_gap": "0.15 mm", "flex_t": "0.8 mm", "flex_len": "10 mm"},
    {"clr_align": "0.1 mm", "divider": "1.6 mm"},
])
def test_design_rebuilds_across_its_parameters(cli, tmp_path, override):
    """solidcraft-checking: the design follows its parameters. Try the values: no errors, every
    body still closed and still standing on the bed."""
    script = tmp_path / "walk.json"
    steps = [{"command": "parameters.change", "params": {"changes": override}},
             {"command": "inspect.measure", "params": {"summary": True}}]
    script.write_text(json.dumps({"commands": steps}), encoding="utf-8")
    res = run_json(cli, ["run", str(script), "--in", str(ENCLOSURE / "coupons.sc"), "--results"], tmp_path / "walk.out.json")
    change, measure = res
    assert not change.get("errors"), change
    bodies = {b["name"]: b for b in measure["bodies"]}
    assert list(bodies) == BODIES and all(b["closed"] for b in bodies.values())
    for name, b in bodies.items():
        assert b["bbox"]["min"][2] == pytest.approx(0, abs=1e-6), name
