import pytest

from sexpr import atom, child, children, parse, parse_value


def test_parse_nested_and_quotes():
    assert parse('(a (b "c d") e)') == ["a", ["b", "c d"], "e"]


def test_parse_escapes_and_empty_list():
    assert parse(r'(x "a\"b" ())') == ["x", 'a"b', []]


def test_parse_kicad_field_shape():
    tree = parse('(comp (ref "J1") (fields (field (name "Role") "J_SEN66")))')
    assert atom(tree, "ref") == "J1"
    field = child(child(tree, "fields"), "field")
    assert field == ["field", ["name", "Role"], "J_SEN66"]
    assert len(children(tree, "ref")) == 1


@pytest.mark.parametrize("bad", ["(a (b)", "a)", ""])
def test_parse_rejects_unbalanced(bad):
    with pytest.raises(ValueError):
        parse(bad)


def test_parse_value():
    assert parse_value("5.1k") == 5100 and parse_value("4k7") == 4700 and parse_value("10u") == 1e-5


def test_parse_value_exact_floats():
    assert parse_value("100n") == 1e-7
    assert parse_value("22u") == 22e-6
    assert parse_value("4.7k") == 4700.0


@pytest.mark.parametrize("text,expected", [
    ("2R2", 2.2), ("0R", 0.0), ("10R", 10.0), ("100", 100.0), ("1M", 1e6),
    ("10uF", 1e-5), ("10\u00b5F", 1e-5), ("5.1k\u03a9", 5100.0), ("4.7kohm", 4700.0),
    ("47pF", 47e-12), ("1mF", 1e-3), (" 5.1 k ", 5100.0),
])
def test_parse_value_kicad_forms(text, expected):
    assert parse_value(text) == expected


@pytest.mark.parametrize("bad", ["", "abc", "k7", "5.1x"])
def test_parse_value_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_value(bad)
