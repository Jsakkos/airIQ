"""JLCPCB fabrication and assembly files from KiCad exports (stdlib only).

- Gerbers and drill: `kicad-cli pcb export gerbers` with GERBER_ARGS and `pcb export drill` with
  DRILL_ARGS, then `gerber_zip` (creation dates dropped, so an unchanged board gives the same zip).
- BOM: `kicad-cli sch export bom` writes JLC's columns directly (see BOM_ARGS).
- CPL: `cpl_from_pos` turns `kicad-cli pcb export pos --format csv --units mm` output
  (Ref,Val,Package,PosX,PosY,Rot,Side) into JLC's Designator,Mid X,Mid Y,Layer,Rotation.

Every option is on the command line: the board's own plot settings (`setup` / `pcbplotparams`) are
rewritten by each rebuild, so settings made in KiCad's Plot dialog would not last. The options follow
JLCPCB's "How to generate Gerber and Drill files in KiCad 9" (jlcpcb.com/help, read 2026-11-25):
the 2-layer set plus both paste layers (needed for SMT assembly), Protel extensions, X2 attributes
and netlist attributes, 4.6 mm coordinates; Excellon in mm, decimal, oval holes in the alternate
(G85 slot) mode, PTH and NPTH in separate files. One difference: the Gerbers, the drill files and the
CPL all use KiCad's drill/place origin (the outline's bottom-left corner, `layout.yaml`), so all
three share one origin with positive coordinates; JLC's guide plots Gerbers and drill in absolute
coordinates, which is equivalent as long as the files agree.

Rotations are KiCad's, with no per-part offsets: every polarised part uses an EasyEDA (JLC library)
footprint, which keeps JLC's placement orientation, and the KiCad stock footprints are 2-pad R/C
parts. Check JLC's placement preview before paying (hardware/README.md, "Ordering").
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path

# Comment = Value, one line per Value + Footprint + LCSC, DNP parts left out.
BOM_ARGS = ["--fields", "Value,Reference,Footprint,LCSC",
            "--labels", "Comment,Designator,Footprint,LCSC",
            "--group-by", "Value,Footprint,LCSC", "--ref-range-delimiter", "", "--exclude-dnp"]
CPL_HEADER = ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]

GERBER_LAYERS = ["F.Cu", "B.Cu", "F.Paste", "B.Paste", "F.Silkscreen", "B.Silkscreen", "F.Mask",
                 "B.Mask", "Edge.Cuts"]
# kicad-cli's defaults are kept for Protel extensions, X2 and netlist attributes and aperture macros;
# --board-plot-params is NOT given, so the board's stored plot settings are ignored. JLC's "check zone
# fills before plotting" is not needed: the build's DRC step refills the zones and saves the board first.
GERBER_ARGS = ["--layers", ",".join(GERBER_LAYERS), "--precision", "6", "--use-drill-file-origin",
               "--subtract-soldermask"]
DRILL_ARGS = ["--format", "excellon", "--drill-origin", "plot", "--excellon-units", "mm",
              "--excellon-zeros-format", "decimal", "--excellon-oval-format", "alternate",
              "--excellon-separate-th"]
# What goes into the zip: one Gerber per layer above (Protel extensions) and the two drill files.
GERBER_SUFFIXES = (".gtl", ".gbl", ".gtp", ".gbp", ".gto", ".gbo", ".gts", ".gbs", ".gm1", ".drl")

_GERBER_DATE = re.compile(r"^(G04 Created by KiCad \([^)]*\)) date [^*]*\*$")
_DRILL_DATE = re.compile(r"^(; DRILL file .*?) date \S+$")


def strip_dates(text: str) -> str:
    """`text` (a KiCad Gerber or Excellon file) without its creation date, with LF line ends.

    Drops the optional `.CreationDate` file attribute (`%TF.CreationDate,...*%` in a Gerber,
    `; #@! TF.CreationDate,...` in a drill file) and the date in KiCad's header comment; nothing
    else changes.
    """
    out = []
    for line in text.splitlines():
        if line.startswith(("%TF.CreationDate,", "; #@! TF.CreationDate,")):
            continue
        out.append(_DRILL_DATE.sub(r"\1", _GERBER_DATE.sub(r"\1*", line)))
    return "\n".join(out) + "\n"


def gerber_zip(folder: Path) -> bytes:
    """A zip of the Gerber and drill files in `folder` (GERBER_SUFFIXES), dates stripped.

    The same files always give the same bytes: members sorted by name, stored (not deflated, so
    the bytes do not depend on the zlib build), with a fixed timestamp and attributes.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for path in sorted(folder.iterdir(), key=lambda p: p.name):
            if path.suffix.lower() not in GERBER_SUFFIXES:
                continue
            info = zipfile.ZipInfo(path.name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system, info.external_attr = 3, 0o100644 << 16
            z.writestr(info, strip_dates(path.read_text(encoding="utf-8")).encode("utf-8"))
    return buf.getvalue()


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
