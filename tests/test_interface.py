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
    # GPIO4 (MTMS) / GPIO5 (MTDI) are strapping/JTAG pins too; keep them unused unless deliberate.
    assert {g for g in sig.values() if g in {"GPIO4", "GPIO5"}} == set()
    assert sig["BUTTON"] == "GPIO9"


def test_i2c_addresses_unique_7bit(addr):
    assert all(isinstance(a, int) for a in addr.values())
    assert len(set(addr.values())) == len(addr)
    assert all(0x08 <= a <= 0x77 for a in addr.values())


def test_qwiic_pinout(iface):
    c = iface["connectors"]
    assert c["J_QWIIC_TONGUE"] == ["GND", "+3V3", "I2C_SDA", "I2C_SCL"] == c["J_QWIIC_AUX"]


def test_sen66_connector_on_3v3(iface):
    # SEN66 runs on 3.15-3.45 V (spec section 3): never wire it to 5 V.
    pins = iface["connectors"]["J_SEN66"]
    assert "+3V3" in pins and "+5V" not in pins


def test_aux_uart_pinout(iface):
    assert iface["connectors"]["J_AUX_UART"] == [
        "GND", "+3V3", "AUX_UART_TX", "AUX_UART_RX", "EN", "BUTTON"]


def test_epd_connector(iface, sig):
    pins = iface["connectors"]["J_EPD"]
    assert len(pins) == 24
    assert pins[7] == "GND"  # pin 8 = BS1, low = 4-wire SPI
    for net in ["EPD_BUSY", "EPD_RST", "EPD_DC", "EPD_CS", "EPD_CLK", "EPD_MOSI"]:
        assert pins.count(net) == 1
        assert net in sig
    # GDEY029T94 spec Rev 1.0 s5 / Waveshare V2 spec Rev 2.1 s1.5: pin 4 NC, pin 5 VSH2.
    assert pins[3] == "NC" and pins[4] == "EPD_VSH2"
    # TSCL/TSDA (pins 6, 7) unused.
    assert pins[5] == "NC" and pins[6] == "NC"


def test_sen66_connector_pins(iface):
    pins = iface["connectors"]["J_SEN66"]
    assert len(pins) == 6
    assert pins.count("I2C_SDA") == 1 and pins.count("I2C_SCL") == 1
    assert pins == ["+3V3", "GND", "I2C_SDA", "I2C_SCL", "NC", "NC"]


def test_no_todo_in_interface_yaml():
    assert "TODO" not in IFACE_PATH.read_text(encoding="utf-8")
