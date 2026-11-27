"""The airQ check design: enclosure/airq.sc with every reference part placed (Task 3a).

`check_script()` returns a command script for `solidcraft-cli run --in enclosure/airq.sc`. It:
- inserts the six references at their places in the layout. ref_main goes only here (R8: it
  adds 5.5 MB);
- sets gasket_squeeze to 0, so the TPU gaskets' faces touch what they seal (R9);
- adds the check bodies, all placed by the design's parameters:
  - `ko_*` keep-outs: the plugs (the SEN66's JST-GH, the Qwiic plugs at the SFA40, the tongue
    and J4, J2's) and the cables' routes through the grommets (review I2: routing room);
  - `air_*` probes: one free section per internal air path (R25). A probe that touches but does
    not overlap anything proves its section is free air; the section is the probe's size;
  - `sweep_*` and `shell_up_*`: the shell's insertion path along -z (review I1): the swept
    columns of its bosses, and copies of the shell raised in steps, with copies of what rides in
    it (`guide_up_*`, `mask_up_*`, `stop_up_*`: SHELL_RIDERS);
- runs the interference check (R9: touching is fine, shared volume is not);
- measures the bodies (the probes' sections);
- sets gasket_squeeze to a small value and checks that each gasket now overlaps what it seals:
  its faces touched at 0 (zero gap, zero overlap);
- saves enclosure/.build/airq-check.sc.

The placement matrices are rigid and proper (det +1). Their translations are parameter
expressions, so the references follow the design's parameters. `distances()` gives the
distances the placements answer, from the generator's values and the boards' sources. Run it all
with `uv run --with pyyaml python enclosure/src/airq_check.py --run`, or through
tests/enclosure/test_airq.py.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import airq
import airq_face as F
import board_sources as B
import enclosure_common as C
import encbuild
import ref_epd
import ref_sen66
import ref_sfa40
from sclib import ENCLOSURE

REF = ENCLOSURE / "reference"
CHECK_SC = encbuild.BUILD_DIR / "airq-check.sc"
REFS = ("ref_sen66", "ref_epd", "ref_fpc_adapter", "ref_sfa40", "ref_tongue", "ref_main")
SHELL_BORNE = ("ref_epd", "ref_fpc_adapter")     # the panel and the adapter are in the shell and come down with it
SWEEP_DZ = (1, 2, 4, 8, 16, 32)                  # the shell's raised copies (mm along +z)
SHELL_RIDERS = (("light_guide", "guide"), ("led_mask", "mask"), ("gap_stop", "stop"))   # bodies that come down with the shell: copies <tag>_up_<dz>
TOUCH_SQUEEZE = 0.05                             # the gaskets overlap their seats by this much when they touch at 0
TOUCHES = (("gasket_out", "sen66_body"), ("gasket_in", "sen66_body"), ("gasket_in", "base_plate"), ("zone_seal", "base_plate"),
           ("sen66_pad", "sen66_body"),
           ("grommet_zone_a", "zone_wall"), ("grommet_zone_b", "zone_wall"), ("grommet_zone_a", "base_plate"),
           ("grommet_zone_b", "base_plate"), ("grommet_j4_a", "base_plate"), ("grommet_j4_b", "base_plate"),
           ("grommet_tongue_a", "hcho_lid"), ("grommet_tongue_b", "hcho_lid"), ("sen66_top_seal", "zone_wall"),
           ("crease_seal", "shell"))
# every squeeze and preload: 0 in the check (R9: faces touch), TOUCH_SQUEEZE in the touch run
SQUEEZES = ("gasket_squeeze", "wiper_squeeze", "pad_squeeze", "ring_preload", "root_squeeze", "grommet_squeeze",
            "drawer_squeeze", "bore_squeeze", "seal_squeeze", "top_seal_squeeze", "crease_squeeze")


def _rows(rot, t):
    """A 3x4 matrix from a 3x3 rotation (rows) and a translation of expressions."""
    return [[*rot[i], t[i]] for i in range(3)]


def placements(s=None) -> list[dict]:
    """insert_design steps for the references, placed by the design's parameters."""
    s = s or airq.build()
    c, sn = s.v("cos_t"), s.v("sin_t")
    slope = lambda sx, tx: (f"({sx}) * sin_t + ({tx}) * cos_t", f"lip + ({sx}) * cos_t - ({tx}) * sin_t")  # noqa: E731
    epd_y, epd_z = slope("panel_s0", "bezel + panel_t")
    ad_y, ad_z = slope("adapter_s", "adapter_t")
    return [
        # SEN66, ports to the rear: module x -> -x (inlet end right), module z (port face -> connector) -> -y,
        # module y -> -z (square inlet high)
        {"path": REF / "sen66.sc", "matrix": _rows([[-1, 0, 0], [0, 0, -1], [0, -1, 0]], ["sen_x1", "sen_y1", "sen_top"])},
        # panel: x -> +x (tail end left), y -> up the slope, z -> the slope's outward normal; tail folded
        {"path": REF / "epd-2.9.sc", "configuration": "folded",
         "matrix": _rows([[1, 0, 0], [0, sn, -c], [0, c, sn]], ["panel_x0", epd_y, epd_z])},
        # adapter: its y (signal path) -> +x, its z (ZIFs) -> toward the panel, x -> down the slope
        {"path": REF / "fpc-adapter.sc", "matrix": _rows([[0, 1, 0], [-sn, 0, -c], [-c, 0, sn]], ["adapter_x", ad_y, ad_z])},
        # SFA40: flat on the floor, opening up; its x (J2 -> J1) -> +y, its y -> -x
        {"path": REF / "sfa40-breakout.sc", "matrix": _rows([[0, -1, 0], [1, 0, 0], [0, 0, 1]], ["sfa_x0", "sfa_y0", "floor_t"])},
        # tongue: turned 180 deg about z, its front edge (VEML7700) toward the lip
        {"path": REF / "airq-tongue.sc", "matrix": _rows([[-1, 0, 0], [0, -1, 0], [0, 0, 1]], ["tongue_x1", "tongue_y0", "tongue_z0"])},
        # main board: STEP frame as it lies (front edge at STEP y -30)
        {"path": REF / "airq-main.sc", "matrix": _rows([[1, 0, 0], [0, 1, 0], [0, 0, 1]], ["board_x0", "board_y0 + board_d", "board_z0"])},
    ]


# --- check bodies (all from the design's parameters) -----------------------------------------
# board-side positions read from interface.yaml (R27), as expressions over the design's names
J2 = B.MAIN["j_sen66"]["body"]
J4 = B.MAIN["j_qwiic_aux"]["body"]
TQ = B.TONGUE["qwiic"]
TQH = B.connector_h("qwiic", board="tongue")
_SFA = ref_sfa40.build().v
_SEN = ref_sen66.build().v
_EPD = ref_epd.build().v
SFA_QW = (f"sfa_x0 + {_SFA('qwiic_y')} - {_SFA('qwiic_w')} / 2", f"sfa_x0 + {_SFA('qwiic_y')} + {_SFA('qwiic_w')} / 2")   # its Qwiic plugs' x span (ref_sfa40)


def _box(name, x0, y0, z0, x1, y1, z1):
    return {"command": "solid.box", "params": {"name": name, "body_name": name, "corner": [x0, y0, z0],
                                               "length": f"({x1}) - ({x0})", "width": f"({y1}) - ({y0})",
                                               "height": f"({z1}) - ({z0})", "operation": "new"}}


def _cyl(name, base, d, h, axis="Z"):
    return {"command": "solid.cylinder", "params": {"name": name, "body_name": name, "base": base, "diameter": d,
                                                    "height": h, "axis": axis, "operation": "new"}}


def keepouts(s) -> list[dict]:
    """The plugs and the cables' routes (I2). The SEN66's connector position and mating direction
    and the plugs' sizes are to confirm: the keep-outs are envelopes, 5 mm plugs out of the
    connector faces with the cable's bend in front."""
    t = lambda tt, z: f"({tt} + ({z} - lip) * sin_t) / cos_t"     # noqa: E731  y at depth tt behind the slope, height z
    mid = "sen_top - sen_up / 2"
    run0, run1 = "pt_yh - cable_gh_d / 2", "pt_yh + cable_gh_d / 2"      # the cables' line through the drawer
    j0, j1 = "j4n_yc - cable_qw_d / 2 - 0.3", "j4n_yc + cable_qw_d / 2 + 0.3"   # the J4 cable's line along the front
    b = []
    # SEN66 plug on its connector face (front), the cable's bend down, the run left, the riser
    b.append(_box("ko_sen66_plug", "plug_x0", "sen_y0 - 6.0", f"{mid} - 2.5", "plug_x1", "sen_y0", f"{mid} + 2.5"))
    b.append(_box("ko_sen66_bend", "plug_x0", "sen_y0 - 6.94", "floor_t", "plug_x1", "sen_y0 - 6.0", f"{mid} + 0.7"))
    b.append(_box("ko_sen66_bend_low", "plug_x0", run0, "floor_t", "plug_x1", "sen_y0 - 6.94", "ledge_z0 + 0.2"))
    b.append(_box("ko_cable_run", "pt_x0", run0, "floor_t", "plug_x0", run1, "floor_t + 3.0"))
    b.append(_box("ko_cable_riser", "pt_x0", run0, "floor_t + 3.0", "qw_x + cable_qw_d / 2", run1, "pt_z0"))
    # through the zone wall's drawer, up the strip behind the folded tail, over the zone wall to J2 and J4
    b.append(_cyl("ko_cable_gh", ["gh_x", "pt_yh", "pt_z0"], "cable_gh_d", "pt_z1 - pt_z0"))
    b.append(_cyl("ko_cable_qwiic", ["qw_x", "pt_yh", "pt_z0"], "cable_qw_d", "pt_z1 - pt_z0"))
    b.append({"command": "sketch.create", "params": {"name": "ko_strip_profile", "plane": "YZ", "offset": "pt_x0"}})
    b.append({"command": "sketch.line", "params": {"closed": True, "points": [
        [t("4.2", "pt_z1"), "pt_z1"], [t("6.9", "pt_z1"), "pt_z1"], [t("6.9", "zw_z1 + 0.5"), "zw_z1 + 0.5"],
        ["board_y0 + board_d - " + str(J4[0][1]), "zw_z1 + 0.5"], ["board_y0 + board_d - " + str(J4[0][1]), "zw_z1 + 2.6"],
        [t("4.2", "zw_z1 + 2.6"), "zw_z1 + 2.6"]]}})
    b += [{"command": "sketch.solve", "params": {}}, {"command": "sketch.finish", "params": {}}]
    b.append({"command": "solid.extrude", "params": {"name": "ko_strip", "body_name": "ko_strip", "sketch": "ko_strip_profile",
                                                     "distance": "strip_x1 - pt_x0", "operation": "new"}})
    bx = "board_x0"
    fy = "board_y0 + board_d"
    b.append(_box("ko_route", "strip_x1", t("6.9", "zw_z1 + 2.6") + " + 0.2", "zw_z1 + 0.5",
                  f"{bx} + {J2[0][0]} - 5.0", f"{fy} - {J4[0][1]}", "zw_z1 + 2.6"))
    b.append(_box("ko_j2_plug", f"{bx} + {J2[0][0]} - 5.0", f"{fy} - {J2[1][1]}", "board_z0 + board_t",
                  f"{bx} + {J2[0][0]}", f"{fy} - {J2[0][1]}", f"board_z0 + board_t + {B.connector_h('j_sen66')}"))
    b.append(_box("ko_j4_plug", f"{bx} + {J4[0][0]} - 5.0", f"{fy} - {J4[1][1]}", "board_z0 + board_t",
                  f"{bx} + {J4[0][0]}", f"{fy} - {J4[0][1]}", f"board_z0 + board_t + {B.connector_h('j_qwiic_aux')}"))
    # SFA40: J2 (front) plug and its cable to grommet_j4, then left in front of the SEN66 to the riser
    wx0, wx1 = "sen_x1 + clr_align", "sen_x1 + clr_align + iwall"
    b.append(_box("ko_sfa_front", SFA_QW[0], "wall + shelf_w + 0.1", "floor_t", SFA_QW[1], "sfa_y0", "lid_z0 - shelf_w - 0.1"))
    b.append(_box("ko_sfa_turn", f"{wx1} + j4_fl + 0.1", j0, "floor_t", SFA_QW[0], j1, "floor_t + 3.8"))
    b.append(_cyl("ko_j4_grommet", [f"{wx0} - j4_fl", "j4n_yc", "j4n_zc"], "cable_qw_d", "iwall + 2 * j4_fl", axis="X"))
    b.append(_box("ko_j4_run", "-bp_x0 + 0.2", j0, "floor_t", f"{wx0} - j4_fl - 0.1", j1, "floor_t + 3.8"))
    b.append(_box("ko_j4_turn", "-bp_x0 + 0.2", j1, "floor_t", "qw_x + cable_qw_d / 2", run0, "floor_t + 3.0"))
    # SFA40: J1 (rear) plug, up through grommet_tongue, to the tongue's Qwiic plug
    b.append(_box("ko_sfa_rear", SFA_QW[0], "sfa_y0 + sfa_w", "floor_t", SFA_QW[1], "hy1", "lid_z0 - 0.5"))
    b.append(_cyl("ko_lid_cable", ["lh_x", "lh_y0 + lid_hole_w / 2", "lid_z0 - 0.5"], "cable_qw_d", "lid_t + tg_fl_t + 0.5"))
    tq_x = f"tongue_x1 - {TQ['center_x']}"
    b.append(_box("ko_tongue_plug", f"{tq_x} - 3.0", f"tongue_y0 + {TQ['mating_face_y']}", "tongue_z0 + tongue_t",
                  f"{tq_x} + 3.0", f"tongue_y0 + {TQ['mating_face_y']} + 4.5", f"tongue_z0 + tongue_t + {TQH}"))
    b.append(_box("ko_tongue_cable", f"{tq_x} - 3.0", f"tongue_y0 + {TQ['mating_face_y']} + 4.5", "lid_z0 + lid_t + tg_fl_t + 0.1",
                  "lh_x + 2.5", "hy1 - 0.6", f"tongue_z0 + tongue_t + {TQH}"))
    return b


