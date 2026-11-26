"""The airQ check design: enclosure/airq.sc with every reference part placed (Task 3a Step 3).

`check_script()` returns a command script for `solidcraft-cli run --in enclosure/airq.sc`. It:
- inserts the six references at their places in the layout. ref_main goes only here (R8: it
  adds 5.5 MB);
- runs the interference check (R9: touching is fine, shared volume is not);
- measures the bodies;
- saves enclosure/.build/airq-check.sc.

The placement matrices are rigid and proper (det +1). Their translations are parameter
expressions, so the references follow the design's parameters. `distances()` gives the
distances that the placements answer, from the generator's values. Run it all with
`uv run --with pyyaml python enclosure/src/airq_check.py`, or through
tests/enclosure/test_airq.py.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import airq
import encbuild
from sclib import ENCLOSURE, mechanical

REF = ENCLOSURE / "reference"
CHECK_SC = encbuild.BUILD_DIR / "airq-check.sc"


def _rows(rot, t):
    """A 3x4 matrix from a 3x3 rotation (rows) and a translation of expressions."""
    return [[*rot[i], t[i]] for i in range(3)]


def placements(s=None) -> list[dict]:
    """insert_design steps for the references, placed by the design's parameters."""
    s = s or airq.build()
    c, sn = s.v("cos_t"), s.v("sin_t")
    slope = lambda sx, tx: (f"({sx}) * sin_t + ({tx}) * cos_t", f"lip + ({sx}) * cos_t - ({tx}) * sin_t")  # noqa: E731
    epd_y, epd_z = slope("panel_s0", "bezel + panel_t")
    ad_y, ad_z = slope("adapter_s", "adapter_t")
    return [
        # SEN66: module x -> +x (inlet end left), module z (port face -> connector) -> +y, module y -> -z
        {"path": REF / "sen66.sc", "matrix": _rows([[1, 0, 0], [0, 0, 1], [0, -1, 0]], ["sen_x0", "sen_y0", "sen_top"])},
        # panel: x -> +x (tail end left), y -> up the slope, z -> the slope's outward normal; tail folded
        {"path": REF / "epd-2.9.sc", "configuration": "folded",
         "matrix": _rows([[1, 0, 0], [0, sn, -c], [0, c, sn]], ["panel_x0", epd_y, epd_z])},
        # adapter: its y (signal path) -> +x, its z (ZIFs) -> toward the panel, x -> down the slope
        {"path": REF / "fpc-adapter.sc", "matrix": _rows([[0, 1, 0], [-sn, 0, -c], [-c, 0, sn]], ["adapter_x", ad_y, ad_z])},
        # SFA40: standing, its opening (+z) facing the rear wall, its board's y -> -z
        {"path": REF / "sfa40-breakout.sc", "matrix": _rows([[1, 0, 0], [0, 0, 1], [0, -1, 0]], ["sfa_x0", "sfa_y0", "sfa_z0"])},
        # tongue: turned 180 deg about z, its front edge (VEML7700) toward the lip
        {"path": REF / "airq-tongue.sc", "matrix": _rows([[-1, 0, 0], [0, -1, 0], [0, 0, 1]], ["tongue_x1", "tongue_y0", "tongue_z0"])},
        # main board: STEP frame as it lies (front edge at STEP y -30)
        {"path": REF / "airq-main.sc", "matrix": _rows([[1, 0, 0], [0, 1, 0], [0, 0, 1]], ["board_x0", "board_y0 + board_d", "board_z0"])},
    ]


def check_script(save: Path = CHECK_SC, budget_s: float = 600) -> dict:
    steps = []
    for pl in placements():
        params = {"path": str(pl["path"]), "matrix": pl["matrix"]}
        if "configuration" in pl:
            params["configuration"] = pl["configuration"]
        steps.append({"command": "component.insert_design", "params": params})
    # a reference's own bodies may overlap inside its STEP model (pins in housings): only pairs
    # with at least one enclosure body, or between two references, count
    own = [[f"{n}:1", f"{n}:1"] for n in ("ref_sen66", "ref_epd", "ref_fpc_adapter", "ref_sfa40", "ref_tongue", "ref_main")]
    steps += [{"command": "inspect.interference", "params": {"budget_s": budget_s, "exclude_pairs": own}},
              {"command": "inspect.measure", "params": {"summary": True}},
              {"command": "file.save", "params": {"path": str(save), "cache": False}}]
    return {"commands": steps}


