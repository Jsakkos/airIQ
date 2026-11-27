"""Shared print-fit defaults: the clearances, grille slot width, wall and flexure sizes that the
coupons test and the enclosure generators (Tasks 3-5) import.

Edit the values here after the owner's coupon results (enclosure/README.md "Coupon results"):
one place, so the coupons and both enclosures stay in step. `add_params(script)` adds them as
commented parameters, in this order, so a generator gets identical names and comments.
"""
from __future__ import annotations

CLR_ALIGN = 0.15       # per-side gap, located part
CLR_REMOVE = 0.20      # per-side gap, part that lifts off
CLR_SNAP = 0.25        # per-side gap, snap or latch fit
SLOT_W = 1.2           # grille slot width
WALL = 1.8             # wall thickness
FLEX_T = 1.0           # flexure beam thickness in the push direction
FLEX_LEN = 12.0        # flexure beam length
FLEX_GAP = 0.10        # pad-to-actuator gap at rest


def add_params(s) -> None:
    """Add the shared defaults to a `sclib.Script`."""
    p = s.param
    p("clr_align", CLR_ALIGN, "plan default (Task 2 results override): per-side gap for an aligned, located part (R20); clearances.py", favorite=True)
    p("clr_remove", CLR_REMOVE, "plan default (Task 2 results override): per-side gap for a part that lifts off (R20); clearances.py", favorite=True)
    p("clr_snap", CLR_SNAP, "plan default (Task 2 results override): per-side gap for a snap or latch fit (R20); clearances.py", favorite=True)
    p("slot_w", SLOT_W, "plan default (Task 2 results override): grille slot width; clearances.py", favorite=True)
    p("wall", WALL, "plan: wall thickness (default 1.8 mm, at least 1.6); clearances.py", favorite=True)
    p("flex_t", FLEX_T, "flexure beam thickness in the push direction: the stiffness to tune from the coupon (a cantilever of 1.0 x 4.9 x 12 mm in PETG is about 0.3 N at full stroke); clearances.py")
    p("flex_len", FLEX_LEN, "flexure beam length (the cantilever from the anchor to the pad); clearances.py")
    p("flex_gap", FLEX_GAP, "gap between the pad and the actuator tip at rest: tune from the coupon; clearances.py")
