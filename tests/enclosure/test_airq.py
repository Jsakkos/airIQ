"""The airQ enclosure (Plan 3 Task 3a, R22, R24-R29): enclosure/src/airq.py and its check design.

Fast tests (CI included): the generator's names and parameters, R22's envelope, the board pose
against the layout study, the SEN66's pose (R17, R12), the positions read from their sources
(R27), the grille and air-path arithmetic (R18, R25, R26, M4), and the shell's insertion
arithmetic. SolidCraft tests (skipped without solidcraft-cli) cover the build and its bounding
box; the check design (interference 0 with every reference, the cables' keep-outs, the air
probes and the shell's sweep; the measured air sections; the gaskets touching what they seal);
and the rebuild over wall 1.6 / 2.4 and clr_* +-0.1.
"""
import json
import math
import re
import subprocess
from dataclasses import replace

import pytest
import yaml

import airq
import airq_check
import airq_face as F
import board_sources as B
import encbuild
import layout_study as L
import ref_epd
import ref_sen66
import ref_sfa40
from sclib import ENCLOSURE, REPO, interface

S = airq.build()
V = S.v
GROMMETS = ["grommet_zone_a", "grommet_zone_b", "grommet_j4_a", "grommet_j4_b", "grommet_tongue_a", "grommet_tongue_b"]
BODIES = ["shell", "base_plate", "zone_wall", "sen66_top_seal", "zone_seal", "sen66_foam", "gasket_out", "gasket_in", "sen66_pad", "hcho_lid",
          *GROMMETS, "light_guide", "crease_seal", "orange_dot"]
TPU = ["gasket_out", "gasket_in", *GROMMETS]
# positions Task 3b needs (task-3-scope, M6), fixed here as parameters
FACE = ["panel_x0", "panel_s0", "bezel", "window_xc", "pocket_x0", "pocket_x1", "led_f0", "led_h_slot", "led_len", "led_z",
        "guide_t", "adapter_x", "adapter_s", "adapter_t", "ffc_len", "j7_x0", "j7_x1", "sw_x", "sw_z", "dot_f", "dot_d",
        "lsw_x", "lsw_z", "lsw_d", "slot_row1_z", "slot_row2_z", "row_x0", "row_x1", "lsw_gap_x0", "lsw_gap_x1",
        "out_gx0", "out_gx1", "out_gz0", "out_gz1", "out_pitch", "out_n", "exh_x0", "exh_x1", "exh_z0", "exh_z1",
        "usb_x", "usb_z", "usb_well", "usb_chamfer",
        "win_x0", "win_x1", "win_s0", "win_s1", "win_chamfer",
        "ffc_w", "ffc_t", "ffc_r", "ffc_s_c3", "ffc_s_b0", "ffc_t_a", "ffc_x_m", "ffc_xc", "ffc_x_c1", "ffc_insert", "ffc_service_dz",
        "hold_s0", "hold_s1", "hold_t0", "hold_t1", "hold_x0", "hold_x1",
        "led_x0", "led_x1", "led_s0", "led_s1", "gd_t0", "gd_t1", "gd_sg", "gd_s0", "gd_y_e", "gd_l1x0", "gd_l1x1", "gd_l2x0", "gd_l2x1", "crease_y0", "crease_squeeze",
        "dot_s", "flex_s0", "flex_s1", "flex_x0", "flex_x1", "flex_stop", "y_pad", "sw_tip", "rod_y0"]


def test_bodies_and_plan_parameters():
    assert S.bodies == BODIES
    # the plan's names (Task 4 reuses them); the plan's `floor` is floor_t (SolidCraft reserves floor)
    for name in ("W", "D", "H", "tilt_deg", "wall", "floor_t", "grille_min_z", "slot_w",
                 "clr_align", "clr_remove", "clr_snap", "lip", "gasket_squeeze"):
        assert name in S.params, name
    for name in FACE:
        assert name in S.params, name


def test_r22_envelope():
    assert (V("W"), V("D"), V("H"), S.params["tilt_deg"].value, V("lip")) == (95.0, 55.0, 51.0, 30.0, 15.0)
    m = airq.MODEL
    assert L.min_depth(m, 0) <= V("D")                     # the lip layout fits 55 deep
    assert L.min_face_height(m) <= V("H") - 0.8            # the study's face plus the ledge's 1 mm


def test_board_pose_satisfies_the_layout_study():
    """The model's board (front-bottom corner at board_y0, board_z0) is a feasible pose of the
    study: every half-plane holds, and the LED/guide corner binds."""
    fy, fz = V("board_y0"), V("board_z0")
    for a, b, c, name in L.constraints(airq.MODEL, 0):
        assert a * fy + b * fz <= c + 1e-6, name
    front = next(c for a, b, c, n in L.constraints(airq.MODEL, 0) if n.startswith("front slope"))
    assert -V("cos_t") * fy + V("sin_t") * fz == pytest.approx(front, abs=1e-6)


def test_sen66_pose_keeps_r17_and_the_zone_rule():
    """The module stands (long axis along x, port face vertical, R17), its port face to the rear
    (the placement maps the module's port normal, -z, to +y) and its top under the zone wall."""
    m = airq_check.placements(S)[0]["matrix"]
    rot = [row[:3] for row in m]
    assert [rot[i][2] for i in range(3)] == [0, -1, 0]        # module +z -> world -y: ports (-z) face +y
    assert [rot[i][0] for i in range(3)] == [-1, 0, 0]        # long axis along x
    det = (rot[0][0] * (rot[1][1] * rot[2][2] - rot[1][2] * rot[2][1]) - rot[0][1] * (rot[1][0] * rot[2][2] - rot[1][2] * rot[2][0])
           + rot[0][2] * (rot[1][0] * rot[2][1] - rot[1][1] * rot[2][0]))
    assert det == 1
    assert V("sen_top") + V("zone_gap") == pytest.approx(V("zw_z0"))
    assert V("board_z0") >= V("zw_z1")                         # the zone rule: electronics above
    y_slant = (V("zw_tf") + V("zone_t") + (V("sen_top") - V("lip")) * V("sin_t")) / V("cos_t")
    assert V("sen_y0") >= y_slant                              # its front top edge behind the slant
    assert V("sen_x0") >= -V("tub_x") and V("sen_x1") <= V("hx0") - V("iwall")


def test_positions_are_read_from_their_sources():
    """R27: every board and reference position the design uses equals its source."""
    main, tongue = interface()["mechanical"]["main"], interface()["mechanical"]["tongue"]
    sen, sfa, epd = ref_sen66.build().v, ref_sfa40.build().v, ref_epd.build().v
    x0, ztop = V("board_x0"), V("board_z0") + V("board_t")
    assert V("sw_x") - x0 == main["button"]["actuator_center_x"]
    assert V("sw_z") - ztop == pytest.approx(main["button"]["actuator_center_z"])
    assert V("led_z") - ztop == pytest.approx(main["leds"]["light_center_z"])
    assert (V("j7_x0") + V("j7_x1")) / 2 - x0 == pytest.approx(main["fpc"]["center_x"])
    assert V("j7_x1") - V("j7_x0") == pytest.approx(float(re.search(r"body ([\d.]+) wide", (REPO / "hardware/interface.yaml").read_text()).group(1)))
    assert V("usb_x") - x0 == pytest.approx(main["usb_c"]["center_x"])
    assert V("usb_z") - ztop == pytest.approx(main["usb_c"]["shell"][1] / 2)
    assert V("tongue_x1") - V("lsw_x") == pytest.approx(tongue["veml7700"]["window_center"][0])
    assert V("lsw_z") - V("tongue_z0") - V("tongue_t") == pytest.approx(tongue["veml7700"]["window_center"][2])
    assert V("sen_x1") - V("outlet_x") == pytest.approx(sen("outlet_x"))
    assert V("sen_top") - V("outlet_z") == pytest.approx(sen("outlet_y"))
    assert V("outlet_d") == sen("outlet_d")
    assert V("panel_x0") + V("panel_l") - V("window_xc") == pytest.approx(epd("va_far") + epd("va_w") / 2)
    assert V("sfa_w") == sfa("board_w") and V("sfa_cap") == pytest.approx(sfa("sensor_top"))
    h = main["mounting_holes"]["centers"]
    assert (V("h1_x") - x0, V("board_y0") + V("board_d") - V("h1_y")) == pytest.approx(tuple(h[0]))
    # U2 (buck): layout.yaml placement and its footprint's courtyard (interface.yaml has no U2)
    place = yaml.safe_load((REPO / "hardware/src/main/layout.yaml").read_text())["placement"]
    u2 = B.layout_part("U2")
    assert u2["center"] == tuple(place["U2"]["at"][:2])
    (bx0, by0), (bx1, by1) = u2["box"]
    assert bx0 < u2["center"][0] < bx1 and by0 < u2["center"][1] < by1
    assert B.layout_part("U4")["center"] == tuple(place["U4"]["at"][:2])


