"""R57: the enclosures' rule checks at one point of the coupons' clearance window (no SolidCraft).

    uv run --with pytest --with pyyaml python tests/enclosure/clearance_window.py CLR_ALIGN CLR_REMOVE

sets `clearances.py`'s values (`clr_snap` = `clr_remove` + 0.05, the README's rule) before anything
imports them, builds both generators' scripts as the fast tests do, and runs every rule test: each
no-argument test of `test_airq.py`, `test_airq_mini.py` and `test_airq_mini_check.py` (the arithmetic
and analytic checks, from the parameters) except those in `NOT_RULES`, which pin a default value or
a committed file rather than a rule. Prints {test: null if it passes, else its error} as JSON.

`test_clearance_window.py` runs this at the window's corners and edges and holds each test to the
window `WINDOWS` gives it (README "Coupon results": the supported window per rule).
"""
from __future__ import annotations

import importlib
import inspect
import json
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODULES = ("test_airq", "test_airq_mini", "test_airq_mini_check")

# The coupons' plausible results (R57): the rules should hold over all of it.
ALIGN = (0.10, 0.20)
REMOVE = (0.15, 0.30)

# Tests that are not rules: they pin a value at the defaults (the committed numbers the README
# quotes) or read committed files, so they move with any clearance by design.
NOT_RULES = {
    "test_airq_mini::test_lip_18_keeps_three_slot_rows_and_the_plug_under_the_slant_at_15_5": "a counterfactual (the rejected 15.5 lip) at the defaults",
    "test_airq_mini_check::test_stop_tolerance_keeps_the_light_checks": "slow (22 s); its arithmetic part is `test_stop_clears_the_board_at_its_thickest`",
    "test_airq_mini_check::test_no_straight_path_between_the_guides": "slow (11 s); run by hand over the window (README)",
}

# A rule that cannot be made independent of the clearances by a local change (R57 point 3) holds
# only over the windows given here: rectangles (clr_align low, high, clr_remove low, high), the
# rule held at any point inside one of them. The README's "Supported window per rule" table gives
# the same windows and the parameter to change outside them. Every other rule test holds over
# ALIGN x REMOVE.
WINDOWS: dict[str, tuple[tuple[float, float, float, float], ...]] = {
    # the 73 mm FFC bought: the jog's window of nominal lengths moves with the board (clr_remove); below 0.16 73 is
    # outside it: set ffc_len inside `airq_face.ffc_len_window` and order that (`test_ffc_jog_takes_one_custom_length`
    # holds over the whole window)
    "test_airq::test_ffc_route_length_and_service_lift": ((0.10, 0.20, 0.16, 0.30),),
    # the guide's delivery (>= 3 % per LED, padded): the tongue narrows with clr_align and the entry gap grows with clr_remove
    "test_airq::test_guide_delivers_light_to_the_exit": ((0.10, 0.15, 0.15, 0.30), (0.10, 0.20, 0.15, 0.28)),
    # R13: lines from the D2 foot's tail-side face pass behind gap_stop through the gd_clr (clr_remove) slab
    "test_airq::test_ms5611_sees_no_led_or_guide_face": ((0.10, 0.20, 0.15, 0.20),),
    # stated, not a rule: led_mask's leak grows with its gd_clr gap
    "test_airq::test_led_mask_leaks_about_2_percent": ((0.10, 0.20, 0.15, 0.25),),
    # the mini's SEN66 plug under the slant, and the intake throat (R25) at the tolerance corner
    "test_airq_mini::test_sen66_plug_clears_the_slant": ((0.10, 0.15, 0.15, 0.30), (0.10, 0.20, 0.15, 0.28)),
    "test_airq_mini_check::test_intake_throat_keeps_r25": ((0.10, 0.15, 0.15, 0.29), (0.10, 0.20, 0.15, 0.28)),
    # the firm foam's bound on the mini's top seal (the soft foam specified holds everywhere)
    "test_airq_mini_check::test_zone_wall_held_down_with_firm_foam": ((0.10, 0.20, 0.18, 0.30),),
}


def windows(test: str) -> tuple[tuple[float, float, float, float], ...]:
    return WINDOWS.get(test, ((*ALIGN, *REMOVE),))


def inside(test: str, align: float, remove: float) -> bool:
    e = 1e-9
    return any(a0 - e <= align <= a1 + e and r0 - e <= remove <= r1 + e for a0, a1, r0, r1 in windows(test))


def rule_tests(mod) -> list[str]:
    out = []
    for name, fn in vars(mod).items():
        if name.startswith("test_") and inspect.isfunction(fn) and not inspect.signature(fn).parameters:
            key = f"{mod.__name__}::{name}"
            if key not in NOT_RULES:
                out.append(name)
    return out


def _where(exc: BaseException, mod_name: str) -> str:
    """The error and the test's line that raised it (outside pytest a bare assert has no message)."""
    frames = [f for f in traceback.extract_tb(exc.__traceback__) if Path(f.filename).stem == mod_name]
    at = f" at {mod_name}.py:{frames[-1].lineno}: {frames[-1].line}" if frames else ""
    msg = str(exc).splitlines()[0][:300] if str(exc) else ""
    return f"{type(exc).__name__}{at}" + (f" | {msg}" if msg else "")


def run(align: float, remove: float) -> dict[str, str | None]:
    sys.path[:0] = [str(HERE.parents[1] / "enclosure" / "src"), str(HERE)]
    import clearances
    if any(m in sys.modules for m in ("enclosure_common", "layout_study", "airq", "airq_mini")):
        raise RuntimeError("clearance_window.run must set clearances.py's values before the generators are imported")
    clearances.CLR_ALIGN, clearances.CLR_REMOVE, clearances.CLR_SNAP = align, remove, round(remove + 0.05, 6)
    out: dict[str, str | None] = {}
    for mod_name in MODULES:
        mod = importlib.import_module(mod_name)
        for name in rule_tests(mod):
            try:
                getattr(mod, name)()
                out[f"{mod_name}::{name}"] = None
            except Exception as exc:     # noqa: BLE001 (the test's own assertion or error, reported)
                out[f"{mod_name}::{name}"] = _where(exc, mod_name)
    return out


if __name__ == "__main__":
    print(json.dumps(run(float(sys.argv[1]), float(sys.argv[2]))))
