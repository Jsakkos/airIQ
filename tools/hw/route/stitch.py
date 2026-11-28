"""Main board, routing step 3 (with main_pour.py): find ground stitching-via positions. Runs in KiCad's
bundled Python (it uses pcbnew's shapes for the clearance checks). Prints x,y pairs (mm from the board's
top-left corner) for main_pour.py.

    <KiCad python> -I tools/hw/route/stitch.py BOARD PITCH SPACING            # grid pass
    <KiCad python> -I tools/hw/route/stitch.py BOARD PITCH SPACING islands    # one via per unstitched fill

Grid pass: candidates on a PITCH grid; a candidate is kept when a 0.6 mm via there is >= 0.25 mm from
every non-GND copper item and from GND pads (no via in pad), its hole >= 0.35 mm from pad holes, inside
both GND pour outlines, outside rule areas that ban vias, and outside footprint courtyards (except U3's:
the module's underside is ground). Kept vias are >= SPACING apart and from existing GND vias.
Islands pass (on a filled board): one candidate in every GND fill polygon that holds no GND via yet.

Hard-codes the main board's extent (60 x 30 mm) and U3 as the one courtyard to stitch under.
Not part of the build.
"""
import sys

import pcbnew

OX, OY = 100.0, 100.0
CLEAR = 0.25
MM = pcbnew.FromMM


def main(argv: list[str]) -> int:
    board = pcbnew.LoadBoard(argv[0])
    pitch, spacing = float(argv[1]), float(argv[2])
    islands = len(argv) > 3 and argv[3] == "islands"
    gnd_zones = [z for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetname() == "GND"]
    rule_areas = [z for z in board.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    items = [p for fp in board.GetFootprints() for p in fp.Pads()] + list(board.GetTracks())
    courtyards = []
    for fp in board.GetFootprints():
        if fp.GetReference() == "U3":
            continue
        poly = fp.GetCourtyard(pcbnew.F_CrtYd)
        if poly.OutlineCount():
            courtyards.append(poly)

    def ok(x: float, y: float) -> bool:
        pos = pcbnew.VECTOR2I(MM(OX + x), MM(OY + y))
        via_shape = pcbnew.SHAPE_CIRCLE(pos, MM(0.3))
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            if not any(z.IsOnLayer(layer) and z.Outline().Contains(pos) for z in gnd_zones):
                return False
        for z in rule_areas:
            if z.Outline().Contains(pos) or z.Outline().Collide(pos, MM(0.3)):
                return False
        for c in courtyards:
            if c.Contains(pos) or c.Collide(pos, MM(0.3)):
                return False
        for it in items:
            gnd = it.GetNetname() == "GND"
            if gnd and it.GetClass() != "PAD":
                continue
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                if it.IsOnLayer(layer) and it.GetEffectiveShape(layer).Collide(via_shape, MM(CLEAR)):
                    return False
            if it.GetClass() == "PAD" and it.GetDrillSizeX() > 0:
                if it.GetEffectiveHoleShape().Collide(via_shape, MM(0.35)):
                    return False
        return True

    cands = []
    y = 1.05
    while y <= 29.2:
        x = 0.8
        while x <= 59.2:
            if ok(x, y):
                cands.append((round(x, 2), round(y, 2)))
            x += pitch
        y += pitch

    if islands:
        gvias = [t.GetPosition() for t in board.GetTracks()
                 if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"]
        extra = []
        for z in gnd_zones:
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                if not (z.IsOnLayer(layer) and z.HasFilledPolysForLayer(layer)):
                    continue
                fills = z.GetFilledPolysList(layer)
                for i in range(fills.OutlineCount()):
                    one = pcbnew.SHAPE_POLY_SET()
                    one.AddOutline(fills.Outline(i))
                    if any(one.Contains(p) for p in gvias):
                        continue
                    pts = [c for c in cands if one.Contains(pcbnew.VECTOR2I(MM(OX + c[0]), MM(OY + c[1])))]
                    if pts:
                        pick = pts[len(pts) // 2]
                        extra.append(pick)
                        gvias.append(pcbnew.VECTOR2I(MM(OX + pick[0]), MM(OY + pick[1])))
        print(" ".join(f"{x},{y}" for x, y in extra), flush=True)
        return 0

    existing = [(pcbnew.ToMM(t.GetPosition().x) - OX, pcbnew.ToMM(t.GetPosition().y) - OY)
                for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"]
    chosen = []
    for c in cands:
        if all((c[0] - o[0]) ** 2 + (c[1] - o[1]) ** 2 >= spacing ** 2 for o in chosen + existing):
            chosen.append(c)
    print(" ".join(f"{x},{y}" for x, y in chosen), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
