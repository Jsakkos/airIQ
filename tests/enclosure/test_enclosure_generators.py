"""Enclosure generators and the committed reference designs, without SolidCraft.

The generators (enclosure/src/) are pure Python: these tests check what they emit (names,
parameters, values read from hardware/interface.yaml, datasheet numbers) and that the committed
.sc files under enclosure/reference/ are what the current generators build (their
document.json and embedded STEP files are read straight from the zip container), so CI catches
a stale design without running SolidCraft. Geometry is measured in test_enclosure_designs.py.
"""
import hashlib
import json
import math
import re
import zipfile

import pytest

import encbuild
import ref_epd
import ref_pcb
import ref_sen66
from sclib import ENCLOSURE, evaluate, interface, names_in

SCRIPTS = {name: encbuild.module(name).build() for name in encbuild.DESIGNS}
STEP_WRAPPERS = ("airq-main", "airq-tongue")
PARTS = [n for n in encbuild.DESIGNS if n not in STEP_WRAPPERS]

FEATURE_COMMANDS = {"solid.box", "solid.cylinder", "solid.extrude", "solid.revolve", "solid.fillet",
                    "solid.chamfer", "solid.shell", "solid.combine", "sketch.create", "file.insert_step"}
# fields that carry a size or a position: each must be a parameter expression (or 0)
SIZE_FIELDS = {"solid.box": ("corner", "length", "width", "height"),
               "solid.cylinder": ("base", "diameter", "height"),
               "solid.extrude": ("distance",), "solid.revolve": ("angle", "axis"),
               "solid.fillet": ("radius",), "solid.chamfer": ("distance",), "solid.shell": ("thickness",),
               "sketch.create": ("offset",),
               "sketch.line": ("points",), "sketch.circle.center": ("center", "diameter")}


def leaves(value):
    if isinstance(value, dict):
        value = value.get("origin", [])          # a revolve axis: its origin is a position
    if isinstance(value, (list, tuple)):
        for v in value:
            yield from leaves(v)
    else:
        yield value


def doc(name: str) -> dict:
    with zipfile.ZipFile(ENCLOSURE / encbuild.module(name).OUTPUT) as z:
        return json.loads(z.read("document.json"))


def values_with(script, **override) -> dict:
    """Parameter values with some changed and the derived ones recomputed in order."""
    vals = {}
    for name, p in script.params.items():
        if name in override:
            vals[name] = override[name]
        elif names_in(p.expression) and p.unit != "deg":
            vals[name] = evaluate(p.expression, vals)
        else:
            vals[name] = p.value
    return vals


# --- what the generators emit ------------------------------------------------------------

def test_component_names_are_the_plan_interfaces():
    """Plan 3 Task 1 'Produces': ref_sen66, ref_epd, ref_sfa40, ref_main, ref_tongue; R6 adds
    ref_fpc_adapter; Task 2 adds the coupons design. insert_design names the component after
    the design."""
    assert {encbuild.module(n).DESIGN for n in encbuild.DESIGNS} == {
        "ref_sen66", "ref_epd", "ref_sfa40", "ref_main", "ref_tongue", "ref_fpc_adapter", "coupons", "airq"}
    for name, s in SCRIPTS.items():
        assert s.commands[0] == {"command": "file.new", "params": {"name": encbuild.module(name).DESIGN}}
        assert encbuild.module(name).OUTPUT.startswith("reference/") == (name not in ("coupons", "airq"))


@pytest.mark.parametrize("name", list(encbuild.DESIGNS))
def test_every_feature_and_sketch_is_named_once(name):
    named = [c["params"].get("name") for c in SCRIPTS[name].commands if c["command"] in FEATURE_COMMANDS]
    assert named and all(named)
    assert len(named) == len(set(named))
    assert not [n for n in named if re.fullmatch(r"(Sketch|Body|Extrude|Box)\d+", n)]


@pytest.mark.parametrize("name", PARTS)
def test_every_size_is_a_parameter(name):
    s = SCRIPTS[name]
    for c in s.commands:
        for field in SIZE_FIELDS.get(c["command"], ()):
            for v in leaves(c["params"].get(field)):
                if isinstance(v, str):
                    assert names_in(v) and names_in(v) <= set(s.params), (c["params"].get("name"), field, v)
                else:
                    assert v == 0, f"{c['command']} {c['params'].get('name')}: {field} = {v} is not a parameter"


@pytest.mark.parametrize("name", PARTS)
def test_every_parameter_says_where_it_comes_from(name):
    adds = [c["params"] for c in SCRIPTS[name].commands if c["command"] == "parameters.add"]
    assert adds and all(a["comment"].strip() for a in adds)


