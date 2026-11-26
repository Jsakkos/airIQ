"""Shared by the routing scripts in this folder: write board-owned items (tracks, vias, rule areas, pours)
into a .kicad_pcb file as text, and remove the items a script wrote on an earlier run.

Every script owns a uuid5 namespace; each item it writes gets the uuid `uuid5(namespace, "<tag>/<n>")`, so
a re-run first strips exactly its own items (and nothing drawn in KiCad or by another script) and then
writes them again. Coordinates are mm from the board's top-left corner; the board origin is the page
point (100, 100) (layout.yaml `board.origin`).

Not part of the build: tools/hw/build.py never imports this folder (hardware/README.md, "How it was routed").
"""
import math
import re
import uuid

OX, OY = 100.0, 100.0
MAX_ITEMS = 5000


def f(v: float) -> str:
    return f"{round(v, 4):g}"


def circle(cx: float, cy: float, r: float, n: int = 24):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def poly(pts) -> str:
    return " ".join(f"(xy {f(OX + x)} {f(OY + y)})" for x, y in pts)


class Items:
    """The items one script writes, in order; `save` replaces the ones it wrote before."""

    def __init__(self, namespace: str, tag: str):
        self.ns, self.tag = uuid.UUID(namespace), tag
        self.items: list[str] = []

    def _uid(self) -> str:
        return str(uuid.uuid5(self.ns, f"{self.tag}/{len(self.items) + 1}"))

    def track(self, net: str, pts, w: float = 0.2, layer: str = "F.Cu") -> None:
        """A polyline of segments through `pts` (repeated points are skipped: no zero-length segments)."""
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if f(x0) == f(x1) and f(y0) == f(y1):
                continue
            self.items.append(f'\t(segment (start {f(OX + x0)} {f(OY + y0)}) (end {f(OX + x1)} {f(OY + y1)}) '
                              f'(width {w}) (layer "{layer}") (net "{net}") (uuid "{self._uid()}"))')

    def via(self, net: str, x: float, y: float) -> None:
        """A 0.6 / 0.3 mm through via (layout.yaml Default net class)."""
        self.items.append(f'\t(via (at {f(OX + x)} {f(OY + y)}) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") '
                          f'(net "{net}") (uuid "{self._uid()}"))')

    def keepout(self, name: str, pts, layers=("F.Cu", "B.Cu"), tracks=False, vias=False, pads=True,
                pour=False, footprints=True) -> None:
        """A rule area (keep-out): each flag says whether that kind of item is allowed inside."""
        yn = lambda ok: "allowed" if ok else "not_allowed"  # noqa: E731
        lay = " ".join(f'"{layer}"' for layer in layers)
        self.items.append(f"""\t(zone (layers {lay}) (uuid "{self._uid()}") (name "{name}")
\t\t(hatch edge 0.5) (connect_pads (clearance 0)) (min_thickness 0.25) (filled_areas_thickness no)
\t\t(keepout (tracks {yn(tracks)}) (vias {yn(vias)}) (pads {yn(pads)}) (copperpour {yn(pour)}) (footprints {yn(footprints)}))
\t\t(placement (enabled no) (sheetname ""))
\t\t(fill (thermal_gap 0.5) (thermal_bridge_width 0.5))
\t\t(polygon (pts {poly(pts)})))""")

    def pour(self, net: str, layer: str, name: str, pts, clearance=0.2, thermal_gap=0.25,
             thermal_bridge=0.3, min_thickness=0.2) -> None:
        """A copper pour, unfilled (the build's DRC run fills it). Keeps every island (mode 0)."""
        self.items.append(f"""\t(zone (net "{net}") (layer "{layer}") (uuid "{self._uid()}") (name "{name}")
\t\t(hatch edge 0.5) (priority 0) (connect_pads (clearance {clearance})) (min_thickness {min_thickness})
\t\t(filled_areas_thickness no)
\t\t(fill yes (thermal_gap {thermal_gap}) (thermal_bridge_width {thermal_bridge}) (island_removal_mode 0)
\t\t\t(island_area_min 0.5))
\t\t(polygon (pts {poly(pts)})))""")

    def raw(self, template: str) -> None:
        """Any other item, written as given; `{uid}` in the text becomes its uuid."""
        self.items.append(template.replace("{uid}", self._uid()))

    def save(self, pcb: str) -> int:
        """Strip this script's earlier items from `pcb`, append the current ones, write the file back."""
        ours = {str(uuid.uuid5(self.ns, f"{self.tag}/{i}")) for i in range(1, MAX_ITEMS)}
        assert len(self.items) < MAX_ITEMS
        text = remove_items(open(pcb, encoding="utf-8").read(),
                            lambda item: (m := re.search(r'\(uuid "([^"]+)"\)', item)) is not None
                            and m.group(1) in ours)
        tail = text.rindex("(embedded_fonts no)")
        text = text[:tail] + "\n".join(self.items).lstrip("\t") + "\n\t" + text[tail:]
        open(pcb, "w", encoding="utf-8", newline="\n").write(text)
        return len(self.items)


def remove_items(text: str, drop) -> str:
    """Remove every top-level board item (an s-expression directly under `kicad_pcb`) for which
    `drop(item_text)` is true. A balanced-parenthesis scan that skips quoted strings."""
    cut, i, depth, start = [], 0, 0, None
    while i < len(text):
        ch = text[i]
        if ch == '"':
            i = text.index('"', i + 1) + 1
            continue
        if ch == "(":
            depth += 1
            if depth == 2:
                start = i
        elif ch == ")":
            if depth == 2 and start is not None:
                if drop(text[start:i + 1]):
                    cut.append((start, i + 1))
                start = None
            depth -= 1
        i += 1
    for a, b in reversed(cut):
        text = text[:a] + text[b:]
    return text