BOARD_NUMBERS = {57.0, 42.4, 12.8, 20.5, 18.35, 1.95, 28.8, 7.75, 24.6, 3.16, 8.94, 7.35, 67.5, 2.7, 25.4, 4.25, 2.95,
                 12.36, 8.55, 57.4, 22.8, 5.99}


def _code_numbers(path):
    """Numbers in a generator's code: numeric literals and the numbers inside expression strings,
    leaving out docstrings and the comments given to parameters (the third argument of p(...))."""
    import ast
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(node, (ast.Module, ast.FunctionDef)) and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant):
            skip.add(id(body[0].value))
        if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) in ("p", "param"):
            for a in node.args[2:3]:
                skip.add(id(a))
                skip.update(id(n) for n in ast.walk(a))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and id(node) not in skip:
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                out.append(float(node.value))
            elif isinstance(node.value, str):
                out += [float(x) for x in re.findall(r"(?<![\w.])\d+\.\d+(?![\w.])", node.value)]
    return out


def test_generator_retypes_no_board_numbers():
    """R27: the generators' code carries no copies of the boards' or references' numbers."""
    for f in ("airq.py", "airq_check.py", "enclosure_common.py"):
        found = BOARD_NUMBERS & set(_code_numbers(ENCLOSURE / "src" / f))
        assert not found, (f, found)


def test_distances_answered_by_the_layout():
    d = airq_check.distances(S)
    assert d["antenna_to_sen66"] >= 15 and d["antenna_to_usb_plug"] >= 15          # R12
    assert d["antenna_to_bosses_and_screws"] >= 15 and d["antenna_to_standoff_screws"] >= 15
    assert d["antenna_to_sfa40"] >= 15                                              # metal kept out of the 15 mm too
    assert d["tongue_to_u3"] >= 20 and d["tongue_to_u2"] >= 20                     # plan
    assert d["h1_to_usb_c_centre"] <= 8.0                                            # support boss within 8 mm
    assert d["h1_free_above_plenum"] <= 2.5                                         # M7: braced to 2.1 under the board
    assert 0 < d["antenna_end_to_rear_wall"] < 1.0


def test_grilles_r18_and_10_mm_rule():
    d = airq_check.distances(S)
    assert d["outlet_grille_open_mm2"] >= 660.1                                     # R18: 2 x 330.1
    assert d["intake_open_mm2"] >= 154.5                                            # R18: 2 x 77.3
    sfa = ref_sfa40.build().v
    assert d["hcho_grille_open_mm2"] >= 2 * sfa("opening_l") * sfa("opening_w")     # 2 x the SFA40's opening
    assert min(d["hcho_grille_lower_edge_z"], d["outlet_grille_lower_edge_z"], V("slot_row1_z"),
               V("lsw_z") - V("lsw_d") / 2, V("exh_z0")) >= V("grille_min_z")       # 10 mm rule
    assert V("out_gx1") <= V("tub_x") - 2.0                                          # the grille stays in the plenum
    assert V("exh_z0") > V("zw_z1") + 2.0                                            # the exhaust stays apart (R26)
    # N7: the intake slots (lip's outer face, y 0) and the outlet slots (rear wall's outer face, y D)
    assert d["intake_to_outlet_grille"] == V("D") >= 20


def test_r26_alternatives_worked():
    """R26: the HCHO pocket's alternatives with numbers; only the chosen one keeps 660.1."""
    rows = L.hcho_alternatives(airq.MODEL)
    assert [r["meets"] for r in rows] == [False, False, False, False, True]
    assert rows[-1]["open_50"] == pytest.approx(airq_check.distances(S)["outlet_grille_open_mm2"])
    assert not rows[1]["fits"] and not rows[3]["fits"]
    # the reason the ports turned to the rear: the front layer cannot reach 330.1 (R25)
    assert L.front_layer(airq.MODEL, 20.0, under_ledge=True) < 330.1


def test_air_paths_by_their_parameters():
    """R25 from the parameters (the check design measures the same on the geometry)."""
    assert V("port_gap") * (V("zw_z0") - V("floor_t")) >= 77.3                       # inlets: the gap
    assert math.pi * V("ring_bore") ** 2 / 4 >= 330.1                                # outlet: the ring's bore
    assert V("ring_bore") > V("outlet_d")
    sfa = ref_sfa40.build().v
    assert V("sfa_w") * V("hcho_air") >= sfa("opening_l") * sfa("opening_w")         # HCHO: over the cap


def test_tongue_leaves_the_intake_rows_open():
    """M4: the tongue is set back from the lip; the slots in front of it feed a channel whose
    side exits pass at least their open area."""
    exits = 2 * V("tongue_gap") * (V("ledge_z0") - V("lid_z0") - V("lid_t"))
    span = V("tongue_x1") - max(V("tongue_x1") - V("tongue_w"), V("lsw_gap_x1"))
    in_front = 2 * V("slot_w") * (span - V("slot_bar"))
    assert exits >= in_front
    assert V("tongue_z0") + V("tongue_t") + V("tongue_parts_h") <= V("ledge_z0")     # under the ledge


def test_shell_lowers_onto_the_base():
    """I1, R24 (arithmetic; the check design sweeps it): the shell goes on from above along -z:
    its floor bosses pass the zone wall's notches, clear of the board's footprint, and the rear
    boss stays above and left of the board."""
    assert airq_check.insertion_probe(S) == []


def _feature(name):
    return next(c["params"] for c in S.commands if c["params"].get("name") == name)


def test_shell_keeps_clr_remove_off_its_datums():
    """Review N1: the shell sits on the floor (z) and against the rear wall's front face (y); at
    the lip it keeps clr_remove: its side walls end clr_remove behind the lip's inner face, its
    slope stops clr_remove above the lip's top, and the lip is recessed clr_remove round the bosses."""
    lip = _feature("Lip to the base")
    y1 = V(lip["corner"][1]) + V(lip["width"])
    z1 = V(lip["corner"][2]) + V(lip["height"])
    assert y1 == pytest.approx(V("wall") + V("clr_remove")) and z1 == pytest.approx(V("lip") + V("clr_remove"))
    crease = _feature("Crease seat")
    assert V(crease["corner"][2]) + V(crease["height"]) == pytest.approx(V("lip") + V("clr_remove"))
    rec = _feature("Boss clearance 1")
    assert V(rec["corner"][1]) == pytest.approx(V("wall") - V("clr_remove"))           # the boss's front is at wall
    assert V("boss_y") - V("boss_d") / 2 == pytest.approx(V("wall"))
    assert V(rec["length"]) >= V("boss_d") + 2 * V("clr_remove") - 1e-9
    # the datums: the side walls end on the rear wall (y) and stand on the floor (z)
    assert V(_feature("Rear wall seat")["corner"][1]) == pytest.approx(V("D") - V("wall"))
    assert V(_feature("Floor seat")["height"]) - V("wall") == pytest.approx(V("floor_t"))


def test_hcho_window_shows_only_the_rail_and_the_zone_wall():
    """Review N2: each step of the HCHO window covers its grille slot and stops under the top of
    what stands behind it (the right rail, which follows the zone wall's underside, then the zone
    wall's end face), so the window does not open the electronics zone."""
    vert = V("zone_t") / V("sin_t")                                       # the slant's height through its thickness
    prev = V("grille_min_z")
    for i, (y_lo, y_hi, top) in enumerate(airq.window_steps()):
        slot_y = f"cy0 + 0.6 + {i} * hg_pitch"
        slot_top = V(f"{airq.C.z_under(slot_y)} - hg_margin")
        assert V(y_lo) <= V(slot_y) and V(slot_y) + V("slot_w") <= V(y_hi)            # the slot is inside its step
        assert V(top) > slot_top > prev                                            # the slot is open, the steps rise
        assert V(top) <= V(airq.C.z_under(y_lo)) + min(vert, V("ledge_t"))            # backed at its lowest corner
        prev = slot_top


