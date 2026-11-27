"""The airQ mini check design: enclosure/airq-mini.sc with every reference part placed (Task 4a).

The construction and the probes are the airQ's (airq_check, whose helpers this module uses); the
places are the mini's. `check_script()` returns a command script for `solidcraft-cli run --in
enclosure/airq-mini.sc`. It:
- inserts the three references the mini holds (ref_sen66, ref_tongue, ref_main; ref_main only
  here, R8) at their places: the SEN66 ports to the rear with its inlet end left, the tongue on
  edge in the intake passage, the board;
- sets every squeeze and preload to 0, so the seals' faces touch what they seal (R9);
- adds the check bodies, all placed by the design's parameters: `ko_*` keep-outs (the SEN66's
  plug and its cable's route along the floor, down the passage's front, over the tongue and up
  through the drawer; the tongue's Qwiic plug and its cable up the drawer; J2's and J4's plugs
  and their drop to the drawer), `air_*` probes (R25: free sections, touching but not
  overlapping), and the shell's sweep along -z (`sweep_*`, `shell_up_*`);
- runs the interference check, measures, nudges the shell (N1), sweeps the drawer's way out
  (cables laid in from the side), sets the SEN66 at its depth extremes (I3(b)), measures R12 and
  the tongue's distances as solid-to-solid clearances, and checks that the seals touch;
- saves enclosure/.build/airq-mini-check.sc.
A second run on the saved check design measures the intake passage's section with the tongue's
real board in it (`passage_sections`): slabs across the passage overlap the tongue, its pin and
the cables by design, and the free section is (slab - overlaps) / thickness.

Run it with `uv run --with pyyaml python enclosure/src/airq_mini_check.py --run`, or through
tests/enclosure/test_airq_mini_check.py.
"""
from __future__ import annotations

import json
import math
import sys

import airq_check as A
import airq_mini
import airq_mini_face as MF
import board_sources as B
import enclosure_common as C
import encbuild
from airq_check import _box, _box_gap, _cyl, _near, _rows
from sclib import ENCLOSURE

REF = ENCLOSURE / "reference"
CHECK_SC = encbuild.BUILD_DIR / "airq-mini-check.sc"
REFS = ("ref_sen66", "ref_tongue", "ref_main")
SHELL_PARTS = ("shell", "orange_dot")
# Task 4b: the parts that ride in the shell (the guides in their slots, the stop on the ribs): their raised copies
# <tag>_up_<dz> are swept with the shell
RIDERS = (("light_guide_co2", "gco2"), ("light_guide_pm", "gpm"), ("guide_stop", "gstop"))
SQUEEZES = ("gasket_squeeze", "wiper_squeeze", "pad_squeeze", "ring_preload", "root_squeeze", "drawer_squeeze", "bore_squeeze",
            "hold_squeeze", "drawer_floor_squeeze",
            "seal_squeeze", "top_seal_squeeze")
TOUCHES = (("gasket_out", "sen66_body"), ("gasket_in", "sen66_body"), ("gasket_in", "base_plate"), ("zone_seal", "base_plate"),
           ("sen66_pad", "sen66_body"), ("grommet_zone_a", "zone_wall"), ("grommet_zone_b", "zone_wall"),
           ("grommet_zone_a", "base_plate"), ("sen66_top_seal", "zone_wall"),
           ("shell", "zone_wall"))                 # review I1: the shell's hold-down pads bear on the zone wall's top
# the shell's datums (N1): the floor and the rear wall, and (review I1) the zone wall's top under its hold-down pads
NUDGE_DATUMS = {"shell_ny_p": (("base_plate", "y", "D - wall"),), "shell_nz_m": (("base_plate", "z", "floor_t"), ("zone_wall", "z", "zw_z1"))}


def nudge_faults(nudge: dict, s=None) -> list[str]:
    """airq_check.nudge_faults with the mini's datums: a nudged shell may meet a part only on that part's datum face."""
    s = s or airq_mini.build()
    out = []
    for p in nudge["interferences"]:
        a, b = (p["a"], p["b"]) if p["a"] in A.NUDGES else (p["b"], p["a"])
        lo, hi = p["bbox"]["min"], p["bbox"]["max"]
        datum = next((d for d in NUDGE_DATUMS.get(a, ()) if d[0] == b), None)
        if datum is None:
            out.append(f"{a} meets {b} at {[round(c, 2) for c in lo]}..{[round(c, 2) for c in hi]}")
            continue
        k = "xyz".index(datum[1])
        face = s.v(datum[2])
        f0, f1 = sorted((face, face + A.NUDGES[a][k]))
        if not (f0 - 1e-3 <= lo[k] and hi[k] <= f1 + 1e-3):
            out.append(f"{a} meets {b} off its datum: {datum[1]} {lo[k]:.3f}..{hi[k]:.3f}")
    return out
EXTREME_PARTS = A.EXTREME_PARTS


def placements(s=None) -> list[dict]:
    """insert_design steps for the references, placed by the design's parameters (rigid, det +1)."""
    s = s or airq_mini.build()
    return [
        # SEN66, ports to the rear, inlet end left: module x -> +x, module z (port face -> connector) -> -y,
        # module y (from the square-inlet edge) -> +z (square inlet low): the airQ's pose turned 180 deg about y
        {"path": REF / "sen66.sc", "matrix": _rows([[1, 0, 0], [0, 0, -1], [0, 1, 0]], ["sen_x0", "sen_y1", "floor_t + foam"])},
        # tongue on edge: its x (the long edge) -> +z, its y (STEP -Y: front edge at 0, rear at -13) -> -y, its z (parts) -> +x
        {"path": REF / "airq-tongue.sc", "matrix": _rows([[0, 0, 1], [0, -1, 0], [1, 0, 0]], ["tongue_x0", "tongue_y0", "tongue_z0"])},
        # main board: STEP frame as it lies (front edge at STEP y -30)
        {"path": REF / "airq-main.sc", "matrix": _rows([[1, 0, 0], [0, 1, 0], [0, 0, 1]], ["board_x0", "board_y0 + board_d", "board_z0"])},
    ]


RUN0, RUN1 = "sen_y0 - sen_d_tol - clr_align - cable_gh_d", "sen_y0 - sen_d_tol - clr_align"   # the SEN66 cable along the front
TURN0, TURN1 = "bp_y1 + clr_align", "bp_y1 + clr_align + cable_gh_d"                           # ... and at the passage's front
DROP_X0, DROP_X1 = "-tub_x + clr_align", "-tub_x + clr_align + cable_gh_d"                     # its drop and run over the tongue
OVER_Z0, OVER_Z1 = "tongue_top + clr_align", "tongue_top + clr_align + cable_gh_d"


def keepouts(s) -> list[dict]:
    """The plugs and the cables' routes (the airQ's I2), all to confirm with the cables bought."""
    ztop = "board_z0 + board_t"
    b = [
        # SEN66 plug on its connector face (front), the cable's bend down, back to the run line along the floor
        _box("ko_sen66_plug", "plug_x0", "sen_y0 - sen_plug_out", "sen_mid - sen_plug_h / 2", "plug_x1", "sen_y0", "sen_mid + sen_plug_h / 2"),
        _box("ko_sen66_bend", "plug_x0", "sen_y0 - sen_bend_out", "floor_t", "plug_x1", "sen_y0 - sen_plug_out", "sen_mid + sen_bend_top"),
        _box("ko_sen66_bend_low", "plug_x0", "sen_y0 - sen_bend_out", "floor_t", "plug_x1", RUN0, "floor_t + cable_gh_d"),
        # along the floor in front of the module to the left, behind the left boss pocket, into the passage
        _box("ko_cable_run", "-bp_x0 + clr_align", RUN0, "floor_t", "plug_x1", RUN1, "floor_t + cable_gh_d"),
        _box("ko_cable_jog", "-bp_x0 + clr_align", RUN0, "floor_t", "sen_x0 - clr_align", TURN1, "floor_t + cable_gh_d"),
        _box("ko_cable_turn", DROP_X0, TURN0, "floor_t", "-bp_x0 + clr_align", TURN1, "floor_t + cable_gh_d"),
        # up the passage's front (in front of the tongue), back over the tongue, up into the drawer
        _box("ko_cable_drop", DROP_X0, TURN0, "floor_t + cable_gh_d", DROP_X1, TURN1, OVER_Z1),
        _box("ko_cable_over", DROP_X0, TURN1, OVER_Z0, DROP_X1, "gh_y + cable_gh_d / 2", OVER_Z1),
        _cyl("ko_cable_gh", ["cab_x", "gh_y", OVER_Z0], "cable_gh_d", f"zw_z1 + 0.5 - ({OVER_Z0})"),
        # the tongue's Qwiic plug, its cable's turn behind it and up into the drawer
        _box("ko_tongue_plug", "tongue_x0 + tongue_t", "tongue_y0 + tq_mate", "tongue_z0 + tq_x0", "tongue_x0 + tongue_t + tq_h", "tq_plug_y1",
             "tongue_z0 + tq_x1"),
        _box("ko_qw_turn", "cab_x - cable_qw_d / 2", "tq_plug_y1", "tongue_z0 + tq_x0", "tongue_x0 + tongue_t + tq_h", "qw_y + cable_qw_d / 2",
             "tongue_z0 + tq_x1"),
        _cyl("ko_cable_qwiic", ["cab_x", "qw_y", "tongue_z0 + tq_x0"], "cable_qw_d", "zw_z1 + 0.5 - tongue_z0 - tq_x0"),
        # J2 and J4 on the board's left edge: the plugs, and the cables' drop beside the board to the drawer
        _box("ko_j2_plug", "j2_face_x - plug_out", "j2_y0", ztop, "j2_face_x", "j2_y1", f"{ztop} + j2_h"),
        _box("ko_j4_plug", "j4_face_x - plug_out", "j4_y0", ztop, "j4_face_x", "j4_y1", f"{ztop} + j4_h"),
        _box("ko_route", "-inner_x + clr_align", "min(j2_y0, dr_y0)", "zw_z1", "board_x0 - clr_align", "max(j4_y1, dr_y1)", f"{ztop} + j2_h"),
    ]
    return b


