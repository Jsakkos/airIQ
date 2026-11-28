"""The committed JLC upload files (hardware/fab/<board>/) and STEP models (hardware/step/).

Pure Python on the committed files (no KiCad needed). tests/hardware/test_kicad_pipeline.py checks
that the fab files equal a rebuild (the stale-output guard); these tests check what JLC and the
enclosure need from them: every layer and both drill files, one origin for Gerbers, drill and CPL
(the outline's bottom-left corner, Y up), the fitted parts and only those, and a STEP model that
holds every fitted part with a 3-D model.
"""
import csv
import io
import math
import re
import zipfile
from pathlib import Path

import pytest
import yaml

from design import placement_entry
from jlc import CPL_HEADER
from sexpr import atom, child, children, parse

REPO = Path(__file__).resolve().parents[2]
BOARDS = ("main", "tongue")
LAYERS = ["F_Cu.gtl", "B_Cu.gbl", "F_Paste.gtp", "B_Paste.gbp", "F_Silkscreen.gto",
          "B_Silkscreen.gbo", "F_Mask.gts", "B_Mask.gbs", "Edge_Cuts.gm1", "PTH.drl", "NPTH.drl"]
MECH = yaml.safe_load((REPO / "hardware/interface.yaml").read_text(encoding="utf-8"))["mechanical"]
_XY = re.compile(r"X(-?\d+)Y(-?\d+)D0([123])\*")        # Gerber 4.6 mm coordinates
_DRILL_XY = re.compile(r"^X(-?[\d.]+)Y(-?[\d.]+)", re.M)


def _layout(board):
    return yaml.safe_load((REPO / f"hardware/src/{board}/layout.yaml").read_text(encoding="utf-8"))


def _zip(board):
    return zipfile.ZipFile(REPO / f"hardware/fab/{board}/airq-{board}-gerbers.zip")


