# airQ v3 firmware (ESPHome 2026.11.1)

Two models share one code base: **airQ** (e-ink display) and **airQ mini** (no display). Each physical unit has its own small device file in `firmware/esphome/`, based on `airq-example.yaml` or `airq-mini-example.yaml`.

## Setup and flashing

1. Copy `firmware/esphome/secrets.example.yaml` to `firmware/esphome/secrets.yaml` and fill in your values. `secrets.yaml` must sit next to the device files. It is gitignored. **Generate your own `api_key` and set your own `ap_password`** (the example values are public placeholders; the fallback setup hotspot and its `/update` page are protected only by `ap_password`):

   ```
   python -c "import base64,os;print(base64.b64encode(os.urandom(32)).decode())"   # api_key (or: openssl rand -base64 32)
   python -c "import secrets;print(secrets.token_urlsafe(12))"                      # ap_password / ota_password
   ```
2. Copy an example file (e.g. to `kitchen.yaml`) and set `name` / `friendly_name`. Entity names are bare (`CO2`, `PM2.5`, ...) because Home Assistant already prefixes them with the device name, so set `friendly_name` to the room (e.g. `Kitchen`) and you get entity ids like `sensor.kitchen_co2`, matching the v2 dashboards.
3. Connect the unit over USB-C and run, from `firmware/esphome/`:

   ```
   esphome run kitchen.yaml
   ```

   Later updates can go over the air (OTA). On Windows, run `esphome compile` from PowerShell (Git Bash breaks the ESP-IDF install).

If the unit does not enter flashing mode, hold the button while powering on: this enters download mode (GPIO9 / BOOT).

## Substitutions

Override these under `substitutions:` in the device file:

| Substitution | Meaning |
|---|---|
| `sen6x_model` | Sensor type, default `SEN66`. |
| `led_count` | Number of status LEDs. The explicit segment bounds must be overridden together with it: `led_first` / `led_last` (airQ), or `led_co2_first` / `led_co2_last` / `led_pm_first` / `led_pm_last` (mini). |
| `light_cap` | Maximum light brightness, 0 to 1 (default 0.5). |
| `epd_model` | E-ink panel model (airQ only), default `waveshare-2.9in-v2`. For the Good Display GDEY029T94 panel use `goodisplay-gdey029t94-2.9`. |
| `co2_asc` | `"true"` (default) or `"false"`: first-boot default of the **CO2 auto-calibration** switch (see Calibration). |
| `sen6x_model` / `sen6x_has_co2` | Sensor variant and whether it measures CO₂ (default `"true"`); see the variants table. |
| `co2_yellow`, `co2_orange`, `co2_red` | CO₂ colour thresholds in ppm (defaults 800 / 1000 / 1500): green below `co2_yellow`, yellow below `co2_orange`, orange below `co2_red`, red above. |
| `pm25_green_max`, `pm25_yellow_max`, `pm25_orange_max`, `pm25_red_max`, `pm25_purple_max` | PM2.5 thresholds in µg/m³ (defaults 9.0 / 35.4 / 55.4 / 125.4 / 225.4): each is the inclusive upper edge of its colour; above `pm25_purple_max` is maroon. |

Note: `full_update_every: 6` in the display package needs a panel with partial refresh (the Waveshare 2.9" V2 and GDEY029T94 both have it); for a panel without it set `full_update_every: 1`.

## SEN6x variants

| Variant | Works | Set |
|---|---|---|
| SEN66 (default) | PM, CO₂, VOC, NOx, T/RH | nothing |
| SEN63C | PM, CO₂, T/RH (no VOC/NOx) | `sen6x_model: SEN63C` |
| SEN65 | PM, VOC, NOx, T/RH (no CO₂) | `sen6x_model: SEN65`, `sen6x_has_co2: "false"` |
| SEN68 | PM, VOC, NOx, T/RH, formaldehyde (no CO₂) | `sen6x_model: SEN68`, `sen6x_has_co2: "false"` |
| SEN69C | PM, CO₂ (weaker than SEN66), VOC, NOx, T/RH, formaldehyde | `sen6x_model: SEN69C` |
| SEN62 | PM and T/RH only | `sen6x_model: SEN62`, `sen6x_has_co2: "false"` |

Outputs a variant lacks are logged as errors at boot and stay empty. With `sen6x_has_co2: "false"` the airQ light follows PM2.5 alone; on the mini the CO₂ half of the light simply stays dark. The installed `sen6x` component exposes formaldehyde for SEN68 and SEN69C; to enable it add this to your device file:

```
sensor:
  - id: !extend sen
    formaldehyde:
      name: Formaldehyde
```

## Optional HCHO sensor (airQ only)

Uncomment the `hcho: !include packages/hcho.yaml` line in your airQ device file to add an SFA40 formaldehyde sensor (I²C 0x5D). It is never included in the mini.

## Button and light

- Press under 1 s: toggle the light. If Night mode is on, the press leaves Night mode and turns the light on instead.
- Hold 5 to 15 s: forced CO₂ recalibration to 420 ppm (see below). White blink ×3 means success, red ×3 means failed or refused.
- Hold 15 s or more: reboot into safe mode.

In Home Assistant, the **Status light** and **Night mode** switches control the light; it dims automatically with room brightness.

If a sensor stops delivering readings (for example a loose SEN66 cable) its value becomes unavailable after 120 s, and the light goes dark and the display shows "--" instead of the last value.

## Calibration

- **Automatic self-calibration (ASC)** is on by default and assumes the room is ventilated to fresh air regularly. In rarely ventilated rooms turn off the **CO2 auto-calibration** switch in Home Assistant (or set `co2_asc: "false"` for the first-boot default) and calibrate manually. The sensor reads the setting only at start-up, so changing the switch restarts the unit after 2 s; the state is remembered across reboots.
- **Forced recalibration (FRC):** power the unit outdoors (for example from a USB power bank), wait at least 3 minutes so the sensor has been measuring in fresh air, then hold the button for 5 to 15 s. The unit refuses (red ×3) if it has been running for less than 3 minutes.
- **Temperature compensation:** the `temperature_compensation` values in `sensors.yaml` are placeholders. Tune them during validation against a reference thermometer (see `docs/validation/results-template.md`).

## Display

The e-ink rotation may need to be 90 or 270 depending on how the display is mounted. During validation check on the real panel that "40000" and the ₂ µ ³ glyphs render correctly.

## Tests and CI

```
uv run --with pytest --with pyyaml pytest tests -v
mkdir -p build && g++ -std=c++17 -Wall -Wextra -Werror -I firmware/esphome/include firmware/tests/test_airq_logic.cpp -o build/test_airq_logic && build/test_airq_logic
```

On a Windows host without `g++`, use the zig toolchain instead:

```
uv run --with ziglang python -m ziglang c++ -std=c++17 -Wall -Wextra -Werror -I firmware/esphome/include firmware/tests/test_airq_logic.cpp -o build/test_airq_logic.exe && build/test_airq_logic.exe
```

CI (`.github/workflows/firmware.yml`) runs both, then `esphome config` and `esphome compile` for both example files, plus `esphome config` for an HCHO-enabled copy of the airQ example, with ESPHome 2026.11.1.
