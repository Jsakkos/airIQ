# airQ v3: design

- **Date:** 2026-11-25
- **Status:** draft, awaiting owner approval. A builder-check review has been done, and the owner's answers to it are included.
- **Research behind this design:** [`reports/Air quality monitor refresh.md`](../../../reports/Air%20quality%20monitor%20refresh.md), with the supporting notes in `research_notes/Air quality monitor refresh/`

> Marked **(owner decision)**: decided by the project owner in the design conversation.
> Marked **(designer's call)**: a proposal the owner hasn't explicitly approved yet; open to change.
> Everything else follows directly from the research or the constraints.

---

## 1. Intent and why

airQ v2 (2021–22) was an ESP8266 (Wemos D1 mini) board carrying four breakout modules: SCD40/41 for CO₂, SGP40 for VOC, SPS30 for particles and BMP280 for pressure. It had one NeoPixel and a Nextion display, ran ESPHome with Home Assistant, and sat on a 121 × 65 mm through-hole PCB. The sensors were chosen for accuracy. The plan had been SMT parts, but the owner couldn't solder them reliably, so the board became a carrier for breakouts.

The project is still relevant, and v3 refreshes it. The owner wants:

- more sensor types
- a new PCB
- an e-ink screen
- a sleek, modern 3D-printed housing

Accuracy stays the first priority, and no surface-mount part is ever hand-soldered.

**Who it's for (owner decision):**
- The owner's own home: **10 units, 5 airQ and 5 airQ mini**.
- The design is published openly, and it might be sold if there's interest (unlikely). So it must be reproducible by strangers, and it shouldn't close off certification.

## 2. Goals, non-goals, anti-goals

**Goals**
1. **Accurate core readings:**
   - CO₂: SCD41-class, ±(50 ppm + 2.5 %) between 400 and 1000 ppm.
   - Particles: PM1, PM2.5, PM4 and PM10.
   - VOC and NOx: relative indices.
   - Temperature and humidity: SHT45-grade once thermally isolated.
   - Barometric pressure and ambient light.
2. **Optional formaldehyde (HCHO), airQ only (owner decision).** Added per room by plugging in an SFA40 breakout, with no board change.
3. **Two models from one PCB and one firmware base:**
   - **airQ:** desk wedge with an e-ink screen.
   - **airQ mini:** compact wedge with no screen.
4. **CO₂ and PM2.5 readable at a glance.** Not a full dashboard on the device (owner decision).
5. **Build cost under $100 per unit at 5–10 units**, preferably lower (owner decision). Targets are in §8.
6. **No SMT hand soldering.** The factory assembles all SMT parts. The builder only plugs in cables and assembles the case, plus optional through-hole parts.
7. **Local only.** ESPHome and Home Assistant, with no cloud dependency.
8. **Reproducible from the repo:**
   - KiCad source, a BOM with LCSC part numbers, and the CPL placement file.
   - ESPHome YAML.
   - SolidCraft source plus STEP and 3MF exports.
   - Build and calibration guides, and the validation results.

**Non-goals (v3)**
- Radon (owner decision).
- Ozone, NO₂ electrochemical cells, CO and sound level. The research rates them noise-level indoors, end-of-life, or not worth the cost.
- Battery operation, because the SEN66's fan draws about 90 mA continuously.
- Touch or multi-page UI on the device.
- Wall mounting. Units sit on desks and shelves (owner decision).
- Matter support, and CE/FCC certification work. The path to them stays open; see §6.3.

**Anti-goals (failure even if it "works")**
- Self-heating that skews temperature or humidity. Specifically, internal over-temperature of 5 °C or more, or readings that move when the light changes brightness.
- A light that can't be dimmed or switched off at night.
- An audible fan or rattle on a desk.
- Any cloud dependence.
- A design others can't rebuild. That includes parts that are unobtainable, sold only on breakouts that go out of stock, or that force JLCPCB's Standard assembly tier.
- A "maker" look: visible boards, cables or screws on the front.
- A per-unit cost over $100.

## 3. Constraints

- **Tools:**
  - KiCad 10, to be installed (`winget install KiCad.KiCad`).
  - SolidCraft 0.48 or later for the enclosure; the AI assistant can drive it directly.
  - Bambu Studio and a Bambu printer.
  - Autodesk Eagle is end-of-life (access ended 2026-06-07) and won't be used.
- **Fabrication:** JLCPCB on the **Economic assembly tier**. That means:
  - SMT parts on one side only.
  - 2–50 boards per order.
  - No V-cut panels.
  - **Every placed part must be Economic-eligible.** One Standard-only part moves the whole order to Standard and roughly doubles the fees.
- **SEN66 power:** a 3.15–3.45 V supply window, about 90 mA average with 300–350 mA pulses. The ESP32-C6 draws transmit peaks of about 350 mA.
- **Firmware:** ESPHome 2026.11 or later, ESP-IDF framework. Required components: `sen6x`, `sht4x`, `bmp581`, `veml7700`, `epaper_spi`, an addressable-LED light component, and a GPIO button.
- **Parts stock:** prices and stock were checked on 2026-11-25 at LCSC/JLCPCB and distributors, and stock changes daily.

## 4. Approaches considered

| # | Approach | Trade-offs | Verdict |
|---|---|---|---|
| **1** | **SEN66 module, cabled into a small custom KiCad board assembled by JLCPCB (Economic tier)** | One sealed airflow path. No hard-to-assemble LGA parts on the board. Under $100 for both models. Risks: SEN66 lead times of up to 17 weeks, and no independent PM validation yet. | **Chosen (owner decision)** |
| 2 | Separate sensors soldered to the board (SCD41 + SGP41 + SEN62 or SPS30 + SHT45 + BMP585) | No more accurate, since the SEN66 contains the same sensor classes. Costs the same with a SEN62 (out of stock), or over $100 with an SPS30. The SCD41 forces the Standard tier. Needs three sealed openings. | Fallback only if SEN66s can't be bought |
| 3 | Off-the-shelf modules and breakouts joined by plug-in cables (XIAO ESP32-C6 + SEN66 breakout + e-ink module) | No PCB design. But bulkier: the mini's size is unreachable. Breakouts cost more and go out of stock. Thermal layout is weak. | Rejected for the product. Allowed as a temporary firmware test rig. |
| – | "Value" build using SEN63C or STCC4 for CO₂ | Saves about $15–20 per unit, but CO₂ accuracy is ±(100 ppm + 10 %), and CO₂ is the headline number. | Rejected |

## 5. Owner decisions (summary)

| Topic | Decision |
|---|---|
| Use | Own home, 5–10 units; published openly; might be sold |
| Budget | < $100 per unit, preferably lower |
| Radon | Not included |
| Placement | Shelves and desks |
| Glance information | CO₂ and PM2.5, not a full dashboard |
| Screen model | Low **"Paper" wedge** with a 2.9″ black-and-white e-ink screen, an LED line under the screen and an orange accent dot (mockup 0, Paper style) |
| Screenless model | **"mini" wedge** with a **split two-colour light**: left half is CO₂, right half is PM2.5, each with a debossed label |
| Build approach | Approach 1 (SEN66 + custom board + JLCPCB Economic) |
| Quantity | **5 airQ + 5 airQ mini** (10 total) |
| Cost-cap accounting | The < $100 cap applies to the **production order**. The prototype round (about $60–70) is a one-off development cost outside the cap. |
| Mini size | May grow from the 66 × 46 × 36 mm mockup to **about 66 × 50 × 42 mm**, so every measurement rule is kept. Same width and look. |
| Formaldehyde | **airQ only**, in a sealed pocket with its own grille. Units fitted with it cost about $50 more; the owner accepted this as an optional extra outside the cap. |

The Paper style is matte warm-white with crisp edges, a single orange accent dot, slot vents along the lower lip, and no visible fasteners on the front.

Mockups are in `.superpowers/brainstorm/3444-1795627844/content/`:
- `form-variants.html`: style references
- `shape-variants.html`: the chosen shape is card 0
- `screenless.html`: the mini; the chosen variant is the split light

## 6. Design

### 6.1 System overview

```
            USB-C 5 V ──► ESD ──► buck 3.3 V (≥1 A) ──┬──► ESP32-C6-MINI-1 (80 MHz, Wi-Fi)
                                                      ├──► SEN66  (JST-GH cable, I²C 0x6B)
                                                      ├──► SHT45 (isolated tongue / sub-board, I²C)
                                                      ├──► BMP585 (I²C)
                                                      ├──► VEML7700 (I²C, behind front window)
                                                      ├──► Qwiic socket (optional SFA40 HCHO)
                                                      ├──► e-ink FPC + driver circuit (screen model only)
                                                      ├──► addressable LEDs → light guide → front light
                                                      └──► button (orange dot)
```

### 6.2 Sensors

| Function | Part | Notes |
|---|---|---|
| PM, CO₂, VOC/NOx index, T/RH | **Sensirion SEN66** | Separate module, cabled (1.25 mm JST GH). Lies flat in the base with its ports coupled to the shell grilles. CO₂ spec matches the SCD41. |
| Reference temperature and humidity | **SHT45-AD1B** | ±0.1 °C, ±1.0 %RH. Must sit **in the incoming air, at least 2 cm from heat sources, with milled slots and copper cleared around it.** This is the reading published as room temperature and humidity. |
| Pressure | **BMP585** (BMP581 acceptable) | Fed into the SEN66's pressure compensation in ESPHome. |
| Ambient light | **VEML7700** | Behind a small window on the front face. Drives auto-dimming of the light. |
| Formaldehyde (optional, **airQ only**) | **SFA40** breakout on a Qwiic (JST SH 4-pin) socket | Fitted only in rooms that need it (new furniture or flooring). The socket is on every board (unused in the mini). In the airQ the breakout sits in **its own sealed pocket in the sensor zone, with its own small grille to room air**, never in warm case air. |

Every SEN6x variant shares the SEN66's body, connector, I²C address and ESPHome component. So the same board and enclosure can take a SEN69C (adds HCHO, but with weaker CO₂) or a SEN62 (particles only), as long as the firmware has a substitution to select the variant.

### 6.3 Microcontroller

- **ESP32-C6-MINI-1**, a pre-certified module with an on-module antenna, so the board needs no RF design and certification stays possible later.
- **Clocked at 80 MHz** with Wi-Fi light power-save, for minimal heat. A 296 × 128 one-bit display frame is only 4.7 KB, so the S3's PSRAM isn't needed.
- **The C6 has no capacitive-touch peripheral,** so the button must be mechanical (§6.6).
- **Fallback:** if C6 stock fails, the ESP32-S3-MINI-1 is the alternative. A dual footprint is not required (designer's call).

### 6.4 Display (airQ only)

- **Panel:** 2.9″ 296 × 128 black-and-white SPI e-ink on a 24-pin 0.5 mm FPC. Candidates are the **GoodDisplay GDEY029T94** and the **Waveshare 2.9″ V2**.
- **Choosing between them:** the first prototype boards test both. Adopt whichever ESPHome's `epaper_spi` drives with clean partial refresh. ESPHome currently lists partial refresh only for the Waveshare V2.
- **Driver circuit:** the standard e-paper circuit (boost inductor, MOSFET, diodes, capacitors) is on **every** board, so there's one BOM. The mini simply leaves the FPC empty.
- **Content:** two large numbers, **CO₂ (ppm)** on the left and **PM2.5 (µg/m³)** on the right, each with a small label and unit. Nothing else by default (designer's call, to honour "not a dashboard").
- **Refresh:**
  - Partial update every about 3 minutes, or sooner when a value crosses a colour band.
  - A full refresh after every 5 partial updates.
  - No update more often than every 180 s.

### 6.5 Status light

**Colour bands** (designer's call; set as ESPHome substitutions so they're easy to change):

| | Green | Yellow | Orange | Red | Purple | Maroon |
|---|---|---|---|---|---|---|
| CO₂ (ppm) | < 800 | 800–999 | 1000–1499 | ≥ 1500 | – | – |
| PM2.5 (µg/m³) | ≤ 9.0 | ≤ 35.4 | ≤ 55.4 | ≤ 125.4 | ≤ 225.4 | > 225.4 |

The PM2.5 bands are the US EPA's 2024 AQI breakpoints. The 2021 firmware used the older 12/35/55/150/250 bands.

**airQ:** a thin LED line under the screen showing the **worse** of the two bands.

**airQ mini:** a light band split in two. The **left half shows the CO₂ band and the right half shows the PM2.5 band**, with "CO₂" and "PM2.5" debossed under each half. Each half needs at least one LED, and the halves must not bleed into each other.

**Brightness (both models):**
- Auto-dims from the VEML7700 reading.
- Capped well below maximum by default.
- Home Assistant exposes an on/off switch and a "night mode" so bedrooms can go dark.

**LEDs sit on the main board.** Printed or clear light guides carry the light to the front slot(s).

**Thermal rule:** switching the light between off and its cap must not shift the compensated temperature by more than 0.2 °C (see §7).

### 6.6 Controls

There is one mechanical button at the orange dot on both models, for example a printed flexure pressing a tactile switch. The mechanism is the builder's choice.

| Action | Function |
|---|---|
| Short press | Toggle the light on/off |
| Long press (≥ 5 s) | Start CO₂ forced recalibration (meant to be done outdoors, 420 ppm), confirmed by a light pattern |
| Very long press (≥ 15 s) | Reboot into the Wi-Fi fallback access point |

(Designer's call.)

### 6.7 Power

- **USB-C, 5 V sink only:** CC pull-downs, ESD protection on the connector.
- **3.3 V from a synchronous buck rated for at least 1 A.** No linear regulator, because of the heat.
- No battery.
- The USB power supply isn't part of the bill of materials.

### 6.8 PCB

- **One 2-layer board design serves both models.** Its outline is dictated by the **mini enclosure**, which is the tighter fit (interior about 62 × 46 × 38 mm at the agreed 66 × 50 × 42 mm outside size, narrowing under the sloped front).
- **All SMT parts on the top side.** Every placed part must be Economic-eligible, checked in JLCPCB's BOM tool **before routing**. Prefer in-stock Basic and Preferred parts, and reuse the same passive values.
- **Plug-in connections:**
  - SEN66: JST GH
  - e-ink: 24-pin FPC
  - Qwiic: JST SH
  - USB-C
  - an unpopulated header for programming and debug
  - an optional unpopulated UART header for a future mmWave presence sensor (designer's call)
- **Thermal layout:**
  - The ESP32 module and the buck converter go at the top/rear edge.
  - The SHT45 goes at the intake end (§6.2). It can be on the main board or on a small sub-board joined by a short cable, whichever the geometry allows (§9).
  - Copper is cleared around the SHT45, with milled slots isolating it.
- **Antenna:** the ESP32-C6 antenna overhangs, or sits at, a board edge with Espressif's keep-out, away from the SEN66 and the e-ink panel.
- **Exports:** the 3D STEP export (`kicad-cli pcb export step`) feeds the SolidCraft enclosure model.

### 6.9 Enclosures (Paper style)

| | airQ | airQ mini |
|---|---|---|
| Outside size (W × D × H) | 95 × 55 × 48 mm | **about 66 × 50 × 42 mm** (owner decision; the mockup was 66 × 46 × 36) |
| Front face | Tilted about 30° back from vertical; screen window plus LED line plus orange dot | Tilted about 24° back; split light band plus labels plus orange dot plus light-sensor window |
| Approximate volume | ~190 cm³ | ~115 cm³ (about 40 % smaller) |
| Formaldehyde pocket | Yes: a sealed pocket with its own grille in the sensor zone (§6.2) | No |

The airQ's size is the mockup target. The mini's size is the agreed maximum envelope. The builder may adjust either by a few millimetres to fit the real parts, but must not loosen the air and heat rules below to make the mini smaller. The proportions and the look are what matter.

**Air and heat, from Sensirion's guidance (both models):**
- **Sensor zone low, electronics zone high,** separated by an internal wall. The SEN66 lies flat, with its openings never facing straight up or down.
- **SEN66 sealing:** its inlet(s) and outlet are each sealed (foam or TPU gasket) to their own grille and sealed from each other and from the case interior.
- **Grille positions:** intake grille in the lower front lip, outlet grille at the lower rear behind a baffle, and electronics exhaust in the upper rear.
- **Grille size:** each grille's open area is at least 2× the port it serves, until Sensirion's exact figure is confirmed.
- **Height off the desk:** no opening's lower edge is less than 10 mm above the desk, counting the feet.
- **Mounting:** the SEN66 sits firmly on thin foam, not wrapped, to avoid fan buzz.

**Material and printing:**
- **Plastic:** ASA if the printer is enclosed, PETG if not (designer's call). Air new prints for several days before trusting VOC readings.
- **Front finish:** print face down on textured PEI for a matte, moulded-looking front. Use chamfers rather than fillets on plate edges, and 45° louvres or vertical slots about 1.2 mm wide so grilles need no supports.
- **Fastening:** heat-set inserts entered from underneath, with felt feet hiding the screws, so nothing shows on the front or sides. Snap fits are acceptable instead.
- **Clearances:** start at 0.1–0.15 mm for alignment, 0.15–0.2 mm for removable parts and 0.2–0.3 mm for snap arms. Print test coupons first.

**CAD workflow:**
1. Import the KiCad STEP into SolidCraft.
2. Build a parametric enclosure: wall thickness, gasket thickness and clearances are parameters, and both models are parametric variants of one design wherever possible.
3. Export 3MF to Bambu Studio and STEP for the repo.

### 6.10 Firmware (ESPHome)

- **Structure:** a shared package (sensors, light logic, button, Home Assistant API, OTA) plus two thin device files, `airq.yaml` (with display) and `airq-mini.yaml` (no display). Substitutions cover device name, SEN6x variant, colour bands and brightness cap.
- **Platform:** ESP32-C6, ESP-IDF, `cpu_frequency: 80MHz`, Wi-Fi `power_save_mode: LIGHT`, Home Assistant API with encryption, OTA, and a fallback access point. No Bluetooth proxy.
- **`sen6x`:**
  - the new `voc_index` / `nox_index` keys
  - pressure compensation from the BMP585
  - temperature compensation and Sensirion's "Light (IAQM)" acceleration preset (T1=100, T2=300, K=20, P=20), tuned during validation
- **CO₂ calibration:** automatic self-calibration is on by default, with a Home Assistant switch to turn it off in rooms that rarely ventilate, plus the forced-recalibration button.
- **Readings published to Home Assistant:**
  - temperature and humidity from the SHT45
  - CO₂, PM1, PM2.5, PM4 and PM10, and the VOC and NOx indices, from the SEN66
  - pressure and illuminance
  - HCHO when an SFA40 is present
- **Index labelling:** VOC and NOx are always labelled as relative indices (VOC 1–500, baseline 100), never as ppb.
- **v2 compatibility:** keep the v2 `name:` conventions where practical, so existing Home Assistant dashboards are easy to migrate.

### 6.11 Validation (acceptance criteria, published in the repo)

| Test | Pass |
|---|---|
| Self-heating (Sensirion method: device on a wooden plate, reference thermometer ≥ 20 cm away and not above it) | Internal over-temperature < 5 °C before compensation |
| Temperature/humidity after compensation, 24 h against a reference thermometer/hygrometer | Within ±0.5 °C and ±3 %RH |
| Light at its brightness cap vs off | Compensated temperature changes ≤ 0.2 °C |
| VOC ink-pen test (pen 10 cm away) | Rises within 30 s, recovers within 1 min |
| CO₂ outdoors (fresh air) and side by side with a v2 unit's SCD4x | Within the SCD41 spec of each other / about 420 ppm outdoors |
| PM2.5 side by side with a v2 unit's SPS30, for several days including cooking | Agreement reported (R² and bias). No hard pass mark, since there's no independent SEN6x data. |
| Fan noise | Not audible at 1 m in a quiet room, no rattle |
| Cost | BOM total < $100 per unit at the order quantity |

### 6.12 Repository layout (designer's call)

```
hardware/kicad/        KiCad 10 project, fab outputs (Gerber, BOM, CPL), STEP
enclosure/             SolidCraft sources, STEP and 3MF for airq and airq-mini
firmware/esphome/      shared package + airq.yaml + airq-mini.yaml
docs/                  build guide, calibration guide, validation results, research
legacy/v2/             the 2021–22 PCB, Nextion files and images (moved, not deleted)
```

**Licence (designer's call; the owner may choose differently):**
- Hardware and enclosure: CC-BY-SA 4.0, as AirGradient uses, which keeps OSHWA certification possible.
- Firmware YAML: MIT.

### 6.13 Build sequence

1. **Order 11 SEN66s now:** 10 units plus 1 spare. Lead times run up to 17 weeks.
2. **Order e-ink panels for evaluation:** 1–2 each of the GDEY029T94 and the Waveshare 2.9″ V2. Buy the rest of the winner later, for 5 airQ in total plus 1 spare.
3. **PCB design** in KiCad 10, with an Economic-tier eligibility check before routing.
4. **Prototype round:** fabricate 5 bare boards and have 2 assembled. Prove footprints, the e-ink panel choice, the light guides and the thermal layout. If they work, they become units 1 and 2. This round's cost is development cost, outside the per-unit cap (owner decision).
5. **Enclosure prototypes** for both models, using the real STEP and printed test coupons.
6. **Firmware bring-up.** It may start earlier on a temporary approach-3 test rig.
7. **Validation** per §6.11, with fixes.
8. **Production order:** fabricate 10, assemble 8. Together with the 2 prototypes that makes 5 airQ + 5 mini, leaving 2 bare boards as spares.
9. **Publish:** source, fab files, build and calibration guides, validation results.

## 7. Requirements summary (testable)

- Both models use the same PCB design, BOM and firmware base.
- No SMT soldering is done by the builder.
- All placed parts are JLCPCB Economic-eligible.
- CO₂ and PM2.5 can be read at a glance on both models. The mini does it by colour per metric.
- The light can be dimmed and switched off. Changing its brightness shifts the compensated temperature by ≤ 0.2 °C.
- Internal over-temperature is < 5 °C.
- No opening is lower than 10 mm above the desk.
- Fully local operation.
- Cost per unit is < $100 for both models in the production order. This excludes the one-off prototype round and the optional formaldehyde add-on.

## 8. Cost targets (from the research report; "est." lines are estimates)

**The plan is 10 units, 5 airQ + 5 mini.** The production order assembles 8 boards, so its roughly $52–55 of assembly fees spread at about $6.8 per board. The research report assumed one order of 10 at $5.41 per board.

| | airQ (screen) | airQ mini |
|---|---|---|
| **Per unit, production order (cap applies)** | **≈ $91** | **≈ $82** |
| With the optional SFA40 formaldehyde breakout | ≈ $141 (accepted as an optional extra outside the cap) | n/a |
| One-off prototype round (2 assembled, 3 bare boards) | ≈ $60–70 total, development cost outside the cap (owner decision) | |

- **What the mini saves:** about $8.3 for the panel plus a little filament. The display driver parts stay on every board.
- **Sensor and spare purchases:** 11 SEN66s (10 units + 1 spare) and 6 e-ink panels (5 + 1 spare), plus 1–2 evaluation panels of the losing candidate.
- **The SEN66 dominates the cost,** at about $47–61 each.
- **Possible cuts:**
  - an SHT40 instead of the SHT45 saves about $3.9, but weakens the temperature reference (not recommended)
  - buying the SEN66 at the low end of its price range saves about $3–5
  - ordering 10 boards instead of 5 saves about $5 per unit in fees
- **Excluded:** shipping, import duty, the USB power supply and the prototype round.

## 9. Left to the builder

- **SHT45 placement.** The tongue must sit in the intake air in **both** enclosures. In the mini the main board sits high, above the SEN66, so a short-cable sub-board (or a snap-off section of the main board) may be needed. Either is acceptable if §6.2's isolation rules are met.
- **Main-board outline and stack-up** within the mini's interior.
- **Light guides:** how the LEDs reach the slot(s), and how the mini's two halves are kept optically separate.
- **The button mechanism.**
- **Which e-ink panel** to adopt, per the §6.4 test.
- **Shell split and assembly:** where the shell divides, gasket geometry, the baffle, and insert positions.
- **Exact grille geometry** within §6.9's rules.
- **Passive values, ESD parts and buck converter choice,** within the Economic-tier constraint.
- **The exact LED part and count:** addressable, at least 1 per mini half.

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| SEN66 lead time or stock | Order first. The discrete approach-2 build is a fallback (needs the Standard tier). |
| No independent SEN6x PM validation | Co-locate with a v2 SPS30 unit and publish the comparison. |
| ESP32-C6 stock swings at LCSC | Check stock at order time. The S3-MINI is the fallback, at the cost of a layout change. |
| E-ink partial refresh unsupported or ghosting | Test both panels in the prototype round. A full refresh on every update is the fallback. |
| A part isn't Economic-eligible | Check before routing; substitute equivalents. |
| VOC baseline disturbed by off-gassing from new prints | Air the prints out, and let the VOC index re-learn before validation. |
| Mini too tight for board, SHT45 and light guides | The envelope was already enlarged to about 66 × 50 × 42 mm (owner decision). If it's still too tight, raise it with the owner, never loosen the air and heat rules. |
| Cost creep pushing a unit past $100 | The SEN66 price is the swing factor; buy at the low end of its $47–61 range. Recheck the BOM total before the production order. |
