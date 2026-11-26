"""coupons: the print-test coupons the owner prints before any enclosure (Plan 3 Task 2).

Their results set the clearance defaults the two enclosures use (`clr_*`, `slot_w`, `flex_*`).
One design, one body per coupon piece, laid out flat on the bed (z = 0 is the print bed, every
coupon prints without supports in the orientation given here):

  coupon_clr_pegs / coupon_clr_holes   Round pegs / holes and rectangular tabs / slots at the five
                                       clearances. Hole = peg + 2 * clr (clr is a per-side gap, R20).
  coupon_grille                        Slots 1.0 / 1.2 / 1.5 mm and 45-degree louvres through a wall
                                       thick plate. Prints face down (the plate's flat face on the bed).
  coupon_insert                        Three M2 heat-set insert holes (3.1 / 3.2 / 3.3 mm, 4.0 deep) in
                                       6.0 mm bosses. Sizes to confirm against the owner's inserts.
  coupon_flexure                       Two side-push button flexures against a stand-in for SW1 (Alps
                                       SKRTLAE010) at a board's front edge: A has the actuator stub, B
                                       has none so it can be pushed to its hard stop.
  coupon_lg_body, coupon_lg_bar_lit,   A 3 x 2 mm clear light-guide bar in an opaque body with an
  coupon_lg_bar_dark,                  SK6812SIDE pocket, with an unlit bar behind a 1.2 mm divider on one
  coupon_lg_bar_dark_2                 side and another behind a 2.0 mm divider on the other, to judge
                                       leakage. Body in the shell material, bars clear.

Every feature that stands for a tested value carries the value as a debossed label that follows
its parameter (`sketch.text` with a text expression). Sources: the plan (Task 2), ruling R20
(enclosure/README "Printing the coupons"), `hardware/interface.yaml` `mechanical.main.button`.
"""
from __future__ import annotations

import clearances
from sclib import Script, mechanical

DESIGN = "coupons"
OUTPUT = "coupons.sc"
# Printable exports of this design (Task 5 reuses this: list the files, `encbuild.build` writes them)
EXPORTS = ["export/coupons.3mf", "export/coupons.step"]

CLR = [1, 2, 3, 4, 5]               # the five clearance steps clr_t1 .. clr_t5
BODIES = ["coupon_clr_pegs", "coupon_clr_holes", "coupon_grille", "coupon_insert",
          "coupon_flexure", "coupon_lg_body", "coupon_lg_bar_lit", "coupon_lg_bar_dark", "coupon_lg_bar_dark_2"]


def at(origin, expr):
    """`origin + (expr)`, an origin of 0 vanishing."""
    return expr if origin == 0 else f"{origin} + ({expr})"


def span(xs, s, lo, hi):
    """Corner and length of an x range [lo, hi] measured from `xs` in the beam direction `s`
    (+1: toward +x, -1: toward -x); lo and hi are expressions."""
    corner = f"{xs} + ({lo})" if s > 0 else f"{xs} - ({hi})"
    return corner, f"({hi}) - ({lo})"


