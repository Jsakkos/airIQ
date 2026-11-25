# Rebuild the 2021 monitor around a SEN66

Replace the four 2021 breakouts with **one Sensirion SEN66**: a single module measuring PM1–PM10, CO2 to the same spec as an SCD41, VOC and NOx indices, temperature and humidity, natively supported in ESPHome. It plugs by cable into a small KiCad board that JLCPCB assembles on its cheapest (Economic) tier. The board carries an **ESP32-C6 module, an isolated SHT45, a BMP585, a VEML7700 light sensor, the driver for a 2.9-inch black-and-white e-ink panel, and the light-bar LEDs**, so the builder never solders a surface-mount part. Estimated cost is **about $98 per unit for five and about $90 for ten**, before shipping. That meets the $100 ceiling but not "much less": the SEN66 is over half the bill, and the only cheaper CO2 sensors have specs two to three times looser. A discrete SCD41 + SGP41 + SEN62 build costs the same within a dollar, but it needs JLCPCB's dearer Standard tier and three sealed openings, so it stays as Plan B. The hard problem is now thermal rather than manufacturing: the desk wedge must keep sensors low at a front intake, the MCU and LEDs high by the exhaust, and self-heating under the 5 °C Sensirion recommends. Install **KiCad 10** for the PCB, since Autodesk ended Eagle access on 7 June 2026; SolidCraft and Bambu Studio already cover the enclosure.

## Strong 2025–2026 designs pair a module with a light bar and local ESPHome

