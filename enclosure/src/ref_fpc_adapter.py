"""ref_fpc_adapter: placeholder for the airQ's 24-pin 0.5 mm FPC-to-FFC adapter.

The owner chose an adapter at the panel's tail end, behind the panel, and an FFC from it to J7
(2026-11-26, option b: interface.yaml `mechanical.main.fpc.airq_fit`, hardware/README.md
"E-ink FPC fit (airQ)"). No part is chosen yet, so this is a parametric placeholder for a
typical adapter board: about 20 x 12 mm with a 24-pin 0.5 mm ZIF connector at each end, mouths
facing out. EVERY size here is to confirm against the part bought; change the parameters.
The ZIF body size defaults to J7's (24-pin 0.5 mm, 15.5 wide x 5.4 deep x 2.0 high, the main
board's FPC connector: interface.yaml `mechanical.main.fpc` comment).

Frame: origin at the centre of the board's bottom face; x across the board (20 mm), y along the
signal path (12 mm): the panel tail enters ZIF "tail" from -y, the FFC enters ZIF "ffc" from +y;
z up from the bottom face, the connectors on top.

Bodies: fpc_adapter_pcb, fpc_adapter_zif_tail, fpc_adapter_zif_ffc.
"""
from __future__ import annotations

from sclib import Script

DESIGN = "ref_fpc_adapter"
OUTPUT = "reference/fpc-adapter.sc"

TC = "placeholder, to confirm on the part bought"


def build() -> Script:
    s = Script(DESIGN)
    p = s.param
    p("pcb_w", 20.0, f"board across the signal path; {TC}", favorite=True)
    p("pcb_l", 12.0, f"board along the signal path; {TC}", favorite=True)
    p("pcb_t", 1.0, f"board thickness; {TC}")
    p("zif_w", 15.5, f"ZIF body width (J7's, interface.yaml main.fpc); {TC}")
    p("zif_d", 5.4, f"ZIF body depth, mouth to back (J7's); {TC}")
    p("zif_h", 2.0, f"ZIF body height (J7's); {TC}")
    p("zif_in", 0.0, f"ZIF mouth inside the board edge; {TC}")
    p("zif_x", 0.0, f"ZIF centre off the board centre, along x; {TC}")
    s.box("Adapter PCB", ["-pcb_w / 2", "-pcb_l / 2", 0], ["pcb_w", "pcb_l", "pcb_t"],
          body="fpc_adapter_pcb")
    s.box("ZIF tail", ["zif_x - zif_w / 2", "zif_in - pcb_l / 2", "pcb_t"], ["zif_w", "zif_d", "zif_h"],
          body="fpc_adapter_zif_tail")
    s.box("ZIF ffc", ["zif_x - zif_w / 2", "pcb_l / 2 - zif_in - zif_d", "pcb_t"],
          ["zif_w", "zif_d", "zif_h"], body="fpc_adapter_zif_ffc")
    return s
