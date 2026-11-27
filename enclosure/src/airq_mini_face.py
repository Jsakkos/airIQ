"""airq_mini_face: the airQ mini's face (Plan 3 Task 4b): the split light band, its labels, the dot.

Everything here is a shell feature or a part that rides in the shell. Positions are the face
parameters `airq_mini.face_params` fixed in 4a (band_*, d1_x ... d4_x, led_z, label_*, sw_*,
dot_*); this module adds the sizes the features need and builds them. Face frame (as
`airq_face`): x as the world, s up the slope from the crease (z = lip), t into the case from the
slope's outer surface.

The band (spec section 6.5): two slots through the face wall, `light_guide_co2` over D1/D2 (left)
and `light_guide_pm` over D3/D4 (right). In the mini the LEDs stand 3 mm behind the face wall's
inner face, level with the band (the band's centre line is the LEDs' light centre carried
horizontally to the face, 4a `led_f`), so each guide is a short clear block: light from a LED
crosses the 0.2 gap (clr_remove), enters a foot's entry face in front of it, and runs straight
(horizontally) or by total internal reflection at the guide's bare faces to the exit face in the
slot. Each guide is three prisms along x: the bar (the tongue in the slot, the flange behind the
wall that keeps it from going out of the front, the body behind it) and two feet that reach back
from the body to the entry plane in front of their LEDs.

Opaque parts round them (shell material or black foam, never in optical contact with a guide: air
gaps of clr_align all round):
- ribs of the shell (`Band rib divider`, `Band rib left`, `Band rib right`): fins from the face
  wall's inner face back to the stop, at the halves' ends. The divider fills the visible gap
  between the halves (no straight path of air or light between the guides, `airq_mini_check`);
- `guide_stop` (black closed-cell foam, adhesive, bought): a strip stuck on the three ribs' back
  faces, behind both bars, windows round the four feet. It keeps the guides in their slots
  (retention: each guide is caught between the wall and the stop with clr_align each way) and
  stops every straight line from a guide's back to the MS5611 (U4, R13).
"""
from __future__ import annotations

import airq_face as F
import board_sources as B
from sclib import Script

LEDS = (("co2", (1, 2)), ("pm", (3, 4)))           # guide half -> its LEDs (interface.yaml leds.chain halves)


def guide_params(s: Script) -> None:
    """The guides' sizes and the opaque parts' (named; each fit is a clr_* parameter)."""
    p = s.param
    p("led_face_w", B.led_body_w(), "LED light face width (interface.yaml leds comment, board_sources)")
    p("led_face_h", B.led_body_h(), "LED light face height (interface.yaml leds comment)")
    p("lg_tg", "clr_align", "light guide: the tongue's clearance in its slot, each side and at each end (located part)")
    p("lg_rec", "clr_remove + 0.1", "light guide: the exit face's recess behind the face's outer surface (the airQ's gd_rec)")
    p("lg_s0", "band_f0 - lip + lg_tg", "light guide: the tongue's lower side, up the slope from the crease")
    p("lg_s1", "band_f1 - lip - lg_tg", "light guide: the tongue's upper side")
    p("lg_tf", "wall + clr_align", "light guide: the flange's front face, clr_align behind the face wall's inner face (it keeps the guide from going out of the front)")
    p("lg_lap", 0.6, "light guide: the flange's lap on the wall's inner face below the slot, along the slope")
    p("lg_z0", "lip + (lg_s0 - lg_lap) * cos_t - lg_tf * sin_t", "light guide: the body's bottom (horizontal), lg_lap down the flange from the tongue's lower side")
    p("lg_z1", "led_z + led_face_h / 2", "light guide: the body's top (horizontal), level with the LED faces' top edge")
    p("lg_ye", "board_y0 - clr_remove", "light guide: the feet's entry faces (vertical), clr_remove in front of the LED faces")
    p("stop_t", 1.2, "guide_stop: foam thickness along y (>= 1.2 opaque)")
    p("lg_ysf", "lg_ye - stop_t", "guide_stop: front face (on the ribs' back faces); its back face is the entry plane, clr_remove in front of the board's edge and the LEDs")
    p("lg_yb", "lg_ysf - clr_align", "light guide: the bar's back face, clr_align in front of the stop")
    p("lg_mz", 0.2, "light guide feet: inside the LED faces' top and lower edges by this much (a line from a foot toward U4 enters the LED body)")
    p("lg_xm", 0.6, "light guide feet: each starts this far inside its LED face's tail-side (-x) edge: U4 lies to -x, and a line from a foot's back toward it drifts that way by up to 1.64 per mm of y (D4)")
    p("lg_xp", 0.2, "light guide feet: each stops this far inside its LED face's far (+x) edge")
    p("lg_fz0", "led_z - led_face_h / 2 + lg_mz", "light guide feet: bottom")
    p("lg_fz1", "led_z + led_face_h / 2 - lg_mz", "light guide feet: top")
    for _, leds in LEDS:
        for i in leds:
            p(f"lg_f{i}_x0", f"d{i}_x - led_face_w / 2 + lg_xm", f"light guide foot in front of D{i}: tail-side (-x) face")
            p(f"lg_f{i}_x1", f"d{i}_x + led_face_w / 2 - lg_xp", f"light guide foot in front of D{i}: far (+x) face")
    p("end_rib_t", 1.2, "band end ribs: thickness (>= 1.2 opaque), beyond each half's outer end")
    p("rib_z0", "lg_z0 - 0.4", "band ribs and guide_stop: bottom, under the guides' bottom")
    p("rib_tin", "wall - 0.5", "band ribs: their front edge runs 0.5 inside the face wall (joined)")
    p("stop_z1", "lg_z1 + 0.4", "guide_stop: top, over the guides' top")
    p("stop_x0", "band_co2_x0 - end_rib_t", "guide_stop: left end (the left end rib's outer face)")
    p("stop_x1", "band_pm_x1 + end_rib_t", "guide_stop: right end (the right end rib's outer face)")


