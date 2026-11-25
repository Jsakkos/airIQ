from datetime import date
from pathlib import Path

from check_bom import check_bom, check_parts

FX = Path(__file__).parent / "fixtures"


def test_parts_ok_passes():
    assert check_parts(FX / "parts_ok.csv") == []


def test_parts_not_economic():
    assert any("C999" in e for e in check_parts(FX / "parts_standard_only.csv"))


def test_parts_stale():
    assert check_parts(FX / "parts_ok.csv", fresh_days=7, today=date(2027, 1, 1)) != []


def test_parts_fresh_passes():
    assert check_parts(FX / "parts_ok.csv", fresh_days=7, today=date(2026, 11, 25)) == []


def test_too_many_extended():
    assert check_parts(FX / "parts_16_ext.csv") != []


def test_extended_cap_is_configurable():
    assert check_parts(FX / "parts_16_ext.csv", max_extended=16) == []


def test_basic_and_preferred_do_not_count_toward_extended_cap():
    assert check_parts(FX / "parts_ok.csv", max_extended=1) == []
    assert check_parts(FX / "parts_ok.csv", max_extended=0) != []


def test_zero_stock_reported(tmp_path):
    p = tmp_path / "parts.csv"
    p.write_text("lcsc,mpn,library,economic,checked_on,stock,unit_usd\n"
                 "C7,X,Basic,yes,2026-11-20,0,0.01\n", encoding="utf-8")
    assert any("C7" in e and "stock" in e for e in check_parts(p))


def test_bom_ok_passes():
    assert check_bom(FX / "bom_ok.csv", FX / "parts_ok.csv") == []


def test_bom_missing_lcsc():
    assert check_bom(FX / "bom_missing.csv", FX / "parts_ok.csv") != []


def test_bom_lcsc_not_in_parts_table(tmp_path):
    bom = tmp_path / "bom.csv"
    bom.write_text("Designator,Value,JLCPCB Part #\nR1,10k,C424242\n", encoding="utf-8")
    e = check_bom(bom, FX / "parts_ok.csv")
    assert any("C424242" in x for x in e)


def test_bom_dnp_rows_skipped_by_value_text(tmp_path):
    bom = tmp_path / "bom.csv"
    bom.write_text("Reference,Value,LCSC\nTP1,TP DNP,\nR1,10k,C25804\n", encoding="utf-8")
    assert check_bom(bom, FX / "parts_ok.csv") == []


def test_bom_extended_cap_counts_only_used_parts(tmp_path):
    # parts table has 16 Extended parts (over the cap) but the BOM uses just one.
    bom = tmp_path / "bom.csv"
    bom.write_text("Reference,LCSC\nR1,C2000\n", encoding="utf-8")
    assert check_bom(bom, FX / "parts_16_ext.csv") == []
    assert check_parts(FX / "parts_16_ext.csv") != []


def test_bom_applies_part_rules_to_used_lines():
    e = check_bom(FX / "bom_ok.csv", FX / "parts_ok.csv", fresh_days=7, today=date(2027, 1, 1))
    assert e != []


def test_bom_without_lcsc_column_reported(tmp_path):
    bom = tmp_path / "bom.csv"
    bom.write_text("Reference,Value\nR1,10k\n", encoding="utf-8")
    assert check_bom(bom, FX / "parts_ok.csv") != []