def build() -> Script:
    s = Script(DESIGN)
    p = s.param
    btn = mechanical("main")["button"]
    board = mechanical("main")

    # --- the fits under test ---------------------------------------------------------------
    clearances.add_params(s)       # clr_align, clr_remove, clr_snap, slot_w, wall, flex_t, flex_len, flex_gap
    for i, v in zip(CLR, (0.10, 0.15, 0.20, 0.25, 0.30)):
        p(f"clr_t{i}", v, f"tested per-side clearance {i} of 5 (R20: hole = peg + 2 x clr); labelled on the coupon")
    p("slot_w_narrow", 1.0, "tested grille slot width, narrower than slot_w (R20)")
    p("slot_w_wide", 1.5, "tested grille slot width, wider than slot_w (R20)")

    # --- layout and shared sizes ------------------------------------------------------------
    p("bed_gap", 6.0, "gap between coupons on the bed (model only)")
    p("cut_over", 0.5, "cutting tools start this far outside a face so cuts are clean (model only)")
    p("text_h", 5.0, "capital height of the debossed labels: the built-in font's strokes are about 0.09 x this, 0.45 mm, above a 0.4 mm nozzle (model only)")
    p("text_depth", 0.4, "label deboss depth (the plan's debossed lettering is 0.4 mm deep)")

    # --- fit coupon: round peg / hole and rectangular tab / slot ----------------------------
    p("fit_t", 3.0, "plate thickness of the peg and hole plates (model only)")
    p("fit_pitch", 14.0, "pitch between the five fits (model only)")
    p("fit_margin", 3.0, "plate margin beyond the outer fits, plus half a pitch (model only)")
    p("fit_w", "5 * fit_pitch + 2 * fit_margin", "plate width: five fits in a row")
    p("fit_lbl_y", 2.0, "label baseline above the plate's front edge (model only)")
    p("fit_round_y", 12.0, "row of round pegs and holes (model only)")
    p("fit_rect_y", 22.0, "row of rectangular tabs and slots (model only)")
    p("fit_d", 28.0, "plate depth (model only)")
    p("peg_d", 6.0, "round peg diameter (model only; a locating pin on the enclosure is about 3 to 6 mm)")
    p("peg_h", 5.0, "round peg height above the plate (model only)")
    p("tab_w", 8.0, "rectangular tab width (model only)")
    p("tab_t", 2.0, "rectangular tab thickness: the light guide's and the panel's thickness class (model only)")
    p("tab_h", 5.0, "rectangular tab height above the plate (model only)")

    # --- grille coupon -----------------------------------------------------------------------
    p("gr_col", 14.0, "width of one column of three slots (model only)")
    p("gr_w", "3 * gr_col", "plate width: three columns, one per slot width")
    p("gr_d", 44.0, "plate depth (model only)")
    p("slot_pitch", 3.0, "pitch of the three straight slots in a column (model only)")
    p("louvre_pitch", 4.0, "pitch of the three louvre slots in a column: wider, so the slats between stay at least 1.3 mm thick (model only)")
    p("slot_len", 10.0, "slot length (model only)")
    p("gr_row_s", 9.0, "front edge of the straight slots (model only)")
    p("gr_row_l", 24.0, "front edge of the louvre slots (model only)")
    p("gr_lbl_lo", 2.0, "baseline of the straight slots' labels (model only)")
    p("gr_lbl_hi", 37.0, "baseline of the louvre slots' labels, which start with L (model only)")

    # --- insert boss coupon ------------------------------------------------------------------
    p("insert_od", 6.0, "boss outer diameter (R20)")
    p("insert_depth", 4.0, "insert hole depth (R20)")
    p("insert_hole_a", 3.1, "M2 heat-set insert hole, trial 1: TO CONFIRM against the owner's inserts (R20)")
    p("insert_hole_b", 3.2, "M2 heat-set insert hole, trial 2: TO CONFIRM against the owner's inserts (R20)")
    p("insert_hole_c", 3.3, "M2 heat-set insert hole, trial 3: TO CONFIRM against the owner's inserts (R20)")
    p("insert_h", 5.0, "boss height above the plate, leaving 1 mm of floor under the hole (model only)")
    p("ib_t", 2.0, "plate thickness: the plan's 2.0 mm floor")
    p("ib_pitch", 10.0, "boss pitch (model only)")
    p("ib_w", "3 * ib_pitch", "plate width: three bosses")
    p("ib_d", 17.0, "plate depth (model only)")
    p("ib_y", 11.0, "boss centre from the plate's front edge (model only)")
    p("ib_lbl_y", 2.0, "label baseline (model only)")

    # label numbers (unitless): the debossed labels show these, so a label follows its value
    for i in CLR:
        p(f"lbl_clr{i}", f"clr_t{i} / 1 mm * 100", f"label of clr_t{i}: the clearance in hundredths of a mm (0.15 mm reads 15)", unit="")
    for w in ("slot_w_narrow", "slot_w", "slot_w_wide", "insert_hole_a", "insert_hole_b", "insert_hole_c"):
        p(f"lbl_{w}", f"{w} / 1 mm * 10", f"label of {w}: the size in tenths of a mm (1.2 mm reads 12, 3.1 mm reads 31)", unit="")

    # --- button flexure coupon ---------------------------------------------------------------
    p("board_t", board["thickness"], "PCB thickness, interface.yaml mechanical.main.thickness: the stand-in's board stub")
    p("sw_w", 4.5, "SW1 body width along the board edge, interface.yaml mechanical.main.button comment (Alps drawing)")
    p("sw_d", 3.4, "SW1 body depth into the board, interface.yaml mechanical.main.button comment (Alps drawing)")
    p("sw_h", 3.3, "SW1 body height above the board, interface.yaml mechanical.main.button comment (Alps drawing)")
    p("sw_act_w", btn["actuator_width"], "SW1 actuator width, interface.yaml mechanical.main.button.actuator_width")
    p("sw_act_z", btn["actuator_center_z"], "SW1 actuator centre above the board top, interface.yaml mechanical.main.button.actuator_center_z")
    p("sw_act_h", 1.0, "SW1 actuator height: stand-in only, TO CONFIRM from the Alps drawing")
    p("sw_tip", round(btn["actuator_tip_y"] - board["outline"][1], 4),
      "actuator tip beyond the board's front edge at rest, interface.yaml mechanical.main.button.actuator_tip_y minus the outline's front edge (0.24 mm)")
    p("sw_travel", 0.20, "SW1 actuator travel, interface.yaml mechanical.main.button comment (0.2 mm; 1.6 N operating force)")
    p("flex_stop", "flex_gap + sw_travel", "pad travel to the hard stop: it ends where the actuator is fully pressed, so the switch is never over-pressed")
    p("flex_h", "board_t + sw_h", "flexure height: pad, beam, anchor and stop stand from the bed to the top of the switch body")
    p("flex_y0", "sw_tip + flex_gap", "pad inner face from the board edge at rest")
    p("flex_pad_d", 2.0, "pad depth, front to back (model only)")
    p("flex_pad_lug", 5.0, "pad extent from the actuator axis toward the stop side: carries the stop lug (model only)")
    p("flex_pad_beam", 2.0, "pad extent from the actuator axis toward the beam (model only)")
    p("flex_stop_w", 2.0, "width of the stop block under the pad's lug (model only)")
    p("flex_stop_y", "flex_y0 - flex_stop", "stop face from the board edge: the pad's inner face reaches it after flex_stop")
    p("flex_anchor_w", 4.0, "width of the anchor block both beams spring from (model only)")
    p("flex_anchor_front", 1.0, "anchor block extent beyond the beams' outer face (model only)")
    p("flex_plate_d", 10.0, "board stub depth behind its front edge (model only)")
    p("flex_margin", 1.0, "board stub margin beyond the pad and its lug (model only)")

    # --- light-guide coupon ------------------------------------------------------------------
    p("lg_bar_w", 3.0, "clear light-guide bar width (plan: 3 x 2 mm bar)")
    p("lg_bar_h", 2.0, "clear light-guide bar height (plan: 3 x 2 mm bar)")
    p("lg_bar_len", 16.0, "clear light-guide bar length (model only)")
    p("lg_led_w", 4.0, "SK6812SIDE body and light face width, R20 / interface.yaml mechanical.main.leds (4.0 x 2.0 face)")
    p("lg_led_d", 1.6, "SK6812SIDE body depth from its light face, R20 (body 4.0 x 1.6 x 2.0)")
    p("lg_led_h", 2.0, "SK6812SIDE body and light face height, R20")
    p("divider_thick", 2.0, "second, thicker opaque divider (the other side of the LED pocket): if 1.2 mm leaks, this tells how much wall stops it")
    p("divider", 1.2, "opaque divider and wall thickness, at least 1.2 mm (plan: opaque wall between a light guide and anything it must not light)")
    p("lg_floor", 1.2, "opaque floor under the pocket and the slots (model only)")
    p("lg_pocket_w", "lg_led_w + 2 * clr_align", "LED pocket width: the LED plus the aligned clearance per side")
    p("lg_pocket_d", "lg_led_d + 2 * clr_align", "LED pocket depth: the LED plus the aligned clearance per side")
    p("lg_slot_w", "lg_bar_w + 2 * clr_align", "bar slot width: the bar plus the aligned clearance per side")
    p("lg_l", "divider + lg_pocket_d + lg_bar_len", "opaque body length")
    p("lg_pocket_y", "divider + lg_slot_w + divider_thick", "LED pocket front edge from the body front: outer wall, thick-divider dark slot, thick divider")
    p("lg_w", "lg_pocket_y + lg_pocket_w + divider + lg_slot_w + divider", "opaque body width: outer wall, dark slot, thick divider, pocket, thin divider, dark slot, outer wall")
    p("lg_h", "lg_floor + lg_led_h", "opaque body height")

    # --- placement on the bed (model only) --------------------------------------------------
    p("lay_holes_y", "fit_d + bed_gap", "hole plate, behind the peg plate")
    p("lay_col2_x", "fit_w + bed_gap", "second column: grille, insert and light-guide coupons")
    p("lay_insert_y", "gr_d + bed_gap", "insert coupon, behind the grille coupon")
    p("lay_lg_y", "lay_insert_y + ib_d + bed_gap", "light-guide body, behind the insert coupon")
    p("lay_lgbar_y", "lay_lg_y + lg_w + bed_gap", "first clear bar, behind the light-guide body")
    p("lay_flex_x", "flex_pad_lug + flex_margin", "flexure coupon: actuator axis of stand-in A")
    p("lay_flex_y", "2 * fit_d + 2 * bed_gap + flex_plate_d", "flexure coupon: board front edge")

    fit_coupons(s)
    grille_coupon(s)
    insert_coupon(s)
    flexure_coupon(s)
    light_guide_coupon(s)
    assert s.bodies == BODIES, s.bodies
    return s


