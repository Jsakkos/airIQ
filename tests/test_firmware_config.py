"""Static checks of the ESPHome packages (no ESPHome install needed)."""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
ESPHOME_DIR = ROOT / "firmware" / "esphome"
PKG = ESPHOME_DIR / "packages"
IFACE_PATH = ROOT / "hardware" / "interface.yaml"


class _Loader(yaml.SafeLoader):
    """SafeLoader that ignores ESPHome's `!secret`, `!lambda`, `!include`, ... tags."""


def _ignore_tag(loader, tag_suffix, node):
    # Keep the raw scalar for scalar nodes; None for anything else.
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    return None


_Loader.add_multi_constructor("!", _ignore_tag)


def load_yaml(path):
    """Plain single-file loader: every `!tag` is ignored (raw scalar or None)."""
    return yaml.load(Path(path).read_text(encoding="utf-8"), Loader=_Loader)


class _IncludeLoader(yaml.SafeLoader):
    """Loader that records `!include` targets and ignores all other `!` tags."""

    includes: list


def _include(loader, node):
    if isinstance(node, yaml.ScalarNode):
        loader.includes.append(loader.construct_scalar(node))
    elif isinstance(node, yaml.MappingNode):
        mapping = loader.construct_mapping(node, deep=True)
        if "file" in mapping:
            loader.includes.append(mapping["file"])
    return None


def _other_tag(loader, tag_suffix, node):
    return _ignore_tag(loader, tag_suffix, node)


_IncludeLoader.add_constructor("!include", _include)
_IncludeLoader.add_multi_constructor("!", _other_tag)


def load_merged(path):
    """Load an ESPHome YAML file and everything it `!include`s, recursively.

    Returns a list of all loaded documents: the root document first, then every
    included package in depth-first order. Handles both `!include path.yaml` and
    `!include {file: path.yaml, vars: ...}`; paths are relative to the including
    file. `!secret`, `!lambda` and any other `!` tag are ignored (raw scalar or
    None). Model-level tests (Tasks 4-6) use it to assert on the merged config
    of a device, e.g. `any("light" in doc for doc in load_merged(f))`.
    """
    path = Path(path)
    docs = []
    seen = set()

    def _load(p):
        p = p.resolve()
        if p in seen:
            return
        seen.add(p)
        text = p.read_text(encoding="utf-8")
        loader = _IncludeLoader(text)
        loader.includes = []
        try:
            doc = loader.get_single_data()
        finally:
            loader.dispose()
        docs.append(doc)
        for inc in loader.includes:
            _load(p.parent / inc)

    _load(path)
    return docs


@pytest.fixture(scope="module")
def board():
    return load_yaml(PKG / "board.yaml")


@pytest.fixture(scope="module")
def sensors():
    return load_yaml(PKG / "sensors.yaml")


def test_pins_mirror_interface():
    iface = yaml.safe_load(IFACE_PATH.read_text(encoding="utf-8"))
    subs = load_yaml(PKG / "pins.yaml")["substitutions"]
    expected = {f"pin_{k.lower()}": v for k, v in iface["signals"].items()}
    pins = {k: v for k, v in subs.items() if k.startswith("pin_")}
    assert pins == expected
    addrs = {k: int(v, 0) for k, v in subs.items() if k.startswith("addr_")}
    assert addrs == {f"addr_{k}": v for k, v in iface["i2c_addresses"].items()}
    assert set(subs) == set(pins) | set(addrs)


def test_offline_safe(board):
    assert board["wifi"]["reboot_timeout"] == "0s"
    assert board["api"]["reboot_timeout"] == "0s"


def test_low_heat_cpu(board):
    # esp32.cpu_frequency is a documented top-level option:
    # https://esphome.io/components/esp32/ (cpu_frequency)
    assert board["esp32"]["cpu_frequency"] == "80MHz"
    assert board["wifi"]["power_save_mode"] == "LIGHT"


def test_esp_idf_c6(board):
    assert board["esp32"]["variant"] == "esp32c6"
    assert board["esp32"]["framework"]["type"] == "esp-idf"


def test_logger_off_uart0(board):
    # GPIO16/17 (UART0) are the aux UART header; log over the USB serial/JTAG.
    # https://esphome.io/components/logger/ (hardware_uart)
    assert board["logger"]["hardware_uart"] == "USB_SERIAL_JTAG"


def test_no_bluetooth(board):
    assert "bluetooth_proxy" not in board and "esp32_ble_tracker" not in board


def test_airq_logic_included(board):
    assert "include/airq_logic.h" in board["esphome"]["includes"]
    assert (ESPHOME_DIR / "include" / "airq_logic.h").is_file()


def test_index_keys(sensors):
    sen6x = next(s for s in sensors["sensor"] if s["platform"] == "sen6x")
    assert "voc_index" in sen6x and "nox_index" in sen6x
    assert "temperature_compensation" in sen6x
    assert sen6x["temperature_acceleration"] == {"t1": 100, "t2": 300, "k": 20, "p": 20}
    assert sen6x["co2"]["ambient_pressure_compensation_source"] == "room_p"


def test_pressure_in_hpa_for_sen6x(sensors):
    sen6x = next(s for s in sensors["sensor"] if s["platform"] == "sen6x")
    src = sen6x["co2"]["ambient_pressure_compensation_source"]
    bmp = next(s for s in sensors["sensor"] if s["platform"] == "bmp581_i2c")
    p = bmp["pressure"]
    assert p["id"] == src
    assert p["unit_of_measurement"] == "hPa"
    assert {"multiply": 0.01} in p["filters"]


def test_lux_smoothed(sensors):
    veml = next(s for s in sensors["sensor"] if s["platform"] == "veml7700")
    filters = veml["ambient_light"]["filters"]
    assert any("sliding_window_moving_average" in f for f in filters)


def test_co2_asc_substitution(sensors, board):
    sen6x = next(s for s in sensors["sensor"] if s["platform"] == "sen6x")
    assert sen6x["co2"]["automatic_self_calibration"] == "${co2_asc}"
    assert board["substitutions"]["co2_asc"] == "true"
    assert "switch" not in sensors


def test_model_bundles_include_base():
    for name in ("model-airq.yaml", "model-mini.yaml"):
        docs = load_merged(PKG / name)
        assert len(docs) >= 4  # bundle + pins + board + sensors
    for name in ("airq-example.yaml", "airq-mini-example.yaml"):
        docs = load_merged(ESPHOME_DIR / name)
        assert any("esp32" in d for d in docs if d)