AIR = {   # probe -> (path, R25 minimum, the probe's face that is the section)
    "air_intake_gap": ("intake: the port gap behind the module's inlet end, to the inlets", 77.3, "x"),
    "air_intake_front": ("intake: the sensor zone in front of the SEN66, over its cable, left of its plug", 77.3, "x"),
    "air_passage_mouth": ("intake: the passage's mouth beside the cable's drop, over the cable's turn", 77.3, "y"),
    "air_outlet_ring": ("outlet: the ring's bore (gasket_out)", 330.1, "y"),
    "air_outlet_left": ("outlet: the plenum left of the ring", None, "x"),
    "air_outlet_left_top": ("outlet: the plenum left of the ring, in front of the rib", None, "x"),
    "air_outlet_h1": ("outlet: the plenum behind H1's post", None, "x"),
    "air_outlet_grille": ("outlet grille: the free air behind its slots, in the plenum", None, "y"),
    "air_slots_front": ("intake rows: the free air behind every slot, to 0.1 in front of the SEN66 cable bend's keep-out (only slots facing free air count)", None, "y"),
    "air_exhaust_left": ("exhaust: the free air behind its slots left of the antenna strip", None, "y"),
    "air_exhaust_top": ("exhaust: the free air behind its slots over the antenna strip", None, "y"),
    "air_usb_axis": ("USB-C: J1's shell axis out through the opening", None, "y"),
}
LSW_STEPS = 12          # the light-sensor window's line to the VEML7700, as small free boxes along it


OPENING_AIR = ("air_outlet_grille", "air_slots_front", "air_exhaust_left", "air_exhaust_top", "air_usb_axis") + tuple(
    f"air_lsw_{k}" for k in range(LSW_STEPS))     # the free air in front of an opening shares air with the paths' probes


def air_probes(s) -> list[dict]:
    """The free sections of the internal air paths (R25), from the parameters. Each must touch and
    not overlap anything; its section is its face in the flow."""
    x_l = "outlet_x - ring_od / 2"
    return [
        _box("air_intake_gap", "sen_x0", "sen_y1", "floor_t", "sen_x0 + 1.0", "plate_y0", "zw_z0"),
        _box("air_intake_front", "plug_x0 - 1.5", "wall + 0.1", "floor_t + cable_gh_d", "plug_x0 - 1.0", RUN1, "ledge_z0"),
        _box("air_passage_mouth", DROP_X1, "tongue_y0 - 0.5", "floor_t + cable_gh_d", "sen_x0", "tongue_y0", "zw_z0"),
        _cyl("air_outlet_ring", ["outlet_x", "sen_y1", "outlet_z"], "ring_bore", "plate_y1 - sen_y1", axis="Y"),
        _box("air_outlet_left", f"{x_l} - 0.9", "plate_y1", "floor_t", f"{x_l} - 0.5", "D - wall", "zw_z0 - rib_d"),
        _box("air_outlet_left_top", f"{x_l} - 0.9", "plate_y1", "zw_z0 - rib_d", f"{x_l} - 0.5", "D - wall - rib_d", "zw_z0"),
        _box("air_outlet_h1", "h1_x - 0.2", "h1_y + standoff_d / 2", "floor_t", "h1_x + 0.2", "D - wall", "zw_z0 - rib_d"),
        _box("air_outlet_grille", "out_gx0", "D - wall - 3.0", "out_gz0", "out_gx1", "D - wall", "out_gz1"),
        # Task 4b: behind the openings
        _box("air_slots_front", "row_x0", "wall", "slot_row1_z", "row_x1", "sen_y0 - sen_bend_out - 0.1", "slot_row3_z + slot_w"),
        _box("air_exhaust_left", "exh_x0", "D - wall - 3.0", "exh_z0", f"{ANT_X0} - clr_align", "D - wall", "exh_z1"),
        _box("air_exhaust_top", ANT_X0, "D - wall - 3.0", f"{ANT_TOP} + clr_align", "exh_gx1", "D - wall", "exh_z1"),
        _box("air_usb_axis", "usb_x - usb_sw / 2", "D - wall", "usb_z - usb_sh / 2", "usb_x + usb_sw / 2", "D", "usb_z + usb_sh / 2"),
    ] + lsw_probes(s)


ANT_X0 = f"(board_x0 + {B.MAIN['antenna']['module_body'][0][0]})"          # the antenna strip's left end (interface.yaml)
ANT_TOP = f"(board_z0 + board_t + {B.module_h()})"                           # its top (the module's height)


def lsw_line(s, f: float) -> tuple:
    """The point a fraction f along the light-sensor window's line, from the window's inner face (lip,
    y = wall) to the VEML7700's window on the tongue, as expressions."""
    def at(a, b):
        return f"({a}) + (({b}) - ({a})) * {f:.6f}"
    return at("lsw_x", "veml_wx"), at("wall", "veml_wy"), at("lsw_z", "veml_wz")


def lsw_probes(s) -> list[dict]:
    """Small free boxes (0.4 a side) along the window's line to the VEML7700: the first 0.3 behind the
    lip's inner face, the last 0.9 short of the sensor's window (the tongue's board is not air)."""
    out = []
    v = s.v
    ln = math.dist((v("lsw_x"), v("wall"), v("lsw_z")), (v("veml_wx"), v("veml_wy"), v("veml_wz")))
    for k in range(LSW_STEPS):
        f = (0.3 + (ln - 1.2) * k / (LSW_STEPS - 1)) / ln
        x, y, z = lsw_line(s, f)
        out.append(_box(f"air_lsw_{k}", f"{x} - 0.2", f"{y} - 0.2", f"{z} - 0.2", f"{x} + 0.2", f"{y} + 0.2", f"{z} + 0.2"))
    return out


BRANCHES = {   # plenum branch -> (its probes, the x it is cut at); the ring is at the right, the flow goes left
    "left of the ring": (("air_outlet_left", "air_outlet_left_top"), "outlet_x - ring_od / 2 - 0.5"),
    "behind H1": (("air_outlet_h1",), "h1_x - standoff_d / 2"),
}


def branches(s, measured: dict) -> dict:
    """{branch: (section measured, area it serves)} for the outlet plenum (R25)."""
    return {name: (sum(measured[p] for p in probes), A.branch_need(s, x, side="left")) for name, (probes, x) in BRANCHES.items()}


OPEN_EDGES = (   # (probe, part, region): the drawer's way out to the zone wall's left end (cables laid in from the side)
    ("edge_drawer", "zone_wall", ("-inner_x - 1", "dr_y0", "zw_z0 - 0.5", "cab_x", "dr_y1", "zw_z1 + 1")),
)


def plug_probes(s) -> list[dict]:
    return [_box(name, *region) for name, _, region in OPEN_EDGES]


def clear_probes(s) -> list[dict]:
    """R12 and the tongue's distances on the geometry (`inspect.clearance`): the antenna strip, U3,
    U2, the USB plug's overmold, the shell's bosses and the board's screws as probe solids from the
    boards' sources; the tongue's envelope on edge."""
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
        _box("cl_tongue", "tongue_x0", "tongue_y0", "tongue_z0", "tongue_x0 + tongue_t + tongue_parts_h", "tongue_y0 + tongue_dp", "tongue_top"),
        _box("cl_usb_plug", "usb_x - usb_plug_w / 2", dev_y(0), "usb_z - usb_plug_h / 2", "usb_x + usb_plug_w / 2", "D + 20.0",
             "usb_z + usb_plug_h / 2"),
    ]
    for i, sx in enumerate(("-boss_x", "boss_x"), 1):
        b.append(_cyl(f"cl_boss_{i}", [sx, "boss_y", "floor_t - head_depth"], "boss_d", "boss_h + head_depth"))
    b.append(_cyl("cl_boss_3", ["rear_boss_x", "D - wall - clr_remove - rear_boss_len", "rear_boss_z"], "boss_d",
                  "rear_boss_len + wall + clr_remove", axis="Y"))
    b.append(_cyl("cl_screw_1", ["h1_x", "h1_y", "board_z0 - pilot_depth"], "screw_d", "pilot_depth + board_t + 2.0"))
    b.append(_cyl("cl_screw_2", ["h2_x", "h2_y", "board_z0 - zw_pilot_depth"], "screw_d", "zw_pilot_depth + board_t + 2.0"))
    return b


CLEAR_PAIRS = {
    "antenna_to_sen66": (("cl_antenna",), ("sen66_body",)),
    "antenna_to_usb_plug": (("cl_antenna",), ("cl_usb_plug",)),
    "antenna_to_inserts": (("cl_antenna",), ("cl_boss_1", "cl_boss_2", "cl_boss_3")),
    "antenna_to_screws": (("cl_antenna",), ("cl_screw_1", "cl_screw_2")),
    "tongue_to_u3": (("cl_tongue",), ("cl_u3",)),
    "tongue_to_u2": (("cl_tongue",), ("cl_u2",)),
    "intake_to_outlet": (("op_intake",), ("op_outlet",)),       # the openings' inner faces (the probes), Task 4b
}


