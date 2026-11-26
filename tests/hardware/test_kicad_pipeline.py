"""End-to-end checks that need KiCad 10 (kicad-cli); skipped where it is not installed (CI)."""
import csv
import shutil
import subprocess
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


BOARDS = ("main", "tongue")      # tools/hw/build.py boards: hardware/src/<board> -> hardware/kicad/<board>


def _tracked(board: str) -> list[str]:
    """Names of the committed (git-tracked) files in hardware/kicad/<board>."""
    out = subprocess.run(["git", "ls-files", f"hardware/kicad/{board}"], cwd=REPO,
                         capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("git is not available")
    return sorted(Path(line).name for line in out.stdout.splitlines())


def _scratch_repo(root: Path, board: str = "main") -> Path:
    """A board's source, the interface contract, the airq library and its committed KiCad project,
    in `root`.

    Starting from the committed project (not from nothing) is what a rebuild does in the
    repository: the board keeps its routing, the .kicad_pro its KiCad settings.
    """
    shutil.copytree(REPO / f"hardware/src/{board}", root / f"hardware/src/{board}")
    shutil.copy(REPO / "hardware/interface.yaml", root / "hardware/interface.yaml")
    lib = root / "hardware/kicad/lib"
    lib.mkdir(parents=True)
    shutil.copy(REPO / "hardware/kicad/lib/airq.kicad_sym", lib)
    shutil.copytree(REPO / "hardware/kicad/lib/airq.pretty", lib / "airq.pretty")
    (root / f"hardware/kicad/{board}").mkdir()
    for name in _tracked(board):
        shutil.copy(REPO / f"hardware/kicad/{board}" / name, root / f"hardware/kicad/{board}" / name)
    return root


def _text(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


@pytest.fixture(scope="module", params=BOARDS)
def board_build(request, tmp_path_factory):
    """(board, scratch root, build result): a rebuild of a committed project in a scratch copy
    of the repository."""
    from build import build
    board = request.param
    root = _scratch_repo(tmp_path_factory.mktemp(board), board)
    return board, root, build(root / f"hardware/src/{board}", root / "build", board)


def test_board_is_clean(board_build):
    """ERC and DRC clean on both boards, which are placed and fully routed: no error of any kind
    (unrouted connections included), every part placed from layout.yaml, no Edge.Cuts drawn by hand,
    and no silkscreen on or over a board edge (reference texts are placed from layout.yaml)."""
    board, _, res = board_build
    assert not [k for (sev, k) in res.erc if sev == "error"], res.erc
    assert res.errors(routed=True) == 0, (res.erc, res.drc)
    assert res.unplaced == [] and res.hand_edges == [] and not res.edges_replaced
    assert not [k for (_, k) in res.drc if k == "silk_edge_clearance"], res.drc


def test_rebuilding_the_committed_project_changes_nothing(board_build):
    """The stale-output guard: the committed files are exactly what a rebuild leaves behind.

    Fails when the source changed without a rebuild, after a KiCad GUI save that a rebuild
    normalises, or when a generated file is not committed (or an obsolete one still is).
    """
    board, root, res = board_build
    written = sorted(p.name for p in res.written)
    assert written == _tracked(board), f"commit exactly the files tools/hw/build.py {board} writes"
    stale = [n for n in written if _text(root / f"hardware/kicad/{board}" / n)
             != _text(REPO / f"hardware/kicad/{board}" / n)]
    assert not stale, f"run tools/hw/build.py {board} and commit: {stale}"


def test_jlc_bom_cpl_and_dsn(board_build):
    board, root, _ = board_build
    bom = list(csv.DictReader((root / f"build/{board}-bom.csv").open(encoding="utf-8")))
    assert list(bom[0]) == ["Comment", "Designator", "Footprint", "LCSC"]
    assert all(r["LCSC"].startswith("C") for r in bom)
    bom_refs = sorted(ref for r in bom for ref in r["Designator"].split(","))
    cpl = list(csv.DictReader((root / f"build/{board}-cpl.csv").open(encoding="utf-8")))
    assert list(cpl[0]) == ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
    assert sorted(r["Designator"] for r in cpl) == bom_refs
    assert all(r["Layer"] == "Top" for r in cpl)
    dsn = (root / f"build/{board}.dsn").read_text(encoding="utf-8")
    assert "(placement" in dsn and "(network" in dsn


def test_tongue_gates(board_build):
    """The plan's Task 6 gates on a fresh rebuild: netlist vs the tongue's interface subset,
    outline <= 22 x 14 mm with every part on F.Cu, and the BOM against the parts table (the
    M2 hole is not a BOM or CPL line)."""
    from check_board import check_board
    from check_bom import check_bom
    from check_netlist import check_netlist
    board, root, res = board_build
    if board != "tongue":
        pytest.skip("tongue only")
    assert check_netlist(root / "build/tongue.net", REPO / "hardware/src/tongue/interface.yaml") == []
    assert check_board(res.pcb, 22.0, 14.0) == []
    assert check_bom(root / "build/tongue-bom.csv", REPO / "hardware/bom/parts.csv") == []
    bom = (root / "build/tongue-bom.csv").read_text(encoding="utf-8")
    assert "H1" not in bom and "H1" not in (root / "build/tongue-cpl.csv").read_text(encoding="utf-8")


def test_main_gates(board_build):
    """The plan's Task 4 gates on a fresh rebuild: the netlist against hardware/interface.yaml (every
    rule group: signals, connectors, USB CC, I2C pull-ups, bulk caps, straps) and the BOM against
    the parts table. The unpopulated J_AUX_UART header is marked DNP: no BOM or CPL line."""
    from check_bom import check_bom
    from check_netlist import Netlist, check_netlist
    board, root, _ = board_build
    if board != "main":
        pytest.skip("main only")
    assert check_netlist(root / "build/main.net", REPO / "hardware/interface.yaml") == []
    assert check_bom(root / "build/main-bom.csv", REPO / "hardware/bom/parts.csv") == []
    aux = Netlist((root / "build/main.net").read_text(encoding="utf-8")).by_role("J_AUX_UART")
    bom = list(csv.DictReader((root / "build/main-bom.csv").open(encoding="utf-8")))
    cpl = list(csv.DictReader((root / "build/main-cpl.csv").open(encoding="utf-8")))
    assert aux and aux not in {ref for r in bom for ref in r["Designator"].split(",")}
    assert aux not in {r["Designator"] for r in cpl}


ROUTED = """
  (segment (start 105 125) (end 115 125) (width 0.4) (layer "B.Cu") (net "GND")
    (uuid "0d1f5b1e-0000-4000-8000-000000000001"))
  (via (at 115 125) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net "GND")
    (uuid "0d1f5b1e-0000-4000-8000-000000000002"))
  (zone (net "GND") (layer "B.Cu") (uuid "0d1f5b1e-0000-4000-8000-000000000003") (hatch edge 0.5)
    (connect_pads (clearance 0.2)) (min_thickness 0.2)
    (fill yes (thermal_gap 0.3) (thermal_bridge_width 0.3))
    (polygon (pts (xy 100 100) (xy 160 100) (xy 160 130) (xy 100 130))))
  (gr_rect (start 140 120) (end 145 121) (stroke (width 0.05) (type default)) (fill no)
    (layer "Edge.Cuts") (uuid "0d1f5b1e-0000-4000-8000-000000000004"))
"""


def test_routing_zones_and_drawn_cutouts_survive_rebuilds(tmp_path):
    """A routed board (track, via, filled ground pour, a slot drawn in KiCad) is kept by a
    rebuild, the pour is refilled and saved, and a second rebuild changes nothing."""
    from build import build
    root = _scratch_repo(tmp_path)
    pcb = root / "hardware/kicad/main/airq-main.kicad_pcb"
    pcb.write_text(pcb.read_text(encoding="utf-8").rstrip()[:-1] + ROUTED + ")\n", encoding="utf-8")
    first = build(root / "hardware/src/main", root / "build", "main")
    tree = parse(pcb.read_text(encoding="utf-8"))
    uuids = {str(atom(i, "uuid")) for i in tree[1:] if isinstance(i, list) and atom(i, "uuid")}
    assert {f"0d1f5b1e-0000-4000-8000-00000000000{i}" for i in range(1, 5)} <= uuids
    zone = next(z for z in children(tree, "zone")
                if atom(z, "uuid") == "0d1f5b1e-0000-4000-8000-000000000003")
    assert child(zone, "filled_polygon") is not None          # filled by DRC, saved
    assert first.hand_edges == ["0d1f5b1e-0000-4000-8000-000000000004"]
    snapshot = {p.name: p.read_bytes() for p in first.written}
    second = build(root / "hardware/src/main", root / "build", "main")
    assert {p.name: p.read_bytes() for p in second.written} == snapshot