def deboss(s: Script, name: str, plane_offset: str, body: str, labels):
    """A label sketch on the top face at `plane_offset` and the 0.4 mm cut into `body`.
    labels: [(content, expression?, (x, y))]."""
    with s.sketch(f"{name} sketch", "XY", offset=plane_offset) as sk:
        for content, expr, pos in labels:
            sk.text(content, pos, "text_h", expression=expr)
    s.extrude(name, f"{name} sketch", "text_depth", operation="cut", targets=[body], direction="negative")


def fit_coupons(s: Script):
    """Peg plate and hole plate: five round and five rectangular fits at clr_t1 .. clr_t5."""
    pegs, holes = "coupon_clr_pegs", "coupon_clr_holes"
    cx = lambda i: f"fit_margin + fit_pitch * {i - 0.5}"
    s.box("Peg plate", [0, 0, 0], ["fit_w", "fit_d", "fit_t"], body=pegs)
    oy = "lay_holes_y"
    s.box("Hole plate", [0, oy, 0], ["fit_w", "fit_d", "fit_t"], body=holes)
    for i in CLR:
        s.cylinder(f"Peg {i}", [cx(i), "fit_round_y", "fit_t"], "peg_d", "peg_h",
                   operation="join", targets=[pegs])
        s.box(f"Tab {i}", [f"{cx(i)} - tab_w / 2", "fit_rect_y - tab_t / 2", "fit_t"],
              ["tab_w", "tab_t", "tab_h"], operation="join", targets=[pegs])
        c = f"clr_t{i}"
        s.cylinder(f"Round hole {i}", [cx(i), at(oy, "fit_round_y"), "-cut_over"],
                   f"peg_d + 2 * {c}", "fit_t + 2 * cut_over", operation="cut", targets=[holes])
        s.box(f"Tab slot {i}", [f"{cx(i)} - (tab_w + 2 * {c}) / 2", at(oy, f"fit_rect_y - (tab_t + 2 * {c}) / 2"),
                                "-cut_over"],
              [f"tab_w + 2 * {c}", f"tab_t + 2 * {c}", "fit_t + 2 * cut_over"],
              operation="cut", targets=[holes])
    deboss(s, "Peg labels", "fit_t", pegs,
           [(f"number(lbl_clr{i}, 0)", True, (cx(i), "fit_lbl_y")) for i in CLR])
    deboss(s, "Hole labels", "fit_t", holes,
           [(f"number(lbl_clr{i}, 0)", True, (cx(i), at(oy, "fit_lbl_y"))) for i in CLR])