def check_bodies(s) -> list[str]:
    return [c["params"]["body_name"] for c in keepouts(s) + air_probes(s) + A.sweeps(s, riders=RIDERS) if c["params"].get("body_name")]


# --- Task 4b: probes over the openings and the face (they overlap their part by design: a run of their own) ---
def opening_probes(s) -> list[tuple[dict, str, str, str]]:
    """(probe, part, thickness, expected open area) per opening, as airq_check.opening_probes: the open
    area is (probe volume - its overlap with the part) / the thickness."""
    sp = "slot_w"
    return [
        (_box("op_intake", "row_x0 - 0.6", "0", "slot_row1_z - 0.6", "row_x1 + 0.6", "wall", f"slot_row3_z + {sp} + 0.4"), "base_plate", "wall",
         f"3 * in_n * in_len * {sp}"),
        (_cyl("op_lsw", ["lsw_x", "0", "lsw_z"], "lsw_d + 1.0", "wall", axis="Y"), "base_plate", "wall", "3.141592653589793 * lsw_d * lsw_d / 4"),
        (_box("op_outlet", "out_gx0", "D - wall", "out_gz0", "out_gx1", "D", "out_gz1"), "base_plate", "wall", f"out_n * {sp} * (out_gz1 - out_gz0)"),
        (_box("op_exhaust", "exh_x0", "D - wall", "exh_z0", "exh_gx1", "D", "exh_z1"), "base_plate", "wall", f"exh_n * {sp} * (exh_z1 - exh_z0)"),
    ]


def opening_areas(s, res: dict) -> dict:
    """{probe: (open area measured, expected)} from the openings run (airq_check.opening_areas)."""
    got = {}
    for p in res["interferences"]:
        a, b = (p["a"], p["b"]) if p["a"].startswith(("op_", "usb_", "low_")) else (p["b"], p["a"])
        got[(a, b)] = got.get((a, b), 0.0) + p["volume_mm3"]
    out = {}
    for c, part, th, exp in opening_probes(s):
        n = c["params"]["body_name"]
        out[n] = ((A._volume(c, s) - got.get((n, part), 0.0)) / s.v(th), s.v(exp))
    return out


def low_probes(s) -> list[dict]:
    """Nothing opens below grille_min_z: slabs z 0 ... 10 over the lip, the rear wall, both rails and both
    of the shell's side walls must be all material (airq_check.low_probes, both sides)."""
    z = "grille_min_z"
    return [_box("low_lip", "-W / 2", "0", "0", "W / 2", "wall - clr_remove", z),
            _box("low_rear", "-W / 2", "D - wall", "0", "W / 2", "D", z),
            _box("low_rail_r", "tub_x", "bp_y1", "floor_t", "tub_x + iwall", "D - wall", z),
            _box("low_rail_l", "-tub_x - iwall", "bp_y1", "floor_t", "-tub_x", "D - wall", z),
            _box("low_side_r", "inner_x", "wall + clr_remove", "floor_t", "W / 2", "D - wall", z),
            _box("low_side_l", "-W / 2", "wall + clr_remove", "floor_t", "-inner_x", "D - wall", z)]


LOW_PARTS = {"low_lip": "base_plate", "low_rear": "base_plate", "low_rail_r": "base_plate", "low_rail_l": "base_plate",
             "low_side_r": "shell", "low_side_l": "shell"}


def face_probes(s) -> list[dict]:
    """Probes in the face frame (airq_check.sbox): each band slot open over its length and height, and a
    0.05 ring round it in the wall; each label's deboss (its box less the shell in it is the letters'
    volume) and the solid 0.05 under it; the flexure's beam, the pad rod's end and its gap to SW1."""
    b = []
    for h in ("co2", "pm"):
        b += A.sbox(s, f"fp_slot_{h}", f"band_{h}_x0 + 0.05", f"band_{h}_x1 - 0.05", "band_f0 - lip + 0.05", "band_f1 - lip - 0.05", "0", "wall")
        b += A.sbox(s, f"fp_ring_{h}", f"band_{h}_x0 - 0.05", f"band_{h}_x1 + 0.05", "band_f0 - lip - 0.05", "band_f1 - lip + 0.05",
                    "0.05", "wall - 0.05")
    for h, x0, x1 in LABEL_BOXES:
        b += A.sbox(s, f"fp_label_{h}", x0, x1, "label_f0 - lip - label_sub_drop - 1", "label_f1 - lip + 1", "0", "label_depth")
        b += A.sbox(s, f"fp_label_{h}_floor", x0, x1, "label_f0 - lip - label_sub_drop - 1", "label_f1 - lip + 1", "label_depth + 0.01",
                    "label_depth + 0.06")
    b += A.sbox(s, "fp_beam", "flex_x0 + 0.5", "flex_x1 - 0.5", "flex_s0 + 1", "flex_s0 + 2", "0", "wall + 0.3")
    b.append(_box("fp_pad_end", "sw_x - 0.5", "y_pad - 0.1", "sw_z - 0.5", "sw_x + 0.5", "y_pad", "sw_z + 0.5"))
    b.append(_box("fp_pad_gap", "sw_x - 0.5", "y_pad", "sw_z - 0.5", "sw_x + 0.5", "sw_tip", "sw_z + 0.5"))
    return b


LABEL_BOXES = (("co2", "label_co_x - label_co_w / 2 - 1", "label_sub_x + label_sub_w / 2 + 1"),
               ("pm", "label_pm_x - 2.01 * label_h - 1", "label_pm_x + 2.01 * label_h + 1"))


def _names(cmds) -> list[str]:
    return [c["params"]["body_name"] for c in cmds if c["params"].get("body_name")]


def check_script(save=CHECK_SC, budget_s: float = 900) -> dict:
    s = airq_mini.build()
    steps = [{"command": "component.insert_design", "params": {"path": str(pl["path"]), "matrix": pl["matrix"]}} for pl in placements(s)]
    steps.append({"command": "parameters.change", "params": {"changes": {n: "0 mm" for n in SQUEEZES}}})
    steps += keepouts(s) + air_probes(s) + A.sweeps(s, riders=RIDERS)
    names = check_bodies(s)
    mark = {"interference": len(steps)}
    steps.append({"command": "inspect.interference", "params": {
        "budget_s": budget_s, "exclude_pairs": A.exclusions(names, refs=REFS, riders=RIDERS, shell_parts=SHELL_PARTS, borne=(),
                                                            opening_air=OPENING_AIR)}})
    mark["measure"] = len(steps)
    steps.append({"command": "inspect.measure", "params": {"summary": True}})
    # N1: the shell nudged each way meets the base only on its datums
    steps += A.nudges(s)
    mark["nudge"] = len(steps)
    steps.append({"command": "inspect.interference", "params": {
        "budget_s": 120, "bodies": [*A.NUDGES, *A.NUDGE_PARTS],
        "exclude_pairs": [[a, b] for i, a in enumerate(A.NUDGES) for b in list(A.NUDGES)[i + 1:]]}})
    # I2: the drawer's way out (no plug passes a closed opening in the mini)
    plugs = plug_probes(s)
    steps += plugs
    mark["plugs"] = len(steps)
    names_p = [n for n, _, _ in OPEN_EDGES]
    steps.append({"command": "inspect.interference", "params": {"budget_s": 120, "bodies": [*names_p, "zone_wall"]}})
    # I3(b): the SEN66 at the ends of its depth tolerance (port face on the ring)
    ext = A.extremes(s)
    steps += ext
    names_e = [c["params"]["body_name"] for c in ext]
    steps.append({"command": "parameters.change", "params": {"changes": {"pad_squeeze": f"{s.v('pad_t - pad_gap')} mm"}}})
    mark["extremes"] = len(steps)
    steps.append({"command": "inspect.interference", "params": {
        "budget_s": 120, "bodies": [*names_e, *EXTREME_PARTS],
        "exclude_pairs": [[a, b] for i, a in enumerate(names_e) for b in names_e[i + 1:]]}})
    steps.append({"command": "parameters.change", "params": {"changes": {"pad_squeeze": "0 mm"}}})
    # Task 4b: the face (band slots, labels, flexure) against its probes
    fprobes = face_probes(s)
    steps += fprobes
    names_f = _names(fprobes)
    mark["face"] = len(steps)
    steps.append({"command": "inspect.interference", "params": {
        "budget_s": 120, "bodies": [*names_f, *SHELL_PARTS], "exclude_pairs": [[a, b] for i, a in enumerate(names_f) for b in names_f[i + 1:]]}})
    # Task 4b: the openings' open area, lower edges and the USB-C fit (probes that overlap the base by design)
    oprobes = [c for c, *_ in opening_probes(s)] + A.usb_probes(s) + low_probes(s)
    steps += oprobes
    names_o = _names(oprobes)
    mark["openings"] = len(steps)
    steps.append({"command": "inspect.interference", "params": {
        "budget_s": 120, "bodies": [*names_o, "base_plate", "shell"],
        "exclude_pairs": [[a, b] for i, a in enumerate(names_o) for b in names_o[i + 1:]] + [["base_plate", "shell"]]}})
    # R12 and the tongue's distances as exact distances between solids
    steps += clear_probes(s)
    mark["clearance"] = len(steps)
    for probes, against in CLEAR_PAIRS.values():
        steps.append({"command": "inspect.clearance", "params": {"bodies": list(probes), "against": list(against), "clearance": 200}})
    steps.append({"command": "parameters.change", "params": {"changes": {n: f"{A.TOUCH_SQUEEZE} mm" for n in SQUEEZES}}})
    mark["touch"] = len(steps)
    steps.append({"command": "inspect.interference", "params": {"budget_s": 120, "bodies": sorted({b for p in TOUCHES for b in p})}})
    steps.append({"command": "parameters.change", "params": {"changes": {n: "0 mm" for n in SQUEEZES}}})
    steps.append({"command": "file.save", "params": {"path": str(save), "cache": False}})
    return {"commands": steps, "mark": mark}