def test_cables_install_with_their_plugs_on():
    """Review I2: every cable crossing a sealed wall goes in with both plugs on.
    - The lid's hole passes the Qwiic plug (its section, the receptacle's, + clr_remove a side):
      the lid goes on over the SFA40's cable to the tongue.
    - The zone wall's drawer and the HCHO pocket's J4 notch are open to an edge (the zone wall's
      left end, the wall's top), so their cables are laid in from the side: no plug passes them
      (the GH plug, up to 10.75 x 4.25, passes no closed opening at all).
    - Every grommet is two halves split along its cables, so it closes round them."""
    assert V("lid_hole_l") >= V("qw_plug_w") + 2 * V("clr_remove") - 1e-9
    assert V("lid_hole_w") >= V("qw_plug_t") + 2 * V("clr_remove") - 1e-9
    assert (V("qw_plug_w"), V("qw_plug_t")) == (6.0, 2.95)                          # the check design's own envelopes
    notch = _feature("Drawer notch")
    assert V(notch["corner"][0]) < V("-inner_x + clr_remove")                     # through the zone wall's left end
    assert V(notch["corner"][0]) + V(notch["length"]) == pytest.approx(V("pt_x1"))
    j4 = _feature("J4 notch")
    assert V(j4["corner"][2]) + V(j4["height"]) > V("lid_z0")                     # through the wall's top
    assert V("j4n_w") >= V("cable_qw_d") + 1.6 - 1e-9
    assert [n for n, *_ in airq_check.PLUG_PASSES] == ["plug_lid"]
    for a, b in (("grommet_zone_a", "grommet_zone_b"), ("grommet_j4_a", "grommet_j4_b"), ("grommet_tongue_a", "grommet_tongue_b")):
        assert a in S.bodies and b in S.bodies


def test_grommets_squeeze_and_are_held():
    """Review N4: each grommet is sized at contact plus gasket_squeeze on the faces it seals (the
    check's touch run proves the contacts) and is held: the drawer halves' ribs sit in the notch's
    grooves (clr_align round them, inside the zone wall's thickness), the J4 halves straddle the
    wall with flanges under the lid, the lid halves have a flange over the lid and a barb under it
    clear of the SFA40's plug."""
    assert V("groove_d") > V("clr_align") and V("groove_w") - 2 * V("clr_align") >= 0.45
    assert V("groove_w") < V("zone_t") - 0.8                                           # the zone wall keeps 0.5 a side
    assert V("pt_y0") - V("groove_d") >= V(airq.C.yb("ledge_z0")) - 1e-9              # the front groove stays in the slant
    assert V("j4_fl") > 0 and V("tg_fl") > 0 and V("tg_barb") > 0
    # round 3, B6: the ribs stand groove_d - clr_align proud of the printed face at any squeeze
    rib = _feature("Zone grommet a")
    assert "drawer_squeeze + groove_d" in json.dumps(S.commands)
    assert V("groove_d") - V("clr_align") >= 0.4 and V("bore_squeeze") > 0 and V("grommet_squeeze") <= 0.1
    sfa_top = V("floor_t") + V("sfa_bt") + airq_check._SFA("qwiic_h")                 # the SFA40's Qwiic plugs' top
    assert V("lid_z0") - V("tg_barb_t") > sfa_top                                       # the barbs pass over the rear plug
    pairs = {frozenset(p) for p in airq_check.TOUCHES}
    for g in GROMMETS:
        assert any(g in p for p in pairs), g


def test_gravity_parts_are_held():
    """Review N5: nothing that seals rests by gravity alone.
    - The zone wall sits on the standoffs' spigots and carries pads up to the board: the board's
      M2 screws clamp it (no gap between its pads and the board's underside).
    - The HCHO lid and the SFA40 are clamped to the base by two M2 screws from under the floor,
      through the SFA40's front-left and rear-right holes, into the lid's posts (pilots in them).
    - The tongue is located by its pocket in the lid and held under the zone wall's pad over its
      VEML7700, clr_align above it."""
    pad = _feature("Zone wall pad H1")
    assert V(pad["base"][2]) + V(pad["height"]) == pytest.approx(V("board_z0"))
    assert V(_feature("Standoff H1")["height"]) == pytest.approx(V("zw_z0 - floor_t + 0.5"))   # up to the zone wall only
    assert V("spigot_h") > 0 and V("screw_d") > V("pilot_d")
    for dx, dy in airq.SFA_SCREWS:
        i = airq.SFA_HOLES.index((dx, dy)) + 1
        assert f"SFA40 screw hole {i}" in S.features and f"SFA40 hold-down {i} pilot" in S.features
        assert f"SFA40 pin {i}" not in S.features
    assert V("floor_t") - V("head_depth") >= 1.6
    assert V("lid_pilot_depth") <= V("lid_z0") - V("floor_t") - V("sfa_bt") + V("lid_t") - 0.5      # blind in the post and lid
    hold = _feature("Tongue hold-down")
    gap = V(hold["corner"][2]) - (V("tongue_z0") + V("tongue_t") + V("tongue_parts_h"))
    assert gap == pytest.approx(V("clr_align"))
    assert V(hold["corner"][1]) + V(hold["width"]) <= V(airq.C.yb("ledge_z0"))        # under the ledge
    assert 0 < V("tongue_recess") < V("lid_t")
    assert "Tongue pin" not in S.features                                          # the lid's top is flat: prints top down


def test_screw_heads_leave_a_floor():
    assert V("floor_t") - V("head_depth") >= 1.6                                   # M5: >= 1.6 under the head


def test_gaskets_have_a_squeeze_and_seats():
    """I3/R9: the TPU parts are sized at contact plus their squeeze; the check runs at 0."""
    assert V("gasket_squeeze") > 0 and V("seat_d") > 0 and V("wiper_squeeze") > 0 and V("pad_squeeze") > 0
    first = json.dumps(airq_check.check_script()["commands"][6])
    assert all(n in first for n in airq_check.SQUEEZES)


def test_sen66_held_over_its_depth_tolerance():
    """I3(b): the port face rests on the outlet ring's land (ring_preload 0: the ring is the stop),
    so the seals see the same port face at 20.8, 21.3 and 21.8 deep; the pad at the front takes the
    tolerance between 33 and 67 % compression; a 21.8 module still clears the guide rail and the
    zone wall's slant; and the pad's force (through the ring's axis) beats the soft inlet blade's
    moment, so the module cannot tip or yaw off the ring."""
    h = airq_check.sen66_hold(S)
    assert V("ring_preload") == 0 and V("pad_y0") + V("pad_gap") == pytest.approx(V("sen_y0"))
    comp, give = h["pad_compression"], h["pad_compression_with_give"]
    assert 0.25 <= min(comp.values()) and max(comp.values()) <= 0.65
    assert min(give.values()) >= 0.25 and max(give.values()) <= max(comp.values())     # the seat's give keeps it in range
    assert h["front_clear_rail"] >= V("clr_align") - 1e-9 and h["front_clear_slant"] >= V("clr_align")
    # round 3: the land stays loaded all round (the reaction inside the land's kern), with margin
    ro, ri = V("ring_od") / 2, V("ring_bore") / 2
    assert h["kern"] == pytest.approx((ro ** 2 + ri ** 2) / (4 * ro))
    assert h["pad_force_min"] == pytest.approx(max(h["wiper_force"]) * (1 + h["arm"] / h["kern"]))
    assert h["pad_force_spec"] == pytest.approx(airq_check.PAD_MARGIN * h["pad_force_min"])
    assert h["pad_force_spec"] < airq_check.PAD_FORCE_MAX / 2
    assert max(h["wiper_force"]) < 1.0


def test_pad_seat_is_stiff_and_tied():
    """Review round 3, B1: the pad's seat is a seat_t plate joined to the left side rail along its
    height (not a free 1.6 rail), behind the cables' riser and run; its stiffness (two cantilevers,
    E of PETG) keeps its give under 0.25 at PAD_FORCE_MAX and its root stress across the layers
    under 8 MPa (creep). B4: its back edge has a 45 deg lead-in that the pad's lower edge meets
    whatever the module's depth, and its top stays under the drawer's grommet."""
    h = airq_check.sen66_hold(S)
    seat = _feature("Pad seat")
    assert seat["distance"] == "plug_x0 - 1.0 + tub_x + iwall"                    # from the side rail's outer face
    assert V("seat_t") >= 2.4 and h["seat_k"] >= 50 and h["seat_give"][1] <= 0.25 and h["seat_stress"] <= 8.0
    assert V("seat_y0") >= V("pt_yh + cable_gh_d / 2") + V("clr_align") - 1e-9       # behind the cables' riser
    # the lead-in: the pad's front face (free) meets the inclined top for every module depth
    entry = [V("sen_y1") - d - V("pad_t") for d in (V("sen_d") + V("sen_d_tol"), V("sen_d") - V("sen_d_tol"))]
    assert V("seat_y0") < min(entry) and max(entry) < V("pad_y0")
    assert V("seat_y0") < V("seat_apex_y") < V("pad_y0") and V("seat_apex_z") > V("seat_lead_z") > V("outlet_z") + V("pad_h") / 2
    # its top stays seat_slant_clr under the zone wall's slant (and the drawer grommet's squeezed face)
    under = V(airq.zt("seat_apex_y", "zw_tf + zone_t")) - V("seat_apex_z")
    assert under == pytest.approx(V("seat_slant_clr")) and V("seat_slant_clr") > V("gasket_squeeze") / V("sin_t")


