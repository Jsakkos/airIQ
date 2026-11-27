"""airq_face: the airQ's shell face (Plan 3 Task 3b-1): window, panel pocket, LED slot, dot and flexure.

Everything here is a shell feature (or a part that rides in the shell). Positions are the face
parameters that `airq.py` fixed in 3a (panel_x0, panel_s0, led_f0, dot_f, ...); this module adds the
sizes the features need and cuts them. Face frame: x as the world, s up the slope from the crease
(z = lip), t into the case from the slope's outer surface (R3, `enclosure_common`).
"""
from __future__ import annotations

import math

import board_sources as B
import enclosure_common as C
import ref_epd
from sclib import Script

MAIN = B.MAIN


def slope_plane(s: Script) -> dict:
    """The sketch plane parallel to the face: x along the world x, y up the slope. The origin is
    the world origin, so a point at slope distance `sv` is at y = sv + lip * cos_t, and an offset
    of `lip * sin_t - t` is the plane `t` deep behind the face (as `enclosure_common.panel_pocket`)."""
    return {"origin": [0, 0, 0], "x_dir": [1, 0, 0], "y_dir": [0, s.v("sin_t"), s.v("cos_t")]}


def ys(sv: str) -> str:
    """Sketch y of the slope distance `sv` (an expression)."""
    return f"({sv}) + lip * cos_t"


def toff(t: str) -> str:
    """Sketch plane offset of the plane `t` deep behind the face (t negative: in front of it)."""
    return f"lip * sin_t - ({t})"


def face_pt(s: Script, x: float, sv: float, t: float = 0.0) -> list[float]:
    """World point of face coordinates (x, s, t), for edge picks."""
    sn, c, lip = s.v("sin_t"), s.v("cos_t"), s.v("lip")
    return [x, sv * sn + t * c, lip + sv * c - t * sn]


def window_params(s: Script) -> None:
    """The screen window: the panel's active area (ref_epd aa_*), 66.90 x 29.06, 3.00 from the far
    end and 3.82 from the long edges, with a crisp chamfer on its outer edge."""
    epd = ref_epd.build().v
    p = s.param
    p("aa_w", epd("aa_w"), "panel active area along the length (ref_epd aa_w)")
    p("aa_h", epd("aa_h"), "panel active area across (ref_epd aa_h)")
    p("aa_far", epd("aa_far"), "active area to the end away from the tail (ref_epd aa_far)")
    p("aa_edge", epd("aa_edge"), "active area to each long edge (ref_epd aa_edge)")
    p("win_x0", "panel_x0 + panel_l - aa_far - aa_w", "screen window: the active area's tail-side edge, x")
    p("win_x1", "win_x0 + aa_w", "screen window: far-side edge, x")
    p("win_s0", "panel_s0 + aa_edge", "screen window: lower edge, up the slope from the crease")
    p("win_s1", "win_s0 + aa_h", "screen window: upper edge")
    p("win_chamfer", 0.5, "screen window: chamfer on the outer edge (bezel is 1.0, so 0.5 leaves a 0.5 land at the panel)")


def window(s: Script) -> None:
    """The screen window through the bezel over the active area, then its crisp chamfer."""
    with s.sketch("Window outline", slope_plane(s), offset=toff("-1")) as sk:
        sk.rect("win_x0", ys("win_s0"), "win_x1", ys("win_s1"))
    s.extrude("Window", "Window outline", "bezel + 1 + 0.5", operation="cut", targets=["shell"], direction="negative")
    v = s.v
    xm, sm = (v("win_x0") + v("win_x1")) / 2, (v("win_s0") + v("win_s1")) / 2
    picks = [face_pt(s, xm, v("win_s0")), face_pt(s, xm, v("win_s1")),
             face_pt(s, v("win_x0"), sm), face_pt(s, v("win_x1"), sm)]
    s.chamfer("Window chamfer", picks, "win_chamfer", body="shell")
