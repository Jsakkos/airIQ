"""Check a .kicad_pcb: the Edge.Cuts outline fits a size limit and every footprint is on F.Cu.

Usage (stdlib only):
    python tools/hw/check_board.py PCB --max-w W --max-h H

The bounding box covers board-level gr_line/gr_rect/gr_arc/gr_circle/gr_poly and footprint-level
fp_* shapes on Edge.Cuts (moved by the footprint position and rotation). Stroke width is ignored.
Prints one error per line and exits 1 when there are any.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from sexpr import atom, child, children, parse

TOL = 1e-6  # mm
_SHAPES = ("line", "rect", "arc", "circle", "poly")


def _xy(node: list, name: str) -> tuple[float, float]:
    c = child(node, name)
    return float(c[1]), float(c[2])


def _arc_points(p0, pm, p1) -> list[tuple[float, float]]:
    """Start, end and true extreme points of the arc through start/mid/end.

    The circle through the three points is found, then every 0/90/180/270 degree extreme
    that lies on the swept part of the arc is added (not just the 3-point bounding box).
    """
    (x1, y1), (x2, y2), (x3, y3) = p0, pm, p1
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-12:  # collinear: no real arc
        return [p0, pm, p1]
    ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / d
    uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / d
    r = math.hypot(x1 - ux, y1 - uy)
    tau = 2 * math.pi
    a_s, a_m, a_e = (math.atan2(y - uy, x - ux) for x, y in (p0, pm, p1))
    to_mid, to_end = (a_m - a_s) % tau, (a_e - a_s) % tau
    ccw = to_mid < to_end  # angles increase from start through mid to end
    sweep = to_end if ccw else tau - to_end
    pts = [p0, p1]
    for k in range(4):
        theta = k * math.pi / 2
        off = (theta - a_s) % tau if ccw else (a_s - theta) % tau
        if off <= sweep:
            pts.append((ux + r * math.cos(theta), uy + r * math.sin(theta)))
    return pts


def _shape_points(shape: list) -> list[tuple[float, float]]:
    kind = shape[0].split("_", 1)[1]
    if kind in ("line", "rect"):
        a, b = _xy(shape, "start"), _xy(shape, "end")
        if kind == "line":
            return [a, b]
        return [a, (b[0], a[1]), b, (a[0], b[1])]
    if kind == "arc":
        return _arc_points(_xy(shape, "start"), _xy(shape, "mid"), _xy(shape, "end"))
    return [(float(p[1]), float(p[2])) for p in children(child(shape, "pts") or [], "xy")]


def _rotate(pt, angle_deg: float):
    """KiCad rotation (positive is counter-clockwise on screen, y points down)."""
    a = math.radians(angle_deg)
    x, y = pt
    return (x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a))


def _edge_points(shapes: list[list], at: tuple[float, float] = (0, 0), rot: float = 0.0):
    pts: list[tuple[float, float]] = []
    for s in shapes:
        if atom(s, "layer") != "Edge.Cuts":
            continue
        if s[0].endswith("circle"):  # rotation leaves the radius unchanged
            (ccx, ccy), (ex, ey) = _xy(s, "center"), _xy(s, "end")
            cx, cy = _rotate((ccx, ccy), rot)
            r = math.hypot(ex - ccx, ey - ccy)
            cx, cy = cx + at[0], cy + at[1]
            pts += [(cx - r, cy - r), (cx + r, cy + r)]
            continue
        pts += [(x + at[0], y + at[1]) for x, y in (_rotate(p, rot) for p in _shape_points(s))]
    return pts


def check_board(pcb: Path, max_w: float, max_h: float) -> list[str]:
    """Return errors for `pcb`; empty when the outline fits and all parts are on F.Cu."""
    tree = parse(Path(pcb).read_text(encoding="utf-8"))
    errors: list[str] = []
    pts = _edge_points([c for c in tree if isinstance(c, list) and c
                        and c[0] in tuple("gr_" + k for k in _SHAPES)])
    for fp in children(tree, "footprint"):
        at = child(fp, "at")
        pos = (float(at[1]), float(at[2])) if at else (0.0, 0.0)
        rot = float(at[3]) if at and len(at) > 3 else 0.0
        pts += _edge_points([c for c in fp if isinstance(c, list) and c
                             and c[0] in tuple("fp_" + k for k in _SHAPES)], pos, rot)
        layer = atom(fp, "layer")
        if layer != "F.Cu":
            errors.append(f"footprint {_reference(fp)} is on {layer}, all parts must be on F.Cu")
    if not pts:
        errors.append("no Edge.Cuts outline found")
        return errors
    width = max(x for x, _ in pts) - min(x for x, _ in pts)
    height = max(y for _, y in pts) - min(y for _, y in pts)
    if width > max_w + TOL:
        errors.append(f"board width {width:.3f} mm exceeds {max_w:g} mm")
    if height > max_h + TOL:
        errors.append(f"board height {height:.3f} mm exceeds {max_h:g} mm")
    return errors


def _reference(fp: list) -> str:
    for p in children(fp, "property"):
        if len(p) > 2 and p[1] == "Reference":
            return p[2]
    for t in children(fp, "fp_text"):
        if len(t) > 2 and t[1] == "reference":
            return t[2]
    return "?"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Check board size and part side.")
    ap.add_argument("pcb")
    ap.add_argument("--max-w", type=float, required=True)
    ap.add_argument("--max-h", type=float, required=True)
    args = ap.parse_args(argv)
    errors = check_board(Path(args.pcb), args.max_w, args.max_h)
    for e in errors:
        print(e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
