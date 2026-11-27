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
import board_sources as B
import encbuild
from airq_check import _box, _box_gap, _cyl, _near, _rows
from sclib import ENCLOSURE

REF = ENCLOSURE / "reference"
CHECK_SC = encbuild.BUILD_DIR / "airq-mini-check.sc"
REFS = ("ref_sen66", "ref_tongue", "ref_main")
SHELL_PARTS = ("shell",)
SQUEEZES = ("gasket_squeeze", "wiper_squeeze", "pad_squeeze", "ring_preload", "root_squeeze", "drawer_squeeze", "bore_squeeze",
            "seal_squeeze", "top_seal_squeeze")
TOUCHES = (("gasket_out", "sen66_body"), ("gasket_in", "sen66_body"), ("gasket_in", "base_plate"), ("zone_seal", "base_plate"),
           ("sen66_pad", "sen66_body"), ("grommet_zone_a", "zone_wall"), ("grommet_zone_b", "zone_wall"),
           ("grommet_zone_a", "base_plate"), ("sen66_top_seal", "zone_wall"))
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
}


OPENING_AIR = ("air_outlet_grille",)     # the free air in front of an opening shares air with the paths' probes


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
    ]


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
}


def check_bodies(s) -> list[str]:
    return [c["params"]["body_name"] for c in keepouts(s) + air_probes(s) + A.sweeps(s, riders=()) if c["params"].get("body_name")]


def check_script(save=CHECK_SC, budget_s: float = 900) -> dict:
    s = airq_mini.build()
    steps = [{"command": "component.insert_design", "params": {"path": str(pl["path"]), "matrix": pl["matrix"]}} for pl in placements(s)]
    steps.append({"command": "parameters.change", "params": {"changes": {n: "0 mm" for n in SQUEEZES}}})
    steps += keepouts(s) + air_probes(s) + A.sweeps(s, riders=())
    names = check_bodies(s)
    mark = {"interference": len(steps)}
    steps.append({"command": "inspect.interference", "params": {
        "budget_s": budget_s, "exclude_pairs": A.exclusions(names, refs=REFS, riders=(), shell_parts=SHELL_PARTS, borne=(), opening_air=OPENING_AIR)}})
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
        print("nudge:", A.nudge_faults(r["nudge"], s), [(p["a"], p["b"]) for p in r["nudge"]["interferences"]])
        print("plugs:", r["plugs"]["count"])
        print("extremes:", {f"{a}/{b}": round(d, 3) for (a, b), d in A.extreme_reach(r["extremes"]).items()})
        print("clearance:", {k: round(x, 2) for k, x in r["clearance"].items()})
        print("touch:", {f"{a}/{b}": round(x, 4) for (a, b), x in A.touch_volumes(r["touch"], TOUCHES).items()})
        print("passage near:", r["passage_near"])
        print("passage:", {k: round(x, 1) for k, x in passage_sections(s, r["passage"]).items()})
        for b in r["measure"]["bodies"]:
            if not b["name"].startswith(("ko_", "air_", "sweep_", "shell_up", "cl_")) and ":" not in b["name"]:
                pass
    else:
        for k, x in distances().items():
            print(k, round(x, 2))
