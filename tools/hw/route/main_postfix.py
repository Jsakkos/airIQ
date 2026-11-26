"""Main board, routing step 2b: hand fixes on Freerouting's result (route_main.sh runs it after the
clean-up, before the pours), like edits made in KiCad after an autorouter pass.

    uv run python tools/hw/route/main_postfix.py hardware/kicad/main/airq-main.kicad_pcb

THIS SCRIPT HARD-CODES THE CURRENT MAIN-BOARD LAYOUT (coordinates: mm from the board's top-left corner).

- USB D+ through the ESD part U1: the line must run contact -> U1 pin 6 -> U1 pin 1 -> module. Pins 6 and
  1 are one net, so Freerouting joins them, and in the committed routing it did so round the part (a via
  west of U1 and a track into pin 1), which leaves the contact side wired to the module past the part.
  Every USB_DP / USB_DN item west of U1 between its pin rows (x < 15.0, y 12.2 .. 14.2: only such a
  bypass can be there) is removed and pins 6 and 1 are joined straight under U1, as D- pins 4 and 3 are.
- C7's +5V link crossed under U1 on the top layer (main_preroute.py), where that D+ link runs; it now
  crosses on B.Cu: a via beside U1 and a B.Cu track to U1's VBUS via.
Checked by tests/hardware/test_main_board.py (test_usb_contacts_go_through_the_esd_part). Re-runnable:
it removes what it wrote before (uuid5 namespace below). Not part of the build.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boarditems import OX, OY, Items, remove_items  # noqa: E402

BYPASS_BOX = (11.0, 12.2, 15.0, 14.2)          # west of U1's pin column, between its pin rows
C7_TOP_CROSSING = ((13.48, 13.0), (16.2, 13.0))


def _xy(item: str, key: str):
    m = re.search(r"\(" + key + r" ([-\d.]+) ([-\d.]+)", item)
    return (round(float(m.group(1)) - OX, 3), round(float(m.group(2)) - OY, 3)) if m else None


def _in_box(p) -> bool:
    x0, y0, x1, y1 = BYPASS_BOX
    return p is not None and x0 <= p[0] <= x1 and y0 <= p[1] <= y1


def _drop(item: str) -> bool:
    net = re.search(r'\(net "([^"]*)"\)', item)
    net = net.group(1) if net else ""
    if item.startswith("(via") and net in ("USB_DP", "USB_DN"):
        return _in_box(_xy(item, "at"))
    if item.startswith("(segment"):
        ends = [_xy(item, "start"), _xy(item, "end")]
        if net in ("USB_DP", "USB_DN"):
            return any(_in_box(p) for p in ends)
        if net == "+5V" and '(layer "F.Cu")' in item:
            return sorted(ends) == sorted(C7_TOP_CROSSING)
    return False


def main(argv: list[str]) -> int:
    pcb = argv[0]
    text = open(pcb, encoding="utf-8").read()
    n = [0]

    def counted(item: str) -> bool:
        hit = _drop(item)
        n[0] += hit
        return hit

    open(pcb, "w", encoding="utf-8", newline="\n").write(remove_items(text, counted))
    out = Items("9e3c5d1a-7b2f-4c8e-a6d4-1f0b2e3c4d5a", "main-postfix")
    out.track("USB_DP", [(15.25, 11.85), (15.25, 14.15)])                     # U1 pin 6 -> pin 1
    out.via("+5V", 13.48, 13.0)
    out.track("+5V", [C7_TOP_CROSSING[0], C7_TOP_CROSSING[1]], 0.4, "B.Cu")
    print(f"removed {n[0]} items, wrote {out.save(pcb)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
