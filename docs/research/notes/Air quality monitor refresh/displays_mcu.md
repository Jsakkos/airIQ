# Displays and MCU Platform for a Refreshed DIY Air Quality Monitor (as of late Nov 2026)

Scope: (a) which ESP32 MCU or module to put on a custom, factory-assembled PCB, and (b) which display technology and panel to use (e-ink vs LCD/RLCD vs OLED/AMOLED). The focus is ESPHome support, power and self-heating (temperature accuracy), size, cost and looks. Latest ESPHome at time of research: 2026.11.x (2026.11.1 blog post dated 18 Nov 2026) — [ESPHome changelog index](https://esphome.io/changelog/).

---

## Q1. MCU: ESP32-S3 vs C6 vs C3 vs C5 vs P4 (+C6) for this application; module vs chip; JLCPCB availability; ESPHome support

### Takeaway
**ESP32-S3 module with PSRAM (ESP32-S3-WROOM-1-N16R8 or an S3-MINI-1 variant) is the safest all-round choice.** It is the only modern variant that has Arduino and ESP-IDF support in ESPHome, octal PSRAM for LVGL/large e-paper buffers, the GPIO count needed for RGB-parallel panels, and is the MCU on almost every ESPHome-supported display board. **ESP32-C6 (C6-MINI-1) is the low-heat/low-cost choice** if the display is small, monochrome or e-ink. It also adds Thread and Zigbee radios, but it has no PSRAM and is ESP-IDF only. C5 (dual-band Wi-Fi 6, PSRAM-capable) is now supported but module supply looks patchy. P4 is overkill: no radio, and it needs a C6 co-processor.

### Cited Findings
**ESPHome variant support (esphome.io ESP32 platform page):**
- ESPHome lists the following ESP32 variants. ESP32 (LX6 dual 240 MHz), S2, S3 (LX7 dual 240 MHz, Wi-Fi + BLE 5.0), C2, C3 (RISC-V 160 MHz), C5 (RISC-V HP 240 MHz + LP core, Wi-Fi 6 on 2.4 *and* 5 GHz, BLE 5.0), C6 (RISC-V 160 MHz + LP core, Wi-Fi 6 2.4 GHz, BLE 5.0, 802.15.4), C61, H2 (no Wi-Fi), P4 (RISC-V dual 400 MHz, "None (needs ESP-Hosted co-processor)"), plus the newer S31/H4/H21 that need ESP-IDF 6.1+ — [ESPHome ESP32 platform](https://esphome.io/components/esp32/)
- The framework `type` "Defaults to `esp-idf` for all ESP32 variants." Arduino is only available for ESP32, C3, S2 and S3. C2, C5, C6, C61, H2 and P4 are ESP-IDF only — [ESPHome ESP32 platform](https://esphome.io/components/esp32/)
- The `platformio` toolchain is deprecated and "will be removed in 2027.2.0" (native toolchains became the default in 2026.7) — [ESPHome ESP32 platform](https://esphome.io/components/esp32/); [ESPHome releases blog](https://esphome.io/blog/tags/releases/)
- Selectable `cpu_frequency` values are 80/160/240 MHz on ESP32/S2/S3/C5, 80/160 on C3, 80/120/160 on C6/C61, and 40/360/400 on P4 (the P4 default is the maximum) — [ESPHome ESP32 platform](https://esphome.io/components/esp32/)
- ESPHome **2026.4.0 changed the default CPU frequency on ESP32, S2, S3 and C5 from 160 MHz to 240 MHz**. The release notes suggest setting 160 MHz on battery C5 devices to save power — [ESPHome 2026.4.0 changelog](https://esphome.io/changelog/2026.4.0/); [HA forum release post](https://community.home-assistant.io/t/esphome-2026-4-0-faster-esp32-defaults-and-signed-ota-esphome-smart-home-made-simple/1022101)
- `execute_from_psram` is available on S3, S31 and P4 (off by default). `nvs_cache_in_psram` frees about 10 KB of internal heap — [ESPHome ESP32 platform](https://esphome.io/components/esp32/)
- 2026.3.0 brought "expanded hardware support" for ESP32-P4 and ESP32-C5, plus a C5 `band_mode` option for dual-band Wi-Fi (AUTO/2.4GHZ/5GHZ). That release also added the **SEN6x** sensor component — [ESPHome 2026.3.0 changelog](https://esphome.io/changelog/2026.3.0/); [ESPHome Wi-Fi component](https://esphome.io/components/wifi/)
- 2025.6.0 added initial ESP32-P4 support and OpenThread — [ESPHome 2025.6.0 blog](https://esphome.io/blog/2025/06/18/esphome-2025-6/); [CNX Software](https://www.cnx-software.com/2025/06/24/esphome-2025-6-0-adds-esp32-p4-and-openthread-support/)
- The ESPHome docs describe the original ESP32 as having "the most mature and well-tested support". No other maturity grades are given — [ESPHome ESP32 platform](https://esphome.io/components/esp32/)
- The mipi_rgb (16-bit parallel RGB) display driver "requires an ESP32 (usually an ESP32-S3 because of the number of GPIO pins required)" and states "PSRAM is a requirement due to the size of the display buffer" — [ESPHome mipi_rgb](https://esphome.io/components/display/mipi_rgb/)
- LVGL in ESPHome: "PSRAM is not a strict requirement but it is generally recommended, especially for large color displays". `buffer_size` defaults to 100% with a runtime fallback to 12%. Without PSRAM the recommended value is 25%. Example memory: a 320x240 RGB565 frame is 153,600 B at 100% and 38,400 B at 25% — [ESPHome LVGL](https://esphome.io/components/lvgl/)

**Power figures (heat proxy):**
- ESP32-C6 datasheet (3.3 V, 25 °C). Wi-Fi RX is 78 mA (11b/g/n HT20) and 82 mA (HT40). Wi-Fi TX peaks are 354 mA (11b @21 dBm) and 280 mA (11n MCS7 @18.5 dBm). Modem-sleep at 160 MHz with the CPU running is 27 mA with all peripheral clocks off and 38 mA with them on. At 80 MHz running it is 19/30 mA, and at 80 MHz idle 14/25 mA. Light-sleep is 180 µA and deep-sleep 7 µA. 802.15.4 RX is 74 mA — [ESP32-C6 datasheet §5.6](https://documentation.espressif.com/esp32-c6_datasheet_en.html)
- Espressif Techpedia gives light-sleep base currents of C3 ≈130 µA, S3 ≈240 µA and C6 ≈35 µA (45 µA measured) — [Espressif ESP Low Power Parameter Configuration](https://docs.espressif.com/projects/esp-techpedia/en/latest/esp-friends/advanced-development/performance/lowpower/lowpower-demo.html)
- ESP32-S3 board-level modem-sleep at 240 MHz is about 32 mA with RTC peripherals on and about 20 mA with the CPU idle and RTC peripherals off. These are board measurements, not datasheet values — [Deneyap Kart v2 power page](https://docs.deneyapkart.org/en/Cards/Deneyap-Kart-v2/Power-Consumption-esp32-s3.md)
- Seeed XIAO board-level modem-sleep is quoted as 27 mA for the S3 and 30 mA for the C6, including on-board parts (via search summary of Qoitech/Seeed data; not independently verified) — [Qoitech](https://www.qoitech.com/?p=19961)
- An Espressif measurement example of an ESP32-S3-WROOM-1 running the deep_sleep example shows about 23.88 mA active and 8.14 µA in deep sleep — [ESP-IDF current consumption measurement of modules](https://docs.espressif.com/projects/esp-idf/en/v6.0/esp32c6/api-guides/current-consumption-measurement-modules.html)

**Module part numbers, JLCPCB/LCSC availability and price:**
- ESP32-S3-WROOM-1-N16R8 is JLCPCB/LCSC part **C2913202**, listed as an **Extended** part, package SMD 25.5x18 mm. LCSC price snapshots conflict: about $5.61 (1+), $4.94 (10+) and $4.41 (30+) in one, and $6.38/$5.89/$5.38 in another. Stock was roughly 4k–13k across snapshots — [JLCPCB C2913202](https://jlcpcb.com/partdetail/3198300-ESP32_S3_WROOM_1N16R8/C2913202); [LCSC C2913202](https://www.lcsc.com/product-detail/C2913202.html)
- The sibling ESP32-S3-WROOM-1-N16R2 is C2913205 (~$5.18 1+, $4.34 30+) — [JLCPCB C2913205](https://jlcpcb.com/partdetail/ESP32-S3-WROOM-1-N16R2/C2913205)
- ESP32-C6-MINI-1-N4 is LCSC **C5736265**. Snapshots range from a reference price of about $3.16 at volume to $4.87 (1+), and stock varied from 0 to about 3.5k between snapshots — [LCSC C5736265](https://www.lcsc.com/product-detail/C5736265.html)
- ESP32-C5: Espressif announced mass production on 30 Apr 2025, but the WROOM module was not in the initial rollout — [Espressif news](https://www.espressif.com/en/news/ESP32-C5_Mass_Production); [CNX Software](https://www.cnx-software.com/2025/04/30/esp32-c5-mass-production-esp32-c5-devkitc-1-board/)
- LCSC lists ESP32-C5-WROOM-1-N16R8 (C53054799) from about $4.26 with 302 in stock but **flagged "Discontinued"**. The C5-WROOM-1U-N8R8 (C51950748) is out of stock. DigiKey's C5-WROOM-1-N4 is $4.99 (1 unit) with a **20-week** standard lead time — [LCSC C53054799](https://www.lcsc.com/product-image/C53054799.html); [LCSC C51950748](https://www.lcsc.com/product-image/C51950748.html); [DigiKey](https://www.digikey.com/en/products/detail/espressif-systems/esp32-c5-wroom-1-n4/27566799)
- Apollo Automation's AIR-1 (a commercial ESPHome AQ monitor) uses an ESP32-C3 Mini module on a custom PCB to keep size down — [Apollo AIR-1 FAQ](https://wiki.apolloautomation.com/products/air1/faq/)

### Inferences
- **S3 vs C6 trade-off for this project:**
  - Choose S3 (WROOM-1-N16R8, or MINI-1-N4R2/N8R2 for a smaller footprint) if the display is a color TFT/AMOLED with LVGL, or a 7.5" e-paper whose buffer wants PSRAM.
  - Choose C6-MINI-1 if the display is ≤4.2" mono e-paper, an RLCD or a small OLED. The C6 has lower modem-sleep current at its 160 MHz maximum, an LP core and an 802.15.4 radio. It is also cheaper and has a smaller module footprint.
  - Prefer a module over a bare chip: it brings pre-certified RF (FCC/CE modular approval), an integrated antenna and crystal, and avoids RF layout risk on a hobby PCB. Bare-chip savings are only about $1–2 at hobby volumes. (Inference; certification benefit is standard industry practice, not sourced here.)
- No ESP32-C6 module variants with PSRAM appeared in any listing reviewed (C6-MINI-1-N4/H4, C6-WROOM-1-N4/N8 only), whereas C5 modules ship as N8R8/N16R8. This is consistent with the C6 having no external PSRAM support (inferred from part numbering; verify in datasheet).
- **ESP32-C3:** still workable and Arduino-capable in ESPHome, but it is a single-core 160 MHz part with ~400 KB SRAM, no PSRAM and no 802.15.4. In 2026 it offers little over the C6 at a similar price, except Arduino-library compatibility.
- **ESP32-C5:** attractive for 5 GHz Wi-Fi and PSRAM, but the LCSC "discontinued" flag on one SKU, the 20-week DigiKey lead time and its newer ESPHome support make it a risky choice for JLCPCB assembly today.
- **ESP32-P4 + C6:** only justified for a MIPI-DSI 5–10" touchscreen. The extra chip, power and heat make it the wrong choice for a temperature-sensitive AQ monitor.
- Because ESPHome now defaults ESP32/S3 to 240 MHz (2026.4), explicitly setting `cpu_frequency: 80MHz` or `160MHz` in YAML is a concrete heat-reduction step for an AQ monitor.

### Gaps
- I could not extract the exact ESP32-S3 datasheet current table (Wi-Fi RX/TX and modem-sleep at 240/160/80 MHz). The PDF/HTML did not parse, so S3 figures above are board-level approximations.
- No authoritative ESP32-C3 current figures were collected this session, beyond the light-sleep baseline.
- JLCPCB Basic/Extended status and current prices for ESP32-S3-MINI-1, ESP32-C6-MINI-1 and ESP32-C3-MINI-1 were not confirmed. All Espressif modules are typically Extended parts (a ~$3 setup fee per unique Extended part), but this was not verified for each.
- ESP32-C61 (Wi-Fi 6 with PSRAM) module availability and ESPHome maturity were not researched.

---

## Q2. Self-heating of MCU/display and how to reduce its impact on onboard T/RH

### Takeaway
MCU and radio heat measurably biases onboard temperature: commercial ESPHome devices need 2–6 °C offsets, and offsets are device-specific and non-linear. Mitigation has three parts. **Physical isolation comes first** (thermal slots, sensor on a separate board or arm, sensor upstream in the airflow, switching regulator rather than LDO). **Firmware power reduction comes second** (lower CPU frequency, Wi-Fi power save, dim or turn off the backlight). **Software compensation comes last** (SEN6x `temperature_compensation`, calibrated against a reference).

### Cited Findings
- ESPHome's SEN6x component has a `temperature_compensation` block (`offset`, `normalized_offset_slope`, …) that "corrects the reported ambient temperature for heat from the enclosure or nearby components" — [ESPHome SEN6x](https://esphome.io/components/sensor/sen6x/)
- Sensirion's SEN6x temperature-compensation app note says self-heating varies from unit to unit, so one fixed offset may not hold across devices ("The larger the self-heating, the larger the variance from device to device") — [Sensirion SEN6x Temperature Compensation & Acceleration AN](https://sensirion.com/media/documents/C964FCC8/69709EC3/PS_AN_SEN6x_Temperature_Compensation_and_Acceleration_Application_No.pdf)
- Apollo AIR-1 (ESP32-C3 + SEN55):
  - The offset needed is "between 2 and 6 °C" — [The Pi Hut AIR-1 listing](https://thepihut.com/products/air-1-air-quality-sensor-for-home-assistant)
  - The default SEN55 temperature offset in Apollo's sensor definitions is 6.0 °C — [Apollo sensor definitions](https://wiki.apolloautomation.com/products/air1/setup/sensor-definitions/)
  - Apollo recommends letting the device sleep between readings so the ESP doesn't heat the sensor, notes the offset "isn't always linear", offers a "predicted room temperature" model with a case-heat multiplier, and says an offset won't replace a standalone temperature sensor — [Apollo AIR-1 FAQ](https://wiki.apolloautomation.com/products/air1/faq/); [Apollo predicted room temp](https://wiki.apolloautomation.com/products/air1/additional-info/predicted-room-temp-humidity/)
- Home Assistant community reports (search summary; the specific thread for each quote was not verified):
  - One user found readings accurate until the sensor went into the enclosure, where "heat from the ESP32 is causing misreadings".
  - Another saw an ESP32-C6 read about +1 °C above the original ESP32 in the same setup.
  - Sources: [HA: High CO2 readings on SEN66](https://community.home-assistant.io/t/high-co2-readings-on-sen66-outside/1019147); [HA: ESP32 temperature reading errors](https://community.home-assistant.io/t/esp32-temperature-reading-errors/975098)
- An ESPHome/ESP32 guide says the Wi-Fi radio, regulator and USB interface "can easily warm the local PCB and enclosure", and that a physical layout fix is preferable to a permanent software offset — [esp32.co.uk AHT20 guide](https://esp32.co.uk/aht20-esp32-esphome-wiring-calibration-home-assistant/)
- ESPHome `wifi: power_save_mode` options are NONE/LIGHT/HIGH, and **LIGHT is the default on ESP32**. The docs warn that the modes "generally also decrease the reliability of the WiFi connection" and that HIGH can cause frequent disconnects. `output_power` ranges from 8.5 to 20.5 dB — [ESPHome Wi-Fi](https://esphome.io/components/wifi/)
- ESP-IDF: to keep Wi-Fi associated while sleeping, use Wi-Fi modem-sleep together with **automatic light-sleep** (power-management `light_sleep_enable`). Plain light or deep sleep drops the Wi-Fi connection — [ESP-IDF Sleep Modes](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/system/sleep_modes.html)
- ESP32-C6 modem-sleep current roughly halves from 38 mA (160 MHz, CPU running, peripherals on) to 19 mA (80 MHz, peripherals off) — [ESP32-C6 datasheet](https://documentation.espressif.com/esp32-c6_datasheet_en.html)

### Inferences
- Typical always-on Wi-Fi ESPHome node budget (inference from the datasheet numbers): about 25–80 mA at 3.3 V, i.e. ~0.1–0.25 W in the MCU.
  - With a 5 V→3.3 V linear LDO, add (5−3.3) V × I ≈ 0.05–0.15 W more in the regulator. A small buck converter (e.g., TPS62xxx class) removes most of that.
  - A backlit TFT adds its backlight power on top; I found no sourced mA figures for specific panels.
  - E-ink and RLCD add near-zero static power.
- **Display choice is a thermal decision.** E-ink and reflective LCD are "cold" displays. TFT/IPS backlights and AMOLED panels dissipate continuously, worst at high brightness on white backgrounds.
- **Recommended firmware settings for an AQ node (inference):**
  - `cpu_frequency: 80MHz` or `160MHz`.
  - Keep `power_save_mode: LIGHT` (default).
  - Reduce `output_power` if RSSI allows.
  - Avoid BLE proxy / bluetooth_proxy on this node, since it keeps the radio scanning.
  - Avoid LVGL animations, and dim or switch off the backlight via an ambient light sensor.
- **PCB layout (inference, consistent with sources):**
  - Put the SEN6x/SHT4x at the board edge or on a tab separated by milled slots, with the MCU module downstream of the airflow.
  - Keep the LDO/buck converter and the backlight LED driver away from the sensor.
  - Consider a separate SHT4x on a thin "finger" outside the main enclosure air volume as a reference for compensating the SEN6x.

### Gaps
- No quantitative °C-per-mW data was found for a specific enclosure; this needs empirical testing.
- I did not find documentation in the ESPHome docs this session for an ESPHome-level "auto light sleep while connected" option for ESP32 (the ESP32 page mentions a separate "ESP32 Power Management" page I did not read).

---

## Q3. Relevance of Thread / Matter / Zigbee (C6/H2/C5)

### Takeaway
Thread and Zigbee are now real options in ESPHome on C5/C6/H2, but for a mains-powered AQ monitor feeding Home Assistant, **Wi-Fi + native API remains the pragmatic default**. ESPHome still has **no Matter application layer**, so a C6 buys optionality but no Matter. An 802.15.4 radio is a reason to prefer the C6 only if the user wants a Thread-only network.

### Cited Findings
- ESPHome OpenThread runs on ESP32 chips with an 802.15.4 radio: C5, C6, H2, H4, H21 and S31 (ESP-IDF). It also runs on nRF52840 under Zephyr. It lets ESPHome nodes talk to HA over Thread — [ESPHome OpenThread](https://esphome.io/components/openthread/)
- OpenThread arrived in 2025.6.0. 2026.11.0 added ESP32 OpenThread Border Router support and Zigbee SED (sleepy end device) support — [ESPHome 2025.6.0 blog](https://esphome.io/blog/2025/06/18/esphome-2025-6/); [ESPHome changelog](https://esphome.io/changelog/)
- ESPHome Zigbee runs on nRF52 and on ESP32 with 802.15.4 (C5, C6, H2, plus future H4/H21).
  - The docs note H2 "seems to work more reliably than" C6.
  - Wi-Fi station + Zigbee **end device** "works fine". Wi-Fi + Zigbee **router** is unstable. Wi-Fi AP + Zigbee is unsupported.
  - Only basic properties are exposed to HA.
  - [ESPHome Zigbee](https://esphome.io/components/zigbee/)
- Matter: community sources note ESPHome uses Thread as a transport only and there is no full ESPHome Matter implementation. A Matter feature request remains open — [HA guide: own Thread devices with ESPHome](https://community.home-assistant.io/t/how-to-make-your-own-thread-devices-with-esphome/962783); [esphome/feature-requests #1397](https://github.com/esphome/feature-requests/issues/1397)
- Matter-over-Thread on the C6 is available outside ESPHome (Arduino-ESP32 / ESP-Matter, Amazon ACK SDK for Matter on C6) — [Espressif Arduino Matter over OpenThread example](https://components.espressif.com/components/espressif/arduino-esp32/versions/3.3.6-rc1/examples/Arduino_ESP_Matter_over_OpenThread); [Amazon developer blog (Mar 2026)](https://developer.amazon.com/en-US/blogs/alexa/device-makers/2026/03/enhanced-device-development-capabilities)

### Inferences
- With Thread, the 802.15.4 radio's RX current (~74 mA on the C6) is similar to Wi-Fi RX. Thread gives no heat advantage for an always-listening router-class mains device.
- If Matter ever becomes a requirement, the C6 (or C5) is the hedge. Otherwise the S3 vs C6 decision should be driven by the display and memory.

### Gaps
- The current status of ESPHome Matter feature request #1397 was not checked directly.

---

## Q4. E-ink: panels, colors, refresh, ESPHome support, refresh cadence, ghosting, front light

### Takeaway
ESPHome has a **new `epaper_spi` component**: non-blocking and queue-based, it replaces the older `waveshare_epaper` and supports partial refresh on several panels. The best fits for an AQ monitor are **B/W panels with partial refresh**:
- GoodDisplay **GDEY029T94** (2.9" 296x128, SSD1680): 3 s full / 0.3 s partial.
- **Waveshare 2.9" v2**.
- **GDEY0154D67** (1.54" 200x200).
- **UC8179 7.5" 800x480** (Waveshare 7.5 V2, reTerminal E1001): fast full + partial.

4.2" **GDEY042T81** (400x300, SSD1683, 0.3 s partial in vendor spec) is a good size, but ESPHome lists it **without** partial refresh. Color and Spectra 6 panels take 15–20 s per refresh with no partial update, so they suit a static dashboard, not a live AQ readout.

### Cited Findings
**ESPHome support:**
- `epaper_spi` is described as a newer architecture using a queue-based state machine that does not block on the BUSY pin. `update_interval` defaults to 60 s — [ESPHome epaper_spi](https://esphome.io/components/display/epaper_spi/)
- epaper_spi models:
  - **Controllers:** JD79660, Spectra-E6, SSD1677, SSD1681, SSD1683, T133A01, UC8151, UC8179, UC8279.
  - **GoodDisplay panels:** GDEY0154D67-1.54, GDEY0213F51-2.13, GDEY029T94-2.9, GDEY029Z95-2.9, GDEY042T81-4.2.
  - **Waveshare panels:** 1.54in-G, 1.54in-v2, 2.13in-bv3/bv4, 2.13in-G, 2.13in-v3, 2.66in-b, 2.9in-v2, 3.97in, 4.26in, 7.5in-bV2-BWR, 7.5in-H, 7.5in-V2.
  - **Other panels:** WeAct 2.13/2.9/4.2 3-color; XSRUPB-7.5in-bwr.
  - **Integrated boards:** Soldered inkplate2 and inkplate6color; Seeed ee04-mono-4.26, reTerminal-E1001/E1002/E1004, reTerminal-Sticky (+gray4); Xteink-X4Pro.
  - Source: [ESPHome epaper_spi](https://esphome.io/components/display/epaper_spi/)
- **Partial refresh** in epaper_spi (`full_update_every` > 1) is supported on these models. The page lists no partial support for other models, including GDEY029T94-2.9 and GDEY042T81-4.2.
  - SSD1681 / Waveshare-1.54in-v2 / GDEY0154D67 (needs `reset_pin`; generic SSD1681 may garble).
  - UC8279 / Xteink-X4Pro.
  - UC8179 / Waveshare-7.5in-V2 / Seeed-reTerminal-E1001 ("fast full and partial refresh").
  - SSD1677 / reTerminal-Sticky.
  - Waveshare-2.9in-v2.
  - reTerminal-Sticky-gray4 (with `monochrome_partial_updates: true`).
  - Source: [ESPHome epaper_spi](https://esphome.io/components/display/epaper_spi/)
- **Color modes** by model: B/W (and 4-gray on some); 3-color BWR (WeAct-3c, Waveshare 2.13 bv4, 2.66 b, 7.5 bV2-BWR); 4-color BWRY (JD79660, Waveshare-7.5in-H); 6-color Spectra 6 (reTerminal E1002/E1004); 7-color (inkplate6color) — [ESPHome epaper_spi](https://esphome.io/components/display/epaper_spi/)
- On B/W panels, LVGL content is converted pixel by pixel to black or white **without dithering** — [ESPHome epaper_spi](https://esphome.io/components/display/epaper_spi/)
- 2026.11.0 added more Waveshare modules, the JD79660, UC8279 and UC8151D controllers, and the Xteink X4 Pro to epaper_spi — [ESPHome changelog](https://esphome.io/changelog/)
- **Deprecation status of `waveshare_epaper`** (conflicting signals):
  - epaper_spi calls it "the deprecated waveshare_epaper component". Its `Waveshare-2.9in-v2` and `GooDisplay-GDEY029T94-2.9` models replace the old `2.90inv2` and `gdey029t94` models — [ESPHome epaper_spi](https://esphome.io/components/display/epaper_spi/)
  - Seeed's wiki also calls it deprecated — [Seeed reTerminal E ESPHome cookbook](https://wiki.seeedstudio.com/reterminal_e10xx_with_esphome/)
  - However, the `waveshare_epaper` page itself showed **no deprecation banner** when fetched. It still documents `full_update_every` (default 30) for 1.54in, 1.54inv2, 2.13in, 2.13inv2, 2.90in, 2.90inv2, 7.50inV2p and gdew029t5 — [ESPHome waveshare_epaper](https://esphome.io/components/display/waveshare_epaper/)
- The waveshare_epaper docs warn that the BUSY pin on gdew0154m09, 7.30in-f and 7.50inV2 "must be inverted to prevent permanent display damage" — [ESPHome waveshare_epaper](https://esphome.io/components/display/waveshare_epaper/)
- The Seeed reTerminal E1002 model needs ESPHome ≥ 2025.11.1 — [Seeed ESPHome cookbook](https://wiki.seeedstudio.com/reterminal_e10xx_with_esphome/)
- A community report has a 4.26" SSD1677 panel working via epaper_spi on a XIAO ESP32-S3 — [HA forum: 4.26" + XIAO ESP32-S3](https://community.home-assistant.io/t/epaper-driver-board-and-4-26-monochrome-display-and-xiao-esp32-s3/979099)

**Panel refresh specs:**
- GDEY029T94 (2.9"): full 3 s, fast 1.5 s, partial 0.3 s at 25 °C. The touch variant GDEY029T94-T01 is listed with a 2 s full update — [Good Display GDEY029T94](https://www.good-display.com/product/389.html); [BuyEPaper GDEY029T94](https://buyepaper.com/products/29-inch-e-paper-screen-296x128-raspberry-pi-spi-display-gdey029t94)
- GDEY042T81 (4.2" 400x300, SSD1683, 4-gray capable): fast 1.5 s, partial 0.3 s; full 2 s per reseller. The older GDEQ042T81 (EOL) was 3 s / 1.5 s / 0.26 s — [BuyEPaper GDEY042T81-T02](https://buyepaper.com/products/gdey042t81-t02); [Good Display product 443 (GDEQ042T81)](https://www.good-display.com/product/443.html)
- **Front-light options** exist: GoodDisplay sells GDEY042T81-FL02 (front light) and GDEY042T81-FT02 (touch + front light) variants — [BuyEPaper GDEY042T81-FL02](https://buyepaper.com/products/gdey042t81-fl02); [BuyEPaper GDEY042T81-FT02](https://buyepaper.com/products/42-inch-e-paper-display-fast-update-morochrome-spi-e-ink-with-touch-and-front-light-gdey042t81-ft02)
- reTerminal refresh times: E1001 (7.5" mono, 4-gray, partial) 2–5 s; **E1002 (7.3" Spectra 6) 15–20 s, no partial**; E1004 (13.3" Spectra 6) ~20 s, no partial — [Seeed reTerminal E overview](https://wiki.seeedstudio.com/reterminal_e10xx_main_page/)

**Refresh cadence and ghosting rules:**
- Good Display guidelines:
  - Allow "at least 180-second interval" after completing a set of display updates.
  - Run a full refresh after every 5 partial updates to prevent ghosting.
  - Fully refresh multi-color/full-color panels at least once every 24 h.
  - [Good Display news/guidelines](https://www.good-display.com/news/80.html); [BuyEPaper usage guidelines](https://buyepaper.com/pages/epaper-display-usage-guidelines-1)
- Waveshare: skipping full refreshes makes ghosting worse and "may even damage the screen". Partial-refresh panels cannot stay in partial mode indefinitely. Waveshare applies the 180 s interval to products without partial refresh — [Waveshare e-Paper FAQ](https://docs.waveshare.com/4.26inch_e-Paper_G/FAQ)

### Inferences
- **Practical AQ cadence on e-ink:**
  - Partial-refresh B/W panels: partial update every 60 s (or on significant change), with `full_update_every: 5–10`.
  - Full-refresh-only panels: update no faster than every ~3 min.
  - Spectra 6 / 3-color panels: one refresh every 5–15 min at most, and accept the 15–20 s flashing refresh.
- **Size and resolution:**
  - **2.9" (296x128):** clean Aranet4-style CO2-number display, but the low resolution limits multi-metric layouts.
  - **4.2" (400x300):** the sweet spot for showing CO2, PM2.5, VOC/NOx index, T/RH and a small trend sparkline.
  - **7.5":** a wall "dashboard" size.
- For partial refresh with ESPHome on a 4.2" panel today, consider Waveshare-4.26in (SSD1677 class, 800x480) or a UC8179 panel. Do not assume GDEY042T81 partial works in epaper_spi; it is listed without partial support (verify on the latest docs).
- E-ink's weaknesses for an AQ monitor: unreadable in the dark without a front light, no backlit "alert" color, and slow color refresh. Pairing e-ink with an RGB LED or LED bar for status (as on the user's 2021 NeoPixel design) covers night-time and at-a-glance alerts.
- There is no ESPHome evidence on driving e-paper front lights; it would be a simple PWM LED channel (`ledc` output + `light`).

### Gaps
- Current e-paper panel prices (GoodDisplay/Waveshare) were not collected.
- A GoodDisplay first-party full-refresh figure for GDEY042T81 was not found; 2 s comes from a reseller.
- No sourced data on how many refresh cycles typical panels are rated for.
- Partial-refresh support status for GDEY042T81 / GDEY029T94 in ESPHome is based only on the docs page; GitHub PRs were not checked.

---

## Q5. Integrated e-paper boards as "brain + display" (with a sensor daughterboard)

### Takeaway
**Seeed reTerminal E1001 ($69, ESP32-S3 + 8 MB PSRAM, 7.5" 800x480 mono with partial refresh, onboard SHT4x, I²C/UART header) is the most ESPHome-mature off-the-shelf e-paper "face"**, and it is a first-class `epaper_spi` model. Inkplate 2/6COLOR are also native. M5Stack PaperS3 and LilyGO T5 S3 Pro (4.7" ED047 parallel panels) are **community-only** in ESPHome. For a sleek custom product, these boards are better used as prototyping references than as the final enclosure.

### Cited Findings
- reTerminal E series (all ESP32-S3, 8 MB PSRAM, 32 MB flash, microSD, onboard temp/humidity, UART/I²C/GPIO expansion header). All four support HA via ESPHome — [Seeed reTerminal E overview](https://wiki.seeedstudio.com/reterminal_e10xx_main_page/)
  - **E1001:** 7.5" mono 4-gray, 800x480, partial refresh, 2–5 s, 2000 mAh, 176x120x53 mm with stand, **$69**.
  - **E1002:** 7.3" Spectra 6, 800x480, 15–20 s, **$99**.
  - **E1003:** 10.3" 16-gray, 1404x1872, touch, **$159.90**.
  - **E1004:** 13.3" Spectra 6, 1200x1600, **$279.90**.
- Japanese retailer price for the E1001 was ¥14,773 incl. tax (listing dated Nov 2025) — [Switch Science](https://www.switch-science.com/collections/%E4%B8%BB%E8%A6%81%E3%83%A1%E3%83%BC%E3%82%AB%E3%83%BC/products/10802)
- CNX Software reviewed the E1001/E1002 with ESPHome and Home Assistant (Dec 2025) — [CNX Software review](https://www.cnx-software.com/2025/12/15/reterminal-e1001-e1002-review-bw-and-color-epaper-displays-tested-with-sensecraft-hmi-and-home-assistant/)
- ESPHome epaper_spi has built-in models for Seeed-reTerminal-E1001/E1002/E1004, reTerminal-Sticky, Seeed-ee04-mono-4.26, inkplate2 and inkplate6color — [ESPHome epaper_spi](https://esphome.io/components/display/epaper_spi/)
- M5Stack PaperS3 has community ESPHome support only, via an epdiy fork on ESP-IDF 5.5.1, tested with ESPHome 2025.11.0 — [HA forum: PaperS3 + ESPHome](https://community.home-assistant.io/t/m5stack-papers3-esphome-working-with-esp-idf-5-5-1-epdiy-fork/956107)
- LilyGO T5 E-Paper S3 Pro (4.7" ED047): no merged ESPHome component found, only a developer's stated intent to port it. The board has V1/V2 revisions and a Lite variant — [HA forum: T5 E-Paper S3 Pro](https://community.home-assistant.io/t/t5-e-paper-s3-pro/834950); [LilyGO wiki](https://wiki.lilygo.cc/get_started/en/E-Paper/T5-E-Paper-S3-Pro/T5-E-Paper-S3-Pro.html)
- There is also an older community component for the LilyGO T5 4.7 — [nickolay/esphome-lilygo-t547plus](https://github.com/nickolay/esphome-lilygo-t547plus)

### Inferences
- The reTerminal E1001's onboard SHT4x sits inside a battery-powered, mostly-sleeping enclosure. Once mains-powered, always-on Wi-Fi with SEN6x sensors added, expect self-heating. An external sensor daughterboard on the I²C header, placed outside or below the case, is the better design.
- M5Stack CoreInk (1.54") was not found in the ESPHome epaper_spi list; treat it as unsupported or community-only.
- For a custom PCB, copying the reTerminal approach (S3 module + UC8179 7.5" or SSD1677 4.26" panel over SPI + FPC connector + booster circuit) gives native ESPHome support.

### Gaps
- No ESPHome status was found for Waveshare's ESP32-S3 e-paper dev boards (e.g., ESP32-S3-ePaper-1.54) or M5Stack CoreInk.
- No Inkplate pricing was collected.

---

## Q6. LCD / RLCD / OLED / AMOLED options and ESPHome drivers

### Takeaway
ESPHome's display stack consolidated in 2025–2026:
- **`mipi_spi`** covers SPI/QSPI/octal panels (ST7789V/P, ILI9341/42/88, GC9A01A, ST7796, CO5300 AMOLED, RM690B0, AXS15231, SPD2010) and makes `ili9xxx` "redundant". It has presets for dozens of boards.
- **`mipi_rgb`** covers 16-bit RGB panels (ST7701S/GC9503V 480x480); PSRAM is required, effectively S3-only.
- **`mipi_dsi`** covers P4 panels.
- **`st7305` (new in 2026.11)** drives **reflective mono LCDs** such as Waveshare's 4.2" 400x300 RLCD. This is a compelling e-ink alternative: no backlight, image retention, sub-second updates.
- Small OLEDs are covered by `ssd1306_i2c/spi`.

### Cited Findings
- `mipi_spi` supports SPI, Quad-SPI and octal (8-bit parallel).
  - **Models:** AXS15231 (320x240), GC9A01A (240x240), GC9D01N, GC9107, **CO5300 (466x466 AMOLED)**, ILI9341/9342/9481/9486/9488, **RM690B0**, SPD2010 (412x412), ST7796, ST7789P, ST7789V, ST7735, CUSTOM.
  - **Board presets include:** Guition JC3248W535, **JC3636W518** (round), JC4827W543; Sunton ESP32-2432S028 ("CYD") variants and ESP32-2424S012; LilyGO T-DISPLAY-S3, **T-DISPLAY-S3-AMOLED**, T-DISPLAY-S3-AMOLED-PLUS, T4-S3; M5CORE/M5CORE2/AtomS3; Waveshare ESP32-S3-TOUCH-AMOLED-1.64/1.75/2.16, TOUCH-LCD-1.46/3.49/3.5B, ESP32-C6-LCD-1.47; WT32-SC01-PLUS; ESP-VoCat; S3BOX.
  - **RM67162 is not listed by chip name**, though the T-DISPLAY-S3-AMOLED preset exists.
  - With LVGL the driver needs no buffer. Without LVGL, the default buffer is 100% with PSRAM, otherwise ≈20 KB.
  - Source: [ESPHome mipi_spi](https://esphome.io/components/display/mipi_spi/)
- The `ili9xxx` page says: "This component has been made redundant since this class of displays is now supported by the MIPI SPI Display Driver" and "may be removed in a future release" — [ESPHome ili9xxx](https://esphome.io/components/display/ili9xxx/)
- `mipi_rgb` covers ST7701S and GC9503V (typical 480x480) plus RPI (no-init) panels.
  - **Presets:** GUITION-4848S040, SEEED-INDICATOR-D1, T-RGB-2.1/2.8 (round), T-PANEL-S3, WAVESHARE-4-480X480, ESP32-S3-TOUCH-LCD-4.3/7, Sunton 8048S050/070, CROWPANEL-ADVANCE-7, Panlee ZX3D95CE01S-TR-4848.
  - "PSRAM is a requirement"; it requires ESP-IDF.
  - Source: [ESPHome mipi_rgb](https://esphome.io/components/display/mipi_rgb/)
- 2026.11.0 added `mipi_dsi` model JC1060P470-V2 (P4), new `mipi_spi` models and the **`st7305` reflective LCD driver**, and **migrated LVGL to 9.6.0** — [ESPHome changelog](https://esphome.io/changelog/)
- 2026.2.0 added ESP32-P4 Waveshare display panels — [ESPHome 2026.2.0 changelog](https://esphome.io/changelog/2026.2.0/)
- `st7305`: Sitronix ST7305/ST7306 reflective mono panels, "1 bit per pixel, have no backlight and retain their image".
  - Built-in model `WAVESHARE-400X300` (4.2", on the ESP32-S3-RLCD-4.2).
  - 4-wire SPI at 10 MHz; default `update_interval` 1 s; writes only the changed window.
  - Source: [ESPHome st7305](https://esphome.io/components/display/st7305/)
- Waveshare ESP32-S3-RLCD-4.2:
  - 4.2" 400x300 B/W reflective LCD (ST7305, no backlight, sunlight-readable, low power).
  - **ESP32-S3-WROOM-1-N16R8**, ES8311 codec, dual mics, **SHTC3 T/RH**, PCF85063 RTC, TF slot, USB-C, optional 18650 holder.
  - 92.5 × 70.1 × 13.5 mm; **$24.99 (no battery) / $26.99 (with 18650)**.
  - Sources: [CNX Software](https://www.cnx-software.com/2026/01/06/esp32-s3-development-board-features-4-2-inch-reflective-lcd-rlcd-dual-microphone-array-onboard-speaker/); [Waveshare product](https://www.waveshare.com/esp32-s3-rlcd-4.2.htm?sku=33298); [Waveshare GitHub](https://github.com/waveshareteam/ESP32-S3-RLCD-4.2); [Hackster](https://www.hackster.io/news/waveshare-s-new-27-esp32-s3-board-features-a-unique-epaper-like-rlcd-a72fb1d3577f)
- Small OLED (`ssd1306_i2c` / `ssd1306_spi`):
  - **Models:** SSD1306 (128x32, 128x64, 96x16, 72x40, 64x48), SH1106 (128x32/64, 96x16, 64x48), SH1107 (128x64, 128x128), SSD1305 (128x32/64). **SSD1309 is not listed.**
  - `contrast` applies to all models; `brightness` works only on SSD1305.
  - Source: [ESPHome SSD1306](https://esphome.io/components/display/ssd1306/)
- LVGL in ESPHome is version 9 and `color_depth` supports only 16 (RGB565). For e-paper and OLED, use a suitable `update_interval`, `update_when_display_idle` or `on_draw_end`. A capacitive touchscreen is "highly preferred" — [ESPHome LVGL](https://esphome.io/components/lvgl/)
- AMOLED burn-in mitigations: pixel shifting, avoiding large static blocks, dark backgrounds with low brightness, and display-off timeouts. Image retention (temporary) differs from burn-in (permanent) — [Digit: OLED burn-in mitigation](https://www.digit.in/features/general/oled-burn-in-mitigation-the-hidden-technologies-protecting-your-display.html); [Garmin AMOLED manual](https://www8.garmin.com/manuals/webhelp/GUID-B613EA0B-EFB7-451C-BA10-DB9EE5A990BF/EN-US/GUID-8ECEF6B4-5257-44E9-BB09-778836BBF700.html)

### Inferences
- **RLCD (ST7305) is the most interesting 2026 development for this use case.** It has e-ink-like looks and zero backlight heat, but updates in about a second with no flashing and no ghosting cycle rules. ESPHome support is native but brand new (2026.11), and it is mono-only and dark in a dark room (no front light). A 4.2" 400x300 RLCD bare panel on a custom S3/C6 PCB, or the $25 Waveshare board as the "face", are both viable.
- **IPS TFT (ST7789 240x320 2.0–2.8", ST7796 3.5"):** cheapest color option, mature via mipi_spi, but it needs a backlight. PWM-dim it via `ledc` output + `light`, auto-dim from a light sensor (e.g., BH1750/VEML7700/LTR-390 in ESPHome), and turn it off at night. The backlight is the main heat source; keep it well away from the T/RH sensor.
- **AMOLED (CO5300 466x466 round, RM690B0, T-Display-S3-AMOLED):** best contrast and "premium phone" look, with no backlight heat on a dark UI. However, a 24/7 static AQ dashboard is a textbook burn-in case. Mitigate with a black background, a slow pixel shift of the layout, auto-off on no presence/at night, and low brightness. AMOLED is not recommended as the primary always-on display unless presence-gated.
- **Small OLED (SSD1306/SH1106 1.3"):** cheap but looks dated or "maker". It also burns in and is small. It is not "sleek modern" except as a tiny secondary status line.
- Round **GC9A01A 240x240 1.28"** is mature and cheap but low-res. The **GC9A01A/ST77916-class 360x360 (JC3636W518)** or **CO5300 466x466 AMOLED** are the round upgrades.

### Gaps
- No sourced per-panel backlight current (mA) figures for ST7789/ILI9341/ST7701S modules, nor ST7305 RLCD power figures.
- No front-light solution for RLCD found.
- Touch controllers (CST816S, FT6336, GT911, CST9217) were not researched in detail. The ESPHome device pages show GT911 on the 4848S040 and CST9217 (external component) on the Waveshare AMOLED 1.75.

---

## Q7. Integrated ESPHome-friendly display boards as an off-the-shelf "face"

### Takeaway
Off-the-shelf ESP32-S3 display boards are cheap ($20–$70) and well supported (many have one-line `model:` presets in mipi_spi/mipi_rgb/epaper_spi). They are viable as the "face" with a sensor daughterboard on I²C/UART. The trade-off is less control over thermal layout and enclosure aesthetics. Best candidates:
- **Seeed reTerminal E1001** (e-ink, $69).
- **Waveshare ESP32-S3-RLCD-4.2** (reflective, $25–27).
- **Guition ESP32-S3-4848S040** (4" 480x480 IPS touch, 86-box wall panel, ~$27).
- **Guition JC3636W518** (1.8" round 360x360, ~$20).
- **Waveshare ESP32-S3-Touch-AMOLED-1.75** (round 466x466 AMOLED, $30–40).

### Cited Findings
- Guition ESP32-S3-4848S040: 4" 480x480 ST7701S + GT911 touch, built-in DAC/speaker output. AliExpress price "around $27". ESPHome devices page rates it "Plug-n-flash (2/5)". There are many LVGL dashboards in a long-running HA thread. Reported issues include phantom touches on some units, washed-out colors and constrained resources — [ESPHome devices: Guition 4848S040](https://devices.esphome.io/devices/Guition-ESP32-S3-4848S040); [HA forum thread](https://community.home-assistant.io/t/guition-4-480x480-esp32-s3-4848s040-smart-display-with-lvgl); [atomic14 board page](https://www.atomic14.com/esp32/boards/guition-4848s040/)
- `GUITION-4848S040` is a built-in `mipi_rgb` preset — [ESPHome mipi_rgb](https://esphome.io/components/display/mipi_rgb/)
- Guition JC3636W518 (1.8" round 360x360, ESP32-S3) is about $20 per a forum user, with a community ESPHome config used on 2025.8.1. `JC3636W518` and `JC3636W518V2` are `mipi_spi` presets. Note the related JC3636K718C has a different pinout — [HA forum: JC3636W518](https://community.home-assistant.io/t/guition-1-8-360x360-esp32-s3-jc3636w518-smart-display/750515); [ESPHome mipi_spi](https://esphome.io/components/display/mipi_spi/); [JC3636K718C notes](https://raw.githubusercontent.com/MichalZaniewicz/esphome-guition-jc3636k718c-va/main/skill/guition-jc3636k718c/SKILL.md)
- Waveshare ESP32-S3-Touch-AMOLED-1.75: round 1.75" (45 mm) 466x466 AMOLED (CO5300) with CST9217 touch and dual mics. ~$30; Waveshare lists $29.99–39.99, and the aluminum-cased 1.75C is $39.99–41.99. It is a `mipi_spi` preset, and the ESPHome devices page has a sample config — [ESPHome devices: Waveshare AMOLED 1.75](https://devices.esphome.io/devices/waveshare-esp32-s3-touch-amoled-1.75); [Waveshare product](https://www.waveshare.com/esp32-s3-touch-amoled-1.75.htm?aff_id=184114); [Waveshare 1.75C](https://www.waveshare.com/esp32-s3-touch-amoled-1.75c.htm)
- The Sunton "Cheap Yellow Display" ESP32-2432S028 (ILI9341/ST7789 variants) is a `mipi_spi` preset. One HA user calls the CYD "the cheapest way in at around €15" — [ESPHome mipi_spi](https://esphome.io/components/display/mipi_spi/); [HA forum thread](https://community.home-assistant.io/t/guition-4-480x480-esp32-s3-4848s040-smart-display-with-lvgl)
- The Guition ESP32-P4 JC1060P470 (7" MIPI-DSI) has an ESPHome `mipi_dsi` preset (V2 added in 2026.11) — [ESPHome changelog](https://esphome.io/changelog/); [HA forum: JC1060P470](https://community.home-assistant.io/t/guition-esp32-p4-jc1060p470/959144)
- A new HA community project "ESP Screens" (2026) manages cheap ESP32 touch screens from HA — [HA forum: ESP Screens](https://community.home-assistant.io/t/introducing-esp-screens-beautiful-cheap-esp32-touch-screens-for-every-room-managed-from-home-assistant/1025191)

### Inferences
- **Off-the-shelf face + custom sensor board** is a legitimate architecture: the display board is the brain, and a small custom PCB carries SEN6x/SCD4x/SFA30 etc. on I²C (JST-SH/Qwiic) in a separately ventilated chamber. This cuts PCB complexity (no RF, no display FPC/booster circuits) and lets the sensor live away from the MCU heat. The downside is looks: these boards have fixed bezels and mounting that constrain a "sleek" enclosure.
- The CYD and generic 2.8" TFTs read as "maker" rather than "product". The 4" 86-box panel reads as a smart-home wall switch. The round AMOLED/LCD reads as "Nest-like premium".
- **For a fully custom PCB with factory SMT**, the cleanest path is S3 module + FPC connector for a bare panel (GDEY042T81 / Waveshare 4.26 e-paper, ST7305 RLCD, or ST7789/ST7796 IPS) with the display on the front of a stacked board. Every one of these has a native ESPHome driver.

### Gaps
- No verified current retail prices beyond forum estimates for Guition boards.
- M5Stack Dial / CoreS3 ESPHome status was not researched this session (M5CORE/M5CORE2 presets exist in mipi_spi).

---

## Q8. What reads as "sleek and modern" for a desk/wall AQ monitor; always-on readability

### Takeaway
Commercial references span three idioms:
1. **Aranet4: e-ink numeric**, minimal, battery-friendly, always readable in daylight.
2. **Awair Element: LED dot-matrix**, glanceable color score plus a number, readable in the dark.
3. **Qingping Air Monitor 2 / Gen 2: 4" 720x720 IPS touchscreen** with auto-brightness and color indicators, "Apple-like".

The modern look comes more from **large typography, few metrics per screen, color-coded status and a clean bezel-less front** than from the display technology itself.

### Cited Findings
- Aranet4 Home: e-ink display with a numeric CO2 ppm readout, 2xAA batteries, ~$189 — [FrontDeskReview Awair Element vs Aranet4](https://frontdeskreview.com/gear/air-quality-monitors/awair-element-vs-aranet4-home/)
- Awair Element: LED dot-matrix display with a 5-dot AQI score plus numeric readout, ~$299. Another source lists it as "Display: None (LED only)" — [FrontDeskReview](https://frontdeskreview.com/gear/air-quality-monitors/awair-element-vs-aranet4-home/); conflicting description at [smarthomecompared](https://smarthomecompared.com/air-quality-monitors/aranet-aranet4-home-vs-qingping-air-quality-monitor-gen-2)
- Qingping Air Monitor 2 / Air Quality Monitor Gen 2:
  - 4" IPS touchscreen, 720x720, 254 ppi.
  - "4-inch touchscreen display with auto brightness, large viewing angle and deep contrast".
  - Uses Sensirion sensors, with color indicators for easy interpretation.
  - Sources: [smarthomecompared Qingping Gen 2](https://smarthomecompared.com/air-quality-monitors/qingping-air-quality-monitor-gen-2); [Sensirion news: Sensirion inside Qingping Air Monitor 2](https://sensirion.com/company/news/press-releases-and-news/article/sensirion-inside-qingping-air-monitor-2); [BreatheSafeAir review](https://breathesafeair.com/qingping-air-quality-monitor-generation-2-review/)
- The Qingping Air Monitor Lite is smaller and cheaper (~$76) and shows one reading at a time — [smarthomecompared](https://smarthomecompared.com/air-quality-monitors/aranet-aranet4-home-vs-qingping-air-monitor-lite)
- The Qingping CO2 Monitor (SmartAir-branded) uses an e-ink display — [knowledgelib 2026 guide](https://knowledgelib.io/home/smart-home/smart-air-quality-monitors/2026)
- Apollo AIR-1 (ESPHome-native commercial AQ device) has no display, only an RGB LED — [Apollo AIR-1 product](https://apolloautomation.com/products/air-1)

### Inferences
- **Always-on readability matrix (inference):**

| Tech | Daylight | Dark room | Glance-from-across-room | Heat | Burn-in | "Premium" feel |
|---|---|---|---|---|---|---|
| E-ink B/W | Excellent | Unreadable (needs front light) | Good if large digits | None | None | High (Aranet4 look) |
| E-ink Spectra 6 | Good, muted colors | Unreadable | Fair | None | None (needs 24 h refresh) | High but slow (15–20 s flashy refresh) |
| RLCD ST7305 | Excellent | Unreadable | Good | None | None | Medium-high ("e-ink-like", faster) |
| IPS TFT + PWM backlight | Good | Excellent (dimmable) | Excellent (color) | Backlight heat | None | Medium-high if bezel-less/round |
| AMOLED | Good | Excellent | Excellent (true black) | Low on dark UI | **High risk** for a static dashboard | Highest |
| Small OLED | Fair | Good | Poor (tiny) | Low | High | Low ("maker") |
| LED matrix / RGB LED | Fair | Excellent | Excellent (color only) | Low | None | High if diffused (Awair look) |

- A hybrid works well: an **e-ink or RLCD for numbers plus a diffused RGB LED or light bar for status color**. This continues the user's 2021 NeoPixel idea and covers the dark-room weakness of reflective displays, with no backlight heat.
- An IPS round/square touch panel gives the "Qingping" look but needs auto-dim and night-off to avoid light pollution and heat.

### Gaps
- No sourced specs found for the AirGradient ONE display (believed to be a small OLED, but not confirmed this session).
- The Aranet4 display refresh interval was not confirmed.
- No user-study data on readability.

---

## Q9. Recommendation matrix (synthesis)

### Takeaway
- **Best e-ink:**
  - 4.2"-class B/W SPI panel on an ESP32-S3 (or C6) custom PCB, driven by `epaper_spi`. For guaranteed ESPHome partial refresh pick Waveshare-4.26in (SSD1677, 800x480) or a 7.5" UC8179; for 2.9" pick GDEY029T94 / Waveshare 2.9 v2.
  - Off-the-shelf: reTerminal E1001.
- **Best LCD:**
  - For an "e-ink look without e-ink pain", the 4.2" ST7305 RLCD (new native driver).
  - For color, a 2.0–3.5" ST7789/ST7796 IPS on mipi_spi with PWM backlight + ambient-light auto-dim, or the 4" 480x480 ST7701S (mipi_rgb, needs S3 + PSRAM).
- **Best round:**
  - GC9A01A 240x240 (cheap, mature); JC3636W518 360x360 round LCD board (~$20).
  - Waveshare 1.75" CO5300 AMOLED 466x466 (premium, but burn-in risk if always on).
- **MCU:** ESP32-S3-WROOM-1-N16R8 (or S3-MINI-1 with PSRAM) as the default; ESP32-C6-MINI-1 for mono e-ink/RLCD/OLED builds prioritizing low heat and cost.

### Cited Findings
- `epaper_spi` model list and partial-refresh support — [ESPHome epaper_spi](https://esphome.io/components/display/epaper_spi/)
- `st7305` reflective LCD driver with `WAVESHARE-400X300` model — [ESPHome st7305](https://esphome.io/components/display/st7305/)
- `mipi_spi` chip and board coverage; `ili9xxx` redundant — [ESPHome mipi_spi](https://esphome.io/components/display/mipi_spi/); [ESPHome ili9xxx](https://esphome.io/components/display/ili9xxx/)
- `mipi_rgb` requires PSRAM and effectively the S3 — [ESPHome mipi_rgb](https://esphome.io/components/display/mipi_rgb/)
- reTerminal E1001 specs/price — [Seeed reTerminal E overview](https://wiki.seeedstudio.com/reterminal_e10xx_main_page/)
- RLCD board specs/price — [CNX Software](https://www.cnx-software.com/2026/01/06/esp32-s3-development-board-features-4-2-inch-reflective-lcd-rlcd-dual-microphone-array-onboard-speaker/)

### Inferences
**Recommendation matrix with ESPHome maturity notes:**

| Option | Panel / driver | Res | ESPHome component (maturity) | MCU needed | Refresh / update | Heat | Approx cost | Look |
|---|---|---|---|---|---|---|---|---|
| **E-ink (best overall for accuracy)** | Waveshare 4.26" (SSD1677) or GDEY042T81 4.2" (SSD1683) | 800x480 / 400x300 | `epaper_spi` (new, actively extended; partial on SSD1677-class/UC8179/2.9v2/1.54v2) | C6 OK (mono), S3 for 7.5" or LVGL | Partial ~0.3 s; full 2–3 s; full every ~5 partials | ~0 | Panel price not collected | Aranet-like, calm |
| E-ink small | GDEY029T94 / Waveshare 2.9 v2 | 296x128 | `epaper_spi` (partial on 2.9in-v2) | C3/C6 | 0.3 s partial / 3 s full | ~0 | not collected | Minimal CO2-first |
| E-ink color | Spectra 6 7.3" (reTerminal E1002) | 800x480 | `epaper_spi` preset (needs ≥2025.11.1) | S3 + PSRAM | 15–20 s, no partial | ~0 | $99 board | Colorful but slow |
| **RLCD (best "LCD")** | ST7305 4.2" (Waveshare RLCD) | 400x300 mono | `st7305` (**new in 2026.11**, early) | S3 or C6 | ~1 s, partial-window writes | ~0 | $25–27 board | E-ink-like, crisp |
| IPS TFT color | ST7789V 2.0–2.8" / ST7796 3.5" | 240x320 / 320x480 | `mipi_spi` (mature; ili9xxx now redundant) | S3 recommended for LVGL; C6 workable with 25% buffer | Real-time | Backlight-dependent | Low | Qingping-like if styled |
| 4" square touch | ST7701S + GT911 (Guition 4848S040) | 480x480 | `mipi_rgb` preset (mature, popular) | **S3 + PSRAM required** | Real-time | Highest of LCDs | ~$27 board | Wall-panel "86-box" |
| **Round LCD** | GC9A01A 1.28" / JC3636W518 1.8" | 240x240 / 360x360 | `mipi_spi` (mature / preset) | S3 | Real-time | Backlight | ~$20 board | Nest-like |
| **Round AMOLED** | CO5300 1.75" (Waveshare) | 466x466 | `mipi_spi` preset; touch via external component | S3 + PSRAM | Real-time | Low on dark UI | $30–40 board | Most premium; burn-in risk |
| Small OLED | SSD1306/SH1106 0.96–1.3" | 128x64 | `ssd1306_i2c` (very mature) | Any (even ESP8266) | Real-time | Low | Very low | Dated |

- **MCU decision:**
  - Pick **S3 + PSRAM** if any color/LVGL/7.5" e-paper/round AMOLED path is plausible; it keeps every display option open, and with `cpu_frequency: 80–160MHz` its heat is manageable.
  - Pick **C6-MINI-1** only if the design is committed to mono e-ink/RLCD and wants minimum heat, cost and size plus Thread/Zigbee optionality.
  - Avoid C5 (supply) and P4 (overkill, no radio) for this build.
  - ESP8266 is not viable with LVGL ("ESP8266 is not supported because it does not have enough RAM") — [ESPHome LVGL](https://esphome.io/components/lvgl/).
- **Nextion replacement:** native ESPHome drivers plus LVGL now replace the user's 2021 Nextion UART HMI with no second MCU. This removes a separate display controller and its heat and simplifies firmware (single YAML).

### Gaps
- Bare-panel BOM costs (e-paper, RLCD, IPS, AMOLED) for a custom PCB were not collected.
- Long-term reliability of the new `st7305` and `epaper_spi` partial-refresh paths is unknown (both are recent).
- Whether the bare ST7305 4.2" RLCD panel is sold separately (outside the Waveshare board) was not confirmed.
