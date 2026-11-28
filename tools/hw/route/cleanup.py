"""Main board, routing clean-up between steps (plain Python on the board file).

    uv run python tools/hw/route/cleanup.py dangling BOARD build/main-drc.json   # prints the count removed
    uv run python tools/hw/route/cleanup.py narrow BOARD 0.15
    uv run python tools/hw/route/cleanup.py unroute BOARD
    uv run python tools/hw/route/cleanup.py unrouted build/main-drc.json            # prints a count
    uv run python tools/hw/route/cleanup.py drop-dangling-vias build/main-drc.json VIAS.txt

- `dangling`: deletes the non-GND vias and track stubs that the last DRC report (build.py writes
  build/main-drc.json) lists as dangling (Freerouting leaves a few connected on one side only).
- `narrow`: deletes track segments narrower than a width (Freerouting's neck-downs below the board
  minimum); a second Freerouting pass routes those connections again.
- `unroute`: deletes every track, via and copper pour or rule area, giving the placed but unrouted board
  that route_main.sh starts from (a rebuild afterwards puts it in normal form).
- `unrouted`: the number of connections the DRC report lists as unrouted, ground (poured) ones excepted.
- `drop-dangling-vias`: removes from a stitch.py via list (x,y pairs) the GND vias the DRC report lists as
  dangling (no pour reached them), so main_pour.py can write the list again without them.

Not part of the build.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from boarditems import remove_items  # noqa: E402


def _rewrite(pcb: str, drop) -> int:
    text = open(pcb, encoding="utf-8").read()
    count = [0]

    def counted(item: str) -> bool:
        hit = drop(item)
        count[0] += hit
        return hit

    text = remove_items(text, counted)
    open(pcb, "w", encoding="utf-8", newline="\n").write(text)
    return count[0]


def dangling(pcb: str, drc: str) -> int:
    report = json.load(open(drc, encoding="utf-8"))
    dead = {i["uuid"] for v in report["violations"] if v["type"] in ("via_dangling", "track_dangling")
            for i in v["items"] if "[GND]" not in i["description"]}

    def drop(item: str) -> bool:
        m = re.search(r'\(uuid "([^"]+)"\)', item)
        return bool(m) and m.group(1) in dead and item.startswith(("(via", "(segment"))

    return _rewrite(pcb, drop)


def narrow(pcb: str, width: float) -> int:
    def drop(item: str) -> bool:
        m = re.search(r"\(width ([\d.]+)\)", item)
        return item.startswith("(segment") and bool(m) and float(m.group(1)) < width - 1e-6

    return _rewrite(pcb, drop)


def unroute(pcb: str) -> int:
    return _rewrite(pcb, lambda item: item.startswith(("(segment", "(via", "(arc", "(zone")))


def unrouted(drc: str) -> int:
    report = json.load(open(drc, encoding="utf-8"))
    return sum(1 for v in report.get("unconnected_items", [])
               if not all("[GND]" in i["description"] for i in v["items"]))


def drop_dangling_vias(drc: str, vias_txt: str) -> tuple[int, int]:
    report = json.load(open(drc, encoding="utf-8"))
    bad = {(round(i["pos"]["x"] - 100, 2), round(i["pos"]["y"] - 100, 2)) for v in report["violations"]
           if v["type"] == "via_dangling" for i in v["items"] if "[GND]" in i["description"]}
    vias = [tuple(float(c) for c in s.split(",")) for s in open(vias_txt).read().split()]
    keep = [v for v in vias if (round(v[0], 2), round(v[1], 2)) not in bad]
    open(vias_txt, "w").write(" ".join(f"{x},{y}" for x, y in keep))
    return len(keep), len(vias) - len(keep)


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[0] == "dangling":
        print(dangling(argv[1], argv[2]))
    elif len(argv) == 3 and argv[0] == "narrow":
        print(f"narrow segments removed: {narrow(argv[1], float(argv[2]))}")
    elif len(argv) == 2 and argv[0] == "unroute":
        print(f"routing items removed: {unroute(argv[1])}")
    elif len(argv) == 2 and argv[0] == "unrouted":
        print(unrouted(argv[1]))
    elif len(argv) == 3 and argv[0] == "drop-dangling-vias":
        kept, dropped = drop_dangling_vias(argv[1], argv[2])
        print(f"stitching vias: {kept} kept, {dropped} dangling dropped")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
