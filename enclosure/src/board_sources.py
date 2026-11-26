"""Board positions read from their sources, not retyped (ruling R27).

- `hardware/interface.yaml` `mechanical.*`: values through `sclib.mechanical`. A few sizes are
  given there only in a comment (the USB-C's length, J7's body, the LED, module and connector
  heights). `comment_number` reads those from the comment text and fails if the comment no
  longer matches, so a board change cannot leave a stale copy here.
- `hardware/src/main/layout.yaml` for parts interface.yaml does not list (U2, the buck, and U4,
  the MS5611): the placement there, and the footprint's courtyard from the part's KiCad symbol
  and footprint in `hardware/kicad/lib/`.

Pure Python (PyYAML), so the fast tests and CI read the same sources.
"""
from __future__ import annotations

import re
from functools import lru_cache

from sclib import INTERFACE, REPO, mechanical

LAYOUT_MAIN = REPO / "hardware" / "src" / "main"
KICAD_LIB = REPO / "hardware" / "kicad" / "lib"
MAIN = mechanical("main")
TONGUE = mechanical("tongue")


@lru_cache(maxsize=None)
def comment_number(pattern: str, group: int = 1) -> float:
    """A number interface.yaml gives only in a comment: the one match of `pattern` (a regex with
    a number group) in the file. Raises if it matches nothing or more than once."""
    text = INTERFACE.read_text(encoding="utf-8")
    found = [m for m in re.finditer(pattern, text)]
    if len(found) != 1:
        raise ValueError(f"interface.yaml: {len(found)} matches for {pattern!r}")
    return float(found[0].group(group))


# comment-only sizes in interface.yaml mechanical.main (each pattern quotes its comment)
def usb_len() -> float:          # usb_c.shell: "length 7.35 into the board"
    return comment_number(r"length ([\d.]+) into the board")


def j7_body() -> tuple[float, float, float]:   # fpc.mouth_y: "body 15.5 wide x 5.4 deep x 2.0 high"
    return tuple(comment_number(r"body ([\d.]+) wide x ([\d.]+) deep x ([\d.]+) high", g) for g in (1, 2, 3))


def led_body_h() -> float:       # leds.face_y: "body 4.0 x 1.6 x 2.0 high"
    return comment_number(r"body [\d.]+ x [\d.]+ x ([\d.]+) high")


def module_h() -> float:         # antenna.module_body: "18 x 25.5, 3.1 high"
    return comment_number(r"module_body: .*# [\d.]+ x [\d.]+, ([\d.]+) high")


def sw_body_h() -> float:        # button.actuator_center_z: "body 4.5 x 3.4, 3.3 high"
    return comment_number(r"body [\d.]+ x [\d.]+, ([\d.]+) high")


def connector_h(key: str, board: str = "main") -> float:
    """Height of a connector's body, from the comment on its `body:` line (`key`: the connector's
    entry under mechanical.<board>, e.g. "j_sen66", or "qwiic" on the tongue)."""
    body = (MAIN if board == "main" else TONGUE)[key]["body"]
    lo, hi = body
    pat = (r"body: \[\[" + re.escape(f"{lo[0]}") + r", " + re.escape(f"{lo[1]}") + r"\], \["
           + re.escape(f"{hi[0]}") + r", " + re.escape(f"{hi[1]}") + r"\]\]\s*# ([\d.]+) high")
    return comment_number(pat)


# --- layout.yaml parts (U2, U4) ---------------------------------------------------------------

@lru_cache(maxsize=1)
def _placements() -> dict:
    import yaml
    return yaml.safe_load((LAYOUT_MAIN / "layout.yaml").read_text(encoding="utf-8"))["placement"]


@lru_cache(maxsize=None)
def _symbol(ref: str) -> str:
    """The part's symbol name from the schematic sources (hardware/src/main/*.yaml)."""
    import yaml
    for f in sorted(LAYOUT_MAIN.glob("*.yaml")):
        if f.name == "layout.yaml":
            continue
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        part = (data.get("parts") or {}).get(ref)
        if part and "symbol" in part:
            return part["symbol"].split(":", 1)[1]
    raise KeyError(f"no symbol for {ref}")


@lru_cache(maxsize=None)
def _footprint(symbol: str) -> str:
    text = (KICAD_LIB / "airq.kicad_sym").read_text(encoding="utf-8")
    i = text.index(f'(symbol "{symbol}"')
    m = re.search(r'"Footprint"\s*"airq:([^"]+)"', text[i:])
    return m.group(1)


@lru_cache(maxsize=None)
def courtyard(footprint: str) -> tuple[tuple[float, float], tuple[float, float]]:
    """The footprint's F.CrtYd box ((x0, y0), (x1, y1)) in its own frame (KiCad, +y down)."""
    text = (KICAD_LIB / "airq.pretty" / f"{footprint}.kicad_mod").read_text(encoding="utf-8")
    pts = [(float(a), float(b)) for line in text.splitlines() if "F.CrtYd" in line
           for a, b in re.findall(r"\((?:start|end) ([-\d.]+) ([-\d.]+)\)", line)]
    if not pts:
        raise ValueError(f"{footprint}: no courtyard")
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys)), (max(xs), max(ys))


def layout_part(ref: str) -> dict:
    """A main-board part from layout.yaml: centre (x, y) and rotation in the layout frame (the
    interface.yaml frame: origin top-left, +Y toward the front edge), and its courtyard box in
    that frame ((x0, y0), (x1, y1)), turned by the rotation (multiples of 90 deg)."""
    at = _placements()[ref]
    at = at["at"] if isinstance(at, dict) else at
    x, y, rot = at
    (cx0, cy0), (cx1, cy1) = courtyard(_footprint(_symbol(ref)))
    if round(rot) % 180 == 90:
        cx0, cy0, cx1, cy1 = cy0, cx0, cy1, cx1
    return {"center": (x, y), "rotation": rot, "footprint": _footprint(_symbol(ref)),
            "box": ((x + cx0, y + cy0), (x + cx1, y + cy1))}
