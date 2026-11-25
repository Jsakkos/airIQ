"""JLCPCB assembly files from KiCad exports (stdlib only).

- BOM: `kicad-cli sch export bom` writes JLC's columns directly (see BOM_ARGS).
- CPL: `cpl_from_pos` turns `kicad-cli pcb export pos --format csv --units mm` output
  (Ref,Val,Package,PosX,PosY,Rot,Side) into JLC's Designator,Mid X,Mid Y,Layer,Rotation.

Rotations are KiCad's. JLC's preview may show some parts turned against its own library;
check the preview before paying (Task 7 records any per-part offsets).
"""
from __future__ import annotations

import csv
import io

# Comment = Value, one line per Value + Footprint + LCSC, DNP parts left out.
BOM_ARGS = ["--fields", "Value,Reference,Footprint,LCSC",
            "--labels", "Comment,Designator,Footprint,LCSC",
            "--group-by", "Value,Footprint,LCSC", "--ref-range-delimiter", "", "--exclude-dnp"]
CPL_HEADER = ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]


def _mm(v: str) -> str:
    s = f"{float(v):.4f}".rstrip("0").rstrip(".")
    return ("0" if s == "-0" else s) + "mm"


def cpl_from_pos(pos_csv: str) -> str:
    rows = list(csv.DictReader(io.StringIO(pos_csv)))
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(CPL_HEADER)
    for r in rows:
        side = r["Side"].strip().lower()
        if side not in ("top", "bottom"):
            raise ValueError(f"{r['Ref']}: unknown side {r['Side']!r}")
        rot = float(r["Rot"]) % 360
        w.writerow([r["Ref"], _mm(r["PosX"]), _mm(r["PosY"]), side.capitalize(),
                    f"{rot:g}"])
    return out.getvalue()
