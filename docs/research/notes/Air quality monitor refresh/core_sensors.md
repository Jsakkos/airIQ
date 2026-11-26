# Core indoor air quality sensors (CO2, PM, VOC/NOx, T/RH/P, combo modules), status as of late Nov 2026

Scope notes for the report writer:
- Snapshot date: 2026-11-25. JLCPCB/LCSC prices and stock come from JLCPCB's public parts-search API, queried 2026-11-25 (the same data appears on the `jlcpcb.com/partdetail/<C-number>` pages linked below). Prices are USD per unit at qty 1 / qty 100. Stock changes daily; treat them as indicative. Every sensor IC listed is in JLCPCB's "Extended" library (API field `componentLibraryType = expand`), none in "Basic".
- "Native ESPHome" means the component appears in the official ESPHome component index ([esphome.io/components](https://esphome.io/components/)). ESPHome API docs show version 2026.10.2 as current ([ESPHome API docs](https://api-docs.esphome.io/pmsa003i_8cpp_source)).
- The user's 2021 build used SCD40/41 + SGP40 + SPS30 + BMP280. The notes call out what changed for each of those parts.

---

## Q1. CO2: SCD40 vs SCD41 vs SCD43 vs SCD30 vs STCC4 vs Senseair (S8/Sunlight/S12) vs Winsen MH-Z19C/E vs Cubic CM1106 vs Infineon PAS CO2. Principle, accuracy per $ and per mm³, independent comparisons

### Takeaway
The SCD4x family is still the best accuracy-per-$-per-mm³ choice for a factory-assembled SMT board. SCD43 (released 2025) has the tightest spec, ±(30 ppm + 3%), and is the drop-in upgrade from the SCD40/41. The SCD41 datasheet spec was also tightened at 400–1000 ppm. The STCC4 is not a precision part: it is thermal-conductivity (not optical), specced at ±(100 ppm + 10%), drifts with temperature, and lost AirGradient's 2026 head-to-head to the Senseair S12 (true NDIR) and the SCD4x. Two parts to watch: the Senseair S12, an SMD true-NDIR part with ±(30 ppm + 3%) and <34 µA that is still in sampling/prototype, and the Sensirion SCD53 ("Upcoming", ±(30 ppm + 3%), stability that does not depend on fresh-air recalibration). Neither has a native ESPHome component.

### Cited Findings

**Comparison table (datasheet / manufacturer numbers)**

| Part | Principle | Specified range | Accuracy (datasheet) | Calibration / drift | Interface | Supply; avg / peak current | Size (mm) | Price (JLC/LCSC, 1 pc / 100 pc; stock 2026-11-25) | ESPHome | Status / caveats |
|---|---|---|---|---|---|---|---|---|---|---|
| Sensirion SCD40-D-R2 | Photoacoustic NDIR (PASens) | 400–2000 ppm (output 0–40k) | ±(50 ppm + 5% rdg) | ASC (weekly 400 ppm), FRC; lifetime >10 yr | I2C | 2.4–5.5 V; 15 mA periodic, 3.2 mA low-power periodic; peak 175 typ / 205 max mA | 10.1×10.1×6.5 | $15.92 / $15.04; 2,358 in stock ([JLC C3659421](https://jlcpcb.com/partdetail/C3659421)) | Native `scd4x` | Active; "base accuracy" variant |
| Sensirion SCD41-D-R2 | Photoacoustic NDIR | 400–5000 ppm | ±(50 ppm + 2.5%) @400–1000; ±(50 ppm + 3%) @1001–2000; ±(40 ppm + 5%) @2001–5000 | ASC/FRC; single-shot mode 0.45 mA avg (1 meas / 5 min) | I2C | same as SCD40 | 10.1×10.1×6.5 | $19.46 / $15.61; 378 in stock ([JLC C3659294](https://jlcpcb.com/partdetail/C3659294)) | Native `scd4x` | Active |
| Sensirion SCD43-D-R2 | Photoacoustic NDIR | 400–5000 ppm | ±(30 ppm + 3%) | ASC/FRC; single-shot | I2C | 2.4–5.5 V; 15 mA avg, 205 mA max | 10.1×10.1×6.5 | $17.87 / $17.33; **0 in stock** ([JLC C50182965](https://jlcpcb.com/partdetail/C50182965)) | Works via `scd4x` (same command set; not named in docs) | Active, new; ASHRAE 62.1 addendum d, Title 24, RESET B, WELL v2 |
| Sensirion STCC4-D-R3 | **Thermal conductivity** (not optical) | 400–5000 ppm (output 380–32,000) | ±(100 ppm + 10%) | ASC (weekly fresh air); FRC; 12 h initial operation; up to 1 h warm-up after >3 h off; lifetime 10 yr | I2C (0x64/0x65) plus a controller port for an SHT4x | 2.7–5.5 V; 950 µA continuous, ~100 µA single-shot (10 s), peak 3.7 typ / 4.2 max mA | 4×3×1.2 | $11.33 / $8.20; 2,590 in stock ([JLC C49191471](https://jlcpcb.com/partdetail/C49191471)) | Native `stcc4` | New (DS v1, June 2025); needs an external SHT4x for accuracy; 10–40 °C operating |
| Sensirion SCD30 | Dual-channel NDIR module | 400–10,000 ppm | ±(30 ppm + 3%) | ASC/FRC | I2C, Modbus, PWM | 3.3–5.5 V; 19 mA avg, 75 mA max | 35×23×7 | $52.99 / $49.14; 183 in stock ([JLC C1519271](https://jlcpcb.com/partdetail/C1519271)) | Native `scd30` | Module (not SMT); no lifecycle label on page |
| Sensirion SCD53 | Photoacoustic NDIR "combined with laser technology" | 400–10,000 ppm | ±(30 ppm + 3%) | "Long-term stability independent of fresh-air-based recalibration" | I2C | 3–5.5 V; 1 mA avg | not given (reflow LGA) | n/a | none | **Upcoming**, flyer dated 03/2026, target market DCV |
| Senseair S8 (LP/Residential/Commercial) | NDIR | 400–10,000 ppm | ±(40 ppm + 3%) | Maintenance-free, ABC; lifetime >15 yr | UART/Modbus | 4.5–5.25 V; 18 mA avg, 300 mA peak | 33.9×19.8×8.7 | not found on JLC | Native `senseair` (UART; ABC actions) | Active; S88 is "a refresh of our S8" |
| Senseair Sunlight (DT variant 006-0-0020) | NDIR (LED) | 0–10,000 ppm | ±(30 ppm + 3%) 0–3000 ppm | DT variant: "No ABC/ASC or field calibration required"; >10 yr | UART, I2C | 3.05–5.5 V; 1–34 µA avg, <125 mA peak | 34×21×12 | not checked | none | Datasheet marked preliminary |
| Senseair S12 | True NDIR, solid-state LED, **SMD reflow** | 400–5000 standard, to 10,000 extended | ±(30 ppm + 3%) to 5000 | ABC must be enabled for maintenance-free use; FRC; >15 yr | UART, I2C | 3.05–5.5 V; <34 µA avg, <20 mA peak | 18×15×7 (web page says 6 mm H) | quote only | none | Sampling; standard S12 listed as "Prototype"; volume production planned for 2026 |
| Infineon XENSIV PASCO2V15 | Photoacoustic (MEMS microphone) | 0–32,000 ppm | ±(50 ppm + 5%) @400–3000 | ABOC (automatic baseline offset) + algorithms; 10 yr | I2C, UART, PWM | 3.3 V logic + **5 V emitter**; ~30 mW avg; 290 mA emitter peak | 14×13.8×7.5 | $24.19 / $22.99; 5 in stock ([JLC C26655608](https://jlcpcb.com/partdetail/C26655608)) | **None native** | PASCO2V01 (12 V) was ±(30 ppm + 3%) @400–5000 |
| Winsen MH-Z19C | NDIR | 400–2000/5000/10,000 | ±(50 ppm + 5%) | Factory calibrated; ABC not described on page; >10 yr | UART, PWM | 5.0 ± 0.1 V; <40 mA avg, 125 mA peak | 32.9×19.7×8.6 | not stocked at JLC | Native `mhz19` | Through-hole module |
| Winsen MH-Z19E | NDIR | 400–2000/5000/10,000 | ±(50 ppm + 5%) | — | UART/PWM | — | — | — | via `mhz19` (not explicitly listed) | — |
| Cubic CM1106SL-NS | Single-beam NDIR with ABC | 0–5000 | ±(50 ppm + 5%) | ABC | UART, I2C | 37 µA (2-min cycle default) / 74 µA (1-min cycle) | 33×19.7×8.9 | not found | Native `cm1106` (UART) | Note: LCSC's "CM1106" hits are an unrelated CIMO IC |

Sources for the table:
- SCD40/41/43 accuracy, repeatability ±10 ppm, response 60 s, currents, 2.4–5.5 V, >10-yr lifetime, ASC weekly-400-ppm requirement, FRC ≥5 days after assembly, extra drift per year after year 5 of typ ±(5 ppm + 0.5%) / max ±(5 ppm + 2%): SCD4x datasheet v1.7, April 2025 — [Sensirion SCD4x datasheet](https://sensirion.com/media/documents/48C4B7FB/67FE0194/CD_DS_SCD4x_Datasheet_D1.pdf)
- SCD41's older spec was ±(40 ppm + 5%) over 400–5000 ppm (v1.5, July 2023): [Mouser SCD4x summary](https://www.mouser.in/new/sensirion/sensirion-scd40); [SparkFun copy of v1.5](https://cdn.sparkfun.com/assets/9/7/5/7/0/Sensirion_SCD4x_Datasheet.pdf)
- SCD43 page (±(30 ppm + 3%), 0–40,000 output, 15 mA avg / 205 mA max, 10.1×10.1×6.5 mm, building standards): [Sensirion SCD43](https://sensirion.com/products/catalog/SCD43); [Sensirion SCD43 launch PR](https://sensirion.com/company/news/press-releases-and-news/article/sensirion-launches-scd43-co-sensor-with-stringent-building-standard-compability)
- STCC4 (thermal conductivity, accuracy, ASC, warm-up, initial operation, currents, 0x64/0x65, SHT4x requirement, 10–40 °C, 20–80 %RH, pressure range 850–1100 hPa without / 700–1100 hPa with compensation, metal-cap LGA, no board wash, 10-yr lifetime): [STCC4 datasheet D1 v1, June 2025 (distributor copy)](https://cdn.soselectronic.com/productdata/dd/9f/50d5ffc9/stcc4-d-r3.pdf); [Sensirion STCC4](https://sensirion.com/products/catalog/STCC4)
- STCC4 thermal-conductivity caveat, quoted from the datasheet: "Any variation in the gas composition results in the thermal conductivity deviating from fresh air ... and is interpreted as a change in CO2 concentration." — [STCC4 datasheet](https://cdn.soselectronic.com/productdata/dd/9f/50d5ffc9/stcc4-d-r3.pdf)
- STCC4 design-in guide (per search summary, not fully read) says the sensor is sensitive to local temperature deviations from 25 °C and to rapid temperature changes, and needs continuous T/RH input from an SHT4x — [STCC4 Design-In Guide](https://sensirion.com/media/documents/4B786C73/68E5EE93/CD_AN_STCC4_Design-In_Guide_D1_1.pdf)
- SCD30 specs: [Sensirion SCD30](https://sensirion.com/products/catalog/SCD30)
- SCD53 (Upcoming; ±(30 ppm + 3%); 400–10,000 ppm; 1 mA; 3–5.5 V; "stability independent of fresh-air-based recalibration"; robust to dust, vibration and mechanical forces): [Sensirion SCD53](https://sensirion.com/products/catalog/SCD53)
- Senseair S8: [Senseair S8](https://senseair.com/product/s8/); product lineup, S88 as "refresh", S12 "New": [Senseair products](https://senseair.com/products/)
- Senseair Sunlight DT (006-0-0020, no ABC needed, RESET grade A, ±(30 ppm + 3%), 1–34 µA, <125 mA peak, 34×21×12): [PSP16381 Rev 1](https://rmtplusstoragesenseair.blob.core.windows.net/docs/publicerat/PSP16381.pdf); standard Sunlight page: [Senseair Sunlight](https://senseair.com/product/sunlight-co2/)
- Senseair S12 (±(30 ppm + 3%) to 5000 ppm, ±(50 ppm + 3%) or worse at 5001–10,000, <34 µA, <20 mA peak, 18×15×7, >15 yr, ABC required for maintenance-free operation, reflow): [S12 datasheet PSP15871 Rev 2](https://www.sensor-test.de/assets/Fairs/2026/ProductNews/PDFs/PSP15871-v2.pdf); [Senseair S12 page](https://senseair.com/product/s12-co2/) (lists 012-0-0001 as "Prototype"); volume production planned for 2026 — [Electronics-Lab](https://www.electronics-lab.com/senseair-unveils-ultra-compact-smd-reflow-solderable-co2-sensor/)
- PASCO2V15 specs and the V01 comparison: [CNX Software](https://www.cnx-software.com/2024/10/04/infineon-pasco2v15-co2-sensor-achieves-%c2%b150-ppm-accuracy-with-built-in-microphone-and-ir-emitter/)
- MH-Z19C: [Winsen MH-Z19C](https://www.winsen-sensor.com/product/mh-z19c.html); MH-Z19E ±(50 ppm + 5%): [Winsen MH-Z19E](https://winsen-sensor.com/product/mh-z19e.html)
- CM1106SL-NS: [CO2Meter CM1106SL-N](https://co2meter.com/products/cm-1106sl-n-low-power-ndir-co2-sensor)
- ESPHome support: [scd4x](https://esphome.io/components/sensor/scd4x/) (docs say single-shot is "only available on scd41"; supports ASC, altitude/pressure compensation, and an external pressure sensor via `ambient_pressure_compensation_source`); [stcc4](https://esphome.io/components/sensor/stcc4/) (supports `temperature_source`/`humidity_source` and pressure compensation); [scd30](https://esphome.io/components/sensor/scd30/); [senseair](https://esphome.io/components/sensor/senseair/) (S8 over UART, with ABC enable/disable/period actions); [mhz19](https://esphome.io/components/sensor/mhz19/); [cm1106](https://esphome.io/components/sensor/cm1106/). No Infineon PAS CO2 or Senseair Sunrise/Sunlight/S12 component appears in the index: [ESPHome components](https://esphome.io/components/)

**Independent and semi-independent comparisons**
- AirGradient, "CO₂ Sensor Technologies: Optical NDIR vs Photoacoustic vs Thermal Conductivity" (Achim Haug, 12 Mar 2026). It compared the Senseair S12, a Sensirion SCD4x and the Sensirion STCC4 in one enclosure for a portable device ("AirGradient Go"), with no reference-grade instrument. In ~90 min of stable outdoor air after calibration to 400 ppm: peak-to-peak S12 ~10 ppm, SCD4x ~26 ppm, STCC4 ~136 ppm; standard deviation 1.84 / 4.46 / 25.47 ppm; sample-to-sample noise 0.38 / 0.89 / 3.11 ppm — [AirGradient blog](https://www.airgradient.com/blog/co2-sensor-technologies/)
- Same post: the STCC4's main problem was slow drift; it never reached ambient during car/outdoor transitions; in one window it correlated with temperature at Pearson ~0.991 after a ~5-min lag; some units failed and did not recover on their own. The author judged it "unreliable for a portable monitor" but said it performs well indoors when conditions are calm. The SCD4x showed occasional jumps but was "predictable", the "safer fallback" to the S12 — [AirGradient blog](https://www.airgradient.com/blog/co2-sensor-technologies/)
- Senseair (the S12's vendor, so not independent) published its own summary of the AirGradient test, titled "Senseair S12 crowned the winner" (27 Mar 2026) — [Senseair](https://senseair.com/senseair-s12-crowned-the-winner/)
- Sensirion's STCC4 testing guide recommends checking STCC4 accuracy against a reference of at least ±(50 ppm + 5%), naming the SCD43, the Edinburgh Gascard NG and the LI-COR LI-850 — [STCC4 Testing Guide](https://sensirion.com/media/documents/D0ABC18E/6A1D5183/CD_AN_STCC4_Testing-Guide_D1.pdf)
- Adafruit sells an STCC4 + SHT41 breakout (product 6478). Its guide calls the STCC4 "really tuned just for indoor air measurement applications" and says it needs roughly weekly outdoor-air exposure for its 400 ppm baseline. The guide has no measured comparison data — [Adafruit STCC4 guide](https://learn.adafruit.com/adafruit-stcc4-and-sht41-co2-temperature-humidity-sensor?view=all)

### Inferences
- **Accuracy at 1000 ppm, worked from the datasheet formulas:** SCD43 ±60 ppm; SCD41 ±75 ppm (new v1.7 spec); SCD40 ±100; SCD30 ±60; S12 ±60; Sunlight ±60; S8 ±70; PASCO2V15 ±100; MH-Z19C ±100; CM1106SL-NS ±100; STCC4 ±200.
- **Volume:** STCC4 14.4 mm³; SCD4x 663 mm³; PASCO2V15 ~1,450 mm³; S12 ~1,890 mm³; SCD30 ~5,640 mm³; S8 ~5,840 mm³; Sunlight ~8,570 mm³. Per mm³, the STCC4 is ~46× smaller than the SCD4x but ~3× worse in spec, and noisier and more temperature-sensitive in AirGradient's test. **The SCD4x remains the best accuracy-per-mm³ optical part.** The S12 matches SCD43 accuracy at ~3× the volume, with µA-level power.
- **Accuracy per $ (JLC 1-pc, Nov 2026):** SCD43 at $17.87 (±60 ppm) is the best value on paper. It is priced *below* the SCD41 ($19.46) but showed 0 stock. Next are the SCD41 at $19.46 (±75) and the SCD40 at $15.92 (±100). The STCC4 at $11.33 (±200) saves only ~$6–8 and needs an SHT4x anyway, which the board will have regardless. The PASCO2V15 costs more ($24) for SCD40-level accuracy and needs a 5 V rail.
- **Recommendation:** For the "flagship accuracy" board, use the **SCD43** footprint (pin- and command-compatible with SCD40/41 per the shared SCD4x datasheet), with the SCD41 as a fallback if SCD43 stock is short. Use the STCC4 only for a value/miniature build, and understand that it is a different class of sensor. Re-evaluate the **SCD53** and **S12** once they are in volume. Both aim to remove the dependence on fresh-air ASC, which matters in a home that rarely sees 400 ppm. Neither has ESPHome support today, so each would need a custom/external component.
- SCD4x peak current of 175–205 mA (and SEN66 peaks, Q5) means the 3.3 V LDO and bulk capacitance must be sized for it. Sensirion's SCD4x datasheet requires a low-noise supply with <30 mV unloaded ripple.
- ESPHome's `scd4x` docs only name the SCD41 for single-shot mode. The SCD43 supports single-shot per the datasheet, and ESPHome probably works with it unchanged, but this is unverified.
- All the photoacoustic and TC parts (SCD4x, STCC4, SEN66) rely on ASC that assumes weekly 400 ppm exposure. If the user's space never ventilates to outdoor levels, plan periodic FRC (exposed in ESPHome) or disable ASC.

### Gaps
- No independent quantitative test of the **SCD43** vs SCD41 was found. The SCD43's accuracy is vendor-only.
- Could not fetch Infineon's current PASCO2V15/V01 product pages (404). PASCO2V01 lifecycle status is unknown.
- No price found for Senseair S8/S12/Sunlight at JLC/LCSC/DigiKey (S12 is quote-only).
- The Senseair Sunrise (non-DT) and the S88 accuracy/current specs were not retrieved.
- Price and lifecycle for MH-Z19E and CM1106 were not retrieved. LCSC has no stock of MH-Z19C.
- No published Aranet or academic comparison including SCD43/STCC4/S12 was found in this pass.

---

## Q2. PM: SPS30 vs SEN5x vs SEN6x (what each variant measures) vs Plantower PMSA003/PMS5003/PMSA003I, Honeywell HPMA115, Panasonic SN-GCJA5, Cubic PM2012; independent accuracy

### Takeaway
The SPS30 is still active and is the best-validated small PM sensor in AQ-SPEC (field PM2.5 R² 0.80–0.83, lab R² 0.99). Sensirion's newer PM path is the **SEN6x** family, built on a new MEMS PM block (SPS6x) with "sheath flow" contamination protection, 3.3 V supply and I2C. The SEN5x (SEN55) is now **NRND**, with the SEN65 as its successor. SEN6x variants: **SEN60** = PM (in the 2024 datasheet; its product page now 404s); **SEN62** = PM + RH/T (launched Apr 2026, entry level); **SEN63C** = PM + RH/T + CO2 (thermal-conductivity class, ±(100 ppm + 10%)); **SEN65** = PM + RH/T + VOC + NOx; **SEN66** = PM + RH/T + VOC + NOx + CO2 (photoacoustic class, SCD41-equivalent spec); **SEN68** = PM + RH/T + VOC + NOx + HCHO; **SEN69C** = SEN68 set + CO2 (TC class, "CO2 not compliant, see SEN66"). Low-cost Plantower/Honeywell/Panasonic modules are 5 V UART (Plantower PMSA003I is I2C) and are mostly out of stock at LCSC. PM10 from every optical sensor of this class correlates poorly with reference monitors.

### Cited Findings

**SEN6x family: what each variant measures**

| Variant | PM1/2.5/4/10 | RH/T | VOC Index | NOx Index | CO2 | HCHO | I2C addr | Notes |
|---|---|---|---|---|---|---|---|---|
| SEN60 | ✔ | | | | | | 0x6C | In SEN6x DS v0.5 (Oct 2024); `sensirion.com/products/catalog/SEN60` returned 404 on 2026-11-25; not in ESPHome `sen6x` list |
| SEN62 | ✔ | ✔ | | | | | 0x6B | "Entry-level" SEN6x, global availability announced 21 Apr 2026; uses SPS6x |
| SEN63C | ✔ | ✔ | | | ✔ ±(100 ppm + 10%), 0–32,000 ppm out, 20 s τ63 | | 0x6B | "CO2 not compliant, see SEN66" |
| SEN65 | ✔ | ✔ | ✔ | ✔ | | | 0x6B | Successor to SEN55 |
| SEN66 | ✔ | ✔ | ✔ | ✔ | ✔ ±(50 + 2.5%) @400–1000, ±(50 + 3%) @1001–2000, ±(40 + 5%) @2001–5000; 0–40,000 out | | 0x6B | Recommended where CO2 compliance (RESET/WELL/Title 24) matters |
| SEN68 | ✔ | ✔ | ✔ | ✔ | | ✔ 0–1000 ppb; ±20 ppb or ±20% (larger); HCHO lifetime >6 yr | 0x6B | |
| SEN69C | ✔ | ✔ | ✔ | ✔ | ✔ ±100 ppm; 0–32,000 out | ✔ 0–2000 ppb; ±20 ppb or 20% | 0x6B | "CO2 not compliant, see SEN66 instead" |

Sources: SEN6x datasheet v0.5, Oct 2024 (variant table, PM/RH/T/VOC/NOx/CO2/HCHO specs, SEN60 address 0x6C vs 0x6B, ordering codes `SEN6x-SIN-T`) — [SEN6x datasheet copy](https://cdn.soselectronic.com/productdata/b9/20/bdca9efc/sen60-sin-t.pdf); [Sensirion SEN66](https://sensirion.com/products/catalog/SEN66); [Sensirion SEN69C](https://sensirion.com/products/catalog/SEN69C); [Sensirion SEN63C](https://sensirion.com/products/catalog/SEN63C); [Sensirion SEN62](https://sensirion.com/products/catalog/SEN62); [SEN62 press release, 21 Apr 2026](https://sensirion.com/company/news/press-releases-and-news/article/sensirion-announces-global-availability-of-the-environmental-sensing-platform-sen62). A newer SEN6x datasheet (v0.92, Dec 2025) covering SEN62 is referenced by distributors but was not retrievable — [Mouser SEN62](https://www.mouser.co.za/new/sensirion/sensirion-sen62-air-quality-sensor).

**SEN6x common specs (DS v0.5 unless noted)**
- PM: 0–1000 µg/m³; PM1/PM2.5 precision ±(5 µg/m³ + 5% m.v.) at 0–100 µg/m³ and ±10% m.v. at 100–1000; PM4/PM10 ±25 µg/m³ / ±25% m.v.; long-term drift ≤1.25 µg/m³/yr (or 1.25% m.v./yr); start-up 30 s; PM2.5 calibrated to TSI DustTrak DRX 8533 (ambient mode); 850 nm Class 1 laser product. PM4/PM10 are "calculated based on distribution profile" — [SEN6x DS](https://cdn.soselectronic.com/productdata/b9/20/bdca9efc/sen60-sin-t.pdf). (Table text was extracted from a jumbled PDF layout; the mapping of values to rows matches the SPS30-style spec but should be verified.)
- Module: lifetime >10 yr (24 h/day), acoustic <24 dB(A) at 0.2 m, weight ~20 g, sampling interval 1 s — [SEN6x DS](https://cdn.soselectronic.com/productdata/b9/20/bdca9efc/sen60-sin-t.pdf)
- RH/T (compensated for module self-heating): T ±0.45 °C typ (15–30 °C), RH ±4.5 %RH typ — [SEN6x DS](https://cdn.soselectronic.com/productdata/b9/20/bdca9efc/sen60-sin-t.pdf); [SEN66 page](https://sensirion.com/products/catalog/SEN66)
- Electrical: VDD 3.15–3.45 V in DS v0.5 (product pages say 3.15–3.6 V). Average current in measurement mode: SEN60 ~75 mA, SEN63C/SEN65 ~80 mA, SEN66 ~90 mA typ / 110 max, SEN68 ~75 mA. Peak (2 ms pulses): ~140/200 mA for most variants and **~300 typ / 350 max mA for SEN66** (as parsed from the DS table) — [SEN6x DS](https://cdn.soselectronic.com/productdata/b9/20/bdca9efc/sen60-sin-t.pdf). The SEN66 page lists 90 mA average; the SEN69C page lists 80 mA average — [SEN66](https://sensirion.com/products/catalog/SEN66), [SEN69C](https://sensirion.com/products/catalog/SEN69C)
- Size 55.2 × 25.6 × 21.3 mm — [SEN66](https://sensirion.com/products/catalog/SEN66)
- SEN66 CO2 uses SCD4x commands for FRC, and the DS references the SCD4x datasheet. Its CO2 spec is identical to the SCD41 v1.7 spec. The SEN63C's CO2 spec (±(100 ppm + 10%), 0–32,000 ppm, 20 s τ63, "accuracy after initial operation for 12 h followed by fresh air") matches the STCC4's — [SEN6x DS](https://cdn.soselectronic.com/productdata/b9/20/bdca9efc/sen60-sin-t.pdf); [STCC4 DS](https://cdn.soselectronic.com/productdata/dd/9f/50d5ffc9/stcc4-d-r3.pdf)
- Sensirion's SEN6x specification statement warns that reference instruments themselves can differ by >20% of measured value — [SEN6x Sensor Specification Statement](https://sensirion.com/media/documents/63F6CCF0/69709F54/PS_AN_SEN6x_Sensor_Specification_Statement_D1.pdf)

**Other PM sensors**

| Part | Principle / interface | Range & accuracy | Supply / current | Size (mm) | Lifetime | Price & stock (JLC/LCSC, 2026-11-25) | ESPHome | Status |
|---|---|---|---|---|---|---|---|---|
| Sensirion SPS30 | Laser scattering, I2C + UART | 0–1000 µg/m³; ±10% precision (page); PM1/2.5/4/10 | 4.5–5.5 V; 55 mA avg, 80 mA max | 41×41×12 | >10 yr | $33.80 / $32.76; 240 in stock ([JLC C5900567](https://jlcpcb.com/partdetail/C5900567)) | Native `sps30` (I2C only; auto-clean interval) | Active; no NRND label; datasheet 07/2023; MCERTS certificate 10/2025 |
| Sensirion SEN55 | PM + RH/T + VOC + NOx, I2C | ±10% PM; ±0.45 °C; ±4.5 %RH | ~4.5–5.5 V (page shows "4.5 V"); 63 mA avg, 110 mA max | 52.8×43.6×22.3 | >10 yr | $25.68; 0 stock ([JLC C7000491](https://jlcpcb.com/partdetail/C7000491)) | Native `sen5x` (SEN50/54/55) | **NRND**, successor SEN65 |
| Sensirion SEN62 | PM + RH/T, I2C | 0–1000 µg/m³; ±0.45 °C; ±4.5 %RH | 3.15–3.6 V | 55.2×25.6×21.3 (family) | >10 yr | $16.94 / $16.42; 0 stock ([JLC C54308787](https://jlcpcb.com/partdetail/C54308787)) | Native `sen6x` | New 2026 |
| Sensirion SEN63C | PM + RH/T + CO2 (TC) | as above | 3.3 V; ~80 mA | same | >10 yr | $26.39; 51 in stock ([JLC C52088895](https://jlcpcb.com/partdetail/C52088895)) | Native `sen6x` | Active |
| Sensirion SEN66 | PM + RH/T + VOC + NOx + CO2 (PA) | as above | 3.3 V; 90 mA avg | same | >10 yr | Not on JLC. Distributor 1-pc ≈ $47–71 (DigiKey ~$61 1-pc / ~$51 @60; Mouser ~$71 1-pc; Arrow/Avnet ~$47), cached pages, lead time up to 17 wk ([DigiKey SEN66](https://www.digikey.com/en/products/detail/sensirion-ag/SEN66-SIN-T/25700945)) | Native `sen6x` | Active |
| Sensirion SEN69C | All of the above + HCHO, CO2 TC | as above | 3.3 V; 80 mA | same | >10 yr (HCHO shorter) | $62.55 / $60.65; 32 in stock ([JLC C55491212](https://jlcpcb.com/partdetail/C55491212)) | Native `sen6x` | Active |
| Plantower PMS5003 | Laser, UART | — | 5 V; UART 3.3 V logic | — | — | $16.25; 0 stock ([JLC C91431](https://jlcpcb.com/partdetail/C91431)) | Native `pmsx003` | — |
| Plantower PMSA003 / PMSA003I | Laser, UART / **I2C** (PMSA003I) | 0.3–10 µm count bins; standard + "environmental" units | 4.5–5.5 V (5 V typ) | — | — | PMSA003-C $20.87; 0 stock ([JLC C89095](https://jlcpcb.com/partdetail/C89095)) | Native `pmsx003`, `pmsa003i` | — |
| Honeywell HPMA115C0/S0 | Laser, UART | 0–1000 µg/m³; ±15% (Honeywell) or ±15 µg/m³ (Farnell listing) | 5 V ± 0.2 V | — | — | HPMA115S0-HLO $16.42; 0 stock ([JLC C2992355](https://jlcpcb.com/partdetail/C2992355)) | **No native component** | RS lists HPMA115C0-004 as "last RS stock" |
| Panasonic SN-GCJA5 | Laser, I2C + UART | ±10%; min particle 0.3 µm | 5 V ± 10%; <100 mA | 37×37×12 | 5-yr design target (laser + fan) | $12.79; 0 stock ([JLC C7083231](https://jlcpcb.com/partdetail/C7083231)) | Native `gcja5` (UART, 9600 even parity) | One element14 listing says "no longer manufactured" (unverified) |
| Cubic PM2012SE-B | Laser | — | — | — | — | not found on JLC | Not native (ESPHome supports Cubic PM2005/PM2105 via `pm2005`, I2C) | — |

Sources: [Sensirion SPS30](https://sensirion.com/products/catalog/SPS30); [Sensirion SEN55 (NRND → SEN65)](https://sensirion.com/products/catalog/SEN55); [ESPHome sps30](https://esphome.io/components/sensor/sps30/) (only I2C implemented; default auto-clean 168 h); [ESPHome sen5x](https://esphome.io/components/sensor/sen5x/); [ESPHome pmsx003](https://esphome.io/components/sensor/pmsx003/) ("All of these sensors are powered from 5V but use 3.3V UART logic levels"); [ESPHome pmsa003i](https://esphome.io/components/sensor/pmsa003i/); PMSA003I supply 4.5–5.5 V — [RAK12039 datasheet](https://docs.rakwireless.com/product-categories/wisblock/rak12039/datasheet/); PMSA003I count bins and dual units — [Adafruit PMSA003I](https://learn.adafruit.com/pmsa003i?view=all); Honeywell HPM — [Honeywell HPMA115C0-003](https://sensing.honeywell.com/HPMA115C0-003-particulate-matter-sensors), [RS HPMA115C0-004](https://za.rs-online.com/web/p/environmental-sensor-ics/2141433); SN-GCJA5 — [Panasonic datasheet copy](https://payda.krakow.pl/mpattachment/file/download/id/1150), [ESPHome gcja5](https://esphome.io/components/sensor/gcja5/) ("rated to last at least 5 years"); [ESPHome pm2005](https://esphome.io/components/sensor/pm2005/).

**SEN6x ESPHome component (native `sen6x`)**
- Supports SEN62, SEN63C, SEN65, SEN66, SEN68, SEN69C (SEN60 is not listed). Exposes PM mass and number concentration (0.5–10 µm), T/RH, VOC/NOx index, CO2 and HCHO. It offers CO2 ASC (default on), altitude/ambient-pressure compensation with an external pressure-sensor source, temperature offset/slope/time-constant compensation, and temperature acceleration parameters. Fan cleaning and the SHT heater are available only as manual actions. Diagnostics include fan error/speed, gas, CO2, HCHO and PM error flags. SEN63C/SEN69C must not be restarted within 24 s while the CO2 sensor is conditioning. The connector is a 6-pin JST GHR-06V-S (1.25 mm pitch). The old `voc`/`nox` keys are deprecated and will be removed in 2027.2.0 — [ESPHome sen6x](https://esphome.io/components/sensor/sen6x/)

**Independent accuracy (South Coast AQMD AQ-SPEC summary table, fetched 2026-11-25)**
- Sensirion SPS30 (est. $35): PM1.0 field R² 0.91 (MAE 1.3–1.4 µg/m³), lab R² 0.99; PM2.5 field R² 0.80–0.83 (MAE 2.0–5.1), lab R² 0.99 (MAE 5.4–6.5); PM10 field R² 0.07–0.20 (MAE 10.8–24.7) — [AQ-SPEC PM summary](https://www.aqmd.gov/aq-spec/evaluations/summary-pm)
- Sensirion SEN54 ($28): PM2.5 field R² 0.76–0.77 (MAE 3.5); PM10 field R² 0.18–0.19. SEN44 (discontinued): PM2.5 0.82 — [AQ-SPEC](https://www.aqmd.gov/aq-spec/evaluations/summary-pm)
- Cubic PM2012SE-B ($45): PM2.5 field R² 0.59–0.63 (MAE 4.9–5.0); PM10 0.10–0.14 — [AQ-SPEC](https://www.aqmd.gov/aq-spec/evaluations/summary-pm)
- Devices for context: AirGradient Open Air O-1PST PM2.5 field R² 0.97–0.98 (MAE 2.8–3.2); PurpleAir PA-II 0.93–0.97 (2026 re-evaluation 0.86–0.87); Tera NextPM 0.87–0.95; Qingping Air Monitor Lite 0.85–0.93; Airthings Space Pro 0.44–0.49 — [AQ-SPEC](https://www.aqmd.gov/aq-spec/evaluations/summary-pm)
- The visible AQ-SPEC summary has no SEN6x PM rows, and no rows for the bare Plantower, Honeywell or Panasonic components — [AQ-SPEC](https://www.aqmd.gov/aq-spec/evaluations/summary-pm)

### Inferences
- The SEN6x moves the PM sensor to the **3.3 V** rail (the SPS30/SEN5x need 5 V). This simplifies an ESP32 board but adds ~75–110 mA continuous load and 200–350 mA pulses on 3.3 V.
- The SEN62 ($17 at LCSC, 0 stock) is a cheaper and smaller (in footprint area) way to get Sensirion-grade PM than the SPS30 ($34). It also brings compensated T/RH. Being new, it has no independent validation yet.
- For PM2.5 indoors, the AQ-SPEC numbers put the SPS30 among the best small component sensors (field R² ~0.8). Plantower-based devices also score well, but they rely on device-level correction. No component sensor reports PM10 reliably; treat PM4/PM10 as estimates.
- Plantower, Honeywell and Panasonic modules have 0 stock at LCSC in this snapshot and are not SMT parts. Their cost advantage over a SEN62 is now small ($13–21 vs $17).
- For a refresh that values accuracy, the realistic PM choices are **SPS30** (proven, 5 V, active), **SEN62** (new, 3.3 V, PM + RH/T), or a **SEN66/SEN65** combo (Q5).

### Gaps
- No AQ-SPEC (or other independent) PM evaluation of SEN6x/SPS6x was found. The only SEN66 row in AQ-SPEC is a tVOC lab test (see Q3).
- SEN60's current lifecycle status (catalog page 404) and whether SEN62 replaces it were not confirmed.
- Datasheet specs for PMS5003/PMSA003/PMSA003I (consistency, current, MTTF, dimensions) were not retrieved (Mouser datasheet link blocked).
- HPMA115 and SN-GCJA5 lifecycle status is unconfirmed (only distributor hints of phase-out).
- The current (v0.92) SEN6x datasheet with SEN62/SEN69C specifics could not be downloaded. The figures above come from v0.5 plus product pages.
- Could not verify which PM component is inside the AirGradient O-1PST and PurpleAir PA-II (commonly reported as Plantower PMS5003-series).

---

## Q3. VOC/NOx: SGP40 vs SGP41 (and successors), Bosch BME680/688/690 (BSEC2, IAQ), ScioSense ENS160/161, Renesas ZMOD4410/4510; what the VOC/NOx Index means

### Takeaway
The **SGP41** (VOC + NOx Index) is still Sensirion's current discrete MOX gas sensor. No SGP4x successor was found; the SGP41 catalog page lists only the SGP40/SGP41. It is the natural upgrade from the user's SGP40 (same 2.44 mm DFN, same ESPHome `sgp4x` component). The **Renesas ZMOD4410/4450/4510 went EOL**: last-time-buy 30 Sep 2025, last shipment 31 Dec 2025. Avoid them. The **BME690** (2025/26) is the current Bosch part; it is BME688-derived with better condensation robustness. ESPHome's native BSEC2 component officially covers only BME680/BME688, and BME690/BSEC3 support in ESPHome is unconfirmed. All of these output *relative* indices (VOC Index, IAQ, AQI-S) or estimated "equivalents" (eCO2, bVOC), not true ppb.

### Cited Findings

| Part | Outputs | Key specs | Supply / current | Package | Price & stock (JLC, 2026-11-25) | ESPHome | Status |
|---|---|---|---|---|---|---|---|
| Sensirion SGP40 | VOC Index (1–500) via host Gas Index Algorithm | MOX; on-chip RH compensation | — | DFN-6 2.44×2.44 | $6.91 / $4.96; 1,705 in stock ([JLC C2874215](https://jlcpcb.com/partdetail/C2874215)) | Native `sgp4x` (auto-detect) | Active |
| Sensirion SGP41 | VOC Index + NOx Index (1–500 each) | VOC: 0–1000 ppm range, LoD <0.05 ppm ethanol-eq., τ63 <10 s, switch-on 1 h; device-to-device 15% m.v. | 1.7–3.6 V; 3.0 mA avg, 3.4 mA max | DFN 2.44×2.44×0.85 | $9.03 / $6.55; 2,154 in stock ([JLC C3659325](https://jlcpcb.com/partdetail/C3659325)) | Native `sgp4x` (driven at 1 Hz internally) | Active (datasheet 12/2021; RoHS declaration 04/2026) |
| Bosch BME680 | T/RH/P + gas → IAQ via BSEC | — | — | LGA-8 3×3 | $10.88 / $7.71; 1,370 in stock ([JLC C125972](https://jlcpcb.com/partdetail/C125972)) | Native `bme680_bsec` (BSEC1) and `bme68x_bsec2` | Listed under "Other gas sensors" (no lifecycle label) |
| Bosch BME688 | as BME680 + gas scanner/AI | — | — | LGA-8 3×3 | $11.51 / $8.09; 3,934 in stock ([JLC C3664478](https://jlcpcb.com/partdetail/C3664478)) | Native `bme68x_bsec2` | — |
| Bosch BME690 | IAQ 0–500, bVOC- and CO2-equivalents (BSEC) | IAQ sensor-to-sensor ±15% ±15 IAQ; LP 3 s / ULP 300 s modes; RH ±3 %RH; T ±0.5 °C (0–65 °C); P ±0.5 hPa abs, ±0.05 hPa rel, TCO ±1.3 Pa/K | VDD 1.71–3.6 V; 4.2 µA (1 Hz THP), 50 µA ULP, 0.5 mA LP, 3.1 mA gas scan | LGA-8 3.0×3.0×0.93 | $9.93 / $7.04; 1,556 in stock ([JLC C42431867](https://jlcpcb.com/partdetail/C42431867)) | **Not listed** in `bme68x_bsec2` (BME680/688 only) | New; "increased robustness for ... high condensation" |
| ScioSense ENS160 | TVOC (0–65,000 ppb), eCO2, AQI-UBA (1–5) | 1 h initial start-up on first power-up; 3 min warm-up afterwards | — | LGA-9 3×3 | ENS160-BGLM $5.71; 0 stock ([JLC C3659288](https://jlcpcb.com/partdetail/C3659288)) | Native `ens160` (I2C or SPI) | Active |
| ScioSense ENS161 | adds AQI-S (0–500 relative index), improved TVOC/eCO2 algorithms | LP 700 µA / ULP 150 µA average | — | LGA-9 3×3 | 0 stock; JLC price fields look erroneous ($0.22–0.50) ([JLC C20416840](https://jlcpcb.com/partdetail/C20416840)) | Not named in `ens160` docs | Datasheet v1.0 "Preliminary" (Dec 2023 upload) |
| Renesas ZMOD4410 / 4450 / 4510 | TVOC/IAQ (4410), O3/NO2 (4510) | — | — | LGA-12 3×3 | ZMOD4410AI2R 5 in stock ([JLC C25739255](https://jlcpcb.com/partdetail/C25739255)) | None native | **EOL**: notice PLC250017, 5 Jun 2025; LTB 30 Sep 2025, LTS 31 Dec 2025; replacement "in evaluation with partner" |

Sources: [Sensirion SGP41](https://sensirion.com/products/catalog/SGP41); [ESPHome sgp4x](https://esphome.io/components/sensor/sgp4x/); [Bosch BME690](https://bosch-sensortec.com/products/environmental-sensors/gas-sensors/bme690) (all five listed distributors showed "Out of Stock" on Bosch's page, while JLC/LCSC had 1,556); [ESPHome bme68x_bsec2](https://esphome.io/components/sensor/bme68x_bsec2/) ("allows you to use your BME680 and BME688"); [ESPHome bme680_bsec](https://esphome.io/components/sensor/bme680_bsec/); [ESPHome ens160](https://esphome.io/components/sensor/ens160/); ENS160 TVOC range, ENS161 AQI-S and LP/ULP currents — [ENS161 datasheet](https://www.sciosense.com/wp-content/uploads/2023/12/ENS161-Datasheet.pdf), [Adafruit ENS161](https://learn.adafruit.com/adafruit-ens161-mox-gas-sensor?view=all), [Electronics-Lab ENS161](https://www.electronics-lab.com/news/ens161-air-quality-sensor/); ZMOD EOL — [Renesas PLC250017](https://www.renesas.com/en/document/eln/plc-250017-end-life-eol-process-select-part-numbers); Renesas also ended software support for ZMOD4410/4510 on its cloud kits (Oct 2025) — [Renesas tool news](https://www.renesas.com/en/document/tnn/notification-parts-notification-ck-ra6m5-ck-rx65n?r=1611751).

**BME690 + BSEC3 / ESPHome status**
- A Bosch community thread asks whether the BME690 works with ESPHome's `bme68x_bsec2_i2c` platform; no confirmed answer was found — [Bosch community](https://community.bosch-sensortec.com/mems-sensors-forum-jrmujtaw/post/bme690-compatibility-with-esphome-bme68x-bsec2-i2c-sensor-platform-3dDH026sdoCL6F6)
- An unofficial "BSEC3 Arduino library" wrapper for the BME690 exists. It is not affiliated with or supported by Bosch — [arduinolibraries.info](https://www.arduinolibraries.info/libraries/bsec3-arduino-library-unofficial)
- Espressif publishes a raw BME690 driver component based on Bosch SensorAPI. It has no BSEC — [Espressif component registry](https://components.espressif.com/components/espressif/bme690)
- ESPHome's BSEC components require accepting Bosch's BSEC license. BSEC also derives "CO2" and "bVOC" from a VOC–CO2 correlation in human breath, so these are not CO2 measurements — [ESPHome bme68x_bsec2](https://esphome.io/components/sensor/bme68x_bsec2/)

**What the VOC Index / NOx Index are (Sensirion)**
- The VOC Index "describes the current VOC status in a room relative to the sensor's recent history." It uses a moving average over the past 24 h (the "learning time") as an offset, mapped to **100**. Values above 100 mean more VOCs than the recent average; values below 100 mean fewer (e.g., fresh air). The gain adapts to the past 24 h of events so that different environments map onto the same 1–500 scale. It "is also sensitive to odorless VOCs, but it cannot discriminate between them" — [Sensirion Info Note: VOC Index](https://sensirion.com/media/documents/02232963/6294E043/Info_Note_VOC_Index.pdf)
- The NOx Index baseline is mapped to **1**; the scale is 1–500 and uses a 24 h learning-time moving average per Sensirion's NOx info note. ESPHome's default NOx gain learning time is 12 h ("Past events will be forgotten after about twice the learning time") — [Sensirion Info Note: NOx Index (mirror)](https://www.sudo.is/docs/esphome/components/sgp4x/Info_Note_NOx_Index.pdf); [ESPHome sgp4x](https://esphome.io/components/sensor/sgp4x/)
- ESPHome renamed the `voc`/`nox` keys to `voc_index`/`nox_index` "since these sensors report Sensirion's unitless Gas Index rather than a concentration" — [ESPHome sgp4x](https://esphome.io/components/sensor/sgp4x/)
- SEN6x VOC/NOx specs: VOC device-to-device variation <±15 index points (or 15% m.v.); NOx <±50 points (or 50%); repeatability <±5 VOC / <±10 NOx; specs met after <1 h (VOC) and <6 h (NOx) switch-on — [SEN6x DS v0.5](https://cdn.soselectronic.com/productdata/b9/20/bdca9efc/sen60-sin-t.pdf)

**Independent results (AQ-SPEC lab, tVOC)**
- Sensirion SGP40 ($7): lab R² 0.91 on the low-concentration ramp (MAE 30–340 ppb), but **R² 0.01 on the high ramp** (MAE 5,000 ppb) — [AQ-SPEC summary](https://www.aqmd.gov/aq-spec/evaluations/summary-pm)
- Sensirion SEN66 ($62): tVOC lab R² 0.99–1.00 on the low ramp (MAE 0.40) and 0.99 on the high ramp (MAE 6.03–6.04). MAE units for an index output are not stated in the summary row — [AQ-SPEC summary](https://www.aqmd.gov/aq-spec/evaluations/summary-pm)

### Inferences
- **Keep the Sensirion SGP41.** It is the only discrete VOC part here that is in stock at JLC, cheap (~$9), natively supported (`sgp4x`), and adds the NOx Index. It also aligns with the SEN65/66 algorithm, so readings are comparable if the user later moves to a SEN6x.
- **Bosch BME690**: attractive as a single 3×3 mm T/RH/P + gas part, but (a) IAQ depends on the closed-source, licensed BSEC; (b) the native ESPHome BSEC2 component officially supports only BME680/688; (c) its T/RH accuracy (±0.5 °C, ±3 %RH) is well below SHT45 level. Treat it as an add-on "second opinion" gas sensor, not the T/RH/P reference.
- **ENS160/161**: cheap, but 0 stock at JLC in this snapshot, and the ENS161 has no ESPHome mention. Its TVOC/eCO2 are algorithm estimates, and it needs a 1 h first start-up.
- Every MOX output here is relative or estimated. None can be used as an absolute ppb TVOC number. The SGP40's poor high-ramp AQ-SPEC result illustrates the saturation/adaptation issue. Formaldehyde and specific gases need dedicated sensors (covered by other researchers).

### Gaps
- No announced successor to the SGP4x line was found (searched Sensirion's catalog pages; none listed).
- No confirmed BSEC3 release notes, and no ESPHome BME690 support status from ESPHome's changelog.
- No independent accuracy data comparing the SGP41 NOx Index vs BME690 IAQ vs ENS161 AQI-S.
- No current ENS161 production status (datasheet seen is "Preliminary" v1.0).
- The identity of Renesas's ZMOD replacement ("in evaluation with partner") is unknown.

---

## Q4. Temperature / humidity / pressure: SHT40/41/45, SHT4xP, SHT3x; BMP390/BMP581/BMP585/BME280; TE MS5611. Best accuracy and easiest thermal isolation

### Takeaway
For T/RH, the **SHT45** (±1.0 %RH, ±0.1 °C typ) in a 1.5×1.5×0.5 mm DFN is the accuracy leader. It costs $5.72 at JLC (SHT45-AD1B-R2, 6,055 in stock; the R3 variant is out of stock). The SHT40 ($1.86) is the budget choice. Its tiny size and 0.4 µA average current make it easy to put on a thermally isolated PCB "peninsula". Note the **SHT4xP / "-AD1P" protective-cover (PTFE membrane) variants** (e.g., SHT40-AD1P-R2, $2.56) for dusty air or conformal-coat protection. For pressure, the **BMP585** ($3.59, 3,820 in stock) and **BMP581** ($2.17, 7,920 in stock) are the current, cheap, in-stock Bosch parts, both supported by ESPHome's `bmp581` component. The user's **BMP280** shows 0 JLC stock at $13. The BMP390 is also out of stock there. Pressure matters mainly for compensating the CO2 sensor, which ESPHome can feed automatically.

### Cited Findings

| Part | Spec (typ unless noted) | Supply / current | Package | Price & stock (JLC, 2026-11-25) | ESPHome | Notes |
|---|---|---|---|---|---|---|
| Sensirion SHT45 | RH ±1.0 %RH; T ±0.1 °C; τ63 RH 4 s / T 2 s; range −40–125 °C, 0–100 %RH | 1.08–3.6 V; 0.4 µA avg | DFN 1.5×1.5×0.5 | AD1B-R2: $5.72 / $4.08; 6,055 in stock ([JLC C5221601](https://jlcpcb.com/partdetail/C5221601)); AD1B-R3: $9.88; 0 stock ([JLC C6705435](https://jlcpcb.com/partdetail/C6705435)) | Native `sht4x` (precision setting; heater duty ≤5%) | SHT4x datasheet V7.3 (04/2025) |
| Sensirion SHT41 | RH ±1.8 %RH (25–75%); T ±0.2 °C (0–75 °C) | — | DFN 1.5×1.5 | $2.18; 0 stock ([JLC C3664396](https://jlcpcb.com/partdetail/C3664396)) | `sht4x` | Ships on the Adafruit STCC4 breakout |
| Sensirion SHT40 | (entry SHT4x) | — | DFN 1.5×1.5 | $1.86 / $1.22; 11,469 in stock ([JLC C2848306](https://jlcpcb.com/partdetail/C2848306)) | `sht4x` | — |
| SHT40-AD1P-R2 ("with protective cover", SHT4xP-type) | — | — | DFN 1.5×1.5 | $2.56 / $1.70; 1,143 in stock ([JLC C45924513](https://jlcpcb.com/partdetail/C45924513)) | `sht4x` | Membrane-covered variant |
| Sensirion SHT31-DIS-B | (older generation) | — | DFN-8 2.5×2.5 | $4.60 / $3.15; 12,664 in stock ([JLC C80862](https://jlcpcb.com/partdetail/C80862)) | Native `sht3xd` | Superseded by SHT4x in price and performance |
| Bosch BMP585 | Abs ±50 Pa max (300–1100 hPa, −5–65 °C); rel ±6 Pa; noise 0.08 Pa RMS; TCO ±0.5 Pa/K; long-term drift ±0.2 hPa/12 mo; solder drift ±0.6 hPa; range 300–1250 hPa | VDD 1.71–3.6 V; 1.3 µA @1 Hz | LGA 3.25×3.25×1.86 (metal lid) | $3.59 / $2.58; 3,820 in stock ([JLC C18184976](https://jlcpcb.com/partdetail/C18184976)) | Native `bmp581` (BMP581 + BMP585) | Bosch distributor widgets showed 0 stock |
| Bosch BMP581 | Abs ±30 Pa typ (300–1100 hPa); rel ±6 Pa; noise 0.08 Pa | Bosch: 85% less current than BMP390 | LGA-10 2×2 | $2.17 / $1.41; 7,920 in stock ([JLC C5362283](https://jlcpcb.com/partdetail/C5362283)) | Native `bmp581` | — |
| Bosch BMP390 | Rel ±0.03 hPa (700–1100 hPa, 25–40 °C); noise 0.02 Pa | — | LGA-10 2×2 | $5.39; 0 stock ([JLC C5124834](https://jlcpcb.com/partdetail/C5124834)) | Native `bmp3xx` | — |
| Bosch BME280 | — | — | LGA-8 2.5×2.5 | $9.08; 3 in stock ([JLC C92489](https://jlcpcb.com/partdetail/C92489)) | Native `bme280` | Poor availability |
| Bosch BMP280 (user's 2021 part) | — | — | LGA-8 2×2.5 | $13.07; **0 stock** ([JLC C83291](https://jlcpcb.com/partdetail/C83291)) | Native `bmp280` | Poor availability / high price |
| TE MS5611-01BA03 | (not retrieved) | — | QFN-8 3×5 | $6.55; 0 stock ([JLC C37148](https://jlcpcb.com/partdetail/C37148)) | Native `ms5611` | — |
| Bosch BME690 (pressure part) | P abs ±0.5 hPa, rel ±0.05 hPa; T ±0.5 °C; RH ±3 %RH | see Q3 | 3×3×0.93 | see Q3 | see Q3 | — |

Sources: [Sensirion SHT45](https://sensirion.com/products/catalog/SHT45) (also lists the SHT40/41 "-AD1P" protective-cover variants, the SHT41A, and address variants 0x45/0x46); [SHT4x datasheet V7.3](https://sensirion.com/media/documents/33FD6951/6A7C10A0/HT_DS_Datasheet_SHT4x_V7.3.pdf); SHT41 accuracy — [Adafruit STCC4/SHT41 guide](https://learn.adafruit.com/adafruit-stcc4-and-sht41-co2-temperature-humidity-sensor?view=all); [ESPHome sht4x](https://esphome.io/components/sensor/sht4x/); [Bosch BMP585](https://www.bosch-sensortec.com/products/environmental-sensors/pressure-sensors/bmp585/); BMP581 ±30 Pa abs and comparison to BMP390 — [Bosch BMP581 news](https://www.bosch-sensortec.com/en/news/bosch-barometic-sensor-bmp581.html); BMP390 relative accuracy and noise — [Bosch BMP390](https://bosch-sensortec.com/products/environmental-sensors/pressure-sensors/bmp390); [ESPHome bmp581](https://esphome.io/components/sensor/bmp581/) (explicitly "BMP581 ... and BMP585"); [ESPHome bmp3xx](https://esphome.io/components/sensor/bmp3xx/); [ESPHome ms5611](https://esphome.io/components/sensor/ms5611/); [Bosch BME690](https://bosch-sensortec.com/products/environmental-sensors/gas-sensors/bme690).

**Thermal isolation guidance**
- Sensirion's SHTxx/STSxx design guide recommends milled slits in the PCB around the sensor to cut heat conduction, removing unnecessary copper around it, and decoupling it from on-board heat sources. It warns that poor housing/PCB design "may cause significant temperature and humidity deviations as well as highly increased response times" — [Sensirion SHTxx/STSxx Design Guide](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/2599/HT_AN_SHTxx_STSxx_Design%20Guide_V1.1_D1.pdf)
- The SCD4x's own on-board SHT gives RH ±6 %RH (15–35 °C, 20–65 %RH) / ±9 %RH full range and T ±0.8 °C (15–35 °C) / ±1.5 °C full range. These figures assume the temperature offset is set correctly for self-heating, which shows why a separate, isolated SHT4x is preferable for T/RH reporting — [SCD4x DS v1.7](https://sensirion.com/media/documents/48C4B7FB/67FE0194/CD_DS_SCD4x_Datasheet_D1.pdf)
- The STCC4 needs an SHT4x on its dedicated controller port (SDA_C/SCL_C, internal 10 kΩ pull-ups, SHT at 0x44). Alternatively, the host can write T/RH via `set_rht_compensation` — [STCC4 DS](https://cdn.soselectronic.com/productdata/dd/9f/50d5ffc9/stcc4-d-r3.pdf). ESPHome's `stcc4` supports external `temperature_source`/`humidity_source` — [ESPHome stcc4](https://esphome.io/components/sensor/stcc4/)
- Pressure compensation inputs: SCD4x/SEN66 accept ambient pressure (700–1200 hPa in SEN6x). ESPHome `scd4x`, `stcc4` and `sen6x` can take an external pressure sensor ID — [ESPHome scd4x](https://esphome.io/components/sensor/scd4x/), [ESPHome sen6x](https://esphome.io/components/sensor/sen6x/)

### Inferences
- **Best T/RH:** SHT45-AD1B-R2 (in stock, $5.72). Place it on a slotted PCB tongue away from the ESP32, the LDO and the SCD4x/SEN6x. Its 1.5 mm package and µA current make it easy to isolate. Use an "-AD1P" (protective cover) SHT4x variant if dust or condensation is a concern; confirm whether an SHT45 cover variant exists, since only SHT40/41-AD1P were seen.
- **Best pressure:** BMP585 or BMP581. Both are in stock, cheap and supported by one ESPHome component. Absolute accuracy (±0.3–0.5 hPa) is more than enough for CO2 compensation. Pressure also has negligible self-heating sensitivity, so placement is less critical. The BMP390 has slightly better relative noise but is out of stock at JLC. Drop the BMP280 (0 stock, $13).
- Pressure sensing gives a measurable CO2 accuracy benefit only if fed to the CO2 sensor. In ESPHome this is a one-line `ambient_pressure_compensation_source`.

### Gaps
- Max (not typ) SHT45 tolerances and the SHT4x datasheet's section 5.5 thermal guidance were not extracted.
- MS5611 accuracy specs and lifecycle were not retrieved.
- BMP280/BME280 official lifecycle status (NRND?) was not confirmed. Only the JLC stock and price signal was observed.
- Whether the BMP585 is gel-filled or water-resistant (vs BMP581) was not confirmed from the Bosch page.

---

## Q5. Combo modules: is a single SEN66-class module + extras better than discrete sensors? (accuracy, airflow, enclosure, cost, ESPHome)

### Takeaway
A **SEN66** gives SCD41-equivalent CO2 accuracy, SGP41-equivalent VOC/NOx, SPS6x PM and self-heating-compensated T/RH (±0.45 °C / ±4.5 %RH) in one pre-calibrated, natively supported module (`sen6x`). It needs one JST cable on a 3.3 V rail. The costs: ~30 cm³ of volume with a fan, a defined inlet/outlet that the enclosure must respect, a large current (~90 mA average and ~300–350 mA pulses on 3.3 V), and T/RH and CO2 accuracy that are **not better** than the best discrete parts (SHT45; SCD43). Price is about the same as a discrete flagship set. Pragmatic recommendation: **SEN66 + discrete SHT45 + BMP585** (feed pressure to SEN66 CO2 via ESPHome). For the best CO2, use **discrete SCD43 + SGP41 + SHT45 + BMP585 + SPS30/SEN62**. Avoid SEN63C/SEN69C when CO2 accuracy matters: their CO2 is TC-class ±(100 ppm + 10%), and Sensirion labels it "not compliant".

### Cited Findings
- SEN66 measures PM1/2.5/4/10, RH, T, VOC Index, NOx Index and CO2. It is sold for RESET/WELL/Title 24 applications. Specs: 3.15–3.6 V, 90 mA average, I2C, 55.2×25.6×21.3 mm, >10-yr lifetime — [Sensirion SEN66](https://sensirion.com/products/catalog/SEN66)
- SEN66 CO2 accuracy equals the SCD41 v1.7 spec (±(50 ppm + 2.5%) @400–1000 ppm etc.). The SEN63C's CO2 is ±(100 ppm + 10%) — [SEN6x DS v0.5](https://cdn.soselectronic.com/productdata/b9/20/bdca9efc/sen60-sin-t.pdf). SEN63C and SEN69C pages say "CO2 not compliant, see SEN66 instead" — [SEN69C](https://sensirion.com/products/catalog/SEN69C), [SEN63C](https://sensirion.com/products/catalog/SEN63C)
- SEN6x enclosure rules (Sensirion Mechanical Design & Assembly Guidelines, per search summary): couple the inlets and outlet directly to ambient air; seal inlet from outlet to prevent parasitic recirculation; any airflow restriction proportionally reduces the PM count rate; isolate the module from strong device airflow; avoid orientations that let dust settle; keep self-heating over-temperature <5 K and keep the module far from heat sources; use foam decoupling against fan resonance — [SEN6x Mechanical Design Guidelines](https://sensirion.com/resource/application_note/SEN6x_mechanical_design_assembly_guidelines). A search summary of Sensirion SEN6x documents (exact source document not confirmed) gave the airflow-isolation threshold as >1 m/s — [Sensirion PS_AN_SEN6x Mechanical Design and Assembly Guidelines D1](https://sensirion.com/media/documents/EA641247/6977159F/PS_AN_SEN6x_Mechanical_Design_and_Assembly_Guidelines_D1.pdf) (this link returned 404 when fetched directly)
- ESPHome `sen6x` exposes temperature-compensation (offset, normalized slope, time constant) and temperature-acceleration parameters for in-enclosure tuning. It also supports CO2 ASC, altitude and pressure compensation from an external sensor, and manual fan cleaning and SHT heater actions. Its startup delay defaults to 60 s — [ESPHome sen6x](https://esphome.io/components/sensor/sen6x/)
- SEN6x average current is 75–90 mA in measurement mode, with 2 ms peaks up to ~350 mA (SEN66) at 3.3 V; supply window 3.15–3.45 V (DS v0.5) — [SEN6x DS](https://cdn.soselectronic.com/productdata/b9/20/bdca9efc/sen60-sin-t.pdf)
- Acoustic: <24 dB(A) at 0.2 m, drift +0.5 dB(A)/yr — [SEN6x DS](https://cdn.soselectronic.com/productdata/b9/20/bdca9efc/sen60-sin-t.pdf)
- AQ-SPEC lab tVOC test of the SEN66: R² 0.99–1.00 (low ramp), 0.99 (high ramp) — [AQ-SPEC](https://www.aqmd.gov/aq-spec/evaluations/summary-pm)
- The SEN66 isn't on JLC/LCSC. Distributors quoted ~$47–71 per unit with up to 17-week lead time (cached DigiKey/Mouser/Arrow/Avnet data) — [DigiKey SEN66](https://www.digikey.com/en/products/detail/sensirion-ag/SEN66-SIN-T/25700945); [findchips SEN65](https://www.findchips.com/search/sen65). SEN63C $26.39 and SEN69C $62.55 at LCSC — [JLC C52088895](https://jlcpcb.com/partdetail/C52088895), [JLC C55491212](https://jlcpcb.com/partdetail/C55491212)
- Bosch BME690, the other "combo" option, is a 3×3 mm T/RH/P + MOX gas part: T ±0.5 °C, RH ±3 %RH, P ±0.5 hPa abs. It needs Bosch BSEC for IAQ — [Bosch BME690](https://bosch-sensortec.com/products/environmental-sensors/gas-sensors/bme690)

### Inferences
- **Accuracy:** The SEN66's CO2 and VOC/NOx are the same silicon class as SCD41/SGP41, so accuracy is roughly equal to that discrete pair. The discrete route wins only by using an **SCD43** (±(30 + 3%) vs ±(50 + 2.5–5%)) and an **SHT45** (±0.1 °C/±1 %RH vs ±0.45 °C/±4.5 %RH compensated). Inside a fan-driven module, the T/RH reflect module self-heating corrected by an algorithm. A separate, isolated SHT45 will be more trustworthy for comfort reporting.
- **Enclosure/airflow:** A SEN66 forces the enclosure around its fan inlet/outlet. In return, it supplies forced, defined airflow over the gas and CO2 sensors, which a passive discrete layout doesn't get. Discrete parts need their own enclosure venting design, plus a separate PM module (SPS30/SEN62), which also has a fan and inlet/outlet. So "fan + defined airflow" is unavoidable if PM is included.
- **Power:** A SEN66 on the ESP32's 3.3 V rail needs a regulator with ≥500 mA headroom and bulk capacitance. Discrete SCD4x also has 205 mA peaks, and SPS30 needs 5 V at 80 mA max.
- **Assembly:** SEN6x and SPS30 are cable-connected modules, not SMT. The SMT board would carry only the JST GHR-06V-S header (for SEN6x) plus the discrete ICs (SCD4x LGA-20, SGP41 DFN, SHT45 DFN, BMP585 LGA). All are JLC "Extended" parts.
- **ESPHome:** Both routes are fully native (`sen6x` or `scd4x` + `sgp4x` + `sht4x` + `bmp581` + `sps30`/`sen6x`). The SEN66 path is simpler: one I2C device, with pressure compensation from the BMP585 via `ambient_pressure_compensation_source`.
- **Verdict for this user** (accuracy-first, more sensor types, cleaner PCB): a **SEN66 + SHT45 + BMP585** core is the cleanest high-accuracy design, and leaves the PCB free for "extended" sensors. Choose the **discrete SCD43 path** only if the extra ~15–25 ppm of CO2 accuracy matters, or if the SEN66 is unobtainable (17-week lead times seen).

### Gaps
- No independent PM or CO2 field validation of the SEN66 module was found. Only a tVOC lab result in AQ-SPEC.
- The full SEN6x mechanical guideline (exact opening areas, distances, flow limits) was not downloaded (PDF links returned 404). The numbers above come from search snippets.
- Real-world SEN66 RH/T accuracy inside a closed enclosure (after compensation) was not found.

---

## Q6. Cost summary: realistic BOM for a "flagship accuracy" set vs a "value" set (sensors only, JLC/LCSC 1-pc prices, 2026-11-25 unless noted)

### Takeaway
A flagship sensor set costs roughly **$55–80** either way. The SEN66 route is SEN66 (~$47–71) + SHT45 ($5.72) + BMP585 ($3.59). The discrete route is SCD43/SCD41 ($17.87/$19.46) + SGP41 ($9.03) + SHT45 ($5.72) + BMP585 ($3.59) + SPS30 ($33.80) ≈ $70–72, or ≈ $53 with a SEN62 instead of the SPS30. A value set is **~$35–40**: SEN63C ($26.39, PM + RH/T + TC-CO2) + SGP41 + BMP581, or STCC4 + SHT40 + SGP40/41 + BMP581 + a SEN62/Plantower PM module. Most of the cost is PM and CO2. VOC, T/RH and pressure together are ~$12–18.

### Cited Findings
- JLC/LCSC unit prices (qty 1 / qty 100) and stock on 2026-11-25:
  - SCD43-D-R2 $17.87 / $17.33, 0 stock ([C50182965](https://jlcpcb.com/partdetail/C50182965))
  - SCD41-D-R2 $19.46 / $15.61, 378 ([C3659294](https://jlcpcb.com/partdetail/C3659294))
  - SCD40-D-R2 $15.92 / $15.04, 2,358 ([C3659421](https://jlcpcb.com/partdetail/C3659421))
  - STCC4-D-R3 $11.33 / $8.20, 2,590 ([C49191471](https://jlcpcb.com/partdetail/C49191471))
  - PASCO2V15 $24.19 / $22.99, 5 ([C26655608](https://jlcpcb.com/partdetail/C26655608))
  - SCD30 $52.99, 183 ([C1519271](https://jlcpcb.com/partdetail/C1519271))
  - SGP41 $9.03 / $6.55, 2,154 ([C3659325](https://jlcpcb.com/partdetail/C3659325)); SGP40 $6.91 / $4.96, 1,705 ([C2874215](https://jlcpcb.com/partdetail/C2874215))
  - BME690 $9.93 / $7.04, 1,556 ([C42431867](https://jlcpcb.com/partdetail/C42431867)); BME688 $11.51, 3,934 ([C3664478](https://jlcpcb.com/partdetail/C3664478))
  - SHT45-AD1B-R2 $5.72 / $4.08, 6,055 ([C5221601](https://jlcpcb.com/partdetail/C5221601)); SHT40-AD1B-R3 $1.86 / $1.22, 11,469 ([C2848306](https://jlcpcb.com/partdetail/C2848306))
  - BMP585 $3.59 / $2.58, 3,820 ([C18184976](https://jlcpcb.com/partdetail/C18184976)); BMP581 $2.17 / $1.41, 7,920 ([C5362283](https://jlcpcb.com/partdetail/C5362283))
  - SPS30 $33.80 / $32.76, 240 ([C5900567](https://jlcpcb.com/partdetail/C5900567))
  - SEN62 $16.94, 0 stock ([C54308787](https://jlcpcb.com/partdetail/C54308787)); SEN63C $26.39, 51 ([C52088895](https://jlcpcb.com/partdetail/C52088895)); SEN69C $62.55, 32 ([C55491212](https://jlcpcb.com/partdetail/C55491212))
  - PMS5003 $16.25, 0 stock ([C91431](https://jlcpcb.com/partdetail/C91431)); PMSA003-C $20.87, 0 stock ([C89095](https://jlcpcb.com/partdetail/C89095))
- SEN66 distributor pricing ~$47–71 (1 pc), ~$50–60 at volume, lead time up to 17 weeks (cached) — [DigiKey SEN66](https://www.digikey.com/en/products/detail/sensirion-ag/SEN66-SIN-T/25700945)
- PASCO2V15 ~$25.95 on Infineon's store — [CNX Software](https://www.cnx-software.com/2024/10/04/infineon-pasco2v15-co2-sensor-achieves-%c2%b150-ppm-accuracy-with-built-in-microphone-and-ir-emitter/)

### Inferences
Example sensor-only BOMs (1-pc prices; excludes PCB, passives, cables, JLC extended-part fees):

| Build | Parts | Approx. sensor cost |
|---|---|---|
| Flagship A (module) | SEN66 + SHT45-AD1B-R2 + BMP585 | ~$56–80 |
| Flagship B (discrete, best CO2) | SCD43 (or SCD41) + SGP41 + SHT45 + BMP585 + SPS30 | ~$70–72 |
| Flagship B' (discrete, 3.3 V PM) | SCD43 + SGP41 + SHT45 + BMP585 + SEN62 | ~$53 (SEN62 0 stock at LCSC) |
| "Like-for-like 2021 refresh" | SCD41 + SGP41 + SHT45 + BMP581 + SPS30 | ~$70 |
| Value A | SEN63C + SGP41 + BMP581 | ~$38 (CO2 is TC-class ±(100 + 10%)) |
| Value B | STCC4 + SHT40 + SGP40 + BMP581 + PMS5003/SEN62 | ~$38–39 (PM modules 0 stock at LCSC) |

- The CO2 sensor and PM module make up ~75–85% of the sensor BOM. Saving money on VOC, T/RH or pressure parts makes little difference.
- Upgrading from the 2021 set (SCD40/41, SGP40, SPS30, BMP280) to SCD43, SGP41, SHT45 and BMP585 adds roughly $15. That buys tighter CO2 accuracy, the NOx Index, better T/RH, and an in-stock pressure sensor.

### Gaps
- JLCPCB extended-part setup fees and SMT assembly costs per unique part were not quantified here (see the assembly researcher's notes).
- Live distributor stock for SEN66 and SCD43 should be re-checked at order time. Both looked constrained (SCD43 0 at LCSC; SEN66 lead time up to 17 weeks).
- Senseair S8/S12 and Honeywell/Panasonic pricing at mainstream distributors was not gathered.