# --- the passage's section with the tongue's real board in it (a second run) ---------------------
SLAB = 0.5


def passage_slab_ys(s) -> dict:
    """Where the slabs cross the passage (their front y): at the tongue's VEML7700 end, its middle,
    its pin and Qwiic socket, its plug, the Qwiic cable's turn, and the module's left stop."""
    return {"slab_veml": "tongue_y0 + 1.0", "slab_mid": "tongue_y0 + 5.0", "slab_pin": "tm_y - 0.25",
            "slab_socket": "tongue_y0 + tq_mate - 1.0", "slab_plug": "tongue_y0 + tq_mate + 2.0", "slab_turn": "qw_y - 0.25",
            "slab_stop": "sen_y1 - stop_l / 2"}


def passage_slabs(s) -> list[dict]:
    return [_box(n, "-tub_x", y, "floor_t", "sen_x0", f"{y} + {SLAB}", "zw_z0") for n, y in passage_slab_ys(s).items()]


def passage_script(s, near: list[str]) -> list[dict]:
    """Slabs across the passage against every body near it (`near`: names from the check design's
    measure). They overlap by design; the free section is (slab - overlaps) / SLAB."""
    slabs = passage_slabs(s)
    names = [c["params"]["body_name"] for c in slabs]
    return slabs + [{"command": "inspect.interference", "params": {
        "budget_s": 300, "bodies": [*names, *near], "exclude_pairs": [[a, b] for i, a in enumerate(near) for b in near[i + 1:]]
        + [[a, b] for i, a in enumerate(names) for b in names[i + 1:]]}}]


def passage_near(s, measure: dict) -> list[str]:
    """Bodies whose boxes reach into the passage (x -tub_x ... sen_x0, y over the slabs)."""
    v = s.v
    x0, x1 = v("-tub_x"), v("sen_x0")
    ys = [v(y) for y in passage_slab_ys(s).values()]
    y0, y1 = min(ys), max(ys) + SLAB
    out = []
    for b in measure["bodies"]:
        lo, hi = b["bbox"]["min"], b["bbox"]["max"]
        if b["name"].startswith(("air_", "sweep_", "shell_up_", "cl_", "ext_", "edge_", "shell_n")):
            continue
        if hi[0] > x0 and lo[0] < x1 and hi[1] > y0 and lo[1] < y1 and hi[2] > v("floor_t") and lo[2] < v("zw_z0"):
            out.append(b["name"])
    return sorted(set(out))


def passage_sections(s, res: dict) -> dict:
    """{slab: free section mm2} from the passage run (overlaps between the near bodies themselves are
    left out, so where two of them overlap inside a slab the section is under-counted: conservative)."""
    got = {}
    for p in res["interferences"]:
        a, b = (p["a"], p["b"]) if p["a"].startswith("slab_") else (p["b"], p["a"])
        got[a] = got.get(a, 0.0) + p["volume_mm3"]
    area = s.v("(sen_x0 + tub_x) * (zw_z0 - floor_t)")
    return {n: area - got.get(n, 0.0) / SLAB for n in passage_slab_ys(s)}


def run(cli: str | None = None) -> dict:
    """Build the check design, then the passage run on it; return the results by name."""
    s = airq_mini.build()
    sc = check_script()
    res = A.run_commands(sc["commands"], "airq-mini-check", ENCLOSURE / airq_mini.OUTPUT, cli)
    m = sc["mark"]
    out = {"inserted": res[:len(REFS)], "interference": res[m["interference"]], "measure": res[m["measure"]],
           "touch": res[m["touch"]], "nudge": res[m["nudge"]], "plugs": res[m["plugs"]], "extremes": res[m["extremes"]],
           "face": res[m["face"]], "openings": res[m["openings"]],
           "clearance": {k: _near(res[m["clearance"] + i]) for i, k in enumerate(CLEAR_PAIRS)}}
    near = passage_near(s, out["measure"])
    pres = A.run_commands(passage_script(s, near), "airq-mini-passage", CHECK_SC, cli)
    out["passage"] = pres[-1]
    out["passage_near"] = near
    return out


# --- distances the layout answers (arithmetic from the parameters and the boards' sources) ---------

def distances(s=None) -> dict:
    s = s or airq_mini.build()
    v = s.v
    m = B.MAIN
    x0, y_front, z_top = v("board_x0"), v("board_y0"), v("board_z0") + v("board_t")
    dev = lambda X, Y: (x0 + X, y_front + v("board_d") - Y)       # noqa: E731
    mod = m["antenna"]["module_body"]
    mh = B.module_h()
    ant = ((x0 + mod[0][0], x0 + mod[1][0]), tuple(sorted((dev(0, 0)[1], dev(0, mod[0][1])[1]))), (z_top, z_top + mh))
    u3 = ((x0 + mod[0][0], x0 + mod[1][0]), tuple(sorted((dev(0, mod[0][1])[1], dev(0, mod[1][1])[1]))), (z_top, z_top + mh))
    (ux0, uy0), (ux1, uy1) = B.layout_part("U2")["box"]
    u2 = ((x0 + ux0, x0 + ux1), tuple(sorted((dev(0, uy0)[1], dev(0, uy1)[1]))), (z_top, z_top + m["max_part_height"]))
    sen = ((v("sen_x0"), v("sen_x1")), (v("sen_y0"), v("sen_y1")), (v("floor_t") + v("foam"), v("sen_top")))
    tongue = ((v("tongue_x0"), v("tongue_x0 + tongue_t + tongue_parts_h")), (v("tongue_y0"), v("tongue_y0 + tongue_dp")),
              (v("tongue_z0"), v("tongue_top")))
    usb_x = v("usb_x")
    plug = ((usb_x - v("usb_plug_w") / 2, usb_x + v("usb_plug_w") / 2), (dev(0, 0)[1], v("D") + 20.0),
            (v("usb_z") - v("usb_plug_h") / 2, v("usb_z") + v("usb_plug_h") / 2))
    r = v("boss_d") / 2
    bosses = [((x - r, x + r), (v("boss_y") - r, v("boss_y") + r), (v("floor_t") - v("head_depth"), v("floor_t") + v("boss_h")))
              for x in (-v("boss_x"), v("boss_x"))]
    rx, rz = v("rear_boss_x"), v("rear_boss_z")
    bosses.append(((rx - r, rx + r), (v("D") - v("wall") - v("clr_remove") - v("rear_boss_len"), v("D")), (rz - r, rz + r)))
    screws = [((x - 1, x + 1), (y - 1, y + 1), (z_top - 6, z_top + 2)) for x, y in ((v("h1_x"), v("h1_y")), (v("h2_x"), v("h2_y")))]
    usb_len = B.usb_len()
    return {
        "antenna_to_sen66": _box_gap(ant, sen),
        "antenna_to_usb_plug": _box_gap(ant, plug),
        "antenna_to_bosses": min(_box_gap(ant, b) for b in bosses),
        "antenna_to_screws": min(_box_gap(ant, b) for b in screws),
        "tongue_to_u3": _box_gap(tongue, u3),
        "tongue_to_u2": _box_gap(tongue, u2),
        "h1_to_usb_c_centre": math.hypot(v("h1_x") - usb_x, v("h1_y") - dev(0, usb_len / 2)[1]),
        "intake_open_mm2": v(airq_mini.INTAKE_OPEN),
        "outlet_grille_open_mm2": v(airq_mini.OUTLET_OPEN),
        "intake_to_outlet_grille": v("D"),
        "passage_envelope_free": v("passage * (zw_z0 - floor_t) - (tongue_t + tongue_parts_h) * tongue_w")
        - math.pi / 4 * v("cable_gh_d") ** 2 - v("tm_collar_d * (tongue_x0 - clr_align + tub_x)"),
    }


# --- Task 4b: the band's light (analytic and arithmetic, in Python: not a SolidCraft ray trace) -------------
# Every solid here is a prism along x: a polygon in the face frame (s, t) between x0 and x1 (airq_face: s up the
# slope from the crease, t into the case). World (y, z) <-> (s, t) is a rotation, so lengths carry over.

def _fr(s) -> tuple[float, float, float]:
    v = s.v
    return v("sin_t"), v("cos_t"), v("lip")


def _world(fr, x, sv, tv) -> tuple[float, float, float]:
    sn, c, lip = fr
    return x, sv * sn + tv * c, lip + sv * c - tv * sn


def _to_st(fr, y, z) -> tuple[float, float]:
    sn, c, lip = fr
    return y * sn + (z - lip) * c, y * c - (z - lip) * sn


def _prism(name, poly, x0, x1, kinds=None) -> dict:
    area2 = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    return {"name": name, "poly": poly, "x": (x0, x1), "kinds": kinds or {}, "sign": 1 if area2 > 0 else -1}


def _yz_box(fr, y0, y1, z0, z1) -> list[tuple[float, float]]:
    return [_to_st(fr, y0, z0), _to_st(fr, y1, z0), _to_st(fr, y1, z1), _to_st(fr, y0, z1)]


