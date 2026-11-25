# Extended indoor environmental sensors (HCHO, O3, NO2, CO, radon, light, sound, occupancy): status as of late 2026

Scope: the "extra" sensor categories for refreshing a 2021 ESPHome/Home Assistant DIY monitor (SCD4x, SGP40, SPS30, BMP280). The new design targets an ESP32-class MCU, a factory-assembled SMT PCB, and a 3D-printed enclosure. CO2/PM/VOC/NOx/T/RH/P and the SEN6x modules as a whole are covered by another researcher. They appear here only where they overlap (the HCHO channel in SEN68/SEN69C, and the SGP41 NOx index).

Research date: 2026-11-25. Sources are mostly manufacturer pages, ESPHome docs, and a few independent evaluations. Specs taken from blogs or distributors are marked as such.

---

## Q1. Formaldehyde (HCHO): which sensor, and is it accurate at indoor levels?

### Takeaway
Electrochemical HCHO is the only low-cost approach that is credible at indoor ppb levels, and the Sensirion SFA40 is the clear pick for 2026. It is a small SMD-style part with I²C, ±20 ppb or ±20% accuracy, ethanol cross-sensitivity under 0.3%, a lifetime over 6 years, and a native ESPHome `sfa40` platform. If the other researcher's recommendation ends up being a SEN68 or SEN69C, HCHO is already built in with the same headline spec, so a separate HCHO sensor would be redundant. The older Winsen ZE08-CH2O and Dart WZ-S style UART cells work, but they have no native ESPHome support (ZE08) or no independent validation, so treat them as fallbacks only. **Tier: worth adding** (via SFA40, or via SEN68/69C if that module is chosen).