# I2: every closed opening a plug must pass, as (probe, the part with the opening, plug width,
# plug thickness, the opening's centre and the axis the plug moves along). The open-edge openings
# (the zone wall's drawer, the HCHO pocket's J4 notch) take their cables from the side: no plug
# passes them, OPEN_EDGES below.
PLUG_PASSES = (
    ("plug_lid", "hcho_lid", "qw_plug_w", "qw_plug_t", ("lh_x", "lh_y0 + lid_hole_w / 2"), "Z"),
)
OPEN_EDGES = (   # (probe, part, its region: x0, y0, z0, x1, y1, z1) from the cable's place out past the part's edge
    ("edge_drawer", "zone_wall", ("-inner_x - 1", "pt_y0", "ledge_z0", "qw_x", "pt_y1", "zw_z1 + 1")),
    ("edge_j4", "base_plate", ("sen_x1 + clr_align - 0.5", "j4n_y0", "j4n_zc", "sen_x1 + clr_align + iwall + 0.5", "j4n_y0 + j4n_w", "lid_z0 + 0.5")),
)


def plug_probes(s) -> list[dict]:
    """I2: each plug's section (its width along x, its thickness along y), swept along the axis it
    moves through its opening, from below the part to above it; and each open edge's free way
    out (the cable's place to past the part's edge). None of them may meet its part."""
    out = []
    for name, _, w, th, (cx, cy), _axis in PLUG_PASSES:
        out.append(_box(name, f"{cx} - {w} / 2", f"{cy} - {th} / 2", "lid_z0 - 2", f"{cx} + {w} / 2", f"{cy} + {th} / 2", "lid_z0 + lid_t + 2"))
    for name, _, (x0, y0, z0, x1, y1, z1) in OPEN_EDGES:
        out.append(_box(name, x0, y0, z0, x1, y1, z1))
    return out


AIR = {   # probe -> (path, R25 minimum, the probe's face that is the section: "x", "y" or "z")
    "air_intake_gap": ("intake: the gap behind the port face to the inlets", 77.3, "x"),
    "air_intake_front": ("intake: the sensor zone in front of the SEN66", 77.3, "x"),
    "air_intake_right": ("intake: over the HCHO lid, toward the gap", 77.3, "y"),
    "air_outlet_ring": ("outlet: the ring's bore (gasket_out)", 330.1, "y"),
    "air_outlet_right": ("outlet: the plenum right of H1", None, "x"),
    "air_outlet_mid": ("outlet: the plenum between the ring and H1", None, "x"),
    "air_outlet_mid_top": ("outlet: the plenum between the ring and H1, in front of the rib", None, "x"),
    "air_outlet_h1": ("outlet: the plenum behind H1, below its trim's top", None, "x"),
    "air_outlet_h1_top": ("outlet: the plenum behind H1, above its trim", None, "x"),
    "air_hcho_layer": ("HCHO: over the SFA40's cap, toward the chimney", 27.4, "x"),
    "air_hcho_window": ("HCHO: the window into the chimney", 27.4, "x"),
    "air_hcho_chimney": ("HCHO: up the chimney to the grille", 27.4, "z"),
    "air_tongue_left": ("intake (M4): the slots in front of the tongue, out to the left", None, "x"),
    "air_tongue_right": ("intake (M4): the slots in front of the tongue, out to the right", None, "x"),
    # 3b-2: the air in front of every opening is free (interference 0 against every reference)
    "air_slots_front": ("intake rows: the free air behind every slot, to the tongue's front edge", None, "y"),
    "air_lsw": ("light-sensor window: the free line to the VEML7700's front edge", None, "y"),
    "air_outlet_grille": ("outlet grille: the free air behind its slots, in the plenum", None, "y"),
    "air_exhaust": ("electronics exhaust: the free air behind its slots", None, "y"),
    "air_usb_axis": ("USB-C: the plug's shell, from inside the rear wall out along J1's axis", None, "y"),
}


def air_probes(s) -> list[dict]:
    """The free sections of the internal air paths (R25), from the parameters. Each must touch
    and not overlap anything; its section is its face in the flow."""
    tl = "tongue_x1 - tongue_w"
    return [
        _box("air_intake_gap", "inlet_x0", "sen_y1", "floor_t", "sen_x1", "plate_y0", "zw_z0"),
        _box("air_intake_front", "plug_x1 + 1.5", "wall + 0.1", "floor_t + 3.8", "plug_x1 + 2.0",
             "sen_y0 - sen_d_tol - clr_align - iwall", "ledge_z0"),
        _box("air_intake_right", "hx0", "cy1 + iwall + 0.5", "tongue_z0 + tongue_t + 3.0", "h2_x - standoff_d / 2 - collar_w - 0.1", "cy1 + iwall + 1.0", "zw_z0"),
        _cyl("air_outlet_ring", ["outlet_x", "sen_y1", "outlet_z"], "ring_bore", "plate_y1 - sen_y1", axis="Y"),
        _box("air_outlet_right", "h1_x + standoff_d / 2 + 0.3", "plate_y1", "floor_t", "h1_x + standoff_d / 2 + 0.7",
             "D - wall", "zw_z0 - rib_d"),
        _box("air_outlet_mid", "outlet_x + ring_od / 2 + 0.5", "plate_y1", "floor_t", "outlet_x + ring_od / 2 + 0.9",
             "D - wall", "zw_z0 - rib_d"),
        _box("air_outlet_mid_top", "outlet_x + ring_od / 2 + 0.5", "plate_y1", "zw_z0 - rib_d", "outlet_x + ring_od / 2 + 0.9",
             "D - wall - rib_d", "zw_z0"),
        _box("air_outlet_h1", "h1_x - 0.2", "plate_y1 + 0.6", "floor_t", "h1_x + 0.2", "D - wall", "h1_trim_z"),
        _box("air_outlet_h1_top", "h1_x - 0.2", "h1_y + standoff_d / 2", "h1_trim_z", "h1_x + 0.2", "D - wall", "zw_z0 - rib_d"),
        _box("air_hcho_layer", "sfa_x0 + 17.0", "sfa_y0", "floor_t + sfa_cap", "sfa_x0 + 17.5", "sfa_y0 + sfa_w", "lid_z0"),
        _box("air_hcho_window", "hx1", "cy0 + 0.8", "floor_t", "cx0", "cy1 - 0.8", "lid_z0 - shelf_w"),
        _box("air_hcho_chimney", "cx0", "cy0", "grille_min_z - 0.5", "tub_x", "cy1", "grille_min_z"),
        _box("air_tongue_left", f"{tl} - 0.5", "wall", "lid_z0 + lid_t", tl, "tongue_y0", "ledge_z0"),
        _box("air_tongue_right", "tongue_x1", "wall", "lid_z0 + lid_t", "tongue_x1 + 0.5", "tongue_y0", "ledge_z0"),
        _box("air_slots_front", "row_x0", "wall", "slot_row1_z", "row_x1", "tongue_y0", "slot_row2_z + slot_w"),
        _cyl("air_lsw", ["lsw_x", "wall", "lsw_z"], "lsw_d", "tongue_y0 - wall", axis="Y"),
        _box("air_outlet_grille", "out_gx0", "D - wall - 3.0", "out_gz0", "out_gx1", "D - wall", "out_gz1"),
        _box("air_exhaust", "exh_x0", "D - wall - 3.0", "exh_z0", "exh_x0 + exh_n * out_pitch - (out_pitch - slot_w)", "D - wall", "exh_z1"),
        _box("air_usb_axis", "usb_x - usb_sw / 2", "D - wall - 1.0", "usb_z - usb_sh / 2", "usb_x + usb_sw / 2", "D + 5.0", "usb_z + usb_sh / 2"),
    ]


# --- the openings (Task 3b-2): open area, lower edge and fit, measured on the cut geometry ----------------
HCHO_SLOTS = airq.HCHO_SLOTS


def _volume(c, s) -> float:
    """Volume of a probe box or cylinder from its parameters."""
    v = s.v
    q = c["params"]
    if c["command"] == "solid.box":
        return v(q["length"]) * v(q["width"]) * v(q["height"])
    return math.pi / 4 * v(q["diameter"]) ** 2 * v(q["height"])


def opening_probes(s) -> list[tuple[dict, str, str, str]]:
    """(probe, part, thickness expression, expected open area expression) per opening. A probe is
    a box (or a cylinder) over the opening and a little of the bars round it, through the wall's
    thickness: the open area is (its volume - its overlap with the part) / the thickness. Every
    one overlaps its part by design, so they run apart from the main interference check."""
    sp = "slot_w"
    out = []
    for side, x0, x1, n, ln in (("l", "row_x0", "lsw_gap_x0", "in_n_l", "in_len_l"), ("r", "lsw_gap_x1", "row_x1", "in_n_r", "in_len_r")):
        out.append((_box(f"op_intake_{side}", x0, "0", "slot_row1_z", x1, "wall", f"slot_row2_z + {sp}"), "base_plate", "wall",
                    f"2 * {n} * {ln} * {sp}"))
    out.append((_cyl("op_lsw", ["lsw_x", "0", "lsw_z"], "lsw_d + 1.0", "wall", axis="Y"), "base_plate", "wall", "3.141592653589793 * lsw_d * lsw_d / 4"))
    out.append((_box("op_outlet", "out_gx0", "D - wall", "out_gz0", "out_gx1", "D", "out_gz1"), "base_plate", "wall",
                 f"out_n * {sp} * (out_gz1 - out_gz0)"))
    out.append((_box("op_exhaust", "exh_x0", "D - wall", "exh_z0", "exh_x0 + exh_n * out_pitch - (out_pitch - slot_w)", "D", "exh_z1"),
                "base_plate", "wall", f"exh_n * {sp} * (exh_z1 - exh_z0)"))
    for i in range(HCHO_SLOTS):
        y = f"cy0 + 0.6 + {i} * hg_pitch"
        top = f"{C.z_under(y)} - hg_margin"
        out.append((_box(f"op_hcho_{i + 1}", "tub_x", f"{y} - 0.3", "grille_min_z", "tub_x + iwall", f"{y} + {sp} + 0.3", top),
                    "base_plate", "iwall", f"{sp} * ({top} - grille_min_z)"))
    return out


def usb_probes(s) -> list[dict]:
    """The USB-C opening's fit: `usb_in` (0.05 smaller all round, through the straight part)
    must meet nothing, `usb_out` (0.05 larger) meets the wall's ring, and `usb_cham` over the
    chamfer's depth meets what the chamfer leaves of its box. Together they place the opening
    within 0.05 of J1's axis and size it."""
    e = 0.05
    hw, hh = "usb_open_w / 2", "usb_open_h / 2"
    x, z = "usb_x", "usb_z"
    y1 = "D - usb_chamfer - 0.05"
    c = "usb_chamfer"
    return [
        _box("usb_in", f"{x} - {hw} + {e}", "D - wall", f"{z} - {hh} + {e}", f"{x} + {hw} - {e}", y1, f"{z} + {hh} - {e}"),
        _box("usb_out", f"{x} - {hw} - {e}", "D - wall", f"{z} - {hh} - {e}", f"{x} + {hw} + {e}", y1, f"{z} + {hh} + {e}"),
        _box("usb_cham", f"{x} - {hw} - {c}", f"D - {c}", f"{z} - {hh} - {c}", f"{x} + {hw} + {c}", "D", f"{z} + {hh} + {c}"),
    ]


def usb_expect(s) -> dict:
    """The material each USB probe should meet (mm3): none in `usb_in`, the wall's ring round the
    straight part in `usb_out`, and the box less the chamfer's frustum in `usb_cham`."""
    v = s.v
    w, h, e, c, wall = v("usb_open_w"), v("usb_open_h"), 0.05, v("usb_chamfer"), v("wall")
    a1, a2 = w * h, (w + 2 * c) * (h + 2 * c)
    frustum = c / 3 * (a1 + a2 + math.sqrt(a1 * a2))
    return {"usb_in": 0.0, "usb_out": ((w + 2 * e) * (h + 2 * e) - w * h) * (wall - c - 0.05),
            "usb_cham": a2 * c - frustum}


