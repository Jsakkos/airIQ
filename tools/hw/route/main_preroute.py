"""Main board, routing step 1: the rule areas and the hand-routed critical nets, written into
hardware/kicad/main/airq-main.kicad_pcb before Freerouting routes the rest (route_main.sh).

    uv run python tools/hw/route/main_preroute.py hardware/kicad/main/airq-main.kicad_pcb

THIS SCRIPT HARD-CODES THE CURRENT MAIN-BOARD LAYOUT: every coordinate below is a pad or a free spot of
the placement in hardware/src/main/layout.yaml as of the owner-gate round (2026-11-25). Move a part and
the matching lines here must be redrawn by hand. It is an authoring record (how the committed routing was
made), not part of the build.

Like routing drawn in KiCad, what it writes is board-owned: tools/hw/build.py keeps it on every rebuild
(hardware/README.md, regeneration contract). Run it only from route_main.sh, on an unrouted board
(route_main.sh runs `cleanup.py unroute` first); its items carry uuid5 names (boarditems.Items,
namespace below). Coordinates: mm from the board's top-left corner.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boarditems import Items, circle  # noqa: E402

PCB = sys.argv[1]
out = Items("3b1f6c2e-9d4a-4e8b-a1c7-5e2d8f9a0b31", "main-preroute")
track, via, keepout = out.track, out.via, out.keepout

DP, DN = "USB_DP", "USB_DN"
P5, G, P33 = "+5V", "GND", "+3V3"
SW, BST, FB = "/power/BUCK_SW", "/power/BUCK_BST", "/power/BUCK_FB"
CC1, CC2 = "/power/USB_CC1", "/power/USB_CC2"

# ---- rule areas -----------------------------------------------------------------------------
# ESP32-C6-WROOM-1 antenna keep-out (Espressif hardware design guidelines, "Keepout zone", lib README):
# the 6.0 mm antenna strip (module y -6.0..0, over the rear edge) extended >= 15 mm away from the feed
# point (-X, to x 26) and 2 mm past the feed-point side (+X), plus 0.5 mm of board inside the rear edge.
# No copper of any kind, no pour, on both layers.
keepout("ANTENNA_KEEPOUT", [(26.0, -6.0), (61.0, -6.0), (61.0, 0.5), (26.0, 0.5)],
        tracks=False, vias=False, pads=False, pour=False, footprints=True)
# Under the module's on-board body (x 41..59, up to its bottom end at y 19.51): the bottom layer stays
# ground (RF ground under the module and the path for its heat from the EPAD's thermal vias). No B.Cu
# tracks; the module's signals leave on F.Cu (below). Vias are allowed for the ground stitching.
keepout("U3_NO_BOTTOM_TRACKS", [(41.0, 0.5), (59.0, 0.5), (59.0, 19.51), (41.0, 19.51)], layers=("B.Cu",),
        tracks=False, vias=True, pads=True, pour=True)
# The module's west half (EPAD and the pin-1..14 side): no top tracks either, so the top pour around the
# EPAD stays whole. The signal lanes from the pin-15..27 column run east of it and below it (y >= 18.75).
keepout("U3_EPAD_TOP", [(42.4, 0.5), (51.0, 0.5), (51.0, 18.3), (42.4, 18.3)], layers=("F.Cu",),
        tracks=False, vias=True, pads=True, pour=True)
# USB-C receptacle body (metal shell on the top surface): no top tracks and no vias under it.
keepout("J1_SHELL", [(11.6, 0.0), (20.8, 0.0), (20.8, 6.6), (11.6, 6.6)], layers=("F.Cu", "B.Cu"),
        tracks=True, vias=False, pads=True, pour=True)
keepout("J1_SHELL_TOP", [(11.6, 0.0), (20.8, 0.0), (20.8, 6.6), (11.6, 6.6)], layers=("F.Cu",),
        tracks=False, vias=False, pads=True, pour=True)
# SKRTLAE010 land pattern: "prohibited area of copper tracks" between the mounting tabs (Alps).
keepout("SW1_NO_COPPER", [(56.0, 28.2), (58.0, 28.2), (58.0, 29.7), (56.0, 29.7)], layers=("F.Cu",),
        tracks=False, vias=False, pads=True, pour=False)
# M2 screw heads (3.8 mm) and standoffs: no tracks or vias within 2.2 mm of the hole centres.
for name, (cx, cy) in (("H1_SCREW", (8.55, 2.6)), ("H2_SCREW", (57.4, 22.8))):
    keepout(name, circle(cx, cy, 2.2), tracks=False, vias=False, pads=True, pour=True)

# ---- buck (TPS562201, U2 at 24.6, 3.4): hot loop C1 - VIN - GND on the top layer -------------
track(P5, [(25.95, 2.45), (27.75, 2.45)], 0.6)               # VIN pin 3 -> C1 +
track(G, [(25.95, 4.35), (27.75, 4.35)], 0.6)                # GND pin 1 -> C1 -
track(SW, [(25.95, 3.4), (29.8, 3.4)], 0.5)                  # SW pin 2 -> L1, between C1's pads
track(P5, [(25.4, 8.08), (26.8, 7.3)], 0.3)                  # C3 (100 nF) + -> C2 +
track(G, [(25.4, 7.12), (24.6, 7.12)], 0.3)                  # C3 - -> via
via(G, 24.6, 7.12)
for x in (26.2, 27.4, 28.2):                                 # GND pin / C1 - to the bottom plane
    track(G, [(x, 4.35), (x, 5.1)], 0.4)
    via(G, x, 5.1)
track(BST, [(23.25, 4.35), (23.25, 5.4), (23.85, 6.0), (24.12, 6.0)], 0.25)   # VBST -> C4
track(SW, [(25.95, 3.4), (25.05, 3.4), (25.05, 5.7), (25.08, 6.0)], 0.3)       # SW pin 2 -> C4 (short stub)
track(P33, [(32.9, 4.6), (33.45, 5.4), (33.45, 6.85), (33.45, 8.85)], 0.6)    # L1 -> C5, C6
for y in (6.85, 8.85):                                       # C5 -, C6 - to the bottom plane
    track(G, [(31.55, y), (30.6, y)], 0.4)
    via(G, 30.6, y)
track(FB, [(22.86, 0.95), (23.25, 0.95), (23.74, 0.95)], 0.25)              # FB node: R4 - R3 - pin 4
track(FB, [(23.25, 0.95), (23.25, 2.45)], 0.25)
# output sense for R3 (FB top): from L1's output pad on B.Cu along the rear edge
track(P33, [(24.76, 0.95), (25.6, 1.2)], 0.25)
via(P33, 25.6, 1.2)
track(P33, [(25.6, 1.2), (34.25, 1.2), (34.25, 2.0)], 0.25, "B.Cu")
via(P33, 34.25, 2.0)
track(P33, [(34.25, 2.0), (33.4, 2.0)], 0.25)

# ---- USB-C (J1) D+/D- fan-out, ESD (U1) and the pair to the module ----------------------------
# J1 pads (y 7.38): D+ B6 15.45, A6 16.45; D- A7 15.95, B7 16.95. U1 rows y 11.85 / 14.15:
# pin 6 D+ 15.25, pin 4 D- 17.15 (top); pin 1 D+ 15.25, pin 3 D- 17.15 (bottom).
track(DP, [(15.45, 7.38), (15.45, 9.2), (15.25, 9.4), (15.25, 11.85)])        # B6 -> U1 pin 6
track(DN, [(16.95, 7.38), (16.95, 8.4), (17.1, 8.55), (17.1, 10.4), (17.1, 11.5), (17.15, 11.85)])  # B7 -> pin 4
track(DN, [(15.95, 7.38), (15.95, 8.4), (15.85, 8.5), (15.85, 10.4), (17.1, 10.4)])   # A7 -> B7
track(DP, [(16.45, 7.38), (16.45, 8.4), (16.5, 8.45), (16.5, 9.6)])           # A6 -> via V1
via(DP, 16.5, 9.6)
# A6 (D+) crosses under A7 (D-) on B.Cu and comes up beside U1 pin 6, so both D+ contacts enter the
# ESD part's flow-through input (pin 6) and leave from pin 1, as D- does (pins 4 -> 3)
track(DP, [(16.5, 9.6), (16.5, 10.0), (14.65, 11.85)], 0.2, "B.Cu")
via(DP, 14.65, 11.85)
track(DP, [(14.65, 11.85), (15.25, 11.85)], 0.2)
track(CC2, [(14.45, 7.38), (14.45, 9.12)], 0.2)                               # CC2 -> R2
track(G, [(14.45, 10.08), (14.45, 10.75)], 0.3)
via(G, 14.45, 10.75)
track(CC1, [(17.45, 7.38), (17.45, 8.15), (18.29, 8.99), (18.29, 9.5)])       # CC1 -> R1
track(G, [(19.4, 7.415), (19.4, 8.6), (19.28, 8.75), (19.28, 9.5)], 0.3)      # GND A12 -> R1 -
track(G, [(19.4, 7.415), (19.97, 7.2), (20.52, 6.83)], 0.3)                  # GND A12 -> shell leg
track(G, [(13.0, 7.415), (12.43, 7.2), (11.88, 6.83)], 0.3)                  # GND B12 -> shell leg
track(P5, [(13.8, 7.4), (13.8, 9.5), (13.48, 9.9), (13.48, 10.9)], 0.3)       # VBUS B9 -> C7 +
track(P5, [(18.6, 7.4), (18.6, 8.45)], 0.3)                                    # VBUS A9 -> via
via(P5, 18.6, 8.45)
track(P5, [(16.2, 11.85), (16.2, 13.0)], 0.25)                               # U1 VBUS pin 5
via(P5, 16.2, 13.0)                                                          # (under U1's body)
track(P5, [(16.2, 13.0), (17.8, 11.4), (18.6, 10.6), (18.6, 8.45)], 0.4, "B.Cu")
# USB VBUS to the buck input: B.Cu trunk from J1's A9 via, up to VIN (pin 3) and over to C2
track(P5, [(18.6, 8.45), (21.5, 8.45), (26.0, 8.45)], 0.5, "B.Cu")
track(P5, [(21.5, 8.45), (22.5, 7.45), (22.5, 4.75), (22.5, 4.4), (24.9, 2.0)], 0.5, "B.Cu")
via(P5, 22.1, 4.75)                                                           # R5 (EN pull-up) +5V
track(P5, [(22.1, 4.75), (22.5, 4.75)], 0.5, "B.Cu")
track(P5, [(22.1, 4.75), (21.9, 4.2), (21.9, 3.91)], 0.3)
via(P5, 24.9, 2.0)
track(P5, [(24.9, 2.0), (25.35, 2.45), (25.95, 2.45)], 0.5)
via(P5, 26.0, 8.45)
track(P5, [(26.0, 8.45), (26.8, 7.65), (26.8, 7.3)], 0.5)
track(G, [(16.2, 14.15), (16.2, 15.0)], 0.25)                                 # U1 GND pin 2
via(G, 16.2, 15.0)
# VBUS B9 and its 1 uF (C7) to the rest of +5V: down past U1's D+ input and between U1's pin rows to
# its VBUS via (main_postfix.py moves the crossing under U1 to B.Cu once the routing is done)
track(P5, [(13.48, 10.9), (13.48, 13.0), (16.2, 13.0)], 0.3)
# the pair, east along y 15.2 (D-) / 15.65 (D+), then into U3 pins 13 (IO12, D-) and 14 (IO13, D+).
# D+ starts 1.9 mm further west and ends on the lower pin: two 0.79 mm bumps on D- match the lengths
# (U1 pin 1 -> U3 pin 14 and U1 pin 3 -> U3 pin 13: 29.85 mm each)
track(DN, [(17.15, 14.15), (17.7, 14.15), (17.7, 15.2), (34.0, 15.2), (34.0, 14.41), (34.8, 14.41),
           (34.8, 15.2), (35.6, 15.2), (35.6, 14.41), (36.4, 14.41), (36.4, 15.2), (38.85, 15.2),
           (38.85, 16.74), (41.25, 16.74)])
track(DP, [(15.25, 14.15), (15.25, 15.65), (38.4, 15.65), (38.4, 18.01), (41.25, 18.01)])

# ---- module supply and reset: C8 (10 uF) and C9 (100 nF) right at pins 1/2, EN RC -------------
track(P33, [(38.0, 3.25), (38.5, 2.78), (39.6, 2.78), (40.1, 2.76), (41.25, 2.76)], 0.4)
track(G, [(38.0, 1.35), (38.15, 1.5), (39.6, 1.5), (41.25, 1.5)], 0.4)
track(G, [(39.6, 1.5), (39.6, 1.82)], 0.4)
track(P33, [(38.79, 4.6), (38.3, 4.11), (38.0, 3.75), (38.0, 3.25)], 0.3)   # R6 (EN pull-up)
track("EN", [(39.81, 4.6), (40.38, 4.03), (41.25, 4.03)], 0.25)
track("EN", [(39.81, 4.6), (39.5, 4.91), (39.5, 5.825)], 0.25)             # C10 (EN delay)

# ---- module signal lanes (F.Cu): the pin-15..27 column sits 0.5 mm from the right edge, so its signals
# leave west under the module, turn down in lanes east of the EPAD (x 51.3.., 0.4 mm pitch) and come
# out below its bottom end, the top pin in the westmost lane, so nothing crosses. Below the module the
# lanes widen with 45-degree jogs (each lower lane jogs further east and further, so no two lanes run
# diagonally side by side) to their final heights, where each ends on a via just west of the module:
# LED_DATA and the aux UART (Freerouting takes them on from there) and the e-ink SPI (its layer change,
# below). BUTTON goes down the east side to R11 and SW1.
LANES = [("LED_DATA", 2.76), ("AUX_UART_TX", 5.30), ("AUX_UART_RX", 6.58),
         ("EPD_BUSY", 10.38), ("EPD_RST", 11.65), ("EPD_DC", 12.92), ("EPD_CS", 14.20), ("EPD_CLK", 15.47),
         ("EPD_MOSI", 16.74)]                         # (net, module pad y), top to bottom; pads at x 58.75
END = [(39.6, 18.75), (40.2, 19.35), (39.6, 19.95)] + [(40.9 if j % 2 else 40.0, 20.85 + 0.6 * j)
                                                      for j in range(6)]   # via of each lane
for k, (net, py) in enumerate(LANES):
    lx, ly = 51.3 + 0.4 * k, 18.75 + 0.45 * k         # lane x; height at which it turns west
    vx, vy = END[k]
    jog = 42.0 + 0.6 * k
    track(net, [(58.75, py), (lx, py), (lx, ly), (jog, ly), (jog - (vy - ly), vy), (vx, vy)])
    via(net, vx, vy)
track("BUTTON", [(58.75, 18.0), (54.95, 18.0), (54.95, 25.6), (57.01, 25.6), (57.01, 27.3)])   # -> SW1 pin 2
track("BUTTON", [(54.95, 23.1), (54.36, 23.1)])                                                 # R11 (pull-up)

# ---- a starting branch for BUTTON towards J6 pin 6 (the unfitted aux header, middle-left): under the
# e-ink lanes just below the module and up north of the via columns (clear of the module's B.Cu
# keep-out, x < 41). Freerouting may re-route it: in the committed routing it ran BUTTON from R11
# instead (the same way, past the via columns at x 40.7) and the clean-up dropped this branch. It stays
# because the routing below was made with it (Freerouting's result depends on its whole input).
track("BUTTON", [(54.95, 20.15), (55.15, 20.15)])
via("BUTTON", 55.15, 20.15)
track("BUTTON", [(55.15, 20.15), (40.8, 20.15), (40.8, 17.6)], 0.2, "B.Cu")

# ---- e-ink SPI into the FPC (J7 pins 9..14 = BUSY, RST, DC, CS, CLK, MOSI at x 30.55 .. 28.05) -------
# The module's pin order is the FPC's mirrored, so the bus changes layer once, outside the module: from
# the via columns at x 40.0 / 40.9 it runs on B.Cu west (y 20.85..23.85), down between the FPC and D3
# (x 35.0..37.25), west along the front edge under the FPC body (y 27.05..29.3) and up into a via row
# there (y 26.5); a short F.Cu fan joins those vias to the pads.
for j, (net, _) in enumerate(LANES[3:]):
    vx, sy = END[3 + j]
    down_x, lane_y, fx = 35.0 + 0.45 * j, 27.05 + 0.45 * j, 31.8 - j
    px = 28.8 + 5.75 - (9 + j - 1) * 0.5              # FPC pad centre x (J7 at 28.8, pin 1 at +5.75)
    track(net, [(vx, sy), (down_x, sy), (down_x, lane_y), (fx, lane_y), (fx, 26.5)], 0.2, "B.Cu")
    via(net, fx, 26.5)
    track(net, [(px, 24.5), (px, 25.35), (fx, 26.5)], 0.2)

# ---- LED data: U5's output through the 33 R series resistor R14 into D1 DIN ---------------------------
track("/leds_button/LED_DATA_5V", [(12.8, 24.15), (11.5, 24.15), (11.5, 25.39), (10.6, 25.39)])
track("/leds_button/LED_DIN_1", [(10.6, 26.41), (10.6, 27.0), (10.8, 27.2), (10.8, 28.65)])

# ---- LEDs: each 100 nF straight onto its LED's VDD pad, ground vias at the cap and the LED ----
for lx in (12.6, 17.7, 39.9, 45.0):
    cx = lx - 0.45
    track(P5, [(cx, 26.88), (cx, 28.63)], 0.3)
    track(G, [(cx, 25.92), (cx, 25.1)], 0.3)
    via(G, cx, 25.1)
    track(G, [(lx + 1.8, 28.63), (lx + 1.8, 27.2)], 0.4)
    via(G, lx + 1.8, 27.2)

# ---- e-ink VGH: D5 (cathode) to its tank cap C25 between C24 and C25, and on to FPC pin 21 ----------
VGH = "/epd/EPD_VGH"
track(VGH, [(25.3, 16.6), (25.3, 19.3), (24.0, 20.6), (24.0, 22.675), (23.2, 22.675)])
track(VGH, [(24.0, 22.675), (24.0, 23.3), (24.55, 23.85), (24.55, 24.5)])

# ---- e-ink boost input cap C19 at L2, its ground with R12/R13 (RESE / GDR pull-downs) ---------
track(P33, [(37.1, 16.65), (35.5, 16.65)], 0.4)
track(G, [(37.1, 18.55), (37.1, 19.3), (36.9, 19.5), (36.9, 20.175)], 0.4)
track(G, [(36.9, 20.175), (38.6, 20.175)], 0.4)
track(G, [(37.1, 19.3), (37.75, 19.3)], 0.4)
via(G, 37.75, 19.3)                                        # between the long B.Cu runs (above)

# ---- FPC pin 8 (GND) sits between e-ink pins: a via for it, clear of the fan and of C21
track(G, [(31.05, 24.5), (31.05, 23.45), (31.8, 23.45)])
via(G, 31.8, 23.45)
# and FPC pin 17 (GND) between pins 16 and 18: a via under the FPC body, beside the e-ink fan
track(G, [(26.55, 24.5), (26.55, 25.7)])
via(G, 26.55, 25.7)

print(f"wrote {out.save(PCB)} items")
