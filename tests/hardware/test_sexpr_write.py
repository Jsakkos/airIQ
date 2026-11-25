import pytest

from sexpr import QStr, dumps, parse


def test_quoted_atoms_come_back_as_qstr_and_still_compare_as_str():
    tree = parse('(layer "F.Cu" (type solid))')
    assert tree == ["layer", "F.Cu", ["type", "solid"]]
    assert isinstance(tree[1], QStr) and not isinstance(tree[2][1], QStr)


def test_dumps_round_trips_quoting_and_escapes():
    text = '(a "x y" b (c "q\\"uo\\\\te" "line\\nbreak") (d 1.5 -2))'
    tree = parse(text)
    again = parse(dumps(tree))
    assert again == tree
    assert [type(a) for a in again[3]] == [type(a) for a in tree[3]]
    assert again[3][1] == 'q"uo\\te' and again[3][2] == "line\nbreak"


def test_dumps_layout_one_line_for_atoms_and_indented_children():
    assert dumps(["at", "1", "2"]) == "(at 1 2)"
    assert dumps(["a", QStr("b"), ["c", "1"], ["d", ["e"]]]) == '(a "b"\n\t(c 1)\n\t(d\n\t\t(e)\n\t)\n)'


def test_bare_atom_that_needs_quotes_is_rejected():
    with pytest.raises(ValueError):
        dumps(["name", "two words"])
    with pytest.raises(ValueError):
        dumps(["name", ""])
