"""The reference designs measured in SolidCraft (skipped where solidcraft-cli is missing, as in CI).

Plan 3 Task 1 Step 2: each bounding box matches its datasheet within +-0.1 mm. The expected
boxes below are the datasheets' numbers, written out independently of the generators; None
skips a coordinate that only the model defines (the depth of a port marker).
"""
import json
import math
import subprocess
import zipfile

import pytest

import encbuild
from sclib import ENCLOSURE, interface

TOL = 0.1
PARTS = ["sen66", "epd-2.9", "sfa40-breakout", "fpc-adapter"]

# body -> ((xmin, ymin, zmin), (xmax, ymax, zmax)), datasheet numbers (sources in enclosure/README.md)
EXPECTED = {
    "sen66": {   # SEN6x Datasheet v1.0, Figure 8 (the plan's box: 55.2 x 25.6 x 21.3)
        "sen66_body": ((0, 0, 0), (55.2, 25.6, 21.3)),
        "sen66_inlet": ((3.2, 2.8, 0), (10.2, 18.2 + 3.0, None)),        # 7x7 square, then d6 circle
        "sen66_outlet": ((42.4 - 10.25, 12.8 - 10.25, 0), (42.4 + 10.25, 12.8 + 10.25, None)),
    },
    "epd-2.9": {  # GDEY029T94 / Waveshare 2.9" V2 drawing; tail per interface.yaml panel_tail
        "epd_panel": ((0, 0, 0), (79.0, 36.7, 1.2)),
        "epd_active_area": ((79.0 - 3.00 - 66.90, 3.82, None), (79.0 - 3.00, 36.7 - 3.82, 1.2)),
        "epd_tail": ((-14.40, 10.97, None), (0, 36.7 - 10.42, None)),
        "epd_tail_stiffener": ((-14.40, 11.50, None), (-14.40 + 6.20, 36.7 - 12.70, None)),
        "epd_tail_contacts": ((-14.40, 11.75, None), (-14.40 + 3.66, 11.75 + 24 * 0.5, None)),
        "epd_tail_block": ((-4.6, 36.7 - 7.4, 0), (0, 36.7 - 2.3, None)),
    },
    "sfa40-breakout": {  # SparkFun SEN-31669 layout/drawing; SFA40 Datasheet v1.1 Figure 6
        "sfa40_board": ((0, -25.4, 0), (25.4, 0, 1.6)),
        "sfa40_sensor": ((12.7 - 5.0, -12.7 - 6.5, 1.6), (12.7 + 5.0, -12.7 + 6.5, 1.6 + 0.8 + 1.59)),
        "sfa40_opening": ((12.7 + 5.0 - 4.15 - 3.8, -12.7 - 3.6, None), (12.7 + 5.0 - 4.15, -12.7 + 3.6, 3.99)),
    },
    "fpc-adapter": {  # placeholder: about 20 x 12 mm, ZIF each end (to confirm)
        "fpc_adapter_pcb": ((-10, -6, 0), (10, 6, None)),
    },
}
OVERALL = {
    "sen66": ((0, 0, 0), (55.2, 25.6, 21.3)),
    "epd-2.9": ((-14.40, 0, 0), (79.0, 36.7, 1.2)),          # tail flat: 79.0 + 14.4 = 93.4 long
    "sfa40-breakout": ((0, -25.4, 0), (25.4, 0, None)),
    "fpc-adapter": ((-10, -6, 0), (10, 6, None)),
}