def run(cli: str | None = None) -> dict:
    """Build the check design and return {interference, measure} (the run's results)."""
    cli = cli or encbuild.cli_path()
    encbuild.BUILD_DIR.mkdir(parents=True, exist_ok=True)
    script = encbuild.BUILD_DIR / "airq-check.json"
    script.write_text(json.dumps(check_script(), indent=1), encoding="utf-8")
    out = encbuild.BUILD_DIR / "airq-check.results.json"
    out.unlink(missing_ok=True)
    proc = subprocess.run([cli, "run", str(script), "--in", str(ENCLOSURE / airq.OUTPUT), "--results", "--quiet",
                           "--json-out", str(out)], capture_output=True, text=True)
    res = json.loads(out.read_text(encoding="utf-8")) if out.exists() else None
    if proc.returncode != 0 or not isinstance(res, list):
        raise RuntimeError(f"check run failed: {res if isinstance(res, dict) else proc.stderr or proc.stdout}")
    return {"inserted": res[:6], "interference": res[6], "measure": res[7]}


def _box_gap(a, b) -> float:
    return math.sqrt(sum(max(0.0, lo2 - hi1, lo1 - hi2) ** 2 for (lo1, hi1), (lo2, hi2) in zip(a, b)))


def distances(s=None) -> dict:
    """The distances 3a's placements answer, from the design's values and interface.yaml."""
    s = s or airq.build()
    v = s.v
    m = mechanical("main")
    x0, y_front, z_top = v("board_x0"), v("board_y0"), v("board_z0") + v("board_t")
    dev = lambda X, Y: (x0 + X, y_front + v("board_d") - Y)       # noqa: E731  layout (X, Y) -> device (x, y)
    mod = m["antenna"]["module_body"]
    ant = ((x0 + mod[0][0], x0 + mod[1][0]), tuple(sorted((dev(0, 0)[1], dev(0, mod[0][1])[1]))), (z_top, z_top + 3.1))
    u3 = ((x0 + mod[0][0], x0 + mod[1][0]), tuple(sorted((dev(0, mod[0][1])[1], dev(0, mod[1][1])[1]))), (z_top, z_top + 3.1))
    u2x, u2y = dev(24.6, 3.4)
    u2 = ((u2x - 1.5, u2x + 1.5), (u2y - 1.5, u2y + 1.5), (z_top, z_top + 1.0))       # TPS562201 SOT-23-6, about 3 x 3
    sen = ((v("sen_x0"), v("sen_x0") + v("sen_l")), (v("sen_y0"), v("sen_y0") + v("sen_d")), (v("floor_t") + v("foam"), v("sen_top")))
    tx1, ty0, tz0 = v("tongue_x1"), v("tongue_y0"), v("tongue_z0")
    tongue = ((tx1 - v("tongue_w"), tx1), (ty0, ty0 + v("tongue_dp")), (tz0, tz0 + v("tongue_t") + 3.0))
    usb_x = v("usb_x")
    plug = ((usb_x - 6.25, usb_x + 6.25), (dev(0, 0)[1], v("D") + 20.0), (v("usb_z") - 3.5, v("usb_z") + 3.5))   # 12.5 x 7 overmold out the rear
    r = v("boss_d") / 2
    bosses = [((x - r, x + r), (y - r, y + r), (v("floor_t") - v("head_depth"), v("floor_t") + v("boss_h")))
              for x, y in ((-v("inner_x") + r - 0.5, v("wall") + 3.0), (v("inner_x") - r + 0.5, v("wall") + 3.0))]
    rz = v("H") - v("wall") - r + 0.5           # the rear boss, screwed from the rear
    bosses.append(((-v("inner_x") + r - 0.5 - r, -v("inner_x") + r - 0.5 + r), (v("D") - v("wall") - 6.2, v("D")),
                   (rz - r, rz + r)))
    sfa = ((v("sfa_x0"), v("sfa_x0") + 25.4), (v("sfa_y0"), v("sfa_y0") + 4.5), (v("sfa_z0"), v("sfa_z0") + 25.4))
    h1 = (v("h1_x"), v("h1_y"))
    j1 = ((usb_x - 8.94 / 2, usb_x + 8.94 / 2), tuple(sorted((dev(0, 0)[1], dev(0, 7.35)[1]))))
    h1_to_j1_edge = math.hypot(max(0.0, j1[0][0] - h1[0], h1[0] - j1[0][1]), max(0.0, j1[1][0] - h1[1], h1[1] - j1[1][1]))
    return {
        "antenna_to_sen66": _box_gap(ant, sen),
        "antenna_to_usb_plug": _box_gap(ant, plug),
        "antenna_to_bosses_and_screws": min(_box_gap(ant, b) for b in bosses),
        "antenna_to_standoff_screws": min(_box_gap(ant, ((x - 1, x + 1), (y - 1, y + 1), (z_top - 6, z_top + 2)))
                                          for x, y in ((v("h1_x"), v("h1_y")), (v("h2_x"), v("h2_y")))),
        "antenna_to_sfa40": _box_gap(ant, sfa),
        "tongue_to_u3": _box_gap(tongue, u3),
        "tongue_to_u2": _box_gap(tongue, u2),
        "h1_to_usb_c_shell": h1_to_j1_edge,
        "h1_to_usb_c_centre": math.hypot(h1[0] - usb_x, h1[1] - dev(0, 7.35 / 2)[1]),
        "antenna_end_to_rear_wall": (v("D") - v("wall")) - dev(0, mod[0][1])[1],
        "hcho_grille_open_mm2": 4 * v("slot_w") * v("hcho_slot_h"),
        "hcho_grille_lower_edge_z": v("grille_min_z") + 1.0,
    }


