from pathlib import Path

import pytest

from design import DesignError, load_design

PROJECT = """
project: tp
output: ../../kicad/tp
sheets: [a]
power_symbols: {GND: test:GND}
libraries:
  symbols: {test: ../../lib/test.kicad_sym}
"""
SHEET = """
title: Sheet A
parts:
  R1:
    symbol: test:R
    at: [25.4, 25.4]
    value: 10k
    footprint: test:R_TEST
    pins: [SIG, GND]
  U1:
    symbol: test:U6
    at: [50.8, 25.4]
    rot: 90
    mirror: y
    stub: 2.54
    fields: {Role: MCU}
    pins: {1: A, 2: B, 3: NC, 4: D, 5: E, 6: F}
"""


def _write(tmp_path: Path, project=PROJECT, sheet=SHEET, layout=None) -> Path:
    src = tmp_path / "hardware" / "src" / "tp"
    src.mkdir(parents=True)
    (src / "project.yaml").write_text(project, encoding="utf-8")
    (src / "a.yaml").write_text(sheet, encoding="utf-8")
    if layout is not None:
        (src / "layout.yaml").write_text(layout, encoding="utf-8")
    return src


def test_loads_parts_pins_and_paths(tmp_path):
    d = load_design(_write(tmp_path, layout="board: {width: 10, height: 5}\n"))
    r1, u1 = d.sheets[0].parts
    assert r1.pins == ["SIG", "GND"] and r1.value == "10k" and r1.at == (25.4, 25.4)
    assert u1.pins["1"] == "A" and u1.pins["3"] == "NC"  # YAML int keys become strings
    assert (u1.rot, u1.mirror, u1.stub, u1.fields) == (90, "y", 2.54, {"Role": "MCU"})
    assert d.symbol_libs["test"] == (tmp_path / "hardware" / "lib" / "test.kicad_sym").resolve()
    assert d.out_dir == (tmp_path / "hardware" / "kicad" / "tp").resolve()
    assert d.layout["board"]["width"] == 10
    assert d.rel(d.sheets[0].source) == "hardware/src/tp/a.yaml"


@pytest.mark.parametrize("edit,expected", [
    (("value: 10k", "valu: 10k"), "unknown key 'valu'"),
    (("rot: 90", "rot: 45"), "rot must be 0, 90, 180 or 270"),
    (("mirror: y", "mirror: z"), "mirror must be x or y"),
    (("stub: 2.54", "stub: -1"), "stub must be a length"),
    (("[SIG, GND]", "[SIG, NO]"), "is not a string"),           # YAML reads NO as False
    (("[SIG, GND]", "[SIG A, GND]"), "invalid net name 'SIG A'"),
    (("[SIG, GND]", "[a/b, GND]"), "invalid net name 'a/b'"),
    (("at: [25.4, 25.4]", "at: 25.4"), "expected [x, y]"),
])
def test_reports_spelling_and_type_problems(tmp_path, edit, expected):
    with pytest.raises(DesignError) as e:
        load_design(_write(tmp_path, sheet=SHEET.replace(*edit, 1)))
    assert any(expected in p for p in e.value.problems), e.value.problems


def test_reports_duplicate_reference_and_missing_project_keys(tmp_path):
    src = _write(tmp_path, project=PROJECT.replace("sheets: [a]", "sheets: [a, b]"))
    (src / "b.yaml").write_text(SHEET, encoding="utf-8")
    with pytest.raises(DesignError) as e:
        load_design(src)
    assert any("reference R1 is also used in a.yaml" in p for p in e.value.problems)
    with pytest.raises(DesignError) as e:
        load_design(_write(tmp_path / "x", project="project: tp\n"))
    assert {"project.yaml: missing `output`", "project.yaml: missing `sheets`"} <= set(e.value.problems)


def test_unknown_layout_key_is_reported(tmp_path):
    with pytest.raises(DesignError) as e:
        load_design(_write(tmp_path, layout="placment: {}\n"))
    assert any("unknown key 'placment'" in p for p in e.value.problems)


def test_polygon_outline_with_cutouts_loads(tmp_path):
    layout = "board:\n  outline: [[0, 0], [10, 0], [10, 5], [0, 5]]\n  cutouts: [[[1, 1], [2, 1], [2, 2]]]\n"
    assert load_design(_write(tmp_path, layout=layout)).layout["board"]["cutouts"][0][2] == [2, 2]


@pytest.mark.parametrize("board,expected", [
    ("{width: 10}", "board `width` and `height` must both be numbers"),
    ("{width: 10, height: 5, outline: [[0, 0], [1, 0], [1, 1]]}", "either `width` and `height` or `outline`"),
    ("{origin: [0, 0]}", "either `width` and `height` or `outline`"),
    ("{outline: [[0, 0], [1, 0]]}", "at least 3 [x, y] points"),
    ("{width: 10, height: 5, cutouts: [[[0, 0], [1, 0], 7]]}", "cutout 1 point 2"),
    ("{width: 10, height: 5, corners: 1}", "unknown key 'corners'"),
])
def test_board_shape_problems(tmp_path, board, expected):
    with pytest.raises(DesignError) as e:
        load_design(_write(tmp_path, layout=f"board: {board}\n"))
    assert any(expected in p for p in e.value.problems), e.value.problems


def test_dnp_must_be_a_boolean(tmp_path):
    sheet = SHEET.replace("pins: [SIG, GND]", "dnp: \"no\"\n    pins: [SIG, GND]", 1)
    with pytest.raises(DesignError) as e:
        load_design(_write(tmp_path, sheet=sheet))
    assert any("dnp must be true or false" in p for p in e.value.problems), e.value.problems
    sheet = SHEET.replace("pins: [SIG, GND]", "dnp: true\n    pins: [SIG, GND]", 1)
    assert load_design(_write(tmp_path / "ok", sheet=sheet)).sheets[0].parts[0].dnp is True


IFACE = """
signals: {SIG: GPIO6, BTN: GPIO9}
connectors:
  J_X: [GND, SIG, NC]
"""


def test_interface_is_loaded_from_the_project(tmp_path):
    src = _write(tmp_path, project=PROJECT + "interface: ../../interface.yaml\n")
    (tmp_path / "hardware" / "interface.yaml").write_text(IFACE, encoding="utf-8")
    d = load_design(src)
    assert d.interface["connectors"]["J_X"] == ["GND", "SIG", "NC"]
    assert d.interface["signals"]["BTN"] == "GPIO9"
    assert load_design(_write(tmp_path / "none")).interface is None   # optional


@pytest.mark.parametrize("iface,expected", [
    ("connectors: {J_X: GND}\n", "connectors.J_X must be a list"),
    ("connectors: {J_X: [GND, NO]}\n", "is not a string"),
    ("signals: {SIG: IO6}\n", "signals.SIG must be GPIO<n>"),
    ("- a\n", "expected a mapping"),
])
def test_interface_problems(tmp_path, iface, expected):
    src = _write(tmp_path, project=PROJECT + "interface: ../../interface.yaml\n")
    (tmp_path / "hardware" / "interface.yaml").write_text(iface, encoding="utf-8")
    with pytest.raises(DesignError) as e:
        load_design(src)
    assert any(expected in p for p in e.value.problems), e.value.problems