The DIY field now has two camps. The accuracy-first camp is led by the **AirGradient ONE**. It pairs a SenseAir S8 NDIR, a Plantower PMS5003, an SGP41 and an SHT40 with an ESP32-C3, a 1.3" OLED and an **11-LED colour bar that shines through an ASA case** measuring 130×130×35 mm. It sells for $230 assembled or $138 as a kit, and every schematic and 3D file is CC-BY-SA 4.0 ([AirGradient](https://www.airgradient.com/indoor/)). It is OSHWA-certified ([OSHWA TH000013](https://certification.oshwa.org/th000013.html)). It was also the first air-quality monitor to earn Home Assistant's official compatibility certification, in September 2025 ([Notebookcheck](https://www.notebookcheck.net/Airgradient-First-air-quality-monitor-to-be-officially-compatible-with-Home-Assistant.1105567.0.html)). The second camp is a 2025–2026 wave of **SEN66 builds on ESP32-C3/C6/S3 boards**. The closest to this project is FeatureNAB's: a SEN66 and a XIAO ESP32-C6 drive a 2.13" e-ink panel through a custom KiCad board, which ships with Gerber, BOM and CPL files for JLCPCB assembly and an ESPHome config using WHO-2021 thresholds ([FeatureNAB](https://github.com/FeatureNAB/air-sensor)). Project Aura went the other way. It joins modules with cables and has no PCB at all, and the build stalled when the Adafruit SEN6x breakout went out of stock ([CNX Software](https://www.cnx-software.com/2026/02/16/project-aura-a-neat-easy-to-assemble-diy-air-quality-monitor-compatible-with-home-assistant/)).

| Device | Sensors | Display and status light | MCU | Size (mm) | Price | Lesson for this build |
|---|---|---|---|---|---|---|
| AirGradient ONE | S8 NDIR, PMS5003, SGP41, SHT40 | 1.3" OLED + 11-LED bar | ESP32-C3 | 130×130×35 | $230 / $138 kit | Light bar, anti-air-loop venting, open licence; reviewers find it large |
| Apollo AIR-1 | SEN55, optional SCD40, DPS368/310 | 3 RGB LEDs, no screen | ESP32-C3 | 61×61×30 | n/a | Compact cube needs 2–6 °C temperature offsets |
| M5Stack Air Quality v1.1 | SEN55 + SCD40 | 1.54" e-ink | ESP32-S3 | 72×56×26.5 | $89.90 | Official ESPHome package; e-ink ghosting |
| Networked Artifacts Air Lab | SCD41, SGP41, LPS22, no PM | 2.9" 296×128 e-ink + RGB LED | ESP32-S3 | 155×65×10 | $229–250 | Same panel class as this plan |
| Airthings View Plus | Radon, PM2.5, CO2, VOC, T/RH/P | 2.9" e-ink | n/a | n/a | n/a | Commercial template for a 2.9" e-ink AQ face |
| FeatureNAB air-sensor | SEN66 | 2.13" e-ink | XIAO ESP32-C6 | n/a | n/a | KiCad + JLC PCBA files to learn from |

Sources: [AirGradient](https://www.airgradient.com/indoor/), [Apollo GitHub](https://github.com/ApolloAutomation/AIR-1), [The Pi Hut](https://thepihut.com/products/air-1-air-quality-sensor-for-home-assistant), [CNX on M5Stack](https://www.cnx-software.com/2025/09/14/m5stack-air-quality-kit-v1-1-features-sensirion-sen55-environmental-sensor-and-scd40-co2-sensor/), [CNX on Air Lab](https://www.cnx-software.com/2025/04/26/air-lab-portable-wi-fi-bluetooth-le-air-quality-monitor-e-paper-touchscreen-display/), [Jeff Geerling](https://www.jeffgeerling.com/blog/2025/air-lab-flipper-zero-air-quality-monitors/), [Airthings](https://www.airthings.com/view-plus).

The chosen direction, a 2.9" e-ink face plus a colour light bar, combines the Air Lab and View Plus panel size with AirGradient's light bar. That pairing covers e-ink's one real weakness: it cannot be read in a dark room. The best-reviewed commercial devices share the same design language. They show one dominant readout, use an ambient colour cue and hide their vents. Aranet4 shows a single CO2 number on e-ink from a Senseair Sunrise NDIR ([Senseair](https://senseair.com/aranet4-senseair-sunrise-inside/)). PurpleAir uses an LED ring ([PurpleAir](https://www2.purpleair.com/products/purpleair-touch)), and Qingping uses Sensirion's SCD40, SGP40 and SHT4x behind a touchscreen ([Sensirion](https://sensirion.com/company/news/press-releases-and-news/article/sensirion-inside-qingping-air-monitor-2)).

The failures are just as consistent, and each one maps to a design rule.

**Self-heating is the top complaint.** Apollo's ESP32-C3 inside a 61 mm cube forces **2–6 °C temperature offsets**. Apollo ships a predicted-room-temperature model to compensate and admits the offset is not always linear ([Apollo FAQ](https://wiki.apolloautomation.com/products/air1/faq/)).

**Parts disappear mid-production.** Apollo shipped some AIR-1 units without a pressure sensor after the DPS310 was discontinued ([Apollo FAQ](https://wiki.apolloautomation.com/products/air1/faq/)).

**Lights that can't be dimmed annoy users.** One Home Assistant user's main complaint about the $49.90 Sonoff AirGuard is that its indicator can't be dimmed ([HA forum](https://community.home-assistant.io/t/new-sonoff-airguard-device-compatibility-sawf-08p-co2-sawf-07p-pm2-5-pm10/962128)).

**Cloud dependence is fragile.** Awair Elements on one partner platform went offline when Awair revoked certificates in 2022 ([AS Home](https://support.asairhome.com/hc/en-us/articles/10053519130509-How-To-Fix-AWAIR-Element-Offline-Status)). Qingping's local MQTT still needs a cloud account or a hack ([Hackaday](https://hackaday.com/2026/01/04/modifying-a-qingping-air-quality-monitor-for-local-mqtt-access)).

**PM accuracy varies widely.** In South Coast AQMD's AQ-SPEC field tests, PM2.5 R² ranges from 0.97–0.98 for the AirGradient Open Air down to 0.44–0.49 for the Airthings Space Pro and 0 for uHoo ([AQ-SPEC](https://www.aqmd.gov/aq-spec/evaluations/summary-pm)).

One price anchor matters for honesty. M5Stack's $89.90 kit already pairs a SEN55 and SCD40 with e-ink and an official ESPHome package. Building only makes sense for what the kit lacks: a larger panel, an isolated T/RH reference, the NOx and formaldehyde options, a light bar, and an open design others can reproduce.

## Each 2021 sensor has a successor, and one module covers most of them

### What changed since 2021

Every 2021 part except the BMP280 is still current, but each has a better successor. The table uses JLCPCB/LCSC single-unit prices and stock as of 25 November 2026. Stock changes daily.

| Category | 2021 part and its status | Best 2026 choice | Headline accuracy | Price and stock | ESPHome |
|---|---|---|---|---|---|
| CO2 | SCD40/41, active; SCD41 spec tightened in datasheet v1.7 | SEN66's internal SCD41-class sensor; discrete SCD43 or SCD41 | SCD41 ±(50 ppm + 2.5%) at 400–1000 ppm (±75 ppm at 1000); SCD43 ±(30 ppm + 3%) (±60) | SCD41 $19.46, 378 in stock; SCD43 $17.87, **0 in stock** | `scd4x`, `sen6x` |
| PM | SPS30, active and still the best-validated small PM sensor | SEN66's SPS6x PM block; SPS30 as the validated alternative | SPS30 field PM2.5 R² 0.80–0.83; **no independent SEN6x PM data yet** | SPS30 $33.80, 240 in stock; SEN62 $16.94, 0 in stock | `sps30`, `sen6x` |
| VOC/NOx | SGP40 | SEN66's internal SGP41-class sensor; discrete SGP41 | Relative index 1–500 (VOC baseline 100, NOx baseline 1) | SGP41 $9.03, 2,154 in stock | `sgp4x`, `sen6x` |
| Temperature/RH | SCD4x internal (±0.8 °C, ±6 %RH) | **SHT45** on a slotted PCB tongue | ±0.1 °C, ±1.0 %RH typical | $5.72, 6,055 in stock; SHT40 $1.86 | `sht4x` |
| Pressure | BMP280, **0 in stock, $13.07** | **BMP585** | ±50 Pa absolute max | $3.59, 3,820 in stock | `bmp581` |
| All-in-one | none | **SEN66** | CO2 = SCD41 spec; T ±0.45 °C, RH ±4.5 %RH | $47–61 at distributors, not at JLC, lead times up to 17 weeks | `sen6x` |

Sources: [SCD4x datasheet v1.7](https://sensirion.com/media/documents/48C4B7FB/67FE0194/CD_DS_SCD4x_Datasheet_D1.pdf), [SCD43](https://sensirion.com/products/catalog/SCD43), [JLC SCD41](https://jlcpcb.com/partdetail/C3659294), [JLC SCD43](https://jlcpcb.com/partdetail/C50182965), [AQ-SPEC](https://www.aqmd.gov/aq-spec/evaluations/summary-pm), [JLC SPS30](https://jlcpcb.com/partdetail/C5900567), [JLC SEN62](https://jlcpcb.com/partdetail/C54308787), [JLC SGP41](https://jlcpcb.com/partdetail/C3659325), [VOC Index note](https://sensirion.com/media/documents/02232963/6294E043/Info_Note_VOC_Index.pdf), [JLC SHT45](https://jlcpcb.com/partdetail/C5221601), [JLC SHT40](https://jlcpcb.com/partdetail/C2848306), [JLC BMP585](https://jlcpcb.com/partdetail/C18184976), [JLC BMP280](https://jlcpcb.com/partdetail/C83291), [SEN66](https://sensirion.com/products/catalog/SEN66), [DigiKey SEN66](https://www.digikey.com/en/products/detail/sensirion-ag/SEN66-SIN-T/25700945), [ESPHome sen6x](https://esphome.io/components/sensor/sen6x/).

**CO2.** The cheap newcomers are a trap for a monitor whose headline number is CO2. Sensirion's STCC4 is tiny and cheap at $11.33, but it measures thermal conductivity rather than absorbing infrared light. Its spec is **±(100 ppm + 10%)**, and its datasheet warns that any change in gas composition reads as a change in CO2 ([STCC4 datasheet](https://cdn.soselectronic.com/productdata/dd/9f/50d5ffc9/stcc4-d-r3.pdf)). In AirGradient's March 2026 three-way test, its peak-to-peak noise in steady outdoor air was **~136 ppm**, against ~26 ppm for an SCD4x and ~10 ppm for a Senseair S12. It also tracked temperature with a Pearson correlation of ~0.991 ([AirGradient](https://www.airgradient.com/blog/co2-sensor-technologies/)). The SEN63C and SEN69C variants carry the same thermal-conductivity CO2 class, and Sensirion labels them "CO2 not compliant, see SEN66" ([SEN69C](https://sensirion.com/products/catalog/SEN69C)). Two parts are worth re-checking next year. The Senseair S12 is a reflow-solderable true-NDIR part, still at prototype status ([Senseair](https://senseair.com/product/s12-co2/)). The Sensirion SCD53, listed as upcoming, promises stability that doesn't depend on fresh-air recalibration ([SCD53](https://sensirion.com/products/catalog/SCD53)). Neither has an ESPHome component.

**VOC, temperature and pressure.** The ZMOD4410/4510 family is out: Renesas set the last-time-buy for September 2025 ([Renesas](https://www.renesas.com/en/document/eln/plc-250017-end-life-eol-process-select-part-numbers)). Bosch's BME690 depends on the closed BSEC library, and ESPHome's BSEC2 component officially lists only the BME680/688 ([ESPHome](https://esphome.io/components/sensor/bme68x_bsec2/)). Those two facts leave Sensirion's gas-index sensors as the default. The BMP585 matters mainly because ESPHome can feed it straight into the CO2 sensor's pressure compensation.

### The SEN66 wins on integration, not on accuracy

Inside the SEN66 is SCD41-class CO2 and SGP41-class VOC/NOx silicon. So a SEN66 is **as accurate as the discrete pair, not more**, and its internal T/RH (±0.45 °C, ±4.5 %RH after self-heating compensation) is clearly worse than an SHT45 ([SEN6x datasheet](https://cdn.soselectronic.com/productdata/b9/20/bdca9efc/sen60-sin-t.pdf)). Its advantages are about integration, and each one matters to this builder.

It replaces three sensor openings with **one fan-driven airflow path**, so a single sealed intake and outlet feed every gas sensor.

It is a **cable-connected module** on a 1.25 mm JST GH connector, so the main board avoids the SCD41. JLCPCB lists the SCD41 as Standard-assembly-only with "High" assembly difficulty ([JLC](https://jlcpcb.com/partdetail/Sensirion-SCD41_DR2/C3659294)).

It runs on 3.3 V, removing the 5 V rail the SPS30 needed.

Every SEN6x variant ESPHome supports, **SEN62 through SEN69C, shares one 55.2×25.6×21.3 mm body, the same I²C address (0x6B) and the same component**, which arrived in ESPHome 2026.3.0 ([ESPHome sen6x](https://esphome.io/components/sensor/sen6x/), [ESPHome 2026.3.0](https://esphome.io/changelog/2026.3.0/)). One board and one enclosure can therefore take a SEN69C, which adds formaldehyde, or a SEN62 in a room where only PM matters.

The costs are real. The SEN66 draws **~90 mA continuously with 300–350 mA pulses**, inside a tight 3.15–3.45 V supply window. It has **no independent PM validation** yet. Distributors quote **$47–61** with lead times up to 17 weeks ([SEN6x datasheet](https://cdn.soselectronic.com/productdata/b9/20/bdca9efc/sen60-sin-t.pdf), [DigiKey](https://www.digikey.com/en/products/detail/sensirion-ag/SEN66-SIN-T/25700945)). The SPS30 in the 2021 units remains the better-validated PM sensor, which is a good reason to keep one old unit running as a co-location reference.

### Add light now, leave room for formaldehyde, skip the other gases

The extended categories sort cleanly by how much indoor information they add per dollar.

**Ambient light is the easy win.** A VEML7700-TR costs about $0.62–0.96 at LCSC ([LCSC C504893](https://www.lcsc.com/product-detail/C504893.html)), has a native ESPHome platform ([ESPHome](https://esphome.io/components/sensor/veml7700/)), and gives the light bar the auto-dimming Sonoff users wanted.

**Formaldehyde is the most meaningful new gas.** The electrochemical Sensirion SFA40 is specified at **±20 ppb or ±20%**, has ethanol cross-sensitivity under 0.3% and a lifetime over six years, and ESPHome has a native `sfa40` platform ([Sensirion](https://sensirion.com/products/catalog/SFA40), [ESPHome](https://esphome.io/components/sensor/sfa40/)). No bare-part price was found, and SparkFun's breakout costs **$49.95** ([SparkFun](https://www.sparkfun.com/sparkfun-formaldehyde-sensor-sfa40.html)). Fitting it to every unit would break the budget. Instead, put a Qwiic socket on every board and add the breakout only in a room with new furniture or flooring.

**Ozone and NO2 cells are not worth it.** Indoor ozone sits in the low tens of ppb, below what hobby cells resolve. Low-cost NO2 cells scored R² near 0 to 0.29 in AQ-SPEC tests ([AQ-SPEC gas](https://www.aqmd.gov/aq-spec/evaluations/criteria-pollutants/summary-gas)). The large NO2 peaks from gas stoves, often over 100 ppb ([Stanford](https://news.stanford.edu/stories/2024/05/people-with-gas-and-propane-stoves-breathe-more-unhealthy-nitrogen-dioxide)), already show up in the SEN66's NOx index.

**CO is optional, and only for homes with combustion appliances.** Even then it must be labelled as not being a CO alarm, as Apollo labels its MiCS sensor ([Apollo](https://wiki.apolloautomation.com/products/air1/setup/sensor-definitions/)).

**Sound should wait.** The two go-to hobby microphones are EOL (ICS-43434) or not recommended for new designs (INMP441) ([TDK](https://invensense.tdk.com/products/ics-43434/), [TDK](https://invensense.tdk.com/digital/inmp441)). ESPHome's native component reports only relative dBFS and warns about conflicts with BLE ([ESPHome](https://esphome.io/components/sensor/sound_level/)).

**mmWave presence is an optional header.** An LD2410 on a spare UART is natively supported ([ESPHome](https://esphome.io/components/sensor/ld2410.html)). It can switch the light bar off in empty rooms.

**Radon is excluded, as the builder requested.** The research found the RD200M module costs about $80 and needs its own vented space, which would consume most of the budget on its own ([Botmonster](https://botmonster.com/smart-home/diy-radon-detector-esphome-home-monitoring/)).

## A 4.7 KB frame buffer lets a cool ESP32-C6 drive the display

The ESP8266 and the Nextion both go. ESPHome's display stack now drives bare panels natively, which removes the Nextion's second processor and its heat. The ESP8266 lacks the RAM for ESPHome's LVGL ([ESPHome LVGL](https://esphome.io/components/lvgl/)). The right replacement is the **ESP32-C6-MINI-1**, not the more popular ESP32-S3. A 296×128 one-bit frame needs only **4,736 bytes**, so the S3's PSRAM buys nothing here.

What matters on this board is heat, and the C6 runs cooler. Its datasheet gives modem-sleep current with the CPU running of **27 mA at 160 MHz and 19 mA at 80 MHz** with peripheral clocks off, or 38 mA and 30 mA with them on ([Espressif](https://documentation.espressif.com/esp32-c6_datasheet_en.html)). In contrast, ESPHome 2026.4.0 raised the S3's default clock to 240 MHz ([ESPHome 2026.4.0](https://esphome.io/changelog/2026.4.0/)). The C6 also brings an 802.15.4 radio. ESPHome supports OpenThread and Zigbee on it ([ESPHome OpenThread](https://esphome.io/components/openthread/)) but still has no Matter layer ([feature request #1397](https://github.com/esphome/feature-requests/issues/1397)). That makes the radio a hedge if the design is ever sold into Matter homes.

Two risks need managing. C6 stock at LCSC swung between 0 and ~3,500 units across snapshots ([LCSC](https://www.lcsc.com/product-detail/C5736265.html)), so lay out a footprint that also fits an S3-MINI as a fallback. Avoid the C5: one LCSC SKU is flagged discontinued ([LCSC](https://www.lcsc.com/product-image/C53054799.html)). Use a module rather than a bare chip, so radio certification rests on the module's existing approvals and the board needs no antenna design.

For the panel, use a **GoodDisplay GDEY029T94** (296×128, 3 s full refresh, 0.3 s partial) ([Good Display](https://www.good-display.com/product/389.html)) or a Waveshare 2.9" V2. The GoodDisplay panel lists at **$8.70, or $8.27 each for 10–49** ([BuyEPaper](https://buyepaper.com/products/29-inch-e-paper-screen-296x128-raspberry-pi-spi-display-gdey029t94)). One caveat decides between them. ESPHome's new `epaper_spi` driver lists partial refresh for the **Waveshare-2.9in-v2 model but not for GDEY029T94** ([ESPHome epaper_spi](https://esphome.io/components/display/epaper_spi/)). Prototype with both and lock in whichever ESPHome refreshes partially without ghosting. One developer had to force a full refresh on every update for M5Stack's 1.54" panel ([Codeberg](https://codeberg.org/stackdrift/esphome-components/pulls/7)).

Set the refresh cadence by GoodDisplay's rules: a full refresh after every five partial updates, and rest intervals of about 180 s ([Good Display](https://www.good-display.com/news/80.html)). A sensible split is to let the e-ink update every three minutes with two large numbers, CO2 in ppm and PM2.5 in µg/m³, plus a small T/RH line. The light bar then provides the real-time cue, showing the worse of the CO2 and PM bands. Keep VOC and NOx as small icons labelled as relative indices, never as ppb, because Sensirion's index has no absolute concentration behind it ([Sensirion](https://sensirion.com/media/documents/02232963/6294E043/Info_Note_VOC_Index.pdf)). GoodDisplay also sells a front-lit GDEY029T94 variant ([BuyEPaper](https://buyepaper.com/products/029-inch-small-e-ink-display-with-frontlight-display-panel-gdey029t94-fl03-645)). The light bar makes it unnecessary, and its light would add heat.

If e-ink's refresh flash proves annoying, the runner-up is a reflective LCD. ESPHome 2026.11 added an `st7305` driver for a 4.2" 400×300 panel that has no backlight and updates in about a second ([ESPHome st7305](https://esphome.io/components/display/st7305/)). Waveshare sells that panel on a $24.99 ESP32-S3 board ([CNX Software](https://www.cnx-software.com/2026/01/06/esp32-s3-development-board-features-4-2-inch-reflective-lcd-rlcd-dual-microphone-array-onboard-speaker/)). The driver is weeks old.

Firmware settings follow from the thermal goal. Set `cpu_frequency: 80MHz` and keep Wi-Fi `power_save_mode: LIGHT`, which is the default ([ESPHome Wi-Fi](https://esphome.io/components/wifi/)). Don't run a Bluetooth proxy on these nodes. Feed the BMP585 into the SEN66's pressure compensation. Use the new `voc_index`/`nox_index` keys, because the old keys disappear in ESPHome 2027.2.0 ([ESPHome sen6x](https://esphome.io/components/sensor/sen6x/)).

CO2 self-calibration (ASC) assumes the room sees outdoor air at about 400 ppm weekly. In a rarely ventilated room, switch it off and recalibrate outdoors every year or two, as Apollo advises ([Apollo FAQ](https://wiki.apolloautomation.com/products/air1/faq/)). A front button wired to forced recalibration makes this as easy as AirGradient's calibration button ([SmartHomeScene](https://smarthomescene.com/reviews/airgradient-one-review-and-esphome-integration/)).

For power, size the 3.3 V supply as a buck converter rated for at least 1 A. The SEN66's 350 mA pulses and the C6's 354 mA transmit peaks can coincide. A linear regulator dropping 5 V to 3.3 V would also put avoidable heat beside the sensors.

## Factory assembly on JLCPCB's Economic tier beats every solder-it-yourself route

For a builder who couldn't hand-solder SMT reliably, the comparison is lopsided. JLCPCB's October 2026 fee schedule makes the Economic tier the cheapest route: **$8.18 setup, $1.53 stencil, $0.0016 per joint, and $3.07 per unique "Extended" part**. Basic and "Preferred Extended" parts carry no loading fee ([JLCPCB](https://jlcpcb.com/help/article/pcb-assembly-price), [JLCPCB blog](https://jlcpcb.com/blog/reduce-pcb-assembly-cost-prototype)). Standard costs $25.56 setup, $8.21 stencil, $16.42 of fixtures and $1.53 for every unique part. The Economic tier has three constraints: parts on one side only, no V-cut panels, and 2–50 boards per order. JLCPCB fabricates at least five boards but will assemble as few as two ([JLCPCB blog](https://jlcpcb.com/blog/reduce-pcb-assembly-cost-prototype)).

| Route | Fees or tooling for 5 boards | Builder effort | Verdict for this builder |
|---|---|---|---|
| **JLCPCB Economic, SEN66 and e-ink plugged in** | **~$52 fees** (calculated, ~13 Extended parts) | Upload files, check placement, plug in cable and ribbon | **Recommended** |
| JLCPCB Standard (SCD41 on board, discrete Plan B) | ~$98 fees (calculated, ~25 unique parts) | Same | Only for Plan B |
| Hybrid: factory SMT plus own through-hole parts | Saves $0–10 against the above | Through-hole soldering only, which this builder can do | Built into the recommendation if any through-hole parts remain |
| Aisler (EU) | ~€645 (€75 setup + €0.38 per placement × ~1,500) | Low | Far over budget |
| PCBWay | Advertises $29 for 1–20 boards; terms unconfirmed | Low | Worth one comparison quote |
| DIY stencil + hot plate | $150–400 of tooling | High; hidden LGA/DFN pads | Rejected |
| 2021-style breakout carrier | ~$40–80 per unit in breakouts (unsourced) | Low | Fallback only; bulky "maker" look |

Sources: [JLCPCB](https://jlcpcb.com/help/article/pcb-assembly-price), [Aisler](https://community.aisler.net/t/our-simple-pricing/102), [PCBWay](https://www.pcbway.com/quotesmt.aspx?f=fa), [Elektor MHP50](https://www.elektormagazine.com/review/miniware-mhp50-hot-plate). Fee totals are calculated estimates.

**DIY reflow fails on exactly the parts this board needs.** The SHT45 is a 1.5 mm DFN and the SCD41 a 10.1 mm LGA, both with pads hidden underneath. JLCPCB's own QFN guide calls hand-dosing paste on hidden pads largely guesswork ([JLCPCB](https://jlcpcb.com/blog/how-to-solder-qfn-components-a-step-by-step-guide)). An experienced hobbyist found stencil-and-hot-plate reflow no better than his earlier attempts, with bridges wherever paste smeared ([Big Mess o' Wires](https://www.bigmessowires.com/?p=4425)). Palm-sized plates such as the Miniware MHP50 are reviewed as suited to small boards, not a ~90 mm main board ([Elektor](https://www.elektormagazine.com/review/miniware-mhp50-hot-plate)). The 0.5 mm e-ink connector and the USB-C receptacle are the two parts most likely to defeat a beginner, and the factory places both.

**The Economic plan only works if every placed part is Economic-eligible.** Check this in JLCPCB's BOM tool before routing. A single Standard-only part moves the whole order to Standard and roughly doubles the fees. The SEN66 isn't stocked at JLCPCB and doesn't need to be, because it arrives from a distributor and plugs into its header. Parts JLCPCB must buy in through Global Sourcing carry minimum order quantities. Leftovers stay in a JLCPCB library and can't be shipped to the builder ([JLCPCB blog](https://jlcpcb.com/blog/reduce-pcb-assembly-cost-prototype)). That is a reason to pick in-stock parts and to reuse the same resistor and capacitor values across the board.

**Order in two steps.** First fabricate five bare boards and have two assembled. They prove the footprints, the e-ink ribbon fit and the thermal layout, and become units 1 and 2 if they work. Then assemble the rest. The second order adds about $50 in fixed fees, roughly $5 per unit spread over ten.

**Reproducibility and a path to certification both point the same way.** Publish the KiCad source plus a BOM with LCSC part numbers, the CPL placement file, the ESPHome YAML and the STEP and 3MF enclosure files. Use a pre-certified radio module, stay on 5 V USB power, and pick a licence AirGradient has already tested: CC-BY-SA 4.0 with OSHWA certification ([OSHWA](https://certification.oshwa.org/th000013.html)). AirGradient also shows how a small seller splits the offer. Its kit ships without warranty or certifications, while the assembled unit carries CE, FCC, RoHS and REACH ([AirGradient](https://www.airgradient.com/indoor/)). Any sale also has to account for the SEN6x being a **Class 1 laser product** ([SEN6x datasheet](https://cdn.soselectronic.com/productdata/b9/20/bdca9efc/sen60-sin-t.pdf)). Check your own market's rules before selling anything assembled.

## The wedge must keep sensors low, heat high and exhaust away from intake

Every Sensirion design guide gives the same geometry, and a desk wedge suits it well.

**The sensor zone sits low and in the coolest air.** VOC sensors belong in the coldest part of the device, below heat sources, because convection carries waste heat upward ([SGP4x Design-In Guide](https://cdn.sparkfun.com/assets/6/c/d/d/7/GAS_SGP4x_Design-In_Guide_D1.pdf)). The SEN6x should sit as far from heat sources as possible, and below them ([SEN6x mechanical guide](https://www.laskakit.cz/user/related_files/sensirion_ps_an_sen6x_mechanical_design_and_assembly_guidelines.pdf)). In the wedge, the SEN66 lies flat in the base. Sensirion approves horizontal or lateral orientation and warns against openings facing straight up or down, which collect dust.

**The SEN66's intake and exhaust are sealed apart.** The two inlets and the outlet each couple straight to a grille in the shell, are sealed from each other with foam or TPU, and are sealed from the case interior. Otherwise the fan pulls exhaust or warm case air back in. Sensirion also warns that any airflow restriction lowers the particle count rate proportionally ([SEN6x guide](https://www.laskakit.cz/user/related_files/sensirion_ps_an_sen6x_mechanical_design_and_assembly_guidelines.pdf)). The intake grille goes on the lower front lip or the sides, facing the room. Desks and shelves emit VOCs, so openings stay at least ~1 cm off any surface ([SGP4x guide](https://cdn.sparkfun.com/assets/6/c/d/d/7/GAS_SGP4x_Design-In_Guide_D1.pdf)). The exhaust exits low at the back, behind a printed baffle that reaches the shell. An AirGradient-community enclosure uses the same baffle ([3dsearch](https://3dsearch.net/model/airgradient-diy-basic-enclosure-tv7010024)). A newer revision of the guide reportedly specifies 56 mm² of inlet area and 148 mm² of outlet area, but that is unverified. Until the current PDF confirms it, make each grille's open area at least twice the port it serves.

**The SHT45 sits on its own PCB tongue at the intake.** Sensirion says about 2 cm of distance plus milled slits around the sensor is enough isolation ([SGP4x guide](https://cdn.sparkfun.com/assets/6/c/d/d/7/GAS_SGP4x_Design-In_Guide_D1.pdf)). Strip copper around it as well ([SHTxx design guide](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/2599/HT_AN_SHTxx_STSxx_Design%20Guide_V1.1_D1.pdf)). The tongue sits upstream of the SEN66, which itself dissipates about 0.3 W.

**The main board stands behind the display in the electronics zone.** The ESP32-C6 and the buck converter sit at the top near the ridge. A printed wall separates that zone from the sensor zone, and exhaust slots in the upper rear vent it.

**The light bar goes along the top ridge.** A translucent band just below the apex is visible across a room. More importantly, it sits in the hot zone. Sensirion warns that any change in operating mode, such as screen brightness or lights, changes waste heat and invalidates temperature compensation ([Sensirion app note](https://sensirion.com/media/documents/C964FCC8/69709EC3/PS_AN_SEN6x_Temperature_Compensation_and_Acceleration_Application_No.pdf)). Cap the LEDs' brightness, let the VEML7700 (behind a small window low on the front face) dim them, and calibrate at typical brightness. Stacking the electronics directly on the SEN66, as one popular build does ([Medium](https://medium.com/@monkeytypewritr/building-an-e-ink-air-quality-monitor-w-home-assistant-integration-b9a5602e2e7b)), is the pattern to avoid.

Calibration closes the loop. Sensirion recommends designing for **less than 5 °C over-temperature** before relying on software. It also recommends characterising the device on a wooden plate that mimics a desk, with the reference thermometer at least 20 cm away and not above the device. For an IAQ monitor it gives an acceleration preset ("Light (IAQM)": T1=100, T2=300, K=20, P=20) ([Sensirion app note](https://sensirion.com/media/documents/C964FCC8/69709EC3/PS_AN_SEN6x_Temperature_Compensation_and_Acceleration_Application_No.pdf)). ESPHome's `sen6x` exposes these offset, slope, time-constant and acceleration parameters ([ESPHome](https://esphome.io/components/sensor/sen6x/)). Sensirion's VOC check is simple. Place an ink pen 10 cm from the device: a good design rises in under 30 s and recovers in under a minute ([SGP4x guide](https://cdn.sparkfun.com/assets/6/c/d/d/7/GAS_SGP4x_Design-In_Guide_D1.pdf)). None of the hobby enclosures surveyed publishes either test. Publishing both would make this design stand out.

**Material.** Print in **ASA** if the printer has an enclosure, and PETG if not. AirGradient ships ASA, Sensirion lists hard plastics such as ABS and PC as suitable near gas sensors, and PLA creeps near warm electronics. Every common FDM plastic keeps emitting VOCs after printing. A 2024 study found ABS, PLA, PETG and PC all off-gassing at broadly similar rates ([Mangin et al.](https://doi.org/10.3390/s24082610)). Air new parts for several days and let the VOC index re-learn its baseline before trusting it.

**Printing.** For a modern finish, print the front face down on textured PEI to get a moulded-looking matte face. Put ≥3 mm chamfers on build-plate edges, use vertical slots or 45° louvers about 1.2 mm wide for the grilles, and fit heat-set inserts entered from underneath. Use light fuzzy skin on visible side walls only ([Bambu forum](https://forum.bambulab.com/t/tip-no-ringing-no-seams-no-visible-layers-homogeneous-color/27731)). Start clearances at 0.1–0.15 mm for alignment features, 0.15–0.2 mm for removable parts and 0.2–0.3 mm around snap arms, and print test coupons first ([UAL makerspace](https://wiki.cci.arts.ac.uk/books/digital-fabrication-lab/page/design-the-clearance-and-tolerance), [Zbotic](https://zbotic.in/3d-printing-tolerances-designing-gaps-for-press-fits-threads-and-snap-fits/)).

**Noise.** The fan is rated under 24 dB(A) at 0.2 m. Most audible noise comes from rigid coupling to the case, so mount the module firmly on a thin foam layer without wrapping it ([SEN6x guide](https://www.laskakit.cz/user/related_files/sensirion_ps_an_sen6x_mechanical_design_and_assembly_guidelines.pdf)). Schedule the fan-cleaning bursts for daytime.

## KiCad 10 completes a toolchain the builder mostly already owns

The only new software needed is **KiCad 10**, which is free. Version 10.0.0 shipped on 20 March 2026, and 9.x is no longer maintained ([KiCad](https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/)). Eagle is no longer an option: Autodesk ended access on 7 June 2026 and points users to the subscription-based Fusion Electronics ([Autodesk](https://www.autodesk.com/products/fusion-360/blog/eagle-to-autodesk-fusion-transition/)).

EasyEDA, the 2021 tool, has the tightest JLCPCB integration. Its Pro format, however, is a zipped JSON-Lines archive whose scripting API runs only inside the browser editor, and it has no command-line DRC or export ([EasyEDA](https://prodocs.easyeda.com/en/api/reference/pro-api.html)). That rules it out for an AI-assisted, reproducible open-source workflow.

KiCad closes those gaps. Its S-expression text files can be edited by Claude Code. Its `kicad-cli` runs ERC and DRC with JSON output and exit codes, and exports Gerbers, drill, placement, BOM and STEP files headlessly ([KiCad CLI](https://docs.kicad.org/10.0/en/cli/cli.html)). Its built-in EasyEDA importer can bring in the 2021 board as a reference ([KiCad dev docs](https://dev-docs.kicad.org/en/import-formats/easyeda/index.html)). Exports from EasyEDA Pro editor 2.2 and later need KiCad 10.0.4 or newer ([Hackaday.io](https://hackaday.io/project/206867-epro2kicad-easyeda-pro-to-kicad-headless)).

Three free add-ons complete the JLCPCB link. **Fabrication Toolkit**, which JLCPCB itself recommends, exports Gerbers, BOM and CPL in JLCPCB's format ([JLCPCB](https://jlcpcb.com/help/article/how-to-generate-the-bom-and-centroid-file-from-kicad)). **Bouni's kicad-jlcpcb-tools** assigns LCSC part numbers ([GitHub](https://www.github.com/Bouni/kicad-jlcpcb-tools)). **easyeda2kicad** pulls symbols, footprints and 3D models by LCSC number. Its README warns that converted footprints aren't guaranteed correct, so check every LGA and USB-C pad map against the datasheet ([easyeda2kicad](https://github.com/uPesy/easyeda2kicad.py)).

Community MCP servers, including ones built for KiCad 10 and Claude Code, can drive the design ([kicad-claude-mcp](https://github.com/greg3001/kicad-claude-mcp), [KiCAD-MCP-Server](https://github.com/mixelpixx/KiCAD-MCP-Server)). Their maturity varies, so pin one to the installed KiCad version. Code-first front ends such as atopile still finish layout in KiCad ([atopile](https://github.com/atopile/atopile)), so they add a learning layer without removing the dependency.

The mechanical side needs nothing new. SolidCraft's command set includes **Insert STEP**, which brings a STEP assembly in as components with clearance and interference checks, along with STEP, STL and 3MF export. The loop is therefore `kicad-cli pcb export step` → SolidCraft enclosure modelled around the real board → 3MF → Bambu Studio. Make gasket thickness, wall thickness and clearances SolidCraft parameters, so the test coupons regenerate in seconds.

## Ten units land near $90 each; five land near $98

The table prices the recommended build. Sourced prices are JLCPCB/LCSC or vendor figures from 25 November 2026. **Every line marked "est." is an unsourced estimate**, and the fee lines are calculated from JLCPCB's published schedule. None of it covers shipping, import duty, the USB power supply or a prototype round.

| Line item | Part and basis | Per unit at 5 | Per unit at 10 | Basis |
|---|---|---|---|---|
| All-in-one sensor | SEN66 (PM, CO2, VOC/NOx, T/RH) | $52.00 | $50.00 | Distributor range $47–61 ([DigiKey](https://www.digikey.com/en/products/detail/sensirion-ag/SEN66-SIN-T/25700945)); midpoint is est. |
| T/RH reference | SHT45-AD1B-R2 | $5.72 | $5.72 | [JLC](https://jlcpcb.com/partdetail/C5221601) |
| Pressure | BMP585 | $3.59 | $3.59 | [JLC](https://jlcpcb.com/partdetail/C18184976) |
| Ambient light | VEML7700-TR | $0.96 | $0.96 | [LCSC](https://www.lcsc.com/product-detail/C504893.html) |
| MCU | ESP32-C6-MINI-1-N4 | $4.87 | $4.50 | [LCSC](https://www.lcsc.com/product-detail/C5736265.html) $3.16–4.87; 10-unit figure is est. |
| Display | GDEY029T94 2.9" B/W e-ink | $8.45 | $8.27 | [BuyEPaper](https://buyepaper.com/products/29-inch-e-paper-screen-296x128-raspberry-pi-spi-display-gdey029t94) tier prices |
| Display driver | FPC connector, boost inductor, MOSFET, diodes, capacitors | $1.50 | $1.50 | est. |
| Light bar | ~8 addressable RGB LEDs + translucent filament | $1.50 | $1.50 | est. |
| Power and I/O | USB-C, buck converter, ESD, passives, JST-GH + Qwiic headers, button | $3.50 | $3.50 | est. |
| Bare PCB | 2-layer, ~90×60 mm | $1.50 | $1.00 | est. |
| Assembly fees share | JLC Economic: setup, stencil, ~13 Extended parts, joints | $10.41 | $5.41 | Calculated from the [JLC fee schedule](https://jlcpcb.com/help/article/pcb-assembly-price) |
| Enclosure | ~100 g ASA, inserts, foam gasket, felt feet | $4.00 | $4.00 | est. |
| **Total** | | **≈ $98** | **≈ $90** | Shipping, duty, PSU and prototype round excluded |

Three findings fall out of the arithmetic. First, the **SEN66 is 53–56% of the unit cost**, and sensors overall are about two-thirds. Everything the builder controls (display, MCU, PCB, enclosure) totals about $25.

Second, the cheapest legitimate cuts are modest. Swapping the SHT45 for an SHT40 saves $3.86, buying the SEN66 at the $47 end of the range saves $3–5, and going from five units to ten saves $5 in fees. Together they reach roughly **$83 per unit at ten**. Getting below that means downgrading CO2 or PM, the two numbers on the screen.

Third, the discrete Plan B doesn't save money. At ten units, sensors plus assembly fees compare as follows:

| Sensor route at 10 units | Sensors | Assembly share | Sum | Catch |
|---|---|---|---|---|
| **SEN66 + SHT45 + BMP585 (Economic)** | $59.31 | $5.41 | **$64.72** | One airflow path; SEN66 lead times |
| SCD41 + SGP41 + SEN62 + SHT45 + BMP585 (Standard) | $54.74 | ~$9.43 | ~$64.17 | SEN62 out of stock at JLC and unvalidated; three sealed openings |
| SCD41 + SGP41 + SPS30 + SHT45 + BMP585 (Standard) | $71.60 | ~$9.43 | ~$81.03 | Best-validated PM, but pushes the total past $100 |
| SEN63C + SGP41 + BMP581 (value) | $37.59 | ~$5.41 | ~$43.00 | CO2 is ±(100 ppm + 10%) and labelled "not compliant" |

Component prices come from the JLC parts linked above, plus [SEN63C](https://jlcpcb.com/partdetail/C52088895) and [BMP581](https://jlcpcb.com/partdetail/C5362283). Assembly shares are calculated from JLCPCB's Economic and Standard fee schedules.

The discrete route wins only in two cases: if SEN66 lead times turn out to be months, or if the SCD43's ±60 ppm at 1,000 ppm becomes worth chasing once it is back in stock.

## Conclusion

The 2021 build used breakouts because factory assembly seemed out of reach. In 2026 the economics have flipped. **JLCPCB's Economic fees of about $5–10 per board cost less than the breakouts they replace**, and factory assembly is the only soldering-free route to a board small enough for a sleek wedge. That moves the real constraint from manufacturing to thermals: where the ESP32, the LEDs and the SEN66's own 0.3 W sit relative to the air the sensors breathe. The budget is shaped like the board. Roughly $60 buys sensor quality and the remaining ~$30 buys everything else. "Much less than $100" therefore isn't available without giving up the CO2 or PM accuracy the display exists to show, and the design should spend on sensors and economise everywhere else.

Two choices make this more than a personal project. First, the **SEN6x family's common body turns one board and enclosure into a platform**: SEN66 for most rooms, SEN69C where formaldehyde matters, SEN62 where only particles do. A public design can serve several needs without a respin. Second, **validation is the missing ingredient in hobby designs**, and it costs almost nothing to add. None of the surveyed hobby builds documents a reference-thermometer comparison or an ink-pen VOC test. One 2021 unit, whose SPS30 has stronger independent field data than any SEN6x, can sit beside the new units as that PM reference. Publishing those results alongside the KiCad, ESPHome and 3MF files is what would make the design credible enough to share, and a sensible first step if a sale ever happens.
