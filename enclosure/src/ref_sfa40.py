"""ref_sfa40: the SparkFun "Formaldehyde Sensor - SFA40 (Qwiic)" breakout (SEN-31669).

Sources:
- board, holes, sensor and connector positions: SparkFun's KiCad layout,
  github.com/sparkfun/SparkFun_Qwiic_Formaldehyde_Sensor_SFA40, Hardware/
  SparkFun_Qwiic_Formaldehyde_Sensor_SFA40.kicad_pcb at commit 181b793 (2026-09-22): Edge.Cuts
  rectangle (123.266, 85.406)-(148.666, 110.806), U3 (SFA40) at (135.966, 98.106) turned 90 deg,
  J1/J2 (Qwiic) at (143.9035 | 128.0285, 98.106) turned +-90 deg, standoffs ST1-ST4 (3.1 mm
  holes) 2.54 mm in from each corner; the same numbers as its product drawing
  (docs/static/ref/SparkFun_Qwiic_Formaldehyde_Sensor_SFA40.png: 1 x 1 in, holes 0.1 in in);
- the sensor and its opening: Sensirion "SFA40 Datasheet" Version 1.1 (April 2026), section
  4.2 "Package Outline", Figure 6 (p. 14): 13 x 10 mm PCB, 0.8 thick; metal cap 10.05 x 8.45,
  1.59 high; the opening (membrane) 7.2 x 3.8, its edge 4.15 from the PCB edge on the marking
  side. Pin 1 (dot) and SparkFun's pad 1 sit on the same corner, which puts the opening 1.05 mm
  toward the J2 (-x) side of the board centre;
- the Qwiic connectors (JST SM04B-SRSS-TB) use the body this repository measured for the same
  part on the main board (interface.yaml `mechanical.main.j_qwiic_tongue.body`: 6.0 x 4.95,
  2.9 high); their mating face, 0.52 mm inside the board edge, is derived from SparkFun's pads
  and the JST body (to confirm on a real board).

Frame: the PCB references' STEP frame: origin at the board's top-left corner as SparkFun's
layout draws it (KiCad grid, +Y down), x = X - 123.266, y = -(Y - 85.406), z = 0 at the board's
bottom face; so the board spans x 0..25.4, y -25.4..0, and the parts sit on its top (z = 1.6).
J2 is at the -x edge, J1 at the +x edge; the 4-pin 0.1" header row (not fitted) is at the
bottom (-y) edge.

Bodies: sfa40_board (with its four holes), sfa40_sensor (PCB and cap; the opening cut out of
the cap top by `opening_depth`), sfa40_opening (fills that pocket: its top face is the
opening), sfa40_qwiic_j1, sfa40_qwiic_j2. Not modelled: the 0603 parts, LED and jumpers
(under 1 mm).
"""
from __future__ import annotations

from sclib import Script, mechanical

DESIGN = "ref_sfa40"
OUTPUT = "reference/sfa40-breakout.sc"

SF = "SparkFun SFA40 kicad_pcb 181b793"
SN = "SFA40 Datasheet v1.1 (Apr 2026) Fig. 6"
TC = "to confirm"