def guide_prisms(s, half: str | None = None) -> list[dict]:
    """The guides' prisms as built (`airq_mini_face.guide_pieces`): {name ("co2 bar", "D1 foot", ...), body, poly,
    x, kinds: {edge: "exit" | "entry"}, sign}. `half` keeps one guide's."""
    v = s.v
    out = []
    for feat, body, key, x0, x1 in MF.guide_pieces():
        if half and body != f"light_guide_{half}":
            continue
        poly = [(v(a), v(b)) for a, b in MF.PROFILES[key]()]
        name = f"{body[len('light_guide_'):]} bar" if key == "bar" else f"{feat.split()[-1]} foot"
        pr = _prism(name, poly, v(x0), v(x1), {"bar": {0: "exit"}, "foot": {1: "entry"}}[key])
        pr["body"] = body
        out.append(pr)
    return out


def _x_ranges(s, skip: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """[-inner_x, inner_x] less the `skip` ranges."""
    v = s.v
    out, x = [], -v("inner_x")
    for a, b in sorted(skip):
        if a > x:
            out.append((x, a))
        x = max(x, b)
    if x < v("inner_x"):
        out.append((x, v("inner_x")))
    return out


def opaque_prisms(s, stop: bool = True) -> list[dict]:
    """The opaque solids round the band, as prisms (each named by its part; `material` says what it is):
    - the shell's face wall (t 0 ... wall, from its lower edge at the crease, z = lip + clr_remove, to the top
      wall's underside), less the band slots, the flexure's whole width (its U slot and thinned beam: no
      blocking counted there) and, over the labels' height, their 0.4 deboss (all x: conservative);
    - the band's ribs (shell) and `guide_stop` (black foam; `stop` False leaves it out) with its windows;
    - the four LED bodies and the board (opaque), the zone wall's section (ledge, slant, flat part) over the
      x between its boss notches and its drawer, `zone_seal` (black foam) and the lip (base), less its intake
      rows (all their x and z: conservative) and the light-sensor window (as its square).
    The crease (the 0.2 parting line over the lip's top) is air: nothing is put there."""
    v = s.v
    fr = _fr(s)
    sn, c, lip = fr
    w = v("wall")
    out = []
    s_b0 = v("clr_remove") / c                                       # the face wall's lower edge (z = lip + clr_remove)
    s_b1 = (v("clr_remove") + w * sn) / c
    s_top0, s_top1 = v("(H - lip) / cos_t"), v("(H - wall - lip + wall * sin_t) / cos_t")
    s_l0, s_l1 = v("label_f0 - lip - label_sub_drop"), v("label_f1 - lip")
    s_g0, s_g1 = v("band_f0 - lip"), v("band_f1 - lip")
    flex = (v("flex_x0 - flex_slot"), v("flex_x1 + flex_slot"))
    full = _x_ranges(s, [flex])
    band = _x_ranges(s, [flex, (v("band_co2_x0"), v("band_co2_x1")), (v("band_pm_x0"), v("band_pm_x1"))])
    t_lab = v("label_depth")
    pieces = [("face low", [(s_b0, 0.0), (s_l0, 0.0), (s_l0, w), (s_b1, w)], full),
              ("face labels", [(s_l0, t_lab), (s_l1, t_lab), (s_l1, w), (s_l0, w)], full),
              ("face mid", [(s_l1, 0.0), (s_g0, 0.0), (s_g0, w), (s_l1, w)], full),
              ("face band", [(s_g0, 0.0), (s_g1, 0.0), (s_g1, w), (s_g0, w)], band),
              ("face high", [(s_g1, 0.0), (s_top0, 0.0), (s_top1, w), (s_g1, w)], full)]
    for name, poly, xs in pieces:
        for k, (a, b) in enumerate(xs):
            pr = _prism(f"shell {name} {k}", poly, a, b)
            pr["material"] = "shell"
            out.append(pr)
    rib = [_to_st(fr, v(y), v(z)) for y, z in MF.rib_profile()]
    for name, (x0, x1) in MF.rib_spans().items():
        pr = _prism(f"shell rib {name}", rib, v(x0), v(x1))
        pr["material"] = "shell"
        out.append(pr)
    if stop:
        y0, y1, z0, z1 = v("lg_ysf"), v("stop_y1"), v("rib_z0"), v("stop_z1")
        wins = [tuple(v(e) for e in wn) for wn in MF.stop_windows()]
        wz0, wz1 = min(wn[2] for wn in wins), max(wn[3] for wn in wins)
        for name, za, zb, xs in (("low", z0, wz0, [(v("stop_x0"), v("stop_x1"))]), ("high", wz1, z1, [(v("stop_x0"), v("stop_x1"))]),
                                 ("mid", wz0, wz1, [])):
            if name == "mid":
                x, xs = v("stop_x0"), []
                for wn in sorted(wins):
                    xs.append((x, wn[0]))
                    x = wn[1]
                xs.append((x, v("stop_x1")))
            for k, (a, b) in enumerate(xs):
                pr = _prism(f"guide_stop {name} {k}", _yz_box(fr, y0, y1, za, zb), a, b)
                pr["material"] = "foam"
                out.append(pr)
    lw, lh, ld = v("led_face_w"), v("led_face_h"), B.led_body_d()
    yf, zt = v("board_y0"), v("board_z0 + board_t")
    for i in range(1, 5):
        pr = _prism(f"D{i}", _yz_box(fr, yf, yf + ld, zt, zt + lh), v(f"d{i}_x") - lw / 2, v(f"d{i}_x") + lw / 2)
        pr["material"] = "LED"
        out.append(pr)
    pr = _prism("board", _yz_box(fr, yf, yf + v("board_d"), v("board_z0"), zt), v("board_x0"), v("board_x0 + board_w"))
    pr["material"] = "board"
    out.append(pr)
    zw = [(v("wall + seal_t"), v("ledge_z0")), (v(C.yb("ledge_z0")), v("ledge_z0")), (v(C.yb("zw_z0")), v("zw_z0")),
          (v("D - wall - clr_remove"), v("zw_z0")), (v("D - wall - clr_remove"), v("zw_z1")), (v(C.yf("zw_z1")), v("zw_z1")),
          (v(C.yf("ledge_z1")), v("ledge_z1")), (v("wall + seal_t"), v("ledge_z1"))]
    zx = v("boss_x - boss_d / 2 - clr_remove")
    pr = _prism("zone_wall", [_to_st(fr, y, z) for y, z in zw], max(-zx, v("dr_x1")), zx)
    pr["material"] = "zone wall"
    out.append(pr)
    pr = _prism("zone_seal", _yz_box(fr, w, v("wall + seal_t"), v("ledge_z0"), v("ledge_z1")), -v("bp_x0"), v("bp_x0"))
    pr["material"] = "foam"
    out.append(pr)
    r, lx, lz = v("lsw_d") / 2, v("lsw_x"), v("lsw_z")
    rz0, rz1, rx0 = v("slot_row1_z"), v("slot_row3_z + slot_w"), v("row_x0")
    W2 = v("W / 2")
    lip_pieces = [(-W2, W2, 0.0, min(rz0, lz - r)), (-W2, W2, rz1, lip), (-W2, rx0, max(rz0, lz + r), rz1) if lz + r < rz1 else None,
                  (-W2, rx0, rz0, lz - r) if lz - r > rz0 else None, (-W2, lx - r, lz - r, lz + r), (lx + r, rx0, lz - r, lz + r)]
    for k, q in enumerate(p for p in lip_pieces if p):
        x0, x1, z0, z1 = q
        if x1 > x0 and z1 > z0:
            pr = _prism(f"lip {k}", _yz_box(fr, 0.0, w, z0, z1), x0, x1)
            pr["material"] = "base"
            out.append(pr)
    for pr in out:
        ys = [_world(fr, 0.0, a, b)[1] for a, b in pr["poly"]]
        zs = [_world(fr, 0.0, a, b)[2] for a, b in pr["poly"]]
        pr["bb"] = (pr["x"][0], min(ys), min(zs), pr["x"][1], max(ys), max(zs))
    return out


def _poly_ivs(P, Q, poly) -> list[tuple[float, float]]:
    """The fractions of P -> Q (2-D) inside the simple polygon `poly`, as intervals."""
    ts = [0.0, 1.0]
    (py, pz), (qy, qz) = P, Q
    dy, dz = qy - py, qz - pz
    n = len(poly)
    for i in range(n):
        (ay, az), (by, bz) = poly[i], poly[(i + 1) % n]
        ey, ez = by - ay, bz - az
        den = dy * ez - dz * ey
        if abs(den) < 1e-12:
            continue
        tt = ((ay - py) * ez - (az - pz) * ey) / den
        u = ((ay - py) * dz - (az - pz) * dy) / den
        if 0 <= tt <= 1 and -1e-12 <= u <= 1 + 1e-12:
            ts.append(tt)
    ts = sorted(set(ts))
    out = []
    for a, b in zip(ts, ts[1:]):
        if b - a > 1e-12 and A._inside(poly, py + dy * (a + b) / 2, pz + dz * (a + b) / 2):
            out.append((a, b))
    return out


def _seg_ivs(fr, p, q, pr) -> list[tuple[float, float]]:
    """The fractions of the world segment p -> q inside the prism `pr`."""
    bb = pr["bb"]
    for k in range(3):
        if max(p[k], q[k]) < bb[k] - 1e-9 or min(p[k], q[k]) > bb[k + 3] + 1e-9:
            return []
    xa, xb = pr["x"]
    dx = q[0] - p[0]
    if abs(dx) < 1e-12:
        if not xa < p[0] < xb:
            return []
        f0, f1 = 0.0, 1.0
    else:
        a, b = (xa - p[0]) / dx, (xb - p[0]) / dx
        f0, f1 = max(0.0, min(a, b)), min(1.0, max(a, b))
    if f0 >= f1 - 1e-12:
        return []

    def st(f):
        return _to_st(fr, p[1] + (q[1] - p[1]) * f, p[2] + (q[2] - p[2]) * f)
    return [(f0 + (f1 - f0) * a, f0 + (f1 - f0) * b) for a, b in _poly_ivs(st(f0), st(f1), pr["poly"])]


def opaque_len(fr, p, q, prisms, enough: float = math.inf) -> float:
    """The length of p -> q inside the union of `prisms` (stops counting past `enough`)."""
    ivs = []
    ln = math.dist(p, q)
    for pr in prisms:
        ivs += _seg_ivs(fr, p, q, pr)
    ivs.sort()
    tot, end = 0.0, -1.0
    for a, b in ivs:
        if b <= end:
            continue
        tot += b - max(a, end)
        end = b
        if tot * ln >= enough:
            break
    return tot * ln


def blocked(fr, p, q, prisms) -> bool:
    return any(b - a > 1e-9 for pr in prisms for a, b in _seg_ivs(fr, p, q, pr))


def surface_samples(s, prisms, dx: float, n_edge: int, n_side: int, skip_kinds: tuple = ()) -> list[tuple]:
    """Points on every exposed face of `prisms` (one guide's, or both: a point counts if just outside it, along
    the face's normal, there is no prism of the same body): each profile edge at n_edge + 1 points along it and
    every `dx` (or finer) along x, each end face on an (n_side + 1)^2 grid inside its profile. Returns (world
    point, world outward normal, face name)."""
    fr = _fr(s)
    sn, c, _ = fr
    out = []
    by_body: dict[str, list] = {}
    for pr in prisms:
        by_body.setdefault(pr.get("body", ""), []).append(pr)

    def add(pr, face, x, sv, tv, n3):
        own = by_body[pr.get("body", "")]
        if A._in_prisms(own, (x + n3[0] * 2e-3, sv + n3[1] * 2e-3, tv + n3[2] * 2e-3)):
            return
        nw = (n3[0], n3[1] * sn + n3[2] * c, n3[1] * c - n3[2] * sn)
        out.append((_world(fr, x, sv, tv), nw, face))
    for pr in prisms:
        poly, (xa, xb) = pr["poly"], pr["x"]
        n = len(poly)
        nx = max(1, math.ceil((xb - xa) / dx))
        for i in range(n):
            kind = pr["kinds"].get(i, f"face {i}")
            if kind in skip_kinds:
                continue
            (s0, t0), (s1, t1) = poly[i], poly[(i + 1) % n]
            ln = math.hypot(s1 - s0, t1 - t0)
            nst = (pr["sign"] * (t1 - t0) / ln, -pr["sign"] * (s1 - s0) / ln)
            for j in range(n_edge + 1):
                f = j / n_edge
                for k in range(nx + 1):
                    add(pr, f"{pr['name']} {kind}", xa + (xb - xa) * k / nx, s0 + (s1 - s0) * f, t0 + (t1 - t0) * f, (0.0, *nst))
        ss, ts = [q[0] for q in poly], [q[1] for q in poly]
        for xe, sx in ((xa, -1.0), (xb, 1.0)):
            for i in range(n_side + 1):
                for j in range(n_side + 1):
                    sv = min(ss) + (max(ss) - min(ss)) * i / n_side
                    tv = min(ts) + (max(ts) - min(ts)) * j / n_side
                    if A._inside(poly, sv, tv):
                        add(pr, f"{pr['name']} end", xe, sv, tv, (sx, 0.0, 0.0))
    return out


def led_face_points(s, n: int = 4) -> list[tuple]:
    """(LED, point) on each LED's light face, an (n + 1)^2 grid."""
    v = s.v
    w, h, yf, zc = v("led_face_w"), v("led_face_h"), v("board_y0"), v("led_z")
    return [(i, (v(f"d{i}_x") - w / 2 + w * a / n, yf, zc - h / 2 + h * b / n)) for i in range(1, 5) for a in range(n + 1) for b in range(n + 1)]


def guide_delivery(s, n_rays: int = 20000, seed: int = 1, max_bounce: int = 200) -> dict:
    """R48 (analytic: a 3-D Monte Carlo ray trace in Python, not a print), the airQ's `airq_check.guide_delivery`
    on the mini's guides: each guide as built (its bar and two feet) with every face bare: PETG (n 1.57) against
    air, total internal reflection at 39.6 deg or more, else the ray leaves. Per LED (D1, D2 into
    light_guide_co2; D3, D4 into light_guide_pm): `n_rays` Lambertian rays from its 4 x 2 face cross the
    clr_remove gap; those that meet its foot's entry face refract in (Snell; the Fresnel transmittance is the
    weight) and are followed until they leave. Out through the exit face (the bar's front, in the slot):
    delivered, times the exit's Fresnel transmittance; anywhere else: lost (its partial reflection dropped:
    conservative). Returns {leds: {Di: fraction of its emission delivered, entered, delivered, straight: the
    delivered rays that met no face on the way}, halves: {co2, pm: lit_x, lit_x90, exit_x, bins (10 over the
    exit), visible: the slot's x}}."""
    import random
    v = s.v
    rng = random.Random(seed)
    fr = _fr(s)
    sn, c, lip = fr
    crit = math.radians(A.CRIT_DEG)
    ye, yf, zc, hh, hw = v("lg_ye"), v("board_y0"), v("led_z"), v("led_face_h") / 2, v("led_face_w") / 2
    leds, halves = {}, {}
    for half, ids in MF.LEDS:
        prisms = guide_prisms(s, half)
        bar = next(p for p in prisms if p["name"].endswith("bar"))
        xs = []
        for i in ids:
            foot = next(p for p in prisms if p["name"] == f"D{i} foot")
            (fs0, ft0), (fs1, ft1) = foot["poly"][1], foot["poly"][2]
            win_z = sorted(lip + sv * c - tv * sn for sv, tv in ((fs0, ft0), (fs1, ft1)))
            cx = v(f"d{i}_x")
            w_sum, entered, hits, straight = 0.0, 0, 0, 0
            for _ in range(n_rays):
                r1, r2 = rng.random(), rng.random()
                ph, sr = 2 * math.pi * r1, math.sqrt(r2)
                d = (sr * math.cos(ph), -math.sqrt(1 - r2), sr * math.sin(ph))
                p0 = (cx + rng.uniform(-hw, hw), yf, zc + rng.uniform(-hh, hh))
                k = (ye - yf) / d[1]
                q = (p0[0] + k * d[0], ye, p0[2] + k * d[2])
                if not (foot["x"][0] <= q[0] <= foot["x"][1] and win_z[0] <= q[2] <= win_z[1]):
                    continue
                entered += 1
                w = A._fresnel_t(-d[1], 1.0, A.N_PETG)
                dx, dz = d[0] / A.N_PETG, d[2] / A.N_PETG
                dw = (dx, -math.sqrt(max(0.0, 1 - dx * dx - dz * dz)), dz)
                D = [dw[0], dw[1] * sn + dw[2] * c, dw[1] * c - dw[2] * sn]
                st = _to_st(fr, q[1], q[2])
                P = [q[0] + 1e-6 * D[0], st[0] + 1e-6 * D[1], st[1] + 1e-6 * D[2]]
                for nref in range(max_bounce):
                    h = A._next_exit(prisms, P, D)
                    if h is None:
                        break
                    lam, nrm, kind = h
                    P = [P[j] + lam * D[j] for j in range(3)]
                    cosi = sum(D[j] * nrm[j] for j in range(3))
                    if math.acos(max(-1.0, min(1.0, cosi))) < crit:
                        if kind == "exit":
                            w_sum += w * A._fresnel_t(cosi, A.N_PETG, 1.0)
                            hits += 1
                            straight += nref == 0
                            xs.append(P[0])
                        break
                    D = [D[j] - 2 * cosi * nrm[j] for j in range(3)]
                    P = [P[j] + 1e-7 * D[j] for j in range(3)]
            leds[f"D{i}"] = {"fraction": w_sum / n_rays, "entered": entered, "delivered": hits, "straight": straight}
        x_lo, x_hi = bar["x"]
        bins = [0] * 10
        for x in xs:
            bins[min(9, int((x - x_lo) / (x_hi - x_lo) * 10))] += 1
        xs.sort()
        halves[half] = {"lit_x": (xs[0], xs[-1]) if xs else None,
                        "lit_x90": (xs[int(0.05 * (len(xs) - 1))], xs[int(0.95 * (len(xs) - 1))]) if xs else None,
                        "exit_x": (x_lo, x_hi), "bins": bins, "visible": (v(f"band_{half}_x0"), v(f"band_{half}_x1"))}
    return {"leds": leds, "halves": halves, "rays_per_led": n_rays}


def u4_port(s) -> tuple[float, float, float]:
    """The MS5611's (U4's) port, as airq_check.u4_port: over its centre, 1.0 above the board's top."""
    return A.u4_port(s)


def ms5611_sight(s, dx: float = 0.25, n_edge: int = 40, n_side: int = 60, stop: bool = True) -> dict:
    """R13 / R50 (arithmetic: exact straight lines against the opaque prisms, not a SolidCraft ray trace): every
    exposed face of both guides (the bars, the feet, their side, top, bottom, end and entry faces; the exit faces
    too), sampled every `dx` along x, n_edge + 1 points along each profile edge, an (n_side + 1)^2 grid on each
    end. A sample counts where U4's port is in its face's outward half-space; its line to the port is unblocked
    if it passes through none of `opaque_prisms` (the shell's wall and ribs, `guide_stop`, the LED bodies, the
    board, the zone wall). The LED faces emit into -y and U4 is behind them. `stop` False leaves `guide_stop`
    out, to show it is the stop that closes the guides' backs. Returns {samples, unblocked, first, by_face}."""
    fr = _fr(s)
    tgt = u4_port(s)
    obst = [o for o in opaque_prisms(s, stop=stop) if o["material"] != "base"]
    n, un, first, by = 0, 0, None, {}
    for p, nw, face in surface_samples(s, guide_prisms(s), dx, n_edge, n_side):
        if sum((tgt[k] - p[k]) * nw[k] for k in range(3)) <= 0:
            continue
        n += 1
        r = by.setdefault(face, [0, 0])
        r[0] += 1
        if not blocked(fr, p, tgt, obst):
            un += 1
            r[1] += 1
            first = first or tuple(round(e, 3) for e in p)
    led_front = sum(1 for _, p in led_face_points(s) if tgt[1] - p[1] < 0)
    return {"target": tgt, "samples": n, "unblocked": un, "first": first, "by_face": by, "led_faces_facing_u4": led_front}


def guide_to_guide(s, dx: float = 2.0, n_edge: int = 4, n_side: int = 4) -> dict:
    """The no-straight-path check (plan Task 4 Step 3), two ways:
    - sampled (arithmetic): every exposed face of `light_guide_co2` against every exposed face of
      `light_guide_pm` (`surface_samples`), each line's opaque length through `opaque_prisms` (the divider rib,
      the face wall, `guide_stop`, the LEDs, the board): `air` counts the lines with none (a straight path of
      air or light), `under` those under 1.2;
    - hull (analytic, exact for every line): a line between the guides crosses the whole divider slab (x from
      band_co2_x1 to band_pm_x0), and inside it its (s, t) is a mix of its ends', so it lies in the convex hull of
      the guides' common profile. `hull_uncovered` counts grid points (0.02) of that hull at the divider's x that
      no opaque profile there (rib, face wall, stop) covers: 0 means every line runs >= the gap's width (6.8) in
      opaque material."""
    fr = _fr(s)
    v = s.v
    obst = opaque_prisms(s)
    a = surface_samples(s, guide_prisms(s, "co2"), dx, n_edge, n_side)
    b = surface_samples(s, guide_prisms(s, "pm"), dx, n_edge, n_side)
    air, under, least = 0, 0, math.inf
    for p, _, _ in a:
        for q, _, _ in b:
            ln = opaque_len(fr, p, q, obst, enough=v("band_pm_x0 - band_co2_x1"))
            least = min(least, ln)
            air += ln <= 1e-9
            under += ln < 1.2
    pts = [pt for pr in guide_prisms(s) for pt in pr["poly"]]
    hull = _hull(pts)
    xm = (v("band_co2_x1") + v("band_pm_x0")) / 2
    cover = [o["poly"] for o in obst if o["x"][0] <= xm <= o["x"][1]]
    ss, ts = [p[0] for p in hull], [p[1] for p in hull]
    unc, tot = 0, 0
    g = 0.02
    for i in range(int((max(ss) - min(ss)) / g) + 1):
        for j in range(int((max(ts) - min(ts)) / g) + 1):
            sv, tv = min(ss) + i * g, min(ts) + j * g
            if A._inside(hull, sv, tv):
                tot += 1
                unc += not any(A._inside(poly, sv, tv) for poly in cover)
    return {"lines": len(a) * len(b), "air": air, "under_1_2": under, "least": least, "hull_points": tot, "hull_uncovered": unc,
            "slab": v("band_pm_x0 - band_co2_x1"), "covers": [o["name"] for o in obst if o["x"][0] <= xm <= o["x"][1]]}


def _hull(pts) -> list[tuple[float, float]]:
    pts = sorted(set(pts))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def gap_dark(s, dx: float = 1.0, n_edge: int = 6, n_side: int = 6, edge: float = 1.2) -> dict:
    """The visible gap between the halves (arithmetic): the least opaque length from any face of either guide
    (`surface_samples`, the exits included) to points on the gap's outer face (t = 0, the slot's height, x from
    `edge` inside each slot's end), through `opaque_prisms`. Within `edge` of a slot's end the wall's own end face
    is thinner than that: the dark part of the gap is its width less 2 x edge."""
    fr = _fr(s)
    v = s.v
    obst = opaque_prisms(s)
    x0, x1 = v("band_co2_x1") + edge, v("band_pm_x0") - edge
    tg = [_world(fr, x0 + (x1 - x0) * i / 6, sv, 0.0) for i in range(7) for sv in (v("band_f0 - lip"), v("band_f0 / 2 + band_f1 / 2 - lip"), v("band_f1 - lip"))]
    least = math.inf
    for p, _, _ in surface_samples(s, guide_prisms(s), dx, n_edge, n_side):
        for q in tg:
            least = min(least, opaque_len(fr, p, q, obst, enough=least))
    return {"least": least, "dark_x": (x0, x1), "dark_w": x1 - x0}


def light_paths(s, dx: float = 1.0, n_edge: int = 6, n_side: int = 6) -> dict:
    """Review focus 3 (arithmetic: exact straight lines through the opaque prisms, not a ray trace): the least
    opaque length along any straight line from a guide's surface (every exposed face, the exit included) or a
    LED face (all four) to:
    - `sensor`: the tongue's VEML7700 window (its centre and 0.5 round it);
    - `lip_window`: the light-sensor window's outer face (its disc);
    - `crease_front`: the crease's open front (y 0, z lip ... lip + clr_remove) along the band's length.
    Counted opaque: the shell's face wall and ribs, `guide_stop`, the LEDs, the board, the zone wall (ledge,
    slant, flat part), `zone_seal` (black foam) and the lip; the crease's 0.2 parting line counts as air.
    Returns {target: (length, (source, target))}."""
    fr = _fr(s)
    v = s.v
    obst = opaque_prisms(s)
    src = [p for p, _, _ in surface_samples(s, guide_prisms(s), dx, n_edge, n_side)] + [p for _, p in led_face_points(s)]
    vx, vy, vz = v("veml_wx"), v("veml_wy"), v("veml_wz")
    r, lx, lz = v("lsw_d") / 2, v("lsw_x"), v("lsw_z")
    lip, cr = v("lip"), v("clr_remove")
    targets = {
        "sensor": [(vx, vy, vz)] + [(vx, vy + dy, vz + dz) for dy, dz in ((0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5))],
        "lip_window": [(lx, 0.0, lz)] + [(lx + r * 0.95 * math.cos(a), 0.0, lz + r * 0.95 * math.sin(a)) for a in [k * math.pi / 4 for k in range(8)]],
        "crease_front": [(x, 0.005, lip + z) for x in (v("stop_x0"), v("band_co2_x0"), v("label_co2_x"), 0.0, v("label_pm_x"), v("band_pm_x1"),
                                                        v("stop_x1")) for z in (0.01, cr / 2, cr - 0.01)],
    }
    out = {}
    for name, ts in targets.items():
        best = (math.inf, None)
        for p in src:
            for q in ts:
                ln = opaque_len(fr, p, q, obst, enough=best[0])
                if ln < best[0]:
                    best = (ln, (tuple(round(e, 3) for e in p), tuple(round(e, 3) for e in q)))
        out[name] = best
    return out


FOAM_KPA = A.FOAM_KPA       # closed-cell foam at 25 % compression, kPa (soft ... firm; to confirm)
TOP_SEAL_KPA = (30.0, 100.0)   # the top seal's foam spec: soft (30) is the design value, firm (100) the bound
ZW_E = 1800.0               # the zone wall's plastic (PETG, the softer of PETG/ASA), MPa
STRIP_W = 20.0              # the zone wall's width taken as carrying the top seal's push to its holds (a strip: the plate is wider, the board ignored)


def hold_supports(s) -> dict:
    """{name: (x, y)} where the zone wall is held down: H1's clamp (the board's screw through its pad into
    H1's post) and the shell's hold-down pads (their bearing areas' centres, `airq_mini_face.hold_spans`)."""
    v = s.v
    yc = (v(C.yf("zw_z1")) + v("lg_ysf")) / 2
    out = {"H1": (v("h1_x"), v("h1_y"))}
    for name, (x0, x1) in MF.hold_spans().items():
        out[name] = ((v(x0) + v(x1)) / 2, yc)
    return out


def seal_forces(s=None) -> dict:
    """Review I1 (analytic, with stated models; the airQ's `airq_check.seal_forces` redone for the mini): what
    pushes on the zone wall and whether its holds keep it, its laps and the top seal closed.
    - loads: the top seal (foam, top_seal_t over zone_gap: its compression, TOP_SEAL_KPA at 25 % taken linear
      to its compression) pushes the zone wall up over the module's top; the zone seal pushes the lip and the
      ledge apart horizontally (no lift); the drawer grommet's faces push the notch's front and rear faces
      (horizontal); its bottom is at contact on the rail (`drawer_floor_squeeze` 0), so no lift there;
    - holds (`hold_supports`): H1's clamp and the shell's pads, all pushing down. Statics as a rigid plate on equal
      springs at the holds (the least-squares split): every hold's reaction must be >= 0 (downward), i.e. the
      top seal's push lies inside the holds' polygon (its distance inside, `inside_mm`);
    - flexibility (a bound): the zone wall as a STRIP_W strip simply supported between the front pads' line and
      H1's line, the push at the seal's centre, PETG at ZW_E; with the foam as a spring in series, the lift at
      the seal and at the plenum plate's lap (the nearest lap in that span), and the top seal's compression
      left. The rail fronts' and the boss-pocket rises' laps are under or beside the pads (lift 0 at contact)."""
    s = s or airq_mini.build()
    v = s.v
    comp = v("top_seal_squeeze") / v("top_seal_t")
    area = v("top_seal_x1 - top_seal_x0") * v("sen_d")
    top = tuple(k / 1000 * comp / 0.25 * area for k in TOP_SEAL_KPA)
    zone = tuple(k / 1000 * 2 * v("bp_x0") * v("ledge_t") for k in FOAM_KPA)
    drawer = tuple(e * v("drawer_squeeze") / v("cab_x + inner_x") * v("dr_y1 - dr_y0") * v("zone_t") for e in A.TPU_E)
    px, py = v("(top_seal_x0 + top_seal_x1) / 2"), v("sen_y0 + sen_d / 2")
    sup = hold_supports(s)
    names = list(sup)
    # least-squares split: R = F (1/n + a (x - xm) + b (y - ym)) with the moments matched
    n = len(names)
    xm = sum(sup[k][0] for k in names) / n
    ym = sum(sup[k][1] for k in names) / n
    sxx = sum((sup[k][0] - xm) ** 2 for k in names)
    syy = sum((sup[k][1] - ym) ** 2 for k in names)
    sxy = sum((sup[k][0] - xm) * (sup[k][1] - ym) for k in names)
    det = sxx * syy - sxy * sxy
    dx, dy = px - xm, py - ym
    a = (dx * syy - dy * sxy) / det
    b = (dy * sxx - dx * sxy) / det
    share = {k: 1 / n + a * (sup[k][0] - xm) + b * (sup[k][1] - ym) for k in names}
    inside = _inside_distance(px, py, [sup[k] for k in names])
    y_f = sup["divider"][1]
    L = sup["H1"][1] - y_f
    aa = py - y_f
    bb = L - aa
    inertia = STRIP_W * v("zone_t") ** 3 / 12
    k_plate = 3 * ZW_E * inertia * L / (aa * aa * bb * bb)          # point load at aa on a simply supported span L
    out = {"top_seal_n": top, "top_seal_compression": comp, "zone_seal_n": zone, "drawer_faces_n": drawer, "drawer_floor_n": 0.0,
           "supports": sup, "share": share, "inside_mm": inside, "span": L, "k_plate": k_plate, "lift": {}}
    yl = v("plate_y0")                                                 # the plenum plate's lap: its front edge, the nearest in the span
    xl = yl - y_f
    for kpa, f in zip(TOP_SEAL_KPA, top):
        k_foam = f / v("top_seal_squeeze")
        lift = k_foam * v("top_seal_squeeze") / (k_foam + k_plate)      # foam and plate in series
        force = k_plate * lift
        lap = force * aa * (L - xl) * (L * L - aa * aa - (L - xl) ** 2) / (6 * ZW_E * inertia * L)
        out["lift"][kpa] = {"at_seal": lift, "force_n": force, "at_plate_lap": lap,
                            "seal_compression_left": (v("top_seal_squeeze") - lift) / v("top_seal_t")}
    return out


def _inside_distance(px, py, pts) -> float:
    """The distance of (px, py) inside the convex hull of `pts` (negative outside)."""
    h = _hull(pts)
    d = math.inf
    for i in range(len(h)):
        (ax, ay), (bx, by) = h[i], h[(i + 1) % len(h)]
        ln = math.hypot(bx - ax, by - ay)
        d = min(d, ((bx - ax) * (py - ay) - (by - ay) * (px - ax)) / ln)
    return d


def values_at(s, **over):
    """An evaluator of the design's parameters with some changed (`wall=2.4`): every parameter re-evaluated in
    order from its expression (angles as the design gives them)."""
    from sclib import evaluate
    vals = {}
    for n, p in s.params.items():
        if n in over:
            vals[n] = over[n]
            continue
        try:
            vals[n] = evaluate(p.expression, vals)
        except ValueError:
            vals[n] = s.v(n)
    return lambda e: evaluate(e, vals)


def intake_throat(s, v=None, dx: float = 0.0, deep: float = 0.0) -> dict:
    """Review M1 (R25, arithmetic): the intake's turn into the passage. All the intake air passes between the
    left boss pocket's inner-back corner (chamfered, `throat_chamfer`: its vertical face) and the SEN66's front-left (its
    foam, its block's left end receding in its corner fillets, its plinth inset), from the floor to the zone
    wall's underside. Per z (0.01 steps), the least distance in plan from the corner to the module's outline;
    the section is its integral over z, less the SEN66 cable, which lies across the whole throat over its own
    height (the cable keep-out's box: the gap counted 0 there). `dx` moves the module along x (-clr_remove: on
    its left stop), `deep` its front forward (sen_d_tol: a 21.8 module). Returns {section, need, by_z}."""
    import ref_sen66
    v = v or s.v
    r = ref_sen66.build().v
    ch = v("throat_chamfer")
    seg = ((-v("bp_x0"), v("bp_y1") - ch), (-v("bp_x0") - ch, v("bp_y1")))      # the pocket's chamfered corner
    zf, zt_ = v("floor_t"), v("zw_z0")
    zb, top = v("floor_t + foam"), v("sen_top")
    pin, ra = r("plinth_inset"), r("r_inlet_end")
    x0 = v("sen_x0") + dx
    yf, yblk = v("sen_y0") - deep, v("sen_y1") - r("block_h")
    c0, c1 = zf, zf + v("cable_gh_d")

    def gap(z):
        if c0 <= z <= c1:
            return 0.0
        zz = min(z, top - 1e-6)
        rects = []
        if zz < zb:
            rects.append((x0, yf))
        else:
            d = min(zz - zb, top - zz)
            rec = ra - math.sqrt(max(0.0, ra * ra - (ra - d) ** 2)) if d < ra else 0.0
            rects.append((x0 + rec, yblk))
            if zb + pin <= zz <= top - pin:
                rp = ra - pin
                dp = min(zz - zb - pin, top - pin - zz)
                recp = rp - math.sqrt(max(0.0, rp * rp - (rp - dp) ** 2)) if dp < rp else 0.0
                rects.append((x0 + pin + recp, yf))
        return min(_seg_quadrant(seg, xa, ya) for xa, ya in rects)
    n = int((zt_ - zf) / 0.01)
    dz = (zt_ - zf) / n
    area = sum(gap(zf + (i + 0.5) * dz) for i in range(n)) * dz
    return {"section": area, "need": 77.3}


def _seg_quadrant(seg, xa, ya, n: int = 50) -> float:
    """The least distance in plan from the segment `seg` to the quarter-plane x >= xa, y >= ya."""
    (x0, y0), (x1, y1) = seg
    return min(math.hypot(max(0.0, xa - (x0 + (x1 - x0) * i / n)), max(0.0, ya - (y0 + (y1 - y0) * i / n))) for i in range(n + 1))


def walls(s) -> dict:
    """The opaque walls' thicknesses (arithmetic): the divider (the visible gap, a rib of the shell), the end
    ribs, `guide_stop`, the face between the PM2.5 half and the flexure's slot."""
    v = s.v
    return {"divider": v("band_pm_x0 - band_co2_x1"), "end_ribs": v("end_rib_t"), "guide_stop": v("stop_t"),
            "pm_to_flexure": v("flex_x0 - flex_slot - band_pm_x1"), "visible_gap": v("band_gap")}


if __name__ == "__main__":
    if "--run" in sys.argv:
        r = run()
        s = airq_mini.build()
        print("interference:", r["interference"]["count"], "checked", r["interference"]["checked"], "unchecked", len(r["interference"]["unchecked"]))
        for p in r["interference"]["interferences"][:40]:
            print("  ", p["a"], p["b"], round(p["volume_mm3"], 4), [round(c, 2) for c in p["bbox"]["min"]], [round(c, 2) for c in p["bbox"]["max"]])
        sec = A.sections(r["measure"], AIR)
        print("sections:", {k: round(x, 1) for k, x in sec.items()})
        print("branches:", {k: tuple(round(x, 1) for x in val) for k, val in branches(s, sec).items()})
        print("nudge:", nudge_faults(r["nudge"], s), [(p["a"], p["b"]) for p in r["nudge"]["interferences"]])
        print("plugs:", r["plugs"]["count"])
        print("extremes:", {f"{a}/{b}": round(d, 3) for (a, b), d in A.extreme_reach(r["extremes"]).items()})
        print("clearance:", {k: round(x, 2) for k, x in r["clearance"].items()})
        print("touch:", {f"{a}/{b}": round(x, 4) for (a, b), x in A.touch_volumes(r["touch"], TOUCHES).items()})
        print("passage near:", r["passage_near"])
        print("passage:", {k: round(x, 1) for k, x in passage_sections(s, r["passage"]).items()})
        print("face:", [(p["a"], p["b"], round(p["volume_mm3"], 3)) for p in r["face"]["interferences"]])
        print("openings:", {k: tuple(round(x, 2) for x in val) for k, val in opening_areas(s, r["openings"]).items()})
        d = guide_delivery(s)
        print("delivery:", {k: round(x["fraction"] * 100, 2) for k, x in d["leds"].items()},
              {h: [round(e, 2) for e in x["lit_x"]] for h, x in d["halves"].items()})
        print("guide to guide:", guide_to_guide(s))
        print("gap:", gap_dark(s))
        sight = ms5611_sight(s)
        print("R13:", sight["samples"], "samples,", sight["unblocked"], "unblocked")
        print("light paths:", {k: round(x[0], 2) for k, x in light_paths(s).items()})
        print("walls:", walls(s))
    else:
        for k, x in distances().items():
            print(k, round(x, 2))
