"""The airQ mini's printable exports (Plan 3 Task 5b): one 3MF and one STEP per printed body, each in its
print orientation on the bed (z = 0), `export/airq-mini-<part>.{3mf,step}`. The airQ's are in
test_airq_exports.py; the mesh readers are shared.

Fast tests read the committed 3MF as plain XML (and the generator's own body list and light trace).
SolidCraft tests (skipped where solidcraft-cli is missing, as in CI) reopen every file and compare it with
the design's body.
"""
import math
import random

import pytest

import airq_check as A
import airq_mini
import airq_mini_check as K
import encbuild
from sclib import ENCLOSURE
from test_airq_exports import down_faces, mesh_areas, mesh_box

EXPORT = ENCLOSURE / "export"
PRINTED = list(airq_mini.PRINT_PARTS)
# Bodies of airq-mini.sc that are bought (cut or stuck on), not printed: the foam parts and the die-cut stop
BOUGHT = ["zone_seal", "sen66_foam", "sen66_pad", "sen66_top_seal", "guide_stop"]
GUIDES = ["light_guide_co2", "light_guide_pm"]
LIMIT = 5 * 1024 * 1024
TOL = 0.05
S = airq_mini.build()
V = S.v


def path(part, ext):
    return EXPORT / f"airq-mini-{part}.{ext}"


def test_every_body_is_printed_or_bought():
    """A new body in the generator must be classified here, as printed (PRINT_PARTS) or bought."""
    assert not set(PRINTED) & set(BOUGHT)
    assert set(S.bodies) == set(PRINTED) | set(BOUGHT), sorted(set(S.bodies) ^ (set(PRINTED) | set(BOUGHT)))


def test_exports_are_registered_per_part():
    assert encbuild.exports_of("airq-mini") == [f"export/airq-mini-{p}.{e}" for p in PRINTED for e in ("3mf", "step")]
    assert not any(b in e for b in BOUGHT for e in encbuild.exports_of("airq-mini"))
    assert [encbuild.part_of(airq_mini, e) for e in encbuild.exports_of("airq-mini")[::2]] == PRINTED


def test_face_down_parts_turn_by_the_faces_tilt():
    """The face is `tilt_deg` off the vertical, so the turn that lays it flat is 90 + tilt_deg about x."""
    flat = round(90 + math.degrees(V("tilt_deg")), 6)      # the script value is in radians
    assert flat == 114
    for part in ("shell", "orange_dot", "zone_wall", *GUIDES):
        assert airq_mini.PRINT_PARTS[part]["turns"] == [("x", flat)]
    assert airq_mini.PRINT_PARTS["orange_dot"]["ref"] == "shell"


# Per part: the least flat area (mm2) that must rest on the bed, and the most down-facing area above it
# steeper than 45 deg (what the slicer must bridge or support). Measured on the committed meshes; the second
# number carries the documented exceptions (README "Print and assembly guide (airQ mini)", section 2).
BED_CONTACT = {
    "shell": (1500, 330),            # chamfer 93, labels and dot recess 65 (0.4 / 0.6 ceilings), side-wall ends and boss notches
    "orange_dot": (10, 1),
    "base_plate": (3300, 540),       # bridges: the intake rows (3 x 79), the outlet grille (152), the USB-C ceiling (12.9 mm wide)
    "zone_wall": (700, 135),         # on its slanted face; shallow ceilings (24 deg from horizontal) all within 1.8 of the bed
    "light_guide_co2": (30, 36),     # exit face down; the two flange fronts (1.6 up) hang, carrying none of the light
    "light_guide_pm": (30, 36),
    "gasket_out": (90, 1),
    "gasket_in": (25, 1),            # lying on its side: nothing hangs
    "grommet_zone_a": (20, 4),       # the 0.5 ribs' undersides
    "grommet_zone_b": (13, 1),
    "tongue_mount": (2.5, 15),       # 2.8 mm2 on the spigot's end; the collar's underside ring hangs 1.0 up: brim
}


