import io
import zipfile

import pytest

from jlc import cpl_from_pos, gerber_zip, strip_dates

POS = """Ref,Val,Package,PosX,PosY,Rot,Side
"C1","10uF","C_0805_2012Metric",27.5000,26.0000,90.0000,top
"J1","USB-C","USB-C",10.0000,25.0000,-90.0000,top
"""


def test_cpl_from_pos_writes_jlc_columns():
    assert cpl_from_pos(POS).splitlines() == [
        "Designator,Mid X,Mid Y,Layer,Rotation",
        "C1,27.5mm,26mm,Top,90",
        "J1,10mm,25mm,Top,270",
    ]


def test_cpl_from_pos_rejects_unknown_side():
    with pytest.raises(ValueError):
        cpl_from_pos(POS.replace(",top\n", ",both\n", 1))


GERBER = ("%TF.GenerationSoftware,KiCad,Pcbnew,10.0.8*%\r\n"
          "%TF.CreationDate,2026-11-25T21:59:02-08:00*%\r\n"
          "%FSLAX46Y46*%\r\n"
          "G04 Created by KiCad (PCBNEW 10.0.8) date 2026-11-25 21:59:02*\r\n"
          "M02*\r\n")
DRILL = ("M48\n; DRILL file KiCad 10.0.8 date 2026-11-25T21:59:03\n"
         "; FORMAT={-:-/ absolute / metric / decimal}\n"
         "; #@! TF.CreationDate,2026-11-25T21:59:03-08:00\n"
         "; #@! TF.GenerationSoftware,Kicad,Pcbnew,10.0.8\nM30\n")


def test_strip_dates_drops_only_the_creation_date():
    assert strip_dates(GERBER) == ("%TF.GenerationSoftware,KiCad,Pcbnew,10.0.8*%\n%FSLAX46Y46*%\n"
                                   "G04 Created by KiCad (PCBNEW 10.0.8)*\nM02*\n")
    assert strip_dates(DRILL) == ("M48\n; DRILL file KiCad 10.0.8\n"
                                  "; FORMAT={-:-/ absolute / metric / decimal}\n"
                                  "; #@! TF.GenerationSoftware,Kicad,Pcbnew,10.0.8\nM30\n")


def test_gerber_zip_is_reproducible_and_holds_only_layers_and_drills(tmp_path):
    (tmp_path / "b-F_Cu.gtl").write_text(GERBER, encoding="utf-8")
    (tmp_path / "b-PTH.drl").write_text(DRILL, encoding="utf-8")
    (tmp_path / "b-job.gbrjob").write_text('{"CreationDate": "x"}', encoding="utf-8")
    first = gerber_zip(tmp_path)
    (tmp_path / "b-F_Cu.gtl").write_text(GERBER.replace("21:59:02", "08:00:00"), encoding="utf-8")
    assert gerber_zip(tmp_path) == first                       # a new export date changes nothing
    z = zipfile.ZipFile(io.BytesIO(first))
    assert z.namelist() == ["b-F_Cu.gtl", "b-PTH.drl"]
    assert all(i.compress_type == zipfile.ZIP_STORED and i.date_time == (1980, 1, 1, 0, 0, 0)
               for i in z.infolist())
    assert b"date" not in z.read("b-F_Cu.gtl") and b"\r" not in z.read("b-F_Cu.gtl")
