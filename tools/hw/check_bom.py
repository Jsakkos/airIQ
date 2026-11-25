"""Check a BOM and/or the curated parts table (stdlib only).

Usage:
    python tools/hw/check_bom.py BOM PARTS [--fresh-days N] [--max-extended N]
    python tools/hw/check_bom.py --parts-only PARTS [--fresh-days N] [--max-extended N]

PARTS is a CSV with columns lcsc,mpn,library,economic,checked_on,stock,unit_usd where
`library` is Basic / Preferred / Extended (JLCPCB assembly part classes).

Rules for every checked part line: economic is yes/true, stock > 0, checked_on is no older
than --fresh-days (when given), and at most --max-extended (default 15) distinct Extended parts.
`--parts-only` applies them to the whole table; with a BOM they apply only to the LCSC numbers
the BOM uses, and every BOM row (except DNP rows) must carry an LCSC number that is in PARTS.
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


def _load_parts(parts_csv: Path) -> dict[str, dict[str, str]]:
    return {r["lcsc"]: r for r in _read_csv(parts_csv)[1] if r.get("lcsc")}


def _check_lines(lines: list[dict[str, str]], max_extended: int, fresh_days: int | None,
                 today: date | None) -> list[str]:
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
    extended = sorted({r["lcsc"] for r in lines if r.get("library", "").lower() == "extended"})
    if len(extended) > max_extended:
        errors.append(f"{len(extended)} distinct Extended parts exceed the limit of {max_extended}: "
                      f"{', '.join(extended)}")
    return errors


def check_parts(parts_csv: Path, max_extended: int = 15, fresh_days: int | None = None,
                today: date | None = None) -> list[str]:
    """Check the whole parts table."""
    return _check_lines(list(_load_parts(parts_csv).values()), max_extended, fresh_days, today)


def check_bom(bom_csv: Path, parts_csv: Path, **kw) -> list[str]:
    """Check a BOM against the parts table; `kw` are check_parts' keyword arguments."""
    parts = _load_parts(parts_csv)
    header, rows = _read_csv(bom_csv)
    lcsc_col = next((h for h in header if _LCSC_HEADER.search(h)), None)
    if lcsc_col is None:
        return [f"{bom_csv}: no LCSC column (expected a header matching 'LCSC' or 'JLCPCB Part')"]
    ref_col = next((h for h in header if _REF_HEADER.search(h)), None)
    dnp_col = next((h for h in header if h.lower() == "dnp"), None)
    errors: list[str] = []
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