def test_plug_room_at_the_deepest_module():
    """Review round 3, B2: a 21.8 module's plug and cable bend (their keep-outs moved sen_d_tol
    forward with its connector face) stay clr_remove clear of the zone wall's slant, in the pocket
    over them; the slant keeps 1.3 there."""
    tb = V("zw_tf + zone_t")
    mid = V("sen_top - sen_up / 2")
    front = V("sen_y0 - sen_d_tol")
    for y, z in ((front - 6.0, mid + 2.5), (front - 6.94, mid + 0.7)):        # the plug's and the bend's top front corners
        depth = y * V("cos_t") - (z - V("lip")) * V("sin_t")                  # t of the corner
        assert depth >= tb - V("plug_room_d") + V("clr_remove") - 1e-9, (y, z, depth)
        assert V("plug_room_z0") < z < V("plug_room_z1")
    assert V("zone_t") - V("plug_room_d") >= 1.2


def test_sfa40_screws_and_feet():
    """Review round 3, B5: the SFA40's screws are M2 x 6: from the counterbore's floor their tips
    stay in the posts' pilots (2 mm of thread or more), under the tongue's pocket; their heads stand
    head_h - head_depth under the floor, less than the felt feet, which they do not sit under (the
    front feet cover the shell's screws)."""
    tip = V("head_depth") + V("sfa_screw_l")
    pilot_top = V("floor_t + sfa_bt - 0.5 + lid_pilot_depth + 0.5")
    assert V("floor_t + sfa_bt") + 2.0 <= tip <= pilot_top - 0.5
    assert pilot_top + 0.5 <= V("lid_z0 + lid_t - tongue_recess")                    # material over the pilot, under the tongue
    assert V("head_h") - V("head_depth") <= V("foot_t") - 0.5
    feet = [(sx * V("boss_x"), V("boss_y")) for sx in (-1, 1)] + [(sx * V("foot_rx"), V("foot_ry")) for sx in (-1, 1)]
    for dx, dy in airq.SFA_SCREWS:
        hx = V(f"sfa_x0 + sfa_hole_in + {dx} * (sfa_w - 2 * sfa_hole_in)")
        hy = V(f"sfa_y0 + sfa_hole_in + {dy} * (sfa_w - 2 * sfa_hole_in)")
        assert all(math.hypot(hx - fx, hy - fy) > V("foot_d") / 2 + V("head_d") / 2 for fx, fy in feet)
    assert V("foot_d") >= V("head_d") + 4                                            # the front feet cover the shell's screw heads


def test_seal_forces_stay_small():
    """Review round 3: the zone seal is closed-cell foam 25 % compressed (TPU 95A at 20 % would push
    hundreds of N and bow the slotted lip); the drawer grommet's push on the zone wall's sliver is
    carried by the key on the boss pocket; the J4 grommet's stack meets the lid at contact (it no
    longer lifts it); the foam strip over the SEN66 pushes the zone wall a few N near H1."""
    f = airq_check.seal_forces(S)
    assert 0.2 <= f["zone_seal_compression"] <= 0.3 and max(f["zone_seal_n"]) <= 15
    assert max(f["key_stress_mpa"]) <= 8 and max(f["drawer_front_n"]) <= 60
    assert f["j4_lid_n"] == 0 and max(f["top_seal_n"]) <= 15
    j4b = _feature("J4 grommet b")
    assert V(j4b["corner"][2]) + V(j4b["height"]) == pytest.approx(V("lid_z0"))     # at contact with the lid


def test_space_beside_the_ring_is_closed():
    """Review round 3: the 0.3 gap over the SEN66 joined the space left of the inlet wiper to the
    inlets' side round the wiper's tip (a 5 mm path). sen66_top_seal closes it across the module's
    top at the wiper's tip, from the port face to the connector face, so that space reaches only the
    front plenum, through slits 21 mm long, far from the inlets."""
    tip0 = V("wiper_x1 - wiper_lean - wiper_w")
    tip1 = V("wiper_x1 - wiper_lean")
    assert V("top_seal_x0") <= tip0 - 1.0 + 1e-9 and V("top_seal_x1") >= tip1 + 1.0 - 1e-9
    seal = _feature("SEN66 top seal")
    assert V(seal["corner"][1]) == pytest.approx(V("sen_y0")) and V(seal["width"]) == pytest.approx(V("sen_d"))
    gaps = (V("zone_gap") - 0.1, V("zone_gap") + 0.2)                              # the module's height +0.1 / -0.2
    assert all(0.15 <= 1 - g / V("top_seal_t") <= 0.7 for g in gaps)


def test_inlet_seal_root_and_lead_in():
    """Review round 3, B3: the inlet seal's root is a root_w foot squeezed root_squeeze into its
    slot's sides and back (no bypass round it, no travel to eat the preload). B4: its tip has a
    45 deg lead-in at the top, deeper than its preload, so the module's bottom edge pushes it back."""
    groove = _feature("Inlet seal groove")
    assert V(groove["length"]) == pytest.approx(V("root_w")) and V(groove["width"]) == pytest.approx(V("seat_d") + 0.5)
    assert V("root_squeeze") > 0 and V("root_w") > V("wiper_w")
    assert V("wiper_lead") > V("wiper_squeeze") + 0.2
    assert ("gasket_in", "base_plate") in airq_check.TOUCHES
    assert V("outlet_z") - V("pad_h") / 2 >= V("floor_t") + V("foam") + ref_sen66.build().v("plinth_inset")   # on the plinth
    # the blade stays out of the inlets' path (R25) and clear of H1
    assert V("wiper_x1") <= V("inlet_x0") - 1.0 + 1e-9
    y_h1 = V("h1_y") - V("standoff_d") / 2                                   # H1's front, standing into the gap
    blade_left = V("wiper_x1 - wiper_w") - (V("plate_y0") - y_h1) * math.tan(math.radians(S.params["wiper_deg"].value))
    assert blade_left > V("h1_x") + V("standoff_d") / 2


def test_face_positions_follow_their_parts():
    assert V("dot_f") == pytest.approx(V("lip") + (V("sw_z") - V("lip")) / V("cos_t"))   # on SW1's push axis
    assert V("sw_x") - V("dot_d") / 2 > V("panel_x0") + V("panel_l") + V("clr_remove") + 1.2   # right of the pocket
    assert V("slot_row1_z") >= V("grille_min_z")
    assert V("slot_row2_z") + V("slot_w") <= V("ledge_z0")                           # slots under the ledge
    led_inner_z = V("lip") + (V("led_f0") - V("lip")) * V("cos_t") - V("wall") * V("sin_t")
    assert led_inner_z >= V("ledge_z1")                                             # LED slot above the ledge
    s_top = V("panel_s0") + V("panel_w")
    assert V("lip") + s_top * V("cos_t") - (V("bezel") + V("panel_t")) * V("sin_t") <= V("H") - V("wall")
    assert V("adapter_t") <= V("zw_tf")                                             # adapter in front of the zone wall
    assert V("row_x0") < V("lsw_gap_x0") < V("lsw_x") < V("lsw_gap_x1") < V("row_x1")


def test_window_and_pocket_follow_the_panel():
    """3b-1 feature 1: the window is the active area (3.00 from the far end, 3.82 from the long
    edges, 66.90 x 29.06) and the pocket is the panel plus clr_remove, with the block's room."""
    epd = ref_epd.build().v
    assert (V("aa_w"), V("aa_h"), V("aa_far"), V("aa_edge")) == pytest.approx((66.90, 29.06, 3.00, 3.82))
    assert V("panel_x0") + V("panel_l") - V("win_x1") == pytest.approx(3.00)
    assert V("win_s0") - V("panel_s0") == pytest.approx(3.82) and V("panel_s0") + V("panel_w") - V("win_s1") == pytest.approx(3.82)
    assert V("win_x1") - V("win_x0") == pytest.approx(66.90) and V("win_s1") - V("win_s0") == pytest.approx(29.06)
    assert V("win_chamfer") < V("bezel")                                    # a land is left at the panel
    assert V("pocket_x1") - (V("panel_x0") + V("panel_l")) == pytest.approx(V("clr_remove"))
    assert V("panel_x0") - V("block_out") - V("pocket_x0") == pytest.approx(V("clr_remove"))   # room for the hatched block
    assert V("pocket_x0") >= -V("inner_x") - 1e-9                           # inside the side walls
    assert V("block_out") == pytest.approx(epd("block_out")) == pytest.approx(4.6)


