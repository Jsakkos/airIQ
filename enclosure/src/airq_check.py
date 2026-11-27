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
    columns of its bosses, and copies of the shell raised in steps;
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
import board_sources as B
import enclosure_common as C
import encbuild
import ref_sen66
import ref_sfa40
from sclib import ENCLOSURE

REF = ENCLOSURE / "reference"
CHECK_SC = encbuild.BUILD_DIR / "airq-check.sc"
REFS = ("ref_sen66", "ref_epd", "ref_fpc_adapter", "ref_sfa40", "ref_tongue", "ref_main")
SHELL_BORNE = ("ref_epd", "ref_fpc_adapter")     # the panel and the adapter are in the shell and come down with it
SWEEP_DZ = (1, 2, 4, 8, 16, 32)                  # the shell's raised copies (mm along +z)
TOUCH_SQUEEZE = 0.05                             # the gaskets overlap their seats by this much when they touch at 0
TOUCHES = (("gasket_out", "sen66_body"), ("gasket_in", "sen66_body"), ("gasket_in", "base_plate"), ("zone_seal", "base_plate"),
           ("sen66_pad", "sen66_body"),
           ("grommet_zone_a", "zone_wall"), ("grommet_zone_b", "zone_wall"), ("grommet_zone_a", "base_plate"),
           ("grommet_zone_b", "base_plate"), ("grommet_j4_a", "base_plate"), ("grommet_j4_b", "base_plate"),
           ("grommet_j4_b", "hcho_lid"), ("grommet_tongue_a", "hcho_lid"), ("grommet_tongue_b", "hcho_lid"))
# every squeeze and preload: 0 in the check (R9: faces touch), TOUCH_SQUEEZE in the touch run
SQUEEZES = ("gasket_squeeze", "wiper_squeeze", "pad_squeeze", "ring_preload", "root_squeeze")


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
    ]


def sweeps(s) -> list[dict]:
    """The shell's way on (I1): it is lowered along -z onto the assembled base. Its bosses are the
    parts that reach into the case, so their swept columns (from where they end up to above the
    case) must clear everything on the base; and the whole shell is copied at raised steps."""
    b = [_cyl(f"sweep_boss_{i}", [sx, "boss_y", "floor_t"], "boss_d", "H + 5 - floor_t") for i, sx in enumerate(("-boss_x", "boss_x"), 1)]
    b.append(_box("sweep_rear_boss", "rear_boss_x - boss_d / 2", "D - wall - clr_remove - rear_boss_len", "rear_boss_z - boss_d / 2",
                  "rear_boss_x + boss_d / 2", "D - wall - clr_remove", "H + 5"))
    for dz in SWEEP_DZ:
        b.append({"command": "solid.move", "params": {"name": f"shell_up_{dz}", "bodies": ["shell"], "translate": [0, 0, dz],
                                                      "copy": True, "body_name": f"shell_up_{dz}"}})
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
    sw = [n for n in names if n.startswith(("sweep_", "shell_up_"))]
    out += [[a, b] for i, a in enumerate(sw) for b in sw[i + 1:]]
    out += [[a, "shell"] for a in sw]
    out += [[a, f"{r}:1"] for a in sw for r in SHELL_BORNE]
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
    extra = keepouts(s) + air_probes(s) + sweeps(s)
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
            "plugs": res[m["plugs"]]}


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
    plug = ((usb_x - 6.25, usb_x + 6.25), (dev(0, 0)[1], v("D") + 20.0), (v("usb_z") - 3.5, v("usb_z") + 3.5))   # 12.5 x 7 overmold out the rear (typical, to confirm)
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


def intake_open(s) -> float:
    """Open area of the two intake rows (1.2 slots, slot_bar bars) between row_x0 and row_x1 with
    the light-sensor window's gap: each span holds slots end to end with bars between."""
    v = s.v
    spans = [(v("row_x0"), v("lsw_gap_x0")), (v("lsw_gap_x1"), v("row_x1"))]
    per_row = 0.0
    for a, b in spans:
        n = max(1, math.floor((b - a + v("slot_bar")) / 10.0))        # slots about 8.8-10 mm long
        per_row += (b - a) - (n - 1) * v("slot_bar")
    return 2 * per_row * v("slot_w")


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