def grille_coupon(s: Script):
    """Three columns (slot_w_narrow, slot_w, slot_w_wide) of three slots each: straight slots
    in the front row, 45-degree louvres in the back row. The plate prints face down."""
    body, ox = "coupon_grille", "lay_col2_x"
    widths = ["slot_w_narrow", "slot_w", "slot_w_wide"]
    xc = lambda j: f"{ox} + gr_col * {j + 0.5}"
    s.box("Grille plate", [ox, 0, 0], ["gr_w", "gr_d", "wall"], body=body)
    with s.sketch("Straight slots sketch", "XY", offset="-cut_over") as sk:
        for j, w in enumerate(widths):
            for k in (-1, 0, 1):
                cx = f"{xc(j)} + slot_pitch * ({k})"
                sk.rect(f"{cx} - {w} / 2", "gr_row_s", f"{cx} + {w} / 2", "gr_row_s + slot_len")
    s.extrude("Straight slots", "Straight slots sketch", "wall + 2 * cut_over", operation="cut", targets=[body])
    # Louvres: a parallelogram section in the XZ plane (sketch y = -z), 45 degrees: the slot
    # shifts sideways by `wall` through the plate. The width is measured square to the slats,
    # so the slot is w * sqrt(2) wide on the face. Extruded along +y for slot_len.
    with s.sketch("Louvre slots sketch", "XZ", offset="gr_row_l") as sk:
        for j, w in enumerate(widths):
            wh = f"{w} * sqrt(2)"
            for k in (-1, 0, 1):
                xl = f"{xc(j)} + louvre_pitch * ({k}) - wall / 2 - {wh} / 2"
                sk.polyline([(f"{xl} - cut_over", "cut_over"),
                             (f"{xl} - cut_over + {wh}", "cut_over"),
                             (f"{xl} + wall + cut_over + {wh}", "-(wall + cut_over)"),
                             (f"{xl} + wall + cut_over", "-(wall + cut_over)")])
    s.extrude("Louvre slots", "Louvre slots sketch", "slot_len", operation="cut", targets=[body])
    deboss(s, "Grille labels", "wall", body,
           [(f"number(lbl_{w}, 0)", True, (xc(j), "gr_lbl_lo")) for j, w in enumerate(widths)]
           + [(f"'L' + number(lbl_{w}, 0)", True, (xc(j), "gr_lbl_hi")) for j, w in enumerate(widths)])


