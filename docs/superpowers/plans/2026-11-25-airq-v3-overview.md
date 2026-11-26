# airQ v3: plan overview

**Spec:** `docs/superpowers/specs/2026-11-25-airq-v3-design.md` (approved 2026-11-25)

The spec covers three subsystems. Each can be built and tested on its own, so each has its own plan. They meet at two contracts, both defined in Plan 1, Task 1:

- **`hardware/interface.yaml`** is the single source of truth shared by the PCB and the firmware: GPIO assignments, I²C addresses and connector pinouts.
- **The board STEP files and outline limits** are what the PCB hands to the enclosure: board size limits plus the KiCad STEP exports.

| Plan | Delivers | Starts when | Blocks |
|---|---|---|---|
| [1: Repo foundation and firmware](2026-11-25-airq-v3-1-firmware.md) | Repo layout, interface contract, ESPHome firmware for both models, logic unit tests, CI | Now | Plan 2 (needs `interface.yaml`) |
| [2: PCB](2026-11-25-airq-v3-2-pcb.md) | KiCad 10 main board and SHT45/light "sense tongue" board; DRC-clean, with JLCPCB Economic-tier fab files and STEP | Plan 1 Task 1 done; KiCad 10 installed | Plan 3 (needs the STEP files) |
| [3: Enclosures](2026-11-25-airq-v3-3-enclosure.md) | Parametric SolidCraft models of airQ and airQ mini, light guides, test coupons, 3MF and STEP | Plan 2 STEP exported (a placeholder board allows an early start) | The build |

## Owner actions (can't be automated)

**Now, in parallel with Plan 1:**
1. **Order 11 × Sensirion SEN66** (10 units plus 1 spare). Lead times run up to 17 weeks. Also buy **SEN6x cables** (JST GH 6-pin), one per module, if they aren't included.
2. **Order e-ink evaluation panels:** 1–2 × GoodDisplay **GDEY029T94** and 1–2 × **Waveshare 2.9″ V2** (bare panel, 24-pin FPC).
3. **Install KiCad 10:** `winget install KiCad.KiCad`. Plan 2 needs it.
4. *Optional, to test firmware early:* a Seeed **XIAO ESP32-C6**, plus SHT45, BMP585 and VEML7700 breakouts with Qwiic cables, and a JST-GH-to-Dupont lead for the SEN66.

**After Plan 2:**
- **Prototype order:** at JLCPCB, fabricate 5 and assemble 2 of each board on the Economic tier (main board plus sense tongue).

**After Plan 3:**
- **Print test coupons**, report the fit, then print the enclosures.

**Build and validation**, with the assistant guiding (spec §6.11):
1. Assemble both prototypes.
2. Flash them with `esphome run` over USB-C.
3. Run every §6.11 test and record the results in `docs/validation/results.md`, using the template from Plan 1 Task 6.
4. Fix any issues.
5. Recompute the per-unit cost from the JLCPCB quote plus the sensor and panel invoices. It must be under $100 for both models (spec §7).
6. Place the **production order**: fabricate 10, assemble 8 of each board.
7. Build units 3–10.
8. Publish.

## Spec deviations decided while planning (all within what §9 leaves to the builder)

- **SHT45 and VEML7700 move to a tiny "sense tongue" board,** cabled to the main board with a Qwiic (JST SH 4-pin) lead.
  - In the mini, the main board sits above the SEN66. A tongue on the main board can't reach the intake air there, so a separate board is the only way to meet §6.2's isolation rule in both models.
  - The main board therefore gets **two** Qwiic sockets: one for the tongue, one for the optional SFA40.
  - Cost: about +$3 per unit for the tongue board's own assembly fees. Estimated cost becomes about $94 for the airQ and about $85 for the mini, both still under the cap.
- **Very long press (≥ 15 s) reboots into ESPHome's safe mode**, not "into the Wi-Fi fallback access point".
  - ESPHome can't force its fallback access point at runtime. It starts that access point automatically whenever the saved network is unreachable, which covers re-provisioning.
  - Safe mode keeps over-the-air recovery available.
- **E-ink refresh rule made consistent.**
  - Spec §6.4 asks for both "every ~3 min, sooner on a band change" and "never more often than 180 s", which conflict.
  - The plan uses: **refresh when the displayed values have changed and at least 180 s have passed since the last refresh**, with a full refresh replacing every 6th refresh. That's about 3 minutes, and the 180 s floor always wins.
- **Light changes are smoothed** with a small hysteresis margin (CO₂ 25 ppm, PM2.5 0.5 µg/m³), so the light doesn't flicker when a reading sits right on a threshold. The spec is silent on this; a reasonable owner would expect it.

