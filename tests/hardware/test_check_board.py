from pathlib import Path

from check_board import check_board, main

FX = Path(__file__).parent / "fixtures"

HEADER = '(kicad_pcb (version 20250907) (layers (0 "F.Cu" signal) (25 "Edge.Cuts" user))\n'


def board(tmp_path, body):
    p = tmp_path / "b.kicad_pcb"
    p.write_text(HEADER + body + ")\n", encoding="utf-8")
    return p


def test_board_ok_passes():
    assert check_board(FX / "board_ok.kicad_pcb", 60, 30) == []  # exactly 60.0 x 30.0


def test_board_too_big():
    assert check_board(FX / "board_61x30.kicad_pcb", 60, 30) != []


def test_part_on_bottom():
    e = check_board(FX / "board_bottom_part.kicad_pcb", 60, 30)
    assert any("B.Cu" in x and "R2" in x for x in e)


def test_too_tall_names_height(tmp_path):
    p = board(tmp_path, '(gr_rect (start 0 0) (end 50 31) (layer "Edge.Cuts"))')
    e = check_board(p, 60, 30)
    assert len(e) == 1 and "height" in e[0]


def test_non_edge_shapes_ignored(tmp_path):
    p = board(tmp_path, '(gr_rect (start 0 0) (end 50 30) (layer "Edge.Cuts"))'
                        '(gr_line (start -100 -100) (end 300 300) (layer "F.SilkS"))')
    assert check_board(p, 60, 30) == []


def test_circle_and_poly(tmp_path):
    p = board(tmp_path, '(gr_circle (center 30 15) (end 45 15) (layer "Edge.Cuts"))')
    assert check_board(p, 30.0, 30.0) == []
    assert check_board(p, 29.0, 30.0) != []
    q = board(tmp_path, '(gr_poly (pts (xy 0 0) (xy 40 0) (xy 40 20) (xy 0 20)) (layer "Edge.Cuts"))')
    assert check_board(q, 40, 20) == []
    assert check_board(q, 39, 20) != []


def test_arc_uses_true_extents_not_three_points(tmp_path):
    # Quarter-plus arc about the origin, r = 10, from 0 deg through 45 deg to 135 deg (y down in file
    # space does not matter). It passes through the extreme at 90 deg (y = 10) between mid and end.
    p = board(tmp_path, '(gr_arc (start 10 0) (mid 7.0710678 7.0710678) (end -7.0710678 7.0710678)'
                        ' (layer "Edge.Cuts"))')
    assert check_board(p, 17.08, 10.0) == []
    assert any("height" in e for e in check_board(p, 17.08, 9.0))  # a 3-point bbox (7.07) would pass


def test_arc_clockwise_direction(tmp_path):
    # Same circle, going the other way round: start 10,0 -> mid at -45 deg -> end at -135 deg.
    p = board(tmp_path, '(gr_arc (start 10 0) (mid 7.0710678 -7.0710678) (end -7.0710678 -7.0710678)'
                        ' (layer "Edge.Cuts"))')
    assert check_board(p, 17.08, 10.0) == []
    assert any("height" in e for e in check_board(p, 17.08, 9.0))


def test_footprint_edge_shape_is_rotated_and_translated(tmp_path):
    fp = ('(footprint "Slot" (layer "F.Cu") (at 10 10 90)'
          ' (property "Reference" "H1")'
          ' (fp_line (start 0 0) (end 20 0) (layer "Edge.Cuts")))')
    p = board(tmp_path, fp)
    # local (0,0)-(20,0) rotated 90 deg (KiCad: y' = -x) -> a 20 mm vertical line.
    assert check_board(p, 1, 20) == []
    assert any("height" in e for e in check_board(p, 1, 19))


def test_no_outline_reported(tmp_path):
    assert any("Edge.Cuts" in e for e in check_board(board(tmp_path, ""), 60, 30))


def test_cli_clean_and_violating(capsys):
    ok = str(FX / "board_ok.kicad_pcb")
    assert main([ok, "--max-w", "60", "--max-h", "30"]) == 0
    assert capsys.readouterr().out == ""
    assert main([str(FX / "board_bottom_part.kicad_pcb"), "--max-w", "60", "--max-h", "30"]) == 1
    assert "B.Cu" in capsys.readouterr().out
    assert main([str(FX / "board_61x30.kicad_pcb"), "--max-w", "60", "--max-h", "30"]) == 1
    assert "width" in capsys.readouterr().out
