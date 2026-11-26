# 3D-Printed Enclosure Design for an Indoor Air Quality Monitor (late-2026 view)

Scope: enclosure best practices and reference designs for a refreshed DIY monitor (SEN6x or SPS30/SEN5x with fan, CO2, T/RH, possibly HCHO, light and mic; ESP32-class MCU; e-ink or LCD; custom PCB), printed on a Bambu Lab printer and modelled in SolidCraft.

Source-handling note: several Sensirion PDFs could not be fetched directly (timeouts or 404s on sensirion.com, mouser.com and farnell.com). Text was taken from mirrors that serve the same Sensirion application notes. Where a figure came only from a search-engine snippet and not from the document itself, it is marked "unverified".

---

## 1. Measurement-correct enclosure design (PM airflow, CO2 diffusion, T/RH thermal isolation, VOC, light/mic, display)

### Takeaway
All of Sensirion's design guides give the same rules. Put the sensors in the coolest, lowest part of the device, right behind large openings in the outer shell. Seal each sensor's opening from the inside volume of the device, and keep the SEN6x/SPS30 inlet and outlet sealed from each other so exhaust air is not pulled back in. Keep T/RH and VOC sensors away from MCU, regulator and display heat by distance, PCB slots or separate PCBs, and separate air volumes. Even after all that, plan to calibrate a temperature offset in firmware.

### Cited Findings