## Decisions made while executing Plan 1

- **R24, bare entity names.** Entities are named `CO2`, `PM2.5`, `Status light`, ... without the `friendly_name` prefix, because Home Assistant's ESPHome integration already prefixes the device name; otherwise HA shows "airQ airQ CO2".
- **R25, ASC switch in Home Assistant via a boot-time setter plus restart.** The spec §6.10 CO₂ self-calibration switch exists again; `sen6x` only reads the setting in its setup chain, so the switch value is copied into the component in an `on_boot` hook (priority 700, between the switch restore at 798 and sen6x setup at 600) and a user change restarts the unit after 2 s.
- **R26, placeholder-to-value refresh bypass.** The first e-ink paint happens while the sensors are still starting and shows "--"; the 180 s floor is skipped once real numbers replace the placeholders, so the display is not blank for 3 minutes after every boot.
- **R27, a short press clears Night mode.** While Night mode is on the light is dark, so a short press used to do nothing visible; it now leaves Night mode and turns the light on.
- **R28, `sen6x_has_co2`.** SEN62/SEN65/SEN68 have no CO₂, which left the airQ light dark whenever PM was green; with `sen6x_has_co2: "false"` the single light follows PM2.5 alone (on the mini the CO₂ half stays dark).
- **R29, colour bands as substitutions.** The spec §6.5 thresholds are the defaults of `co2_yellow` ... `pm25_purple_max`, so owners can retune the bands without touching C++.
- **Stale-reading guard.** Every sensor output has a 120 s `timeout` filter (publishes NaN), because the sen6x driver never publishes NaN on I²C failure and a loose cable would otherwise freeze the light and display on the last value (possibly green).
- **Fallback access point has a password** (`ap_password` secret), since the captive portal exposes an unauthenticated firmware upload.
- **FRC implementation.** ESPHome's `sen6x` has no FRC action, so the button script suspends the component and sends the raw SEN66 command 0x6707 over the shared I²C bus; it is refused unless uptime is at least 180 s (3 min of measurement, R19).

## Decisions made while executing Plan 2

- **R22, WROOM-1-N8 and MS5611 (owner-confirmed 2026-11-25).** JLCPCB marks the spec-pinned ESP32-C6-MINI-1-N4 and BMP585 "Standard Only", so the board uses the ESP32-C6-WROOM-1-N8 (LCSC C5366877, same ESP32-C6, PCB antenna, 8 MB flash) and the TE MS5611-01BA03 (LCSC C15639) to stay on the Economic tier. Impact: the module is 25.5 x 18 mm (larger than the MINI-1) and the MS5611 adds about $2.5 per unit. The MS5611 sits at I2C 0x77 (CSB tied to GND); `interface.yaml`, `pins.yaml` and the firmware `ms5611` platform follow it (it reports hPa directly, so no scaling filter).
- **SK6812SIDE-A LEDs.** Genuine WS2812B side-view parts are Standard Only; the SK6812SIDE-A is WS2812-protocol compatible, so the firmware uses `chipset: SK6812`.
- **Tongue front edge.** The sense tongue's front edge is the long edge opposite the cable (R34); the VEML7700 faces it.
- **J_EPD pin 4/5 correction.** Pins 4 and 5 of the e-ink FPC connector were corrected in the board design and `interface.yaml`.
- **J_SEN66 pins 5/6 are NC.** The SEN66 pins 5 and 6 are not connected on the board.
- **E-ink FPC fit in the airQ: extension (owner decision 2026-11-26).** The GDEY029T94's FPC tail leaves a short end of the panel and is 14.4 mm long, so with the panel landscape on the airQ's front face it cannot reach J7 at the main board's front-edge centre (about 22.7 mm short), and in the 95 mm case it must fold behind the panel (79.0 + 14.4 mm is more than the ~91 mm interior). The owner chose option (b): a 24-pin 0.5 mm adapter at the panel's tail end, behind the panel, and a 24-pin 0.5 mm FFC to J7 as placed. No board change; J7 stays where the owner approved it. The prototype must show the panel's boost (GDR, RESE) working through the extension, and pin 1 arriving on J7 pin 1, before airQ boards are ordered beyond the prototype round. The analysis and the pin-order rule are in `hardware/README.md`, "E-ink FPC fit (airQ)"; Plan 3 models the tail from `interface.yaml` `mechanical.main.fpc.panel_tail` and routes the FFC per `mechanical.main.fpc.airq_fit`.
