"""Main board, routing step 3: the GND pours (both layers, whole board) and the ground stitching vias,
written into hardware/kicad/main/airq-main.kicad_pcb (board-owned items, kept by every rebuild).

    uv run python tools/hw/route/main_pour.py BOARD [x,y ...]

The vias come from the command line as x,y pairs (mm from the board's top-left corner), found by
stitch.py. Re-runnable: it first removes what it wrote before (boarditems.Items, uuid5 namespace below).
Hard-codes the main board's 60 x 30 mm outline. Not part of the build.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boarditems import Items  # noqa: E402

BOARD = [(0, 0), (60, 0), (60, 30), (0, 30)]


def main(argv: list[str]) -> int:
    pcb, vias = argv[0], [tuple(float(v) for v in a.split(",")) for a in argv[1:]]
    out = Items("7c4e2a91-1f3b-4d6e-8a5c-2b9d0e6f4a73", "main-pour")
    for layer, name in (("F.Cu", "GND_TOP"), ("B.Cu", "GND_BOTTOM")):
        out.pour("GND", layer, name, BOARD)
    for x, y in vias:
        out.via("GND", x, y)
    print(f"wrote {out.save(pcb)} items")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