def insertion_probe(s=None) -> list[str]:
    """I1: the shell is lowered onto the assembled base along -z (R24). Everything of the shell
    below the zone wall's top must pass the zone wall through a notch, and no part of the shell
    may pass through the board's footprint below the board's top. Returns the conflicts (none
    when it assembles). The rear boss sits above the board's parts and left of the board."""
    s = s or airq.build()
    v = s.v
    out = []
    r = v("boss_d") / 2
    board = ((v("board_x0"), v("board_x0") + v("board_w")), (v("board_y0"), v("board_y0") + v("board_d") + v("antenna_out")))
    for i, (x, y) in enumerate(((-v("inner_x") + r - 0.5, v("wall") + 3.0), (v("inner_x") - r + 0.5, v("wall") + 3.0)), 1):
        notch = s.commands[[c["params"].get("name") for c in s.commands].index(f"Zone wall boss notch {i}")]["params"]
        nx0, ny0 = v(notch["corner"][0]), v(notch["corner"][1])
        nx1, ny1 = nx0 + v(notch["length"]), ny0 + v(notch["width"])
        if not (nx0 <= x - r and x + r <= nx1 and ny0 <= y - r and y + r <= ny1):
            out.append(f"floor boss {i} does not pass the zone wall's notch")
        if board[0][0] < x + r and x - r < board[0][1] and board[1][0] < y + r and y - r < board[1][1]:
            out.append(f"floor boss {i} passes through the board's footprint")
    rx, rz = -v("inner_x") + r - 0.5, v("H") - v("wall") - r + 0.5
    if rx + r > board[0][0] and rz - r < v("board_z0") + v("board_t") + 4.25:
        out.append("rear boss passes the board")
    return out


if __name__ == "__main__":
    d = distances()
    print(json.dumps({k: round(x, 2) for k, x in d.items()}, indent=1))
    print("insertion probe:", insertion_probe() or "clear")
    if "--run" in sys.argv:
        r = run()
        i = r["interference"]
        print("interference: count", i["count"], "checked", i["checked"], "unchecked", len(i["unchecked"]),
              "pairs", i["pairs_candidate"], i["pairs_intersected"])
        for pair in i["interferences"][:30]:
            print("  ", pair["a"], "|", pair["b"], round(pair["volume_mm3"], 3), [round(c, 2) for c in pair["center"]])
        for u in i["unchecked"][:10]:
            print("  unchecked", u)