def low_probes(s) -> list[dict]:
    """Nothing opens below grille_min_z: a box under the line over each wall's face must be all
    material. The lip and the rear wall are base_plate (the lip's inner face is recessed clr_remove
    round the bosses, so its probe stops there); the right side is the rail (base_plate) and the
    shell's wall (past its seam clr_remove from the lip, over the floor lap)."""
    z = "grille_min_z"
    return [_box("low_lip", "-W / 2", "0", "0", "W / 2", "wall - clr_remove", z),
            _box("low_rear", "-W / 2", "D - wall", "0", "W / 2", "D", z),
            _box("low_rail", "tub_x", "bp_y1", "0", "tub_x + iwall", "D - wall", z),
            _box("low_side", "inner_x", "wall + clr_remove", "floor_t", "W / 2", "D - wall", z)]


LOW_PARTS = {"low_lip": "base_plate", "low_rear": "base_plate", "low_rail": "base_plate", "low_side": "shell"}


def opening_run_bodies(s) -> list[str]:
    names = [c["params"]["body_name"] for c, *_ in opening_probes(s)]
    return names + [c["params"]["body_name"] for c in usb_probes(s) + low_probes(s)]


def clear_probes(s) -> list[dict]:
    """R12 and the tongue's distances on the geometry (`inspect.clearance`): the antenna strip, the
    USB plug's overmold, the shell's bosses and the standoffs' screws as probe solids from the
    boards' sources, against the SEN66's body; and the tongue's envelope against U3 and U2."""
    m = B.MAIN
    x0, z_top = "board_x0", "board_z0 + board_t"
    mod = m["antenna"]["module_body"]
    mh = B.module_h()
    (ux0, uy0), (ux1, uy1) = B.layout_part("U2")["box"]
    dev_y = lambda yy: f"(board_y0 + board_d - {yy})"          # noqa: E731
    b = [
        _box("cl_antenna", f"{x0} + {mod[0][0]}", dev_y(mod[0][1]), z_top, f"{x0} + {mod[1][0]}", dev_y(0), f"{z_top} + {mh}"),
        _box("cl_u3", f"{x0} + {mod[0][0]}", dev_y(mod[1][1]), z_top, f"{x0} + {mod[1][0]}", dev_y(mod[0][1]), f"{z_top} + {mh}"),
        _box("cl_u2", f"{x0} + {ux0}", dev_y(uy1), z_top, f"{x0} + {ux1}", dev_y(uy0), f"{z_top} + {m['max_part_height']}"),
        _box("cl_tongue", "tongue_x1 - tongue_w", "tongue_y0", "tongue_z0", "tongue_x1", "tongue_y0 + tongue_dp",
             "tongue_z0 + tongue_t + tongue_parts_h"),
        _box("cl_usb_plug", "usb_x - usb_plug_w / 2", dev_y(0), "usb_z - usb_plug_h / 2", "usb_x + usb_plug_w / 2", "D + 20.0",
             "usb_z + usb_plug_h / 2"),
    ]
    for i, sx in enumerate(("-boss_x", "boss_x"), 1):
        b.append(_cyl(f"cl_boss_{i}", [sx, "boss_y", "floor_t - head_depth"], "boss_d", "boss_h + head_depth"))
    b.append(_cyl("cl_boss_3", ["rear_boss_x", "D - wall - clr_remove - rear_boss_len", "rear_boss_z"], "boss_d",
                  "rear_boss_len + wall + clr_remove", axis="Y"))
    for i, (x, y) in enumerate((("h1_x", "h1_y"), ("h2_x", "h2_y")), 1):
        b.append(_cyl(f"cl_screw_{i}", [x, y, "board_z0 - pilot_depth"], "screw_d", "pilot_depth + board_t + 2.0"))
    return b


CLEAR_PAIRS = {   # distance label -> (the probes, the bodies they are measured against)
    "antenna_to_sen66": (("cl_antenna",), ("sen66_body",)),
    "antenna_to_usb_plug": (("cl_antenna",), ("cl_usb_plug",)),
    "antenna_to_inserts": (("cl_antenna",), ("cl_boss_1", "cl_boss_2", "cl_boss_3")),
    "antenna_to_screws": (("cl_antenna",), ("cl_screw_1", "cl_screw_2")),
    "tongue_to_u3": (("cl_tongue",), ("cl_u3",)),
    "tongue_to_u2": (("cl_tongue",), ("cl_u2",)),
    "intake_to_outlet": (("op_intake_l", "op_intake_r"), ("op_outlet",)),     # the openings' inner faces (the probes)
}


def sweeps(s) -> list[dict]:
    """The shell's way on (I1): it is lowered along -z onto the assembled base. Its bosses are the
    parts that reach into the case, so their swept columns (from where they end up to above the
    case) must clear everything on the base; and the whole shell is copied at raised steps, with the
    parts that ride in it (SHELL_RIDERS: the light guide, `led_mask`, `gap_stop`)."""
    b = [_cyl(f"sweep_boss_{i}", [sx, "boss_y", "floor_t"], "boss_d", "H + 5 - floor_t") for i, sx in enumerate(("-boss_x", "boss_x"), 1)]
    b.append(_box("sweep_rear_boss", "rear_boss_x - boss_d / 2", "D - wall - clr_remove - rear_boss_len", "rear_boss_z - boss_d / 2",
                  "rear_boss_x + boss_d / 2", "D - wall - clr_remove", "H + 5"))
    for dz in SWEEP_DZ:
        b.append({"command": "solid.move", "params": {"name": f"shell_up_{dz}", "bodies": ["shell"], "translate": [0, 0, dz],
                                                      "copy": True, "body_name": f"shell_up_{dz}"}})
        # 3b-1: the light guide and the two foam stops ride in the shell (stuck on the panel): their raised copies must
        # clear the base, the board and the cables too
        for body, tag in SHELL_RIDERS:
            b.append({"command": "solid.move", "params": {"name": f"{tag}_up_{dz}", "bodies": [body], "translate": [0, 0, dz],
                                                          "copy": True, "body_name": f"{tag}_up_{dz}"}})
    return b


NUDGE = 0.05            # review N1: the shell nudged this far each way (less than clr_remove)
NUDGES = {"shell_nx_m": (-NUDGE, 0, 0), "shell_nx_p": (NUDGE, 0, 0), "shell_ny_m": (0, -NUDGE, 0),
          "shell_ny_p": (0, NUDGE, 0), "shell_nz_m": (0, 0, -NUDGE), "shell_nz_p": (0, 0, NUDGE)}
NUDGE_PARTS = ("base_plate", "zone_wall", "zone_seal")
# the shell's datums: only these nudges may meet the base, and only on these faces (N1)
NUDGE_DATUMS = {"shell_ny_p": ("y", "D - wall"), "shell_nz_m": ("z", "floor_t")}


def nudges(s) -> list[dict]:
    """Review N1: copies of the shell moved NUDGE along +-x, +-y, +-z. The shell is seated on two
    datums, the floor (z) and the rear wall's front face (y); everywhere else it keeps clr_remove
    from the base, so only the copy pushed into a datum may meet the base, and only on that face."""
    return [{"command": "solid.move", "params": {"name": n, "bodies": ["shell"], "translate": list(t), "copy": True,
                                                 "body_name": n}} for n, t in NUDGES.items()]


def window_probes(s) -> list[dict]:
    """Review N2: one probe per step of the HCHO window, through the shell's wall and 0.5 into
    what stands behind it (the right rail and the zone wall's end). It must not meet the shell
    (the window is open) and it must meet the rail and the zone wall over its whole section but
    the grille slot: then nothing of the case's inside shows through the window."""
    return [_box(f"win_{i}", "tub_x + iwall - 0.5", y_lo, "grille_min_z", "W / 2 + 0.1", y_hi, top)
            for i, (y_lo, y_hi, top) in enumerate(airq.window_steps())]


def window_backing(s) -> dict:
    """{probe: the volume the rail and the zone wall must fill}: 0.5 x (the step's area less its slot's)."""
    v = s.v
    out = {}
    for i, (y_lo, y_hi, top) in enumerate(airq.window_steps()):
        area = (v(y_hi) - v(y_lo)) * (v(top) - v("grille_min_z"))
        y_slot = f"cy0 + 0.6 + {i} * hg_pitch"
        slot = v("slot_w") * (v(f"{C.z_under(y_slot)} - hg_margin") - v("grille_min_z"))
        out[f"win_{i}"] = 0.5 * (area - slot)
    return out


# --- the shell face (Task 3b-1): probes in the face frame (x, s up the slope, t into the case) ----------
FACE_PARTS = ("shell", "orange_dot")          # parts the face probes are checked against (3b-1 adds the others as they appear)


def sbox(s, name: str, x0: str, x1: str, s0: str, s1: str, t0: str, t1: str, join_to: str | None = None) -> list[dict]:
    """A new body `name` (or, with `join_to`, a piece joined to that body): the box x0..x1, s0..s1,
    t0..t1 in the face frame (sketch on the slope plane t0 deep, extruded to t1). Every bound is an
    expression over the design's parameters."""
    y0, y1 = F.ys(s0), F.ys(s1)
    sk = f"{name}_sk"
    ex = {"name": name if not join_to else f"{join_to}_{name}", "sketch": sk, "distance": f"({t1}) - ({t0})", "direction": "negative"}
    ex.update({"operation": "join", "targets": [join_to]} if join_to else {"body_name": name, "operation": "new"})
    return [
        {"command": "sketch.create", "params": {"name": sk, "plane": F.slope_plane(s), "offset": F.toff(t0)}},
        {"command": "sketch.line", "params": {"closed": True, "points": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]}},
        {"command": "sketch.solve", "params": {}}, {"command": "sketch.finish", "params": {}},
        {"command": "solid.extrude", "params": ex}]


def spoly(s, name: str, pts: list[tuple[str, str]], t0: str, t1: str, join_to: str | None = None) -> list[dict]:
    """Like `sbox` for a polygon: points (x, s) in the face frame, expressions."""
    sk = f"{name}_sk"
    ex = {"name": name if not join_to else f"{join_to}_{name}", "sketch": sk, "distance": f"({t1}) - ({t0})", "direction": "negative"}
    ex.update({"operation": "join", "targets": [join_to]} if join_to else {"body_name": name, "operation": "new"})
    return [
        {"command": "sketch.create", "params": {"name": sk, "plane": F.slope_plane(s), "offset": F.toff(t0)}},
        {"command": "sketch.line", "params": {"closed": True, "points": [[x, F.ys(sv)] for x, sv in pts]}},
        {"command": "sketch.solve", "params": {}}, {"command": "sketch.finish", "params": {}},
        {"command": "solid.extrude", "params": ex}]


def ffc_pieces(s) -> list[tuple[str, list[tuple[str, str]], str, float]]:
    """The FFC keep-out's pieces: (name, polygon (x, s) in the face frame, layer, volume): the four
    layers, each cut by its crease lines (45 degrees across the ribbon), so the folds' triangles are
    where the ribbon is. The layers touch (a fold has no air), so the pieces do not overlap; the bend
    over to J7 is `ffc_bend`."""
    v = s.v
    w, th = v("ffc_w"), v("ffc_t")
    h = "ffc_w / 2"
    x1, x3, sa, sc = "ffc_x_c1", "ffc_xc", "adapter_s", "ffc_s_c3"
    pieces = {
        "a": ([("ffc_x_m", f"{sa} - {h}"), (f"{x1} + {h}", f"{sa} - {h}"), (f"{x1} - {h}", f"{sa} + {h}"), ("ffc_x_m", f"{sa} + {h}")], "ffc_t_a"),
        "b": ([(f"{x1} - {h}", f"{sa} + {h}"), (f"{x1} + {h}", f"{sa} - {h}"), (f"{x1} + {h}", f"{sc} - {h}"), (f"{x1} - {h}", f"{sc} + {h}")], "ffc_t_b"),
        "c": ([(f"{x1} + {h}", f"{sc} - {h}"), (f"{x3} - {h}", f"{sc} - {h}"), (f"{x3} + {h}", f"{sc} + {h}"), (f"{x1} - {h}", f"{sc} + {h}")], "ffc_t_c"),
        "d": ([(f"{x3} - {h}", f"{sc} - {h}"), (f"{x3} + {h}", f"{sc} + {h}"), (f"{x3} + {h}", "ffc_s_b0"), (f"{x3} - {h}", "ffc_s_b0")], "ffc_t_d")}
    out = []
    for k, (pts, layer) in pieces.items():
        xy = [(v(x), v(y)) for x, y in pts]
        area = 0.5 * abs(sum(xy[i][0] * xy[(i + 1) % len(xy)][1] - xy[(i + 1) % len(xy)][0] * xy[i][1] for i in range(len(xy))))
        out.append((k, pts, layer, area * th))
    return out


