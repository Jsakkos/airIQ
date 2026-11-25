"""End-to-end checks that need KiCad 10 (kicad-cli); skipped where it is not installed (CI)."""
import csv
import shutil
from pathlib import Path

import pytest

import kicad_env
from design import PartSrc
from gen_pcb import read_netlist
from gen_sch import generate_schematics
from sexpr import atom, child, children, parse

REPO = Path(__file__).resolve().parents[2]
FIXTURE_LIB = Path(__file__).resolve().parent / "fixtures" / "lib"

try:
    kicad_env.kicad_cli()
    HAVE_KICAD = True
except kicad_env.KicadNotFound:
    HAVE_KICAD = False
pytestmark = pytest.mark.skipif(not HAVE_KICAD, reason="kicad-cli (KiCad 10) not installed")


def _netlist(make_design, libs, tmp_path, parts) -> str:
    d = make_design({"t": parts})
    out = tmp_path / "out"
    out.mkdir()
    for name, text in generate_schematics(d, libs).items():
        (out / name).write_text(text, encoding="utf-8")
    (out / "tp.kicad_pro").write_text("{}\n", encoding="utf-8")
    (out / "sym-lib-table").write_text(
        f'(sym_lib_table (version 7) (lib (name "test") (type "KiCad") '
        f'(uri "{(FIXTURE_LIB / "test.kicad_sym").as_posix()}") (options "") (descr "")))\n',
        encoding="utf-8")
    kicad_env.run_cli("sch", "export", "netlist", "--format", "kicadsexpr", "-o", out / "tp.net",
                      out / "tp.kicad_sch")
    return (out / "tp.net").read_text(encoding="utf-8")


def test_pin_ends_match_kicad_for_every_rotation_and_mirror(make_design, libs, tmp_path):
    parts, expected = [], {}
    for i, (mirror, rot) in enumerate((m, r) for m in (None, "x", "y") for r in (0, 90, 180, 270)):
        ref = f"U{i + 1}"
        nets = {str(n): f"N{i}_{n}" for n in range(1, 7)}
        expected.update({(ref, n): net for n, net in nets.items()})
        parts.append(PartSrc(ref, "test:U6", (38.1 + (i % 4) * 63.5, 38.1 + (i // 4) * 50.8),
                             rot=rot, mirror=mirror, stub=2.54 * (i % 2), pins=nets))
    got = {}
    for net in children(child(parse(_netlist(make_design, libs, tmp_path, parts)), "nets"), "net"):
        for node in children(net, "node"):
            got[(atom(node, "ref"), atom(node, "pin"))] = atom(net, "name")
    assert {k: v.rsplit("/", 1)[-1] for k, v in got.items()} == expected


def test_dnp_and_fields_reach_the_netlist(make_design, libs, tmp_path):
    parts = [PartSrc("R1", "test:R", (25.4, 25.4), footprint="test:R_TEST", dnp=True,
                     fields={"Role": "J_X"}, pins=["A", "B"])]
    (r1,) = read_netlist(_netlist(make_design, libs, tmp_path, parts))
    assert r1.dnp and r1.fields["Role"] == "J_X" and r1.path.count("/") == 2


@pytest.fixture(scope="module")
def main_build(tmp_path_factory):
    """The real main-board source built in a scratch copy of the repository layout."""
    from build import build
    root = tmp_path_factory.mktemp("repo")
    shutil.copytree(REPO / "hardware/src/main", root / "hardware/src/main")
    (root / "hardware/kicad/lib").mkdir(parents=True)
    shutil.copy(REPO / "hardware/kicad/lib/airq.kicad_sym", root / "hardware/kicad/lib")
    shutil.copytree(REPO / "hardware/kicad/lib/airq.pretty", root / "hardware/kicad/lib/airq.pretty")
    return root, build(root / "hardware/src/main", root / "build", "main")


def test_main_board_is_clean_apart_from_routing(main_build):
    _, res = main_build
    assert res.errors(routed=False) == 0, (res.erc, res.drc)
    assert not [k for (sev, k) in res.erc if sev == "error"]
    assert {k for (sev, k) in res.drc if sev == "error"} <= {"unconnected_items"}
    assert res.unplaced == []


def test_committed_kicad_files_are_up_to_date_with_the_source(main_build):
    root, _ = main_build
    built = root / "hardware/kicad/main"
    names = sorted(p.name for p in built.iterdir() if p.suffix != ".kicad_prl")
    committed = REPO / "hardware/kicad/main"
    assert names == sorted(p.name for p in committed.iterdir() if p.suffix != ".kicad_prl")
    stale = [n for n in names if (built / n).read_bytes().replace(b"\r\n", b"\n")
             != (committed / n).read_bytes().replace(b"\r\n", b"\n")]
    assert not stale, f"regenerate with tools/hw/build.py main and commit: {stale}"


def test_jlc_bom_cpl_and_dsn(main_build):
    root, _ = main_build
    bom = list(csv.DictReader((root / "build/main-bom.csv").open(encoding="utf-8")))
    assert list(bom[0]) == ["Comment", "Designator", "Footprint", "LCSC"]
    assert all(r["LCSC"].startswith("C") for r in bom)
    bom_refs = sorted(ref for r in bom for ref in r["Designator"].split(","))
    cpl = list(csv.DictReader((root / "build/main-cpl.csv").open(encoding="utf-8")))
    assert list(cpl[0]) == ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
    assert sorted(r["Designator"] for r in cpl) == bom_refs
    assert all(r["Layer"] == "Top" for r in cpl)
    dsn = (root / "build/main.dsn").read_text(encoding="utf-8")
    assert "(placement" in dsn and "(network" in dsn


def test_routing_survives_a_rebuild(main_build):
    from build import build
    root, _ = main_build
    pcb = root / "hardware/kicad/main/airq-main.kicad_pcb"
    text = pcb.read_text(encoding="utf-8").rstrip()
    seg = ('(segment (start 105 110) (end 106 110) (width 0.4) (layer "B.Cu") (net "GND") '
           '(uuid "0d1f5b1e-0000-4000-8000-000000000001"))')
    pcb.write_text(text[:-1] + seg + "\n)\n", encoding="utf-8")
    build(root / "hardware/src/main", root / "build", "main")
    segs = children(parse(pcb.read_text(encoding="utf-8")), "segment")
    assert [atom(s, "uuid") for s in segs] == ["0d1f5b1e-0000-4000-8000-000000000001"]
    assert atom(segs[0], "net") == "GND"