def insert_coupon(s: Script):
    """Three bosses on a plate, each with a blind M2 insert hole of a different diameter."""
    body, ox, oy = "coupon_insert", "lay_col2_x", "lay_insert_y"
    holes = ["insert_hole_a", "insert_hole_b", "insert_hole_c"]
    xc = lambda j: at(ox, f"ib_pitch * {j + 0.5}")
    s.box("Insert plate", [ox, oy, 0], ["ib_w", "ib_d", "ib_t"], body=body)
    for j, h in enumerate(holes):
        s.cylinder(f"Boss {j + 1}", [xc(j), at(oy, "ib_y"), "ib_t"], "insert_od", "insert_h",
                   operation="join", targets=[body])
    for j, h in enumerate(holes):
        s.cylinder(f"Insert hole {j + 1}", [xc(j), at(oy, "ib_y"), "ib_t + insert_h - insert_depth"],
                   h, "insert_depth + cut_over", operation="cut", targets=[body])
    deboss(s, "Insert labels", "ib_t", body,
           [(f"number(lbl_{h}, 0)", True, (xc(j), at(oy, "ib_lbl_y"))) for j, h in enumerate(holes)])


def flexure_coupon(s: Script):
    """A board stub with a stand-in for SW1 at its front edge (stand-in A has the actuator stub,
    B none), and in front of each a pad on a flexure beam with a hard stop. Everything
    stands on the bed. Beams spring from a shared anchor block between the two units."""
    body = "coupon_flexure"
    ox, oy = "lay_flex_x", "lay_flex_y"
    unit = "2 * (flex_pad_beam + flex_len) + flex_anchor_w"          # x of unit B's axis from A's
    xs_a, xs_b = ox, at(ox, unit)
    s.box("Board stub", [at(ox, "-flex_pad_lug - flex_margin"), at(oy, "-flex_plate_d"), 0],
          [f"{unit} + 2 * (flex_pad_lug + flex_margin)", "flex_plate_d", "board_t"], body=body)
    s.box("Anchor", [at(ox, "flex_pad_beam + flex_len"), at(oy, "-flex_plate_d"), 0],
          ["flex_anchor_w", "flex_plate_d + flex_y0 + flex_pad_d + flex_anchor_front", "flex_h"],
          operation="join", targets=[body])
    for tag, xs, sgn, stub in (("A", xs_a, 1, True), ("B", xs_b, -1, False)):
        c, n = span(xs, sgn, "-sw_w / 2", "sw_w / 2")
        s.box(f"Stand-in {tag}", [c, at(oy, "-sw_d"), "board_t"], [n, "sw_d", "sw_h"],
              operation="join", targets=[body])
        if stub:
            c, n = span(xs, sgn, "-sw_act_w / 2", "sw_act_w / 2")
            s.box(f"Actuator stub {tag}", [c, oy, "board_t + sw_act_z - sw_act_h / 2"],
                  [n, "sw_tip", "sw_act_h"], operation="join", targets=[body])
        c, n = span(xs, sgn, "-flex_pad_lug", "-flex_pad_lug + flex_stop_w")
        s.box(f"Stop {tag}", [c, at(oy, "-flex_plate_d"), 0], [n, "flex_plate_d + flex_stop_y", "flex_h"],
              operation="join", targets=[body])
        c, n = span(xs, sgn, "flex_pad_beam", "flex_pad_beam + flex_len")
        s.box(f"Beam {tag}", [c, at(oy, "flex_y0 + flex_pad_d - flex_t"), 0], [n, "flex_t", "flex_h"],
              operation="join", targets=[body])
        c, n = span(xs, sgn, "-flex_pad_lug", "flex_pad_beam")
        s.box(f"Pad {tag}", [c, at(oy, "flex_y0"), 0], [n, "flex_pad_d", "flex_h"],
              operation="join", targets=[body])
    deboss(s, "Flexure", "board_t", body,
           [("A", False, (xs_a, at(oy, "-flex_plate_d + 1"))), ("B", False, (xs_b, at(oy, "-flex_plate_d + 1")))])


