# airQ v3 validation results

Copy this file per unit (e.g. `results-unit1.md`) and fill it in. Acceptance criteria are from the design spec section 6.11.

Unit: ______  Model (airQ / mini): ______  Firmware commit: ______  Date: ______  Tester: ______

## 1. Self-heating

Pass: internal over-temperature < 5 °C before compensation. Method (Sensirion): device on a wooden plate, reference thermometer at least 20 cm away and not above it.

| Setup | Readings | Pass/Fail | Notes |
|---|---|---|---|
| | | | |

## 2. Temperature and humidity after compensation (24 h)

Pass: within ±0.5 °C and ±3 %RH of a reference thermometer/hygrometer over 24 h.

| Setup | Readings | Pass/Fail | Notes |
|---|---|---|---|
| | | | |

## 3. Light at brightness cap vs off

Pass: compensated temperature changes ≤ 0.2 °C.

| Setup | Readings | Pass/Fail | Notes |
|---|---|---|---|
| | | | |

## 4. VOC ink-pen test (pen 10 cm away)

Pass: VOC index rises within 30 s and recovers within 1 min.

| Setup | Readings | Pass/Fail | Notes |
|---|---|---|---|
| | | | |

## 5. CO₂ outdoors and side by side with a v2 unit's SCD4x

Pass: within the SCD41 spec of each other; about 420 ppm outdoors.

| Setup | Readings | Pass/Fail | Notes |
|---|---|---|---|
| | | | |

## 6. PM2.5 side by side with a v2 unit's SPS30 (several days, including cooking)

No hard pass mark (no independent SEN6x data). Report agreement (R² and bias).

| Setup | Readings (R², bias) | Pass/Fail | Notes |
|---|---|---|---|
| | | n/a | |

## 7. Fan noise

Pass: not audible at 1 m in a quiet room, no rattle.

| Setup | Readings | Pass/Fail | Notes |
|---|---|---|---|
| | | | |

## 8. Cost

Pass: BOM total < $100 per unit at the order quantity.

| Setup | Readings | Pass/Fail | Notes |
|---|---|---|---|
| | | | |

## Display checks (airQ only)

| Setup | Readings | Pass/Fail | Notes |
|---|---|---|---|
| Rotation correct for mounting (90 vs 270) | | | |
| "40000" and the ₂ µ ³ glyphs render on the real panel | | | |
