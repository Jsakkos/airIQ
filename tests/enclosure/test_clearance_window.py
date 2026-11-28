"""R57: the rule checks hold over the coupons' clearance window, not only at the plan's defaults.

The coupon results (README "Coupon results") change `clr_align`, `clr_remove` and `clr_snap` in
`src/clearances.py`; both enclosures' sizes follow them. This runs every rule test of the airQ and
the airQ mini (`clearance_window.py`: the arithmetic and analytic checks, from the parameters, no
SolidCraft) with the clearances moved to each point of a grid over the window, clr_align 0.10 ...
0.20 by 0.05 and clr_remove 0.15 ... 0.30 by 0.05 (`clr_snap` = `clr_remove` + 0.05), each point
in its own process (the generators read clearances.py when they are imported). A rule holds over
the whole window unless `clearance_window.WINDOWS` gives it a narrower one; those are the rules a
local change cannot free from the clearances, and the README's "Supported window per rule" table
says, for each, the window and the parameter to change outside it.
"""
from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import clearance_window as W

HERE = Path(__file__).resolve().parent
GRID = [(a, r) for a in (0.10, 0.15, 0.20) for r in (0.15, 0.20, 0.25, 0.30)]


def _run(point):
    a, r = point
    out = subprocess.run([sys.executable, str(HERE / "clearance_window.py"), f"{a:.2f}", f"{r:.2f}"],
                         capture_output=True, text=True, timeout=600)
    if out.returncode:
        raise RuntimeError(f"clearance_window.py {a} {r} failed:\n{out.stderr[-2000:]}")
    return json.loads(out.stdout)


@pytest.fixture(scope="module")
def results():
    with ThreadPoolExecutor(max_workers=len(GRID)) as pool:
        return dict(zip(GRID, pool.map(_run, GRID)))


def test_the_grid_covers_the_window_and_the_defaults():
    import clearances
    assert (min(a for a, _ in GRID), max(a for a, _ in GRID)) == W.ALIGN
    assert (min(r for _, r in GRID), max(r for _, r in GRID)) == W.REMOVE
    assert (clearances.CLR_ALIGN, clearances.CLR_REMOVE) in GRID
    for test, rects in W.WINDOWS.items():                     # each narrower window keeps the defaults
        assert W.inside(test, clearances.CLR_ALIGN, clearances.CLR_REMOVE), test
        assert all(W.ALIGN[0] <= a0 <= a1 <= W.ALIGN[1] and r0 <= r1 for a0, a1, r0, r1 in rects), test


@pytest.mark.parametrize("point", GRID, ids=[f"align{a:.2f}-remove{r:.2f}" for a, r in GRID])
def test_rules_hold_over_the_clearance_window(results, point):
    a, r = point
    res = results[point]
    assert len(res) >= 70, sorted(res)                         # every rule test ran
    assert set(W.WINDOWS) <= set(res), set(W.WINDOWS) - set(res)
    broken = {t: msg for t, msg in res.items() if msg and W.inside(t, a, r)}
    assert not broken, json.dumps(broken, indent=1)


def test_narrower_windows_are_needed(results):
    """Each rule given a narrower window does fail somewhere outside it on the grid (else it would not need one)."""
    for test in W.WINDOWS:
        assert any(res[test] for (a, r), res in results.items() if not W.inside(test, a, r)), test