def light_guide_coupon(s: Script):
    """Opaque body with an LED pocket and two parallel slots (the lit one and, past the divider,
    a dark one), and two clear bars lying beside it as they print."""
    body, ox, oy = "coupon_lg_body", "lay_col2_x", "lay_lg_y"
    s.box("Light-guide body", [ox, oy, 0], ["lg_l", "lg_w", "lg_h"], body=body)
    s.box("LED pocket", [at(ox, "divider"), at(oy, "lg_pocket_y"), "lg_floor"],
          ["lg_pocket_d", "lg_pocket_w", "lg_led_h + cut_over"], operation="cut", targets=[body])
    s.box("Lit slot", [at(ox, "divider + lg_pocket_d"), at(oy, "lg_pocket_y + lg_pocket_w / 2 - lg_slot_w / 2"), "lg_floor"],
          ["lg_bar_len + cut_over", "lg_slot_w", "lg_bar_h + cut_over"], operation="cut", targets=[body])
    s.box("Dark slot", [at(ox, "divider + lg_pocket_d"), at(oy, "lg_pocket_y + lg_pocket_w + divider"), "lg_floor"],
          ["lg_bar_len + cut_over", "lg_slot_w", "lg_bar_h + cut_over"], operation="cut", targets=[body])
    s.box("Dark slot thick divider", [at(ox, "divider + lg_pocket_d"), at(oy, "divider"), "lg_floor"],
          ["lg_bar_len + cut_over", "lg_slot_w", "lg_bar_h + cut_over"], operation="cut", targets=[body])
    s.box("Lit bar", [ox, "lay_lgbar_y", 0], ["lg_bar_len", "lg_bar_w", "lg_bar_h"], body="coupon_lg_bar_lit")
    s.box("Dark bar", [ox, "lay_lgbar_y + lg_bar_w + bed_gap", 0], ["lg_bar_len", "lg_bar_w", "lg_bar_h"],
          body="coupon_lg_bar_dark")
    s.box("Dark bar thick divider", [ox, "lay_lgbar_y + 2 * (lg_bar_w + bed_gap)", 0],
          ["lg_bar_len", "lg_bar_w", "lg_bar_h"], body="coupon_lg_bar_dark_2")


