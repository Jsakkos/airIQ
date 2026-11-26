"""ref_main / ref_tongue: the assembled PCBs, imported unchanged from hardware/step/*.step.

`component.insert_design` takes only .sc designs, so each STEP file is wrapped in a design that
holds nothing but the import (`file.insert_step`, the file's own axes: no transform). The STEP
frame is the one interface.yaml `mechanical.<board>.step` records: STEP x = X, y = -Y,
z = Z + 1.6 in the layout frame (board top-left corner, +Y toward the board's front edge for the
main board and toward the Qwiic edge for the tongue): the board's bottom face at z = 0, its top
face at z = 1.6 (KiCad exports the dielectric only, z 0 .. 1.51).

The .sc file embeds the STEP file (a container blob named by its SHA-256), so a re-exported
STEP needs a rebuild: tests/enclosure checks the embedded copy is the current one. The copy
embedded is the file as git stores it (LF line endings): `prepare()` stages it in
enclosure/.build/step/, so a checkout with CRLF endings (core.autocrlf on Windows) builds the
same design as any other.
"""
from __future__ import annotations

from pathlib import Path

from sclib import ENCLOSURE, REPO, Script

STEP_DIR = REPO / "hardware" / "step"
STAGE_DIR = ENCLOSURE / ".build" / "step"


def canonical(step_name: str) -> bytes:
    """The STEP file's bytes with LF line endings, as the repository stores it."""
    return (STEP_DIR / step_name).read_bytes().replace(b"\r\n", b"\n")


def stage(step_name: str) -> Path:
    """Write the canonical copy to enclosure/.build/step/ (when it differs) and return its path."""
    data = canonical(step_name)
    path = STAGE_DIR / step_name
    if not path.exists() or path.read_bytes() != data:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return path


def wrapper(design: str, step_name: str) -> Script:
    if not (STEP_DIR / step_name).exists():
        raise FileNotFoundError(STEP_DIR / step_name)
    s = Script(design)
    # the import makes a component named after `name` and many features (its rigid group's
    # joints take ids too), so no feature may follow it in this script
    s._feature("file.insert_step", step_name.removesuffix(".step"), {"path": str(STAGE_DIR / step_name)})
    s.next_id = None
    return s