# --- geometry helpers: (s, t) points from world lines, as expressions ---------------------------

def st_yz(y: str, z: str) -> tuple[str, str]:
    """(s, t) of the world point (y, z)."""
    return f"({y}) * sin_t + (({z}) - lip) * cos_t", f"({y}) * cos_t - (({z}) - lip) * sin_t"


def st_tz(t: str, z: str) -> tuple[str, str]:
    """(s, t) of the point at depth t on the horizontal plane z."""
    return f"((({z}) - lip) + ({t}) * sin_t) / cos_t", t


def bar_profile() -> list[tuple[str, str]]:
    """The bar's (s, t) profile: the exit face (edge 0), the tongue's upper side, the flange's front
    over the slot, the body's top, back and bottom, the flange's front under the slot, the tongue's
    lower side."""
    return [("lg_s0", "lg_rec"), ("lg_s1", "lg_rec"), ("lg_s1", "lg_tf"), st_tz("lg_tf", "lg_z1"),
            st_yz("lg_yb", "lg_z1"), st_yz("lg_yb", "lg_z0"), st_tz("lg_tf", "lg_z0"), ("lg_s0", "lg_tf")]


def foot_profile() -> list[tuple[str, str]]:
    """A foot's (s, t) profile: a rectangle in (y, z) from 0.1 inside the bar's back to the entry
    plane (edge 1), between the feet's bottom and top."""
    yb = "lg_yb - 0.1"
    return [st_yz(yb, "lg_fz0"), st_yz("lg_ye", "lg_fz0"), st_yz("lg_ye", "lg_fz1"), st_yz(yb, "lg_fz1")]


def rib_profile() -> list[tuple[str, str]]:
    """A band rib's (y, z) profile: from inside the face wall (t = rib_tin) back to the stop's front
    face (y = lg_ysf), from rib_z0 up to where the stop's front plane meets the wall."""
    return [(f"(rib_tin + (rib_z0 - lip) * sin_t) / cos_t", "rib_z0"), ("lg_ysf", "rib_z0"),
            ("lg_ysf", "lip + (lg_ysf * cos_t - rib_tin) / sin_t")]


def guide_pieces() -> list[tuple[str, str, str, str, str]]:
    """The guides' pieces as built: (feature, body, profile key, x0, x1), one source for the build and
    the checks (`airq_mini_check`)."""
    out = []
    for half, leds in LEDS:
        body = f"light_guide_{half}"
        out.append((f"Guide {half} bar", body, "bar", f"band_{half}_x0 + lg_tg", f"band_{half}_x1 - lg_tg"))
        for i in leds:
            out.append((f"Guide {half} foot D{i}", body, "foot", f"lg_f{i}_x0", f"lg_f{i}_x1"))
    return out


PROFILES = {"bar": bar_profile, "foot": foot_profile}


def band_slots(s: Script) -> None:
    """The two band slots through the face wall (perpendicular to the face), each half's visible length."""
    for half in ("co2", "pm"):
        with s.sketch(f"Band slot {half} outline", F.slope_plane(s), offset=F.toff("-1")) as sk:
            sk.rect(f"band_{half}_x0", F.ys("band_f0 - lip"), f"band_{half}_x1", F.ys("band_f1 - lip"))
        s.extrude(f"Band slot {half}", f"Band slot {half} outline", "wall + 1 + 0.2", operation="cut", targets=["shell"],
                  direction="negative")


def rib_spans() -> dict:
    """{rib: (x0, x1)}: the divider fills the visible gap between the halves; the end ribs stand
    beyond each half's outer end."""
    return {"divider": ("band_co2_x1", "band_pm_x0"), "left": ("band_co2_x0 - end_rib_t", "band_co2_x0"),
            "right": ("band_pm_x1", "band_pm_x1 + end_rib_t")}


