"""Generate a board's KiCad project files: .kicad_pro settings and the library tables.

The library tables register the project libraries (`airq`) and every stock KiCad library the
design uses, so the project opens with all symbols and footprints resolved even where KiCad's
global library tables are not set up (as on the machine this was built on). A stock entry has
the same name and path as in KiCad's default global table, so it shadows it harmlessly.

The .kicad_pro is merged: the sections this generator owns are replaced whole from the source,
so a rule or severity deleted from the source is gone from the project and KiCad's default applies:
`board.design_settings.rules`, `board.design_settings.rule_severities`, `erc.rule_severities`,
`net_settings.classes` and `net_settings.netclass_patterns`. Everything else KiCad or the owner
saved (track and via presets, plot settings, ...) is kept. The file is written as JSON with sorted
keys and two-space indent, like KiCad's, but is not byte-for-byte what a KiCad save writes: after
a save in the KiCad GUI, rebuild once and commit the result.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from design import Design
from gen_sch import Placed
from kicad_lib import Libraries, split_lib_id, symbol_property

# Checks that are warnings by default but guard the generated design, so `--severity-error`
# must fail on them: DRC schematic parity (board no longer matches its schematic) and the
# library comparisons (a footprint or symbol differs from its library: a stale build after a
# library edit, or a generator bug). Layout/project overrides still win.
DRC_ERRORS = ("missing_footprint", "extra_footprint", "duplicate_footprints",
              "footprint_symbol_mismatch", "net_conflict", "lib_footprint_mismatch")
ERC_ERRORS = ("lib_symbol_mismatch",)
_NETCLASS_DEFAULTS = {
    "bus_width": 12, "clearance": 0.2, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
    "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
    "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
    "track_width": 0.2, "tuning_profile": "", "via_diameter": 0.6, "via_drill": 0.3,
    "wire_width": 6,
}


def used_libraries(design: Design, placed: list[Placed]) -> tuple[list[str], list[str]]:
    """Sorted symbol and footprint library nicknames used by the design."""
    syms = {split_lib_id(pl.src.symbol)[0] for pl in placed}
    syms |= {split_lib_id(v)[0] for v in design.power_symbols.values()}
    fps = {split_lib_id(pl.src.footprint or symbol_property(pl.sym, "Footprint"))[0]
           for pl in placed if not pl.power}
    return sorted(syms), sorted(fps)


def _table(kind: str, rows: list[tuple[str, str, str]]) -> str:
    lines = [f"({kind}", "\t(version 7)"]
    for name, uri, descr in rows:
        lines.append(f'\t(lib (name "{name}") (type "KiCad") (uri "{uri}") (options "") '
                     f'(descr "{descr}"))')
    return "\n".join(lines) + "\n)\n"


def _project_uri(path: Path, out_dir: Path) -> str:
    return "${KIPRJMOD}/" + Path(os.path.relpath(path, out_dir)).as_posix()


def lib_tables(design: Design, placed: list[Placed], libs: Libraries) -> dict[str, str]:
    syms, fps = used_libraries(design, placed)
    sym_rows = [(n, _project_uri(design.symbol_libs[n], design.out_dir), "airQ project library")
                if n in design.symbol_libs else
                (n, f"${{KICAD10_SYMBOL_DIR}}/{n}.kicad_sym", "KiCad stock library") for n in syms]
    fp_rows = [(n, _project_uri(design.footprint_libs[n], design.out_dir), "airQ project library")
               if n in design.footprint_libs else
               (n, f"${{KICAD10_FOOTPRINT_DIR}}/{n}.pretty", "KiCad stock library") for n in fps]
    return {"sym-lib-table": _table("sym_lib_table", sym_rows),
            "fp-lib-table": _table("fp_lib_table", fp_rows)}


def _netclasses(layout: dict) -> tuple[list[dict], list[dict]]:
    classes, patterns = [], []
    defined = layout.get("netclasses") or {}
    names = ["Default"] + [n for n in defined if n != "Default"]
    for prio, name in enumerate(names):
        spec = dict(defined.get(name) or {})
        nets = spec.pop("nets", [])
        cls = {**_NETCLASS_DEFAULTS, **spec, "name": name,
               "priority": 2147483647 if name == "Default" else prio - 1}
        classes.append(cls)
        patterns += [{"netclass": name, "pattern": str(n)} for n in nets]
    return classes, patterns


def kicad_dru(design: Design) -> str:
    """The project's custom DRC rules file: layout.yaml `custom_rules`, in KiCad's rule syntax."""
    rules = str(design.layout.get("custom_rules") or "").strip()
    return "(version 1)\n" + (rules + "\n" if rules else "")


def kicad_pro(design: Design, existing: str | None) -> str:
    """`existing` with the sections this generator owns replaced (see the module docstring)."""
    pro = json.loads(existing) if existing else {}
    pro["meta"] = {"filename": f"{design.name}.kicad_pro", "version": 3}
    pro.setdefault("erc", {})["rule_severities"] = {**{k: "error" for k in ERC_ERRORS},
                                                    **design.erc_severities}
    ds = pro.setdefault("board", {}).setdefault("design_settings", {})
    ds["rules"] = dict(design.layout.get("rules") or {})
    ds["rule_severities"] = {**{k: "error" for k in DRC_ERRORS},
                             **(design.layout.get("drc_severities") or {})}
    classes, patterns = _netclasses(design.layout)
    ns = pro.setdefault("net_settings", {})
    ns["classes"], ns["netclass_patterns"] = classes, patterns
    ns.setdefault("meta", {"version": 4})
    return json.dumps(pro, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
