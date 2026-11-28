"""Main board, routing step 2: prepare the Specctra DSN that tools/hw/build.py writes (build/main.dsn) for
Freerouting 2.5.0.

    uv run python tools/hw/route/fr_prep.py [--signal-width UM] build/main.dsn build/fr-main.dsn [NET ...]

- Moves the nets the ground pours connect (default: GND) into their own net class `Poured`, which
  Freerouting is told to ignore (`-inc Poured`). Their pads, tracks and vias stay in the design with
  their net, so they are neither routed nor treated as foreign obstacles.
- Routes the Power class at 0.3 mm (0.4 mm is only its drawing default in layout.yaml).
- `--signal-width UM` routes the default class narrower (a second pass for what the first one left).
- Keeps routing 0.35 mm from the outline (layout.yaml `min_copper_edge_clearance` is 0.3; the DSN does
  not carry it): keep-out bands inside the four edges of the 60 x 30 mm outline (DSN units um, y negated).

Hard-codes the main board's outline (60 x 30 mm at page 100, 100). Not part of the build.
"""
import re
import sys

POWER_WIDTH = 300          # um
EDGE_BAND = 350            # um
OUTLINE = (100000, -100000, 160000, -130000)    # x0, y0, x1, y1 in DSN units (um, y up)


def main(argv: list[str]) -> int:
    args = list(argv)
    signal_width = None
    if "--signal-width" in args:
        i = args.index("--signal-width")
        signal_width = int(args[i + 1])
        del args[i:i + 2]
    src, dst, nets = args[0], args[1], args[2:] or ["GND"]
    t = open(src, encoding="utf-8").read()
    if signal_width:
        k = t.index("(class kicad_default")
        w = t.index("(width 200)", k)
        t = t[:w] + f"(width {signal_width})" + t[w + len("(width 200)"):]
    for net in nets:                       # take the net out of the class that lists it
        t, n = re.subn(r"(\(class [^\n]*?) " + re.escape(net) + r"(?=[\s)])", r"\1", t)
        assert n == 1, (net, n)
    k = t.index("(class Power")
    w = t.index("(width 400)", k)
    t = t[:w] + f"(width {POWER_WIDTH})" + t[w + len("(width 400)"):]
    nl = "\n"
    block = ("    (class Poured " + " ".join(nets) + nl + "      (circuit" + nl
             + '        (use_via "Via[0-1]_600:300_um")' + nl + "      )" + nl + "      (rule" + nl
             + "        (width 300)" + nl + "        (clearance 150)" + nl + "      )" + nl + "    )" + nl)
    x0, y0, x1, y1 = OUTLINE
    d = EDGE_BAND
    bands = [(x0, y0, x1, y0 - d), (x0, y1 + d, x1, y1), (x0, y0, x0 + d, y1), (x1 - d, y0, x1, y1)]
    ko = "".join(f'    (keepout "" (polygon {layer} 0  {a} {b}  {c} {b}  {c} {e}  {a} {e})){nl}'
                 for layer in ("F.Cu", "B.Cu") for a, b, c, e in bands)
    j = t.index("    (keepout ")
    t = t[:j] + ko + t[j:]
    i = t.index("    (class ")
    t = t[:i] + block + t[i:]
    open(dst, "w", encoding="utf-8", newline="\n").write(t)
    print("moved to class Poured:", nets)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
