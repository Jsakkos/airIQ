"""Build the enclosure designs from their generators.

    uv run --with pyyaml python enclosure/build.py <design>... | all
    uv run --with pyyaml python enclosure/build.py --list

Each generator (enclosure/src/) emits a SolidCraft command script into enclosure/.build/
(gitignored); solidcraft-cli runs it and saves the design (.sc) where the design's OUTPUT says,
under enclosure/. See enclosure/README.md.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import encbuild  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("designs", nargs="*", help=f"'all' or any of: {', '.join(encbuild.DESIGNS)}")
    ap.add_argument("--list", action="store_true", help="list the designs and exit")
    ap.add_argument("--no-commit", action="store_true",
                    help="build into enclosure/.build/ only; leave the committed files alone")
    args = ap.parse_args(argv)
    if args.list or not args.designs:
        for name, mod in encbuild.DESIGNS.items():
            print(f"{name:16} {mod}")
        return 0 if args.list else 2
    names = list(encbuild.DESIGNS) if args.designs == ["all"] else args.designs
    unknown = [n for n in names if n not in encbuild.DESIGNS]
    if unknown:
        ap.error(f"unknown design(s): {', '.join(unknown)}")
    cli = encbuild.cli_path()
    if not cli:
        print("solidcraft-cli not found: install SolidCraft or set SOLIDCRAFT_CLI", file=sys.stderr)
        return 1
    for name in names:
        r = encbuild.build(name, cli, commit=not args.no_commit)
        where = r["file"].relative_to(encbuild.ENCLOSURE.parent)
        note = "" if r["committed"] else "  (not committed: over the R8 limit, or --no-commit)"
        print(f"{name}: {r['design']} -> {where} ({r['bytes'] / 1024:.0f} KB){note}")
        bodies = r["bodies"]
        shown = bodies if len(bodies) <= 12 else {"(all bodies)": encbuild.union(bodies.values())}
        if len(bodies) > 12:
            print(f"    {len(bodies)} bodies")
        for body, bb in shown.items():
            size = " x ".join(f"{hi - lo:.3f}" for lo, hi in zip(bb["min"], bb["max"]))
            print(f"    {body:28} {size}   min {[round(v, 3) for v in bb['min']]}")
        for ex in r["exports"]:
            where = ex["file"].relative_to(encbuild.ENCLOSURE.parent)
            parts = f", reopens with {len(ex['parts'])} parts" if ex["parts"] is not None else ""
            print(f"    export {where} ({ex['bytes'] / 1024:.0f} KB{parts})"
                  + ("" if ex["committed"] else "  (not committed)"))
            for part, bb in (ex["parts"] or {}).items():
                size = " x ".join(f"{hi - lo:.3f}" for lo, hi in zip(bb["min"], bb["max"]))
                print(f"      {part:26} {size}   min {[round(v, 3) for v in bb['min']]}")
        for w in r["warnings"]:
            print(f"    warning: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
