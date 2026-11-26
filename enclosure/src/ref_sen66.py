"""ref_sen66: the Sensirion SEN66 module, with its two air inlets and its air outlet as bodies.

Source: Sensirion "SEN6x - Datasheet", Version 1.0 (October 2026), section 5.1 "Package
Outline", Figure 8 (p. 56), all dimensions in mm; which openings are inlets and which the outlet:
Sensirion "SEN6x - Mechanical Design and Assembly Guidelines", Version 0.9 (December 2024),
Figure 1 "SEN6x package overview" (p. 2).

Frame (the datasheet's own datums, so every number below is the drawing's): x along the
55.2 mm length from the inlet end (x = 0) to the outlet end; y across the 25.6 mm width from
the edge nearer the square inlet (y = 0); z through the 21.3 mm height from the port face
(z = 0) to the connector face. All three ports open in the z = 0 face and face -z; the cable
connector is on the opposite face (datasheet Figure 9, not dimensioned).

Bodies: sen66_body (the module, ports cut out of its z = 0 face by `port_depth`), sen66_inlet
(both inlets, one body of two pieces) and sen66_outlet, which fill those pockets: their outer
faces are the port faces, flush with the module face. Not modelled: the recesses in the long
sides and the ends (the body is their envelope), the 0.3/0.5 mm edge rounds, the snap pockets.
"""
from __future__ import annotations

import math

from sclib import Script

DESIGN = "ref_sen66"
OUTPUT = "reference/sen66.sc"

DS = "SEN6x Datasheet v1.0 (Oct 2026) Fig. 8"


def build() -> Script:
    s = Script(DESIGN)
    p = s.param
    p("L", 55.2, f"length, +0.2/-0.4 ({DS})", favorite=True)
    p("W", 25.6, f"width, +0.1/-0.2 ({DS})", favorite=True)
    p("H", 21.3, f"height port face to connector face, +-0.5 ({DS})", favorite=True)
    p("block_h", 19.3, f"main block height, +-0.3; the rest is the plinth on the connector face ({DS})")
    p("plinth_inset", 1.2, f"plinth inset all round, +0.1/-0.2 ({DS})")
    p("r_inlet_end", 2.8, f"plan corner radius at the inlet end, 2x ({DS})")
    p("r_outlet_end", 4.3, f"plan corner radius at the outlet end, 2x ({DS})")
    p("inlet_sq_x0", 3.2, f"square inlet x from, +-0.1 ({DS})")
    p("inlet_sq_x1", 10.2, f"square inlet x to, +-0.1 ({DS})")
    p("inlet_sq_y0", 2.8, f"square inlet y from, +-0.1 ({DS})")
    p("inlet_sq_y1", 9.8, f"square inlet y to, +-0.1 ({DS})")
    p("inlet_rd_x", 6.7, f"round inlet centre x, +-0.1 ({DS})")
    p("inlet_rd_y", 18.2, f"round inlet centre y, +-0.2 ({DS})")
    p("inlet_rd_d", 6.0, f"round inlet diameter, +-0.2 ({DS})")
    p("outlet_x", 42.4, f"outlet (fan) centre x, +-0.3 ({DS})")
    p("outlet_y", 12.8, f"outlet (fan) centre y, +-0.2 ({DS})")
    p("outlet_d", 20.5, f"outlet (fan) diameter, +-0.3 ({DS})")
    p("port_depth", 0.5, "depth of the port marker bodies into the module face (model only, not a datasheet value)")

    L, W, H, bh, i = (s.v(n) for n in ("L", "W", "H", "block_h", "plinth_inset"))

    s.box("Body block", [0, 0, 0], ["L", "W", "block_h"], body="sen66_body")
    s.fillet("Block corners inlet end", [[0, 0, bh / 2], [0, W, bh / 2]], "r_inlet_end", body="sen66_body")
    s.fillet("Block corners outlet end", [[L, 0, bh / 2], [L, W, bh / 2]], "r_outlet_end", body="sen66_body")
    # the plinth is rounded on its own first: its square corner would stand 0.08 mm outside
    # the block's R4.3 corner, so it is filleted concentric with the block before the join
    s.box("Plinth", ["plinth_inset", "plinth_inset", "block_h"],
          ["L - 2 * plinth_inset", "W - 2 * plinth_inset", "H - block_h"], body="sen66_plinth")
    zp = (bh + H) / 2
    s.fillet("Plinth corners inlet end", [[i, i, zp], [i, W - i, zp]],
             "r_inlet_end - plinth_inset", body="sen66_plinth")
    s.fillet("Plinth corners outlet end", [[L - i, i, zp], [L - i, W - i, zp]],
             "r_outlet_end - plinth_inset", body="sen66_plinth")
    s.combine("Plinth on block", "sen66_body", ["sen66_plinth"])

    # port pockets (cutters start port_depth outside the face) and the port bodies filling them
    s.box("Square inlet pocket", ["inlet_sq_x0", "inlet_sq_y0", "-port_depth"],
          ["inlet_sq_x1 - inlet_sq_x0", "inlet_sq_y1 - inlet_sq_y0", "2 * port_depth"],
          operation="cut", targets=["sen66_body"])
    s.cylinder("Round inlet pocket", ["inlet_rd_x", "inlet_rd_y", "-port_depth"], "inlet_rd_d",
               "2 * port_depth", operation="cut", targets=["sen66_body"])
    s.cylinder("Outlet pocket", ["outlet_x", "outlet_y", "-port_depth"], "outlet_d",
               "2 * port_depth", operation="cut", targets=["sen66_body"])
    s.box("Square inlet", ["inlet_sq_x0", "inlet_sq_y0", 0],
          ["inlet_sq_x1 - inlet_sq_x0", "inlet_sq_y1 - inlet_sq_y0", "port_depth"], body="sen66_inlet")
    s.cylinder("Round inlet", ["inlet_rd_x", "inlet_rd_y", 0], "inlet_rd_d", "port_depth",
               operation="join", targets=["sen66_inlet"])
    s.cylinder("Outlet", ["outlet_x", "outlet_y", 0], "outlet_d", "port_depth", body="sen66_outlet")
    return s


def port_areas(s: Script | None = None) -> dict[str, float]:
    """Port face areas in mm^2 from the drawing (gross openings: the outlet's is the whole
    20.5 mm circle, fan hub and spokes included)."""
    s = s or build()
    v = s.v
    square = (v("inlet_sq_x1") - v("inlet_sq_x0")) * (v("inlet_sq_y1") - v("inlet_sq_y0"))
    round_ = math.pi * v("inlet_rd_d") ** 2 / 4
    return {"inlet_square": square, "inlet_round": round_, "inlet": square + round_,
            "outlet": math.pi * v("outlet_d") ** 2 / 4}


def expected_volume(s: Script | None = None) -> float:
    """Volume of sen66_body + sen66_inlet + sen66_outlet (the port bodies refill the pockets)."""
    s = s or build()
    v = s.v
    L, W, H, bh, i = v("L"), v("W"), v("H"), v("block_h"), v("plinth_inset")
    ra, rb = v("r_inlet_end"), v("r_outlet_end")
    k = 2 * (1 - math.pi / 4)               # area lost by two filleted plan corners, per r^2
    block = (L * W - k * (ra ** 2 + rb ** 2)) * bh
    plinth = ((L - 2 * i) * (W - 2 * i) - k * ((ra - i) ** 2 + (rb - i) ** 2)) * (H - bh)
    return block + plinth