def test_ffc_route_length_and_service_lift():
    """3b-1 feature 2 (R42: at most three 45-degree direction-change folds, made once at assembly over a jig): the
    FFC is 12.5 x 0.3; the route has at most three folds (flat, no radius, not re-flexed) and one radiused bend
    into J7 of inner radius >= 1 (the only bend that moves); its centre line plus the two insertions fills the
    bought 80 mm within the length tolerance (so there is no slack to place and no bow); with both ends plugged
    in the shell can be lifted the service distance with a margin of 3 mm or more over the straight distance."""
    g = F.ffc_geometry(V, V("ffc_s_c3"))
    assert (V("ffc_w"), V("ffc_t")) == pytest.approx((12.5, 0.3))
    assert round(g["creases"] / V("ffc_crease")) <= 3                              # at most three folds
    assert V("ffc_r") - V("ffc_t") / 2 >= 1.0                                        # the J7 bend: inner radius >= 1
    assert g["arc1"] > 0 and g["arc2"] > 0 and min(V("ffc_r") - V("ffc_t") / 2, V("ffc_r") + V("ffc_t") / 2) >= 1.0
    assert g["centre_len"] + 2 * V("ffc_insert") <= V("ffc_len")                    # fits the bought length
    assert V("ffc_insert") <= B.j7_body()[1] - 0.2 + 1e-9                           # inserted short of J7's back
    spare = V("ffc_len") - 2 * V("ffc_insert") - g["centre_len"]
    assert 0 <= spare <= V("ffc_tol")                                               # the route matches the length: no bow
    assert V("ffc_len") == 80.0                                                     # a standard length
    # J7: the ribbon enters its mouth between D2 and D3, inside the 15.5 body, flat, 1 mm over the board
    leds = B.MAIN["leds"]["chain"]
    d2, d3 = V("board_x0") + leds[1]["center_x"] + 2.0, V("board_x0") + leds[2]["center_x"] - 2.0
    assert d2 < V("ffc_xc") - V("ffc_w") / 2 and V("ffc_xc") + V("ffc_w") / 2 < d3
    assert V("j7_x0") <= V("ffc_xc") - V("ffc_w") / 2 and V("ffc_xc") + V("ffc_w") / 2 <= V("j7_x1")
    assert V("ffc_z_j7") - V("board_z0") - V("board_t") == pytest.approx(B.MAIN["fpc"].get("slot_h", 1.0))
    path = F.ffc_path(V, g)
    assert path[-1][0] == pytest.approx(V("board_y0"), abs=0.02) and path[-1][1] == pytest.approx(V("ffc_z_j7"))
    assert path[-1][2] == 0.0 and g["l_v"] >= 0 and g["u"] > 0                      # horizontal into J7, a real route
    # the run under the LEDs stays below their faces; the adapter's mouth is where the route starts
    led_lo = V("board_y0") * V("sin_t") + (V("led_z") - 1.0 - V("lip")) * V("cos_t")
    assert V("ffc_s_c3") + V("ffc_w") / 2 <= led_lo - 0.29
    assert V("ffc_x_m") == pytest.approx(V("adapter_x") + V("ad_l") / 2)
    sv = F.ffc_service(V, g, V("ffc_service_dz"))
    assert sv["ok"] and sv["chain"] - sv["d_lift"] - V("ffc_service_margin") >= 3.0, sv   # service lift: 3 mm over the allowance
    assert V("ffc_service_dz") <= V("zw_z1") + 1 - (V("floor_t") + V("boss_h"))     # the bosses are still in the zone wall's notches: the shell stays guided
    # the contacts side and pin 1 (hardware/interface.yaml mechanical.main.fpc.pin_order)
    out = F.ffc_pin_outcome()
    assert out == {"creases": 3, "contacts_up": True, "pin1_x": 1, "mirrored": False}
    assert B.MAIN["fpc"]["pin1_x"] > B.MAIN["fpc"]["center_x"]                       # pin 1 on the viewer's right


def test_adapter_holder_flanks_the_board():
    assert V("hold_s0") - (V("adapter_s") + V("ad_w") / 2) == pytest.approx(V("clr_remove"))      # clr_remove over the upper edge
    assert V("hold_t0") < V("adapter_t") - V("ad_pcb_t") and V("hold_t1") < V("zw_tf")             # beside the board, short of the zone wall
    assert V("hold_x0") <= -V("inner_x") and V("hold_x1") == pytest.approx(V("adapter_x") + V("ad_l") / 2)
    # it must not sit in the cables' strip (airq cable_params): the arm is above its top end
    assert V("hold_s0") * V("cos_t") + V("lip") - V("hold_t1") * V("sin_t") > V("zw_z1") + 2.6      # z above the strip's top


def test_led_slot_and_light_guide_follow_the_leds():
    """3b-1 feature 3: a 30 mm slot centred under the window; a clear guide whose entry faces are gd_clr in
    front of the four LED faces (at their real positions, 4.0 x 2.0 centred 1.0 above the board), whose
    legs end at the faces' top edge, and which keeps out of the FFC's strip into J7 and behind the panel."""
    leds = B.MAIN["leds"]["chain"]
    assert V("led_x1") - V("led_x0") == pytest.approx(30.0) and (V("led_x0") + V("led_x1")) / 2 == pytest.approx(V("window_xc"))
    for i, led in enumerate(leds, 1):
        assert V(f"led_d{i}_x") - V("board_x0") == pytest.approx(led["center_x"])
    assert (V("led_face_w"), V("led_face_h")) == pytest.approx((4.0, 2.0))
    assert V("led_z") - V("board_z0") - V("board_t") == pytest.approx(1.0)                  # the face's centre, 1.0 above the board
    assert V("gd_y_e") == pytest.approx(V("board_y0") - V("gd_clr"))
    assert V("gd_t0") >= V("bezel") + V("panel_t") + V("clr_remove") - 1e-9               # behind the panel's back face
    assert V("gd_t1") - V("gd_t0") == pytest.approx(V("guide_t"))
    assert V("gd_l1x0") < V("led_d1_x") - 2.0 and V("led_d2_x") + 2.0 < V("gd_l1x1")        # the legs flank the LED faces
    assert V("gd_l2x0") < V("led_d3_x") - 2.0 and V("led_d4_x") + 2.0 < V("gd_l2x1")
    assert V("gd_l1x1") < V("ffc_xc") - V("ffc_w") / 2 and V("ffc_xc") + V("ffc_w") / 2 < V("gd_l2x0")   # the FFC's strip is clear
    assert V("gd_l1x1") - V("gd_l1x0") < 10.0 and V("gd_l2x1") <= V("board_x0") + V("board_w")
    zmin = V("lip") + V("gd_sg") * V("cos_t") - V("gd_t0") * V("sin_t")
    assert zmin >= V("lip") + V("clr_remove") + 0.2 - 1e-9                                  # no part of the guide lower than 0.4 over the lip's top
    assert V("gd_top_z") == pytest.approx(V("led_z") + V("led_face_h") / 2)                 # no surface sees over the LEDs
    assert V("panel_s0") - V("clr_remove") - V("led_s1") >= 0.9                                  # a bar of about 1 between slot and pocket


def test_guide_fits_come_from_the_clearances():
    """Review I2: the guide's fits are clr_align / clr_remove, not literals (a coupon result moves them), and the
    bar's gap to the panel (the adhesive pad that holds the guide) is clr_remove."""
    assert V("gd_tg") == V("clr_align") and V("gd_clr") == V("clr_remove")
    assert V("gd_t0") - (V("bezel") + V("panel_t")) == pytest.approx(V("clr_remove"))
    assert V("gd_rec") >= V("clr_remove")                                          # the tongue's face is behind the face
    assert V("led_s1") - V("led_s0") - 2 * V("gd_tg") > 0.4                         # a visible tongue


def test_guide_delivers_light_to_the_exit():
    """Review I1 / R40, analytic: 2-D ray trace in the guide's section from each entry window, in the LED's cone,
    with TIR (critical angle 39.6) and escapes. Every foot facet meets the light over the critical angle, rays
    reach the exit through the foot facet and the bottom facet, and most entry points deliver. It does not
    prove the line is even along its 30 mm (that needs a rough bottom facet or a print)."""
    assert 90 - S.params["tilt_deg"].value > airq_check.CRIT_DEG + 10              # the foot facet's incidence (60 deg)
    d = airq_check.guide_delivery(S)
    assert d["delivered"] >= 10 and d["fraction"] >= 0.03, d
    assert d["entry_points_reaching"] >= d["entry_points"] - 1, d
    assert min(d["bounces"]) >= 2                                                  # foot facet, then the bottom facet


