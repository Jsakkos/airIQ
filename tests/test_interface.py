"""Sanity tests for hardware/interface.yaml (GPIO / I2C / connector contract)."""
from pathlib import Path

import pytest
import yaml

IFACE_PATH = Path(__file__).resolve().parent.parent / "hardware" / "interface.yaml"

# GPIOs exposed by the ESP32-C6-MINI-1 module (GPIO10/11 are not broken out).
# Source: ESP32-C6-MINI-1 & MINI-1U Datasheet v1.5, section 3 "Pin Definitions",
# Table 3-1 Pin Description:
# https://documentation.espressif.com/esp32-c6-mini-1_mini-1u_datasheet_en.pdf
MODULE_GPIOS = {f"GPIO{n}" for n in [*range(0, 10), *range(12, 24)]}


@pytest.fixture(scope="module")
def iface():
    return yaml.safe_load(IFACE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def sig(iface):
    return iface["signals"]


@pytest.fixture(scope="module")
def addr(iface):
    return iface["i2c_addresses"]


def test_signal_gpios_unique(sig):
    assert len(set(sig.values())) == len(sig)


def test_signal_gpios_exist_on_module(sig):
    assert set(sig.values()) <= MODULE_GPIOS


def test_no_reserved_gpio_used(iface, sig):
    assert not set(sig.values()) & set(iface["reserved"])


def test_strapping_pins_only_button(sig):
    assert {g for g in sig.values() if g in {"GPIO8", "GPIO15"}} == set()
    assert sig["BUTTON"] == "GPIO9"


def test_i2c_addresses_unique_7bit(addr):
    assert all(isinstance(a, int) for a in addr.values())
    assert len(set(addr.values())) == len(addr)
    assert all(0x08 <= a <= 0x77 for a in addr.values())


def test_qwiic_pinout(iface):
    c = iface["connectors"]
    assert c["J_QWIIC_TONGUE"] == ["GND", "+3V3", "I2C_SDA", "I2C_SCL"] == c["J_QWIIC_AUX"]
