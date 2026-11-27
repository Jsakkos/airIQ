"""ref_epd: the GoodDisplay GDEY029T94 2.9" e-paper panel with its FPC tail, flat or folded.

Sources:
- the tail (length, widths, offset, root, contacts, stiffener) is read from hardware/interface.yaml
  `mechanical.main.fpc.panel_tail`, recorded there from GoodDisplay "GDEY029T94 Product
  Specifications" Rev 1.0 (2021/03/15), section 4 "Mechanical Drawing of EPD module" (p. 7);
- the outline, active area, view area, tail thicknesses and the 9.56 mm narrow length are read
  from the same drawing as Waveshare prints it for this panel (identical tail and pin-out, see
  interface.yaml `connectors.J_EPD`): Waveshare "2.9inch e-Paper V2 Specification" Rev 2.1
  (2020/02/10), section 1.3 "Mechanical Specifications" (p. 4) and section 1.4 "Mechanical
  Drawing of EPD module" (p. 5, front and side views);
- the thickness 1.2 mm is the specification's ("36.7(H)x79.0(V)x1.2(T)", Waveshare section 1.3;
  GoodDisplay's product page: "79x36.7x1.2"); the side view dimensions the panel 1.1 +-0.1.

Frame: x along the 79.0 mm length, x = 0 at the short end the tail leaves, +x away from it; y
along the 36.7 mm width, y = 0 at the pin-24 long edge, +y toward the pin-1 long edge; z = 0 at
the panel's back, +z toward the viewer (display side). This is the drawing's front view (display
toward you, tail on the left, pin 1 at the top) with z out of the page. The tail leaves toward -x.

Bodies: epd_panel (the active area cut out of its face by `aa_depth`), epd_active_area (fills
that pocket: its top face is the active area), epd_tail_block (the drawing's unlabelled hatched
block at the tail end; scaled, to confirm), and the tail in one of two states, chosen by the
parameter `tail_folded` (configuration rows `flat` and `folded`; the rules switch the features
when the parameter alone changes):
- flat (0, as drawn): epd_tail (narrow part, flare, full-width root; contacts on +z),
  epd_tail_stiffener (on the back, -z), epd_tail_contacts (24 contacts, on the display side);
- folded (1): the tail turns 180 deg back under the panel, bending only in the 8.2 mm next to
  the glass (the stiffened 6.2 mm cannot bend): epd_tail_folded (flat run `fold_out`, a
  half-turn of inner radius `fold_r`, then back under the panel; the bent part is modelled at
  the root's full width, an envelope of the root and flare), epd_tail_folded_stiffener (now on
  the side facing the panel) and epd_tail_folded_contacts (now facing -z, away from the panel).
"""
from __future__ import annotations

from sclib import Script, mechanical

DESIGN = "ref_epd"
OUTPUT = "reference/epd-2.9.sc"

GD = "GoodDisplay GDEY029T94 spec Rev 1.0 s.4 p.7 via interface.yaml panel_tail"
WS = "Waveshare 2.9in e-Paper V2 spec Rev 2.1 s.1.4 p.5"
TC = "to confirm"

FLAT = ["Tail flat", "Stiffener flat", "Contacts flat"]
FOLDED = ["Fold upper leg", "Fold bend", "Fold lower leg", "Fold stiffened end",
          "Stiffener folded", "Contacts folded"]


def tail_yaml() -> dict:
    return mechanical("main")["fpc"]["panel_tail"]


