"""Specctra DSN export and SES import for Freerouting. Runs in KiCad's bundled Python.

    <KiCad python> tools/hw/kicad_dsn.py BOARD.kicad_pcb OUT.dsn
    <KiCad python> tools/hw/kicad_dsn.py --import-ses BOARD.kicad_pcb IN.ses

build.py runs the export (it finds KiCad's Python, see kicad_env.py). The import adds the routed
tracks and vias of a Freerouting session to the board and saves it, as KiCad's "Import Specctra
Session" does; rebuild afterwards (tools/hw/build.py) so the board is in the generator's normal form.
These are the only code paths that need `pcbnew`; everything else in the pipeline is plain Python.
kicad-cli has neither a DSN export nor an SES import.
"""
import sys

import pcbnew


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[0] == "--import-ses":
        board = pcbnew.LoadBoard(argv[1])
        if not pcbnew.ImportSpecctraSES(board, argv[2]):
            print(f"ImportSpecctraSES failed for {argv[2]}")
            return 1
        pcbnew.SaveBoard(argv[1], board)
        return 0
    if len(argv) != 2:
        print(__doc__)
        return 2
    board = pcbnew.LoadBoard(argv[0])
    if not pcbnew.ExportSpecctraDSN(board, argv[1]):
        print(f"ExportSpecctraDSN failed for {argv[0]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