@pytest.mark.parametrize("name", PARTS)
def test_every_body_is_named(name):
    expected = {
        "sen66": ["sen66_body", "sen66_inlet", "sen66_outlet"],
        "epd-2.9": ["epd_panel", "epd_active_area", "epd_tail_block", "epd_tail", "epd_tail_stiffener",
                    "epd_tail_contacts", "epd_tail_folded", "epd_tail_folded_stiffener",
                    "epd_tail_folded_contacts"],
        "sfa40-breakout": ["sfa40_board", "sfa40_sensor", "sfa40_opening", "sfa40_qwiic_j1", "sfa40_qwiic_j2"],
        "fpc-adapter": ["fpc_adapter_pcb", "fpc_adapter_zif_tail", "fpc_adapter_zif_ffc"],
        "coupons": ["coupon_clr_pegs", "coupon_clr_holes", "coupon_grille", "coupon_insert",
                    "coupon_flexure", "coupon_lg_body", "coupon_lg_bar_lit", "coupon_lg_bar_dark",
                    "coupon_lg_bar_dark_2"],
        "airq": ["shell", "base_plate", "zone_wall", "sen66_top_seal", "zone_seal", "sen66_foam", "gasket_out", "gasket_in", "sen66_pad", "hcho_lid",
                 "grommet_zone_a", "grommet_zone_b", "grommet_j4_a", "grommet_j4_b", "grommet_tongue_a", "grommet_tongue_b", "light_guide", "crease_seal", "led_mask", "orange_dot"],
    }[name]
    assert SCRIPTS[name].bodies == expected


def test_sen66_follows_the_datasheet():
    """SEN6x Datasheet v1.0 (Oct 2026), Figure 8; the plan's box is 55.2 x 25.6 x 21.3."""
    v = SCRIPTS["sen66"].v
    assert (v("L"), v("W"), v("H"), v("block_h"), v("plinth_inset")) == (55.2, 25.6, 21.3, 19.3, 1.2)
    assert (v("inlet_sq_x0"), v("inlet_sq_x1"), v("inlet_sq_y0"), v("inlet_sq_y1")) == (3.2, 10.2, 2.8, 9.8)
    assert (v("inlet_rd_x"), v("inlet_rd_y"), v("inlet_rd_d")) == (6.7, 18.2, 6.0)
    assert (v("outlet_x"), v("outlet_y"), v("outlet_d")) == (42.4, 12.8, 20.5)
    areas = ref_sen66.port_areas()
    assert areas["inlet"] == pytest.approx(49.0 + 9 * math.pi)
    assert areas["outlet"] == pytest.approx(math.pi * 10.25 ** 2)
    # Sensirion's minimum openings (SEN6x mechanical guide v0.92/v1.01, to confirm) are below
    # the drawn port areas
    assert areas["inlet"] > 56 and areas["outlet"] > 148


def test_epd_tail_is_read_from_interface_yaml():
    t = interface()["mechanical"]["main"]["fpc"]["panel_tail"]
    s = SCRIPTS["epd-2.9"]
    v = s.v
    assert v("tail_len") == t["length"] and v("tail_w") == t["width"] and v("tail_offset") == t["offset"]
    assert v("root_w") == t["root"]["width"] and v("root_from_end") == t["root"]["from_finger_end"]
    assert v("root_gap") == t["root"]["edge_gaps"][0]
    assert [v("contact_n"), v("contact_pitch"), v("contact_len")] == t["contacts"]
    assert v("stiff_len") == t["stiffener"]
    # the expressions carry the YAML numbers (nothing retyped into a feature)
    assert s.params["tail_len"].expression == f"{t['length']:g} mm"


def test_epd_tail_geometry_is_consistent():
    """The drawing's chain: root 10.97 + 15.31 + 10.42 = 36.70; narrow part 11.50 / 12.70 from
    the long edges; root 2.42 outside the glass; 8.2 mm can bend."""
    t = interface()["mechanical"]["main"]["fpc"]["panel_tail"]
    v = SCRIPTS["epd-2.9"].v
    assert v("root_gap") + v("root_w") + t["root"]["edge_gaps"][1] == pytest.approx(v("panel_w"))
    assert v("narrow_y0") == pytest.approx(11.50)
    assert v("panel_w") - v("narrow_y0") - v("tail_w") == pytest.approx(12.70)
    assert v("root_len") == pytest.approx(2.42)
    assert v("flare_x") == pytest.approx(4.84)
    assert v("flex_len") == pytest.approx(8.2)
    assert v("contact_span") == pytest.approx(12.0)
    # active area per the drawing: 3.00 from the far end, 3.82 from both long edges
    assert v("aa_x0") == pytest.approx(79.0 - 3.0 - 66.9)
    assert v("panel_w") - v("aa_edge") - v("aa_h") == pytest.approx(3.82)