def test_every_printed_part_has_a_bed_contact_budget():
    assert set(BED_CONTACT) == set(PRINTED)


@pytest.mark.parametrize("part", PRINTED)
def test_committed_files_are_small_and_rest_on_the_bed(part):
    for ext in ("3mf", "step"):
        f = path(part, ext)
        assert f.exists(), f
        assert f.stat().st_size <= LIMIT, f"{f.name} over the R8 limit"
    n, lo, _ = mesh_box(path(part, "3mf"))
    assert n == 1
    zmin, bed, over = mesh_areas(path(part, "3mf"))
    assert abs(zmin) < TOL
    least, most = BED_CONTACT[part]
    assert bed >= least, f"{part} rests on only {bed:.1f} mm2 of flat bed contact (needs {least})"
    assert over <= most, f"{part} hangs {over:.1f} mm2 of steep overhang over the bed (budget {most})"


# What hangs, by name (normal and lowest z of the face after the print turn, area in mm2)
HANGING = {
    # the two flange fronts (over and under the slot, 22.5 + 12.1), parallel to the exit face and 1.6 over it
    "light_guide_co2": {((0.0, 0.0, -1.0, 1.6), 34.6): "flange fronts over and under the slot"},
    "light_guide_pm": {((0.0, 0.0, -1.0, 1.6), 34.6): "flange fronts over and under the slot"},
    # the collar's underside ring round the spigot it stands on (1.0 up)
    "tongue_mount": {((0.0, 0.0, -1.0, 1.0), 13.8): "collar underside ring"},
    "grommet_zone_a": {((0.0, 0.0, -1.0, 0.7), 3.2): "ribs' undersides"},
}


@pytest.mark.parametrize("part", list(HANGING))
def test_small_parts_hang_only_the_named_faces(part):
    got = down_faces(path(part, "3mf"))
    named = {k: a for k, a in HANGING[part]}
    assert len(got) == len(named), f"{part} hangs faces {sorted(got)}"
    for key, area in got.items():
        match = [k for k in named if all(abs(x - y) < 0.1 for x, y in zip(key[:3], k[:3])) and abs(key[3] - k[3]) < 0.15]
        assert match, f"{part} hangs {area:.1f} mm2 over the bed on an unnamed face {key}"
        assert area <= named[match[0]] * 1.1, (part, key, area)


def test_zone_wall_hangs_only_shallow_ceilings_near_the_bed():
    """On its slanted face the down-facing area is ceilings 24 deg off horizontal (the ledge tip 67, the boss
    notches' ledges 37), within 1.8 of the bed, plus the drawer notch's three groove faces (z 23.1 ... 24.2,
    10 mm2) and under 9 mm2 of tessellation slivers (each under 1 mm2) on the cable bores' and notches' curved edges."""
    got = down_faces(path("zone_wall", "3mf"))
    big = {k: a for k, a in got.items() if a >= 1.0}
    assert all(abs(k[0]) < 0.1 and abs(k[1] - 0.4) < 0.1 and abs(k[2] + 0.9) < 0.1 for k in big), sorted(big)
    near = sum(a for k, a in big.items() if k[3] <= 1.8)
    far = {k: a for k, a in big.items() if k[3] > 1.8}
    assert near >= 100, near
    assert sum(far.values()) <= 11 and all(23.0 <= k[3] <= 24.3 for k in far), sorted(far)
    assert sum(a for a in got.values() if a < 1.0) <= 9


# --- the light guides' supports against the trace of the light -------------------------------------------

def face_down_rotation(deg):
    sin_a, cos_a = math.sin(math.radians(deg)), math.cos(math.radians(deg))
    return lambda ny, nz: ny * sin_a + nz * cos_a      # z of a world normal (x, ny, nz) turned about x


