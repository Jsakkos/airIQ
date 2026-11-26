import pytest

from design import DesignError, PartSrc
from gen_sch import generate_schematics, pin_end, resolve_design, to_sheet, to_sheet_angle
from kicad_lib import symbol_pins
from sexpr import atom, child, children, parse


# ---- geometry (the 12 rot/mirror combinations are checked against KiCad itself in
# test_kicad_pipeline.py; these pin the conventions down without KiCad) --------------------

@pytest.mark.parametrize("p,rot,mirror,expected", [
    ((1, 2), 0, None, (11, 18)),     # library Y up, page Y down
    ((1, 0), 90, None, (10, 19)),    # counter-clockwise: right turns up
    ((1, 0), 270, None, (10, 21)),
    ((1, 0), 180, None, (9, 20)),
    ((1, 0), 0, "y", (9, 20)),       # mirror y flips left/right
    ((0, 1), 0, "x", (10, 21)),      # mirror x flips top/bottom
    ((1, 0), 90, "x", (10, 21)),     # rotation first, then the mirror
    ((1, 0), 90, "y", (10, 19)),
])
def test_to_sheet(p, rot, mirror, expected):
    assert to_sheet(*p, (10, 20), rot, mirror) == expected


@pytest.mark.parametrize("angle,rot,mirror,expected", [
    (0, 0, None, 0), (0, 90, None, 90), (90, 90, None, 180), (0, 0, "y", 180),
    (90, 0, "x", 270), (0, 90, "x", 270), (180, 270, "x", 270), (180, 270, "y", 90),
])
def test_to_sheet_angle(angle, rot, mirror, expected):
    assert to_sheet_angle(angle, rot, mirror) == expected


# ---- generated files ---------------------------------------------------------------------

def _parts():
    return {
        "a": [PartSrc("R1", "test:R", (25.4, 50.8), value="10k", footprint="test:R_TEST",
                      lcsc="C1", pins=["SIG", "GND"]),
              PartSrc("U1", "test:U6", (76.2, 50.8), stub=2.54, fields={"Role": "MCU"},
                      pins={"1": "SIG", "2": "LOCAL", "3": "NC", "4": "VCC", "5": "LOCAL2",
                            "6": "GND"}),
              PartSrc("#FLG01", "test:PWR_FLAG", (101.6, 76.2), pins=["GND"])],
        "b": [PartSrc("R2", "test:R", (25.4, 50.8), footprint="test:R_TEST", pins=["SIG", "VCC"])],
    }


def _items(text: str, kind: str) -> list:
    return children(parse(text), kind)


def _xy(node) -> tuple[float, float]:
    at = child(node, "at")
    return float(at[1]), float(at[2])


def test_output_is_deterministic(make_design, libs):
    d = make_design(_parts())
    assert generate_schematics(d, libs) == generate_schematics(d, libs)
    assert set(generate_schematics(d, libs)) == {"tp.kicad_sch", "a.kicad_sch", "b.kicad_sch"}


def test_every_pin_ends_in_its_net_marker(make_design, libs):
    d = make_design(_parts())
    files = generate_schematics(d, libs)
    a = files["a.kicad_sch"]
    pins = {p.number: p for p in symbol_pins(libs.symbol("test:R"))}
    r1 = _parts()["a"][0]
    # SIG is used on sheets a and b: a global label exactly on R1 pin 1
    glob = {(str(g[1]), _xy(g)) for g in _items(a, "global_label")}
    assert ("SIG", pin_end(pins["1"], r1)) in glob
    # LOCAL is used on sheet a only: a local label, at the end of U1's 2.54 mm stub
    u1 = _parts()["a"][1]
    u_pins = {p.number: p for p in symbol_pins(libs.symbol("test:U6"))}
    x, y = pin_end(u_pins["2"], u1)
    labels = {(str(lb[1]), _xy(lb)) for lb in _items(a, "label")}
    assert ("LOCAL", (round(x - 2.54, 4), y)) in labels
    wires = [[tuple(float(v) for v in xy[1:]) for xy in children(child(w, "pts"), "xy")]
             for w in _items(a, "wire")]
    assert [(x, y), (round(x - 2.54, 4), y)] in wires
    # NC: a no-connect flag on the pin itself, no stub
    assert pin_end(u_pins["3"], u1) in {_xy(n) for n in _items(a, "no_connect")}


