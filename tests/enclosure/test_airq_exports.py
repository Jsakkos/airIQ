"""The airQ's printable exports (Plan 3 Task 5): one 3MF and one STEP per printed body, each in its
print orientation on the bed (z = 0).

Fast tests read the committed 3MF as plain XML. SolidCraft tests (skipped where solidcraft-cli is
missing, as in CI) reopen every file and compare it with the design's body.
"""
import math
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


def mesh_areas(path, tol=0.05, steep=-0.72):
    """(down-facing flat area on the bed, down-facing area above the bed steeper than 45 deg), mm2, from
    the 3MF's triangles: a flat face counts as on the bed when it lies within `tol` of the lowest z."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("3D/3dmodel.model"))
    ns = {"m": root.tag[root.tag.index("{") + 1:root.tag.index("}")]}
    v = [(float(e.get("x")), float(e.get("y")), float(e.get("z"))) for e in root.findall(".//m:vertex", ns)]
    zmin = min(p[2] for p in v)
    bed = over = 0.0
    for t in root.findall(".//m:triangle", ns):
        a, b, c = (v[int(t.get(k))] for k in ("v1", "v2", "v3"))
        u = [b[i] - a[i] for i in range(3)]
        w = [c[i] - a[i] for i in range(3)]
        n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
        length = math.sqrt(sum(x * x for x in n))
        if not length:
            continue
        nz = n[2] / length
        if nz < -0.999 and max(a[2], b[2], c[2]) - zmin < tol:
            bed += length / 2
        elif nz < steep:
            over += length / 2
    return zmin, bed, over


# Per part: the least flat area (mm2) that must rest on the bed, and the most down-facing area above
# it steeper than 45 deg (what the slicer must bridge or support). Measured on the committed meshes;
# the second number carries the documented exceptions (README "Print and assembly guide", section 2).
BED_CONTACT = {
    "shell": (1500, 400),            # one support (the adapter arm, 62); chamfer, top-wall strip, wall strips accepted
    "orange_dot": (10, 1),
    "base_plate": (4500, 700),       # bridges: slots, grilles, the USB-C ceiling (12.9 mm)
    "zone_wall": (80, 25),           # one small support at the boss notch's ledge
    "hcho_lid": (600, 300),          # the tongue pocket's 13.3 mm bridge
    "light_guide": (9, 75),          # on its +x end (R54): 67.5 mm2 over the bed, all on the two feet's +x end faces
    "gasket_out": (90, 1),
    "gasket_in": (6, 1),             # 7.1 mm2 of contact on a 27.9 tall post: brim
    "grommet_zone_a": (28, 40),
    "grommet_zone_b": (28, 48),
    "grommet_j4_a": (7, 8),
    "grommet_j4_b": (7, 8),
    "grommet_tongue_a": (3, 8),      # 3.3 mm2: brim
    "grommet_tongue_b": (3, 8),
}


def down_faces(path, tol=0.05, steep=-0.72):
    """{(nx, ny, nz, z): area mm2} of the down-facing faces above the bed steeper than 45 deg, grouped by
    plane (the normal rounded to 0.05, the lowest z of the face rounded to 0.1)."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("3D/3dmodel.model"))
    ns = {"m": root.tag[root.tag.index("{") + 1:root.tag.index("}")]}
    v = [(float(e.get("x")), float(e.get("y")), float(e.get("z"))) for e in root.findall(".//m:vertex", ns)]
    zmin = min(p[2] for p in v)
    groups = {}
    for t in root.findall(".//m:triangle", ns):
        a, b, c = (v[int(t.get(k))] for k in ("v1", "v2", "v3"))
        u = [b[i] - a[i] for i in range(3)]
        w = [c[i] - a[i] for i in range(3)]
        n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
        length = math.sqrt(sum(x * x for x in n))
        if not length or n[2] / length >= steep:
            continue
        if max(a[2], b[2], c[2]) - zmin < tol:
            continue                               # on the bed
        key = tuple(round(round(x / length / 0.05) * 0.05, 2) + 0.0 for x in n) + (round(min(a[2], b[2], c[2]), 1),)
        groups[key] = groups.get(key, 0.0) + length / 2
    return groups


# R54: the guide stands on its +x end face; its only down-facing faces over the bed are the two feet's +x
# end faces (33.7 mm2 each, one TIR face each, about 35-38 % of the delivered rays). Normals and z are
# the world's after the print turn; z is the face's lowest point.
GUIDE_SUPPORTED = {
    "D1 foot +x end face": ((0.0, 0.0, -1.0, 16.9), 33.7),
    "D2 foot +x end face": ((0.0, 0.0, -1.0, 11.8), 33.7),
}


def test_light_guide_hangs_only_the_named_faces():
    got = down_faces(EXPORT / "airq-light_guide.3mf")
    named = dict(GUIDE_SUPPORTED.values())
    assert len(got) == len(named), f"light_guide hangs faces {sorted(got)}"
    for key, area in got.items():
        match = [k for k in named if all(abs(x - y) < 0.1 for x, y in zip(key[:3], k[:3])) and abs(key[3] - k[3]) < 0.15]
        assert match, f"light_guide hangs {area:.1f} mm2 over the bed on an unnamed face {key}"
        assert area <= named[match[0]] * 1.1
    assert sum(got.values()) <= 75


def test_every_printed_part_has_a_bed_contact_budget():
    assert set(BED_CONTACT) == set(PRINTED)


@pytest.mark.parametrize("part", PRINTED)
def test_committed_files_are_small_and_rest_on_the_bed(part):
    for ext in ("3mf", "step"):
        f = EXPORT / f"airq-{part}.{ext}"
        assert f.exists(), f
        assert f.stat().st_size <= LIMIT, f"{f.name} over the R8 limit"
    n, lo, _ = mesh_box(EXPORT / f"airq-{part}.3mf")
    assert n == 1
    zmin, bed, over = mesh_areas(EXPORT / f"airq-{part}.3mf")
    assert abs(zmin) < TOL
    least, most = BED_CONTACT[part]
    assert bed >= least, f"{part} rests on only {bed:.1f} mm2 of flat bed contact (needs {least})"
    assert over <= most, f"{part} hangs {over:.1f} mm2 of steep overhang over the bed (budget {most})"


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


def test_file_prefix_comes_from_the_design():
    import airq_mini
    assert encbuild.part_of(airq, "export/airq-shell.3mf") == "shell"
    assert encbuild.part_of(airq_mini, "export/airq-mini-shell.3mf") == "shell"
