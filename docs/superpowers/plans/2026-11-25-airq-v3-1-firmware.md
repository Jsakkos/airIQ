# airQ v3 Plan 1: Repo foundation and firmware implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the repo for v3, define the hardware/firmware interface contract, and ship ESPHome firmware for both models (airQ with e-ink, airQ mini with a split light). The firmware compiles in CI, and its logic is unit-tested on the host.

**Architecture:**
- All decision logic lives in one dependency-free C++ header, `airq_logic.h`. It covers colour bands, hysteresis, brightness, button classification, display text and refresh policy, and is unit-tested on the host.
- ESPHome YAML is split into small packages. Two model bundles compose them, and each physical unit gets a thin device file that includes one bundle.
- `hardware/interface.yaml` is the single source of truth for pins and addresses. A pytest check keeps the firmware's `pins.yaml` in sync with it.

**Tech stack:**
- ESPHome ≥ 2026.11 (ESP-IDF, ESP32-C6), installed with `uv tool install`.
- C++17 host tests compiled with `zig c++`, via the `ziglang` PyPI package (no system compiler exists on this machine).
- pytest with PyYAML.
- GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-25-airq-v3-design.md`. The overview and its deviations are in `docs/superpowers/plans/2026-11-25-airq-v3-overview.md`.

## Global constraints

- Platform: ESP32-C6-MINI-1, `framework: esp-idf`, `cpu_frequency: 80MHz`, Wi-Fi `power_save_mode: LIGHT`. No Bluetooth proxy.
- Local only: the Home Assistant API uses encryption, and nothing reaches the cloud.
- CO₂ bands (ppm), green / yellow / orange / red: `< 800`, `800–999`, `1000–1499`, `≥ 1500`.
- PM2.5 bands (µg/m³), green / yellow / orange / red / purple / maroon: `≤ 9.0`, `≤ 35.4`, `≤ 55.4`, `≤ 125.4`, `≤ 225.4`, `> 225.4`.
- Band colours (RGB 0–1), the same as v2: green (0,1,0), yellow (1,0.93,0), orange (1,0.4,0), red (1,0,0), purple (0.85,0,1), maroon (1,0,0.22).
- VOC and NOx are published as relative indices (`voc_index` / `nox_index` keys), never in ppb.
- Display (airQ only): CO₂ in ppm on the left, PM2.5 in µg/m³ on the right, each with a label and unit, and nothing else.
- Refresh rule: refresh only when the shown text has changed **and** at least 180 000 ms have passed since the last refresh. Every 6th refresh is a full refresh.
- Light: capped by default (`light_cap: "0.5"`), auto-dimmed by the VEML7700, and exposed to Home Assistant as a "Status light" on/off switch plus a "Night mode" switch.
- Button press durations: under 50 ms ignored; under 1 s toggles the light; 1–5 s ignored; 5–15 s runs CO₂ forced recalibration to 420 ppm; 15 s or longer reboots into safe mode.
- Entity names follow `${friendly_name} CO2`, `${friendly_name} PM2.5`, …, so v2 Home Assistant dashboards migrate easily.
- Any pin or address appears exactly once in `hardware/interface.yaml`. `firmware/esphome/packages/pins.yaml` mirrors it.

## Review focus

1. **Missing readings** (boot, SEN66 warm-up, a disconnected sensor, NaN): the display shows `--`, and that half of the light (or the whole worst-of light) goes dark. It must never show a false green. Tested in Task 2 and verified in Task 4.
2. **Readings on or near a threshold**: boundaries are exact (799→green, 800→yellow, 9.0→green, 9.1→yellow), and the light doesn't flicker on noise within the hysteresis margin. Tested in Task 2.
3. **Home Assistant or Wi-Fi offline**: the device keeps measuring, displaying and lighting, and never reboots in a loop. Both `api.reboot_timeout` and `wifi.reboot_timeout` are `0s`. Tested in Task 3.
4. **The light sensor seeing the device's own LEDs, or extreme lux values**: brightness stays within `[0, cap]`, never decreases as lux rises, and lux is smoothed over a 30 s sliding window. Tested in Task 2, configured in Task 3.
5. **Power loss**: the Status light and Night mode switches come back to their previous state. Tested in Task 4.

---

### Task 1: Repo restructure and interface contract

**Files:**
- Move: `pcb/`, `nextion/` and `images/` to `legacy/v2/` with `git mv`. Then fix the v2 image paths in the README section moved to `legacy/v2/README.md`.
- Create: `legacy/v2/README.md`, holding the current `README.md` content, with paths updated.
- Move: `reports/` and `research_notes/` to `docs/research/` with `git mv` (spec §6.12). Update the research links in the spec header and in `docs/superpowers/plans/*.md`.
- Modify: `README.md`, rewritten as a short v3 landing page that links the spec, plans, research report and `legacy/v2/`.
- Create: `LICENSE` (MIT, applies to `firmware/` and `tools/`) and `hardware/LICENSE.md` (CC-BY-SA 4.0 notice covering `hardware/` and `enclosure/`, with a link to the legal code).
- Modify: `.gitignore`, adding `firmware/esphome/secrets.yaml`, `firmware/esphome/.esphome/`, `build/` and `__pycache__/`.
- Create: `hardware/interface.yaml`
- Test: `tests/test_interface.py`

**Interfaces:**
- Produces: `hardware/interface.yaml` with these top-level keys:
  - `signals:` mapping signal name to `GPIOn`: `I2C_SDA`, `I2C_SCL`, `EPD_CLK`, `EPD_MOSI`, `EPD_CS`, `EPD_DC`, `EPD_RST`, `EPD_BUSY`, `LED_DATA`, `BUTTON`, `AUX_UART_TX`, `AUX_UART_RX`
  - `i2c_addresses:` mapping device name to an integer: `sen6x`, `sht45`, `bmp585`, `veml7700`, `sfa40`
  - `connectors:` mapping a connector role to the **net name on each pin, in pin order**: `J_SEN66`, `J_QWIIC_TONGUE`, `J_QWIIC_AUX`, `J_LED_EXT`, `J_AUX_UART`, `J_EPD`. Use the schematic's net names: `GND`, `+3V3`, `+5V`, `I2C_SDA`, `I2C_SCL`, `LED_DOUT_5V`, etc. Write `NC` for unconnected pins. Plan 2's netlist checker compares these lists pin by pin.
  - `mechanical:` empty for now. Plan 2 fills it with board outlines and mounting-hole positions for Plan 3.
  - `reserved:` the GPIOs the design must not use (USB D−/D+ and in-module flash)
- Starting proposal, to verify against the ESP32-C6-MINI-1 datasheet ("Pin Definitions") and ESP32-C6 strapping pins (GPIO8, GPIO9, GPIO15):
  - I²C SDA = GPIO6, SCL = GPIO7
  - EPD CLK = 19, MOSI = 18, CS = 20, DC = 21, RST = 22, BUSY = 23
  - LED_DATA = GPIO2
  - BUTTON = GPIO9 (the BOOT strap, so the button doubles as the download button)
  - AUX UART TX = GPIO16, RX = GPIO17
  - Reserved: GPIO12/13 (USB)
  - Addresses: sen6x 0x6B, sht45 0x44, bmp585 0x46, veml7700 0x10, sfa40 per the SFA40 datasheet (SFA30 used 0x5D)
  - Connector pinouts come from each part's datasheet. The Qwiic order is `GND`, `+3V3`, `I2C_SDA`, `I2C_SCL`.

- [ ] **Step 1: Write failing tests** in `tests/test_interface.py`. Load the YAML with `yaml.safe_load`. Copy the module's exposed GPIO list from the datasheet into `MODULE_GPIOS`.
  ```python
  def test_signal_gpios_unique():          assert len(set(sig.values())) == len(sig)
  def test_signal_gpios_exist_on_module(): assert set(sig.values()) <= MODULE_GPIOS
  def test_no_reserved_gpio_used():        assert not set(sig.values()) & set(iface["reserved"])
  def test_strapping_pins_only_button():   assert {g for g in sig.values() if g in {"GPIO8","GPIO15"}} == set() and sig["BUTTON"] == "GPIO9"
  def test_i2c_addresses_unique_7bit():    assert len(set(addr.values())) == len(addr) and all(0x08 <= a <= 0x77 for a in addr.values())
  def test_qwiic_pinout():                 assert iface["connectors"]["J_QWIIC_TONGUE"] == ["GND","+3V3","I2C_SDA","I2C_SCL"] == iface["connectors"]["J_QWIIC_AUX"]
  ```
- [ ] **Step 2: Run** `uv run --with pytest --with pyyaml pytest tests/test_interface.py -v`. Expected: **FAIL**, file not found.
- [ ] **Step 3: Write `hardware/interface.yaml`** from the proposal above. Correct any pin the datasheet contradicts, and add a one-line YAML comment on each such change.
- [ ] **Step 4: Do the moves, README, licences and `.gitignore`.** Check that no v2 file was deleted: `git status` should show only renames under `legacy/v2/`.
- [ ] **Step 5: Run** the tests again. Expected: **6 passed**.
- [ ] **Step 6: Commit** with the message `chore: v3 repo layout, licences, hardware interface contract`.

### Task 2: Logic header and host unit tests

**Files:**
- Create: `firmware/esphome/include/airq_logic.h`
- Test: `firmware/tests/test_airq_logic.cpp`, using a minimal `CHECK(expr)` macro that counts failures. `main` returns non-zero if any check fails and prints `N checks passed`.

**Interfaces:**
- Produces, in `namespace airq` (all functions `inline`, with no ESPHome includes):
  - `enum class Band : uint8_t { Unknown, Green, Yellow, Orange, Red, Purple, Maroon };`
  - `struct Rgb { float r, g, b; };`
  - `Band co2_band(float ppm);` and `Band pm25_band(float ugm3);`: NaN or negative input returns `Unknown`.
  - `Band co2_band_hyst(float ppm, Band prev);` (margin 25 ppm) and `Band pm25_band_hyst(float ugm3, Band prev);` (margin 0.5)
  - `Band worse(Band a, Band b);`: a known band always beats `Unknown`.
  - `Rgb band_color(Band b);`: `Unknown` returns `{0,0,0}`.
  - `float light_brightness(float lux, float cap);`
  - `enum class Press : uint8_t { None, ToggleLight, ForceCo2Calibration, SafeModeReboot };` with `Press classify_press(uint32_t held_ms);`
  - `std::string co2_text(float ppm);` and `std::string pm25_text(float ugm3);`
  - `enum class Refresh : uint8_t { None, Partial, Full };` with `Refresh decide_refresh(uint32_t now_ms, uint32_t last_ms, bool ever_refreshed, bool changed, uint8_t partials_since_full);`

- [ ] **Step 1: Write the failing tests**, covering at least these assertions:
  ```cpp
  CHECK(co2_band(NAN) == Band::Unknown);  CHECK(co2_band(-1) == Band::Unknown);
  CHECK(co2_band(799) == Band::Green);    CHECK(co2_band(800) == Band::Yellow);
  CHECK(co2_band(1000) == Band::Orange);  CHECK(co2_band(1500) == Band::Red);
  CHECK(pm25_band(9.0f) == Band::Green);  CHECK(pm25_band(9.1f) == Band::Yellow);
  CHECK(pm25_band(55.5f) == Band::Red);   CHECK(pm25_band(225.5f) == Band::Maroon);
  CHECK(co2_band_hyst(810, Band::Green) == Band::Green);   CHECK(co2_band_hyst(826, Band::Green) == Band::Yellow);
  CHECK(co2_band_hyst(790, Band::Yellow) == Band::Yellow); CHECK(co2_band_hyst(774, Band::Yellow) == Band::Green);
  CHECK(co2_band_hyst(900, Band::Unknown) == Band::Yellow);
  CHECK(pm25_band_hyst(9.3f, Band::Green) == Band::Green); CHECK(pm25_band_hyst(9.6f, Band::Green) == Band::Yellow);
  CHECK(worse(Band::Green, Band::Orange) == Band::Orange); CHECK(worse(Band::Unknown, Band::Green) == Band::Green);
  CHECK(band_color(Band::Unknown).r == 0 && band_color(Band::Unknown).g == 0 && band_color(Band::Unknown).b == 0);
  CHECK(band_color(Band::Yellow).g == 0.93f);
  CHECK(light_brightness(0.5f, 0.6f) == 0.6f * 0.05f); CHECK(light_brightness(300, 0.6f) == 0.6f);
  CHECK(light_brightness(1e6f, 0.6f) == 0.6f);         CHECK(light_brightness(NAN, 0.6f) == 0.3f);
  // monotonic: for lux in 1..300 step 1, b(lux+1) >= b(lux), and 0 <= b <= cap
  CHECK(classify_press(30) == Press::None);     CHECK(classify_press(400) == Press::ToggleLight);
  CHECK(classify_press(3000) == Press::None);   CHECK(classify_press(5000) == Press::ForceCo2Calibration);
  CHECK(classify_press(15000) == Press::SafeModeReboot);
  CHECK(co2_text(612.4f) == "612");  CHECK(co2_text(NAN) == "--");  CHECK(co2_text(40000) == "40000");
  CHECK(pm25_text(4.4f) == "4");     CHECK(pm25_text(4.6f) == "5"); CHECK(pm25_text(-2) == "--");
  CHECK(decide_refresh(1000, 0, false, true, 0) == Refresh::Full);
  CHECK(decide_refresh(179999, 0, true, true, 0) == Refresh::None);
  CHECK(decide_refresh(180000, 0, true, false, 0) == Refresh::None);
  CHECK(decide_refresh(180000, 0, true, true, 4) == Refresh::Partial);
  CHECK(decide_refresh(180000, 0, true, true, 5) == Refresh::Full);
  CHECK(decide_refresh(100000, 4294900000u, true, true, 0) == Refresh::None); // millis() wrap: 167 296 ms elapsed
  ```
- [ ] **Step 2: Run:**
  ```
  uv run --with ziglang python -m ziglang c++ -std=c++17 -Wall -Werror -I firmware/esphome/include firmware/tests/test_airq_logic.cpp -o build/test_airq_logic.exe && build/test_airq_logic.exe
  ```
  Expected: **compile error**, since `airq_logic.h` doesn't exist yet.
- [ ] **Step 3: Implement `airq_logic.h`** using the Global constraints values.
  - Hysteresis: if `prev` lies between `band(v − margin)` and `band(v + margin)`, return `prev`; otherwise return `band(v)`.
  - Brightness: `≤ 1 lux` gives `0.05·cap`, `≥ 300 lux` gives `cap`, log-linear in between; NaN gives `0.5·cap`.
  - Elapsed time: `now_ms − last_ms` in `uint32_t` arithmetic, so wrap-around is handled.
- [ ] **Step 4: Run** the command again. Expected: `N checks passed`, exit code 0.
- [ ] **Step 5: Commit** with the message `feat(firmware): host-tested airq_logic (bands, hysteresis, brightness, button, refresh)`.

### Task 3: ESPHome base, sensors, model bundles and offline safety

**Files:**
- Create in `firmware/esphome/packages/`:
  - `pins.yaml`: substitutions mirroring `interface.yaml`, with the same keys in lowercase, e.g. `pin_i2c_sda`, `addr_sht45`
  - `board.yaml`
  - `sensors.yaml`
  - `model-airq.yaml`
  - `model-mini.yaml`
- Create in `firmware/esphome/`:
  - `airq-example.yaml`
  - `airq-mini-example.yaml`
  - `secrets.example.yaml`
- Test: `tests/test_firmware_config.py`

**Interfaces:**
- Consumes: `hardware/interface.yaml` (Task 1) and `airq_logic.h` (Task 2).
- Produces these sensor ids for later tasks: `room_t`, `room_rh` (SHT45); `room_p` (BMP585); `room_lux` (VEML7700, smoothed); `co2`, `pm_1_0`, `pm_2_5`, `pm_4_0`, `pm_10_0`, `voc_index`, `nox_index`, `sen_t`, `sen_rh` (SEN6x); switch `co2_asc`.
- Produces these substitutions, which device files may override: `name`, `friendly_name`, `sen6x_model` (default SEN66), `led_count` (default 4), `light_cap` (default "0.5"), `epd_model`.
- Produces: `board.yaml` includes `include/airq_logic.h` through `esphome: includes:`.

- [ ] **Step 1: Write failing tests** in `tests/test_firmware_config.py`. Use a YAML loader that ignores `!secret`, `!include` and `!lambda` tags (`yaml.SafeLoader` with a no-op multi-constructor for `!`).
  ```python
  def test_pins_mirror_interface():  assert pins_subs == expected_from(interface_yaml)    # every signal and address, same values
  def test_offline_safe():           assert board["wifi"]["reboot_timeout"] == "0s" and board["api"]["reboot_timeout"] == "0s"
  def test_low_heat_cpu():           assert board["esp32"]["cpu_frequency"] == "80MHz" and board["wifi"]["power_save_mode"] == "LIGHT"
  def test_no_bluetooth():           assert "bluetooth_proxy" not in board and "esp32_ble_tracker" not in board
  def test_index_keys():             assert "voc_index" in sen6x and "nox_index" in sen6x
  def test_lux_smoothed():           assert any("sliding_window_moving_average" in f for f in veml_filters)
  ```
- [ ] **Step 2: Run** `uv run --with pytest --with pyyaml pytest tests/test_firmware_config.py -v`. Expected: **FAIL**.
- [ ] **Step 3: Write `board.yaml`.**
  - Platform: `esp32` variant `esp32c6`, framework `esp-idf`, 80 MHz.
  - Logger.
  - `api` with an encryption key from `!secret api_key` and `reboot_timeout: 0s`.
  - `ota` (platform esphome) using `!secret ota_password`.
  - `wifi` with ssid/password secrets, `power_save_mode: LIGHT`, `reboot_timeout: 0s`, and a fallback `ap:` named `${name}-setup`.
  - `captive_portal`, plus `safe_mode` with a safe-mode `button` (id `safe_mode_btn`).
  - `i2c` on the `pins.yaml` pins at 100 kHz.
- [ ] **Step 4: Write `sensors.yaml`** using the ESPHome components `sht4x`, `bmp581` (address `${addr_bmp585}`), `veml7700` (30 s sliding window) and `sen6x` (model `${sen6x_model}`). Configure `sen6x` exactly as follows, checking the key names against esphome.io/components/sensor/sen6x:
  - pressure compensation fed from `room_p`
  - temperature compensation enabled
  - Sensirion "Light (IAQM)" acceleration preset: T1=100, T2=300, K=20, P=20
  - VOC/NOx through `voc_index` / `nox_index`
  - the automatic self-calibration switch exposed as `co2_asc`, default on, restored after reboot
  - SHT45 is the published room temperature and humidity. The SEN66's own T/RH is published as diagnostic entities.
- [ ] **Step 5: Write the model bundles and example device files.**
  - `model-airq.yaml` and `model-mini.yaml` include `pins`, `board` and `sensors` for now; later tasks add their packages.
  - The example device files set `name` and `friendly_name` and include one model bundle.
  - `secrets.example.yaml` holds placeholders.
- [ ] **Step 6: Run** pytest again. Expected: **6 passed**.
- [ ] **Step 7: Validate both configs.**
  1. Install once: `uv tool install "esphome>=2026.11,<2026.12"`.
  2. Copy `secrets.example.yaml` to `secrets.yaml`.
  3. Run `esphome config firmware/esphome/airq-example.yaml` and then `esphome config firmware/esphome/airq-mini-example.yaml`.

  Expected: `Configuration is valid!` for both.
- [ ] **Step 8: Commit** with the message `feat(firmware): ESPHome base, sensors, model bundles`.

### Task 4: Status light and button

**Files:**
- Create in `firmware/esphome/packages/`:
  - `light-common.yaml`: the `esp32_rmt_led_strip` (WS2812-class, `${led_count}` LEDs on `${pin_led_data}`), template switches "Status light" (`RESTORE_DEFAULT_ON`) and "Night mode" (`RESTORE_DEFAULT_OFF`), and globals `co2_band_g`, `pm_band_g`
  - `light-worst.yaml`: the airQ's single light, showing the worst of the two bands
  - `light-split.yaml`: a `partition` light, with the first half `co2_light` and the second half `pm_light`
  - `button.yaml`
- Modify: `model-airq.yaml` (add light-common, light-worst and button) and `model-mini.yaml` (add light-common, light-split and button)
- Test: `tests/test_firmware_config.py`, adding the tests below

**Interfaces:**
- Consumes: Task 3 sensor ids, and `airq::*_band_hyst`, `worse`, `band_color`, `light_brightness` and `classify_press`.
- Produces: switch ids `status_light`, `night_mode`.

- [ ] **Step 1: Write failing tests:**
  ```python
  def test_light_state_restores():  assert switch("status_light")["restore_mode"] == "RESTORE_DEFAULT_ON" and switch("night_mode")["restore_mode"] == "RESTORE_DEFAULT_OFF"
  def test_mini_has_two_halves():   assert {"co2_light","pm_light"} <= light_ids(model_mini)
  def test_airq_single_light():     assert "co2_light" not in light_ids(model_airq)
  ```
- [ ] **Step 2: Run** pytest. Expected: **FAIL**.
- [ ] **Step 3: Implement the light logic** with an `interval` running every 2 s:
  - Update the band globals with `*_band_hyst`.
  - Compute the target colour per light: the airQ uses `worse`, the mini uses each band for its own half.
  - Compute brightness with `light_brightness(room_lux, ${light_cap})`.
  - If Night mode is on or Status light is off, turn the light(s) off.
  - Turn a light (or half) **off** when its band is `Unknown`.
  - Set the transition length to 1 s.
- [ ] **Step 4: Implement `button.yaml`:**
  - A GPIO binary sensor on `${pin_button}`, inverted, with pull-up.
  - Record `millis()` on press, then `classify_press` on release.
  - `ToggleLight` toggles `status_light`.
  - `ForceCo2Calibration` calls the SEN6x forced-recalibration action with a 420 ppm target (verify the action name in the sen6x docs) and then blinks white 3 times.
  - `SafeModeReboot` presses `safe_mode_btn`.
- [ ] **Step 5: Run** pytest, then `esphome config` on both example files. Expected: all pass, `Configuration is valid!` twice.
- [ ] **Step 6: Commit** with the message `feat(firmware): status light (worst-of / split) and button actions`.

### Task 5: E-ink display (airQ only)

**Files:**
- Create: `firmware/esphome/packages/display.yaml`
- Modify: `model-airq.yaml` (add display)
- Test: `tests/test_firmware_config.py`, adding the tests below

**Interfaces:**
- Consumes: sensor ids `co2` and `pm_2_5`; `airq::co2_text`, `pm25_text`, `decide_refresh`.
- Produces: display id `epd`, and globals `epd_last_ms`, `epd_ever`, `epd_partials`, `epd_shown` (the last drawn text).

- [ ] **Step 1: Write failing tests:**
  ```python
  def test_display_manual_update():  assert display("epd")["update_interval"] == "never"
  def test_display_only_in_airq():   assert "display" in model_airq_merged and "display" not in model_mini_merged
  ```
- [ ] **Step 2: Run** pytest. Expected: **FAIL**.
- [ ] **Step 3: Implement `display.yaml`.**
  - `spi` on the EPD pins, and `display: platform: epaper_spi` with `model: ${epd_model}`. The default is the Waveshare 2.9″ V2 model name exactly as listed in the epaper_spi docs.
  - CS, DC, reset and busy pins from `pins.yaml`.
  - Fonts: one bold numeral face sized so "40000" fits in half the 296 px width, plus one small label face.
  - The lambda draws "CO₂" with "ppm" on the left half and "PM2.5" with "µg/m³" on the right half, using `co2_text` and `pm25_text`.
  - An `interval` every 10 s calls `decide_refresh`, updates the globals and calls `component.update: epd`.
  - Full versus partial: use the component's own mechanism if `epaper_spi` exposes one (e.g. `full_update_every: 6`). Otherwise request a full refresh when `decide_refresh` returns `Full`.
- [ ] **Step 4: Run** pytest, then `esphome config firmware/esphome/airq-example.yaml`. Expected: pass.
- [ ] **Step 5: Commit** with the message `feat(firmware): e-ink CO2/PM2.5 display with 180 s refresh policy`.

### Task 6: HCHO option, full compiles, CI and docs

**Files:**
- Create:
  - `firmware/esphome/packages/hcho.yaml`: an `sfa40` sensor with id `hcho` on `${addr_sfa40}`. It is airQ-only and never included by `model-mini.yaml`.
  - `firmware/README.md`: per-unit device files, flashing over USB-C (`esphome run`), adding `hcho.yaml` to a unit's packages, calibration notes (ASC versus forced recalibration outdoors, temperature-compensation tuning), and the note that holding the button at power-on enters download mode.
  - `docs/validation/results-template.md`: one table per spec §6.11 test, with columns for setup, readings, pass/fail and notes.
  - `.github/workflows/firmware.yml`
- Modify: `airq-example.yaml`, adding `hcho.yaml` as a commented-out package line with a one-line explanation.
- Test: `tests/test_firmware_config.py`, adding `test_hcho_package`

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Write the failing test** `test_hcho_package`. It asserts three things:
  - `packages/hcho.yaml` exists and defines a sensor with `platform: sfa40` and `id: hcho`.
  - The merged `model-mini.yaml` package tree never references `hcho.yaml`.
  - `airq-example.yaml` mentions `hcho.yaml` only in a comment.

  Run it. Expected: **FAIL**, file not found.
- [ ] **Step 2: Write `hcho.yaml`.** Check the `sfa40` keys and the default address in the ESPHome docs; if the address differs, correct it in `interface.yaml` and `pins.yaml` together.
- [ ] **Step 3: Write the CI workflow** with three jobs on `ubuntu-latest`:
  - `host-tests`: `g++ -std=c++17 -Wall -Werror` on `test_airq_logic.cpp`, then run it.
  - `config-tests`: pytest.
  - `esphome`: install ESPHome 2026.11, copy the example secrets, run `esphome config` and `esphome compile` for both example files, and cache `~/.platformio` and `.esphome`.
- [ ] **Step 4: Compile both models locally:** `esphome compile firmware/esphome/airq-example.yaml`, then the same for `airq-mini-example.yaml`. Expected: `SUCCESS` for both. The first run downloads the toolchain and takes several minutes.
- [ ] **Step 5: Run all tests:** pytest (all pass) and the host tests (`N checks passed`).
- [ ] **Step 6: Commit** with the message `feat(firmware): HCHO option, CI, firmware and validation docs`.
