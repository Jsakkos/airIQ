from pathlib import Path

import yaml

from check_netlist import check_netlist

FX = Path(__file__).parent / "fixtures"
IFACE = FX / "iface.yaml"


def errs(name, iface=IFACE):
    return check_netlist(FX / name, iface)


def test_netlist_clean_fixture_passes():
    assert check_netlist(FX / "good.net", FX / "iface.yaml") == []


def test_wrong_gpio_net_reported():
    assert any("IO6" in e for e in check_netlist(FX / "swapped_i2c.net", FX / "iface.yaml"))


def test_shared_cc_resistor_reported():
    assert any("CC2" in e for e in check_netlist(FX / "shared_cc.net", FX / "iface.yaml"))


def test_missing_bulk_cap_reported():
    assert any("+3V3" in e for e in check_netlist(FX / "no_bulk.net", FX / "iface.yaml"))


def test_connector_pin_order():
    assert any("J_SEN66" in e for e in check_netlist(FX / "mirrored_sen66.net", FX / "iface.yaml"))


def test_each_violation_fixture_trips_only_its_own_rule():
    assert all("IO" in e or "I2C_S" in e for e in errs("swapped_i2c.net"))
    assert all("J_SEN66" in e for e in errs("mirrored_sen66.net"))
    assert all("CC2" in e for e in errs("shared_cc.net"))
    assert all("+3V3" in e and "bulk" in e for e in errs("no_bulk.net"))


def test_cc_resistor_wrong_value_reported():
    e = errs("cc_wrong_value.net")
    assert len(e) == 1 and "USB_CC2" in e[0]


def test_missing_i2c_pullup_reported():
    e = errs("no_i2c_pullup.net")
    assert len(e) == 1 and "I2C_SCL" in e[0]


def test_missing_button_pullup_reported():
    e = errs("no_button_pullup.net")
    assert len(e) == 1 and "BUTTON" in e[0]


def test_strap_pin_with_led_reported():
    e = errs("strap_led.net")
    assert len(e) == 1 and "GPIO8" in e[0]


def test_hierarchical_net_names_match_by_suffix():
    assert errs("hier.net") == []


def test_ambiguous_net_name_reported():
    e = errs("ambiguous.net")
    assert any("ambiguous" in x and "I2C_SDA" in x for x in e)


def test_absent_things_are_reported_as_missing(tmp_path):
    # Rule 1: the net is absent / Rule 2: the connector part is absent.
    text = (FX / "good.net").read_text(encoding="utf-8")
    no_sda = text.replace('(name "I2C_SDA")', '(name "SOMETHING_ELSE")')
    p = tmp_path / "no_sda.net"
    p.write_text(no_sda, encoding="utf-8")
    e = check_netlist(p, IFACE)
    assert any(x.startswith("missing") and "I2C_SDA" in x for x in e)
    no_j = tmp_path / "no_j.net"
    no_j.write_text(text.replace('(field (name "Role") "J_SEN66")', ""), encoding="utf-8")
    assert any(x.startswith("missing") and "J_SEN66" in x for x in check_netlist(no_j, IFACE))


def test_real_violations_do_not_start_with_missing():
    assert not any(e.startswith("missing") for e in errs("swapped_i2c.net"))
    assert not any(e.startswith("missing") for e in errs("mirrored_sen66.net"))


def test_nc_pin_on_a_real_net_is_reported():
    e = errs("nc_connected.net")
    assert len(e) == 1 and "J_SEN66" in e[0] and "pin 6" in e[0]


def test_checks_key_selects_rule_groups(tmp_path):
    tongue = FX / "tongue.net"
    assert check_netlist(tongue, FX / "iface_tongue.yaml") == []
    data = yaml.safe_load((FX / "iface_tongue.yaml").read_text(encoding="utf-8"))
    del data["checks"]
    all_checks = tmp_path / "iface_all.yaml"
    all_checks.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert check_netlist(tongue, all_checks) != []


def test_unknown_check_group_reported(tmp_path):
    p = tmp_path / "i.yaml"
    p.write_text("checks: [bogus]\nsignals: {}\nconnectors: {}\n", encoding="utf-8")
    assert any("bogus" in e for e in check_netlist(FX / "good.net", p))
