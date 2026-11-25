# airQ v3 firmware (ESPHome 2026.11.1)

Two models share one code base: **airQ** (e-ink display) and **airQ mini** (no display). Each physical unit has its own small device file in `firmware/esphome/`, based on `airq-example.yaml` or `airq-mini-example.yaml`.

## Setup and flashing

1. Copy `firmware/esphome/secrets.example.yaml` to `firmware/esphome/secrets.yaml` and fill in your values. `secrets.yaml` must sit next to the device files. It is gitignored.
2. Copy an example file (e.g. to `kitchen.yaml`) and set `name` / `friendly_name`.
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
| `epd_model` | E-ink panel model (airQ only), default `waveshare-2.9in-v2`. |
| `co2_asc` | `"true"` (default) or `"false"` to disable automatic self-calibration. |

## Optional HCHO sensor (airQ only)

Uncomment the `hcho: !include packages/hcho.yaml` line in your airQ device file to add an SFA40 formaldehyde sensor (I²C 0x5D). It is never included in the mini.

## Button and light

- Press under 1 s: toggle the light.
- Hold 5 to 15 s: forced CO₂ recalibration to 420 ppm (see below). White blink ×3 means success, red ×3 means failed or refused.
- Hold 15 s or more: reboot into safe mode.

In Home Assistant, the **Status light** and **Night mode** switches control the light; it dims automatically with room brightness.

## Calibration

- **Automatic self-calibration (ASC)** is on by default and assumes the room is ventilated to fresh air regularly. In rarely ventilated rooms set `co2_asc: "false"` and calibrate manually.
- **Forced recalibration (FRC):** power the unit outdoors (for example from a USB power bank), wait at least 3 minutes so the sensor has been measuring in fresh air, then hold the button for 5 to 15 s. The unit refuses (red ×3) if it has been running for less than 3 minutes.
- **Temperature compensation:** the `temperature_compensation` values in `sensors.yaml` are placeholders. Tune them during validation against a reference thermometer (see `docs/validation/results-template.md`).

## Display

The e-ink rotation may need to be 90 or 270 depending on how the display is mounted. During validation check on the real panel that "40000" and the ₂ µ ³ glyphs render correctly.

## Tests and CI

```
uv run --with pytest --with pyyaml pytest tests -v
mkdir -p build && g++ -std=c++17 -Wall -Werror -I firmware/esphome/include firmware/tests/test_airq_logic.cpp -o build/test_airq_logic && build/test_airq_logic
```

CI (`.github/workflows/firmware.yml`) runs both, then `esphome config` and `esphome compile` for both example files with ESPHome 2026.11.1.
