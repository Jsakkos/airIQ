import pytest

from jlc import cpl_from_pos

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
