import json
import shutil

from conftest import FIXTURE_LIB
from design import PartSrc
from gen_project import DRC_ERRORS, ERC_ERRORS, kicad_dru, kicad_pro, lib_tables
from gen_sch import resolve_design
from kicad_lib import Libraries


def test_lib_tables_list_used_libraries_only(make_design, tmp_path):
    stock = tmp_path / "stock-footprints" / "Resistor_SMD.pretty"   # stands in for KiCad's folder
    stock.mkdir(parents=True)
    shutil.copy(FIXTURE_LIB / "test.pretty" / "R_TEST.kicad_mod", stock / "R_0402_1005Metric.kicad_mod")
    libs = Libraries({"test": FIXTURE_LIB / "test.kicad_sym"}, {"test": FIXTURE_LIB / "test.pretty"},
                     stock_footprints=stock.parent)
    d = make_design({"a": [PartSrc("R1", "test:R", (25.4, 25.4), footprint="Resistor_SMD:R_0402_1005Metric",
                                   pins=["A", "B"])]})
    d.symbol_libs = {"test": tmp_path / "hardware" / "kicad" / "lib" / "test.kicad_sym"}
    d.footprint_libs = {"test": tmp_path / "hardware" / "kicad" / "lib" / "test.pretty"}
    d.out_dir = tmp_path / "hardware" / "kicad" / "tp"
    tables = lib_tables(d, resolve_design(d, libs), libs)
    sym, fp = tables["sym-lib-table"], tables["fp-lib-table"]
    assert '(name "test") (type "KiCad") (uri "${KIPRJMOD}/../lib/test.kicad_sym")' in sym
    assert '(name "Resistor_SMD") (type "KiCad") (uri "${KICAD10_FOOTPRINT_DIR}/Resistor_SMD.pretty")' in fp
    assert '"test"' not in fp  # no footprint from the project library is used
    assert sym.startswith("(sym_lib_table\n\t(version 7)") and fp.endswith(")\n")


def test_kicad_pro_merges_into_existing_settings(make_design):
    layout = {"rules": {"min_clearance": 0.15}, "drc_severities": {"silk_overlap": "ignore"},
              "netclasses": {"Power": {"track_width": 0.4, "nets": ["+5V", "*SW"]},
                             "Default": {"clearance": 0.15}}}
    d = make_design({"a": []}, layout=layout)
    d.erc_severities = {"pin_to_pin": "error"}
    # as a KiCad GUI save leaves it: full rule sets, a since-removed severity, other settings
    existing = json.dumps({"board": {"design_settings": {
                               "rules": {"min_track_width": 0.2, "min_clearance": 0.3},
                               "rule_severities": {"clearance": "error", "track_width": "ignore"},
                               "track_widths": [0.0, 0.3]}},
                           "erc": {"rule_severities": {"pin_not_driven": "warning"}},
                           "text_variables": {"X": "µ"}})
    pro = json.loads(kicad_pro(d, existing))
    ds = pro["board"]["design_settings"]
    # owned sections are replaced whole: what the source no longer lists is gone
    assert ds["rules"] == {"min_clearance": 0.15}
    assert ds["rule_severities"] == {**{k: "error" for k in DRC_ERRORS}, "silk_overlap": "ignore"}
    assert pro["erc"]["rule_severities"] == {**{k: "error" for k in ERC_ERRORS}, "pin_to_pin": "error"}
    # everything else is kept, UTF-8 as KiCad writes it
    assert ds["track_widths"] == [0.0, 0.3] and pro["text_variables"] == {"X": "µ"}
    assert "µ" in kicad_pro(d, existing) and pro["meta"]["filename"] == "tp.kicad_pro"
    classes = {c["name"]: c for c in pro["net_settings"]["classes"]}
    assert classes["Default"]["clearance"] == 0.15 and classes["Power"]["track_width"] == 0.4
    assert pro["net_settings"]["netclass_patterns"] == [{"netclass": "Power", "pattern": "+5V"},
                                                        {"netclass": "Power", "pattern": "*SW"}]
    assert kicad_pro(d, kicad_pro(d, existing)) == kicad_pro(d, existing)  # stable


def test_kicad_dru(make_design):
    assert kicad_dru(make_design({"a": []})) == "(version 1)\n"
    rule = '(rule "x" (constraint hole_clearance (min 0.15mm)))'
    assert kicad_dru(make_design({"a": []}, layout={"custom_rules": rule + "\n"})) == \
        f"(version 1)\n{rule}\n"