def expected_bboxes(s: Script | None = None) -> dict[str, tuple]:
    """Each body's bounding box ((min), (max)) from the parameters, written out independently of
    the features (the tests compare the built design with these)."""
    s = s or build()
    v = s.v
    px = v("lay_col2_x")
    unit = 2 * (v("flex_pad_beam") + v("flex_len")) + v("flex_anchor_w")
    fx0 = v("lay_flex_x") - v("flex_pad_lug") - v("flex_margin")
    fy1 = v("lay_flex_y") + v("flex_y0") + v("flex_pad_d") + v("flex_anchor_front")
    peg_top = v("fit_t") + max(v("peg_h"), v("tab_h"))
    lgy = v("lay_lgbar_y")
    return {
        "coupon_clr_pegs": ((0, 0, 0), (v("fit_w"), v("fit_d"), peg_top)),
        "coupon_clr_holes": ((0, v("lay_holes_y"), 0), (v("fit_w"), v("lay_holes_y") + v("fit_d"), v("fit_t"))),
        "coupon_grille": ((px, 0, 0), (px + v("gr_w"), v("gr_d"), v("wall"))),
        "coupon_insert": ((px, v("lay_insert_y"), 0), (px + v("ib_w"), v("lay_insert_y") + v("ib_d"),
                                                        v("ib_t") + v("insert_h"))),
        "coupon_flexure": ((fx0, v("lay_flex_y") - v("flex_plate_d"), 0),
                           (fx0 + unit + 2 * (v("flex_pad_lug") + v("flex_margin")), fy1, v("flex_h"))),
        "coupon_lg_body": ((px, v("lay_lg_y"), 0), (px + v("lg_l"), v("lay_lg_y") + v("lg_w"), v("lg_h"))),
        "coupon_lg_bar_lit": ((px, lgy, 0), (px + v("lg_bar_len"), lgy + v("lg_bar_w"), v("lg_bar_h"))),
        "coupon_lg_bar_dark": ((px, lgy + v("lg_bar_w") + v("bed_gap"), 0),
                               (px + v("lg_bar_len"), lgy + 2 * v("lg_bar_w") + v("bed_gap"), v("lg_bar_h"))),
        "coupon_lg_bar_dark_2": ((px, lgy + 2 * (v("lg_bar_w") + v("bed_gap")), 0),
                                 (px + v("lg_bar_len"), lgy + 3 * v("lg_bar_w") + 2 * v("bed_gap"), v("lg_bar_h"))),
    }