def ffc_folds(s) -> list[dict]:
    """The folds of the FFC keep-out, found from its pieces' outlines and depths (not from how many there are):
    wherever two pieces of the ribbon share an edge in the face's (x, s) plane but lie at different depths, the
    ribbon turns over on that edge, folded flat (a crease). Returns one {pieces, crease: its two end points (x, s),
    angle: the crease to x (deg), dt: the depth step} per fold, in route order."""
    v = s.v
    pcs = [(k, [(v(x), v(y)) for x, y in pts], v(layer)) for k, pts, layer, _ in ffc_pieces(s)]
    out = []
    for i, (ka, pa, ta) in enumerate(pcs):
        for kb, pb, tb in pcs[i + 1:]:
            shared = [p for p in pa if any(math.dist(p, q) < 1e-6 for q in pb)]
            if len(shared) == 2 and abs(ta - tb) > 1e-6:
                (x0, s0), (x1, s1) = shared
                ang = math.degrees(math.atan2(abs(s1 - s0), abs(x1 - x0)))
                out.append({"pieces": (ka, kb), "crease": shared, "angle": ang, "dt": tb - ta})
    return out


def ffc_bend(s) -> tuple[list[list[float]], float]:
    """The bend over to J7 as a closed polygon in (y, z) (the ribbon's section along its centre line,
    thickness ffc_t) and its area."""
    v = s.v
    g = F.ffc_geometry(v, v("ffc_s_c3"))
    pts = F.ffc_path(v, g)
    h = v("ffc_t") / 2
    left = [[y - h * math.sin(a), z + h * math.cos(a)] for y, z, a in pts]
    right = [[y + h * math.sin(a), z - h * math.cos(a)] for y, z, a in pts]
    poly = left + right[::-1]
    area = 0.5 * abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly))))
    return poly, area


def ffc_body(s) -> list[dict]:
    """`ref_ffc`: the FFC keep-out, one body (12.5 x 0.3, bends of centre-line radius ffc_r), from
    the adapter's mouth to J7's mouth."""
    cmds = []
    for i, (k, pts, layer, _) in enumerate(ffc_pieces(s)):
        cmds += spoly(s, "ref_ffc" if i == 0 else f"ffc_{k}", pts, f"{layer} - ffc_t / 2", f"{layer} + ffc_t / 2", join_to=None if i == 0 else "ref_ffc")
    poly, _ = ffc_bend(s)
    cmds += [{"command": "sketch.create", "params": {"name": "ffc_bend_sk", "plane": "YZ", "offset": "ffc_xc - ffc_w / 2"}},
             {"command": "sketch.line", "params": {"closed": True, "points": [[round(y, 5), round(z, 5)] for y, z in poly]}},
             {"command": "sketch.solve", "params": {}}, {"command": "sketch.finish", "params": {}},
             {"command": "solid.extrude", "params": {"name": "ffc_bend", "sketch": "ffc_bend_sk", "distance": "ffc_w",
                                                     "operation": "join", "targets": ["ref_ffc"]}}]
    return cmds


def ffc_volume(s) -> float:
    return sum(p[3] for p in ffc_pieces(s)) + ffc_bend(s)[1] * s.v("ffc_w")


def face_probes(s) -> list[dict]:
    """Probes over the window and the pocket: the shell may overlap them only where the face's
    solid (3b-1: window, panel pocket, hatched block's room)."""
    b = []
    # window: open over the active area; solid in a 1 mm ring round it (to the chamfer's depth);
    # the chamfer shows as the ring's missing volume
    b += sbox(s, "fp_win_open", "win_x0", "win_x1", "win_s0", "win_s1", "0", "bezel")
    b += sbox(s, "fp_win_ring", "win_x0 - 1", "win_x1 + 1", "win_s0 - 1", "win_s1 + 1", "win_chamfer + 0.05", "bezel")
    b += sbox(s, "fp_win_cham", "win_x0 - 1", "win_x1 + 1", "win_s0 - 1", "win_s1 + 1", "0", "win_chamfer")
    # pocket: the panel's envelope with clr_remove all round, and the hatched block's room
    b += sbox(s, "fp_pocket", "panel_x0 - block_out - clr_remove", "panel_x0 + panel_l + clr_remove",
              "panel_s0 - clr_remove", "panel_s0 + panel_w + clr_remove", "bezel", "bezel + panel_t")
    b += sbox(s, "fp_block", "panel_x0 - block_out", "panel_x0",
              f"panel_s0 + panel_w - {_EPD('block_y1')}", f"panel_s0 + panel_w - {_EPD('block_y0')}", "bezel", "bezel + panel_t")
    # adapter holder: clr_remove over the board's upper edge, the arm's lower face 0.05 in
    b += sbox(s, "fp_hold", "adapter_x - ad_l / 2", "adapter_x + ad_l / 2", "adapter_s + ad_w / 2", "hold_s0 + 0.05", "hold_t0", "hold_t1")
    # 3b-1 feature 4: the flexure's beam, its hard stop and the pad rod's end
    b += sbox(s, "fp_beam", "flex_x0 + 0.5", "flex_x1 - 0.5", "flex_s0 + 1", "flex_s0 + 2", "0", "wall + 0.3")
    b.append(_box("fp_pad_end", "sw_x - 0.5", "y_pad - 0.1", "sw_z - 0.5", "sw_x + 0.5", "y_pad", "sw_z + 0.5"))
    b.append(_box("fp_pad_gap", "sw_x - 0.5", "y_pad", "sw_z - 0.5", "sw_x + 0.5", "sw_tip", "sw_z + 0.5"))
    return b


def face_pairs(s) -> list[list[str]]:
    """The face probes' own pairs (excluded from the check: probes may overlap each other)."""
    names = [c["params"]["body_name"] for c in face_probes(s) if c["params"].get("body_name")]
    return [[a, c] for i, a in enumerate(names) for c in names[i + 1:]]


def face_volumes(face: dict) -> dict:
    """{(probe, part): overlap volume} from the face run."""
    out = {}
    for p in face["interferences"]:
        a, b = (p["a"], p["b"]) if p["a"].startswith("fp_") else (p["b"], p["a"])
        out[(a, b)] = out.get((a, b), 0.0) + p["volume_mm3"]
    return out


# --- light paths (3b-1 feature 3): the guide's light against the crease, the light sensor and U4 -------
def _clip_len(p, q, poly) -> float:
    """Length of the segment p->q inside the simple polygon `poly` (list of (y, z))."""
    ts = [0.0, 1.0]
    (py, pz), (qy, qz) = p, q
    dy, dz = qy - py, qz - pz
    n = len(poly)
    for i in range(n):
        (ay, az), (by, bz) = poly[i], poly[(i + 1) % n]
        ey, ez = by - ay, bz - az
        den = dy * ez - dz * ey
        if abs(den) < 1e-12:
            continue
        t = ((ay - py) * ez - (az - pz) * ey) / den
        u = ((ay - py) * dz - (az - pz) * dy) / den
        if 0 <= t <= 1 and 0 <= u <= 1:
            ts.append(t)
    ts = sorted(set(ts))

    def inside(y, z):
        c = False
        for i in range(n):
            (ay, az), (by, bz) = poly[i], poly[(i + 1) % n]
            if (az > z) != (bz > z) and y < ay + (z - az) * (by - ay) / (bz - az):
                c = not c
        return c
    total = 0.0
    for a, b in zip(ts, ts[1:]):
        m = (a + b) / 2
        if inside(py + dy * m, pz + dz * m):
            total += (b - a) * math.hypot(dy, dz)
    return total


def _opaque_len(p, q, polys) -> float:
    """Length of p->q inside any of the (non-overlapping) opaque polygons."""
    return sum(_clip_len(p, q, poly) for poly in polys)


def section_polys(s) -> dict:
    """The opaque parts in the section at the light sensor's x (the sensor is under the line's
    right end), as (y, z) polygons: what a ray from the guide to the sensor, to the lip's window or
    to the crease's open end must cross."""
    v = s.v
    sn, c, lip = v("sin_t"), v("cos_t"), v("lip")
    yz = lambda sv, tv: (sv * sn + tv * c, lip + sv * c - tv * sn)   # noqa: E731
    box = lambda y0, y1, z0, z1: [(y0, z0), (y1, z0), (y1, z1), (y0, z1)]   # noqa: E731
    w, hz, dz = v("wall"), v("lsw_z"), v("lsw_d") / 2
    zw = [(v("wall + seal_t"), v("ledge_z0")), (v(C.yb("ledge_z0")), v("ledge_z0")), (v(C.yb("zw_z0")), v("zw_z0")),
          (v("D - wall - clr_remove"), v("zw_z0")), (v("D - wall - clr_remove"), v("zw_z1")), (v(C.yf("zw_z1")), v("zw_z1")),
          (v(C.yf("ledge_z1")), v("ledge_z1")), (v("wall + seal_t"), v("ledge_z1"))]
    z_bot = lip + v("clr_remove")                                      # the shell's lowest plane
    s_slot0, s_slot1 = v("led_s0"), v("led_s1")
    y_out = (z_bot - lip) / c * sn                                     # the outer face at z_bot
    low_out = yz(s_slot0, 0.0)
    t_cut = (low_out[1] - z_bot) / sn                                  # along the slot's lower face down to z_bot
    return {
        "lip_low": box(0, w, 0, hz - dz), "lip_high": box(0, w, hz + dz, lip),
        "zone_seal": box(w, v("wall + seal_t"), v("ledge_z0"), v("ledge_z1")),
        "crease_seal": box(v("crease_y0"), w, lip, z_bot),
        "zone_wall": zw,
        "face_below_slot": [(y_out, z_bot), low_out, yz(s_slot0, t_cut)],
        "face_bar": [yz(s_slot1, 0.0), yz(v("panel_s0 - clr_remove"), 0.0), yz(v("panel_s0 - clr_remove"), w), yz(s_slot1, w)],
    }


def guide_outline(s) -> list[tuple[float, float]]:
    """The guide's cross-section as one simple polygon in (s, t): tongue, bar and leg joined
    (the build's `guide_profile_pts` pieces, as they overlap)."""
    v = s.v
    return [(v("led_s0") + v("gd_tg"), v("gd_rec")), (v("led_s1") - v("gd_tg"), v("gd_rec")),
            (v("led_s1") - v("gd_tg"), v("gd_t0")), (v("gd_sf"), v("gd_t0")), (v("gd_sb"), v("gd_tb")),
            (v("gd_sc"), v("gd_tc")), (v("gd_sc"), v("gd_t1")), (v("gd_s0"), v("gd_t1")), (v("gd_sg"), v("gd_t0"))]


def guide_surface_points(s, n: int = 12) -> list[tuple[float, float]]:
    """Sample points (y, z) on the light guide's surfaces in the section, except the exit face (the
    light is meant to leave there, outside): every edge of `guide_outline` but the first."""
    v = s.v
    sn, c, lip = v("sin_t"), v("cos_t"), v("lip")
    yz = lambda sv, tv: (sv * sn + tv * c, lip + sv * c - tv * sn)   # noqa: E731
    poly = guide_outline(s)
    pts = []
    for i in range(1, len(poly)):                                    # edge 0 is the exit face
        (a0, b0), (a1, b1) = poly[i], poly[(i + 1) % len(poly)]
        for j in range(n + 1):
            f = j / n
            pts.append(yz(a0 + (a1 - a0) * f, b0 + (b1 - b0) * f))
    return pts


CRIT_DEG = 39.6                  # PETG (n 1.57) against air, the critical angle
N_PETG = 1.57
N_PAD = 1.47                     # the acrylic adhesive pad on the bar's front (it frustrates TIR under asin(1.47 / 1.57))


def guide_prisms(s) -> list[dict]:
    """The guide's pieces as built (`airq_face.guide_pieces`): {name, poly: (s, t) profile, x: (x0, x1),
    kinds: {edge index: face name}, sign: the profile's winding}. The profile's edge i runs from point i to
    point i + 1."""
    v = s.v
    pc = F.guide_profile_pts()
    kinds = {"tongue": {0: "exit"}, "low": {0: "bar_front", 3: "bottom_facet"}, "leg": {1: "foot_facet", 2: "entry"}}
    names = {"Guide tongue": "tongue", "Guide low": "bar", "Guide leg 1": "D1 foot", "Guide leg 2": "D2 foot"}
    out = []
    for n, k, x0, x1 in F.guide_pieces():
        poly = [(v(a), v(b)) for a, b in pc[k]]
        area2 = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
        out.append({"name": names[n], "poly": poly, "x": (v(x0), v(x1)), "kinds": kinds[k], "sign": 1 if area2 > 0 else -1})
    return out


def _in_prisms(prisms, P) -> bool:
    return any(p["x"][0] <= P[0] <= p["x"][1] and _inside(p["poly"], P[1], P[2]) for p in prisms)


def _fresnel_t(cos_i: float, n1: float, n2: float) -> float:
    """Unpolarised Fresnel transmittance from n1 into n2 at incidence cos_i (0 past the critical angle)."""
    sin_t = n1 / n2 * math.sqrt(max(0.0, 1 - cos_i * cos_i))
    if sin_t >= 1:
        return 0.0
    cos_t = math.sqrt(1 - sin_t * sin_t)
    rs = ((n1 * cos_i - n2 * cos_t) / (n1 * cos_i + n2 * cos_t)) ** 2
    rp = ((n1 * cos_t - n2 * cos_i) / (n1 * cos_t + n2 * cos_i)) ** 2
    return 1 - (rs + rp) / 2


