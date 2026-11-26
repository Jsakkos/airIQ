"""Build a board's KiCad 10 project from its design source, then check and export it.

    uv run --with pyyaml python tools/hw/build.py {main,tongue} [--routed] [--step]

Steps (outputs other than the KiCad project go to build/):
 1. read hardware/src/<board>/ (design.py);
 2. copy the project libraries into build/kicad-lib/ in the current KiCad format
    (`kicad-cli sym upgrade` / `fp upgrade`; the generators read only that format);
 3. write the schematic (gen_sch.py), library tables and .kicad_pro (gen_project.py), and let
    KiCad re-save every sheet in its native format (`kicad-cli sch upgrade --force`);
 4. export the netlist: build/<board>.net;
 5. write the board from the netlist and layout.yaml (gen_pcb.py), keeping the routing of the
    current board, and let KiCad re-save it (`kicad-cli pcb upgrade --force`);
 6. ERC, and DRC with schematic parity after refilling the zones; DRC saves the board, so the
    committed zone fills always match the footprints (build/<board>-erc.json, -drc.json);
 7. JLC BOM and CPL (build/<board>-bom.csv, -cpl.csv), Gerbers and drill files
    (build/<board>-gerbers/, zipped as build/<project>-gerbers.zip; options in jlc.py) and the
    Specctra DSN (build/<board>.dsn);
 8. publish the JLC upload files into the project's `fab` folder (hardware/fab/<board>/:
    <project>-gerbers.zip, bom.csv, cpl.csv); they are committed, like the KiCad project;
 9. with --step only: the STEP model into the project's `step` file (hardware/step/), for the
    enclosure. Not part of every build: the export takes seconds and is not byte-reproducible.

Exit status 1 if ERC reports an error, or DRC reports an error other than unrouted
connections; with --routed (after routing) those count too.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import kicad_env
from design import DesignError, load_design
from gen_pcb import Board, generate_board, read_netlist
from gen_project import kicad_dru, kicad_pro, lib_tables
from gen_sch import generate_schematics, resolve_design
from jlc import BOM_ARGS, DRILL_ARGS, GERBER_ARGS, cpl_from_pos, gerber_zip
from kicad_lib import Libraries

REPO = Path(__file__).resolve().parents[2]
BOARDS = {"main": REPO / "hardware/src/main", "tongue": REPO / "hardware/src/tongue"}
UNROUTED = "unconnected_items"
# STEP origin = KiCad's grid origin, the board's top-left corner (the layout.yaml placement frame):
# STEP x = X, y = -Y, z = Z + board thickness (board bottom at z = 0); recorded in
# hardware/interface.yaml `mechanical.<board>.step`. DNP parts (the unfitted J_AUX_UART header) are
# left out: they are not on the built board.
STEP_ARGS = ["--subst-models", "--grid-origin", "--no-dnp", "--force"]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def upgrade_libraries(design, cache: Path) -> Libraries:
    """Current-format copies of the project libraries, plus KiCad's stock folders."""
    syms, fps = {}, {}
    cache.mkdir(parents=True, exist_ok=True)
    for nick, src in design.symbol_libs.items():
        syms[nick] = cache / f"{nick}.kicad_sym"
        syms[nick].unlink(missing_ok=True)  # kicad-cli will not overwrite its output
        kicad_env.run_cli("sym", "upgrade", "--force", src, "-o", syms[nick])
    for nick, src in design.footprint_libs.items():
        fps[nick] = cache / f"{nick}.pretty"
        shutil.rmtree(fps[nick], ignore_errors=True)
        kicad_env.run_cli("fp", "upgrade", "--force", src, "-o", fps[nick])
    return Libraries(syms, fps, kicad_env.stock_symbol_dir(), kicad_env.stock_footprint_dir())