@pytest.mark.parametrize("fold_r", [0.5, 1.0, 1.5])
@pytest.mark.parametrize("fold_out", [0.2, 0.5, 1.5])
def test_epd_fold_stays_valid_over_its_range(fold_r, fold_out):
    """Across the commented ranges the bend leaves flexible tail under the panel, and the
    folded leg with its stiffener stays below the panel's back (z < 0)."""
    vals = values_with(SCRIPTS["epd-2.9"], fold_r=fold_r, fold_out=fold_out)
    assert vals["fold_low"] > 0
    assert vals["fold_z"] + vals["stiff_t"] < 0


def test_epd_configuration_switches_the_tail_variants():
    s = SCRIPTS["epd-2.9"]
    steps = {c["command"]: c["params"] for c in s.commands if c["command"].startswith("config.")}
    assert steps["config.configure"]["params"] == ["tail_folded"]
    assert set(steps["config.configure"]["features"]) == set(ref_epd.FLAT + ref_epd.FOLDED)
    rows = {c["params"].get("rename", c["params"]["name"]): c["params"]["values"]
            for c in s.commands if c["command"] == "config.row"}
    assert rows["flat"]["param:tail_folded"] == "0" and rows["folded"]["param:tail_folded"] == "1"
    for f in ref_epd.FLAT:
        assert rows["flat"][f"suppress:{f}"] == "false" and rows["folded"][f"suppress:{f}"] == "true"
    for f in ref_epd.FOLDED:
        assert rows["flat"][f"suppress:{f}"] == "true" and rows["folded"][f"suppress:{f}"] == "false"
    drive = [r for r in steps["config.rule"]["rules"] if r["effect"]["type"] == "drive_suppression"]
    ids = {s.features[f]: f for f in ref_epd.FLAT + ref_epd.FOLDED}
    assert len(drive) == 2 * len(ids)
    for r in drive:
        folded = r["condition"]["expression"] == "1"
        assert r["effect"]["value"] == ((ids[r["effect"]["feature"]] in ref_epd.FLAT) == folded)
    assert steps["config.activate"] == {"row": "flat"}


def test_sfa40_and_adapter_take_shared_sizes_from_interface_yaml():
    body = interface()["mechanical"]["main"]["j_qwiic_tongue"]["body"]
    v = SCRIPTS["sfa40-breakout"].v
    assert (v("qwiic_w"), v("qwiic_d")) == pytest.approx((body[1][0] - body[0][0], body[1][1] - body[0][1]))
    # the opening lies on the cap, the cap on the sensor
    x0 = v("sensor_x + sensor_w / 2 - opening_gap - opening_w")
    assert v("sensor_x - cap_w / 2") <= x0 and x0 + v("opening_w") <= v("sensor_x + cap_w / 2")
    assert v("opening_l") <= v("cap_l") <= v("sensor_l")


def test_pcb_wrappers_import_the_board_step_files():
    for name in STEP_WRAPPERS:
        mod = encbuild.module(name)
        step = [c["params"] for c in SCRIPTS[name].commands if c["command"] == "file.insert_step"]
        assert len(step) == 1 and step[0]["path"].endswith(mod.STEP)
        assert (ref_pcb.STEP_DIR / mod.STEP).exists()


# --- the committed designs ---------------------------------------------------------------

@pytest.mark.parametrize("name", list(encbuild.DESIGNS))
def test_committed_design_is_light(name):
    """R8: a committed design stays at or under 5 MB; a larger one is built into enclosure/.build/."""
    path = ENCLOSURE / encbuild.module(name).OUTPUT
    assert path.exists(), f"{path} missing: run enclosure/build.py {name}"
    assert path.stat().st_size <= encbuild.COMMIT_LIMIT


@pytest.mark.parametrize("name", list(encbuild.DESIGNS))
def test_committed_design_is_what_the_generator_builds(name):
    """Parameters (expression and comment) and features (names, and ids where the generator
    counts them: the configuration rules use them) as in the committed .sc."""
    s, d = SCRIPTS[name], doc(name)
    assert d["name"] == encbuild.module(name).DESIGN
    assert [(p["name"], p["expr"], p.get("comment", "")) for p in d["params"]] == \
        [(p.name, p.expression, p.comment) for p in s.params.values()]
    built = {f["name"]: f["id"] for f in d["features"]}
    if name in STEP_WRAPPERS:
        assert list(built) == list(s.features)
    else:
        assert built == s.features


@pytest.mark.parametrize("name", STEP_WRAPPERS)
def test_committed_pcb_design_embeds_the_current_step(name):
    """The .sc holds its own copy of the STEP file: it must be today's hardware/step file (as
    git stores it, LF endings). Re-run enclosure/build.py after re-exporting the boards."""
    data = ref_pcb.canonical(encbuild.module(name).STEP)
    with zipfile.ZipFile(ENCLOSURE / encbuild.module(name).OUTPUT) as z:
        blobs = [n for n in z.namelist() if n.startswith("blobs/")]
        assert blobs == [f"blobs/{hashlib.sha256(data).hexdigest()}.step"]
        assert z.read(blobs[0]) == data
