"""Export a board to a Specctra DSN file for Freerouting. Runs in KiCad's bundled Python.

    <KiCad python> tools/hw/kicad_dsn.py BOARD.kicad_pcb OUT.dsn

build.py runs it (it finds KiCad's Python, see kicad_env.py). It only calls pcbnew; everything
else in the pipeline is plain Python. kicad-cli has no DSN export.
"""
import sys

import pcbnew


def main(argv: list[str]) -> int:
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