def test_power_nets_get_power_symbols_pointing_away_from_the_part(make_design, libs):
    files = generate_schematics(make_design(_parts()), libs)
    syms = _items(files["a.kicad_sch"], "symbol")
    power = {(atom(s, "lib_id"), _xy(s)): child(s, "at")[3] for s in syms
             if str(atom(s, "lib_id")) in ("test:GND", "test:VCC")}
    r1 = _parts()["a"][0]
    r_pins = {p.number: p for p in symbol_pins(libs.symbol("test:R"))}
    assert power[("test:GND", pin_end(r_pins["2"], r1))] == "0"      # bottom pin: GND hangs down
    u1 = _parts()["a"][1]
    u_pins = {p.number: p for p in symbol_pins(libs.symbol("test:U6"))}
    x, y = pin_end(u_pins["4"], u1)                                    # right side, 2.54 stub
    assert power[("test:VCC", (round(x + 2.54, 4), y))] == "270"                 # VCC turned to point right
    refs = [next(p[2] for p in children(s, "property") if p[1] == "Reference") for s in syms
            if str(atom(s, "lib_id")) in ("test:GND", "test:VCC")]
    assert len(refs) == len(set(refs)) == 4 and all(r.startswith("#PWR") for r in refs)


def test_instances_link_root_sheet_and_symbol(make_design, libs):
    files = generate_schematics(make_design(_parts()), libs)
    root = parse(files["tp.kicad_sch"])
    root_uuid = atom(root, "uuid")
    sheets = children(root, "sheet")
    assert [next(p[2] for p in children(s, "property") if p[1] == "Sheetfile") for s in sheets] \
        == ["a.kicad_sch", "b.kicad_sch"]
    a_uuid = atom(sheets[0], "uuid")
    r1 = next(s for s in _items(files["a.kicad_sch"], "symbol")
              if any(p[1] == "Reference" and p[2] == "R1" for p in children(s, "property")))
    path = child(child(child(r1, "instances"), "project"), "path")
    assert path[1] == f"/{root_uuid}/{a_uuid}" and atom(path, "reference") == "R1"
    props = {p[1]: p[2] for p in children(r1, "property")}
    assert props["Value"] == "10k" and props["Footprint"] == "test:R_TEST" and props["LCSC"] == "C1"
    lib_ids = [s[1] for s in children(child(parse(files["a.kicad_sch"]), "lib_symbols"), "symbol")]
    assert lib_ids == sorted(lib_ids) and "test:R" in lib_ids and "test:GND" in lib_ids


@pytest.mark.parametrize("part,expected", [
    (PartSrc("R9", "test:R", (25.4, 25.4), footprint="test:R_TEST", pins=["A"]),
     "pin 2 of test:R has no net"),
    (PartSrc("R9", "test:R", (25.4, 25.4), footprint="test:R_TEST", pins={"1": "A", "2": "B", "3": "C"}),
     "test:R has no pin 3"),
    (PartSrc("R9", "test:R", (25.4, 25.4), footprint="test:R_TEST", pins=["A", "B", "C"]),
     "test:R has no pin 3"),
    (PartSrc("R9", "test:R", (25.0, 25.4), footprint="test:R_TEST", pins=["A", "B"]),
     "off the 1.27 mm grid"),
    (PartSrc("R9", "test:R", (25.4, 25.4), pins=["A", "B"]), "no footprint"),
    (PartSrc("J9", "test:QUAD", (25.4, 25.4), pins=["A", "B"]), "not numbered 1..n"),
    (PartSrc("FLG", "test:PWR_FLAG", (25.4, 25.4), pins=["GND"]), "must start with '#'"),
    (PartSrc("#R9", "test:R", (25.4, 25.4), footprint="test:R_TEST", pins=["A", "B"]),
     "only power symbols"),
    (PartSrc("R9", "test:NOPE", (25.4, 25.4), pins=["A", "B"]), "not found"),
])
def test_resolve_reports_problems(make_design, libs, part, expected):
    with pytest.raises(DesignError) as e:
        resolve_design(make_design({"a": [part]}), libs)
    assert any(expected in p for p in e.value.problems), e.value.problems


def test_resolve_reports_pins_that_would_touch(make_design, libs):
    parts = [PartSrc("R1", "test:R", (25.4, 25.4), footprint="test:R_TEST", pins=["A", "B"]),
             PartSrc("R2", "test:R", (25.4, 33.02), footprint="test:R_TEST", pins=["C", "D"])]
    with pytest.raises(DesignError) as e:
        resolve_design(make_design({"a": parts}), libs)
    assert any("R2 pin 1 and R1 pin 2 meet" in p for p in e.value.problems), e.value.problems


# ---- pins by name, interface.yaml roles, stacked pins ---------------------------------------

IFACE = {"signals": {"I2C_SDA": "GPIO6", "BUTTON": "GPIO9"},
         "connectors": {"J_X": ["GND", "SIG", "NC", "VCC", "NC", "B"]}}