**Fan-based PM sensor (SEN6x; the same rules apply to SEN5x/SPS30)**
- SEN6x has two air inlets and one outlet. They must not be obstructed and must be "properly coupled to ambient air". Ideally both connect directly to ambient air with no channel. If a channel is needed, keep it short, and the inlet/outlet channel widths "should never restrict the airflow" — [Sensirion SEN6x Mechanical Design & Assembly Guidelines v0.9, Dec 2024 (mirror)](https://www.laskakit.cz/user/related_files/sensirion_ps_an_sen6x_mechanical_design_and_assembly_guidelines.pdf)
- "Inlet and outlet are well insulated from each other by proper sealing." Both must be "sealed tightly from the rest of the device's volume to avoid sucking air through any parasitic channels". The module itself is not airtight, so avoid any over- or under-pressure between the ambient-coupled openings and the device interior (P_INT = P_AMB). "Any restriction of the airflow through the Sensor module will proportionally affect the count rate of particulate matter" — [SEN6x guide v0.9](https://www.laskakit.cz/user/related_files/sensirion_ps_an_sen6x_mechanical_design_and_assembly_guidelines.pdf)
- Orientation: with the inlets/outlet facing up or down, dust builds up inside and the sensor ages faster, and large particles can fall in if the openings face up. Lateral and horizontal placements are "both ok" — [SEN6x guide v0.9](https://www.laskakit.cz/user/related_files/sensirion_ps_an_sen6x_mechanical_design_and_assembly_guidelines.pdf)
- External airflow: shield the sensor from device or room airflow faster than 1 m/s, which can create a pressure drop between inlet and outlet or stop particles entering. A duct-style mount is suggested for flows above 1 m/s — [SEN6x guide v0.9](https://www.laskakit.cz/user/related_files/sensirion_ps_an_sen6x_mechanical_design_and_assembly_guidelines.pdf)
- Sunlight: direct sun adds temperature offset and gradients, speeds up aging, and light entering the inlets/outlet can affect PM readings. Use a light shade or a suitable design-in — [SEN6x guide v0.9](https://www.laskakit.cz/user/related_files/sensirion_ps_an_sen6x_mechanical_design_and_assembly_guidelines.pdf)
- Revision status: v0.9 (Dec 2024) was the first public release. v0.91 (May 2025) added a "required area in Coupling to Ambient" — [ManualsLib copy of SEN6x guide v0.91](https://www.manualslib.com/manual/3970269/Sensirion-Sen6-Series.html). A search snippet attributes "inlets 56 mm², outlet 148 mm²" to v1.01 on sensirion.com, but the document could not be fetched (404). **Unverified**: confirm against the current PDF — [Sensirion SEN6x guide v1.01 URL (404 at time of research)](https://sensirion.com/media/documents/4C2A5D87/6A70A6FF/SEN6x_Mechanical_Design_and_Assembly_Guidelines.pdf); [Sensirion application-note landing page](https://sensirion.com/resource/application_note/SEN6x_mechanical_design_assembly_guidelines)
- SPS30 guide: "Inlets should always be above outlet to avoid particles getting back from the outlet to the inlets due to gravity" (quoted from a search snippet of the PDF, which timed out on direct fetch) — [Sensirion Mechanical Design and Assembly Guidelines for SPS30 (Farnell mirror)](https://www.farnell.com/datasheets/2725182.pdf)
- The AirGradient ONE enclosure was designed so that "there is good airflow to the sensor modules, that air loops in front of the sensor modules are avoided" and so that "the risk of condensation inside the enclosure is reduced as much as possible" — [AirGradient ONE product page](https://www.airgradient.com/indoor/)
- A third-party Thingiverse enclosure for the AirGradient DIY Basic adds "a baffle to separate the PM sensor fan intake and exhaust" and "a separate enclosure to isolate the temperature sensor from the heat generating electronics" — [AirGradient DIY Basic enclosure (3dsearch index of Thingiverse model)](https://3dsearch.net/model/airgradient-diy-basic-enclosure-tv7010024)
- SEN66 combines PM, RH/T, VOC, NOx and CO2 in one module, so a separate CO2 sensor may not be needed — [Sensirion SEN66 product page](https://sensirion.com/products/catalog/SEN66)

**CO2 (SCD4x)**
- SCD4x design-in guide (v1.1, Mar 2022): its top recommendations are a large housing opening close to the sensor and a small dead volume. Seal the sensor off from air trapped in the housing, because large dead volumes "can increase response time of the sensor significantly". Bad examples include missing sealing and "a small opening far from the sensor". Poor housing or PCB designs "may cause significant deviations in CO2 and temperature readings". These points come from search snippets of the guide; the PDF did not parse — [SCD4x Design-In Guide (DFRobot mirror)](https://img.dfrobot.com.cn/wiki/5d57611a3416442fa39bffca/c87d61dea475243af819046d17ddca1c.pdf)
- SCD4x datasheet v1.5 (Jul 2023): self-heating and the surroundings affect the built-in RH/T reading, and the temperature offset "inside the customer device must be set correctly". The default offset is 4 °C and recommended values are 0–20 °C. The offset depends on measurement mode, "self-heating of close components, the ambient temperature and air flow", so determine it in the finished device, in thermal equilibrium, in the operating mode you will actually use, then save it with `persist_settings` — [Sensirion SCD4x Datasheet v1.5 (SparkFun mirror)](https://cdn.sparkfun.com/assets/9/7/5/7/0/Sensirion_SCD4x_Datasheet.pdf)
- SCD4x ASC needs exposure to ~400 ppm air weekly. The typical τ63 response time is 60 s, and the datasheet says response "depends on design-in". The package is 10.1 × 10.1 × 6.5 mm — [SCD4x Datasheet v1.5](https://cdn.sparkfun.com/assets/9/7/5/7/0/Sensirion_SCD4x_Datasheet.pdf)
- Sensirion's SFA40 guide defines dead volume as "the volume of air that must be fully exchanged before equilibrium with the target environment is reached" (search snippet) — [Sensirion SFA40 Design-In Guide](https://sensirion.com/media/documents/851ABA76/6A38E89C/DesignIn_Guide_SFA40.pdf)

**T/RH thermal isolation**
- SEN6x compensates for its own self-heating, but heat from the MCU, battery, Wi-Fi module, display and similar components adds an offset the internal algorithm "can only partially" correct. Mount the SEN6x "as far apart from any heat sources as possible" and **below** them, because convection rising from heat sources warms the sensor. Do not thermally insulate the sensor itself, or it will overheat. The compensation tuning is in a separate app note, "SEN6x – Temperature Acceleration and Compensation Instructions" (Feb 2025) — [SEN6x guide v0.9](https://www.laskakit.cz/user/related_files/sensirion_ps_an_sen6x_mechanical_design_and_assembly_guidelines.pdf)
- When combining SGP4x and SHTxx, use separate flex PCBs for each sensor to cut conduction. If that is not possible, place them as far apart as possible: "a distance of around 2 cm (~0.8 in.) and milling slits in the PCB around the SHTxx is sufficient." Separate air volumes are "beneficial and recommended". If they share a volume, mount the SHT **lower** than the SGP, since warm air rises — [Sensirion SGP4x Design-In Guide v1.0 (SparkFun mirror)](https://cdn.sparkfun.com/assets/6/c/d/d/7/GAS_SGP4x_Design-In_Guide_D1.pdf)
- SHTxx/STSxx Design Guide: heat conducts mostly through PCB metal, so use thin traces, keep enough spacing from heat sources, remove unnecessary copper around the sensor, and mill slits around it to reduce conduction — [Sensirion SHTxx/STSxx Design Guide V1.1 (Digi-Key mirror)](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/2599/HT_AN_SHTxx_STSxx_Design%20Guide_V1.1_D1.pdf); [Digi-Key HTML version](https://www.digikey.hk/htmldatasheets/production/3763624/0/0/1/sht11.html)
- The STCC4 design-in guide notes that the best ambient coupling for an SHT4x may be in a different spot than for the CO2 sensor. Its advice is to keep both "in the same local environmental conditions" — [Sensirion STCC4 Design-In Guide](https://sensirion.com/media/documents/4B786C73/68E5EE93/CD_AN_STCC4_Design-In_Guide_D1_1.pdf)
- Apollo AIR-1 (SEN55 + SCD40 + ESP32-C3, 61 × 61 × 30 mm): the default SEN55 temperature offset is 6.0 °C — [Apollo wiki: sensor definitions](https://wiki.apolloautomation.com/products/air1/setup/sensor-definitions/). A retailer page attributes the offset to ESP32-C3 heat and puts it at 2–6 °C — [The Pi Hut AIR-1 listing](https://thepihut.com/products/air-1-air-quality-sensor-for-home-assistant). Deep sleep between readings gives more accurate SEN55 T/RH and needs a much smaller offset — [Apollo AIR-1 product page](https://apolloautomation.com/products/air-1)
- Apollo also offers a "Predicted Room Temperature" entity. It blends SEN55, DPS310 and SCD40 temperatures using a provisional multiplier of 0.5357, which you tune against a reference thermometer — [Apollo wiki: predicted room temp/humidity](https://wiki.apolloautomation.com/products/air1/additional-info/predicted-room-temp-humidity/); [Apollo AIR-1 GitHub (Predicted_Room.yaml)](https://github.com/ApolloAutomation/AIR-1)
- A secondary review mentions "some concerns" about the AirGradient ONE's internal temperature compensation (secondary source, low confidence) — [Breathe Safe Air AirGradient ONE review](https://breathesafeair.com/airgradient-one-review/)

**VOC/NOx (SGP4x, also inside SEN5x/SEN6x)**
- Put the sensor close to the outer shell with a large opening, since bigger openings exchange air better. Face it toward the room, not toward the desk or wall, because those surfaces emit VOCs from paint, cleaners and polish. If facing a surface cannot be avoided, keep the opening at least ~1 cm from it — [SGP4x Design-In Guide v1.0](https://cdn.sparkfun.com/assets/6/c/d/d/7/GAS_SGP4x_Design-In_Guide_D1.pdf)
- Put the sensor in the "coldest part" of the device, because outgassing from surrounding materials rises with temperature and creates a background signal. The biggest heat sources are listed as CPU, display, Wi-Fi module and batteries. Lower in the device is better because of convection — [SGP4x Design-In Guide](https://cdn.sparkfun.com/assets/6/c/d/d/7/GAS_SGP4x_Design-In_Guide_D1.pdf)
- Recommended sealing is "a silicone or rubber sealing compressed between the housing and the PCB". If no seal is possible, minimise the housing-to-PCB gap and use a wide, short opening — [SGP4x Design-In Guide](https://cdn.sparkfun.com/assets/6/c/d/d/7/GAS_SGP4x_Design-In_Guide_D1.pdf)
- Design-in sanity check: put the device and a reference 10 cm apart with an ink pen as the VOC source between them. A good design shows a fast rise (<30 s) and fast recovery (<1 min). A coarse metal grid in front of the opening helps with ESD. No extra dust membrane is needed, but if you add one, use a large pore size — [SGP4x Design-In Guide](https://cdn.sparkfun.com/assets/6/c/d/d/7/GAS_SGP4x_Design-In_Guide_D1.pdf)

### Inferences
- **Recommended architecture: two thermal zones.**
  - Lower sensor zone: SEN6x mounted horizontally or laterally, its inlets and outlet sealed to the shell with a foam or TPU gasket. If it is not a SEN66, the CO2 sensor and an SHT4x on a slotted PCB tongue go here too, under their own openings.
  - Upper electronics zone: ESP32, buck/LDO, display driver and any LCD backlight.
  - Separate the zones with an internal printed wall, and route the ribbon or FFC through a tight slot. This follows Sensirion's "sensor below heat sources / coldest part / separate volumes" rules. The upper zone needs its own vents (top slots) so its heat leaves by convection instead of soaking down.
- **PM inlet/outlet placement.** Put the SEN6x inlets and outlet on *different* faces, or on the same face with a printed baffle or fin that extends to the shell. Exhaust leaving the outlet should not reach the intake grille: this is AirGradient's "air loops". On a wedge or tent desk unit, a side or bottom-front intake with a rear exhaust works well. Keep inlets above the outlet when mounted vertically (SPS30 rule), and never have the openings facing straight up.
- **Opening size.** Until the v1.x numbers are confirmed, make each external grille's open area clearly larger than the sensor's own inlet/outlet port area, at least 2× as a working margin. The reported 56 mm² inlet / 148 mm² outlet figures, if confirmed, set a floor. Slots ≈1.2–2 mm wide keep fingers and insects out without restricting flow. These are engineering judgment, not Sensirion numbers.
- **Display heat.** E-ink draws essentially no power between refreshes, so it is much friendlier to T/RH accuracy than a backlit LCD. With an LCD, put it in the upper zone, PWM-dim the backlight, and expect a larger, ambient-dependent offset.
- **Duty-cycle the MCU** (deep sleep or light sleep between readings) to shrink the self-heating offset. Apollo's SEN55 offset drops "much lower" in sleep mode.
- **Calibration hooks.** Expose the SEN6x temperature-offset parameters and the SCD4x `set_temperature_offset` in firmware. Calibrate against a reference thermometer after the case is finished and the device has been running for at least an hour in its final orientation.
- **Light sensor window.** Use a small through-hole fitted with a clear or diffused insert, or a light pipe to the PCB-mounted sensor, on a face that doesn't get direct sun on the PM inlet.
- **Microphone port.** Use a short, straight acoustic channel sealed to the MEMS mic with a gasket so the inside of the case does not act as a resonant cavity. Keep it away from the PM fan outlet. This is judgment; see Gaps.

### Gaps
- Could not fetch the current SEN6x guide v1.01 to confirm the required inlet/outlet areas (56/148 mm² is unverified), or the SEN6x temperature-compensation app note for its parameter values.
- The full SCD4x design-in guide PDF did not parse. Its points come from search snippets only.
- Found no Sensirion or vendor guidance specific to light-sensor windows or MEMS mic ports in AQ enclosures. Those recommendations are engineering inference.
- No quantitative AirGradient or M5Stack descriptions of vent placement were available.

---

## 2. Materials: PLA vs PETG vs ASA vs PC — heat, off-gassing, UV, finish

### Takeaway
Sensirion's own VOC-sensor guide names hard plastics such as ABS and PC as recommended near the sensor, and lists PA, POM and PMMA as not recommended. Peer-reviewed tests show that freshly FDM-printed ABS, PLA, PETG and PC all keep emitting VOCs after printing at broadly similar rates, while PVDF emits little. ASA (which AirGradient uses) or PC/ABS are the most defensible choices for heat and UV. Whatever the material, seal the VOC sensor from the case interior and let new prints air out before trusting VOC baselines.

### Cited Findings
- From the SGP4x design-in guide's material table: Recommended are "Hard plastics (e.g., ABS, PC)", PTFE/Teflon, PEEK and metals; Not recommended are PA, POM and PMMA. (Text extraction flattened the two-column table. The split shown is how the columns read; check against the PDF figure.) — [SGP4x Design-In Guide v1.0](https://cdn.sparkfun.com/assets/6/c/d/d/7/GAS_SGP4x_Design-In_Guide_D1.pdf)
- The same guide says "Electronic components, batteries, PCBs, and plastic parts of typical devices emit VOCs. They accumulate inside the device to high concentrations". Without sealing they "mask environmental VOC changes", and outgassing "increases with temperature" — [SGP4x Design-In Guide](https://cdn.sparkfun.com/assets/6/c/d/d/7/GAS_SGP4x_Design-In_Guide_D1.pdf)
- Mangin, Blanchard & Kelly (2024, *Sensors* 24(8):2610) tested FDM-printed ABS, PETG, PLA, PC and PVDF against CO, CO2, NO, NO2 and VOCs:
  - ABS, PLA, PETG and PC "still release VOCs after the printing process", with off-gassing rates of roughly 18–31 (ccm·ppb/cm² as reported).
  - PVDF "releases little to no VOCs".
  - They found no to limited interaction with CO/CO2 and a small interaction with NO/NO2.
  — [Mangin et al. 2024 (DOI)](https://doi.org/10.3390/s24082610); [PMC full text](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11053552/); [NSF PAR copy](https://par.nsf.gov/biblio/10535024)
- That paper cites Zwicker et al., who found VOC off-gassing from printed PLA increases above 75 °C (search snippet of the paper) — [Mangin et al. 2024](https://www.mdpi.com/1424-8220/24/8/2610)
- A reviewer comment on the paper notes that PLA and PETG had similar post-print VOC emission rates, unlike an earlier study that found PETG lower than PLA *during* printing — [MDPI review report](https://mdpi.com/1424-8220/24/8/2610/review_report)
- A hobbyist emissions test *during printing* found no measurable VOCs from PLA. PETG registered on one sensor at about the same order as ASA/ABS but not on a Bosch sensor, so results depended on the sensor (attribution via search summary; this concerns printing emissions, not finished parts) — [Tom's 3D: "3D printers are worse than I thought"](https://toms3d.org/2024/10/07/3d-printers-are-worse-than-i-thought-time-to-do-something-about-it/)
- SGP41 output in ESPHome is a relative 1–500 VOC index. The ppm conversion is not supported — [Printables Sensorbox v2 (3D printer emission sensor array)](https://www.printables.com/model/1079858-3d-printer-emission-sensor-array-sensorbox-v2)
- AirGradient ONE's enclosure is "ASA Plastic, UV Resistant and Weather Proof" — [AirGradient ONE product page](https://www.airgradient.com/indoor/)
- A MakerWorld enclosure project recommends PETG or ABS/ASA for printed enclosure parts and warns that PLA may warp — [MakerWorld Chamber Sentinel VOC fan mod](https://makerworld.com/en/models/1906907-chamber-sentinel-smart-voc-fan-mod-p1-x1)

### Inferences
- **Material ranking for this project:**
  - **ASA** (Bambu ASA): best mix of heat resistance, UV stability and matte finish, and it is what AirGradient ships.
  - **PC or PC-blend**: hard plastic named by Sensirion, high heat resistance; harder to print.
  - **PETG**: good heat margin, fine for indoor use, glossier, strings more.
  - **PLA/PLA Matte**: easiest and prettiest. Its low glass-transition temperature (commonly cited around 55–60 °C) makes creep near a warm regulator or in a sunny window a real risk, and it lacks the UV stability of ASA.
  - Avoid nylon (PA) or POM parts near the VOC sensor, per Sensirion's table.
- **New-print VOC skew.** Since all common FDM plastics keep off-gassing after printing and the SGP algorithm is relative, expect a raised VOC baseline for the first days in a new case.
  - Mitigations: bake or air new parts (e.g., several days in a ventilated room, or a few hours warm but well below the material's softening point); seal the SEN6x/SGP inlet to the shell so it samples room air, not case air; let the VOC index algorithm re-adapt before judging.
  - Don't use fresh silicone RTV, hot glue or solvent-based paints near the sensor.
  - No source quantified how many days this takes.
- **Gaskets.** Use pre-cured silicone or EPDM foam, or printed TPU. Sensirion explicitly suggests silicone/rubber seals. TPU's outgassing was not covered in the sources.

### Gaps
- Found no controlled study or credible report that specifically measures an SGP40/SGP41 VOC-index shift caused by a freshly printed enclosure, nor how long it lasts. Mangin et al. measured emission rates, not the SGP response.
- No data found on ASA or TPU off-gassing specifically. Mangin et al. did not test ASA.
- Did not retrieve Sensirion's "Handling and Assembly Instructions for SGPxx" document, which may list more materials.

---

## 3. "Sleek, modern" aesthetics on FDM and form-factor effects on airflow

### Takeaway
The cleanest FDM looks come from a few things. Use simple primary volumes (square puck, wedge, slab) with large consistent radii or chamfers and one accent material or colour. Make vents a deliberate graphic element, such as rows of slots or an LED-lit band, not scattered holes. Use slicer surface techniques (fuzzy skin or textured-PEI faces, careful seam placement) and hide fasteners with snap or compliant joints or magnets. Choose the form factor with airflow in mind: a desk wedge or a wall slab both work if the sensor intakes face the room and stay at least ~1 cm off the surface they sit against.

### Cited Findings
- AirGradient ONE: 130 × 130 × 35 mm square slab. Eleven RGB LEDs "shine through the enclosure" as a status bar (configurable colour bands for CO2 or PM; can be turned off). It wall-mounts with screw spacing that fits EU/US junction boxes, or stands on a desk with optional clip-on stands, and cables can enter from the top or bottom — [AirGradient ONE product page](https://www.airgradient.com/indoor/)
- M5Stack AirQ (SEN55 + SCD40 + 1.54" 200×200 e-ink, ESP32-S3 StampS3): 72 × 56 × 24.1 mm. The base has LEGO-compatible holes, a magnetic base and removable mounting lugs, so it can be mounted several ways — [M5Stack AirQ docs](https://docs.m5stack.com/en/core/AirQ); [Mouser India product page](https://www.mouser.in/en/new/m5stack/m5stack-air-quality-kits/); [Digitec listing (dimensions)](https://www.digitec.ch/en/s1/product/m5stack-air-quality-kit-scd40-and-sen55-development-boards-kits-43301100)
- Apollo AIR-1: 61 × 61 × 30 mm. The README says "we have focused on efficient heat management within this small package", with a "thoughtful PCB layout and case design, incorporating ventilation and strategic component placement" — [Apollo AIR-1 GitHub](https://github.com/ApolloAutomation/AIR-1)
- Bitclock (Printables) is an e-ink desk companion and AQ-monitor enclosure where "no screws, everything snaps together using a compliant mechanism" (search snippet; the page returned 403 to direct fetch) — [Printables Bitclock](https://www.printables.com/model/965358-bitclock-an-e-ink-desk-companion)
- Desk and wall surfaces emit VOCs, so face the sensor toward the room. If it must face a surface, keep the opening ≥ ~1 cm away — [SGP4x Design-In Guide](https://cdn.sparkfun.com/assets/6/c/d/d/7/GAS_SGP4x_Design-In_Guide_D1.pdf)
- Fuzzy skin roughens perimeters to hide layer lines and seams. Bambu Studio and PrusaSlicer can apply it through a modifier to only some faces. It changes wall dimensions, so it affects fits — [Snapmaker fuzzy-skin guide](https://www.snapmaker.com/blog/fuzzy-skin-3d-print/); [All3DP: Orca Slicer fuzzy skin](https://all3dp.com/2/orca-slicer-fuzzy-skin-simply-explained/)
- To mimic a textured-PEI finish, a Bambu forum user suggests very light fuzzy skin (≈0.07 mm thickness, 0.4 mm point distance). Snapmaker suggests ≈0.1 mm for both as a subtle matte baseline (via search summary) — [Bambu Lab forum: "no ringing, no seams, no visible layers"](https://forum.bambulab.com/t/tip-no-ringing-no-seams-no-visible-layers-homogeneous-color/27731); [Snapmaker](https://blog.snapmaker.com/blog/fuzzy-skin-3d-print/)
- Hackaday article on design techniques to hide layer lines in printed parts — [Hackaday, 2024-03-04](https://hackaday.com/2024/03/04/design-tips-to-hide-layer-lines-in-3d-printed-parts)
- Fuzzy skin can also be applied to top surfaces in newer slicer builds — [Hackster.io news](https://www.hackster.io/news/you-can-now-add-fuzzy-skin-to-the-top-surfaces-of-your-3d-prints-fdb0aa1df178)

### Inferences
- **Design language to borrow (from general product knowledge, not researched sources):**
  - Aranet4: flat slab with a big e-ink panel flush in a matte bezel, one small status cue.
  - Awair Element: fabric or wood-like front with a dot-matrix display behind it.
  - Qingping: white Apple-like squircles with a front display.
  - HomePod mini / Nest: soft volumes with a uniform texture where the vents disappear into a pattern.
  - Dieter Rams (Braun): rows of identical slots as graphic grilles, one accent colour, honest proportions.
- **FDM recipes for these looks:**
  - Print the front face *down* on the Bambu textured PEI plate. You get a uniform matte, injection-moulded-looking face with no layer lines.
  - Make the display window a pocket in that face.
  - Use ≥3 mm chamfers on the build-plate edges (fillets overhang badly there) and large vertical-edge fillets elsewhere.
  - Put vent slots on the side walls as vertical slots or 45° louvers. These print without supports and read as a "Braun grille".
  - Use the AMS for a contrasting band or a translucent white "light pipe" strip lit by the PCB's RGB LED (the AirGradient LED-bar effect).
  - Add felt or silicone feet, and a keyhole slot or magnets for wall mounting.
- **Form factor vs airflow:**
  - **Wedge/tent desk unit**: tilts the display toward the user and naturally creates a lower front intake and an upper rear exhaust. This is the best match for "sensors low, heat high".
  - **Wall slab** (AirGradient style): needs side intakes and stand-offs or a spacer so the rear vents don't face the wall within 1 cm.
  - **Cylinder/puck** (HomePod style): looks great, but puts the MCU and display close to the sensors. Use a stacked design with the sensor deck at the bottom, intake around the lower perimeter, and exhaust through the top grille.
- Avoid putting the PM inlet on the underside of a puck that sits on a desk: dust, and it risks surface-VOC bias.

### Gaps
- Did not retrieve primary teardown or design write-ups for Aranet4, Awair Element, Qingping or HomePod mini industrial design. Those comparisons are general knowledge, not cited.
- No source quantified the airflow trade-offs between desk-wedge, wall and puck enclosures.

---

## 4. Reference designs (gallery with links and critique)

### Takeaway
The commercial open designs (AirGradient ONE, Apollo AIR-1, M5Stack AirQ) show the core trade-off between compact size and self-heating. There is now a healthy set of SEN66 + ESP32 + e-paper hobby enclosures on MakerWorld, Printables and GitHub that can serve as starting points, but few of them document airflow or thermal validation.

### Cited Findings

**Commercial / semi-open products**
- **AirGradient ONE.** ASA, 130 × 130 × 35 mm, 1.3" OLED, LED bar through the enclosure, wall or desk mounting. Designed for airflow and to avoid air loops and condensation. Code, schematics and 3D files are open source (CC-BY-SA 4.0) — [AirGradient ONE](https://www.airgradient.com/indoor/). Reviews note it is well ventilated with most holes at the top and bottom, while one reviewer wondered whether the roomy internal layout was intentional (via search summary) — [CNX Software review](https://cnx-software.com/2023/11/29/airgradient-one-kit-review-an-open-source-indoor-air-quality-monitor); [Lester Chan review](https://lesterchan.net/blog/2025/10/20/airgradient-one-indoor-monitor-i-9psl-review/)
- **Apollo AIR-1.** 61 × 61 × 30 mm, SEN55 + SCD40 + DPS310 + ESP32-C3. Compact, but it needs a SEN55 temperature offset of up to ~6 °C and a modelled "predicted room temperature". Case files are on Printables — [Apollo AIR-1 GitHub](https://github.com/ApolloAutomation/AIR-1); [Printables AIR-1 case model 932001](https://www.printables.com/model/932001-apollo-automation-air-1-air-quality-sensor-for-hom); [Apollo wiki](https://wiki.apolloautomation.com/products/air1/setup/sensor-definitions/)
- **M5Stack AirQ (K131 / Air Quality Kit v1.1).** SEN55 + SCD40 + 1.54" e-ink + ESP32-S3, 72 × 56 × 24.1 mm. Battery and RTC sleep; magnetic base and LEGO holes — [M5Stack docs](https://docs.m5stack.com/en/core/AirQ); [CNX Software: Air Quality Kit v1.1](https://www.cnx-software.com/2025/09/14/m5stack-air-quality-kit-v1-1-features-sensirion-sen55-environmental-sensor-and-scd40-co2-sensor/)

**SEN66 / SEN6x hobby designs**
- **MakerWorld "Air Quality Monitor – SEN66 + ESP32-C6" (logicbz).** Compact two-piece enclosure for SEN6x (incl. SEN66) and XIAO ESP32-C6, no display — [MakerWorld 2649511](https://makerworld.com/en/models/2649511-air-quality-monitor-sen66-esp32-c6)
- **MakerWorld "AirRing".** Desk AQ meter with SEN66 and a Waveshare ESP32-S3 Touch AMOLED. Source in GitHub socquique/Monitor-SEN66 — [MakerWorld 3199590](https://makerworld.com/en/models/3199590-airring-air-quality-monitor-mqtt)
- **MarioHP Air-quality-monitor.** SEN66-SIN-T based; MakerWorld model plus GitHub docs — [GitHub MarioHP/Air-quality-monitor](https://github.com/MarioHP/Air-quality-monitor); [MakerWorld 1540218](https://makerworld.com/en/models/1540218-air-quality-monitor)
- **Printables "ESPHome Sen66 Air Quality Sensor" (bitr0t).** Housing for SEN66/SEN6x, any XIAO ESP32, a **40 mm fan** and a USB-C breakout — [Printables 1616151](https://www.printables.com/model/1616151-esphome-sen66-air-quality-sensor)
- **airInk (GitHub).** SEN66 + XIAO ESP32-C3 + 1.54" B/W e-paper in a horizontal layout, ESPHome, with periodic full refresh against ghosting — [GitHub Sirofjelly/airInk](https://github.com/Sirofjelly/airInk)
- **FeatureNAB air-sensor.** ESP32 + SEN66 + ESPHome — [GitHub FeatureNAB/air-sensor](https://github.com/FeatureNAB/air-sensor)
- **Medium build log (e-ink AQ monitor).** E-paper stacked directly on top of the SEN66 with the ESP32-C3 sandwiched in between, held by 4 × M2.5 screws from the front; ~US$57 in parts — [Medium: Building an E-Ink Air Quality Monitor](https://medium.com/@monkeytypewritr/building-an-e-ink-air-quality-monitor-w-home-assistant-integration-b9a5602e2e7b)
- **Project Aura (hackaday.io).** SEN66 + optional SFA30 (HCHO), Waveshare ESP32-S3-Touch-LCD-4.3 (800×480). Enclosure STLs come through a MakerWorld crowdfunding campaign; ~US$170–200 build — [hackaday.io Project Aura](https://hackaday.io/project/204993-project-aura-open-source-esp32-air-quality)
- A Thingiverse design by "3dPrintPerson1" pairs a SEN66 with Seeed's XIAO ePaper Display Board (2.13" mono), CC-BY-SA (from search summary; no direct URL retrieved) — [Yeggi "sen66" index](https://www.yeggi.com/q/sen66/)

**SEN5x / SPS30 / older designs**
- **MakerWorld "SEN55 Air Quality Sensor Case" (Syvel Engineering).** For SEN55/54/50, with ESPHome YAML and BOM — [MakerWorld 893126](https://makerworld.com/en/models/893126-sen55-air-quality-sensor-case). A remix adds an SCD41; one commenter found the fit difficult — [MakerWorld 1037899](https://makerworld.com/en/models/1037899-sen55-scd41-air-quality-sensor-case)
- **MakerWorld "Air Quality Sensor (SEN5x + ESP32)"** — [MakerWorld 437005](https://makerworld.com/pt/models/437005-air-quality-sensor-sen5x-sensor-esp32)
- **Printables "Environmental sensor SEN5x" (Lupilpl).** Sensor mount that needs supports — [Printables 751198](https://www.printables.com/model/751198-environmental-sensor-sen5x)
- **Printables "Air Quality box" (ArcherNE).** SEN55 + D1 Mini + SenseAir S8 + OLED — [Printables 234659](https://www.printables.com/model/234659-air-quality-box)
- **Printables "Air Quality Sensor" (GiorgioFoX)** — [Printables 1175028](https://www.printables.com/model/1175028-air-quality-sensor)
- **hackaday.io "Air Quality Station".** ESP32-S2 + 3.7" e-paper + SCD40 + PMS5003, Thingiverse enclosure — [hackaday.io 205888](https://hackaday.io/project/205888-air-quality-station)
- **uELKO ESPHome-Air-Quality-Monitor.** ESP32-S3 + 2.13" e-ink HAT; three-part printable housing — [GitHub uELKO](https://github.com/uELKO/ESPHome-Air-Quality-Monitor)
- **Adafruit "No-Code IAQ Monitor with Separate Display".** Optional 3D-printed parts; physically separating display from sensors is a useful pattern — [Adafruit Learn](https://learn.adafruit.com/no-code-indoor-air-quality-monitor-with-separate-display/3d-prints-and-assembly-optional)
- **AirGradient DIY Basic enclosure (Thingiverse).** Example of a PM intake/exhaust baffle plus an isolated T/RH compartment — [3dsearch index](https://3dsearch.net/model/airgradient-diy-basic-enclosure-tv7010024)
- **Printables tag listing** for more AQ sensor enclosures — [Printables #airqualitysensor](https://www.printables.com/tag/airqualitysensor)

### Inferences
- **Good patterns to copy:**
  - AirGradient: light bar through the case, junction-box mounting, ASA, explicit anti-loop airflow goal.
  - Apollo: honest documentation of the self-heating offset and a model-based correction.
  - M5Stack: e-ink, magnetic and LEGO mounting, sleep-driven low heat.
  - Bitclock: screwless compliant snaps.
  - The Thingiverse AirGradient remix: baffle plus a separate T/RH chamber.
- **Bad patterns to avoid:**
  - Stacking MCU and display directly on top of the SEN66 (Medium build). This puts heat right above the sensor; Sensirion says sensor-below-heat is better, but direct conduction and a shared air volume still bias T/RH and VOC.
  - Ultra-compact cubes (AIR-1 size) that force multi-degree offsets.
  - Adding a strong case fan (bitr0t's 40 mm fan). It can help flush heat, but must not blow >1 m/s across the SEN6x openings or pressurise one side of the sensor.
- None of the hobby designs found document a reference-thermometer comparison or an SGP "ink-pen" response test. That gap is an opportunity for this project to stand out.

### Gaps
- MakerWorld and Printables pages mostly blocked direct fetching (403). Design details for those models come from search snippets/metadata, not full page reads. Licences, print settings and photos were not checked.
- Could not find an "industrial-design standout" Hackaday *blog* article specifically on an AQ monitor enclosure.
- Did not confirm the exact GitHub path for the AirGradient ONE enclosure CAD files. The product page only says the 3D files are open source.

---

## 5. Design-for-printing details (Bambu): tolerances, walls, orientation, grilles, display windows, assembly

### Takeaway
Start from published Bambu-class clearance values: ~0.1–0.15 mm for alignment fits, 0.15–0.2 mm for removable parts, 0.2–0.3 mm around snap arms. Print test coupons first, and leave fuzzy skin off mating surfaces. Most of the "premium" look comes from orientation (show face on the textured plate) and from features that print without supports (chamfers, vertical slots, 45° louvers).

### Cited Findings
- Tolerance starting points from a Bambu H2D Pro makerspace guide: 0–0.05 mm for press fits, 0.1–0.15 mm for alignment pegs/holes, 0.15–0.2 mm for removable parts and hinges, ≥0.2 mm for free movement. Material, orientation, first-layer squish, wall thickness and geometry all change the fit, so print a test sample — [UAL CCI Digital Fabrication Lab wiki: Design the clearance and tolerance](https://wiki.cci.arts.ac.uk/books/digital-fabrication-lab/page/design-the-clearance-and-tolerance)
- Snap fits: leave 0.2–0.3 mm clearance around the snap arm so it flexes without rubbing. PLA is brittle, so avoid extreme interference — [Zbotic: 3D printing tolerances for press fits, threads and snap fits](https://zbotic.in/3d-printing-tolerances-designing-gaps-for-press-fits-threads-and-snap-fits/)
- Additional tolerance guidance for Prusa MK4/XL-class printers — [UF Libraries makerspace guide](https://makerspace.uflib.ufl.edu/services/3dprocess/recommended-software-for-3d-printing/designing-for-3d-printing-tolerances-on-the-mk4-and-xl/); [Formlabs tolerances blog (general)](https://formlabs.com/global/blog/3D-printing-tolerances-for-engineering-fit/)
- Fuzzy skin adds wall thickness and changes fits, and it can be limited to selected faces with modifiers (via search summary) — [Snapmaker](https://www.snapmaker.com/blog/fuzzy-skin-3d-print/); [All3DP](https://all3dp.com/2/orca-slicer-fuzzy-skin-simply-explained/)
- Sensirion's SEN6x example uses a snap-in fixture for the sensor; its figure marks the inlet, outlet and connector areas that must stay unobstructed — [SEN6x guide v0.9 §3, Figs 10–11](https://www.laskakit.cz/user/related_files/sensirion_ps_an_sen6x_mechanical_design_and_assembly_guidelines.pdf)

### Inferences (engineering practice; not individually sourced)
- **Walls:** 2.0–2.4 mm shells (5–6 perimeters at 0.4 mm), 1.2 mm minimum for thin internal baffles and light-pipe walls. Add ribs instead of thicker walls on large flat panels to avoid sink and warp, which matters especially with ASA.
- **Orientation:**
  - Front/display face down on textured PEI.
  - If the display face can't be down, put the Z-seam on a rear inside corner (Bambu Studio "Back" or painted seam) and use fuzzy skin on the visible side walls only.
  - Use ironing only on large top surfaces that are visible.
  - Split the housing into a front shell and a rear/base so each visible face can print flat.
- **Grilles without supports:**
  - Vertical slots on side walls, ≥1.2 mm wide with ≥1.2 mm bars.
  - Horizontal louvers at ≥45°.
  - Hex or Voronoi patterns only on surfaces that print flat on the plate.
  - Avoid horizontal round holes larger than ~5 mm on walls without a teardrop or diamond top.
- **Display windows** (best to worst for looks):
  1. Open bezel pocket printed face-down, with a 0.6–1.0 mm lip overlapping the e-ink panel's inactive border and the panel held from behind by a printed clamp plus foam.
  2. A laser-cut or thin clear acrylic/PC window glued into a recess (cleanest for LCDs and touch panels).
  3. A 1–2 layer "skin" in clear or white PETG over a status LED or light sensor only. It is too hazy for a readable display.
  
  E-ink panels are fragile: avoid point loads on the glass edge and leave ~0.2–0.3 mm clearance around the panel outline.
- **Fasteners:**
  - Heat-set M2/M2.5/M3 inserts in the rear shell with screws entering from the back or underside (invisible from the front).
  - Or compliant snap hooks (Bitclock-style) for the front shell.
  - Magnets (6×2 mm press-fit) for a detachable wall plate or desk stand.
  - Felt or silicone bumpers underneath, and a keyhole slot for wall mounting.
- **Assembly sequence:**
  1. SEN6x into its snap or foam cradle with the inlet/outlet gaskets on the lower shell.
  2. PCB (with the T/RH tongue and CO2 near their openings) onto standoffs.
  3. Fit the internal thermal wall.
  4. Display into the front bezel with its FFC through the wall slot.
  5. Close with the rear screws.
  6. Run the ink-pen VOC test and a 1–2 h reference-thermometer soak to set the offsets.
- **Prototyping:** use the SolidCraft parametric model with gasket thickness, clearance and wall thickness as parameters, so test coupons (snap arm, display pocket, gasket compression) can be regenerated quickly.

### Gaps
- Found no official Bambu Lab wiki page with recommended enclosure clearances. The values above come from a university makerspace and a third-party guide.
- No sources found specifically on printed light pipes or on clear-PETG thin-skin display windows for e-ink.

---

## 6. Fan noise and vibration isolation for PM sensor fans

### Takeaway
Sensirion PM modules are quiet by design (SPS30 ≤ 25 dB(A) at 0.2 m), so most perceived noise comes from the enclosure: loose mounting, panel resonance and grille whistle. Sensirion recommends a firm fixture combined with flexible foam decoupling, plus optional acoustic foam or thin rubber, while keeping the module not thermally insulated.

### Cited Findings
- SEN6x assembly guidance: "To avoid any resonances building up in the housing structure, we recommend a firm mechanical fixture with a flexible foam decoupling to avoid any structural borne sound." "Acoustic foam or thin rubber can be used to further reduce noise." The module's own acoustic emission always meets the datasheet; foam addresses noise from "mechanical coupling between the sensor and the housing". The sensor "should not be thermally insulated to avoid overheating" — [SEN6x guide v0.9 §3](https://www.laskakit.cz/user/related_files/sensirion_ps_an_sen6x_mechanical_design_and_assembly_guidelines.pdf)
- SPS30: acoustic emission level 25 dB(A) at 0.2 m, with long-term acoustic drift ≤ +0.5 dB(A)/year (via search summary of the datasheet) — [Sensirion SPS30 datasheet (SparkFun mirror)](https://cdn.sparkfun.com/assets/4/e/e/f/8/Sensirion_PM_Sensors_Datasheet_SPS30.pdf); [Sensirion SPS30 datasheet](https://sensirion.com/file/datasheet_sps30)

### Inferences
- Mount the SEN6x in a printed cradle or snap fixture that holds it firmly, with 1–2 mm closed-cell foam (EPDM/PU) or a TPU pad between the module and the shell. The same foam can double as the inlet/outlet gasket.
- Don't wrap the whole module in foam (thermal warning).
- Stiffen large flat panels next to the sensor with ribs or curvature to avoid drumming.
- Avoid narrow slots directly in the fan outlet jet, which can whistle.
- In firmware, SEN6x/SPS30 fan-cleaning cycles produce brief louder bursts; schedule them for daytime.
- An additional enclosure fan (as in bitr0t's design) adds more noise than the sensor itself. Choose a low-RPM fan, PWM it, and keep its flow away from the SEN6x openings (1 m/s rule).

### Gaps
- No published SEN66/SEN6x acoustic dB(A) figure was found in this session; check the current SEN6x datasheet.
- No hobbyist measurements were found comparing enclosure designs for PM-fan noise.