def build() -> Script:
    qw = mechanical("main")["j_qwiic_tongue"]["body"]       # [[x0, y0], [x1, y1]], same JST part
    qwiic_w, qwiic_d = qw[1][0] - qw[0][0], qw[1][1] - qw[0][1]
    s = Script(DESIGN)
    p = s.param
    p("board_w", 25.4, f"board width, 1 in ({SF}; product drawing)", favorite=True)
    p("board_h", 25.4, f"board height, 1 in ({SF}; product drawing)", favorite=True)
    p("board_t", 1.6, f"board thickness ({SF} general/thickness)")
    p("hole_d", 3.1, f"mounting hole diameter, non-plated ({SF} Standoff pads)")
    p("hole_in", 2.54, f"hole centres from each edge, 0.1 in ({SF}; product drawing)")
    p("sensor_x", 12.7, f"SFA40 centre from the left edge ({SF} U3)")
    p("sensor_y", 12.7, f"SFA40 centre below the top edge ({SF} U3)")
    p("sensor_l", 13.0, f"SFA40 PCB length, +-0.3, along the board's y ({SN})")
    p("sensor_w", 10.0, f"SFA40 PCB width, +-0.3, along the board's x ({SN})")
    p("sensor_t", 0.8, f"SFA40 PCB thickness, +-0.2 ({SN})")
    p("cap_l", 10.05, f"metal cap length, +-0.3 ({SN})")
    p("cap_w", 8.45, f"metal cap width, +-0.3 ({SN})")
    p("cap_h", 1.59, f"metal cap height above the SFA40 PCB, +-0.2 ({SN})")
    p("opening_l", 7.2, f"opening length, +-0.3, along the board's y ({SN})")
    p("opening_w", 3.8, f"opening width, +-0.3, along the board's x ({SN})")
    p("opening_gap", 4.15, f"opening edge to the SFA40 PCB edge on the marking (+x) side, +-0.3 ({SN})")
    p("opening_depth", 0.1, "depth of the opening marker body into the cap (model only)")
    p("qwiic_w", qwiic_w, "Qwiic connector body width (interface.yaml main.j_qwiic_tongue, same JST part)")
    p("qwiic_d", qwiic_d, "Qwiic connector body depth (interface.yaml main.j_qwiic_tongue, same JST part)")
    p("qwiic_h", 2.9, "Qwiic connector height (interface.yaml main.j_qwiic_tongue comment; "
                      "hardware/kicad/lib/README.md fix 12)")
    p("qwiic_in", 0.52, f"Qwiic mating face inside the board edge, from SparkFun's pads; {TC}")
    p("qwiic_y", 12.7, f"Qwiic connector centres below the top edge ({SF} J1, J2)")
    p("sensor_top", "board_t + sensor_t + cap_h", "derived: top of the SFA40 cap")

    s.box("Board", [0, "-board_h", 0], ["board_w", "board_h", "board_t"], body="sfa40_board")
    for name, (x, y) in {"Hole top left": ("hole_in", "-hole_in"),
                         "Hole top right": ("board_w - hole_in", "-hole_in"),
                         "Hole bottom left": ("hole_in", "hole_in - board_h"),
                         "Hole bottom right": ("board_w - hole_in", "hole_in - board_h")}.items():
        s.cylinder(name, [x, y, "-board_t"], "hole_d", "3 * board_t", operation="cut",
                   targets=["sfa40_board"])
    s.box("Sensor PCB", ["sensor_x - sensor_w / 2", "-sensor_y - sensor_l / 2", "board_t"],
          ["sensor_w", "sensor_l", "sensor_t"], body="sfa40_sensor")
    s.box("Sensor cap", ["sensor_x - cap_w / 2", "-sensor_y - cap_l / 2", "board_t + sensor_t"],
          ["cap_w", "cap_l", "cap_h"], operation="join", targets=["sfa40_sensor"])
    opening = ["sensor_x + sensor_w / 2 - opening_gap - opening_w", "-sensor_y - opening_l / 2"]
    s.box("Opening pocket", [*opening, "sensor_top - opening_depth"],
          ["opening_w", "opening_l", "2 * opening_depth"], operation="cut", targets=["sfa40_sensor"])
    s.box("Opening", [*opening, "sensor_top - opening_depth"],
          ["opening_w", "opening_l", "opening_depth"], body="sfa40_opening")
    s.box("Qwiic J1", ["board_w - qwiic_in - qwiic_d", "-qwiic_y - qwiic_w / 2", "board_t"],
          ["qwiic_d", "qwiic_w", "qwiic_h"], body="sfa40_qwiic_j1")
    s.box("Qwiic J2", ["qwiic_in", "-qwiic_y - qwiic_w / 2", "board_t"],
          ["qwiic_d", "qwiic_w", "qwiic_h"], body="sfa40_qwiic_j2")
    return s
