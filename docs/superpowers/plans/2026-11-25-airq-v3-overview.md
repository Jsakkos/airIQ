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