def build() -> Script:
    t = tail_yaml()
    n_contacts, pitch, contact_len = t["contacts"]
    s = Script(DESIGN)
    p = s.param
    p("panel_l", 79.0, f"outline length ({WS})", favorite=True)
    p("panel_w", 36.7, f"outline width ({WS})", favorite=True)
    p("panel_t", 1.2, "thickness: spec 1.2 (Waveshare s.1.3; GoodDisplay page 79x36.7x1.2); "
                      f"side view 1.1 +-0.1 ({WS})", favorite=True)
    p("aa_w", 66.90, f"active area along the length ({WS})")
    p("aa_h", 29.06, f"active area across ({WS}; GoodDisplay page 29.056)")
    p("aa_far", 3.00, f"active area to the end away from the tail ({WS})")
    p("aa_edge", 3.82, f"active area to the pin-24 long edge; 3.82 to the pin-1 edge too ({WS})")
    p("va_w", 67.50, f"view area along the length, for the window ({WS})")
    p("va_h", 29.66, f"view area across, for the window ({WS})")
    p("va_far", 2.70, f"view area to the end away from the tail ({WS})")
    p("va_edge", 3.52, f"view area to each long edge ({WS})")
    p("aa_depth", 0.1, "depth of the active-area marker body into the face (model only)")
    p("aa_x0", "panel_l - aa_far - aa_w", "derived: active area from the tail end")

    p("tail_len", t["length"], f"outline to finger end ({GD})")
    p("tail_w", t["width"], f"narrow part width ({GD})")
    p("tail_offset", t["offset"], f"narrow part centre toward the pin-24 edge ({GD})")
    p("narrow_len", 9.56, f"narrow part length from the finger end ({WS}; {GD} comment)")
    p("root_w", t["root"]["width"], f"root width ({GD})")
    p("root_from_end", t["root"]["from_finger_end"], f"full width from here to the outline ({GD})")
    p("root_gap", t["root"]["edge_gaps"][0], f"root to the pin-24 long edge ({GD})")
    p("contact_n", n_contacts, f"contacts ({GD})", unit="")
    p("contact_pitch", pitch, f"contact pitch ({GD})")
    p("contact_len", contact_len, f"contact length from the finger end ({GD})")
    p("stiff_len", t["stiffener"], f"stiffener from the finger end, on the back ({GD})")
    p("tail_t", 0.10, f"flex thickness, +-0.03 ({WS} side view)")
    p("stiff_t", 0.20, f"stiffener: 0.3 +-0.03 total at the finger end less the flex ({WS} side view)")
    p("tail_z", 0.6, f"tail back face above the panel back, scaled from the side view ({WS}); {TC}")
    p("contact_t", 0.05, "thickness of the contact marker body (model only)")
    p("narrow_y0", "panel_w / 2 - tail_offset - tail_w / 2", "derived: narrow part from the pin-24 edge")
    p("root_len", "tail_len - root_from_end", "derived: full-width root outside the glass")
    p("flare_x", "tail_len - narrow_len", "derived: where the narrow part starts, from the outline")
    p("contact_span", "contact_n * contact_pitch", "derived: width of the contact row")
    p("contact_y0", "narrow_y0 + (tail_w - contact_span) / 2", "derived: contact row from the pin-24 edge")

    p("block_out", 4.6, f"hatched block reach past the outline, scaled ({GD}; hardware/README); {TC}")
    p("block_y0", 2.3, f"hatched block from the pin-1 long edge, scaled ({GD}); {TC}")
    p("block_y1", 7.4, f"hatched block to, from the pin-1 long edge, scaled ({GD}); {TC}")
    p("block_t", "panel_t", f"hatched block thickness: not given, taken as the panel's; {TC}")

    p("tail_folded", 0, "0: tail flat as drawn (airQ mini); 1: folded 180 deg behind the panel "
                        "(airQ, interface.yaml fpc.airq_fit). Whole number, 0 or 1", unit="", favorite=True)
    p("fold_out", 0.5, f"folded: flat run past the outline before the bend, 0.2 .. 1.5; {TC}")
    p("fold_r", 1.0, f"folded: inner bend radius, 0.5 .. 1.5 (the lower leg must stay under z = 0); {TC}")
    p("fold_angle", 180, "folded: the tail turns back under the panel (interface.yaml fpc.airq_fit "
                         "tail_fold). 180 deg only: fold_low and the legs after the bend assume a half turn",
      unit="deg")
    p("flex_len", "tail_len - stiff_len", "derived: the part that can bend (8.2 mm)")
    p("fold_low", "flex_len - fold_out - pi * (fold_r + tail_t / 2)",
      "derived: flexible length left under the panel after the bend")
    p("fold_z", "tail_z - 2 * fold_r", "derived: folded lower leg's face toward the panel")

    # panel and active area
    s.box("Panel", [0, 0, 0], ["panel_l", "panel_w", "panel_t"], body="epd_panel")
    s.box("Active area pocket", ["aa_x0", "aa_edge", "panel_t - aa_depth"],
          ["aa_w", "aa_h", "2 * aa_depth"], operation="cut", targets=["epd_panel"])
    s.box("Active area", ["aa_x0", "aa_edge", "panel_t - aa_depth"], ["aa_w", "aa_h", "aa_depth"],
          body="epd_active_area")
    s.box("Hatched block", ["-block_out", "panel_w - block_y1", 0],
          ["block_out", "block_y1 - block_y0", "block_t"], body="epd_tail_block")

    # flat tail, as drawn
    with s.sketch("Tail outline", "XY", offset="tail_z") as sk:
        sk.polyline([("-tail_len", "narrow_y0"), ("-flare_x", "narrow_y0"),
                     ("-root_len", "root_gap"), (0, "root_gap"),
                     (0, "root_gap + root_w"), ("-root_len", "root_gap + root_w"),
                     ("-flare_x", "narrow_y0 + tail_w"), ("-tail_len", "narrow_y0 + tail_w")])
    s.extrude("Tail flat", "Tail outline", "tail_t", body="epd_tail")
    s.box("Stiffener flat", ["-tail_len", "narrow_y0", "tail_z - stiff_t"],
          ["stiff_len", "tail_w", "stiff_t"], body="epd_tail_stiffener")
    s.box("Contacts flat", ["-tail_len", "contact_y0", "tail_z + tail_t"],
          ["contact_len", "contact_span", "contact_t"], body="epd_tail_contacts")

    # folded tail: flat run, half-turn down and back, then under the panel
    s.box("Fold upper leg", ["-fold_out", "root_gap", "tail_z"], ["fold_out", "root_w", "tail_t"],
          body="epd_tail_folded")
    # the section's plane faces -x (sketch x = world z, sketch y = world y), so the revolve
    # (which turns the way the sketch normal points) carries it outward, then down and back
    with s.sketch("Fold bend section", {"origin": [0, 0, 0], "x_dir": [0, 0, 1], "y_dir": [0, 1, 0]},
                  offset="fold_out") as sk:
        sk.rect("tail_z", "root_gap", "tail_z + tail_t", "root_gap + root_w")
    s.revolve("Fold bend", "Fold bend section", ["-fold_out", 0, "tail_z - fold_r"], [0, 1, 0],
              "fold_angle", operation="join", targets=["epd_tail_folded"])
    s.box("Fold lower leg", ["-fold_out", "root_gap", "fold_z - tail_t"],
          ["fold_low", "root_w", "tail_t"], operation="join", targets=["epd_tail_folded"])
    s.box("Fold stiffened end", ["fold_low - fold_out", "narrow_y0", "fold_z - tail_t"],
          ["stiff_len", "tail_w", "tail_t"], operation="join", targets=["epd_tail_folded"])
    s.box("Stiffener folded", ["fold_low - fold_out", "narrow_y0", "fold_z"],
          ["stiff_len", "tail_w", "stiff_t"], body="epd_tail_folded_stiffener")
    s.box("Contacts folded",
          ["fold_low - fold_out + stiff_len - contact_len", "contact_y0", "fold_z - tail_t - contact_t"],
          ["contact_len", "contact_span", "contact_t"], body="epd_tail_folded_contacts")

    s.configuration("tail_folded", {"flat": ("0", FOLDED), "folded": ("1", FLAT)}, default="flat")
    return s