def _csv(board, name):
    with open(REPO / f"hardware/fab/{board}/{name}", newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def _footprints(board):
    """reference -> (attributes, has a 3-D model, footprint `at` x/y/rotation, pads), page mm."""
    tree = parse((REPO / f"hardware/kicad/{board}/airq-{board}.kicad_pcb").read_text(encoding="utf-8"))
    out = {}
    for fp in children(tree, "footprint"):
        ref = next(str(p[2]) for p in children(fp, "property") if p[1] == "Reference")
        attr = child(fp, "attr")
        at = child(fp, "at")
        pads = [(float(child(p, "at")[1]), float(child(p, "at")[2])) for p in children(fp, "pad")]
        out[ref] = ({str(a) for a in attr[1:]} if attr else set(), bool(children(fp, "model")),
                    (float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0), pads)
    return out


def _fitted(board):
    """References JLC places: not DNP and not excluded from the BOM (the mounting holes)."""
    return {r for r, (attrs, *_) in _footprints(board).items()
            if not attrs & {"dnp", "exclude_from_bom", "exclude_from_pos_files"}}


@pytest.mark.parametrize("board", BOARDS)
def test_gerber_zip_holds_every_layer_and_both_drill_files(board):
    z = _zip(board)
    assert sorted(z.namelist()) == sorted(f"airq-{board}-{n}" for n in LAYERS)
    for name in z.namelist():
        text = z.read(name).decode("utf-8")
        assert "CreationDate" not in text and " date " not in text, name   # reproducible
        if name.endswith(".drl"):
            assert text.startswith("M48\n") and "METRIC" in text and text.rstrip().endswith("M30")
        else:
            assert "%FSLAX46Y46*%" in text and "%MOMM*%" in text and "%TF.FileFunction," in text


@pytest.mark.parametrize("board", BOARDS)
def test_gerbers_drill_and_cpl_share_one_origin(board):
    """The outline spans 0..W x 0..H in the Gerbers (origin at its bottom-left corner, Y up), the
    mounting holes sit at (x, H - y) of the layout in the NPTH file, and every CPL line is the
    part's layout.yaml placement in the same frame."""
    layout = _layout(board)
    w, h = layout["board"]["width"], layout["board"]["height"]
    z = _zip(board)
    edge = [(int(x) / 1e6, int(y) / 1e6) for x, y, _ in
            _XY.findall(z.read(f"airq-{board}-Edge_Cuts.gm1").decode())]
    assert (min(p[0] for p in edge), min(p[1] for p in edge)) == (0, 0)
    assert (max(p[0] for p in edge), max(p[1] for p in edge)) == (w, h)
    npth = {(float(x), float(y)) for x, y in
            _DRILL_XY.findall(z.read(f"airq-{board}-NPTH.drl").decode())}
    holes = {r: placement_entry(v) for r, v in layout["placement"].items() if r.startswith("H")}
    assert holes and {(x, round(h - y, 3)) for x, y, *_ in holes.values()} <= npth
    for name in (f"airq-{board}-PTH.drl", f"airq-{board}-NPTH.drl"):
        for x, y in _DRILL_XY.findall(z.read(name).decode()):
            assert 0 <= float(x) <= w and 0 <= float(y) <= h, (name, x, y)
    place = {r: placement_entry(v) for r, v in layout["placement"].items()}
    header, *rows = _csv(board, "cpl.csv")
    assert header == CPL_HEADER
    for ref, mx, my, layer, rot in rows:
        x, y, r, _ = place[ref]
        assert (float(mx.removesuffix("mm")), float(my.removesuffix("mm"))) == \
            pytest.approx((x, h - y), abs=1e-4), ref
        assert layer == "Top" and float(rot) == pytest.approx(r % 360), ref


@pytest.mark.parametrize("board", BOARDS)
def test_bom_and_cpl_list_exactly_the_fitted_parts(board):
    """JLC's columns; one LCSC number per BOM line; the unfitted J_AUX_UART header (DNP) and the
    mounting holes are in neither file."""
    header, *bom = _csv(board, "bom.csv")
    assert header == ["Comment", "Designator", "Footprint", "LCSC"]
    assert all(re.fullmatch(r"C\d+", lcsc) for *_, lcsc in bom)
    bom_refs = [r for _, refs, _, _ in bom for r in refs.split(",")]
    cpl_refs = [row[0] for row in _csv(board, "cpl.csv")[1:]]
    assert sorted(bom_refs) == sorted(cpl_refs) == sorted(_fitted(board))
    dnp = {r for r, (attrs, *_) in _footprints(board).items() if "dnp" in attrs}
    assert board != "main" or dnp == {"J6"}
    assert not dnp & set(bom_refs)


@pytest.mark.parametrize("board", BOARDS)
def test_no_paste_on_unfitted_parts(board):
    h = _layout(board)["board"]["height"]
    ox, oy = _layout(board)["board"]["origin"]
    paste = [(int(x) / 1e6, int(y) / 1e6) for x, y, op in
             _XY.findall(_zip(board).read(f"airq-{board}-F_Paste.gtp").decode()) if op == "3"]
    for ref, (attrs, _, (fx, fy, frot), pads) in _footprints(board).items():
        if "dnp" not in attrs:
            continue
        a = math.radians(frot)
        for px, py in pads:
            bx = fx + px * math.cos(a) + py * math.sin(a) - ox
            by = oy + h - (fy - px * math.sin(a) + py * math.cos(a))
            assert not [p for p in paste if math.dist(p, (bx, by)) < 0.5], (ref, bx, by)


def test_usb_c_shell_legs_are_pin_in_paste():
    """J1's four plated shell legs get paste apertures (kicad/lib/README.md fix 22): JLC places the
    receptacle on its SMT line, so the paste printed over the slots solders them in reflow."""
    tree = parse((REPO / "hardware/kicad/main/airq-main.kicad_pcb").read_text(encoding="utf-8"))
    h = _layout("main")["board"]["height"]
    ox, oy = _layout("main")["board"]["origin"]
    paste = [(int(x) / 1e6, int(y) / 1e6) for x, y, op in
             _XY.findall(_zip("main").read("airq-main-F_Paste.gtp").decode()) if op == "3"]
    j1 = next(fp for fp in children(tree, "footprint")
              if any(str(p[1]) == "Reference" and str(p[2]) == "J1" for p in children(fp, "property")))
    fx, fy, frot = (float(v) for v in child(j1, "at")[1:4])
    legs = [p for p in children(j1, "pad") if str(p[2]) == "thru_hole"]
    assert len(legs) == 4
    a = math.radians(frot)
    for pad in legs:
        assert "F.Paste" in [str(layer) for layer in child(pad, "layers")[1:]]
        px, py = float(child(pad, "at")[1]), float(child(pad, "at")[2])
        bx = fx + px * math.cos(a) + py * math.sin(a) - ox
        by = oy + h - (fy - px * math.sin(a) + py * math.cos(a))
        assert [p for p in paste if math.dist(p, (bx, by)) < 0.01], (bx, by)


@pytest.mark.parametrize("board", BOARDS)
def test_step_holds_every_fitted_part_with_a_model(board):
    """`build.py --step` writes the board body and one instance per fitted part that has a 3-D
    model (DNP parts left out). A part added or removed since the export fails here; a moved part
    does not, so re-export after any placement change (hardware/README.md)."""
    step = (REPO / f"hardware/step/airq-{board}.step").read_text(encoding="utf-8", errors="replace")
    assert step.startswith("ISO-10303-21;") and "KiCad electronic assembly" in step[:300]
    assert f"PRODUCT('airq-{board}_PCB'" in step
    refs = [r for r in re.findall(r"NEXT_ASSEMBLY_USAGE_OCCURRENCE\('[^']*','([^']*)'", step)
            if not r.startswith("=>")]
    modelled = {r for r, (attrs, has_model, *_) in _footprints(board).items()
                if has_model and "dnp" not in attrs}
    assert sorted(refs) == sorted(modelled)
    assert MECH[board]["step"] == {"x": "X", "y": "-Y", "z": "Z + 1.6"}
