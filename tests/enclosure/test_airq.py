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
          *GROMMETS]
TPU = ["gasket_out", "gasket_in", *GROMMETS]
# positions Task 3b needs (task-3-scope, M6), fixed here as parameters
FACE = ["panel_x0", "panel_s0", "bezel", "window_xc", "pocket_x0", "pocket_x1", "led_f0", "led_h_slot", "led_len", "led_z",
        "guide_t", "adapter_x", "adapter_s", "adapter_t", "ffc_len", "j7_x0", "j7_x1", "sw_x", "sw_z", "dot_f", "dot_d",
        "lsw_x", "lsw_z", "lsw_d", "slot_row1_z", "slot_row2_z", "row_x0", "row_x1", "lsw_gap_x0", "lsw_gap_x1",
        "out_gx0", "out_gx1", "out_gz0", "out_gz1", "out_pitch", "out_n", "exh_x0", "exh_x1", "exh_z0", "exh_z1",
        "usb_x", "usb_z", "usb_well", "usb_chamfer"]


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
