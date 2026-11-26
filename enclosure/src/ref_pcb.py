"""ref_main / ref_tongue: the assembled PCBs, imported unchanged from hardware/step/*.step.

`component.insert_design` takes only .sc designs, so each STEP file is wrapped in a design that
holds nothing but the import (`file.insert_step`, the file's own axes: no transform). The STEP
frame is the one interface.yaml `mechanical.<board>.step` records: STEP x = X, y = -Y,
z = Z + 1.6 in the layout frame (board top-left corner, +Y toward the board's front edge for the
main board and toward the Qwiic edge for the tongue): the board's bottom face at z = 0, its top
face at z = 1.6 (KiCad exports the dielectric only, z 0 .. 1.51).

The .sc file embeds the STEP file byte for byte (container blob named by its SHA-256), so a
re-exported STEP needs a rebuild: tests/enclosure checks the embedded copy is the current one.
"""
from __future__ import annotations

from sclib import REPO, Script

STEP_DIR = REPO / "hardware" / "step"


def wrapper(design: str, step_name: str) -> Script:
    s = Script(design)
    path = STEP_DIR / step_name
    if not path.exists():
        raise FileNotFoundError(path)
    # the import makes a component named after `name` and many features (its rigid group's
    # joints take ids too), so no feature may follow it in this script
    s._feature("file.insert_step", step_name.removesuffix(".step"), {"path": str(path)})
    s.next_id = None
    return s
