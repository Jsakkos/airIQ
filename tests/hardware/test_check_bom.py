from datetime import date
from pathlib import Path

import pytest

from check_bom import check_bom, check_parts, main

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


HDR = "lcsc,mpn,library,economic,checked_on,stock,unit_usd\n"


def _parts(tmp_path, text):
    p = tmp_path / "parts.csv"
    p.write_text(text, encoding="utf-8")
    return p


def test_parts_header_typo_reported(tmp_path):
    p = _parts(tmp_path, HDR.replace("lcsc", "LCSC") + "C1,X,Basic,yes,2026-11-20,5,0.01\n")
    assert any("lcsc" in e and "column" in e for e in check_parts(p))
    assert any("column" in e for e in check_bom(FX / "bom_ok.csv", p))


def test_empty_parts_table_reported(tmp_path):
    assert any("empty" in e for e in check_parts(_parts(tmp_path, HDR)))


def test_duplicate_lcsc_reported(tmp_path):
    row = "C1,X,Basic,yes,2026-11-20,5,0.01\n"
    assert any("duplicate" in e and "C1" in e for e in check_parts(_parts(tmp_path, HDR + row + row)))


def test_row_without_lcsc_reported(tmp_path):
    p = _parts(tmp_path, HDR + "C1,X,Basic,yes,2026-11-20,5,0.01\n,Y,Basic,yes,2026-11-20,5,0.01\n")
    assert any("no LCSC" in e for e in check_parts(p))


def test_cli_bom_and_parts_only(capsys):
    assert main([str(FX / "bom_ok.csv"), str(FX / "parts_ok.csv")]) == 0
    assert capsys.readouterr().out == ""
    assert main([str(FX / "bom_missing.csv"), str(FX / "parts_ok.csv")]) == 1
    assert "no LCSC" in capsys.readouterr().out
    assert main(["--parts-only", str(FX / "parts_ok.csv")]) == 0
    assert capsys.readouterr().out == ""
    assert main(["--parts-only", str(FX / "parts_standard_only.csv")]) == 1
    assert "C999" in capsys.readouterr().out


def test_cli_fresh_days(tmp_path, capsys):
    old = _parts(tmp_path, HDR + "C1,X,Basic,yes,2000-01-01,5,0.01\n")
    assert main(["--parts-only", str(old), "--fresh-days", "7"]) == 1
    assert "stale" in capsys.readouterr().out
    new = _parts(tmp_path, HDR + f"C1,X,Basic,yes,{date.today()},5,0.01\n")
    assert main(["--parts-only", str(new), "--fresh-days", "7"]) == 0


def test_cli_arity_errors():
    with pytest.raises(SystemExit) as e:
        main(["--parts-only", str(FX / "parts_ok.csv"), str(FX / "parts_ok.csv")])
    assert e.value.code == 2
    with pytest.raises(SystemExit):
        main([str(FX / "bom_ok.csv")])