def _nets(make_design, libs, part, interface=IFACE):
    d = make_design({"a": [part]})
    d.interface = interface
    (pl,) = resolve_design(d, libs)
    return pl.nets


def test_pins_can_be_named_and_a_name_covers_every_pin_with_it(make_design, libs):
    part = PartSrc("U1", "test:MCU5", (50.8, 50.8),
                   pins={"GND": "GND", "IO6": "A", "IO9": "B", "EN": "EN", "7": "NC"})
    assert _nets(make_design, libs, part, None) == {"1": "GND", "5": "GND", "2": "A", "3": "B",
                                                     "4": "EN", "7": "NC"}


def test_mcu_signals_come_from_the_interface(make_design, libs):
    part = PartSrc("U1", "test:MCU5", (50.8, 50.8), fields={"Role": "MCU"},
                   pins={"GND": "GND", "EN": "EN", "7": "NC"})
    nets = _nets(make_design, libs, part)
    assert nets["2"] == "I2C_SDA" and nets["3"] == "BUTTON"


def test_role_connector_pins_come_from_the_interface(make_design, libs):
    part = PartSrc("J1", "test:U6", (50.8, 50.8), fields={"Role": "J_X"})
    assert _nets(make_design, libs, part) == {"1": "GND", "2": "SIG", "3": "NC", "4": "VCC",
                                              "5": "NC", "6": "B"}


@pytest.mark.parametrize("part,expected", [
    (PartSrc("J1", "test:U6", (50.8, 50.8), fields={"Role": "J_X"}, pins={"2": "SIG"}),
     "pin 2 gets a net from both"),
    (PartSrc("U1", "test:MCU5", (50.8, 50.8), fields={"Role": "MCU"},
             pins={"GND": "GND", "EN": "EN", "7": "NC", "IO6": "X"}),
     "pin 2 gets a net from both"),
    (PartSrc("U1", "test:MCU5", (50.8, 50.8), fields={"Role": "J_NOPE"},
             pins={"GND": "GND", "IO6": "A", "IO9": "B", "EN": "EN", "7": "NC"}),
     "Role J_NOPE is neither MCU nor a connector"),
    (PartSrc("J1", "test:R", (50.8, 50.8), footprint="test:R_TEST", fields={"Role": "J_X"}),
     "has no pin 3 for connectors.J_X"),
    (PartSrc("U1", "test:U6", (50.8, 50.8), fields={"Role": "MCU"},
             pins={"1": "A", "2": "B", "3": "C", "4": "D", "5": "E", "6": "F"}),
     "has no pin IO6 for signal I2C_SDA"),
    (PartSrc("U1", "test:MCU5", (50.8, 50.8),
             pins={"GND": "GND", "IO6": "A", "IO9": "B", "EN": "EN", "2": "X"}),
     "pin key 2 is ambiguous"),
    (PartSrc("U1", "test:MCU5", (50.8, 50.8),
             pins={"GND": "GND", "1": "GND", "IO6": "A", "IO9": "B", "EN": "EN", "7": "NC"}),
     "pin 1 gets a net from both"),
    (PartSrc("U1", "test:MCU5", (50.8, 50.8),
             pins={"1": "GND", "5": "VCC", "IO6": "A", "IO9": "B", "EN": "EN", "7": "NC"}),
     "U1 pin 5 and U1 pin 1 meet"),          # stacked pins must share their net
    (PartSrc("R9", "test:R", (25.4, 25.4), footprint="test:NOPE", pins=["A", "B"]),
     "footprint 'test:NOPE' not found"),
])
def test_role_and_name_problems(make_design, libs, part, expected):
    with pytest.raises(DesignError) as e:
        _nets(make_design, libs, part)
    assert any(expected in p for p in e.value.problems), e.value.problems


def test_a_role_without_interface_needs_every_pin_in_the_sheet(make_design, libs):
    part = PartSrc("J1", "test:U6", (50.8, 50.8), fields={"Role": "J_X"})
    with pytest.raises(DesignError) as e:
        _nets(make_design, libs, part, None)
    assert any("pin 1 of test:U6 has no net" in p for p in e.value.problems), e.value.problems


def test_stacked_pins_share_one_marker(make_design, libs):
    part = PartSrc("U1", "test:MCU5", (50.8, 50.8),
                   pins={"GND": "GND", "IO6": "A", "IO9": "B", "EN": "EN", "7": "NC"})
    sheet = parse(generate_schematics(make_design({"a": [part]}), libs)["a.kicad_sch"])
    gnd = [s for s in children(sheet, "symbol") if str(atom(s, "lib_id")) == "test:GND"]
    assert len(gnd) == 1     # pins 1 and 5 sit on one point: one GND symbol