def _next_exit(prisms, P, D):
    """The nearest point where the ray P + l D (face frame x, s, t) leaves the union of the prisms:
    (l, outward unit normal, face name), or None."""
    cands = []
    for p in prisms:
        poly, (xa, xb) = p["poly"], p["x"]
        n = len(poly)
        for i in range(n):
            (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
            ex, ey = bx - ax, by - ay
            den = D[1] * ey - D[2] * ex
            if abs(den) < 1e-14:
                continue
            lam = ((ax - P[1]) * ey - (ay - P[2]) * ex) / den
            u = ((ax - P[1]) * D[2] - (ay - P[2]) * D[1]) / den
            if lam > 1e-9 and -1e-9 <= u <= 1 + 1e-9 and xa - 1e-9 <= P[0] + lam * D[0] <= xb + 1e-9:
                ln = math.hypot(ex, ey)
                cands.append((lam, (0.0, p["sign"] * ey / ln, -p["sign"] * ex / ln), p["kinds"].get(i, p["name"] + " side")))
        for xe, nx in ((xa, -1.0), (xb, 1.0)):
            if abs(D[0]) > 1e-14:
                lam = (xe - P[0]) / D[0]
                if lam > 1e-9 and _inside(poly, P[1] + lam * D[1], P[2] + lam * D[2]):
                    cands.append((lam, (nx, 0.0, 0.0), p["name"] + " end"))
    for lam, nrm, kind in sorted(cands, key=lambda q: q[0]):
        if not _in_prisms(prisms, [P[k] + (lam + 1e-6) * D[k] for k in range(3)]):
            return lam, nrm, kind
    return None


def guide_delivery(s, pad: bool = False, n_rays: int = 20000, seed: int = 1, max_bounce: int = 200) -> dict:
    """R48 (analytic: a 3-D Monte Carlo ray trace in Python, not a print): the light guide as built (the four
    prisms of `guide_prisms`) with every face bare: PETG (n 1.57) against air, total internal reflection where
    the incidence is at least the critical angle (39.6 deg), else the ray leaves the guide. Per LED (D1, D2):
    `n_rays` Lambertian rays from its 4 x 2 light face cross the gd_clr air gap; those that meet its foot's
    entry face refract in (Snell; the Fresnel transmittance is the ray's weight) and are followed, reflection by
    reflection, until they leave. A ray leaving through the tongue's front face (the exit) is delivered, times
    the exit's Fresnel transmittance; one leaving anywhere else is lost (its partial reflection is dropped:
    conservative). With `pad`, the 0.2 adhesive pad (n 1.47) on the bar's front behind the panel (s >= panel_s0,
    worst case: the pad over all of it) takes every ray that meets it under asin(1.47 / 1.57).
    Returns {leds: {D1, D2: {fraction of the LED's emission delivered, rays entered, rays delivered}}, lit_x: the
    lowest and highest x a delivered ray leaves at, lit_x90: the x span of the middle 90 % of them, bins: delivered
    rays in 10 equal bins over the exit's length, exit_x: the exit's x range, min_reflections: the fewest
    reflections of any delivered ray, lost: where the others went}."""
    import random
    v = s.v
    rng = random.Random(seed)
    sn, c, lip = v("sin_t"), v("cos_t"), v("lip")
    crit, pad_crit = math.radians(CRIT_DEG), math.asin(N_PAD / N_PETG)
    prisms = guide_prisms(s)
    by_name = {p["name"]: p for p in prisms}
    ye, yf, zc, hh, hw = v("gd_y_e"), v("board_y0"), v("led_z"), v("led_face_h") / 2, v("led_face_w") / 2
    leg = by_name["D1 foot"]["poly"]
    win_z = sorted(lip + sv * c - tv * sn for sv, tv in leg[2:4])            # the entry face's z extent (edge 2)
    x_lo, x_hi = by_name["tongue"]["x"]
    out_leds, xs, lost, min_ref = {}, [], {}, None
    for i in (1, 2):
        cx = v(f"led_d{i}_x")
        foot = by_name[f"D{i} foot"]
        w_sum, entered, hits = 0.0, 0, 0
        for _ in range(n_rays):
            r1, r2 = rng.random(), rng.random()                             # Lambertian about -y
            ph, sr = 2 * math.pi * r1, math.sqrt(r2)
            d = (sr * math.cos(ph), -math.sqrt(1 - r2), sr * math.sin(ph))
            p0 = (cx + rng.uniform(-hw, hw), yf, zc + rng.uniform(-hh, hh))
            k = (ye - yf) / d[1]
            q = (p0[0] + k * d[0], ye, p0[2] + k * d[2])
            if not (foot["x"][0] <= q[0] <= foot["x"][1] and win_z[0] <= q[2] <= win_z[1]):
                lost["missed the entry face"] = lost.get("missed the entry face", 0) + 1
                continue
            entered += 1
            w = _fresnel_t(-d[1], 1.0, N_PETG)
            dx, dz = d[0] / N_PETG, d[2] / N_PETG                            # Snell across the plane y = gd_y_e
            dw = (dx, -math.sqrt(max(0.0, 1 - dx * dx - dz * dz)), dz)
            D = [dw[0], dw[1] * sn + dw[2] * c, dw[1] * c - dw[2] * sn]
            P = [q[0] + 1e-6 * D[0], q[1] * sn + (q[2] - lip) * c + 1e-6 * D[1], q[1] * c - (q[2] - lip) * sn + 1e-6 * D[2]]
            fate = "max reflections"
            for nref in range(max_bounce):
                h = _next_exit(prisms, P, D)
                if h is None:
                    fate = "no exit found"
                    break
                lam, nrm, kind = h
                P = [P[k] + lam * D[k] for k in range(3)]
                cosi = sum(D[k] * nrm[k] for k in range(3))
                inc = math.acos(max(-1.0, min(1.0, cosi)))
                if pad and kind == "bar_front" and P[1] >= v("panel_s0") and inc < pad_crit:
                    fate = "into the adhesive pad"
                    break
                if inc < crit:
                    if kind == "exit":
                        fate = "delivered"
                        w_sum += w * _fresnel_t(cosi, N_PETG, 1.0)
                        hits += 1
                        xs.append(P[0])
                        min_ref = nref if min_ref is None else min(min_ref, nref)
                    else:
                        fate = "left through " + kind
                    break
                D = [D[k] - 2 * cosi * nrm[k] for k in range(3)]
                P = [P[k] + 1e-7 * D[k] for k in range(3)]
            if fate != "delivered":
                lost[fate] = lost.get(fate, 0) + 1
        out_leds[f"D{i}"] = {"fraction": w_sum / n_rays, "entered": entered, "delivered": hits}
    bins = [0] * 10
    for x in xs:
        bins[min(9, int((x - x_lo) / (x_hi - x_lo) * 10))] += 1
    xs.sort()
    span90 = (xs[int(0.05 * (len(xs) - 1))], xs[int(0.95 * (len(xs) - 1))]) if xs else None
    return {"leds": out_leds, "lit_x": (xs[0], xs[-1]) if xs else None, "lit_x90": span90, "bins": bins, "exit_x": (x_lo, x_hi),
            "min_reflections": min_ref, "lost": dict(sorted(lost.items())), "pad": pad, "rays_per_led": n_rays}


def light_paths(s) -> dict:
    """The least opaque length (mm) along any straight line from the guide's surfaces (not its exit
    face) to: the light sensor (the VEML7700's window, behind the lip), the lip's window hole
    (outside) and the crease's open end (the parting line's front, plugged by the crease seal). In the section at the sensor's x; lines at other x are longer.
    Returns {target: (length, (source, target point))}."""
    v = s.v
    polys = list(section_polys(s).values())
    src = guide_surface_points(s) + [(v("board_y0"), v("led_z") + v("led_face_h") * (k / 4 - 0.5)) for k in range(5)]   # + the LED faces
    hz, dz = v("lsw_z"), v("lsw_d") / 2
    lip, cr = v("lip"), v("clr_remove")
    targets = {
        "sensor": [(v("tongue_y0") + 0.25, hz)],
        "lip_window": [(0.0, hz + dz * k / 4) for k in range(-4, 5)],
        "crease_front": [(v("crease_y0") + 0.005, lip + z) for z in (0.01, cr / 2, cr - 0.01)],
    }
    out = {}
    for name, ts in targets.items():
        best = (1e9, None)
        for p in src:
            for q in ts:
                ln = _opaque_len(p, q, polys)
                if ln < best[0]:
                    best = (ln, (p, q))
        out[name] = best
    return out


def ms5611_sight(s, stops: bool = True) -> dict:
    """R13 / R50 (arithmetic: exact straight lines against the opaque obstacles, not a SolidCraft ray trace):
    `unblocked` counts the straight lines to the MS5611's port (U4) that nothing opaque stops (0 is the pass).
    - LED faces (all four): each emits into -y only and U4 is behind them, so no line in the hemisphere.
    - The guide's entry faces (each foot's entry plane in front of D1 and D2, its whole area).
    - Every exposed face of the guide's four prisms whose outward half-space holds U4, the side and end faces
      included, sampled at fine x (`guide_surface_sight`).
    The obstacles (`sight_obstacles`) are the zone wall, the four LED bodies, the board, `led_mask` over D3 and D4,
    and `gap_stop` over the gap between the D1 and D2 feet (R50: without it, lines from the D2 foot's tail-side face
    pass between D1 and D2 to U4; `stops=False` leaves it out to show that)."""
    v = s.v
    sn, c, lip = v("sin_t"), v("cos_t"), v("lip")
    tgt = u4_port(s)
    obst = sight_obstacles(s, stops)
    w, hh, yf, zc = v("led_face_w"), v("led_face_h"), v("board_y0"), v("led_z")
    prisms = {p["name"]: p for p in guide_prisms(s)}
    n = 6
    count = {"led_faces": 0, "entry_windows": 0}
    un = {"led_faces": 0, "entry_windows": 0}
    for i in range(1, 5):
        cx = v(f"led_d{i}_x")
        for a in range(n + 1):
            for b in range(n + 1):
                p = (cx - w / 2 + w * a / n, yf, zc - hh / 2 + hh * b / n)
                count["led_faces"] += 1
                # a LED face emits into -y only: U4 is behind it, so only lines in that hemisphere count
                if tgt[1] - p[1] <= 0 and not _sight_blocked(s, obst, p, tgt):
                    un["led_faces"] += 1
    for i in (1, 2):                                                 # D3, D4: behind led_mask
        foot = prisms[f"D{i} foot"]
        (s0, t0), (s1, t1) = foot["poly"][2], foot["poly"][3]        # the entry face (edge 2)
        x0, x1 = foot["x"]
        for a in range(n + 1):
            for b in range(n + 1):
                sv, tv = s0 + (s1 - s0) * b / n, t0 + (t1 - t0) * b / n
                p = (x0 + (x1 - x0) * a / n, sv * sn + tv * c, lip + sv * c - tv * sn)
                count["entry_windows"] += 1
                if not _sight_blocked(s, obst, p, tgt):
                    un["entry_windows"] += 1
    surf = guide_surface_sight(s, stops=stops)
    count["guide_faces"], un["guide_faces"] = surf["all"][0], surf["all"][1]
    return {"target": tgt, "samples": count, "unblocked": un, "faces": surf}


def _inside(poly, y, z) -> bool:
    c = False
    for i in range(len(poly)):
        (ay, az), (by, bz) = poly[i], poly[(i + 1) % len(poly)]
        if (az > z) != (bz > z) and y < ay + (z - az) * (by - ay) / (bz - az):
            c = not c
    return c


def _seg_box(p, q, lo, hi) -> bool:
    """Does the segment p -> q pass through the inside of the box lo .. hi (more than touch it)?"""
    t0, t1 = 0.0, 1.0
    for k in range(3):
        d = q[k] - p[k]
        if abs(d) < 1e-12:
            if p[k] <= lo[k] + 1e-9 or p[k] >= hi[k] - 1e-9:
                return False
            continue
        a, b = (lo[k] - p[k]) / d, (hi[k] - p[k]) / d
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
    return t0 < t1 - 1e-9


def _seg_prism(s, p, q, poly, xa, xb) -> bool:
    """Does the segment p -> q (world) pass through the prism of the face-frame profile `poly` ((s, t)) from x xa
    to xb (more than touch it)?"""
    v = s.v
    sn, c, lip = v("sin_t"), v("cos_t"), v("lip")
    d = q[0] - p[0]
    if abs(d) < 1e-12:
        if not xa < p[0] < xb:
            return False
        t0, t1 = 0.0, 1.0
    else:
        a, b = (xa - p[0]) / d, (xb - p[0]) / d
        t0, t1 = max(0.0, min(a, b)), min(1.0, max(a, b))
    if t0 >= t1 - 1e-9:
        return False

    def st(f):
        y, z = p[1] + (q[1] - p[1]) * f, p[2] + (q[2] - p[2]) * f
        return y * sn + (z - lip) * c, y * c - (z - lip) * sn
    return _clip_len(st(t0), st(t1), poly) > 1e-6


def u4_port(s) -> tuple[float, float, float]:
    """The MS5611's (U4's) port: over its centre on the board, 1.0 above the board's top (the package's height,
    datasheet; the port is in its lid)."""
    v = s.v
    u4 = B.layout_part("U4")["center"]
    return v("board_x0") + u4[0], v("board_y0") + v("board_d") - u4[1], v("board_z0") + v("board_t") + 1.0


def sight_obstacles(s, stops: bool = True) -> list[tuple]:
    """R13's opaque obstacles between the guide and U4: ("poly", (y, z) polygon) for the zone wall's section (it
    runs the whole width); ("box", lo, hi) for the four LED bodies and the board; ("prism", (s, t) profile, x0, x1)
    for the black foam `led_mask` and, with `stops`, `gap_stop` (`airq_face.foam_stops`)."""
    v = s.v
    zw = [(v("wall + seal_t"), v("ledge_z0")), (v(C.yb("ledge_z0")), v("ledge_z0")), (v(C.yb("zw_z0")), v("zw_z0")),
          (v("D - wall - clr_remove"), v("zw_z0")), (v("D - wall - clr_remove"), v("zw_z1")), (v(C.yf("zw_z1")), v("zw_z1")),
          (v(C.yf("ledge_z1")), v("ledge_z1")), (v("wall + seal_t"), v("ledge_z1"))]
    w, hh, dep = v("led_face_w"), v("led_face_h"), B.led_body_d()
    yf, zc = v("board_y0"), v("led_z")
    out = [("poly", zw)]
    out += [("box", (v(f"led_d{i}_x") - w / 2, yf, zc - hh / 2), (v(f"led_d{i}_x") + w / 2, yf + dep, zc + hh / 2)) for i in range(1, 5)]
    out.append(("box", (v("board_x0"), yf, v("board_z0")), (v("board_x0") + v("board_w"), yf + v("board_d"), v("board_z0") + v("board_t"))))
    for name, (pts, x0, x1) in F.foam_stops().items():
        if stops or name != "gap_stop":
            out.append(("prism", [(v(a), v(b)) for a, b in pts], v(x0), v(x1)))
    return out


def _sight_blocked(s, obst, p, q) -> bool:
    for o in obst:
        if o[0] == "poly" and _clip_len((p[1], p[2]), (q[1], q[2]), o[1]) > 1e-6:
            return True
        if o[0] == "box" and _seg_box(p, q, o[1], o[2]):
            return True
        if o[0] == "prism" and _seg_prism(s, p, q, o[1], o[2], o[3]):
            return True
    return False


def guide_surface_sight(s, dx: float = 0.25, n_edge: int = 40, n_side: int = 60, stops: bool = True) -> dict:
    """R13 / R50 (arithmetic, not a SolidCraft ray trace): every exposed face of the guide's four prisms as built
    (`guide_prisms`: tongue, bar, D1 foot, D2 foot), the side and end faces included. Each profile face is sampled
    at n_edge + 1 points along its edge and at every `dx` (or finer) along its x range; each prism's two end faces
    (at x0 and x1) on an (n_side + 1)^2 grid inside its profile. A sample counts if it is exposed (just outside it,
    along the face's normal, there is no guide) and U4's port is in the face's outward half-space; its straight line
    to the port is unblocked if it passes through none of `sight_obstacles` (with `stops` False, `gap_stop` is left
    out). Returns {face: [samples, unblocked, first unblocked (x, s, t)]}, with the totals under "all"."""
    v = s.v
    sn, c, lip = v("sin_t"), v("cos_t"), v("lip")
    tgt = u4_port(s)
    obst = sight_obstacles(s, stops)
    prisms = guide_prisms(s)
    res: dict[str, list] = {}

    def sample(face, x, sv, tv, n3):
        if _in_prisms(prisms, (x + n3[0] * 2e-3, sv + n3[1] * 2e-3, tv + n3[2] * 2e-3)):
            return                                                  # inside the guide there: not an exposed face
        p = (x, sv * sn + tv * c, lip + sv * c - tv * sn)
        nw = (n3[0], n3[1] * sn + n3[2] * c, n3[1] * c - n3[2] * sn)
        if sum((tgt[k] - p[k]) * nw[k] for k in range(3)) <= 0:
            return                                                  # U4 is behind the face
        r = res.setdefault(face, [0, 0, None])
        r[0] += 1
        if not _sight_blocked(s, obst, p, tgt):
            r[1] += 1
            r[2] = r[2] or (round(x, 3), round(sv, 3), round(tv, 3))
    for pr in prisms:
        poly, (xa, xb) = pr["poly"], pr["x"]
        n = len(poly)
        nx = max(1, math.ceil((xb - xa) / dx))
        for i in range(n):
            (s0, t0), (s1, t1) = poly[i], poly[(i + 1) % n]
            ln = math.hypot(s1 - s0, t1 - t0)
            nst = (pr["sign"] * (t1 - t0) / ln, -pr["sign"] * (s1 - s0) / ln)
            name = f"{pr['name']} {pr['kinds'].get(i, 'face ' + str(i))}"
            for j in range(n_edge + 1):
                f = j / n_edge
                for k in range(nx + 1):
                    sample(name, xa + (xb - xa) * k / nx, s0 + (s1 - s0) * f, t0 + (t1 - t0) * f, (0.0, nst[0], nst[1]))
        ss, ts = [q[0] for q in poly], [q[1] for q in poly]
        for xe, sx in ((xa, -1.0), (xb, 1.0)):
            for i in range(n_side + 1):
                for j in range(n_side + 1):
                    sv = min(ss) + (max(ss) - min(ss)) * i / n_side
                    tv = min(ts) + (max(ts) - min(ts)) * j / n_side
                    if _inside(poly, sv, tv):
                        sample(f"{pr['name']} end x {xe:.2f}", xe, sv, tv, (sx, 0.0, 0.0))
    res["all"] = [sum(r[0] for r in res.values()), sum(r[1] for r in res.values()), None]
    return res


def mask_leak(s, n_rays: int = 100000, seed: int = 3) -> dict:
    """R50 (analytic, a Monte Carlo of straight rays): the share of D3's and D4's Lambertian emission that crosses
    the gd_clr air gap and passes `led_mask`'s edges instead of meeting its back face (the plane y = gd_y_e), by
    where it leaves: past the tail-side (-x) or far (+x) edge, over the top or under the bottom. That light goes
    into the case at grazing angles, away from U4 (the faces emit into -y). Returns {D3, D4: {total, -x, +x, up,
    down}} as fractions of the LED's emission."""
    import random
    v = s.v
    rng = random.Random(seed)
    sn, c, lip = v("sin_t"), v("cos_t"), v("lip")
    pts, x0, x1 = F.foam_stops()["led_mask"]
    mx0, mx1 = v(x0), v(x1)
    mz0, mz1 = sorted(lip + v(a) * c - v(b) * sn for a, b in pts[1:3])       # the back face's z (its edge 1 -> 2)
    ye, yf, zc, hh, hw = v("gd_y_e"), v("board_y0"), v("led_z"), v("led_face_h") / 2, v("led_face_w") / 2
    out = {}
    for i in (3, 4):
        cx = v(f"led_d{i}_x")
        n = {"-x": 0, "+x": 0, "up": 0, "down": 0}
        for _ in range(n_rays):
            r1, r2 = rng.random(), rng.random()
            ph, sr = 2 * math.pi * r1, math.sqrt(r2)
            d = (sr * math.cos(ph), -math.sqrt(1 - r2), sr * math.sin(ph))
            p = (cx + rng.uniform(-hw, hw), yf, zc + rng.uniform(-hh, hh))
            k = (ye - yf) / d[1]
            x, z = p[0] + k * d[0], p[2] + k * d[2]
            if mx0 <= x <= mx1 and mz0 <= z <= mz1:
                continue
            n["up" if z > mz1 else "down" if z < mz0 else "-x" if x < mx0 else "+x"] += 1
        out[f"D{i}"] = {"total": sum(n.values()) / n_rays, **{k: q / n_rays for k, q in n.items()}}
    return out


EXTREME_PARTS = ("base_plate", "zone_wall", "sen66_pad", "gasket_out", "gasket_in")


def extremes(s) -> list[dict]:
    """I3(b): the front of the SEN66 at its depth tolerance's ends, its port face on the ring (the
    datum): `ext_max_*` 21.8 deep (its plinth, inset plinth_in, a slice of the block behind it,
    and, B2, its plug and the cable's bend, the keep-outs moved with its connector face),
    `ext_min_plinth` 20.8 deep. Only the pad may meet them."""
    pin = _SEN("plinth_inset")
    ph = _SEN("H") - _SEN("block_h")
    fx = ("sen_x0", "sen_x1")
    z0, z1 = "floor_t + foam", "sen_top"
    out = []
    for tag, dy in (("max", "- sen_d_tol"), ("min", "+ sen_d_tol")):
        y = f"sen_y0 {dy}"
        out.append(_box(f"ext_{tag}_plinth", f"{fx[0]} + {pin}", y, f"{z0} + {pin}", f"{fx[1]} - {pin}", f"{y} + {ph}", f"{z1} - {pin}"))
    out.append(_box("ext_max_block", fx[0], f"sen_y0 - sen_d_tol + {ph}", z0, fx[1], f"sen_y0 - sen_d_tol + {ph} + 0.5", z1))
    # B2: what moves with a 21.8 module's connector face: its plug and the cable's bend
    mid = "sen_top - sen_up / 2"
    f = "sen_y0 - sen_d_tol"
    out.append(_box("ext_max_plug", "plug_x0", f"{f} - 6.0", f"{mid} - 2.5", "plug_x1", f, f"{mid} + 2.5"))
    out.append(_box("ext_max_bend", "plug_x0", f"{f} - 6.94", "floor_t", "plug_x1", f"{f} - 6.0", f"{mid} + 0.7"))
    return out


def extreme_reach(ext: dict) -> dict:
    """{(probe, body): its overlap's depth along y} from the extremes run."""
    out = {}
    for p in ext["interferences"]:
        a, b = (p["a"], p["b"]) if p["a"].startswith("ext_") else (p["b"], p["a"])
        out[(a, b)] = p["bbox"]["max"][1] - p["bbox"]["min"][1]
    return out


OPENING_AIR = ("air_slots_front", "air_lsw", "air_outlet_grille", "air_exhaust", "air_usb_axis")


def check_bodies(s) -> list[str]:
    names = []
    for c in keepouts(s) + air_probes(s) + sweeps(s):
        n = c["params"].get("body_name")
        if n:
            names.append(n)
    return names


def exclusions(names: list[str]) -> list[list[str]]:
    """Pairs that may overlap: each reference's own STEP bodies (pins in housings), keep-outs
    with each other (the routes join), and the shell's sweep with the shell and what it carries."""
    out = [[f"{n}:1", f"{n}:1"] for n in REFS]
    ko = [n for n in names if n.startswith("ko_")]
    out += [[a, b] for i, a in enumerate(ko) for b in ko[i + 1:]]
    sw = [n for n in names if n.startswith(("sweep_", "shell_up_") + tuple(f"{tag}_up_" for _, tag in SHELL_RIDERS))]
    out += [[a, b] for i, a in enumerate(sw) for b in sw[i + 1:]]
    out += [[a, p] for a in sw for p in ("shell", "orange_dot") + tuple(body for body, _ in SHELL_RIDERS)]
    out += [[a, f"{r}:1"] for a in sw for r in SHELL_BORNE]
    # 3b-2: the free-air probes in front of the openings share air with the paths' probes
    op = [n for n in names if n in OPENING_AIR]
    out += [[a, b] for a in op for b in names if b.startswith("air_") and a != b]
    return out


def check_script(save: Path = CHECK_SC, budget_s: float = 900) -> dict:
    s = airq.build()
    steps = []
    for pl in placements(s):
        params = {"path": str(pl["path"]), "matrix": pl["matrix"]}
        if "configuration" in pl:
            params["configuration"] = pl["configuration"]
        steps.append({"command": "component.insert_design", "params": params})
    steps.append({"command": "parameters.change", "params": {"changes": {n: "0 mm" for n in SQUEEZES}}})
    extra = keepouts(s) + air_probes(s) + sweeps(s) + ffc_body(s)
    steps += extra
    names = check_bodies(s)
    mark = {"interference": len(steps)}
    steps.append({"command": "inspect.interference", "params": {"budget_s": budget_s, "exclude_pairs": exclusions(names)}})
    mark["measure"] = len(steps)
    steps.append({"command": "inspect.measure", "params": {"summary": True}})
    # N1: the shell nudged each way meets the base only on its datums
    steps += nudges(s)
    mark["nudge"] = len(steps)
    steps.append({"command": "inspect.interference", "params": {
        "budget_s": 120, "bodies": [*NUDGES, *NUDGE_PARTS],
        "exclude_pairs": [[a, b] for i, a in enumerate(NUDGES) for b in list(NUDGES)[i + 1:]]}})
    # N2: what stands behind the HCHO window
    win = window_probes(s)
    steps += win
    names_w = [c["params"]["body_name"] for c in win]
    mark["window"] = len(steps)
    steps.append({"command": "inspect.interference", "params": {
        "budget_s": 120, "bodies": [*names_w, "shell", "base_plate", "zone_wall"],
        "exclude_pairs": [[a, b] for i, a in enumerate(names_w) for b in names_w[i + 1:]]
        + [["shell", "base_plate"], ["shell", "zone_wall"], ["base_plate", "zone_wall"]]}})
    # I2: each plug through its opening, each open edge's way out
    plugs = plug_probes(s)
    steps += plugs
    mark["plugs"] = len(steps)
    pairs = [(n, part) for n, part, *_ in PLUG_PASSES] + [(n, part) for n, part, _ in OPEN_EDGES]
    names_p = [n for n, _ in pairs]
    steps.append({"command": "inspect.interference", "params": {
        "budget_s": 120, "bodies": [*names_p, *sorted({part for _, part in pairs})],
        "exclude_pairs": [[a, b] for i, a in enumerate(names_p) for b in names_p[i + 1:]]
        + [[n, part] for n in names_p for _, part in pairs if (n, part) not in pairs]
        + [["hcho_lid", "zone_wall"], ["hcho_lid", "base_plate"], ["zone_wall", "base_plate"]]}})
    # I3(b): the SEN66 at the ends of its depth tolerance, its port face on the ring: the front of
    # the deepest module clears the cradle and the zone wall, and the pad (free) still presses the
    # shallowest one
    ext = extremes(s)
    steps += ext
    names_e = [c["params"]["body_name"] for c in ext]
    steps.append({"command": "parameters.change", "params": {"changes": {"pad_squeeze": f"{s.v('pad_t - pad_gap')} mm"}}})
    mark["extremes"] = len(steps)
    steps.append({"command": "inspect.interference", "params": {
        "budget_s": 120, "bodies": [*names_e, *EXTREME_PARTS],
        "exclude_pairs": [[a, b] for i, a in enumerate(names_e) for b in names_e[i + 1:]]}})
    # 3b-1: the shell's face (window, pocket, ...) against its probes
    fprobes = face_probes(s)
    steps += fprobes
    names_f = [c["params"]["body_name"] for c in fprobes if c["params"].get("body_name")]
    mark["face"] = len(steps)
    steps.append({"command": "inspect.interference", "params": {
        "budget_s": 120, "bodies": [*names_f, *FACE_PARTS], "exclude_pairs": face_pairs(s)}})
    # 3b-2: the openings' open area, lower edge and fit (probes that overlap the base by design)
    oprobes = [c for c, *_ in opening_probes(s)] + usb_probes(s) + low_probes(s)
    steps += oprobes
    names_o = opening_run_bodies(s)
    mark["openings"] = len(steps)
    steps.append({"command": "inspect.interference", "params": {
        "budget_s": 120, "bodies": [*names_o, "base_plate", "shell"],
        "exclude_pairs": [[a, b] for i, a in enumerate(names_o) for b in names_o[i + 1:]] + [["base_plate", "shell"]]}})
    # 3b-2: R12, the tongue's distances and the grilles' separation as exact distances between solids
    steps += clear_probes(s)
    mark["clearance"] = len(steps)
    for probes, against in CLEAR_PAIRS.values():
        steps.append({"command": "inspect.clearance", "params": {"bodies": list(probes), "against": list(against), "clearance": 200}})
    steps.append({"command": "parameters.change", "params": {"changes": {n: f"{TOUCH_SQUEEZE} mm" for n in SQUEEZES}}})
    mark["touch"] = len(steps)
    steps.append({"command": "inspect.interference", "params": {"budget_s": 120, "bodies": sorted({b for p in TOUCHES for b in p})}})
    steps.append({"command": "parameters.change", "params": {"changes": {n: "0 mm" for n in SQUEEZES}}})
    steps.append({"command": "file.save", "params": {"path": str(save), "cache": False}})
    return {"commands": steps, "mark": mark}


def run(cli: str | None = None) -> dict:
    """Build the check design and return {inserted, interference, measure, touch} (the run's results)."""
    cli = cli or encbuild.cli_path()
    encbuild.BUILD_DIR.mkdir(parents=True, exist_ok=True)
    sc = check_script()
    script = encbuild.BUILD_DIR / "airq-check.json"
    script.write_text(json.dumps({"commands": sc["commands"]}, indent=1), encoding="utf-8")
    out = encbuild.BUILD_DIR / "airq-check.results.json"
    out.unlink(missing_ok=True)
    proc = subprocess.run([cli, "run", str(script), "--in", str(ENCLOSURE / airq.OUTPUT), "--results", "--quiet",
                           "--json-out", str(out)], capture_output=True, text=True)
    res = json.loads(out.read_text(encoding="utf-8")) if out.exists() else None
    if proc.returncode != 0 or not isinstance(res, list):
        raise RuntimeError(f"check run failed: {res if isinstance(res, dict) else proc.stderr or proc.stdout}")
    m = sc["mark"]
    return {"inserted": res[:6], "interference": res[m["interference"]], "measure": res[m["measure"]],
            "touch": res[m["touch"]], "nudge": res[m["nudge"]], "window": res[m["window"]], "extremes": res[m["extremes"]],
            "plugs": res[m["plugs"]], "face": res[m["face"]], "openings": res[m["openings"]],
            "clearance": {k: _near(res[m["clearance"] + i]) for i, k in enumerate(CLEAR_PAIRS)}}


def _near(res: dict) -> float:
    """The least distance in an `inspect.clearance` result (inf when nothing is within the search)."""
    return min([p["distance_mm"] for p in res["near"]] + [math.inf])


def opening_areas(s, res: dict) -> dict:
    """{probe: (open area measured, expected)} for every opening, from the openings run:
    (probe volume - its overlap with the part) / the thickness."""
    got = {}
    for p in res["interferences"]:
        a, b = (p["a"], p["b"]) if p["a"].startswith(("op_", "usb_", "low_")) else (p["b"], p["a"])
        got[(a, b)] = got.get((a, b), 0.0) + p["volume_mm3"]
    out = {}
    for c, part, th, exp in opening_probes(s):
        n = c["params"]["body_name"]
        out[n] = ((_volume(c, s) - got.get((n, part), 0.0)) / s.v(th), s.v(exp))
    return out


def nudge_faults(nudge: dict, s=None) -> list[str]:
    """N1: the nudged shells' contacts that are not on a datum face (none when the shell has its
    clearances): a nudge other than into a datum that meets anything, or a datum nudge that
    meets the base anywhere but on that face."""
    s = s or airq.build()
    out = []
    for p in nudge["interferences"]:
        a, b = (p["a"], p["b"]) if p["a"] in NUDGES else (p["b"], p["a"])
        lo, hi = p["bbox"]["min"], p["bbox"]["max"]
        datum = NUDGE_DATUMS.get(a)
        if datum is None or b != "base_plate":
            out.append(f"{a} meets {b} at {[round(c, 2) for c in lo]}..{[round(c, 2) for c in hi]}")
            continue
        k = "xyz".index(datum[0])
        face = s.v(datum[1])
        step = NUDGES[a][k]                       # the overlap lies between the face and the face + step
        f0, f1 = sorted((face, face + step))
        if not (f0 - 1e-3 <= lo[k] and hi[k] <= f1 + 1e-3):
            out.append(f"{a} meets the base off its datum: {datum[0]} {lo[k]:.3f}..{hi[k]:.3f}")
    return out


def window_fill(window: dict) -> dict:
    """{probe: (volume the rail and the zone wall fill, volume the shell overlaps)} (N2)."""
    out = {}
    for p in window["interferences"]:
        a, b = (p["a"], p["b"]) if p["a"].startswith("win_") else (p["b"], p["a"])
        fill, shell = out.get(a, (0.0, 0.0))
        out[a] = (fill + p["volume_mm3"], shell) if b != "shell" else (fill, shell + p["volume_mm3"])
    return out


def sections(measure: dict) -> dict:
    """Each air probe's section (mm2) from its measured box: the face named in AIR (the ring's is
    its circle, pi d^2 / 4 from its measured width)."""
    boxes = {b["name"]: b["bbox"] for b in measure["bodies"]}
    out = {}
    for name, (_, _, face) in AIR.items():
        lo, hi = boxes[name]["min"], boxes[name]["max"]
        dx, dy, dz = (hi[i] - lo[i] for i in range(3))
        if name == "air_outlet_ring":
            out[name] = math.pi * dx * dx / 4
        else:
            out[name] = {"x": dy * dz, "y": dx * dz, "z": dx * dy}[face]
    return out


BRANCHES = {   # plenum branch -> (its probes, the x it is cut at)
    "between the ring and H1": (("air_outlet_mid", "air_outlet_mid_top"), "outlet_x + ring_od / 2 + 0.5"),
    "at H1": (("air_outlet_h1", "air_outlet_h1_top"), "h1_x - standoff_d / 2"),
    "right of H1": (("air_outlet_right",), "h1_x + standoff_d / 2 + 0.3"),
}


def branch_need(s, x_expr: str, port: float = 330.1) -> float:
    """The outlet port area a plenum branch serves: the port's area times the share of the outlet
    grille's open area to the right of x (the grille's slots are alike, so the share is their count)."""
    v = s.v
    x = v(x_expr)
    x0, pitch, n = v("out_gx0"), v("out_pitch"), int(v("out_n"))
    right = sum(1 for i in range(n) if x0 + i * pitch >= x)
    return port * right / n


def branches(s, measured: dict) -> dict:
    """{branch: (section measured, area it serves)} for the outlet plenum (R25)."""
    return {name: (sum(measured[p] for p in probes), branch_need(s, x)) for name, (probes, x) in BRANCHES.items()}


def touch_volumes(touch: dict) -> dict:
    """{(a, b): overlap volume} for TOUCHES at gasket_squeeze = TOUCH_SQUEEZE."""
    got = {frozenset((p["a"], p["b"])): p["volume_mm3"] for p in touch["interferences"]}
    return {pair: got.get(frozenset(pair), 0.0) for pair in TOUCHES}


# --- distances the layout answers (arithmetic from the parameters and the boards' sources) ---------

def _box_gap(a, b) -> float:
    return math.sqrt(sum(max(0.0, lo2 - hi1, lo1 - hi2) ** 2 for (lo1, hi1), (lo2, hi2) in zip(a, b)))


def distances(s=None) -> dict:
    """The distances 3a's placements answer, from the design's values, interface.yaml and
    layout.yaml (U2: its footprint's courtyard)."""
    s = s or airq.build()
    v = s.v
    m = B.MAIN
    x0, y_front, z_top = v("board_x0"), v("board_y0"), v("board_z0") + v("board_t")
    dev = lambda X, Y: (x0 + X, y_front + v("board_d") - Y)       # noqa: E731  layout (X, Y) -> device (x, y)
    mod = m["antenna"]["module_body"]
    mh = B.module_h()
    ant = ((x0 + mod[0][0], x0 + mod[1][0]), tuple(sorted((dev(0, 0)[1], dev(0, mod[0][1])[1]))), (z_top, z_top + mh))
    u3 = ((x0 + mod[0][0], x0 + mod[1][0]), tuple(sorted((dev(0, mod[0][1])[1], dev(0, mod[1][1])[1]))), (z_top, z_top + mh))
    (ux0, uy0), (ux1, uy1) = B.layout_part("U2")["box"]
    u2 = ((x0 + ux0, x0 + ux1), tuple(sorted((dev(0, uy0)[1], dev(0, uy1)[1]))), (z_top, z_top + m["max_part_height"]))
    sen = ((v("sen_x0"), v("sen_x1")), (v("sen_y0"), v("sen_y1")), (v("floor_t") + v("foam"), v("sen_top")))
    tx1, ty0, tz0 = v("tongue_x1"), v("tongue_y0"), v("tongue_z0")
    tongue = ((tx1 - v("tongue_w"), tx1), (ty0, ty0 + v("tongue_dp")), (tz0, tz0 + v("tongue_t") + v("tongue_parts_h")))
    usb_x = v("usb_x")
    plug = ((usb_x - v("usb_plug_w") / 2, usb_x + v("usb_plug_w") / 2), (dev(0, 0)[1], v("D") + 20.0),
            (v("usb_z") - v("usb_plug_h") / 2, v("usb_z") + v("usb_plug_h") / 2))   # the overmold out the rear (typical, to confirm)
    r = v("boss_d") / 2
    bosses = [((x - r, x + r), (v("boss_y") - r, v("boss_y") + r), (v("floor_t") - v("head_depth"), v("floor_t") + v("boss_h")))
              for x in (-v("boss_x"), v("boss_x"))]
    rx, rz = v("rear_boss_x"), v("rear_boss_z")
    bosses.append(((rx - r, rx + r), (v("D") - v("wall") - v("clr_remove") - v("rear_boss_len"), v("D")), (rz - r, rz + r)))
    sfa = ((v("sfa_x0"), v("sfa_x0") + v("sfa_w")), (v("sfa_y0"), v("sfa_y0") + v("sfa_w")),
           (v("floor_t"), v("floor_t") + v("sfa_bt") + v("sfa_parts")))
    h1 = (v("h1_x"), v("h1_y"))
    usb_len = B.usb_len()
    j1 = ((usb_x - v("usb_sw") / 2, usb_x + v("usb_sw") / 2), tuple(sorted((dev(0, 0)[1], dev(0, usb_len)[1]))))
    h1_to_j1_edge = math.hypot(max(0.0, j1[0][0] - h1[0], h1[0] - j1[0][1]), max(0.0, j1[1][0] - h1[1], h1[1] - j1[1][1]))
    slots = [(v(f"cy0 + 0.6 + {i} * hg_pitch"), v(f"min(zw_z0, max(ledge_z0, lip + ((cy0 + 0.6 + {i} * hg_pitch) * cos_t - zw_tf - zone_t) / sin_t)) - hg_margin"))
             for i in range(5)]
    return {
        "antenna_to_sen66": _box_gap(ant, sen),
        "antenna_to_usb_plug": _box_gap(ant, plug),
        "antenna_to_bosses_and_screws": min(_box_gap(ant, b) for b in bosses),
        "antenna_to_standoff_screws": min(_box_gap(ant, ((x - 1, x + 1), (y - 1, y + 1), (z_top - 6, z_top + 2)))
                                          for x, y in ((v("h1_x"), v("h1_y")), (v("h2_x"), v("h2_y")))),
        "antenna_to_sfa40": _box_gap(ant, sfa),
        "tongue_to_u3": _box_gap(tongue, u3),
        "tongue_to_u2": _box_gap(tongue, u2),
        "h1_to_usb_c_shell": h1_to_j1_edge,
        "h1_to_usb_c_centre": math.hypot(h1[0] - usb_x, h1[1] - dev(0, usb_len / 2)[1]),
        "h1_free_above_plenum": v("board_z0") - v("zw_z0"),
        "antenna_end_to_rear_wall": (v("D") - v("wall")) - dev(0, mod[0][1])[1],
        "hcho_grille_open_mm2": sum(v("slot_w") * (top - v("grille_min_z")) for _, top in slots),
        "hcho_grille_lower_edge_z": v("grille_min_z"),
        "outlet_grille_open_mm2": v("out_n") * v("slot_w") * (v("out_gz1") - v("out_gz0")),
        "outlet_grille_lower_edge_z": v("out_gz0"),
        "intake_open_mm2": intake_open(s),
        # the intake slots open in the lip's outer face (y 0), the outlet slots in the rear wall's outer
        # face (y D), over overlapping x and z ranges: the openings are D apart, outer face to outer face (N7)
        "intake_to_outlet_grille": v("D"),
    }


TPU_E = (26.0, 50.0)        # TPU 95A tensile modulus range, MPa (filament data sheets; the print decides)
SEAT_E = 1800.0             # the base's plastic (PETG, the softer of PETG/ASA), MPa
PAD_FORCE_MAX = 15.0        # the most the pad may push (the seat's root stress across layers, the module's housing), N
PAD_MARGIN = 1.5            # the pad's least force over the least it needs


def sen66_hold(s=None) -> dict:
    """I3(b), arithmetic: the SEN66 is held by its port face on the outlet ring's land (its rear
    stop) and by the pad at its front; its depth tolerance goes into the pad.
    - pad_compression: the pad's compression at 20.8, 21.3 and 21.8 deep (of pad_t), the seat rigid;
    - front_clear_rail / front_clear_slant: a 21.8 module's connector face to the right rail, and
      its plinth's top front edge to the zone wall's slant (the plinth is inset plinth_inset);
    - wiper_force: the inlet blade's push on the port face for TPU_E (cantilever, 3 E I / L^3
      along the blade, over the module's height, the axial part sin^2 of its lean);
    - kern: the ring land's kern radius, (r_o^2 + r_i^2) / (4 r_o): the land stays loaded all round
      while the ring's reaction acts inside it (review round 3);
    - pad_force_min: the least pad force that keeps that reaction inside the kern against the
      blade's moment about the outlet axis; pad_force_spec = PAD_MARGIN x that, the least the pad
      must give at its least compression;
    - seat_k: the pad seat's stiffness, a seat_t plate as two cantilevers in parallel, up from the
      floor and out from the side rail, over pad_w + 2 seat_t (B1); seat_give at pad_force_spec
      and PAD_FORCE_MAX, and the compression range with that give (the pad's least compression
      uses the least force, its most the most);
    - seat_stress: the root bending stress across the layers at PAD_FORCE_MAX (its share up from
      the floor)."""
    s = s or airq.build()
    v = s.v
    tol, gap, t = v("sen_d_tol"), v("pad_gap"), v("pad_t")
    comp = {d: 1 - (gap + k * tol) / t for d, k in ((21.3 - 0.5, 1), (21.3, 0), (21.3 + 0.5, -1))}
    front = v("sen_y0") - tol
    pin = _SEN("plinth_inset")
    z_edge = v("sen_top") - pin
    y_slant = v(C.yb(str(z_edge)))
    rail_r = v("sen_y0 - sen_d_tol - clr_align")
    a = math.radians(s.params["wiper_deg"].value)
    L = (v("plate_y0") - v("sen_y1") + v("wiper_squeeze")) / math.cos(a)
    inertia = v("wiper_t") ** 3 / 12
    force = [3 * e * inertia / (L ** 3 * math.sin(a) ** 2) * v("sen_up") * v("wiper_squeeze") for e in TPU_E]
    arm = abs((v("wiper_x1") - v("wiper_lean") - v("wiper_w") / 2) - v("outlet_x"))
    ro, ri = v("ring_od") / 2, v("ring_bore") / 2
    kern = (ro ** 2 + ri ** 2) / (4 * ro)
    need = max(force) * (1 + arm / kern)
    spec = PAD_MARGIN * need
    b, st = v("pad_w") + 2 * v("seat_t"), v("seat_t")
    lv, lh = v("outlet_z") - v("floor_t"), v("outlet_x") + v("tub_x")
    ei3 = 3 * SEAT_E * b * st ** 3 / 12
    kv, kh = ei3 / lv ** 3, ei3 / lh ** 3
    k = kv + kh
    stress = PAD_FORCE_MAX * kv / k * lv / (b * st ** 2 / 6)
    comp_give = {20.8: 1 - (gap + tol + spec / k) / t, 21.3: 1 - (gap + spec / k) / t, 21.8: 1 - (gap - tol + PAD_FORCE_MAX / k) / t}
    return {"pad_compression": comp, "front_clear_rail": front - rail_r, "front_clear_slant": front - y_slant,
            "wiper_force": tuple(force), "kern": kern, "arm": arm, "pad_force_min": need, "pad_force_spec": spec,
            "pad_pressure_kpa_spec": spec / (v("pad_w") * v("pad_h")) * 1000,
            "pad_pressure_kpa_max": PAD_FORCE_MAX / (v("pad_w") * v("pad_h")) * 1000,
            "seat_k": k, "seat_give": (spec / k, PAD_FORCE_MAX / k), "pad_compression_with_give": comp_give,
            "seat_stress": stress}


FOAM_KPA = (30.0, 100.0)    # closed-cell PU foam at 25 % compression, kPa (soft to firm; to confirm)


def seal_forces(s=None) -> dict:
    """Round 3, B6 and the zone seal: what the seals push on their parts at their squeeze (TPU
    95A at TPU_E, foam at FOAM_KPA), with the stresses that matter.
    - zone_seal: foam on the lip, between the boss pockets (the lip's top must not bow);
    - drawer_front: the drawer grommet's front half on the notch's front face, and the share on
      the sliver at the boss notch, carried by the key: its root bending stress;
    - j4_lid: the J4 grommet's push on the lid (its stack meets the lid at contact: 0);
    - top_seal: the foam strip over the SEN66 pushing the zone wall up (H1's clamp takes it)."""
    s = s or airq.build()
    v = s.v
    zone = tuple(k / 1000 * 2 * v("bp_x0") * v("ledge_t") for k in FOAM_KPA)
    half = v("pt_yh") - v("pt_y0")
    band_h = v("zone_t") / v("sin_t")
    length = v("pt_x1") + v("inner_x") - v("clr_remove")
    drawer = tuple(e * v("drawer_squeeze") / half * length * band_h for e in TPU_E)
    sliver_len = v("-bp_x0 - 1.5") - v("-tub_x - iwall + 0.5")
    on_sliver = tuple(f * (v("-boss_x + boss_d / 2 + clr_remove") + v("inner_x") - v("clr_remove")) / length for f in drawer)
    key_z = sliver_len * v("key_w") ** 2 / 6
    key_stress = tuple(f * v("key_h") / 2 / key_z for f in on_sliver)
    top = tuple(k / 1000 * (1 + 1) * (v("top_seal_x1") - v("top_seal_x0")) * v("sen_d") for k in FOAM_KPA)   # x2: 50 % vs 25 %
    return {"zone_seal_n": zone, "zone_seal_compression": v("seal_squeeze") / (v("seal_t") + v("seal_squeeze")),
            "drawer_front_n": drawer, "drawer_on_sliver_n": on_sliver, "key_stress_mpa": key_stress,
            "j4_lid_n": 0.0, "top_seal_n": top}


def intake_open(s) -> float:
    """Open area of the two intake rows as cut: in_n_l slots in the left span and in_n_r in the
    right span, in two rows, each slot in_len_* long and slot_w high."""
    v = s.v
    return 2 * v("slot_w") * (v("in_n_l") * v("in_len_l") + v("in_n_r") * v("in_len_r"))


def insertion_probe(s=None) -> list[str]:
    """I1, arithmetic: the shell is lowered onto the assembled base along -z (R24). Each front
    floor boss must pass the zone wall's notch and stay out of the board's footprint; the rear
    boss stays above and left of the board. The geometric sweep is in the check design
    (`sweeps`). Returns the conflicts (none when it assembles)."""
    s = s or airq.build()
    v = s.v
    out = []
    r = v("boss_d") / 2
    board = ((v("board_x0"), v("board_x0") + v("board_w")), (v("board_y0"), v("board_y0") + v("board_d") + v("antenna_out")))
    for i, x in enumerate((-v("boss_x"), v("boss_x")), 1):
        y = v("boss_y")
        notch = s.commands[[c["params"].get("name") for c in s.commands].index(f"Zone wall boss notch {i}")]["params"]
        nx0, ny0 = v(notch["corner"][0]), v(notch["corner"][1])
        nx1, ny1 = nx0 + v(notch["length"]), ny0 + v(notch["width"])
        if not (nx0 <= x - r and x + r <= nx1 and ny0 <= y - r and y + r <= ny1):
            out.append(f"floor boss {i} does not pass the zone wall's notch")
        if board[0][0] < x + r and x - r < board[0][1] and board[1][0] < y + r and y - r < board[1][1]:
            out.append(f"floor boss {i} passes through the board's footprint")
    rx, rz = v("rear_boss_x"), v("rear_boss_z")
    if rx + r > board[0][0] and rz - r < v("board_z0") + v("board_t") + B.MAIN["max_part_height"]:
        out.append("rear boss passes the board")
    return out


if __name__ == "__main__":
    d = distances()
    print(json.dumps({k: round(x, 2) for k, x in d.items()}, indent=1))
    print("insertion probe:", insertion_probe() or "clear")
    if "--run" in sys.argv:
        r = run()
        i = r["interference"]
        print("interference: count", i["count"], "checked", i["checked"], "unchecked", len(i["unchecked"]),
              "pairs", i["pairs_candidate"], i["pairs_intersected"], "excluded", i["pairs_excluded"])
        for pair in i["interferences"][:40]:
            print("  ", pair["a"], "|", pair["b"], round(pair["volume_mm3"], 3), [round(c, 2) for c in pair["center"]])
        for u in i["unchecked"][:10]:
            print("  unchecked", u)
        print("sections:", {k: round(x, 1) for k, x in sections(r["measure"]).items()})
        print("outlet branches (section, serves):", {k: (round(a, 1), round(b, 1)) for k, (a, b) in branches(airq.build(), sections(r["measure"])).items()})
        print("touch at squeeze", TOUCH_SQUEEZE, ":", {f"{a}|{b}": round(x, 3) for (a, b), x in touch_volumes(r["touch"]).items()})
        print("nudge (N1):", [(p["a"], p["b"], round(p["volume_mm3"], 3), [round(c, 3) for c in p["bbox"]["min"]],
                               [round(c, 3) for c in p["bbox"]["max"]]) for p in r["nudge"]["interferences"]],
              "faults:", nudge_faults(r["nudge"]) or "none")
        print("plugs and open edges (I2):", [(p["a"], p["b"], round(p["volume_mm3"], 3)) for p in r["plugs"]["interferences"]] or "clear",
              "checked", r["plugs"]["checked"])
        print("extremes (I3b) overlap depth along y:", {f"{a}|{b}": round(x, 3) for (a, b), x in extreme_reach(r["extremes"]).items()})
        need = window_backing(airq.build())
        print("window (N2) fill / need / shell:", {k: (round(f, 2), round(need[k], 2), round(sh, 3))
                                                   for k, (f, sh) in window_fill(r["window"]).items()})
        s = airq.build()
        o = r["openings"]
        print("openings (open area measured / expected):", {k: (round(a, 2), round(e, 2)) for k, (a, e) in opening_areas(s, o).items()})
        vols = {}
        for p in o["interferences"]:
            n = p["a"] if p["a"].startswith(("usb_", "low_")) else p["b"]
            if n.startswith(("usb_", "low_")):
                vols[(n, p["b"] if n == p["a"] else p["a"])] = round(p["volume_mm3"], 3)
        print("usb / low probes (material met):", vols, "expected usb:", {k: round(x, 3) for k, x in usb_expect(s).items()})
        print("clearance (exact distances):", {k: round(x, 2) for k, x in r["clearance"].items()})
