"""Check a BOM and/or the curated parts table (stdlib only).

Usage:
    python tools/hw/check_bom.py BOM PARTS [--fresh-days N] [--max-extended N]
    python tools/hw/check_bom.py --parts-only PARTS [--fresh-days N] [--max-extended N]

PARTS is a CSV with columns lcsc,mpn,library,economic,checked_on,stock,unit_usd where
`library` is Basic / Preferred / Extended (JLCPCB assembly part classes). An optional 8th
column `boards` lists, space-separated, the boards a part is placed on (e.g. `main`, `tongue`,
`main tongue`).

Rules for every checked part line: economic is yes/true, stock > 0, checked_on is no older
than --fresh-days (when given), and at most --max-extended (default 15) distinct Extended parts.
`--parts-only` applies them to the whole table; when the table has a `boards` column the
Extended cap is applied per board instead (each board is a separate JLC order) and every
row must name at least one board. With a BOM the rules apply only to the LCSC numbers the BOM
uses, and every BOM row (except DNP rows) must carry an LCSC number that is in PARTS.
The BOM's LCSC column is found by header (/lcsc|jlcpcb part/i); a row is DNP when a `DNP`
column is truthy or any cell contains "DNP".

Prints one error per line and exits 1 when there are any.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date, timedelta
from pathlib import Path

_TRUE = {"yes", "true", "y", "1"}
_LCSC_HEADER = re.compile(r"lcsc|jlcpcb part", re.IGNORECASE)
_REF_HEADER = re.compile(r"designator|reference|^ref$", re.IGNORECASE)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), [
            {k: (v or "").strip() for k, v in row.items() if k is not None} for row in reader]


PARTS_COLUMNS = ("lcsc", "mpn", "library", "economic", "checked_on", "stock", "unit_usd")
BOARDS_COLUMN = "boards"  # optional


def _load_parts(parts_csv: Path) -> tuple[dict[str, dict[str, str]], list[str]]:
    """The parts table keyed by LCSC number, plus structural errors (header, empty, duplicates)."""
    header, rows = _read_csv(parts_csv)
    header = [h.strip() for h in header]
    absent = [c for c in PARTS_COLUMNS if c not in header]
    if absent:
        return {}, [f"{parts_csv}: parts table is missing column(s): {', '.join(absent)}"]
    parts: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    for i, r in enumerate(rows, 2):
        r = {k.strip(): v for k, v in r.items()}
        if not r.get("lcsc"):
            errors.append(f"{parts_csv} line {i}: parts row has no LCSC number")
        elif r["lcsc"] in parts:
            errors.append(f"{parts_csv} line {i}: duplicate LCSC number {r['lcsc']}")
        else:
            parts[r["lcsc"]] = r
    if not parts and not errors:
        errors.append(f"{parts_csv}: parts table is empty")
    return parts, errors


def _check_extended_cap(lines: list[dict[str, str]], max_extended: int, scope: str = "") -> list[str]:
    extended = sorted({r["lcsc"] for r in lines if r.get("library", "").lower() == "extended"})
    if len(extended) > max_extended:
        return [f"{scope}{len(extended)} distinct Extended parts exceed the limit of {max_extended}: "
                f"{', '.join(extended)}"]
    return []


def _check_lines(lines: list[dict[str, str]], max_extended: int | None, fresh_days: int | None,
                 today: date | None) -> list[str]:
    """Per-line rules, plus the Extended cap over all `lines` unless max_extended is None."""
    today = today or date.today()
    errors: list[str] = []
    for r in lines:
        lcsc = r["lcsc"]
        if r.get("economic", "").lower() not in _TRUE:
            errors.append(f"{lcsc}: not economic (economic = {r.get('economic', '')!r})")
        try:
            in_stock = int(float(r.get("stock", ""))) > 0
        except ValueError:
            in_stock = False
        if not in_stock:
            errors.append(f"{lcsc}: no stock (stock = {r.get('stock', '')!r})")
        if fresh_days is not None:
            try:
                checked = date.fromisoformat(r.get("checked_on", ""))
            except ValueError:
                errors.append(f"{lcsc}: checked_on {r.get('checked_on', '')!r} is not an ISO date")
            else:
                if checked < today - timedelta(days=fresh_days):
                    errors.append(f"{lcsc}: stale, checked_on {checked} is more than "
                                  f"{fresh_days} days before {today}")
    if max_extended is not None:
        errors += _check_extended_cap(lines, max_extended)
    return errors


def check_parts(parts_csv: Path, max_extended: int = 15, fresh_days: int | None = None,
                today: date | None = None) -> list[str]:
    """Check the whole parts table; with a `boards` column the Extended cap is per board."""
    parts, errors = _load_parts(parts_csv)
    lines = list(parts.values())
    if not any(BOARDS_COLUMN in r for r in lines):
        return errors + _check_lines(lines, max_extended, fresh_days, today)
    errors += _check_lines(lines, None, fresh_days, today)
    per_board: dict[str, list[dict[str, str]]] = {}
    for r in lines:
        boards = r.get(BOARDS_COLUMN, "").split()
        if not boards:
            errors.append(f"{r['lcsc']}: no board named in the '{BOARDS_COLUMN}' column")
        for b in boards:
            per_board.setdefault(b, []).append(r)
    for b in sorted(per_board):
        errors += _check_extended_cap(per_board[b], max_extended, scope=f"board {b}: ")
    return errors


def check_bom(bom_csv: Path, parts_csv: Path, **kw) -> list[str]:
    """Check a BOM against the parts table; `kw` are check_parts' keyword arguments."""
    parts, parts_errors = _load_parts(parts_csv)
    if not parts:
        return parts_errors
    header, rows = _read_csv(bom_csv)
    lcsc_col = next((h for h in header if _LCSC_HEADER.search(h)), None)
    if lcsc_col is None:
        return [f"{bom_csv}: no LCSC column (expected a header matching 'LCSC' or 'JLCPCB Part')"]
    ref_col = next((h for h in header if _REF_HEADER.search(h)), None)
    dnp_col = next((h for h in header if h.lower() == "dnp"), None)
    errors: list[str] = list(parts_errors)
    used: dict[str, dict[str, str]] = {}
    for i, row in enumerate(rows, 2):  # line 1 is the header
        if dnp_col and row.get(dnp_col, "").lower() in _TRUE | {"dnp", "x"}:
            continue
        if any("dnp" in v.lower() for v in row.values()):
            continue
        who = row.get(ref_col, "") if ref_col else ""
        where = f"BOM line {i}" + (f" ({who})" if who else "")
        lcsc = row.get(lcsc_col, "")
        if not lcsc:
            errors.append(f"{where}: no LCSC number")
        elif lcsc not in parts:
            errors.append(f"{where}: {lcsc} is not in the parts table")
        else:
            used[lcsc] = parts[lcsc]
    return errors + _check_lines(list(used.values()), kw.get("max_extended", 15),
                                 kw.get("fresh_days"), kw.get("today"))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Check a BOM / parts table.")
    ap.add_argument("files", nargs="+", metavar="FILE", help="BOM PARTS, or PARTS with --parts-only")
    ap.add_argument("--parts-only", action="store_true", help="check the parts table alone")
    ap.add_argument("--fresh-days", type=int, default=None)
    ap.add_argument("--max-extended", type=int, default=15)
    args = ap.parse_args(argv)
    if len(args.files) != (1 if args.parts_only else 2):
        ap.error("expected PARTS with --parts-only, otherwise BOM PARTS")
    kw = {"max_extended": args.max_extended, "fresh_days": args.fresh_days}
    if args.parts_only:
        errors = check_parts(Path(args.files[0]), **kw)
    else:
        errors = check_bom(Path(args.files[0]), Path(args.files[1]), **kw)
    for e in errors:
        print(e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