def test_guide_light_stays_off_the_crease_the_sensor_and_u4():
    """3b-1 feature 3: from every non-exit surface of the guide, every straight line to the light
    sensor, to the lip's window and to the crease (the 0.2 parting line's front, which the foam tape
    plugs) crosses at least 1.2 mm of opaque material; no line from an LED face or a guide window
    reaches the MS5611 (R13)."""
    paths = airq_check.light_paths(S)
    for name, (length, _) in paths.items():
        assert length >= 1.2 - 1e-6, (name, length)
    sight = airq_check.ms5611_sight(S)
    assert sight["unblocked"] == {"led_faces": 0, "entry_windows": 0}, sight
    assert sight["samples"]["entry_windows"] > 100
    # the crease seal: the lip's top to the shell's lowest plane, over 1.2 of foam
    assert V("wall") - V("crease_y0") >= 1.2                                                 # foam tape: 1.2 or more along the line


def test_panel_top_keeps_clr_remove_under_the_top_wall():
    top_z = V("lip") + (V("panel_s0") + V("panel_w")) * V("cos_t") - (V("bezel") + V("panel_t")) * V("sin_t")
    assert V("H") - V("wall") - top_z >= V("clr_remove") - 1e-9


def test_dot_and_flexure_on_sw1s_axis():
    """3b-1 feature 4: the dot is on SW1's push axis (the axis meets the face at the dot), top right; the flexure
    is the coupon's (flex_t, flex_len, flex_gap); the pad stops flex_gap short of the actuator tip; the hard
    stop lets the dot move flex_gap + the switch's travel and no more; beam stress stays small."""
    z_on_face = V("lip") + V("dot_s") * V("cos_t")
    assert z_on_face == pytest.approx(V("sw_z"))
    assert V("sw_x") - V("dot_d") / 2 > V("pocket_x1")
    assert (V("sw_travel"), V("sw_force")) == pytest.approx((0.2, 1.6))
    assert V("flex_s1") - V("flex_s0") >= V("flex_len") and V("flex_x1") - V("flex_x0") == pytest.approx(V("flex_w"))
    assert V("sw_tip") - V("y_pad") == pytest.approx(V("flex_gap"))
    assert V("rod_d") >= V("sw_aw")
    # the stop is SW1's body, reached after flex_stop along y: past the switch's travel, a few hundredths over
    assert V("flex_stop") == pytest.approx(V("flex_gap") + V("sw_travel") + V("flex_over")) and 0 < V("flex_over") < 0.1
    dot_travel = V("flex_stop") / V("cos_t")                                     # along the face's normal, to the stop
    k = 3 * 2100 * (V("flex_w") * V("flex_t") ** 3 / 12) / V("flex_len") ** 3     # N/mm, PETG 2100 MPa
    assert k * dot_travel < 1.0                                                  # the beam's own force at the stop, under the switch's 1.6 N
    assert 3 * V("flex_t") * dot_travel / (2 * V("flex_len") ** 2) < 0.005      # strain < 0.5 %


# --- SolidCraft --------------------------------------------------------------------------

def test_build_and_bounding_box(cli):
    r = encbuild.build("airq", cli, commit=False)
    box = encbuild.union(r["bodies"].values())
    assert box["min"] == pytest.approx([-47.5, 0.0, 0.0], abs=0.01)
    assert box["max"] == pytest.approx([47.5, 55.0, 51.0], abs=0.01)
    assert not r["warnings"]


@pytest.fixture(scope="module")
def check(cli):
    return airq_check.run(cli)


def test_no_interference_with_the_references(check):
    """R9: no shared volume between the enclosure, the references (ref_main included), the
    cables' keep-outs, the air probes and the shell's sweep along -z (I1)."""
    inter = check["interference"]
    assert inter["count"] == 0, [(p["a"], p["b"], p["volume_mm3"]) for p in inter["interferences"]]
    assert not inter["unchecked"]
    names = {b["name"] for b in check["measure"]["bodies"]}
    assert {"ko_sen66_plug", "ko_strip", "ko_j2_plug", "ko_j4_plug", "ko_tongue_plug", "shell_up_32", "sweep_boss_1"} <= names
    assert inter["checked"] > 380                                    # ref_main's 308 bodies included


def test_air_paths_are_free_sections(check):
    """R25 on the geometry: each probe is free air (interference 0) and its section is at least
    the port area its path serves; the plenum's branches carry their share of the outlet grille."""
    sec = airq_check.sections(check["measure"])
    for name, (_, need, _) in airq_check.AIR.items():
        if need:
            assert sec[name] >= need, (name, sec[name])
    for name, (got, need) in airq_check.branches(S, sec).items():
        assert got >= need, (name, got, need)


def test_gaskets_touch_what_they_seal(check):
    """I3: at gasket_squeeze 0 the TPU faces touch (interference 0); at a small squeeze each
    overlaps its counterpart by its contact area times the squeeze, so there was no gap."""
    vols = airq_check.touch_volumes(check["touch"])
    q = airq_check.TOUCH_SQUEEZE
    ring = math.pi / 4 * (V("ring_od") ** 2 - V("ring_bore") ** 2) * q
    strip = V("wiper_w") * (V("zw_z0") - V("wiper_lead") - V("floor_t") - V("foam")) * q   # under the tip's lead-in
    lip = 2 * V("bp_x0") * V("ledge_t") * q
    pad = V("pad_w") * V("pad_h") * q
    top = (V("top_seal_x1") - V("top_seal_x0")) * V("sen_d") * q
    assert vols[("sen66_top_seal", "zone_wall")] == pytest.approx(top, rel=0.05)
    assert vols[("gasket_in", "base_plate")] > 0                                       # B3: the root squeezed in its slot
    assert vols[("gasket_out", "sen66_body")] == pytest.approx(ring, rel=0.05)
    assert vols[("gasket_in", "sen66_body")] == pytest.approx(strip, rel=0.05)
    assert vols[("zone_seal", "base_plate")] == pytest.approx(lip, rel=0.05)
    assert vols[("sen66_pad", "sen66_body")] == pytest.approx(pad, rel=0.05)


def test_sen66_at_its_depth_extremes(check):
    """I3(b) on the geometry: with the port face on the ring, a 21.8 module's front (plinth and
    block) meets nothing but the pad, which it squeezes to pad_t - 2 tol (67 %); a 20.8 module's
    front still meets the free pad, by pad_t - pad_gap - tol."""
    reach = airq_check.extreme_reach(check["extremes"])
    assert set(reach) == {("ext_max_plinth", "sen66_pad"), ("ext_min_plinth", "sen66_pad")}, reach
    # B2: the plug and the cable's bend, moved with a 21.8 module's connector face, were in the run
    names = [c["params"]["body_name"] for c in airq_check.extremes(S)]
    assert {"ext_max_plug", "ext_max_bend"} <= set(names)
    assert check["extremes"]["checked"] == len(names) + len(airq_check.EXTREME_PARTS)
    assert reach[("ext_max_plinth", "sen66_pad")] == pytest.approx(V("pad_t - pad_gap + sen_d_tol"), abs=0.01)
    assert reach[("ext_min_plinth", "sen66_pad")] == pytest.approx(V("pad_t - pad_gap - sen_d_tol"), abs=0.01)


def test_plugs_pass_their_openings(check):
    """Review I2 on the geometry: the Qwiic plug's section swept through the lid's hole meets
    nothing of the lid, and the open edges' ways out meet nothing of their parts."""
    plugs = check["plugs"]
    assert plugs["count"] == 0, [(p["a"], p["b"]) for p in plugs["interferences"]]
    assert plugs["checked"] == len(airq_check.PLUG_PASSES) + len(airq_check.OPEN_EDGES) + 3


def test_grommets_touch_what_they_seal(check):
    """Review N4: at squeeze 0 the grommets' faces touch their openings (interference 0); at a
    small squeeze each overlaps the part it seals, so there was no gap."""
    vols = airq_check.touch_volumes(check["touch"])
    for a, b in airq_check.TOUCHES:
        if a.startswith("grommet_"):
            assert vols[(a, b)] > 0, (a, b)


