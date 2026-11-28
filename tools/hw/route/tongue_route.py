"""Sense tongue: its whole routing, written into hardware/kicad/tongue/airq-tongue.kicad_pcb.

    uv run python tools/hw/route/tongue_route.py hardware/kicad/tongue/airq-tongue.kicad_pcb
    uv run --with pyyaml python tools/hw/build.py tongue --routed

THIS SCRIPT HARD-CODES THE TONGUE'S LAYOUT (hardware/src/tongue/layout.yaml, Task 4): every coordinate
is a pad of that placement. It is an authoring record (how the committed routing was made), not part of
the build. Equivalent to routing by hand in KiCad: the items it writes (tracks, vias, the B.Cu ground pour
and the SHT45_ISOLATION rule area) are board-owned, so tools/hw/build.py keeps them on every rebuild.
Re-runnable: it first removes what it wrote before (boarditems.Items, uuid5 namespace below).
Coordinates: mm from the board's top-left corner.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boarditems import Items, poly  # noqa: E402

PCB = sys.argv[1]
W = 0.2                                 # track width (mm): thin, so the island's neck conducts little heat
SDA, SCL, VDD, GND = "/sense/I2C_SDA", "/sense/I2C_SCL", "+3V3", "GND"
out = Items("5a1d7f0e-2b8c-4d1e-9f3a-7c6b5e4d3a21", "tongue-route")
via = out.via


def track(net: str, pts, layer: str = "F.Cu") -> None:
    out.track(net, pts, W, layer)


# ---- SHT45 island (U1 at 4.5, 4.5; rot 0): pads 1 SDA (3.85, 4.1), 2 SCL (3.85, 4.9),
# 3 VDD (5.15, 4.9), 4 VSS (5.15, 4.1). VSS/VDD leave straight toward the neck, SDA/SCL loop round
# the top/bottom. Neck lines: SDA 3.75, VSS 4.25, VDD 4.75, SCL 5.25 (neck y 3.3..5.7).
track(SDA, [(3.85, 4.1), (3.3, 4.1), (3.3, 3.3), (6.1, 3.3), (6.55, 3.75), (8.75, 3.75), (10.1, 2.4),
            (14.3, 2.4)])
track(SDA, [(14.3, 2.4), (16.15, 2.4), (16.45, 2.1)])            # to U2 pad 4 (SDA)
track(GND, [(5.15, 4.1), (5.5, 4.1), (5.65, 4.25), (9.5, 4.25), (9.73, 4.02), (10.0, 4.02)])  # to C1-2
track(VDD, [(5.15, 4.9), (5.5, 4.9), (5.65, 4.75), (9.5, 4.75), (9.73, 4.98), (10.0, 4.98)])  # to C1-1
track(SCL, [(3.85, 4.9), (3.3, 4.9), (3.3, 5.7), (6.1, 5.7), (6.55, 5.25), (8.75, 5.25), (9.0, 5.5),
            (9.0, 9.3), (9.5, 9.8), (16.0, 9.8), (16.5, 9.3), (16.5, 7.91)])  # under J1's body to J1-4

# ---- body: C1 (10.0, 4.5) rot 90: 1 VDD (10.0, 4.98), 2 GND (10.0, 4.02)
track(GND, [(10.0, 4.02), (10.9, 4.02)])
via(GND, 10.9, 4.02)
track(VDD, [(10.0, 4.98), (10.5, 4.98), (11.05, 5.53), (14.5, 5.53)])
# U2 (18.35, 2.1) rot 0, window -Y: pads 4 SDA (16.45, 2.1), 3 GND (17.72), 2 VDD (18.98),
# 1 SCL (20.25). C2 (18.35, 4.0) rot 180: 1 VDD (18.83, 4.0), 2 GND (17.87, 4.0).
track(VDD, [(14.5, 5.53), (18.83, 5.53), (18.83, 4.0)])          # to C2-1
track(VDD, [(18.83, 4.0), (18.98, 2.1)])                         # C2-1 to U2 pad 2 (VDD)
track(GND, [(17.87, 4.0), (17.72, 2.1)])                         # C2-2 to U2 pad 3 (GND)
track(GND, [(17.87, 4.0), (17.0, 4.0)])
via(GND, 17.0, 4.0)
# J1 (15.0, 9.85) rot 0: 1 GND (13.5, 7.91), 2 +3V3 (14.5), 3 SDA (15.5), 4 SCL (16.5)
track(VDD, [(14.5, 5.53), (14.5, 7.91)])
track(GND, [(13.5, 7.91), (13.5, 6.5)])
via(GND, 13.5, 6.5)
track(SDA, [(15.5, 7.91), (15.5, 6.5)])                          # SDA crosses +3V3 on B.Cu
via(SDA, 15.5, 6.5)
track(SDA, [(15.5, 6.5), (14.3, 5.3), (14.3, 2.4)], "B.Cu")      # via clear of U2's body
via(SDA, 14.3, 2.4)
track(SCL, [(16.5, 7.91), (16.5, 6.8), (20.25, 6.8), (20.25, 2.1)])  # to U2 pad 1 (SCL)

# ---- B.Cu ground pour over the body only (x >= 9.3): none near the SHT45 island
out.raw(f"""\t(zone (net "GND") (layer "B.Cu") (uuid "{{uid}}") (name "GND_B")
\t\t(hatch edge 0.5) (connect_pads (clearance 0.25)) (min_thickness 0.2) (filled_areas_thickness no)
\t\t(fill yes (thermal_gap 0.3) (thermal_bridge_width 0.3) (island_removal_mode 0))
\t\t(polygon (pts {poly([(9.3, 0), (22, 0), (22, 13), (9.3, 13)])})))""")

# ---- rule area: the SHT45 island, its slot and neck, and the frame round them (x < 9.3, y < 8.3).
# No vias and no pours on either layer; tracks and the SHT45's own pads are allowed (a custom rule in
# layout.yaml bans every other part's pads here).
out.raw(f"""\t(zone (layers "F.Cu" "B.Cu") (uuid "{{uid}}") (name "SHT45_ISOLATION")
\t\t(hatch edge 0.5) (connect_pads (clearance 0)) (min_thickness 0.25) (filled_areas_thickness no)
\t\t(keepout (tracks allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))
\t\t(placement (enabled no) (sheetname ""))
\t\t(fill (thermal_gap 0.5) (thermal_bridge_width 0.5))
\t\t(polygon (pts {poly([(0, 0), (9.3, 0), (9.3, 8.3), (0, 8.3)])})))""")

print(f"wrote {out.save(PCB)} items")