def build_schematic(design, libs: Libraries) -> tuple[Path, list[Path]]:
    """Write the schematic and project files; return the root sheet and every file written."""
    out = design.out_dir
    out.mkdir(parents=True, exist_ok=True)
    placed = resolve_design(design, libs)
    pro = out / f"{design.name}.kicad_pro"
    _write(pro, kicad_pro(design, pro.read_text(encoding="utf-8") if pro.exists() else None))
    files = {pro.name: None, f"{design.name}.kicad_dru": kicad_dru(design),
             **lib_tables(design, placed, libs)}
    sheets = generate_schematics(design, libs)
    for name, text in {**files, **sheets}.items():
        if text is not None:
            _write(out / name, text)
    for name in sheets:
        kicad_env.run_cli("sch", "upgrade", "--force", out / name)
        if name != f"{design.name}.kicad_sch":  # re-saving a sub-sheet alone leaves these
            for junk in (out / name).with_suffix(".kicad_prl"), (out / name).with_suffix(".kicad_pro"):
                junk.unlink(missing_ok=True)
    return out / f"{design.name}.kicad_sch", [out / n for n in {**files, **sheets}]


def build_board(design, libs: Libraries, netlist: Path) -> tuple[Path, Board]:
    pcb = design.out_dir / f"{design.name}.kicad_pcb"
    existing = pcb.read_text(encoding="utf-8") if pcb.exists() else None
    comps = read_netlist(netlist.read_text(encoding="utf-8"))
    board = generate_board(design.name, design.title, design.rev, design.company,
                           design.rel(design.src_dir / "layout.yaml"), comps, design.layout, libs,
                           existing)
    _write(pcb, board.text)
    kicad_env.run_cli("pcb", "upgrade", "--force", pcb)
    return pcb, board


def _summary(items: list[dict]) -> Counter:
    return Counter((v.get("severity", "?"), v.get("type", "?")) for v in items)


def run_erc(sch: Path, report: Path) -> Counter:
    kicad_env.run_cli("sch", "erc", "--format", "json", "--severity-all", "-o", report, sch)
    data = json.loads(report.read_text(encoding="utf-8"))
    return _summary([v for s in data.get("sheets", []) for v in s.get("violations", [])])


def run_drc(pcb: Path, report: Path) -> Counter:
    """DRC on freshly filled zones; the board is saved with those fills (deterministic)."""
    kicad_env.run_cli("pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity",
                      "--refill-zones", "--save-board", "-o", report, pcb)
    data = json.loads(report.read_text(encoding="utf-8"))
    return _summary(data.get("violations", []) + data.get("unconnected_items", [])
                    + data.get("schematic_parity", []))


def _print_counts(title: str, counts: Counter) -> None:
    print(f"{title}: " + (", ".join(f"{n} {sev} {kind}" for (sev, kind), n in sorted(counts.items()))
                          or "clean"))


def export_fab(sch: Path, pcb: Path, build: Path, board: str, fab_dir: Path | None) -> list[Path]:
    """BOM, CPL, Gerber zip and DSN into `build`; the JLC upload files also into `fab_dir`.

    Returns the files written into `fab_dir` (none without one)."""
    bom, cpl = build / f"{board}-bom.csv", build / f"{board}-cpl.csv"
    kicad_env.run_cli("sch", "export", "bom", *BOM_ARGS, "-o", bom, sch)
    pos = build / f"{board}-pos.csv"
    kicad_env.run_cli("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "front",
                      "--use-drill-file-origin", "--exclude-dnp", "-o", pos, pcb)
    _write(cpl, cpl_from_pos(pos.read_text(encoding="utf-8")))
    gerbers = build / f"{board}-gerbers"
    shutil.rmtree(gerbers, ignore_errors=True)
    gerbers.mkdir(parents=True)
    kicad_env.run_cli("pcb", "export", "gerbers", *GERBER_ARGS, "-o", gerbers, pcb)
    kicad_env.run_cli("pcb", "export", "drill", *DRILL_ARGS, "-o", gerbers, pcb)
    zipped = build / f"{pcb.stem}-gerbers.zip"
    zipped.write_bytes(gerber_zip(gerbers))
    dsn = subprocess.run([str(kicad_env.kicad_python()), str(Path(__file__).with_name("kicad_dsn.py")),
                          str(pcb), str(build / f"{board}.dsn")], capture_output=True, text=True)
    if dsn.returncode != 0:
        raise RuntimeError(f"DSN export failed:\n{dsn.stdout}{dsn.stderr}")
    if fab_dir is None:
        return []
    fab_dir.mkdir(parents=True, exist_ok=True)
    published = [fab_dir / zipped.name, fab_dir / "bom.csv", fab_dir / "cpl.csv"]
    for src, dst in zip((zipped, bom, cpl), published):
        shutil.copyfile(src, dst)
    return published