def traced_shares(turn_deg, n_rays=20000, seed=1):
    """{half: result} of `airq_mini_check.guide_delivery`'s trace (the same rays: one random stream that runs on
    from the CO2 half's LEDs into the PM2.5 half's), instrumented. Per half: `delivered` rays reach the exit;
    `hung` = those that meet a face which hangs when the guide is turned `turn_deg` about x (that face's outward
    normal's z after the turn under -0.72, i.e. steeper than 45 deg: supports go there); `reflected` = those that
    reflect off at least one face; `per_led` delivered counts; `normals` = the exit's and the entry faces' normal z
    after the turn."""
    rng = random.Random(seed)
    return {half: _traced(half, turn_deg, n_rays, rng) for half in ("co2", "pm")}


def _traced(half, turn_deg, n_rays, rng):
    v = V
    sn, c, lip = K._fr(S)
    nz_of = face_down_rotation(turn_deg)
    crit = math.radians(A.CRIT_DEG)
    ye, yf, zc, hh, hw = v("lg_ye"), v("board_y0"), v("led_z"), v("led_face_h") / 2, v("led_face_w") / 2
    prisms = K.guide_prisms(S, half)
    delivered = hung = reflected = 0
    per_led = {}
    normals = {}
    for i in dict(K.MF.LEDS)[half]:
        foot = next(p for p in prisms if p["name"] == f"D{i} foot")
        (fs0, ft0), (fs1, ft1) = foot["poly"][1], foot["poly"][2]
        win_z = sorted(lip + sv * c - tv * sn for sv, tv in ((fs0, ft0), (fs1, ft1)))
        cx = v(f"d{i}_x")
        per_led[f"D{i}"] = 0
        for _ in range(n_rays):
            r1, r2 = rng.random(), rng.random()
            ph, sr = 2 * math.pi * r1, math.sqrt(r2)
            d = (sr * math.cos(ph), -math.sqrt(1 - r2), sr * math.sin(ph))
            p0 = (cx + rng.uniform(-hw, hw), yf, zc + rng.uniform(-hh, hh))
            k = (ye - yf) / d[1]
            q = (p0[0] + k * d[0], ye, p0[2] + k * d[2])
            if not (foot["x"][0] <= q[0] <= foot["x"][1] and win_z[0] <= q[2] <= win_z[1]):
                continue
            dx, dz = d[0] / A.N_PETG, d[2] / A.N_PETG
            dw = (dx, -math.sqrt(max(0.0, 1 - dx * dx - dz * dz)), dz)
            D = [dw[0], dw[1] * sn + dw[2] * c, dw[1] * c - dw[2] * sn]
            st = K._to_st((sn, c, lip), q[1], q[2])
            P = [q[0] + 1e-6 * D[0], st[0] + 1e-6 * D[1], st[1] + 1e-6 * D[2]]
            faces = []
            for _bounce in range(200):
                h = A._next_exit(prisms, P, D)
                if h is None:
                    break
                lam, nrm, kind = h
                P = [P[j] + lam * D[j] for j in range(3)]
                cosi = sum(D[j] * nrm[j] for j in range(3))
                world_nz = nz_of(nrm[1] * sn + nrm[2] * c, nrm[1] * c - nrm[2] * sn)
                if math.acos(max(-1.0, min(1.0, cosi))) < crit:
                    if kind == "exit":
                        normals["exit"] = world_nz
                        delivered += 1
                        per_led[f"D{i}"] += 1
                        hung += any(f < -0.72 for f in faces)
                        reflected += bool(faces)
                    break
                faces.append(world_nz)
                D = [D[j] - 2 * cosi * nrm[j] for j in range(3)]
                P = [P[j] + 1e-7 * D[j] for j in range(3)]
    foot = next(p for p in prisms if p["name"].endswith("foot"))
    es, et = foot["poly"][1], foot["poly"][2]
    ds, dt = et[0] - es[0], et[1] - es[1]
    ln = math.hypot(ds, dt)
    ns, nt = foot["sign"] * dt / ln, -foot["sign"] * ds / ln              # the entry face's outward normal in (s, t)
    normals["entry"] = nz_of(ns * sn + nt * c, ns * c - nt * sn)
    return {"delivered": delivered, "hung": hung, "reflected": reflected, "per_led": per_led, "normals": normals}