def band_ribs(s: Script) -> None:
    """The divider and the two end ribs, joined to the shell's face wall."""
    for name, (x0, x1) in rib_spans().items():
        with s.sketch(f"Band rib {name} profile", "YZ", offset=x0) as sk:
            sk.polyline(rib_profile())
        s.extrude(f"Band rib {name}", f"Band rib {name} profile", f"({x1}) - ({x0})", operation="join", targets=["shell"])


def light_guides(s: Script) -> None:
    """`light_guide_co2` and `light_guide_pm`: clear PETG, every face bare (no coat, no cladding, no
    adhesive on the guide)."""
    seen = set()
    for name, body, key, x0, x1 in guide_pieces():
        with s.sketch(f"{name} profile", "YZ", offset=x0) as sk:
            sk.polyline([F.yz(sv, tv) for sv, tv in PROFILES[key]()])
        if body in seen:
            s.extrude(name, f"{name} profile", f"({x1}) - ({x0})", operation="join", targets=[body])
        else:
            s.extrude(name, f"{name} profile", f"({x1}) - ({x0})", body=body)
            seen.add(body)


def stop_windows() -> list[tuple[str, str, str, str]]:
    """The stop's windows round the feet: (x0, x1, z0, z1), clr_align round each foot."""
    out = []
    for _, leds in LEDS:
        for i in leds:
            out.append((f"lg_f{i}_x0 - clr_align", f"lg_f{i}_x1 + clr_align", "lg_fz0 - clr_align", "lg_fz1 + clr_align"))
    return out


def guide_stop(s: Script) -> None:
    """`guide_stop`: black closed-cell foam (adhesive-backed, bought, die-cut), stuck on the three ribs'
    back faces behind both bars; the feet pass its windows."""
    s.box("Guide stop", ["stop_x0", "lg_ysf", "rib_z0"], ["stop_x1 - stop_x0", "stop_t", "stop_z1 - rib_z0"], body="guide_stop")
    for k, (x0, x1, z0, z1) in enumerate(stop_windows(), 1):
        s.box(f"Guide stop window {k}", [x0, "lg_ysf - 0.5", z0], [f"({x1}) - ({x0})", "stop_t + 1", f"({z1}) - ({z0})"],
              operation="cut", targets=["guide_stop"])


def label_params(s: Script) -> None:
    """The labels' layout. The built-in font's own subscript two is 0.58 of the cap height: at 5 mm its
    strokes are about 0.40, at the 0.4 nozzle's limit, so the CO2 label's subscript is a plain "2" at
    label_sub_h (strokes about 0.48), dropped under the baseline. Widths of the built-in font, measured
    on solidcraft-cli 0.50.0 text outlines: "CO" 2.04 x its cap height, "2" 0.664 x."""
    p = s.param
    p("label_sub_h", 3.5, "the CO2 label's subscript 2: its cap height (strokes about 0.136 x this, 0.48 mm, above the 0.4 nozzle)")
    p("label_sub_drop", 1.0, "the subscript's baseline under the label's baseline")
    p("label_sub_gap", 0.4, "gap between the label's O and its subscript")
    p("label_co_w", "2.04 * label_h", "width of 'CO' in the built-in font (measured: 2.04 x the cap height)")
    p("label_sub_w", "0.664 * label_sub_h", "width of '2' in the built-in font (measured: 0.664 x the cap height)")
    p("label_co_x", "label_co2_x - (label_sub_gap + label_sub_w) / 2", "'CO' centre x: the label with its subscript centred under the CO2 half")
    p("label_sub_x", "label_co_x + label_co_w / 2 + label_sub_gap + label_sub_w / 2", "the subscript's centre x")


def labels(s: Script) -> None:
    """`label_debossing`: "CO2" (a subscript 2) under the left half and "PM2.5" under the right,
    debossed label_depth into the face, label_h tall (the Task 2 coupon: >= 5 mm reads at 0.4 deep)."""
    with s.sketch("Label debossing sketch", F.slope_plane(s), offset=F.toff("0")) as sk:
        sk.text("CO", ("label_co_x", F.ys("label_f0 - lip")), "label_h")
        sk.text("2", ("label_sub_x", F.ys("label_f0 - lip - label_sub_drop")), "label_sub_h")
        sk.text("PM2.5", ("label_pm_x", F.ys("label_f0 - lip")), "label_h")
    s.extrude("Label debossing", "Label debossing sketch", "label_depth", operation="cut", targets=["shell"], direction="negative")


def band_x_check(v) -> dict:
    """Numbers the build relies on: the right end rib against the flexure's slot, the guides' fits."""
    return {"rib_to_flex": v("flex_x0 - flex_slot") - v("band_pm_x1 + end_rib_t"),
            "face_to_flex": v("flex_x0 - flex_slot") - v("band_pm_x1")}