def run_json(cli, args, out):
    proc = subprocess.run([cli, *args, "--quiet", "--json-out", str(out)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(out.read_text(encoding="utf-8"))


def evaluate_design(cli, name, tmp_path):
    return run_json(cli, ["eval", str(ENCLOSURE / encbuild.module(name).OUTPUT)], tmp_path / f"{name}.json")


def union(bodies):
    return encbuild.union(b["bbox"] for b in bodies)


def assert_box(bbox, expected, what):
    for side, exp in zip(("min", "max"), expected):
        for axis, (got, want) in enumerate(zip(bbox[side], exp)):
            if want is not None:
                assert abs(got - want) <= TOL, f"{what}: {side} {'xyz'[axis]} = {got:.3f}, datasheet {want:.3f}"


@pytest.mark.parametrize("name", PARTS)
def test_reference_part_matches_its_datasheet(cli, name, tmp_path):
    d = evaluate_design(cli, name, tmp_path)
    assert not [f for f in d["timeline"] if f["error"]]
    assert all(sk["dof"] == 0 and sk["status"] == "solved" for sk in d["sketches"])
    bodies = {b["name"]: b for b in d["bodies"]}
    for body, expected in EXPECTED[name].items():
        assert_box(bodies[body]["bbox"], expected, body)
    assert_box(union(d["bodies"]), OVERALL[name], f"{name} overall")


def test_sen66_port_areas(cli, tmp_path):
    """Port bodies are prisms port_depth deep: their volume / depth is the port face area."""
    bodies = {b["name"]: b for b in evaluate_design(cli, "sen66", tmp_path)["bodies"]}
    assert bodies["sen66_inlet"]["volume_mm3"] / 0.5 == pytest.approx(7.0 * 7.0 + math.pi * 3.0 ** 2, rel=1e-4)
    assert bodies["sen66_outlet"]["volume_mm3"] / 0.5 == pytest.approx(math.pi * 10.25 ** 2, rel=1e-4)


def test_epd_tail_folds_with_its_parameter(cli, tmp_path):
    """tail_folded = 1 alone switches to the folded tail (configuration rules), and back."""
    script = tmp_path / "fold.json"
    script.write_text(json.dumps({"commands": [
        {"command": "parameters.change", "params": {"name": "tail_folded", "expression": "1"}},
        {"command": "inspect.measure", "params": {"summary": True}},
        {"command": "parameters.change", "params": {"name": "tail_folded", "expression": "0"}},
        {"command": "inspect.measure", "params": {"summary": True}}]}), encoding="utf-8")
    res = run_json(cli, ["run", str(script), "--in", str(ENCLOSURE / "reference/epd-2.9.sc"), "--results"],
                   tmp_path / "fold.out.json")
    folded = {b["name"]: b for b in res[1]["bodies"]}
    flat = {b["name"]: b for b in res[3]["bodies"]}
    assert "epd_tail" not in folded and "epd_tail_folded" in folded
    assert "epd_tail" in flat and "epd_tail_folded" not in flat
    # folded behind the panel: nothing of the tail past the hatched block, all of it under z = 0
    # except the bend's upper end at the tail's own height
    assert_box(union(res[1]["bodies"]), ((-4.6, 0, -1.55), (79.0, 36.7, 1.2)), "folded overall")
    for body in ("epd_tail_folded_stiffener", "epd_tail_folded_contacts"):
        assert folded[body]["bbox"]["max"][2] < 0
    # the flexible 8.2 mm keeps its length round the bend (r = 1.0, t = 0.1, run 0.5)
    r, t, run, w_root = 1.0, 0.1, 0.5, 15.31
    low = 8.2 - run - math.pi * (r + t / 2)
    vol = (run + low) * w_root * t + math.pi / 2 * ((r + t) ** 2 - r ** 2) * w_root + 6.2 * 12.5 * t
    assert folded["epd_tail_folded"]["volume_mm3"] == pytest.approx(vol, rel=1e-6)


def test_epd_fold_rebuilds_over_its_range(cli, tmp_path):
    """The fold parameters walked to the ends of their commented ranges, one change after
    another (solidcraft-checking: every allowed value), and back: each state rebuilds without
    errors and keeps the flexible length round the bend."""
    states = [(0.5, 0.5), (0.5, 0.2), (1.5, 0.2), (1.5, 1.5), (0.5, 1.5), (1.0, 0.5)]
    steps = [{"command": "parameters.change", "params": {"name": "tail_folded", "expression": "1"}}]
    for r, run in states:
        steps += [{"command": "parameters.change", "params": {"changes": {"fold_r": f"{r} mm", "fold_out": f"{run} mm"}}},
                  {"command": "inspect.measure", "params": {"summary": True}}]
    script = tmp_path / "walk.json"
    script.write_text(json.dumps({"commands": steps}), encoding="utf-8")
    res = run_json(cli, ["run", str(script), "--in", str(ENCLOSURE / "reference/epd-2.9.sc"), "--results"],
                   tmp_path / "walk.out.json")
    t, w_root = 0.1, 15.31
    for i, (r, run) in enumerate(states):
        change, measure = res[1 + 2 * i], res[2 + 2 * i]
        assert not change.get("errors"), change
        bodies = {b["name"]: b for b in measure["bodies"]}
        low = 8.2 - run - math.pi * (r + t / 2)
        vol = (run + low) * w_root * t + math.pi / 2 * ((r + t) ** 2 - r ** 2) * w_root + 6.2 * 12.5 * t
        assert bodies["epd_tail_folded"]["volume_mm3"] == pytest.approx(vol, rel=1e-6), (r, run)
        assert bodies["epd_tail_folded"]["bbox"]["min"][0] == pytest.approx(-(run + r + t), abs=1e-6)
        assert bodies["epd_tail_folded_stiffener"]["bbox"]["max"][2] < 0


def test_references_insert_as_components(cli, tmp_path):
    """The way Tasks 3-4 use them: component.insert_design, by configuration for the panel."""
    refs = ENCLOSURE / "reference"
    script = tmp_path / "asm.json"
    script.write_text(json.dumps({"commands": [
        {"command": "file.new", "params": {"name": "asm"}},
        {"command": "component.insert_design", "params": {"path": str(refs / "epd-2.9.sc"), "configuration": "folded"}},
        {"command": "component.insert_design", "params": {"path": str(refs / "sen66.sc")}},
        {"command": "component.insert_design", "params": {"path": str(refs / "sfa40-breakout.sc")}},
        {"command": "component.insert_design", "params": {"path": str(refs / "fpc-adapter.sc")}}]}),
        encoding="utf-8")
    res = run_json(cli, ["run", str(script), "--results"], tmp_path / "asm.out.json")
    names = {r["name"]: r["bodies"] for r in res[1:]}
    assert set(names) == {"ref_epd", "ref_sen66", "ref_sfa40", "ref_fpc_adapter"}
    assert "epd_tail_folded" in names["ref_epd"] and "epd_tail" not in names["ref_epd"]
    # an inserted copy shows the two inlet pieces as two bodies
    assert names["ref_sen66"] == ["sen66_body", "sen66_inlet", "sen66_inlet (2)", "sen66_outlet"]


@pytest.mark.parametrize("name,board", [("airq-main", "main"), ("airq-tongue", "tongue")])
def test_pcb_reference_matches_interface_yaml(cli, name, board, tmp_path):
    """The STEP frame of interface.yaml mechanical.<board>.step: board x 0..W, y -H..0,
    dielectric z 0..1.51; parts no higher than 1.6 + max_part_height."""
    m = interface()["mechanical"][board]
    w, h = m["outline"]
    d = evaluate_design(cli, name, tmp_path)
    pcb = [b for b in d["bodies"] if b["name"].endswith("_PCB")]
    assert len(pcb) == 1
    assert_box(pcb[0]["bbox"], ((0, -h, 0), (w, 0, 1.51)), f"{name} board")
    top = m["thickness"] + m["max_part_height"]
    if board == "main":
        # the button's actuator tip (front edge, -y) and the module's antenna strip (rear, +y)
        expected = ((0, -m["button"]["actuator_tip_y"], 0), (w, m["antenna"]["overhang"], top))
    else:
        expected = ((0, -h, 0), (w, 0, top))
    assert_box(union(d["bodies"]), expected, f"{name} overall")


@pytest.mark.parametrize("name", list(encbuild.DESIGNS))
def test_committed_design_rebuilds_identically(cli, name):
    """The committed .sc is what the generator builds (built into enclosure/.build/), but for
    the random identities SolidCraft gives configuration rows."""
    r = encbuild.build(name, cli, commit=False)
    with zipfile.ZipFile(r["file"]) as built, zipfile.ZipFile(ENCLOSURE / encbuild.module(name).OUTPUT) as ref:
        assert sorted(built.namelist()) == sorted(ref.namelist())
        for n in built.namelist():
            assert encbuild.entry(built, n) == encbuild.entry(ref, n), n