@pytest.mark.parametrize("half", ["co2", "pm"])
def test_supports_touch_none_of_the_light(half):
    """Turned 114 deg, the guide lies on its exit face (that face's normal points straight down) and the entry
    faces lean up; of the rays the trace delivers, none meets a face that hangs (the supports go only under the
    flange fronts). The same trace as the check's: every LED's delivered count equals `guide_delivery`'s, and
    most delivered rays do reflect somewhere (the test is not vacuous: with the guide on its back they would
    meet a hanging face)."""
    t = traced_shares(114)[half]
    d = K.guide_delivery(S)
    for led, n in t["per_led"].items():
        assert n == d["leds"][led]["delivered"], (led, n)
    assert t["delivered"] > 4000
    assert t["normals"]["exit"] == pytest.approx(-1.0, abs=1e-6)       # exit face down: the bed
    assert t["normals"]["entry"] > 0.9                                  # entry faces lean up: no support there
    assert t["hung"] == 0
    assert t["reflected"] > 0.3 * t["delivered"]
    # as designed (turn 0) the foot bottoms and the tongue lower side hang and carry light: the check can fail
    assert traced_shares(0, n_rays=4000)[half]["hung"] > 0


# --- SolidCraft: the files reopen as the design's bodies ---------------------------------------------

@pytest.fixture(scope="module")
def design(cli, tmp_path_factory):
    """The saved design's bodies, and the printed parts' boxes after their turns (before the bed)."""
    import json
    import subprocess
    tmp = tmp_path_factory.mktemp("airq_mini_exports")
    out = tmp / "design.json"
    subprocess.run([cli, "eval", str(ENCLOSURE / "airq-mini.sc"), "--quiet", "--json-out", str(out)], check=True)
    bodies = {b["name"]: b for b in json.loads(out.read_text(encoding="utf-8"))["bodies"]}
    boxes = encbuild.print_boxes("airq-mini", ENCLOSURE / "airq-mini.sc", cli, tmp / "boxes.json")
    return bodies, boxes, tmp


def test_every_saved_body_is_printed_or_bought(design):
    assert set(design[0]) == set(PRINTED) | set(BOUGHT)


@pytest.mark.parametrize("part", PRINTED)
def test_reopened_exports_match_the_design_body(cli, design, part):
    bodies, boxes, tmp = design
    body = bodies[part]
    spec = airq_mini.PRINT_PARTS[part]
    lift = -boxes[spec.get("ref", part)]["min"][2]
    want = boxes[part]
    for ext in ("3mf", "step"):
        got = encbuild.eval_bodies(path(part, ext), cli, tmp / f"{part}.{ext}.json")
        assert len(got) == 1, f"{part}.{ext} reopens with {len(got)} bodies"
        (bb,) = got.values()
        for i in range(3):
            shift = lift if i == 2 else 0
            assert abs(bb["min"][i] - (want["min"][i] + shift)) < TOL, (part, ext, i)
            assert abs(bb["max"][i] - (want["max"][i] + shift)) < TOL, (part, ext, i)
        if all(deg % 90 == 0 for _, deg in spec["turns"]):
            dbox = body["bbox"]
            extents = sorted(hi - lo for lo, hi in zip(dbox["min"], dbox["max"]))
            got_ext = sorted(hi - lo for lo, hi in zip(bb["min"], bb["max"]))
            assert all(abs(a - b) < TOL for a, b in zip(got_ext, extents)), (part, got_ext, extents)
    assert abs(want["volume"] - body["volume_mm3"]) < 1e-6 * body["volume_mm3"]


def test_build_writes_the_committed_exports(cli):
    r = encbuild.build("airq-mini", cli, commit=False)
    assert len(r["exports"]) == 2 * len(PRINTED)
    for e in r["exports"]:
        if e["parts"] is not None:
            assert len(e["parts"]) == 1