### Cited Findings
**Sensirion SFA40 (current part, successor to SFA30)**
- Electrochemical formaldehyde sensor for indoor air quality, able to detect formaldehyde "as low as tens of ppb". Range 0–2000 ppb. Accuracy ±20 ppb or ±20% of measured value (whichever is larger), specified for 0–200 ppb in otherwise clean air. Ethanol cross-sensitivity <0.3%. — [Sensirion SFA40 catalog page](https://sensirion.com/products/catalog/SFA40); [DigiKey SFA40 highlight](https://www.digikey.com/es/product-highlight/s/sensirion/sfa40-formaldehyde-sensor)
- I²C digital output, factory calibrated in Switzerland. Supply 1.62–3.6 V (per datasheet and search summaries) or 1.8–3.6 V (per catalog page), so check the datasheet. About 80 µA average and 2 mA max current. Package 13 × 10 × 2.4 mm. — [Sensirion SFA40 datasheet](https://sensirion.com/media/documents/27767BDE/69D61CAE/Datasheet_SFA40.pdf); [Sensirion catalog page](https://sensirion.com/products/catalog/SFA40)
- Datasheet lifetime is >6 years. — [Sensirion SFA40 datasheet](https://sensirion.com/media/documents/27767BDE/69D61CAE/Datasheet_SFA40.pdf)
- Launched as the SFA30's successor ("builds on the market success of its predecessor, SFA30"). The catalog tags it "Available 2026". The datasheet found is v1.0 dated April 2026. One retailer still showed "Coming Soon", so stock may vary by distributor. — [Sensirion catalog](https://sensirion.com/products/catalog/SFA40); [Avnet NPI](https://www.avnet.com/americas/products/new-product-introductions/npi/sensirion-sfa40/); [SelectScience](https://www.selectscience.net/article/the-next-generation-formaldehyde-sensor-sfa40)
- Breakouts: SparkFun Qwiic SFA40 (about $49.95), DFRobot Gravity SFA40, and the Sensirion SEK-SFA40 evaluation kit (needs SEK-SensorBridge). — [SparkFun](https://www.sparkfun.com/sparkfun-formaldehyde-sensor-sfa40.html); [Mouser DFRobot Gravity SFA40](https://www.mouser.in/en/new/dfrobot/dfrobot-gravity-sfa40-hcho-sensor/); [Mouser SEK-SFA40](https://www.mouser.in/en/new/sensors/sensor-development-tools/multiple-function-sensor-development-tools/sensirion-sek-sfa40-eval-kit/n-d0qzdZ2iq2fv)
- Sensirion has a Design-In Guide and Handling Instructions for the SFA40 (relevant to PCB/enclosure airflow design). — [SFA40 Design-In Guide](https://sensirion.com/media/documents/851ABA76/6A38E89C/DesignIn_Guide_SFA40.pdf); [SFA40 Handling Instructions](https://sensirion.com/media/documents/57BBCF4B/6A38E93F/Handling-Instructions_SFA40.pdf)
- **ESPHome:** there is a native `sfa40` platform (I²C) that outputs formaldehyde, temperature, and humidity. The source auto-detects production units and engineering-sample (B4) units. — [ESPHome SFA40 docs](https://esphome.io/components/sensor/sfa40/); [ESPHome sfa40 source (2026.11.0-dev)](https://api-docs-dev.esphome.io/sfa40_8cpp_source)

**Sensirion SFA30 (predecessor)**
- ESPHome still has a native `sfa30` platform (I²C; UART "listed but not implemented"), outputting formaldehyde, temperature, and humidity. — [ESPHome SFA30 docs](https://esphome.io/components/sensor/sfa30/); [new.esphome.io SFA30](https://new.esphome.io/components/sensor/sfa30)

**HCHO built into the SEN68 / SEN69C combo modules**
- The SEN69C's HCHO channel is specified at 0–2000 ppb and ±20 ppb or ±20% of measured value, the same headline accuracy as the SFA40. — [Sensirion SEN69C catalog](https://sensirion.com/products/catalog/SEN69C)
- Range conflict: Sensirion's SEN68 page lists HCHO as 0–1000 ppb, and Mouser's SEK-SEN69C listing also says 0–1000 ppb, while the SEN69C catalog page says 0–2000 ppb. — [Sensirion SEN68](https://www.sensirion.com/products/catalog/SEN68); [Mouser SEK-SEN69C](https://www.mouser.in/new/sensirion/sensirion-sek-sen69c-kit/); [Sensirion SEN69C](https://sensirion.com/products/catalog/SEN69C)
- SEN69C module: I²C, 3.15–3.6 V, about 80 mA average, 55.2 × 25.6 × 21.3 mm. Its CO2 channel is ±100 ppm and marked "CO2 not compliant, see SEN66 instead" (relevant to the other researcher). — [Sensirion SEN69C](https://sensirion.com/products/catalog/SEN69C)
- The ESPHome `sen6x` component supports SEN62/63C/65/66/68/69C. The `formaldehyde:` option (ppb) works only on SEN68 or SEN69C, and the code errors with "Formaldehyde requires SEN68 or SEN69C" on other models. — [ESPHome SEN6x docs](https://esphome.io/components/sensor/sen6x/); [sen6x source](https://api-docs-dev.esphome.io/sen6x_8cpp_source)
- The SEN6x has an HCHO sensor-error flag. The CircuitPython driver notes that HCHO values may be unknown or wrong while that flag is set. — [Sensirion SEN6x datasheet](https://sensirion.com/media/documents/FAFC548D/693FBB15/PS_DS_SEN6x.pdf); [CircuitPython SEN6x API](https://docs.circuitpython.org/projects/sen6x/en/latest/api.html)

**Winsen ZE08-CH2O, Dart WZ-S, Plantower PMS5003ST**
- ZE08-CH2O has no native ESPHome platform. A community gist (UART, 9600 baud, ppb output) provides a custom component, and a fork (haplm/winsen_ze08_ch2o) is reported to work with ESPHome 2025.2+. One commenter reported about 25 ppb outdoors, which they considered implausibly high. — [cretep ZE08 gist](https://gist.github.com/cretep/f96606dc6a4eae0d85993d6085959220)
- Dart WZ-S and Prosense WZ-H3 formaldehyde sensors have an Arduino library but no ESPHome platform turned up. — [Arduino WZ library](https://arduino.cc/reference/en/libraries/wz-library)
- The Plantower PMS5003ST (PM sensor plus electrochemical HCHO probe and T/RH) is natively supported by ESPHome `pmsx003`, which reports formaldehyde in µg/m³. A vendor page claims HCHO error below ±5%, but no independent validation was found. — [ESPHome PMSX003](https://esphome.io/components/sensor/pmsx003/); [Botland PMS5003ST](https://botland.com.pl/en/air-sensors/9532-the-dustair-quality-formaldehyde-temperature-humidity-sensor-pm25-pms5003.html)

### Inferences
- The brief cites a WHO guideline of about 80–100 ppb (0.1 mg/m³ over 30 min; not re-sourced this session). At that level, ±20 ppb or ±20% means roughly ±20 ppb, about 20–25% uncertainty. That is good enough to tell "clean home (<20–30 ppb)" from "new furniture or flooring off-gassing (>50–100 ppb)". It is not good enough for fine-grained trends below about 20 ppb.
- MOx VOC sensors (SGP40/41, ENS160, MiCS) cannot isolate formaldehyde. The SFA40's selectivity claim (ethanol <0.3%) is exactly what separates it from the existing SGP40 VOC index. A dedicated HCHO channel therefore adds genuinely new information.
- If the design moves to a SEN69C (all-in-one), a separate SFA40 is redundant. The SEN69C's weak CO2 spec ("not compliant") argues for SEN68 + SCD41/SCD43, or SEN66 + SFA40, depending on the other researcher's CO2 conclusions. An SFA40 on the main PCB is a low-cost, low-power way to add HCHO to a SEN66-based design.
- The PMS5003ST is attractive as a PM + HCHO two-in-one with native ESPHome support, but it would replace the accuracy-first SPS30/SEN6x PM channel with a Plantower one, and its HCHO accuracy is unverified. It does not fit the accuracy-first philosophy.

### Gaps
- SFA40 warm-up/stabilization time, resolution, and humidity/temperature dependence were not extracted from the datasheet (the catalog page does not list them).
- SFA30 lifecycle status (NRND/EOL?) was not confirmed. Sensirion only calls SFA40 its successor.
- No independent co-location study (e.g., AQ-SPEC) of the SFA40, SEN68/69C HCHO channel, ZE08, or WZ-S at indoor ppb levels was found.
- SFA40 bare-part price (versus $49.95 for the SparkFun breakout) was not found.

---

## Q2. Ozone (O3) and nitrogen dioxide (NO2): are any hobby-price sensors accurate at low indoor ppb?

### Takeaway
Mostly no. Typical indoor ozone is a fraction of outdoor levels (indoor/outdoor ratio about 0.3–0.8). Hobby electrochemical O3 modules resolve only about 10 ppb (Winsen ZE27-O3) to about 150 ppb (SPEC DGS2), and they cross-react with NO2/Cl2 and drift with T/RH. Independent field evaluations of low-cost electrochemical NO2 sensors are poor (AQ-SPEC R² near 0 to about 0.3 for several units). Gas-stove NO2 events, however, are large (peaks of hundreds of ppb, kitchen 1-hour averages above 100 ppb in some homes). A qualitative signal like the SGP41/SEN6x NOx index already captures those events. **Tier: ozone, skip** (unless the user owns ozone-emitting devices). **NO2, skip a dedicated cell and rely on the NOx index**, or treat it as optional, experimental only, for gas-stove homes.

### Cited Findings
**Indoor concentrations (what the sensor would need to resolve)**
- Residential indoor/outdoor ozone ratios typically fall around 0.3–0.8, rising with air-exchange rate. The source text is garbled, so treat this as approximate. — [RSC Environ. Sci.: Processes & Impacts 2019](https://pubs.rsc.org/en/content/articlehtml/2019/em/c9em00129h)
- A Beijing study using low-cost sensors found indoor ozone of -2 to 23 ppb after calibration. — [RSC Environ. Sci.: Processes & Impacts 2020 (Beijing O3)](https://pubs.rsc.org/en/content/articlehtml/2020/em/c9em00377k)
- Gas/propane stove use raises annual-average NO2 exposure by about 4 ppb nationally (US). Cooking can produce peaks of hundreds of ppb, exceeding 100 ppb within minutes. — [Stanford News 2024](https://news.stanford.edu/stories/2024/05/people-with-gas-and-propane-stoves-breathe-more-unhealthy-nitrogen-dioxide); [Lebel et al. 2022, ES&T](https://jacksonlab.stanford.edu/sites/g/files/sbiybj20871/files/media/file/lebel_et_al.2022_stoves_est.pdf)
- In one study, 4 of 9 homes had kitchen 1-hour NO2 above the 100 ppb US ambient standard. Inner-city homes with gas stoves averaged 33.1 ppb NO2 versus 16.8 ppb without. — [Lebel et al. 2022](https://jacksonlab.stanford.edu/sites/g/files/sbiybj20871/files/media/file/lebel_et_al.2022_stoves_est.pdf); [NCBI Bookshelf NBK138707](https://www.ncbi.nlm.nih.gov/books/NBK138707/)

**Winsen ZE27-O3 (electrochemical module)**
- Range 0–10 ppm, resolution 0.01 ppm (10 ppb), response ≤90 s, working life 2 years in air. UART output at 3 V TTL, supply 3.7–5.5 V. — [Winsen ZE27-O3 product page](https://www.winsen-sensor.com/product/ze27-o3.html); [ZE27-O3 datasheet](https://www.winsen-sensor.com/d/files/ZE27-O3.pdf)
- The datasheet lists NO2 and Cl2 as interfering gases (not quantified). Winsen's own O3 guide notes cross-sensitivity to oxidizers (Cl2, NO2) and acid gases, and says humidity and temperature shift zero and slope. — [ZE27-O3 datasheet](https://www.winsen-sensor.com/d/files/ZE27-O3.pdf); [Winsen O3 sensor guide](https://www.winsen-sensor.com/knowledge/o3-sensor.html)
- A Winsen ZE25-O3 also exists (datasheet available, specs not extracted). No ESPHome component for ZE27/ZE25 was found. — [Winsen ZE25-O3](https://www.winsen-sensor.com/product/ze25-o3.html)

**SPEC Sensors (Interlink Electronics) DGS2 digital modules**
- The DGS2 970-series is a family of electrochemical sensors on a digital module with a UART interface (active and low-power modes). Variants include CO (0–400 ppm, and 0–20 ppm with 0.03 ppm resolution), O3 (970-400), NO2 (970-500), and EtOH. The 972-xxx parts are sensor plus module without the USB-UART adapter. — [SPEC 970-series datasheet (Orwintech mirror)](https://orwintech.com/static/pdf/970-100.pdf); [DigiKey 972-500 NO2](https://www.digikey.co.uk/en/products/detail/spec-sensors-a-division-of-interlink-electronics/972-500/22490693)
- Distributor listings give a 2.6–3.6 V supply and ±15% accuracy for the O3 module (972-400). An older developer-kit brochure lists O3 at 20 ppm range / 150 ppb resolution and NO2 at 20 ppm / 100 ppb resolution. These may not reflect the current DGS2 spec. — [Microchip USA 972-400](https://www.microchipusa.com/product/spec-sensors-a-division-of-interlink-electronics/gas-sensors/972-400); [DGS dev kit brochure](https://www.digikey.cn/htmldatasheets/production/2038351/0/0/1/digital-gas-sensor-dev-kit.pdf)
- A study of SPEC DGS-NO2 sensors at an urban background site found they "underperformed tremendously" relative to SPEC DGS-O3 sensors. — [Collier-Oxandale et al. 2020 / AQ-SPEC STAR grant](https://www.aqmd.gov/docs/default-source/aq-spec/star-grant/collier-oxandale-et-al-2020.pdf?sfvrsn=8)

**Independent evaluations (AQ-SPEC and others)**
- In AQ-SPEC field/lab summaries, several electrochemical NO2 sensors showed R² from near zero up to about 0.29. — [AQ-SPEC gas sensor summary](https://www.aqmd.gov/aq-spec/evaluations/criteria-pollutants/summary-gas)
- Collier-Oxandale et al. (2020) evaluated 28 gas-phase sensors: NO2 results were more mixed than CO and O3, and the best NO2 sensor reached r = 0.77 with MAE 5.41 ppb. — [Collier-Oxandale et al., field and lab evaluations of 28 gas-phase sensors](https://www.aqmd.gov/docs/default-source/aq-spec/resources-page/collier_field-and-laboratory-performance-evaluations-of-28-gas-phase-air-quality-sensors.pdf?sfvrsn=6)
- A CARB-funded final report (Contract 22RD020) on low-cost sensors for indoor air quality exists and lists AQ-SPEC evaluations. Its contents were not retrieved. — [CARB 22RD020 Final Report](https://ww2.arb.ca.gov/sites/default/files/2025-05/Research%20Contract%2022RD020%20Final%20Report.pdf)

**Sensirion SGP41 NOx index (relative only)**
- The VOC and NOx Index run on a 1–500 scale via Sensirion's Gas Index Algorithm. The NOx index baseline is 1 (VOC baseline is 100 for a typical indoor environment). It is not an absolute ppb value. — [Sensirion SGP41](https://sensirion.com/products/catalog/SGP41); [Sensirion NOx Index info note](https://www.sudo.is/docs/esphome/components/sgp4x/Info_Note_NOx_Index.pdf)
- The NOx index has no gain adaptation, because NOx event composition varies less than VOC events. Device-to-device tolerance is ±50 index points or ±50%, whichever is larger. — [Sensirion NOx Index info note](https://www.sudo.is/docs/esphome/components/sgp4x/Info_Note_NOx_Index.pdf)
- Sensirion also publishes an info note on oxidizing gases (NOx pixel response). — [Sensirion Info Note Oxidizing Gases](https://sensirion.com:443/media/documents/A00A17D5/6294E01E/Info_Note_Oxidizing_Gases.pdf)

**MOx multi-gas (Amphenol SGX MiCS family)**
- Apollo Automation ships an optional MiCS-4514 (CO, ethanol, H2, NO2, NH3, CH4) in the AIR-1. Its own wiki warns it does not meet safety standards for gas monitoring and should not be relied on as a CO or gas-leak alarm. — [Apollo AIR-1 sensor definitions](https://wiki.apolloautomation.com/products/air1/setup/sensor-definitions/); [SmartHomeScene AIR-1 review](https://smarthomescene.com/reviews/apollo-air-1-review-complete-air-quality-monitoring-for-home-assistant/)
- Home Assistant users discuss MiCS-5524 versus MiCS-6814 for CO with unclear outcomes. — [HA community: MICS-5524 or MICS-6814](https://community.home-assistant.io/t/co-sensor-mics-5524-or-mics-6814/292550)

### Inferences
- With indoor ozone typically in the low tens of ppb or less, a 10 ppb-resolution module with T/RH zero drift and NO2 interference will mostly report noise around zero. It would only show something useful when an ozone generator (ionizer, "ozone purifier", some UV devices) is running, or with windows open during an outdoor ozone episode. Not meaningful as a routine indoor channel.
- For NO2, the meaningful indoor events (gas cooking) are large and short. The SGP41/SEN6x NOx index (already planned via the other researcher's SEN6x/SGP41 selection) should flag them qualitatively. A dedicated NO2 cell with about 100 ppb resolution and documented poor field performance adds cost and calibration burden for limited extra information. Exception: a user with a gas stove who wants to quantify range-hood effectiveness might justify an SPEC DGS2 NO2 module as an experiment.
- MiCS/MOx multi-gas sensors are effectively gimmicks for ppb-level O3 or NO2 indoors because of poor selectivity. Skip them.
- Research-grade cells (Alphasense O3-B4/NO2-B43F with ISB boards) were not price-checked here. They are generally far above hobby pricing and still need per-unit calibration and T/RH correction, so they don't change the recommendation.

### Gaps
- No independent indoor (low-ppb) validation of the Winsen ZE27-O3/ZE25-O3 was found.
- The current DGS2 O3/NO2 resolution and LOD (the brochure's 150/100 ppb may be outdated) could not be confirmed from the official SPEC/Interlink datasheet.
- Alphasense and SGX electrochemical O3/NO2 pricing and indoor-level specs were not retrieved.
- AQ-SPEC per-sensor numbers for the specific modules discussed here were not extracted.
- No ESPHome components were found for ZE27-O3 or DGS2 (both are UART, so a custom/external component would be needed).

---

## Q3. Carbon monoxide (CO): which sensor, and is it useful as a safety-adjacent feature?

### Takeaway
Electrochemical CO cells are mature and reasonably selective. Several hobby-accessible options exist: the Winsen ZE15-CO/ZE07-CO UART modules (community ESPHome external component), Figaro's TGS5141 bare cell (10+ year life, needs a potentiostat/TIA front end) and its upcoming IAQ-oriented CMM5141 module (0–23 ppm, analog), and SPEC DGS2 CO modules (0–20 ppm range at 0.03 ppm resolution). In a home without combustion appliances or an attached garage, indoor CO normally sits near zero, so the channel mostly reads zero. It is useful as an early-warning/curiosity signal where sources exist. It must be clearly labeled as **not** a UL 2034/EN 50291 CO alarm. **Tier: optional** (worth it only for homes with gas/oil/wood appliances or attached garages).

### Cited Findings
**Winsen ZE15-CO / ZE07-CO**
- Both are electrochemical CO modules with a 0–500 ppm range, marketed for household CO alarms and smart-home devices. — [Winsen ZE15-CO](https://www.winsen-sensor.com/product/ze15-co.html); [Winsen ZE07-CO](https://www.winsen-sensor.com/product/ze07-co.html)
- ZE15-CO: UART output (0/3 V logic), 5–12 V DC supply, 0.1 ppm resolution. — [ZE15-CO datasheet](https://www.winsen-sensor.com/d/files/ZE15-CO.pdf); [ZE15-CO manual](https://www.winsen-sensor.com/d/files/manual/ze15-co.pdf)
- ZE07-CO: UART plus a DAC voltage output (0.4–2 V). — [ZE07-CO manual](https://www.winsen-sensor.com/d/files/manual/ze07-co.pdf)
- A community ESPHome external component supports ZE15-CO (auto mode, sensor fault detection) and ZE07-CO (passive or Q&A mode, optional dormant mode) over UART at 9600 baud. The URL found appears to be a GitHub mirror, so verify the original repo before using it. — [esphome-winsen-co-sensor (mirror)](https://github.xiaohuzi123231346.workers.dev/Bjk8kds/esphome-winsen-co-sensor)

**Figaro TGS5141 (bare electrochemical cell) and CMM5141 (module, coming soon)**
- TGS5141-P00: range 0–5000 ppm (typical), output 1.2–3.2 nA/ppm, baseline offset <±10 ppm equivalent (at 20 °C / 40% RH). UL-recognized component under UL 2075. — [Figaro TGS5141-P00 product information rev09](https://www.figarosensor.com/product/tgs5141-p00_product%20information%28fusa%29_rev09.pdf)
- Expected life is 10+ years. There is no water reservoir, so no dry-out degradation. Weight is about 2.5 g. — [Figaro TGS5141 feature page](https://www.figarosensor.com/product/feature/tgs5141.html); [Figaro product information](https://www.figarosensor.com/product/tgs5141-p00_product%20information%28fusa%29_rev09.pdf)
- Output current is very small, so amplification is needed for adequate resolution (i.e., an analog front end on the PCB). — [Figaro TGS5141 manual](https://manuals.online/figaro/accessories/tgs5141-p00/manual/vqk1)
- Figaro CMM5141 module (tentative specs, "coming soon", no launch date): TGS5141-based, factory pre-calibrated, range 0–23 ppm CO, analog output 0–2.3 V (Vconc = ppm/10), 2.5–5.5 V supply, 5 mA max, about 33 × 32 × 13 mm, 0–50 °C. Targeted at IAQ monitoring, ventilation control, low-concentration CO, and wellness devices, not alarms. — [Figaro CMM5141 page](https://www.figarosensor.com/product/feature/cmm5141.html)
- Older Figaro TGS5042 (battery-operable CO cell) datasheet for reference. — [Figaro TGS5042 datasheet (Conrad)](https://asset.conrad.com/media10/add/160267/c1/-/en/001273389DS01/datasheet-1273389-figaro-gas-sensor-tgs-5042-suitable-for-gases-carbon-monoxide-o-x-l-141-mm-x-497-mm.pdf)

**SPEC/Interlink DGS2 CO**
- DGS2 970-series CO modules come in 0–400 ppm and 0–20 ppm ranges. The low range resolves 0.03 ppm. UART interface, 2.6–3.6 V. — [SPEC 970-series datasheet (mirror)](https://orwintech.com/static/pdf/970-100.pdf); [DigiKey 970-010](https://www.digikey.co.uk/en/products/detail/spec-sensors-a-division-of-interlink-electronics/970-010/21380628)
- In Collier-Oxandale et al. (2020), CO and O3 sensors generally performed better than NO2 sensors in field and lab tests. — [Collier-Oxandale et al. 28-sensor evaluation](https://www.aqmd.gov/docs/default-source/aq-spec/resources-page/collier_field-and-laboratory-performance-evaluations-of-28-gas-phase-air-quality-sensors.pdf?sfvrsn=6)

**MOx "CO" sensors**
- ESPHome's device database lists the MQ-7 (MOx). Apollo's MiCS-4514 warning (not for safety) applies to MOx CO sensing generally. — [ESPHome devices: MQ-7](https://devices.esphome.io/devices/mq-7); [Apollo AIR-1 sensor definitions](https://wiki.apolloautomation.com/products/air1/setup/sensor-definitions/)

### Inferences
- **Safety framing:** the TGS5141 is a UL 2075 *component*, but a DIY device built around it is not a listed CO alarm. The firmware/UI should label CO as "informational" and recommend a separate listed CO alarm. Apollo's wiki language for MiCS is a reasonable model for that disclaimer.
- **Accuracy:** for an IAQ display (0–10 ppm region), a sensor with ±10 ppm baseline uncertainty (bare TGS5141 without zero calibration) or 0–500 ppm alarm-oriented modules (ZE07/ZE15) will mostly show zero or noise. A low-range module (DGS2 0–20 ppm, Figaro CMM5141 0–23 ppm) is better matched to IAQ use, if the user wants CO at all.
- **PCB impact:** the ZE15-CO needs 5–12 V, so the board would need a 5 V rail (likely present anyway for an SPS30/SEN6x fan or USB input). The CMM5141 is analog and would use an ESP32 ADC (noisy) or an external ADC. The DGS2 is 3.3 V UART and the simplest electrically, but ESP32 UART count becomes a constraint if radon (UART), CO (UART), and mmWave radar (UART) are all added.
- Recommendation: optional, and only for homes with combustion sources. If chosen, prefer a low-range electrochemical module (DGS2 0–20 ppm, or CMM5141 once available) over 0–500 ppm alarm modules.

### Gaps
- No source was found for typical background indoor CO concentrations in homes without combustion sources.
- DGS2 CO accuracy, drift, and price (2026) were not confirmed from the manufacturer.
- The original GitHub location and maintenance status of the Winsen CO ESPHome component were not verified.
- CMM5141 release date and price are unknown (Figaro says "coming soon").
- Sensirion has no CO sensor that was found in this research.

---

## Q4. Radon: modules, ESPHome integration, cost, size, time to first reading

### Takeaway
Radon is the most health-relevant of the "extra" channels (a leading cause of lung cancer in non-smokers; not re-sourced here) and is invisible to every other sensor in the device. The proven hobby path is the **FTLAB/Ecosense RD200M** pulsed-ion-chamber module: about $80, UART 9600, first reading in about 60 minutes, ±10% above 10 pCi/L, community ESPHome external component. A newer, smaller **Winsen ZD100** alpha-detection module (UART, ≤10 mA, 52.65 × 42.5 × 27.8 mm, 1-minute updates on a 4-hour moving average) exists, but its accuracy is unstated and no independent validation was found. A zero-hardware alternative is to read a consumer **RadonEye RD200** over BLE using ESPHome's native `radon_eye_ble`/`radon_eye_rd200` component. **Tier: worth adding** for anyone in a radon-prone area or with a basement or ground-floor living space. The main costs are size, enclosure venting, and about $80.

### Cited Findings
**FTLAB / Ecosense RD200M**
- Pulsed ion-chamber module with simple UART output. About $80 direct from FTLab or distributors; the full DIY build is about $150. — [Botmonster RD200M + ESPHome build](https://botmonster.com/smart-home/diy-radon-detector-esphome-home-monitoring/)
- Sensitivity 0.5 cpm per pCi/L (30 cph/pCi/L). Range 0.1–99.99 pCi/L. Accuracy "better than ±10% above 10 pCi/L", with minimum error ±0.5 pCi/L, factory calibrated. — [Botmonster](https://botmonster.com/smart-home/diy-radon-detector-esphome-home-monitoring/)
- A third-party product built on the RD200M (RadonTec Expert+) lists accuracy within ±10% (minimum ±0.5 pCi/L), precision <10% at 10 pCi/L, and a 60-minute measuring/storage interval. — [RadonTec Expert+ manual](https://manuals.online/radontec/measuring-instrument/expert/user-manual/1cqjx)
- Time to first reading is about 60 minutes after power-on. A meaningful rolling average needs about 24 hours. New data every 10 minutes, with a 60-minute internal moving average. Power cycles discard the 24-hour buffer. The RadonEye RD200 manual similarly says reliable data comes in under 1 hour (versus 24–48 hours for older methods). — [Botmonster](https://botmonster.com/smart-home/diy-radon-detector-esphome-home-monitoring/); [RadonEye RD200 manual](https://manuals.online/ftlab/security-sensor/radon-eye-rd200/user-manual/1pxfd)
- Electrical: 5 V supply, about 60–65 mA. UART 9600 8N1 with 3.3 V logic, so no level shifter is needed. Operating range 10–40 °C, <90% RH. — [Botmonster](https://botmonster.com/smart-home/diy-radon-detector-esphome-home-monitoring/)
- Size is stated by the blog as 68 mm diameter × 98 mm tall. Unverified, and possibly the size of a housed unit rather than the bare module, so confirm against the FTLAB datasheet. The official RD200M datasheet (v1.3, June 2016) exists but could not be text-extracted here. — [Botmonster](https://botmonster.com/smart-home/diy-radon-detector-esphome-home-monitoring/); [RD200M datasheet (Global Sources copy)](https://p.globalsources.com/IMAGES/PDT/SPEC/110/K1157701110.pdf)
- **ESPHome:** there is no built-in RD200M driver. The cited build uses the external component `github://ekyuho/Rd200m` (`rd200m`, UART 9600). Single blog source, repo not verified. — [Botmonster](https://botmonster.com/smart-home/diy-radon-detector-esphome-home-monitoring/)
- Installation caveats: vent the enclosure and do not seal it. Place the unit on the lowest lived-in level, 50 cm–2 m above the floor, away from exterior walls, HVAC, kitchens, and bathrooms. Cross-check against a charcoal kit; agreement within about ±20% is described as normal. — [Botmonster](https://botmonster.com/smart-home/diy-radon-detector-esphome-home-monitoring/)
- Cheap MQ-series "radon" modules sold online are MOx VOC sensors and do not detect alpha particles. — [Botmonster](https://botmonster.com/smart-home/diy-radon-detector-esphome-home-monitoring/)

**Winsen ZD100 (newer module)**
- Detects alpha particles from radon decay. Range 0–20,000 Bq/m³, resolution 1 Bq/m³. Updates every 1 minute (4-hour moving average), preheat 3 minutes. — [Winsen ZD100 product page](https://www.winsen-sensor.com/product/zd100.html); [Winsen ZD100 article](https://www.winsen-sensor.com/articles/zd100-radon-detection-module.html)
- UART at 3.3 V TTL, 9600 bps. Supply 5 V ±0.1 V, ≤10 mA. 52.65 × 42.50 × 27.8 mm, about 24.85 g. Operating 5–40 °C, 15–70% RH. Free-diffusion sampling. Marketed as "maintenance-free and calibration-free". — [Winsen ZD100 product page](https://www.winsen-sensor.com/product/zd100.html)
- Accuracy, sensitivity, and price are not stated on Winsen's pages. — [Winsen ZD100 product page](https://www.winsen-sensor.com/product/zd100.html)

**Other options**
- FTLAB FRD400 is a consumer monitor, not a module: ionization pulse chamber, first values after about 30 minutes, hourly storage, 5 V adapter, app. — [RadonShop FRD400](https://www.radonshop.com/ftlab-frd400-radon-monitor)
- ESPHome has a native `radon_eye_ble` component (`radon_eye_rd200` platform) for reading the consumer RadonEye RD200 over BLE. Users note the RD200's MAC must not also be in a `ble_client:` entry, and RD200 V2 peak values need ESPHome ≥2022.12.4. — [ESPHome Radon Eye BLE](https://esphome.io/components/sensor/radon_eye_ble.html); [HA community RadonEye BLE thread](https://community.home-assistant.io/t/radoneye-ble-interface/94962?page=9)
- The consumer RadonEye RD200 (about $180, BLE) is reported to use the same sensing element as the RD200M. Airthings View Plus costs $299 (radon, CO2, PM2.5, VOC, T/RH/P), sends data to the cloud by default, and needs the Airthings gateway for local HA. Airthings Corentium Home is about $200 with no connectivity. No source found that Airthings sells its sensor as a module. — [Botmonster](https://botmonster.com/smart-home/diy-radon-detector-esphome-home-monitoring/)
- Winsen has a radon technology/selection guide. — [Winsen radon sensor guide](https://www.winsen-sensor.com/knowledge/radon-sensor.html)

### Inferences
- Unit context (standard conversions, not re-sourced this session): 1 pCi/L = 37 Bq/m³. The US EPA action level is 4 pCi/L (148 Bq/m³) and the WHO reference level is 100 Bq/m³. The RD200M's ±0.5 pCi/L floor and ±10% spec are adequate to tell "below action level" from "mitigate".
- Radon is genuinely meaningful indoors and complements the rest of the device (it correlates with ventilation, as CO2 does). It is the best "new sensor type" for health value per dollar, if the home is at risk.
- **Enclosure/PCB:** the RD200M is large and needs free air exchange, so it would likely dictate enclosure size and possibly need a separate vented chamber. The ZD100 is much smaller and lower power (≤10 mA vs 60–65 mA). It would be attractive if its accuracy were validated, but until independent data exists it is a gamble against the accuracy-first philosophy. Design the PCB with a UART header and 5 V rail so either module can be fitted.
- **BLE alternative:** if the user already owns or prefers a RadonEye RD200, the ESP32 can read it via ESPHome BLE with no added hardware. Note that ESPHome's audio docs warn BLE components cause problems alongside audio components (see Q6), so this conflicts with on-device sound measurement.
- For the brief's question "how long until first reading": about 30–60 minutes for ion-chamber devices (RD200M about 60 min, FRD400 about 30 min), with day-scale averages needed for stable values. ZD100 claims a 3-minute preheat but reports a 4-hour moving average.

### Gaps
- The official RD200M datasheet (dimensions, current, exact UART protocol) could not be text-extracted. The 68 × 98 mm figure is unverified.
- The ZD100's accuracy, price, distributor availability, and any independent evaluation were not found. Its launch date is unknown.
- The `ekyuho/Rd200m` ESPHome external component was not verified (maintenance status, compatibility with 2026 ESPHome).
- No evidence was found of other new radon modules in 2025–2026 (e.g., from Airthings, Ecosense, or RadonTec) sold for OEM/hobby integration.

---

## Q5. Ambient light (lux): which sensor for display auto-dimming and as a data point

### Takeaway
A cheap, easy win: all candidate parts (VEML7700/VEML6030, TSL2591, BH1750, LTR-390) have native ESPHome platforms over I²C. The VEML7700 (wide range, 16-bit, auto-gain in ESPHome) is the best general choice. The BH1750 is the simplest and cheapest, and the TSL2591 adds IR/full-spectrum channels. A UV sensor (LTR-390) adds little indoors. **Tier: worth adding (VEML7700 or BH1750); LTR-390 UV, skip.**

### Cited Findings
- ESPHome has a native `veml7700` platform covering both VEML7700 and VEML6030. It exposes `ambient_light` (lux) among other outputs and handles gain switching. — [ESPHome VEML7700/VEML6030](https://esphome.io/components/sensor/veml7700/)
- The VEML7700 covers roughly 0 to about 120,000 lux with 16-bit resolution (third-party review). — [atomic14 VEML7700](https://www.atomic14.com/esp32/sensors/veml7700/)
- A 2022 HA forum thread shows users once needed a custom Arduino workaround (which broke on ESP-IDF) before the native component existed. Now superseded by the native component. — [HA community VEML7700 with ESPHome](https://community.home-assistant.io/t/veml7700-with-esphome/469545)
- The ESPHome `tsl2591` platform outputs visible, infrared, full-spectrum, and calculated lux, with auto gain and an `actual_gain` sensor. — [ESPHome TSL2591](https://esphome.io/components/sensor/tsl2591/)
- The ESPHome `bh1750` platform is native over I²C. A third-party guide says the default update interval is 60 s (likely too slow for responsive dimming unless shortened). — [ESPHome BH1750](https://esphome.io/components/sensor/bh1750/); [esp32.co.uk BH1750 guide](https://esp32.co.uk/bh1750-lux-sensor-home-assistant-lighting-automation-esphome/)
- The ESPHome `ltr390` platform outputs UV index, raw UV counts, lux, and raw ambient counts, with separate gain/resolution per channel. A forum thread reported the resolution option not working (leave it at the 18-bit default); current status unknown. — [ESPHome LTR390](https://esphome.io/components/sensor/ltr390.html); [HA community LTR390 UV index](https://community.home-assistant.io/t/uv-index-with-ltr390-uv-sensor/461305/9)
- General overview of ambient light and UV sensor selection. — [applied-ee: Ambient Light & UV Sensors](https://applied-ee.github.io/embedded/docs/sensor-integration/optical-and-proximity/ambient-light-and-uv-sensors/)

### Inferences
- For a display, the sensor needs an optical window or light pipe in the 3D-printed enclosure. Opaque PLA/PETG will badly attenuate light, and calibration then becomes relative. The display's own backlight can feed back into the reading unless the sensor is shielded or placed away from the display.
- Lux data is meaningful (circadian lighting, occupancy hints, "lights left on"), costs about $1–5 in parts, and adds negligible power. Worth adding.
- UV index indoors is near zero behind most window glass, so the LTR-390 is not meaningful unless the device sits outdoors or on a sunny sill.

### Gaps
- VEML7700 vs VEML6030 vs BH1750 bare-IC pricing and lifecycle status (late 2026) were not checked.
- The ams TSL2591 lifecycle status was not checked.

---

## Q6. Sound / noise level: I2S MEMS microphones, dBA in ESPHome, privacy

### Takeaway
Feasible but more involved than it looks. ESPHome's native `sound_level` sensor (I²S mic) reports **relative dBFS** RMS and peak, with no A-weighting and no SPL calibration. Real dBA (LAeq/LAmax with A/C weighting and mic calibration) requires the community `stas-sl/esphome-sound-level-meter` external component. The go-to hobby mics are in flux: TDK lists the **ICS-43434 as EOL** and the **INMP441 as NR/ND**. Mic noise floors (about 29–33 dBA by SNR arithmetic) are at or above quiet-bedroom levels. Audio processing consumes significant ESP32 RAM/CPU, and ESPHome warns it conflicts with BLE. **Tier: optional**, a nice data point for daytime noise and events, not a precise meter. Do all processing on-device and never stream audio.

### Cited Findings
**ESPHome native `sound_level`**
- Reports average (RMS) and peak sound pressure levels over a `measurement_duration` of 50 ms–60 s (default 1 s). Values are relative dB where 0 dB is the loudest the mic can measure, so not absolute SPL. Has a `passive` mode (measures only while another component captures audio) and `sound_level.start`/`stop` actions. — [ESPHome Sound Level Sensor](https://esphome.io/components/sensor/sound_level/)
- ESPHome warns that audio components use significant RAM/CPU, that crashes are likely with many extra components, and that BLE components cause problems alongside audio components. — [ESPHome Sound Level Sensor](https://esphome.io/components/sensor/sound_level/)
- The `i2s_audio` microphone platform works only on ESP32-family chips. — [ESPHome I²S Audio Microphone](https://new.esphome.io/components/microphone/i2s_audio/)
- Users report difficulty getting `sound_level` working with an ICS-43434 on an ESP32-C6, and one INMP441 user reported that the external component worked while the built-in path did not (unverified single reports). — [HA community ICS-43434 + ESP32-C6](https://community.home-assistant.io/t/cant-get-sound-level-sensor-to-work-to-save-my-life-ics-43434-with-sparkfun-esp32-c6/941449); [HA community INMP441](https://community.home-assistant.io/t/esp32-with-inmp441-only-microphone-yaml-needed/827921)

**stas-sl/esphome-sound-level-meter (external component, for dBA)**
- Computes Leq, Lmin, Lmax, and Lpeak over configurable windows, with Z, A, or C weighting via SOS filter chains. Example sensors include LAeq and LApeak. — [stas-sl/esphome-sound-level-meter](https://github.com/stas-sl/esphome-sound-level-meter)
- Calibration converts dBFS to dB SPL through `mic_sensitivity` (e.g., -26 dB), `mic_sensitivity_ref` (94 dB), and an optional `offset`. The example includes INMP441 equalization coefficients, and `bits_shift` may be needed for left-aligned 32-bit I²S data. — [stas-sl repo](https://github.com/stas-sl/esphome-sound-level-meter)
- Tested with ESPHome 2025.9.0 on ESP32 (Arduino 3.1.3 / ESP-IDF 5.3.2). The README recommends its dev (2.0.0) branch and notes that ESPHome's official components are better for basic measurements, with this one for A/C weighting and mic EQ. Filtering costs about 204–211 ms per second of audio at 80 MHz (six SOS sections), about 67 ms at 240 MHz. No accuracy comparison against a reference meter is given. — [stas-sl repo](https://github.com/stas-sl/esphome-sound-level-meter)
- Another standalone ESP32 sound-level-meter project exists (non-ESPHome reference). — [RideMyByte ESP32-SoundLevelMeter](https://github.com/RideMyByte/ESP32-SoundLevelMeter)

**Microphones**
- TDK lists the ICS-43434 as **EOL**. Specs: SNR 65 dBA (64 dBA in some listings), AOP 120 dB SPL, sensitivity -26 dBFS ±1 dB, 60 Hz–20 kHz, I²S 24-bit, 3.5 × 2.65 × 0.98 mm bottom-port. No successor is named on the page. — [TDK ICS-43434](https://invensense.tdk.com/products/ics-43434/); [ICS-43434 datasheet v1.2](https://cdn.sparkfun.com/assets/a/9/c/9/1/DS-000069-ICS-43434-v1.2.pdf)
- TDK's catalog lists the INMP441 as NR/ND (not recommended for new design), SNR 61 dBA. A TDK forum post asking for a direct INMP441 replacement had no visible answer. — [TDK INMP441](https://invensense.tdk.com/digital/inmp441); [TDK INMP441 replacement thread](https://adm.invensense.tdk.com/inmp441-replacement)

### Inferences
- Noise-floor arithmetic (SNR is referenced to 94 dB SPL): INMP441 about 33 dBA and ICS-43434 about 29–30 dBA self-noise. Quiet bedrooms at night are often near or below that, so the sensor cannot resolve "very quiet". It does capture daytime activity, traffic, HVAC, and loud events well.
- **Part selection:** for a new SMT PCB in late 2026, avoid designing around the EOL ICS-43434 or NR/ND INMP441 without checking stock. Candidate replacements to evaluate (not researched here) include newer TDK I²S/PDM parts and Infineon/Knowles digital mics. A PDM mic works on ESP32 via the I²S peripheral in PDM mode, but whether a given ESPHome component supports PDM must be checked.
- **Privacy:** compute LAeq/LAmax on-device and publish only scalar levels. Do not enable voice assistant or audio streaming. Document this in the README and consider a hardware jumper or DNP option so builders can omit the mic.
- **Resource conflict:** sound plus BLE (e.g., the RadonEye BLE path, or BLE proxy) is explicitly called out as problematic by ESPHome. Choose one, or use an ESP32-S3 with PSRAM and test thoroughly.
- **Calibration:** without a reference SPL meter or calibrator, absolute dBA accuracy will be roughly ±2–3 dB at best (inference from the ±1 dB sensitivity tolerance plus enclosure acoustics). The 3D-printed enclosure's acoustic port design will affect frequency response.

### Gaps
- Infineon IM69D130 (PDM) and Knowles SPH0645 (I²S) specs, lifecycle, and ESPHome compatibility were not researched this session.
- TDK's recommended successor to the ICS-43434/INMP441 was not identified.
- No independent accuracy comparison of either ESPHome sound component against a Class 1/2 meter was found.
- The ESPHome version that introduced `sound_level` was not confirmed.

---

## Q7. Anything else worth considering (occupancy via mmWave, etc.)

### Takeaway
24 GHz mmWave presence radar (HLK-LD2410 for stationary presence, HLK-LD2450 for up to 3-target X/Y tracking) is natively supported in ESPHome and is a common companion to DIY air monitors. It adds occupancy context (useful for interpreting CO2 rises and automating ventilation). It is not an air-quality measurement and needs a free UART plus careful tuning. **Tier: optional.** Commercial reference: the Apollo AIR-1 uses SEN55 + DPS310 (+ optional SCD40 and MiCS-4514), and Apollo notes the DPS310 was discontinued. This is a reminder to check lifecycle status for every part in the new BOM.

### Cited Findings
- ESPHome `ld2450` supports the HLK-LD2450 presence/motion/tracking radar: up to three targets with X/Y position and speed, plus presence binary sensors. — [ESPHome LD2450](https://esphome.io/components/sensor/ld2450/)
- ESPHome `ld2410` supports the HLK-LD2410 motion/presence radar. Community guidance says LD2410/LD2412 detect stationary presence better, while the LD2450 tracks moving targets with position. Some builders run both. — [ESPHome LD2410](https://esphome.io/components/sensor/ld2410.html); [atomic14 HLK-LD2450](https://www.atomic14.com/esp32/sensors/hlk-ld2450/); [HA community LD2410 tips](https://community.home-assistant.io/t/ld2410-esphome-tips/477058?page=31)
- The LD2450 is reported as weak at static presence beyond about 2 m. Forum posts note false positives at low thresholds. — [atomic14 HLK-LD2450](https://www.atomic14.com/esp32/sensors/hlk-ld2450/); [HA community LD2410 tips](https://community.home-assistant.io/t/ld2410-esphome-tips/477058?page=35)
- A compiled list of mmWave modules exists for comparison. — [SmartHomeScene mmWave module list](https://smarthomescene.com/blog/the-ultimate-list-of-mmwave-radar-sensor-modules/)
- Apollo AIR-1: SEN55 core (PM1/2.5/4/10, VOC index, NOx index, T, RH), DPS310 pressure (some units shipped without it because the part was discontinued), optional SCD40 CO2 and MiCS-4514 gas. — [Apollo AIR-1 FAQ](https://wiki.apolloautomation.com/products/air1/faq/); [Apollo AIR-1 sensor definitions](https://wiki.apolloautomation.com/products/air1/setup/sensor-definitions/); [ESPHome devices: Apollo AIR-1](https://devices.esphome.io/devices/apollo-automation-air-1/)
- The SM300D2 "7-in-1" module has an ESPHome component (an example of cheap combo modules that bundle non-selective gas channels). — [ESPHome SM300D2](https://new.esphome.io/components/sensor/sm300d2)

### Inferences
- mmWave lets HA distinguish "CO2 rising because the room is occupied" from "ventilation failure", and can gate display brightness or the display itself. Modest value for about $3–10 of hardware. It needs one UART, competing with the radon/CO/O3 UART modules on ESP32 variants with few hardware UARTs (ESP32-S3 has 3, one usually used for logging).
- CO2-based occupancy inference (rate of rise) is free in software given the existing SCD4x. It may be "good enough" and avoids a radar entirely.
- Radar through a 3D-printed enclosure wall generally works, but metal or thick walls and the PCB ground plane in front of the antenna will degrade it. Mount it at the board edge, facing the room (general RF practice, not sourced here).
- Apollo's DPS310 experience mirrors this research's EOL findings (ICS-43434 EOL, INMP441 NR/ND, SFA30 superseded). A late-2026 BOM should be checked against lifecycle status before PCB layout.
- The AIR-1 search did not confirm that it includes an LD2410 (other Apollo products like the MSR series do). Don't cite AIR-1 as a radar example.

### Gaps
- Whether the Apollo AIR-1 includes mmWave was not confirmed. The search returned no mention of LD2410 or ENS160 for the AIR-1.
- No quantitative comparison was found of CO2-derived occupancy versus mmWave for HA automations.
- Lifecycle status of the HLK-LD2410/LD2450 modules (late 2026) was not checked.

---

## Q8. Overall recommendation tiers (summary for the report writer)

### Takeaway
**Worth adding:** HCHO (SFA40, or included via SEN68/69C), ambient light (VEML7700 or BH1750), radon (RD200M, or design for RD200M/ZD100 and validate the ZD100). **Optional:** CO (low-range electrochemical, homes with combustion sources only, clearly not an alarm), sound level (only with an external dBA component; mind mic EOL, BLE conflicts, and privacy), mmWave occupancy (LD2410/LD2450). **Skip:** dedicated ozone cells, dedicated NO2 cells (rely on the NOx index), MOx multi-gas (MiCS/MQ/SM300D2-type), and UV (LTR-390) indoors.

### Cited Findings
| Category | Best realistic part(s) | Principle | Range / accuracy (headline) | Interface / power | ESPHome | Meaningful indoors? | Tier |
|---|---|---|---|---|---|---|---|
| HCHO | Sensirion SFA40 ([catalog](https://sensirion.com/products/catalog/SFA40)); or SEN68/69C HCHO channel ([SEN69C](https://sensirion.com/products/catalog/SEN69C)) | Electrochemical | 0–2000 ppb; ±20 ppb / ±20%; ethanol <0.3%; >6 yr life ([datasheet](https://sensirion.com/media/documents/27767BDE/69D61CAE/Datasheet_SFA40.pdf)) | I²C, ~80 µA avg | Native `sfa40` ([docs](https://esphome.io/components/sensor/sfa40/)); `sen6x` formaldehyde ([docs](https://esphome.io/components/sensor/sen6x/)) | Yes: off-gassing from furniture/flooring | Worth adding |
| O3 | Winsen ZE27-O3 ([page](https://www.winsen-sensor.com/product/ze27-o3.html)); SPEC DGS2 970-400 ([datasheet](https://orwintech.com/static/pdf/970-100.pdf)) | Electrochemical | ZE27: 0–10 ppm, 10 ppb res., NO2/Cl2 cross-sens., 2 yr life | UART | None found | Rarely: indoor O3 is low | Skip |
| NO2 | SPEC DGS2 970-500 ([DigiKey](https://www.digikey.co.uk/en/products/detail/spec-sensors-a-division-of-interlink-electronics/972-500/22490693)); SGP41/SEN6x NOx index ([note](https://www.sudo.is/docs/esphome/components/sgp4x/Info_Note_NOx_Index.pdf)) | Electrochemical / MOx index | DGS kit brochure: 100 ppb res.; NOx index ±50 pts device-to-device | UART / I²C | Index: native (sgp4x/sen5x/sen6x) | Gas-stove events only | Skip dedicated cell (use NOx index) |
| CO | Winsen ZE15-CO ([page](https://www.winsen-sensor.com/product/ze15-co.html)); Figaro TGS5141 / CMM5141 ([CMM5141](https://www.figarosensor.com/product/feature/cmm5141.html)); SPEC DGS2 CO 0–20 ppm ([datasheet](https://orwintech.com/static/pdf/970-100.pdf)) | Electrochemical | ZE15: 0–500 ppm, 0.1 ppm res.; CMM5141: 0–23 ppm (tentative); TGS5141: 10+ yr life | UART (ZE15 5–12 V); analog (CMM5141) | External component (ZE07/ZE15) ([repo mirror](https://github.xiaohuzi123231346.workers.dev/Bjk8kds/esphome-winsen-co-sensor)) | Only with combustion sources | Optional (not an alarm) |
| Radon | FTLAB RD200M ([Botmonster](https://botmonster.com/smart-home/diy-radon-detector-esphome-home-monitoring/)); Winsen ZD100 ([page](https://www.winsen-sensor.com/product/zd100.html)); RadonEye RD200 via BLE ([ESPHome](https://esphome.io/components/sensor/radon_eye_ble.html)) | Pulsed ion chamber / alpha detection | RD200M: ±10% >10 pCi/L, first reading ~60 min, ~$80; ZD100: 0–20,000 Bq/m³, accuracy unstated | UART 9600, 5 V (RD200M ~60–65 mA; ZD100 ≤10 mA) | External `rd200m` component; native BLE for RD200 | Yes: a major health risk, invisible to other sensors | Worth adding (risk areas) |
| Light | VEML7700/VEML6030; BH1750; TSL2591 ([ESPHome VEML7700](https://esphome.io/components/sensor/veml7700/)) | Photodiode ALS | VEML7700 ~0–120k lux, 16-bit ([atomic14](https://www.atomic14.com/esp32/sensors/veml7700/)) | I²C, µA-level | Native | Yes: dimming and lighting context | Worth adding |
| UV | LTR-390 ([ESPHome](https://esphome.io/components/sensor/ltr390.html)) | UV photodiode | UV index + lux | I²C | Native | No (behind glass) | Skip |
| Sound | ICS-43434 (EOL) / INMP441 (NR/ND) / successor TBD ([TDK](https://invensense.tdk.com/products/ics-43434/)) | MEMS mic, I²S/PDM | SNR 61–65 dBA → ~29–33 dBA floor | I²S | Native `sound_level` (relative dBFS) ([docs](https://esphome.io/components/sensor/sound_level/)); dBA via `stas-sl` ([repo](https://github.com/stas-sl/esphome-sound-level-meter)) | Partly: daytime/events, not quiet nights | Optional |
| Occupancy | HLK-LD2410 / LD2450 ([ESPHome LD2450](https://esphome.io/components/sensor/ld2450/)) | 24 GHz mmWave | Presence, up to 3 targets with X/Y (LD2450) | UART | Native | Context for CO2 and automations | Optional |
| Multi-gas MOx | MiCS-4514/6814, MQ-x ([Apollo warning](https://wiki.apolloautomation.com/products/air1/setup/sensor-definitions/)) | MOx | Non-selective | Analog / I²C | Various | Mostly a gimmick | Skip |

### Inferences
- **UART budget is the hidden PCB constraint:** RD200M/ZD100 (UART), ZE15-CO/DGS2 (UART), ZE27-O3 (UART), and LD2410/2450 (UART) can't all fit on an ESP32 without software UART or a UART expander (e.g., SC16IS752). The recommended set (SFA40 + VEML7700 on I²C, one radon module on UART, optional radar on a second UART) fits an ESP32-S3.
- **Power budget:** the RD200M (~60–65 mA at 5 V) and any SEN6x (~80 mA) dominate. The SFA40 (80 µA) and VEML7700 are negligible.
- **Accuracy-first consistency:** only HCHO (Sensirion electrochemical), radon (ion chamber), and lux meet an "accuracy-first" bar at indoor levels. CO is accurate but usually reads about zero. O3/NO2 at hobby prices do not meet the bar.
- **Lifecycle risk:** ICS-43434 is EOL, INMP441 is NR/ND, SFA30 is superseded by SFA40, and Apollo's DPS310 was discontinued. Verify every part's lifecycle before ordering assembled PCBs.

### Gaps
- Late-2026 bare-component pricing (SFA40, ZD100, DGS2, ZE15-CO, CMM5141) was mostly not found. Only breakout/module prices are available (SparkFun SFA40 $49.95; RD200M about $80).
- No single independent study benchmarks these extended-category sensors together under indoor conditions.