def test_shell_nudged_meets_the_base_only_on_its_datums(check):
    """Review N1: the shell nudged 0.05 each way meets the base only when pushed into a datum (back
    against the rear wall, down onto the floor), and only on that face; forward, sideways and up it
    meets nothing, so a shell or base printed up to clr_remove off size still goes together."""
    assert airq_check.nudge_faults(check["nudge"], S) == []
    met = {p["a"] if p["a"] in airq_check.NUDGES else p["b"] for p in check["nudge"]["interferences"]}
    assert met == set(airq_check.NUDGE_DATUMS)


def test_hcho_window_is_backed(check):
    """Review N2: behind every step of the HCHO window the rail and the zone wall fill the probe's
    0.5 mm slab all but the grille slot, and the shell stays clear of the opening."""
    need = airq_check.window_backing(S)
    got = airq_check.window_fill(check["window"])
    assert set(got) == set(need)
    for k, (fill, shell) in got.items():
        assert shell == 0 and fill == pytest.approx(need[k], rel=0.01), (k, fill, need[k])


def test_rebuilds_over_wall_and_clearances(cli, tmp_path):
    """check_parameters: wall 1.6 and 2.4, every clr_* +-0.1, each back to its default."""
    states = [{"wall": "1.6 mm"}, {"wall": "2.4 mm"}, {"wall": "1.8 mm"}]
    for n in ("clr_align", "clr_remove", "clr_snap"):
        d = V(n)
        states += [{n: f"{d - 0.1:.2f} mm"}, {n: f"{d + 0.1:.2f} mm"}, {n: f"{d:.2f} mm"}]
    steps = []
    for st in states:
        steps += [{"command": "parameters.change", "params": {"changes": st}},
                  {"command": "document.inspect", "params": {"measure": True, "sketches": False, "timeline": "summary"}}]
    script = tmp_path / "walk.json"
    script.write_text(json.dumps({"commands": steps}), encoding="utf-8")
    out = tmp_path / "walk.out.json"
    proc = subprocess.run([cli, "run", str(script), "--in", str(ENCLOSURE / airq.OUTPUT), "--results", "--quiet",
                           "--json-out", str(out)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    res = json.loads(out.read_text(encoding="utf-8"))
    vols = []
    for st, ins in zip(states, res[1::2]):
        bad = [f for f in ins["timeline"] if f.get("error") or f.get("warning")]
        assert not bad, (st, bad)
        assert len(ins["bodies"]) == len(BODIES), st
        vols.append(sum(b["volume_mm3"] for b in ins["bodies"]))
    assert vols[1] > vols[2] > vols[0]                              # thicker walls, more material
    assert all(math.isclose(v, vols[2], rel_tol=1e-9) for v in vols[2::3])   # each back to the default


def test_window_over_the_active_area_with_a_chamfer(check):
    """3b-1 feature 1 on the geometry: the shell is open over the whole active area, solid round
    it (the 1 mm ring's volume is exact, so the window is the active area and no larger), and the
    chamfer takes the volume of a 45-degree bevel off the outer edge; the pocket takes the panel's
    envelope plus clr_remove and the hatched block's room without touching the shell."""
    vol = airq_check.face_volumes(check["face"])
    assert ("fp_win_open", "shell") not in vol
    a, b, c, bz = V("aa_w"), V("aa_h"), V("win_chamfer"), V("bezel")
    probe = (a + 2) * (b + 2)
    assert vol[("fp_win_ring", "shell")] == pytest.approx((probe - a * b) * (bz - c - 0.05), rel=0.005)
    n = 2000                                                              # the bevel: the opening is aa + 2 (c - t) at depth t
    bevel = sum(probe - (a + 2 * (c - (i + .5) * c / n)) * (b + 2 * (c - (i + .5) * c / n)) for i in range(n)) * c / n
    assert vol[("fp_win_cham", "shell")] == pytest.approx(bevel, rel=0.005)
    assert ("fp_pocket", "shell") not in vol and ("fp_block", "shell") not in vol


def test_ffc_keepout_is_the_route_and_the_holder_flanks_the_adapter(check):
    """3b-1 feature 2 on the geometry: `ref_ffc` is one body of exactly the route's volume (12.5 x 0.3,
    four layers cut by their creases and the bend over to J7), between the adapter's mouth and J7's, and
    it is in the main interference run (0 pairs: not crushed by, and clear of, every body); the holder
    arm lies clr_remove over the adapter board's upper edge."""
    bodies = {b["name"]: b for b in check["measure"]["bodies"]}
    ffc = bodies["ref_ffc"]
    assert ffc["volume_mm3"] == pytest.approx(airq_check.ffc_volume(S), rel=2e-3)
    lo, hi = ffc["bbox"]["min"], ffc["bbox"]["max"]
    assert lo[0] == pytest.approx(V("ffc_x_m"), abs=0.01) and hi[0] == pytest.approx(V("ffc_xc") + V("ffc_w") / 2, abs=0.01)
    assert check["interference"]["count"] == 0
    vol = airq_check.face_volumes(check["face"])
    assert vol[("fp_hold", "shell")] == pytest.approx(0.05 * V("ad_l") * (V("hold_t1") - V("hold_t0")), rel=0.02)


def test_light_guide_and_crease_seal_on_the_geometry(check):
    """3b-1 feature 3 on the geometry: the light guide is one clear part from the slot's exit tongue to the
    LED faces' top edge, gd_clr in front of the LEDs, and clear of the FFC, the panel and the shell
    (interference 0 in the main run, including its raised copies along the shell's way down); the
    crease seal's foam presses the shell's lower edge by exactly its squeeze at TOUCH_SQUEEZE."""
    bodies = {b["name"]: b for b in check["measure"]["bodies"]}
    lo, hi = bodies["light_guide"]["bbox"]["min"], bodies["light_guide"]["bbox"]["max"]
    assert hi[2] == pytest.approx(V("gd_top_z"), abs=0.01) and hi[1] == pytest.approx(V("gd_y_e"), abs=0.01)
    assert lo[0] == pytest.approx(V("led_x0") + V("clr_align"), abs=0.01) and hi[0] == pytest.approx(V("gd_l2x1"), abs=0.01)
    assert lo[2] >= V("lip") + V("clr_remove") + 0.0 - 1e-6                                      # off the parting line
    assert check["interference"]["count"] == 0
    names = {b["name"] for b in check["measure"]["bodies"]}
    assert {"guide_up_1", "guide_up_32", "ref_ffc", "crease_seal"} <= names
    vols = airq_check.touch_volumes(check["touch"])
    expect = V("W") * (V("wall") - V("crease_y0")) * airq_check.TOUCH_SQUEEZE
    assert vols[("crease_seal", "shell")] == pytest.approx(expect, rel=0.08)


def test_flexure_beam_stop_and_pad_on_the_geometry(check):
    """3b-1 feature 4 on the geometry: the beam's skin is flex_t thick; the pad rod ends flex_gap short of the tip with nothing in the gap;
    the whole shell, rod and dot clear every body (interference 0), at rest."""
    vol = airq_check.face_volumes(check["face"])
    assert vol[("fp_beam", "shell")] == pytest.approx((V("flex_w") - 1.0) * 1.0 * V("flex_t"), rel=0.01)
    assert vol[("fp_pad_end", "shell")] == pytest.approx(0.1, rel=0.02)
    assert ("fp_pad_gap", "shell") not in vol
    bodies = {b["name"]: b for b in check["measure"]["bodies"]}
    d = bodies["orange_dot"]["bbox"]
    assert (d["min"][0] + d["max"][0]) / 2 == pytest.approx(V("sw_x"), abs=0.01)
    assert bodies["orange_dot"]["volume_mm3"] == pytest.approx(3.14159 / 4 * V("dot_d") ** 2 * V("dot_depth"), rel=0.03)
    assert check["interference"]["count"] == 0


# --- Task 3b-2: the base openings and the Step 4 checks -----------------------------------

def _cuts(prefix):
    return [c["params"] for c in S.commands if str(c["params"].get("name", "")).startswith(prefix)]


def _lower_edge(q):
    """z of a cut's lowest point: a box's corner, a cylinder along y's centre less its radius."""
    if "length" in q:
        return V(q["corner"][2])
    return V(q["base"][2]) - V(q["diameter"]) / 2


def test_openings_are_cut_where_the_parameters_say():
    """3b-2: each opening is a cut in base_plate at its parameters, with its lower edge on or
    above the 10 mm line; the slots' count and sizes follow their parameters."""
    cuts = {k: _cuts(k) for k in ("Intake slot", "Outlet slot", "Exhaust slot", "HCHO grille slot", "Light-sensor window", "USB-C opening")}
    assert [len(cuts[k]) for k in ("Intake slot", "Outlet slot", "Exhaust slot", "HCHO grille slot")] == \
        [2 * int(V("in_n_l") + V("in_n_r")), int(V("out_n")), int(V("exh_n")), 5]
    for k, qs in cuts.items():
        assert qs, k
        for q in qs:
            assert q["operation"] == "cut" and q["targets"] == ["base_plate"], (k, q)
            assert _lower_edge(q) >= V("grille_min_z") - 1e-9, (k, q)
    # intake: both rows end to end with slot_bar bars, between row_x0 and row_x1 round the window's gap
    for q in cuts["Intake slot"]:
        x0, x1 = V(q["corner"][0]), V(q["corner"][0]) + V(q["length"])
        assert (V("row_x0") - 1e-9 <= x0 and x1 <= V("lsw_gap_x0") + 1e-9) or (V("lsw_gap_x1") - 1e-9 <= x0 and x1 <= V("row_x1") + 1e-9)
        assert V(q["corner"][2]) in (pytest.approx(V("slot_row1_z")), pytest.approx(V("slot_row2_z")))
        assert V(q["height"]) == V("slot_w") and V(q["corner"][1]) < 0 < V("wall") < V(q["corner"][1]) + V(q["width"])   # through the lip
    assert V("slot_row2_z") + V("slot_w") <= V("ledge_z0")                              # under the zone wall's ledge
    assert V("in_len_l") > 5 and V("in_len_r") > 5
    # light-sensor window: on the tongue's VEML7700 (R27), through the lip, in the rows' gap
    q = cuts["Light-sensor window"][0]
    assert (V(q["base"][0]), V(q["base"][2]), V(q["diameter"])) == pytest.approx((V("lsw_x"), V("lsw_z"), V("lsw_d")))
    assert V("lsw_gap_x0") < V("lsw_x") - V("lsw_d") / 2 and V("lsw_x") + V("lsw_d") / 2 < V("lsw_gap_x1")
    # outlet and exhaust: whole slots in their ranges, through the rear wall, apart (R26)
    last = cuts["Outlet slot"][-1]
    assert V(last["corner"][0]) + V("slot_w") == pytest.approx(V("out_gx1"))
    assert V("exh_x0") + (V("exh_n") - 1) * V("out_pitch") + V("slot_w") <= V("exh_x1")
    assert V("out_gz1") < V("exh_z0") - 5                                              # the grilles are 9.7 apart in z, though they overlap in x
    assert V("exh_z0") >= V("zw_z1") + 2 and V("exh_z1") <= V("H") - V("wall")
    # USB-C: on J1's plug axis, the plug's overmold passes, 0.5 chamfer on the outer face
    q = cuts["USB-C opening"][0]
    assert V(q["corner"][0]) + V(q["length"]) / 2 == pytest.approx(V("usb_x"))
    assert V(q["corner"][2]) + V(q["height"]) / 2 == pytest.approx(V("usb_z"))
    assert V("usb_open_w") >= V("usb_plug_w") and V("usb_open_h") >= V("usb_plug_h") and V("usb_open_w") > V("usb_sw")
    assert V(q["corner"][2]) >= V("zw_z1") - 2 * V("clr_remove")                          # at most the zone wall's slit lower
    ch = _feature("USB-C chamfer")
    assert V(ch["distance"]) == 0.5 and len(ch["edges"]) == 4 and all(abs(e[1] - V("D")) < 1e-6 for e in ch["edges"])
    # the openings in the rear wall keep apart, and the intake and outlet face opposite ways
    assert V("exh_x0") - (V("usb_x") + V("usb_open_w") / 2) >= 1.2
    assert max(V(q["corner"][1]) for q in cuts["Intake slot"]) < V("D") / 2 < min(V(q["corner"][1]) for q in cuts["Outlet slot"] + cuts["Exhaust slot"])


def test_openings_measured_open_areas(check):
    """R18 on the geometry: each opening's open area is its probe's volume less the base's
    overlap, over the wall's thickness; it equals the parameters' area and meets 2 x its port."""
    areas = airq_check.opening_areas(S, check["openings"])
    for name, (got, want) in areas.items():
        assert got == pytest.approx(want, rel=2e-3), name
    intake = areas["op_intake_l"][0] + areas["op_intake_r"][0]
    hcho = sum(a[0] for n, a in areas.items() if n.startswith("op_hcho_"))
    sfa = ref_sfa40.build().v
    assert intake >= 154.5 and areas["op_outlet"][0] >= 660.1                                    # 2 x 77.3, 2 x 330.1
    assert hcho >= 2 * sfa("opening_l") * sfa("opening_w")                                       # 2 x the SFA40's opening
    assert areas["op_exhaust"][0] > 100 and areas["op_lsw"][0] == pytest.approx(math.pi / 4 * V("lsw_d") ** 2, rel=2e-3)


def test_nothing_opens_below_the_10_mm_line(check):
    """Every opening's lower edge is at least 10 above z = 0 (no feet): a slab from z 0 to the
    line over the lip, the rear wall, the rail and the shell's right wall is all material."""
    got = {}
    for p in check["openings"]["interferences"]:
        n, other = (p["a"], p["b"]) if p["a"].startswith("low_") else (p["b"], p["a"])
        if n.startswith("low_"):
            got[(n, other)] = got.get((n, other), 0.0) + p["volume_mm3"]
    for c in airq_check.low_probes(S):
        n = c["params"]["body_name"]
        assert got[(n, airq_check.LOW_PARTS[n])] == pytest.approx(airq_check._volume(c, S), rel=1e-6), n


def test_usb_opening_fit_and_chamfer(check):
    """The USB-C opening within 0.05 of J1's axis and the overmold's size, with the 0.5 chamfer:
    the probe 0.05 under the opening meets nothing, the one 0.05 over meets the wall's ring, and
    over the chamfer's depth the wall keeps the box less the chamfer's frustum."""
    got = {}
    for p in check["openings"]["interferences"]:
        n = p["a"] if p["a"].startswith("usb_") else p["b"]
        if n.startswith("usb_"):
            got[n] = got.get(n, 0.0) + p["volume_mm3"]
    want = airq_check.usb_expect(S)
    assert got.get("usb_in", 0.0) == 0.0
    assert got["usb_out"] == pytest.approx(want["usb_out"], rel=0.01)
    assert got["usb_cham"] == pytest.approx(want["usb_cham"], rel=0.01)


def test_the_air_in_front_of_every_opening_is_free(check):
    """The intake slots, the light-sensor window, the outlet and exhaust grilles and J1's plug axis
    face free air: their probes meet no reference (interference 0), and the tongue stays 4.5 behind the slots."""
    names = {b["name"] for b in check["measure"]["bodies"]}
    assert set(airq_check.OPENING_AIR) <= names
    assert check["interference"]["count"] == 0
    assert V("tongue_y0") - V("wall") >= 4.5


def test_distances_on_the_geometry(check):
    """R12 and the tongue's distances as exact distances between solids (`inspect.clearance`):
    never under the arithmetic of `distances()` (its boxes enclose), and over the rules."""
    d, c = airq_check.distances(S), check["clearance"]
    assert c["antenna_to_sen66"] >= d["antenna_to_sen66"] - 1e-3 and c["antenna_to_sen66"] >= 15
    assert c["antenna_to_usb_plug"] == pytest.approx(d["antenna_to_usb_plug"], abs=0.01) and c["antenna_to_usb_plug"] >= 15
    assert c["antenna_to_inserts"] == pytest.approx(d["antenna_to_bosses_and_screws"], abs=0.01) and c["antenna_to_inserts"] >= 15
    assert c["antenna_to_screws"] >= 15
    assert c["tongue_to_u3"] == pytest.approx(d["tongue_to_u3"], abs=0.01) and c["tongue_to_u3"] >= 20
    assert c["tongue_to_u2"] == pytest.approx(d["tongue_to_u2"], abs=0.01) and c["tongue_to_u2"] >= 20
    assert c["intake_to_outlet"] == pytest.approx(V("D") - 2 * V("wall"), abs=1e-3) and c["intake_to_outlet"] >= 20   # inner face to inner face


def test_shell_openings_are_above_the_10_mm_line():
    """Review M3: the shell's own openings (screen window, LED slot, flexure U-slot) are well over the 10 mm line (their
    lowest edge at the face's inner side), arithmetic from the parameters."""
    z = lambda sv, t=0.0: V("lip") + V(sv) * V("cos_t") - t * V("sin_t")   # noqa: E731
    for name, zz in (("screen window", z("win_s0")), ("LED slot", z("led_s0", V("wall"))), ("flexure U-slot", z("flex_s0", V("wall")))):
        assert zz >= V("grille_min_z"), (name, zz)