def export_step(pcb: Path, step: Path) -> None:
    step.parent.mkdir(parents=True, exist_ok=True)
    kicad_env.run_cli("pcb", "export", "step", *STEP_ARGS, "-o", step, pcb)


@dataclass
class BuildResult:
    sch: Path
    pcb: Path
    written: list[Path]       # every KiCad project file the generator owns (what to commit)
    fab: list[Path]           # the JLC upload files published into the project's `fab` folder
    unplaced: list[str]
    hand_edges: list[str]     # UUIDs of Edge.Cuts items not from layout.yaml (kept)
    erc: Counter              # (severity, violation type) -> count
    drc: Counter
    edges_replaced: bool = False  # the board's generated Edge.Cuts differed from layout.yaml
    step: Path | None = None      # the STEP model, when exported (--step)

    def errors(self, routed: bool) -> int:
        """ERC errors plus DRC errors; unrouted connections only count once `routed`."""
        return (sum(n for (sev, _), n in self.erc.items() if sev == "error")
                + sum(n for (sev, kind), n in self.drc.items()
                      if sev == "error" and (routed or kind != UNROUTED)))


def build(src_dir: Path, build_dir: Path, board: str, step: bool = False) -> BuildResult:
    """Run every step for the design in `src_dir`; exports go to `build_dir`/<board>*, the JLC
    upload files also to the project's `fab` folder, and with `step` the STEP model to its `step`
    file."""
    design = load_design(src_dir)
    if step and design.step_file is None:
        raise DesignError(["project.yaml: --step needs `step` (the STEP file to write)"])
    libs = upgrade_libraries(design, build_dir / "kicad-lib")
    sch, written = build_schematic(design, libs)
    netlist = build_dir / f"{board}.net"
    kicad_env.run_cli("sch", "export", "netlist", "--format", "kicadsexpr", "-o", netlist, sch)
    pcb, layout = build_board(design, libs, netlist)
    erc = run_erc(sch, build_dir / f"{board}-erc.json")
    drc = run_drc(pcb, build_dir / f"{board}-drc.json")
    fab = export_fab(sch, pcb, build_dir, board, design.fab_dir)
    if step:
        export_step(pcb, design.step_file)
    return BuildResult(sch, pcb, [*written, pcb], fab, layout.unplaced, layout.hand_edges, erc, drc,
                       layout.edges_replaced, design.step_file if step else None)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("board", choices=sorted(BOARDS))
    ap.add_argument("--routed", action="store_true",
                    help="treat unrouted connections as DRC errors (after routing)")
    ap.add_argument("--step", action="store_true",
                    help="also export the board's STEP model (project.yaml `step`) for the enclosure")
    args = ap.parse_args(argv)
    try:
        res = build(BOARDS[args.board], REPO / "build", args.board, step=args.step)
    except DesignError as e:
        print("design source problems:\n" + "\n".join(f"  {p}" for p in e.problems))
        return 2
    print(f"schematic: {res.sch.relative_to(REPO)}\nboard:     {res.pcb.relative_to(REPO)}")
    if res.unplaced:
        print("no placement entry (kept or parked beside the board): " + ", ".join(res.unplaced))
    if res.edges_replaced:
        print("Edge.Cuts outline/cutouts replaced from layout.yaml (they differed on the board): "
              "expected after editing layout.yaml; an outline edited in KiCad is lost, so copy "
              "such an edit into layout.yaml `board`")
    if res.hand_edges:
        print(f"Edge.Cuts items drawn in KiCad, kept (move them into layout.yaml): "
              f"{len(res.hand_edges)}")
    _print_counts("ERC", res.erc)
    _print_counts("DRC", res.drc)
    print(f"exports:   build/{args.board}.net, -bom.csv, -cpl.csv, -gerbers/, .dsn, -erc.json, "
          "-drc.json")
    if res.fab:
        print(f"fab:       {res.fab[0].parent.relative_to(REPO).as_posix()}/: "
              + ", ".join(p.name for p in res.fab))
    if res.step:
        print(f"step:      {res.step.relative_to(REPO).as_posix()}")
    return 1 if res.errors(args.routed) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
