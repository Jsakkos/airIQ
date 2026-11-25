"""Make tools/hw importable (the checkers are plain scripts, not a package), and share fixtures."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "hw"))

FIXTURE_LIB = Path(__file__).resolve().parent / "fixtures" / "lib"


@pytest.fixture
def libs():
    """The hand-written test library `test` (symbols R, U6, QUAD, GND, VCC, PWR_FLAG)."""
    from kicad_lib import Libraries
    return Libraries({"test": FIXTURE_LIB / "test.kicad_sym"}, {"test": FIXTURE_LIB / "test.pretty"})


@pytest.fixture
def make_design(tmp_path):
    """Build a Design from {sheet name: [PartSrc, ...]} without YAML files."""
    from design import Design, SheetSrc

    def make(sheets: dict, power=None, layout=None, name="tp"):
        src = tmp_path / "hardware" / "src" / name
        return Design(
            name=name, title="Test board", company="", rev="1",
            sheets=[SheetSrc(n, f"{n} sheet", "A4", parts, src / f"{n}.yaml")
                    for n, parts in sheets.items()],
            power_symbols=power if power is not None else {"GND": "test:GND", "VCC": "test:VCC"},
            symbol_libs={}, footprint_libs={}, out_dir=tmp_path / "out", erc_severities={},
            layout=layout or {}, src_dir=src)
    return make
