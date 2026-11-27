"""The airQ's printable exports (Plan 3 Task 5): one 3MF and one STEP per printed body, each in its
print orientation on the bed (z = 0).

Fast tests read the committed 3MF as plain XML. SolidCraft tests (skipped where solidcraft-cli is
missing, as in CI) reopen every file and compare it with the design's body.
"""
import xml.etree.ElementTree as ET
import zipfile

import pytest

import airq
import encbuild
from sclib import ENCLOSURE

EXPORT = ENCLOSURE / "export"
PRINTED = list(airq.PRINT_PARTS)
# Bodies of airq.sc that are bought (cut or stuck on), not printed
BOUGHT = ["sen66_foam", "sen66_pad", "zone_seal", "sen66_top_seal", "crease_seal", "led_mask", "gap_stop"]
LIMIT = 5 * 1024 * 1024
TOL = 0.05


def mesh_box(path):
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("3D/3dmodel.model"))
    ns = {"m": root.tag[root.tag.index("{") + 1:root.tag.index("}")]}
    objs = root.findall(".//m:object", ns)
    pts = [(float(v.get("x")), float(v.get("y")), float(v.get("z"))) for v in root.findall(".//m:vertex", ns)]
    return len(objs), [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def test_exports_are_registered_per_part():
    assert encbuild.exports_of("airq") == [f"export/airq-{p}.{e}" for p in PRINTED for e in ("3mf", "step")]
    assert not set(PRINTED) & set(BOUGHT)
    assert not any("led_mask" in e or "gap_stop" in e or "seal" in e or "foam" in e or "pad" in e
                   for e in encbuild.exports_of("airq"))


@pytest.mark.parametrize("part", PRINTED)
def test_committed_files_are_small_and_hold_one_part_on_the_bed(part):
    for ext in ("3mf", "step"):
        f = EXPORT / f"airq-{part}.{ext}"
        assert f.exists(), f
        assert f.stat().st_size <= LIMIT, f"{f.name} over the R8 limit"
    n, lo, _ = mesh_box(EXPORT / f"airq-{part}.3mf")
    assert n == 1
    assert abs(lo[2]) < TOL, f"{part} does not sit on the bed (min z {lo[2]})"


@pytest.fixture(scope="module")
def design(cli, tmp_path_factory):
    """The saved design's bodies, and the printed parts' boxes after their turns (before the bed)."""
    import json
    import subprocess
    tmp = tmp_path_factory.mktemp("airq_exports")
    out = tmp / "design.json"
    subprocess.run([cli, "eval", str(ENCLOSURE / "airq.sc"), "--quiet", "--json-out", str(out)], check=True)
    bodies = {b["name"]: b for b in json.loads(out.read_text(encoding="utf-8"))["bodies"]}
    boxes = encbuild.print_boxes("airq", ENCLOSURE / "airq.sc", cli, tmp / "boxes.json")
    return bodies, boxes, tmp


def test_every_body_is_printed_or_bought(design):
    assert set(design[0]) == set(PRINTED) | set(BOUGHT)


@pytest.mark.parametrize("part", PRINTED)
def test_reopened_exports_match_the_design_body(cli, design, part):
    bodies, boxes, tmp = design
    body = bodies[part]
    dbox = body["bbox"]
    extents = sorted(hi - lo for lo, hi in zip(dbox["min"], dbox["max"]))
    turns = airq.PRINT_PARTS[part]["turns"]
    spec = airq.PRINT_PARTS[part]
    lift = -boxes[spec.get("ref", part)]["min"][2]
    want = boxes[part]
    for ext in ("3mf", "step"):
        got = encbuild.eval_bodies(EXPORT / f"airq-{part}.{ext}", cli, tmp / f"{part}.{ext}.json")
        assert len(got) == 1, f"{part}.{ext} reopens with {len(got)} bodies"
        (bb,) = got.values()
        for i in range(3):
            shift = lift if i == 2 else 0
            assert abs(bb["min"][i] - (want["min"][i] + shift)) < TOL, (part, ext, i)
            assert abs(bb["max"][i] - (want["max"][i] + shift)) < TOL, (part, ext, i)
        if all(deg % 90 == 0 for _, deg in turns):
            # quarter turns only permute the box: the file's box is the design body's box
            got_ext = sorted(hi - lo for lo, hi in zip(bb["min"], bb["max"]))
            assert all(abs(a - b) < TOL for a, b in zip(got_ext, extents)), (part, got_ext, extents)
    assert abs(want["volume"] - body["volume_mm3"]) < 1e-6 * body["volume_mm3"]


def test_build_writes_the_committed_exports(cli):
    r = encbuild.build("airq", cli, commit=False)
    assert len(r["exports"]) == 2 * len(PRINTED)
    for e in r["exports"]:
        if e["parts"] is not None:
            assert len(e["parts"]) == 1
