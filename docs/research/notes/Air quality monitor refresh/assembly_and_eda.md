# PCB Assembly Options and EDA Software for the Air Quality Monitor Refresh (as of late Nov 2026)

Scope: (A) how to get a ~40-60 part, ~5-board run of a 2-layer ESP32 + Sensirion board assembled, given the user previously failed at hand-soldering SMT; (B) which EDA tool works best with an AI coding assistant (Claude Code) that generates and edits files and produces fab outputs.

Research date: 2026-11-25. All prices are approximate, USD unless noted, exclude shipping/tariffs, and move with exchange rates. Re-quote before ordering.

---

## A1. Fully factory-assembled SMT: JLCPCB PCBA (Economic vs Standard) and alternatives

### Takeaway
JLCPCB is still the cheapest turnkey option for a 5-board hobby run. Economic PCBA has an $8.18 setup fee plus $3.07 per unique Extended part. Standard PCBA costs $25.56 setup (single-sided) plus $1.53 per unique part plus fixtures. The SCD41 is a Standard-only part, so putting it directly on the board pushes the whole order into Standard. Western assemblers (Aisler, Eurocircuits, MacroFab) cost several times more for prototypes. PCBWay advertises a $29 promo for 1-20 pcs, but I could not confirm its terms.

### Cited Findings
**JLCPCB fee schedule (help page "Last updated on Oct 22, 2026"):**
- Setup fee: Economic $8.18; Standard $25.56 single-side / $51.12 double-side — [JLCPCB: PCB Assembly Price](https://jlcpcb.com/help/article/pcb-assembly-price)
- Stencil: Economic $1.53; Standard $8.21 single-side / $16.42 double-side — [JLCPCB: PCB Assembly Price](https://jlcpcb.com/help/article/pcb-assembly-price)
- SMT assembly: $0.0016 per joint (both tiers at low volume) — [JLCPCB: PCB Assembly Price](https://jlcpcb.com/help/article/pcb-assembly-price)
- Manual (through-hole) assembly: $0.0164 per joint (1-10,000 joints) plus $3.58 hand-soldering labor per order, same on both tiers — [JLCPCB: PCB Assembly Price](https://jlcpcb.com/help/article/pcb-assembly-price)
- Feeder loading: Economic $3.07 per unique Extended part; Standard $1.53 per unique part (Basic or Extended) — [JLCPCB: PCB Assembly Price](https://jlcpcb.com/help/article/pcb-assembly-price)
- Standard-only extras: fixtures for rigid PCB at $8.21 each, 2 fixtures for 1-29 pcs; packing $0.50 + $0.00003/cm²; stencil/fixture storage $4.93 each. The handling fee works as a floor: if a design also qualifies for Economic, the Standard total must be at least $14.93 higher, and any shortfall is charged. "Confirm parts placement" costs $0.45 on both tiers — [JLCPCB: PCB Assembly Price](https://jlcpcb.com/help/article/pcb-assembly-price)
- Basic parts and "Preferred Extended" parts (former Basic parts now hand-loaded) have no loading fee on Economic — [JLCPCB blog: How to Reduce Prototype PCB Assembly Cost (Oct 2026)](https://jlcpcb.com/blog/reduce-pcb-assembly-cost-prototype)
- Build time: Economic 1-3 days; Standard 4 days or more — [JLCPCB blog (Oct 2026)](https://jlcpcb.com/blog/reduce-pcb-assembly-cost-prototype)
- Quantity: Economic covers 2-50 pcs for common specs (some thickness/color/finish combinations are capped at 30). JLCPCB fabricates at least 5 bare boards but can assemble as few as 2 — [JLCPCB blog (Oct 2026)](https://jlcpcb.com/blog/reduce-pcb-assembly-cost-prototype)
- Double-sided assembly requires Standard: setup $51.12 plus stencil $16.42, compared with $8.18 + $1.53 for single-sided Economic — [JLCPCB blog (Oct 2026)](https://jlcpcb.com/blog/reduce-pcb-assembly-cost-prototype)
- Economic PCBA cannot use V-cut panelization; use mouse bites instead — [JLCPCB help/guide via search snippet](https://jlcpcb.com/help/article/pcb-assembly-price)
- Worked quote (Oct 9, 2026), an upper-bound reference: 140×75 mm, 4-layer, 75 BOM lines, single-sided Economic. 2 pcs $280.97; **5 pcs $474.83 ($94.97/board)**; 10 pcs $593.66; 20 pcs $992.49; 50 pcs $1,867.77 (excluding shipping). Of a two-board breakdown, about $167 was fixed cost, including **$132.01 in loading fees for 43 Extended parts** — [JLCPCB blog (Oct 2026)](https://jlcpcb.com/blog/reduce-pcb-assembly-cost-prototype)
- Global Sourcing (parts JLCPCB/LCSC don't stock) carries minimum order quantities and attrition. In the blog's example, a part used 10 times needed a 443-piece minimum buy. Leftovers stay in your private JLCPCB parts library for future PCBA orders and **cannot be shipped to you separately**. Sourced parts must arrive before assembly starts — [JLCPCB blog (Oct 2026)](https://jlcpcb.com/blog/reduce-pcb-assembly-cost-prototype)
- Older third-party guides still quote round numbers ($8 setup, $3/Extended part, $25/$50 Standard setup). Treat these as outdated next to the Oct 2026 figures above — [itechguides](https://www.itechguides.com/jlcpcb-smt-assembly-service-complete-guide-to-files-pricing-parts-and-ordering/); [nexteverything 48-line BOM example](https://nexteverything.io/guides/jlcpcb-extended-part-fees/)

**Alternatives:**
- PCBWay advertises a $29 total for 1-20 pcs assembly with free shipping for 1-20 pcs. I could not find the terms (time limit, what's included). Its offerings are Turnkey, Kitted/Consigned, and Combo — [PCBWay SMT quote page](https://www.pcbway.com/quotesmt.aspx?f=fa)
- A competitor (NextPCB) claims PCBWay usually runs higher than JLCPCB Economic for simple SMT boards. This is a biased source — [NextPCB comparison 2026](https://www.nextpcb.com/blog/jlcpcb-vs-pcbway-vs-nextpcb-comparison-2026)
- Aisler "Amazing Assembly" (Germany) promises delivery within 6 business days. Its published example pricing is a €75.00 setup and handling fee, €30.00 for two-sided assembly, and €0.38 per placement (date of the example unknown) — [Aisler assembly](https://aisler.net/products/assembly); [Aisler community: Our Simple Pricing](https://community.aisler.net/t/our-simple-pricing/102)
- Aisler states it fully supports KiCad 10 files — [Aisler community](https://community.aisler.net/t/kicad-10-is-live-and-100-supported-by-aisler/5567)
- Eurocircuits: prototype turnaround of 3 working days (proto) or 5 (standard pool). It is positioned above maker-tier services — [lcamtuf: Comparing hobby PCB vendors](https://lcamtuf.substack.com/p/comparing-hobby-pcb-vendors); [Hackaday in-depth comparison (2023)](https://hackaday.com/2023/10/13/an-in-depth-comparison-of-hobby-pcb-manufacturers)
- OSH Park (bare boards only): about $5 per square inch for three 2-layer copies, 5-6 business days (per a 2026 comparison; verify) — [dev.to Top 10 PCB prototype manufacturers 2025/2026](https://dev.to/frank_1871bc3c55f35370df3/top-10-pcb-prototype-manufacturers-20252026-35mf)
- One source says Chinese fabs adjusted FR-4 pricing again in early Aug 2026 — [AtlasPCB: JLCPCB alternatives](https://atlaspcb.com/blog/jlcpcb-alternatives) (via search snippet; not verified)

### Inferences
- **Estimated JLCPCB fees for this board, 5 pcs.** These come from the Oct 2026 fee schedule above; parts and bare-PCB cost are not included.
  - *Standard PCBA* (forced if the SCD41 is soldered on the board), assuming about 25 unique parts, about 300 SMT joints per board, and 2 THT connectors at about 30 joints per board:

    | Item | Cost |
    |---|---|
    | Setup | $25.56 |
    | Stencil | $8.21 |
    | 2 fixtures | $16.42 |
    | Loading (25 × $1.53) | $38.25 |
    | SMT joints (1,500 × $0.0016) | $2.40 |
    | THT joints (150 × $0.0164) | $2.46 |
    | Hand-soldering labor | $3.58 |
    | Confirm placement | $0.45 |
    | Packing | about $0.60 |
    | **Assembly fees total** | **about $98** |

    Add components (the SCD41 is likely the single largest line item; price not sourced here), bare PCBs, and shipping. A realistic total for 5 boards is roughly $150-300.
  - *Economic PCBA* (possible only if every part is Economic-eligible, e.g. the SCD41 is replaced by a connector-attached module such as the SEN66 or a breakout), assuming about 8 Extended parts: setup $8.18 + stencil $1.53 + loading 8 × $3.07 = $24.56 + joints about $5 + THT labor $3.58, giving **about $43 in fees** before components, PCBs, and shipping.
- Each unique Extended part costs $3.07 on Economic. Consolidating values (e.g. all 100 nF and 10 kΩ, the same LDO, the same LED) and favoring Basic/Preferred parts is the single biggest cost lever, as the blog's $132 loading line shows.
- Single-sided placement matters. Double-sided assembly forces Standard (setup $51.12, stencil $16.42), so keep all SMT on the top side.
- Through-hole add-ons are cheap at JLCPCB (cents per joint plus $3.58 per order). Factory-soldering the USB-C or JST connectors is cheaper than the user's time. Hand-soldering through-hole parts yourself is also easy.
- At about 5 boards, Aisler's €75 setup plus €0.38/placement means roughly €75 + 5 × 300 × €0.38 ≈ €645 at 300 placements per board, many times JLCPCB's cost. That is only worth it for EU shipping, speed, or no-tariff reasons. *(Inference from the published example; Aisler may count placements differently. Check the live quote.)*

### Gaps
- Seeed Fusion PCBA and MacroFab 2026 pricing: no current data found.
- Eurocircuits assembly pricing: not found (the sources above cover only fab turnaround and positioning).
- PCBWay's $29 promo terms (whether setup, stencil, and parts are included; the part-count limit) are unconfirmed.
- JLCPCB consigned-parts process and fees were not on the Oct 2026 price page. Only Global Sourcing is documented.
- Exact shipping and US tariff costs for 2026 were not researched.

---

## A2. Which Sensirion parts JLCPCB/LCSC stock (SCD41, SHT45, SGP41, STCC4, SEN6x)

### Takeaway
The SCD41 is in JLCPCB's catalog (C3659294), but it is Extended, Standard-PCBA-only, LGA-20 package, and rated "High" assembly difficulty. Stock could not be confirmed. The SHT45 (C6705435) is listed but showed 0 stock in a snippet. Some SHT40-family parts are Economic-eligible. No JLCPCB/LCSC listing turned up for the SGP41 or STCC4.

### Cited Findings
- SCD41-D-R2, JLCPCB part C3659294: Extended part, **Standard PCBA only**, assembly difficulty "High", package LGA-20. No stock or price was shown on the page fetched 2026-11-25 — [JLCPCB part detail C3659294](https://jlcpcb.com/partdetail/Sensirion-SCD41_DR2/C3659294)
- An alternate JLCPCB "Assembly-sourced" SCD41 entry exists (C9900006734), package SMD-20_L10.1-W10.1-P1.25 — [JLCPCB C9900006734](https://jlcpcb.com/partdetail/JLCPCBAssembly-SCD41_DR2/C9900006734)
- An LCSC datasheet page snapshot for C3659294 showed "In Stock: 0" (snapshot date unclear) — [LCSC datasheet C3659294](https://datasheet.lcsc.com/lcsc/2312280726_Sensirion-SCD41-D-R2_C3659294.pdf) (via search snippet)
- DigiKey and Mouser list the SCD41-D-R2 (stock varies) — [DigiKey SCD41-D-R2](https://www.digikey.com/en/products/detail/sensirion-ag/SCD41-D-R2/13684005); [Findchips SCD41-D-R2](https://www.findchips.com/search/SCD41-D-R2)
- SHT45-AD1B-R3, JLCPCB C6705435: SMD-4P, SMT assembly. The snippet showed zero stock, minimum order 1 — [JLCPCB C6705435](https://jlcpcb.com/partdetail/SENSIRION-SHT45_AD1BR3/C6705435) (via search snippet)
- Some SHT40-family listings show PCBA Type "Economic and Standard" — [JLCPCB SHT40-AD1B-R3 C2848306](https://jlcpcb.com/partdetail/SHT40-AD1B-R3/C2848306); [JLCPCB SHT41-AD1B-R2 C7461861](https://jlcpcb.com/partdetail/SHT41-AD1B-R2/C7461861) (via search snippet)
- A Sensirion SEN63C entry exists on JLCPCB (C52088895), so SEN6x modules appear in the catalog — [JLCPCB SEN63C](https://jlcpcb.com/partdetail/Sensirion-SEN63C_SINT/C52088895) (from search result title only)
- Purchased parts (incl. pre-ordered stock) live in the JLCPCB private library for PCBA use only and cannot be shipped separately — [JLCPCB C3659294](https://jlcpcb.com/partdetail/Sensirion-SCD41_DR2/C3659294)
- JLCPCB Sensirion manufacturer listing (browse current stock here) — [JLCPCB Sensirion parts](https://jlcpcb.com/parts/manufacturers/Sensirion)

### Inferences
- If the SCD41 is on the PCB, the order is Standard PCBA (about $25.56 setup plus fixtures, $1.53 for every unique part). If stock is 0, Global Sourcing or pre-ordering applies, with possible MOQs. Two ways around this: (a) put the CO₂ sensor on a breakout or use a connector-based SEN66-style module, keeping the main board Economic-eligible; or (b) accept Standard and pre-order the SCD41 into the JLCPCB parts library before ordering.
- For RH/T, an SHT40/SHT41 that is Economic-eligible and in stock is the practical substitute if the SHT45 is out of stock. The accuracy difference should be weighed in the sensor-selection workstream.

### Gaps
- Live stock and price for SCD41, SHT45, SGP41, and STCC4 at LCSC/JLCPCB could not be read: JLCPCB part pages render stock client-side and the fetch returned none. **Check live before committing.**
- The SGP41 (DFN) and STCC4 had no JLCPCB/LCSC listing in results. They may exist under other names or need Global Sourcing.
- The SEN66 specifically (as opposed to the SEN63C) was not confirmed on JLCPCB.

---

## A3. Hybrid: factory-assemble the fine-pitch SMT, hand-solder through-hole

### Takeaway
This is the sweet spot for this user. JLCPCB places the MCU/module, LGA/DFN sensors, regulator, and passives. The user (or JLCPCB, for cents per joint) solders through-hole headers, JST/Qwiic connectors, and display sockets. That removes the exact failure mode from 2021 (unreliable SMT soldering).

### Cited Findings
- JLCPCB manual/THT assembly is $0.0164 per joint plus $3.58 per order. A 2×10 header on 5 boards (100 joints) costs about $1.60 plus the labor fee. THT parts carry no feeder loading fee — [JLCPCB blog (Oct 2026)](https://jlcpcb.com/blog/reduce-pcb-assembly-cost-prototype)
- Manual-assembly per-joint pricing is identical on Economic and Standard — [JLCPCB: PCB Assembly Price](https://jlcpcb.com/help/article/pcb-assembly-price)
- The SCD41 is a 10.1×10.1 mm LGA-20 at 1.25 mm pitch (pads underneath), rated "High" assembly difficulty by JLCPCB — [JLCPCB C9900006734](https://jlcpcb.com/partdetail/JLCPCBAssembly-SCD41_DR2/C9900006734); [JLCPCB C3659294](https://jlcpcb.com/partdetail/Sensirion-SCD41_DR2/C3659294)

### Inferences
- Recommended split: factory places everything SMT on the top side (ESP32 module or bare chip, SCD41/SHT4x/SGP41, LDO, USB-C receptacle, ESD, passives, FPC connector). The user hand-solders only THT: pin headers for an optional display module, JST-GH or SH connector for an SPS30/SEN66 cable, mounting hardware. Alternatively, let JLCPCB do the THT as well for a few dollars.
- The FPC connector for e-ink (typically 0.5 mm pitch) and the USB-C receptacle (fine-pitch SMT legs) are the two parts most likely to defeat a beginner. Both should be factory-placed.
- Hybrid keeps rework possible. If a sensor choice changes, a header or JST footprint can host an off-board breakout without a respin.

### Gaps
- I found no published failure-rate data for JLCPCB assembly of LGA sensors such as the SCD41. JLCPCB's "High difficulty" label is the only signal.

---

## A4. DIY SMT: stencil + paste + hot plate or oven

### Takeaway
DIY reflow works for many hobbyists on QFN and LGA parts, but the evidence is anecdotal. Bridging from smeared paste and overheating are the common failures, and LGA/QFN parts with hidden pads cannot be done with an iron. For a user who already struggled with SMT, a 50×50 mm hot plate will not fit a 121×65 mm board. Factory assembly is cheaper than buying tooling for one 5-board run.

### Cited Findings
- JLCPCB's QFN guide recommends stencil-applied paste with a window-pane pattern on the thermal pad, careful tweezer placement, and reflow by hot plate, hot air, or oven. It argues that hand-dosing paste on a hidden thermal pad and 0.4 mm perimeter pads is largely guesswork — [JLCPCB: How to Solder QFN Components](https://jlcpcb.com/blog/how-to-solder-qfn-components-a-step-by-step-guide)
- JLCPCB has a hot-plate + stencil home reflow guide — [JLCPCB: How to Master PCB Reflow Soldering at Home](https://jlcpcb.com/blog/how-to-master-pcb-reflow-soldering)
- RepRap wiki calls hot-plate reflow forgiving and accessible even for beginners — [RepRap: Hotplate Reflow Technique](https://reprap.org/wiki/HotplateReflowTechnique)
- Adafruit (2016) reported a 100 W hot plate working well for 0.5 mm pitch QFN and LGA packages — [Adafruit blog](https://blog.adafruit.com/2016/04/13/100w-1-hot-plate-for-smt-reflow/)
- Big Mess o' Wires tried stencil + hot-plate reflow and found it no better than earlier efforts. Most bridges occurred where paste had smeared — [BMOW: Reflow Soldering with Hot Plate and Stencil](https://www.bigmessowires.com/?p=4425); [BMOW](https://bigmessowires.com/?p=4411)
- Forum counterpoints: hot plates can't heat tall components from above, dwell times may be too long and damage parts, and one TI engineer's 48-pin QFN board reportedly delaminated on a hot plate — [diyAudio forum post](https://diyaudio.com/community/goto/post?id=7827972) (via search snippet; exact attribution unverified)
- Hobbyist guidance favors Sn63/Pb37 paste for its wider process window when RoHS isn't required — [AllPCB hobbyist guide](https://www.allpcb.com/es-ES/allelectrohub/easy-smd-soldering-techniques-for-electronic-hobbyists) (via search snippet)
- Miniware MHP50 hot plate prices: £85.80 (HobbyRC UK), £97.90 (Flying Tech UK), €109 (Welectron), $209.95 for the brass MHP50-B5 (SparkFun) — [HobbyRC](https://www.hobbyrc.co.uk/miniware-mhp50-mini-hot-plate-preheater-2); [Flying Tech](https://www.flyingtech.co.uk/product/miniware-mhp50-mini-hot-plate-preheater/); [Welectron](https://welectron.com/Miniware-MHP50-Hot-Plate-Preheater); [SparkFun MHP50-B5](https://www.sparkfun.com/hot-plate-preheater-mhp50-b5-brass.html)
- MHP50 notes: a PD power supply is not included. With a 50 W PD supply it took nearly 5 minutes to reach 220 °C; with a 65 W supply, 2 minutes. Reflow mode can only start when the plate is below 100 °C. Elektor says it can reflow small boards — [Elektor MHP50 review](https://www.elektormagazine.com/review/miniware-mhp50-hot-plate)
- An EEVblog commenter says small ceramic plates often heat unevenly (said of the MHP30) — [EEVblog: advice for small reflow plate](https://eevblog.com/forum/reviews/advice-for-small-reflow-plate)

### Inferences
- **Hand-solderability by iron.** This is general practitioner consensus, not from a source fetched here; see Gaps.

  | Part | Soldering with an iron |
  |---|---|
  | 1206/0805 passives | Comfortable |
  | 0603 | Doable with practice |
  | 0402 | Hard for a beginner |
  | SOIC/SOT-23/SOT-223 | Fine |
  | TSSOP/QFP 0.5 mm | Drag-solder with flux, risky for a beginner |
  | QFN/DFN with exposed pad, LGA (SCD41, SGP41 DFN, SHT4x 1.5×1.5 mm DFN) | Not reliably solderable by iron; needs paste plus hot air, hot plate, or oven |

- **Board size versus tooling.** The MHP50's heated area is reportedly about 50×50 mm (implied by the name; verify). That cannot reflow a 121×65 mm board in one pass. The options are a larger generic hot plate, a converted or controlled toaster oven, or hot air on individual parts.
- **Tooling cost for a credible DIY setup** (rough, unsourced except the MHP50):
  - Hot plate about $85-210 plus a PD supply.
  - Stencil about $7-15.
  - Paste about $15-30, which needs refrigeration and has a limited shelf life.
  - Fine tweezers, flux, and solder wick about $20.
  - Optionally a hot-air station about $60-150 and a magnifier or microscope.
  - **Total about $150-400.** That exceeds the extra cost of JLCPCB assembly for 5 boards.
- **Likely failure modes for this user:**
  - Paste bridging on the 0.5 mm FPC connector and USB-C.
  - Voids or opens under the LGA/QFN that are invisible without X-ray.
  - Overheating sensors: Sensirion parts have reflow limits and the SCD41 is optically sensitive.
  - Contaminating sensor openings with flux.
  - Tombstoning of small passives.

### Gaps
- No quantitative beginner success rates for stencil + hot plate on LGA/DFN were found. All evidence is anecdotal (vendor blogs, forums, old Adafruit/BMOW posts).
- Sensirion's specific reflow and handling guidance for the SCD4x/SHT4x/SGP4x (e.g. no washing, sensor opening protection) was not researched here. Check the datasheets and handling instructions.
- A sourced reference for iron-solderable package limits (0805 vs 0402 etc.) was not fetched. The table above is common practice, not cited.
- Stand-alone stencil prices (outside PCBA) and generic large hot plate or controlled-oven (e.g. Controleo3) prices were not researched.

---

## A5. Module and breakout approach (castellated ESP32 module plus vendor breakouts on a carrier)

### Takeaway
This is what the 2021 board already did. It is the lowest-risk route and needs no SMT skill, but it gives a large, tall, less polished board and costs more per unit. Connector and header reliability is the weak point. A middle ground keeps the ESP32 as a factory-placed module (castellated or LGA module) while putting the sensors directly on the PCB via JLCPCB.

### Cited Findings
- easyeda2kicad and the JLCPCB plugins (see B2) make it easy to pull LCSC footprints for ESP32 modules and connectors when designing a carrier — [easyeda2kicad](https://github.com/uPesy/easyeda2kicad.py)
- atopile advertises reusable modules and a package registry (packages.atopile.io), relevant for composing known-good sub-circuits — [atopile GitHub](https://github.com/atopile/atopile)

### Inferences
- **Pros:**
  - Zero SMT soldering.
  - Sensors can be swapped or upgraded without a respin.
  - Vendor breakouts include proper decoupling, level shifting, and sometimes thermal isolation.
  - Qwiic/STEMMA QT cables let sensors sit away from ESP32 heat. That matters for SCD41/SHT4x temperature and RH accuracy.
  - No dependency on JLCPCB stock of LGA sensors.
- **Cons:**
  - Footprint and height: the 2021 board was 121×65 mm largely because of breakouts.
  - Higher BOM cost per unit (each breakout costs several times the bare sensor).
  - Cable and header connections can loosen or corrode.
  - Harder to make a sleek enclosure.
  - Breakout pinouts and revisions change over time.
- **Hybrid variant (likely best fit):**
  - JLCPCB-assembled main board with the ESP32 module (e.g. a WROOM-style module), the SHT4x placed thermally isolated with slots and copper keep-out, the SCD41 on-board if Standard PCBA is acceptable, LDO, and USB-C.
  - Plus a JST-GH socket for the SEN66/SPS30 cable and one Qwiic socket for future add-ons.

### Gaps
- No current (2026) prices or availability for Adafruit/SparkFun/Seeed breakouts of the SCD41, SGP41, SHT45, or STCC4 were researched in this pass.
- No published reliability data comparing Qwiic-cabled sensors with on-board sensors was found.

---

## A6. Cost and effort comparison for about 5 boards (decision matrix)

### Takeaway
For this user, the hybrid of JLCPCB-assembled SMT plus self-soldered THT gives the best cost, reliability, and effort trade-off. A fully breakout-based carrier is the fallback if Sensirion parts are out of stock at JLCPCB. DIY reflow does not pay off for a single 5-board run.

### Cited Findings
- All per-fee numbers come from [JLCPCB: PCB Assembly Price (Oct 22, 2026)](https://jlcpcb.com/help/article/pcb-assembly-price) and [JLCPCB blog (Oct 2026)](https://jlcpcb.com/blog/reduce-pcb-assembly-cost-prototype). Aisler numbers come from [Aisler community pricing](https://community.aisler.net/t/our-simple-pricing/102); MHP50 prices from [Elektor](https://www.elektormagazine.com/review/miniware-mhp50-hot-plate) and [SparkFun](https://www.sparkfun.com/hot-plate-preheater-mhp50-b5-brass.html).

### Inferences
Matrix (estimates for 5 boards, about 40-60 parts; all dollar figures are inferences built from the cited fee schedules plus unsourced rough component and tool costs):

| Approach | Est. cost, 5 boards (excl. shipping) | User effort | Board size and look | Key risks and failure modes |
|---|---|---|---|---|
| **1. JLCPCB full SMT, Standard** (SCD41 on board) | about $98 assembly fees + parts (SCD41 dominant) + about $5-20 PCBs, so **about $150-300** | Low: upload Gerber/BOM/CPL, review placement | Smallest, most polished; sensors can be thermally isolated by layout | SCD41/SHT45 out of stock, leading to Global Sourcing MOQs and delays; wrong footprint or rotation in CPL; design bug means a respin of about 1-2 weeks |
| **2. JLCPCB Economic** (no Standard-only parts; CO₂ via SEN66 or breakout on connector) | about $43 assembly fees + parts + PCBs + module cost, so **about $120-250** (module dominates) | Low | Compact main board plus cabled module | Requires that all parts be Economic-eligible; Extended part fee of $3.07 each adds up |
| **3. Hybrid: JLCPCB SMT + user THT** (recommended) | Same as 1 or 2, plus about $0-10 saved by self-soldering THT | Low-medium: only THT soldering, which the user can do reliably | Compact | Same as 1 or 2; minor THT workmanship risk |
| **4. Aisler / EU assembly** | €75 setup + €0.38/placement means **about €400-700+** | Low | Same as 1 | Cost; part availability within their library |
| **5. DIY stencil + hot plate/oven** | PCBs + stencil about $15-30, parts about $50-150, tooling **about $150-400** one-time | High; learning curve | Same as 1 if successful | Bridging, voids under LGA/QFN (invisible), overheated sensors, flux in sensor ports; 121×65 mm board exceeds a 50 mm plate; past failure history |
| **6. Breakout/module carrier** (2021 style) | Bare PCB about $5-20 + breakouts, likely **about $40-80 per unit** in parts (unsourced) | Low (THT only) | Largest and tallest, "maker" look | Connector and header reliability; higher unit cost; bulky enclosure |

### Gaps
- Component prices (ESP32 module, SCD41, SGP41, SHT4x, SEN66) were not gathered in this research pass. They drive totals more than the assembly fees do.
- Bare 2-layer PCB price at JLCPCB for 5 pcs at about 100×60 mm in 2026 was not fetched (often quoted as a few dollars, but unverified here).

---

## B1. KiCad: current version, kicad-cli capabilities, file format

### Takeaway
KiCad 10 (10.0.0 released March 20, 2026; bug-fix releases continued to at least 10.0.5) is current, and 9.x is no longer maintained. `kicad-cli` covers everything an AI assistant needs headlessly: ERC/DRC with JSON output and exit codes, Gerber/drill/pos/BOM/netlist export, ODB++ and IPC-2581, STEP/GLB/STL 3D export, and jobsets. KiCad's S-expression text files diff cleanly and can be edited by an LLM.

### Cited Findings
- KiCad 10.0.0 was released, with the blog dated March 2026 (page metadata: March 20, 2026) — [KiCad blog: Version 10.0.0 Released](https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/)
- KiCad 10 highlights:
  - Graphical DRC rule editor (compatible with the custom-rules language) and DRC suggested-fix actions.
  - Design variants (shared schematic, differing BOM/properties).
  - Overhauled time-domain track tuning.
  - Windows dark mode.
  - 3D PDF export.
  - New Allegro, PADS, and gEDA importers.
  - Official libraries ship STEP files only (+952 symbols, +1,216 footprints, +386 3D models).

  [KiCad 10 release blog](https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/); [CNX Software](https://www.cnx-software.com/2026/03/22/kicad-10-release-dark-mode-graphical-drc-rule-editor-new-file-importers-and-more/); [Hackster](https://www.hackster.io/news/what-s-new-in-kicad-10-63372efa034c)
- KiCad 9.0.8 bug-fix released 2026-03-16 — [KiCad 10 release blog](https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/)
- The GitHub release listing shows 10.0.5 as the latest bug-fix entry, says KiCad 9.x is no longer actively maintained, and says KiCad 11 development is underway — [KiCad source mirror releases](https://github.com/KiCad/kicad-source-mirror/releases) (via search snippet)
- **kicad-cli (v10 docs):**
  - `pcb export`: gerbers, drill, pos, step, stpz, brep, xao, glb, vrml, stl, ply, u3d, ipc2581, odb, ipcd356, gencad, svg, pdf, 3dpdf, dxf, ps, stats.
  - `pcb drc`; `sch erc`.
  - `sch export`: bom, netlist, pdf, python-bom, svg, dxf, ps, hpgl.
  - `jobset run`; fp/sym export and upgrade.

  [KiCad docs: CLI](https://docs.kicad.org/10.0/en/cli/cli.html)
- DRC/ERC: `--format report|json` and `--exit-code-violations` (exit 0 if clean, 5 if violations). These are suitable for CI and for agent loops — [KiCad docs: CLI](https://docs.kicad.org/10.0/en/cli/cli.html)
- STEP export options:
  - `--subst-models` (swap VRML for STEP/IGS models of the same name).
  - `--include-tracks`, `--include-pads`, `--include-zones`, `--include-silkscreen`, `--include-soldermask`.
  - `--board-only`, `--no-dnp`, `--variant`, `--fuse-shapes`, `--user-origin`.
  - `--no-optimize-step`.

  [KiCad docs: CLI](https://docs.kicad.org/10.0/en/cli/cli.html)

### Inferences
- An agent workflow is fully scriptable. Claude Code can edit `.kicad_sch`/`.kicad_pcb` text, or drive the IPC API or an MCP server. It can then run `kicad-cli sch erc --format json --exit-code-violations`, `kicad-cli pcb drc ...`, and `kicad-cli pcb export gerbers/drill/pos` plus `sch export bom`, all from Bash on Windows. A `jobset` file can make output generation reproducible.
- KiCad 10's STEP-only libraries plus `pcb export step --subst-models` give good-quality STEP for the SolidCraft/Bambu enclosure workflow.

### Gaps
- I did not confirm the exact latest point release as of Nov 2026 (10.0.5 or later). Check kicad.org/download.
- The S-expression file format's diff-friendliness is well known but was not cited from a fetched source in this pass.

---

## B2. KiCad ecosystem for JLCPCB, LCSC parts, Python/IPC API, and AI/MCP tooling

### Takeaway
KiCad has the richest AI-adjacent ecosystem:
- JLCPCB output plugins: Fabrication Toolkit (via PCM), and Bouni's kicad-jlcpcb-tools for LCSC part assignment and parts DB search.
- easyeda2kicad for pulling LCSC symbols, footprints, and 3D models by C-number.
- An official IPC API with kicad-python (SWIG deprecated).
- Several community MCP servers for Claude, including ones targeting KiCad 10.

All MCP servers are community projects of varying maturity.

### Cited Findings
- **Fabrication Toolkit** (bennymeg): JLCPCB's own help article recommends it as a free plugin that exports Gerbers, BOM, and CPL in JLCPCB format in one click. It installs via the Plugin and Content Manager — [JLCPCB help: BOM/centroid from KiCad](https://jlcpcb.com/help/article/how-to-generate-the-bom-and-centroid-file-from-kicad); [Fabrication Toolkit GitHub](https://github.com/bennymeg/Fabrication-Toolkit)
- **Bouni kicad-jlcpcb-tools** assigns LCSC part numbers, queries the JLCPCB parts database, looks up datasheets, and generates fab and assembly files. Its README mostly shows KiCad 7/8 paths. One guide says to install manually into the KiCad 10 plugins folder if it is not yet listed in PCM — [Bouni/kicad-jlcpcb-tools](https://www.github.com/Bouni/kicad-jlcpcb-tools); [ZUDO guide](https://zudopd.netlify.app/pj/zudo-pd/docs/how-to/kicad-jlcpcb-tools)
- **easyeda2kicad**:
  - `pip install easyeda2kicad`; `easyeda2kicad --full --lcsc_id=C2040` creates the symbol, footprint, and 3D model, with `--output` for a library path.
  - Supports KiCad v6+.
  - On Windows, run it with `python -m easyeda2kicad` from the KiCad Command Prompt.
  - The README warns that converted symbols and footprints are not guaranteed correct.

  [easyeda2kicad GitHub](https://github.com/uPesy/easyeda2kicad.py)
- **IPC API / Python:**
  - SWIG Python bindings are deprecated as of KiCad 9.0. The docs point to kicad-python, the official Python bindings for the Protobuf IPC API.
  - In KiCad 9 and 10 the IPC API only talks to a **running KiCad GUI instance**, and its scope is focused on the PCB editor.
  - Docs say SWIG removal was planned for 10.0, while a devlist post warns that plugins will break in KiCad 11. The timing conflicts.

  [KiCad dev docs: PCB Python Bindings](https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/); [IPC API for add-on developers](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/); [kicad-python on PyPI](https://pypi.org/project/kicad-python/0.1.0a0/); [FOSDEM 2025: Bringing a new API to KiCad](https://archive.fosdem.org/2025/schedule/event/fosdem-2025-6802-bringing-a-new-api-to-kicad/)
- **KiCad MCP servers** (community, not official):
  - *mixelpixx/KiCAD-MCP-Server* (MIT): project setup, schematic and PCB editing, routing, DRC/ERC, export. Maintainers say it has spun off into **Konnect-EDA, a native KiCad 10 plugin (single Rust binary) using the official IPC API** — [mixelpixx/KiCAD-MCP-Server](https://github.com/mixelpixx/KiCAD-MCP-Server) (via search summary)
  - *Greg3001/kicad-claude-mcp*: built for Claude Code, advertises 105 tools covering schematic, library indexing, layout, Freerouting autorouting, ERC/DRC, manufacturing outputs, panelization, and SPICE. It edits KiCad files directly, so KiCad is needed only for review — [Greg3001/kicad-claude-mcp](https://github.com/greg3001/kicad-claude-mcp)
  - *kicad-mcp-server* (PyPI, GPLv3) targets KiCad 9.x — [PyPI kicad-mcp-server](https://pypi.org/project/kicad-mcp-server/)
  - *muammar-yacoob/kicad-mcp* lists KiCad 8.x as a prerequisite — [muammar-yacoob/kicad-mcp](https://github.com/muammar-yacoob/kicad-mcp)
  - KiCad forum threads discuss MCP servers for AI-assisted design — [KiCad forum: KiCAD MCP Server](https://forum.kicad.info/t/kicad-mcp-server/60704); [KiCad forum: I built an MCP server...](https://forum.kicad.info/t/i-built-an-mcp-server-that-lets-ai-assistants-help-with-kicad-pcb-design/66451)

### Inferences
- A practical Claude Code + KiCad 10 stack:
  - Claude edits or generates schematic and board files, or works through an MCP server.
  - easyeda2kicad pulls exact LCSC footprints and 3D models for the parts actually ordered (SCD41, ESP32 module, USB-C, FPC).
  - Bouni's plugin or a BOM field assigns LCSC C-numbers.
  - `kicad-cli` produces Gerbers, drill, pos, BOM, and STEP.
  - Fabrication Toolkit formats the output for JLCPCB, or Claude scripts the CPL and BOM column mapping.
  - The human does final placement and routing review in the GUI.
- Pin the MCP server to the installed KiCad major version, since the projects target 8, 9, and 10 respectively. Prefer IPC-API-based tools for future-proofing because SWIG is going away.
- Footprint verification is the agent's biggest risk. easyeda2kicad warns about correctness, and a wrong LGA pad map or USB-C footprint is the classic respin cause. Always cross-check against the datasheet and use JLCPCB's placement preview.

### Gaps
- I could not verify each MCP server's maturity, test coverage, or recent commit activity. The Konnect-EDA claim comes from a search summary and was not fetched directly.
- Whether Bouni's plugin is officially in the KiCad 10 PCM was not confirmed.

---

## B3. EasyEDA Std/Pro: scriptability, file format, JLC integration, AI editability

### Takeaway
EasyEDA Pro has tight JLCPCB/LCSC integration and a documented (2025) JSON-Lines file format plus a browser-side extension API. However, project files are zipped `.epro` archives, editing happens inside the browser runtime, and there is no headless CLI for DRC or Gerber output. That makes it much less practical for an AI coding assistant than KiCad. KiCad can import EasyEDA Pro projects, which gives the user a migration path for their 2021 design.

### Cited Findings
- EasyEDA Pro projects are `.epro` ZIP archives containing JSON Lines documents. EasyEDA Standard files are single JSON documents — [KiCad dev docs: EasyEDA import format](https://dev-docs.kicad.org/en/import-formats/easyeda/index.html)
- EasyEDA publishes a V3 file-format spec dated 2025-10-21 (V2.2 marked as not the latest) — [EasyEDA Pro File Format](https://prodocs.easyeda.com/en/format/index)
- Pro extension API code runs inside EasyEDA Pro's browser runtime (`async function(eda) {...}`) — [EasyEDA Pro Extension API reference](https://prodocs.easyeda.com/en/api/reference/pro-api.html); [How to start](https://prodocs.easyeda.com/en/api/guide/how-to-start.html)
- Legacy Std API exposes `api('getSource', {type:'json'})` and `applySource` — [EasyEDA API (Std)](https://docs.easyeda.com/en/API/1-How-to-Use-API/)
- EasyEDA Pro's format converter imports `.kicad_pcb`/`.kicad_sch` but exports only `.zip` and `.epro` — [EasyEDA Pro format converter](https://prodocs.easyeda.com/en/import-export/easyeda-pro-format-converter/)
- KiCad has a native EasyEDA Pro importer. The community epro2kicad script drives it headlessly. Newer EasyEDA exports (editor 2.2+) store design-rule values in a way older KiCad rejected, fixed in KiCad 10.0.4+. Some exports have CR/LF issues — [Hackaday.io: epro2kicad](https://hackaday.io/project/206867-epro2kicad-easyeda-pro-to-kicad-headless)
- An `easyeda/easyeda-api-skill` repository with a SKILL.md exists (contents not verified) — [jsDelivr: easyeda-api-skill SKILL.md](https://cdn.jsdelivr.net/gh/easyeda/easyeda-api-skill@main/SKILL.md)

### Inferences
- An AI assistant could in principle unzip an `.epro`, edit the JSON Lines, and re-zip it. In practice there is no CLI DRC or export, so every verification and fab-output step needs the GUI. That breaks the edit, check, and export loop that makes Claude Code effective.
- For the user's existing 2021 EasyEDA board: import it into KiCad 10.0.4+ (or use epro2kicad) as a reference, rather than continuing in EasyEDA.
- EasyEDA's main advantage, one-click LCSC parts and JLC ordering, is largely matched in KiCad by easyeda2kicad plus the JLCPCB plugins.

### Gaps
- I didn't verify whether the EasyEDA "API skill" repo is an official AI-agent integration or what it can do. It may be worth a follow-up look.
- EasyEDA Pro STEP export quality was not researched.

---

## B4. Autodesk Eagle: EOL status and migration

### Takeaway
Autodesk ended Eagle access on June 7, 2026 (some Autodesk pages say June 6), so it is now past EOL. The user's installed Eagle should be treated as dead. Autodesk's path is Fusion Electronics, which opens `.sch`/`.brd`/`.lbr`. The free alternative is KiCad's built-in Eagle importer.

### Cited Findings
- Autodesk blog: Eagle access was scheduled to end on June 7, 2026. Autodesk will keep investing in Fusion Electronics — [Autodesk: What's Next for EAGLE Users](https://www.autodesk.com/products/fusion-360/blog/eagle-to-autodesk-fusion-transition/)
- A Japanese-language Autodesk page gives June 6 (time-zone difference) — [Autodesk JP blog](https://www.autodesk.com/products/fusion-360/blog/ja/eagle-to-autodesk-fusion-transition/)
- Forum thread "EAGLE dying on June 7, 2026" — [Autodesk forums](https://forums.autodesk.com/t5/eagle-forum/eagle-dying-on-june-7-2026/td-p/12017987)
- Autodesk's migration guide covers importing `.sch`, `.brd`, and `.lbr` into Fusion Electronics. Managed libraries appear automatically in Fusion — [Autodesk support: migrate EAGLE to Fusion Electronics](https://www.autodesk.com/support/download-install/troubleshoot/issues/howto-guide-eagle-schematics-to-autodesk-fusion-electronics); [Autodesk: How to Migrate From EAGLE to Fusion 360 Electronics](https://www.autodesk.com/products/fusion-360/blog/migrate-from-eagle-to-fusion-360-electronics-tutorial/)
- LCSC's guide states Eagle is no longer sold or supported and the standalone app can no longer run, and points to KiCad's built-in Eagle importer. Autodesk's own wording is "end of access", so treat the "cannot run" claim with care — [LCSC: EAGLE End-of-Life & Migration Guide](https://www.lcsc.com/blog/pcb-cad-guide/)

### Inferences
- The user's 2021 design is in EasyEDA, not Eagle, so there is little to migrate from Eagle. The user can uninstall Eagle; any old `.brd`/`.sch` files import into KiCad.
- Fusion Electronics is subscription-based, has limited scripting compared with kicad-cli, and uses a proprietary cloud format. That makes it a weaker fit for an AI coding assistant than KiCad, although it has native MCAD/ECAD integration.

### Gaps
- Fusion Electronics' 2026 pricing, free/personal-tier electronics limits, and CLI or automation capabilities were not researched.

---

## B5. Code-based PCB design: atopile, SKiDL, tscircuit

### Takeaway
atopile (MIT, about 4.1k GitHub stars) is the most relevant. It compiles a declarative `.ato` language into a KiCad layout, picks parts parametrically, has a package registry, and ships CLAUDE.md/AGENTS.md files. Layout is still done manually in KiCad, and Windows users are pointed to WSL. tscircuit (TypeScript/React with built-in autorouting, browser-based) is more experimental, and its verification maturity has been questioned. For a ~40-part board, these add a learning layer for modest gain. Plain KiCad with Claude editing files plus kicad-cli is the lower-risk path, with atopile as an optional schematic-as-code front end.

### Cited Findings
- atopile:
  - Its compiler "updates your KiCad layout".
  - Build outputs are BOM, fabrication and assembly data, and reports.
  - Parametric picking of discrete components.
  - Reusable modules via packages.atopile.io.
  - Place and route are done in KiCad.
  - The repo contains `.claude`, `.cursor`, `AGENTS.md`, and `CLAUDE.md`.
  - WSL is recommended on Windows.
  - MIT license, about 4.1k stars, about 2,843 commits.

  [atopile GitHub](https://github.com/atopile/atopile)
- atopile maintainers have described it as aimed at low-to-medium complexity boards. One HN user reported barely writing ato code anymore, using Claude Code with a rules file and an MCP server — [Hacker News: atopile thread](https://news.ycombinator.com/item?id=44548449); [HN comment thread](https://news.ycombinator.com/item?id=46944460) (via search summary; exact comment not verified)
- A 2026 guide (by a competing vendor, siliXon, published Oct 30, 2026 and updated Nov 24, 2026) lists atopile and tscircuit as free and open source. It says atopile's layout is manual in KiCad, says tscircuit does placement in code with autorouting, and estimates "hours to days" to a board for each — [siliXon: Best AI PCB design tools in 2026](https://silixon.io/blog/best-ai-pcb-design-tools) (vendor-biased)
- tscircuit: PCB design in React/TypeScript. A forum thread raised concerns that browser speed doesn't replace mature PCB verification — [Elektroda: tscircuit](https://www.elektroda.com/news/news4169243.html)

### Inferences
- **atopile** suits this project only if the user wants schematic-as-code with reusable modules (e.g. a "Sensirion I²C sensor + decoupling" module). It still ends in KiCad for layout and fab output, so KiCad is required either way.
- **tscircuit** could suit an AI-first flow because the whole board is TypeScript that an LLM writes fluently. However, KiCad export, DRC rigor, and JLCPCB-ready outputs need verification before trusting it with a first real order.
- **SKiDL** (Python netlist generation for KiCad) was not researched this pass. It generates netlists only, so layout remains in KiCad.

### Gaps
- No direct 2026 maturity or version data for atopile (version number, release date), tscircuit (KiCad export support, DRC), or SKiDL was gathered.
- No independent (non-vendor) 2026 reviews were found for atopile or tscircuit.

---

## B6. Autorouting and AI-assisted layout

### Takeaway
Freerouting remains the free autorouter used with KiCad, including via MCP servers such as Greg3001/kicad-claude-mcp. Commercial AI layout tools exist: Quilter does AI placement and routing and is free for non-commercial use, and Flux.ai is a browser ECAD with an AI agent from $100/month with poor Trustpilot reviews. For a 2-layer, ~40-part board with sensitive sensor placement, human-guided placement with assisted routing is still the realistic approach.

### Cited Findings
- Greg3001/kicad-claude-mcp integrates Freerouting autorouting into a Claude Code MCP workflow — [Greg3001/kicad-claude-mcp](https://github.com/greg3001/kicad-claude-mcp)
- Quilter: AI placement and routing from a finished schematic and board file. Free for non-commercial use and very small businesses, otherwise priced per project by pins to route. Typical jobs return in about 4 hours, complex ones up to 24 hours (vendor-stated, via siliXon's article) — [siliXon guide](https://silixon.io/blog/best-ai-pcb-design-tools)
- Flux.ai: browser ECAD with an AI agent, from $100/month after a 7-day trial with no free plan (per siliXon). Trustpilot 1.9/5 from 138 reviews as of Oct 30, 2026. Reviewers reported a simple ESP32 board still undesigned after 2 hours — [siliXon guide](https://silixon.io/blog/best-ai-pcb-design-tools) (vendor-biased source)
- A discussion of autorouting's good and bad sides — [electronics.dev: Auto-Routing in PCB Design](https://electronics.dev/p/auto-routing-in-pcb-design-the-good)

### Inferences
- For this board, the layout-critical decisions are not routing:
  - Sensor thermal isolation from the ESP32 and LDO (slots, keep-outs).
  - SCD41 and SHT4x airflow and enclosure port alignment.
  - Antenna keep-out for the ESP32 module.
  - USB-C ESD placement.

  Claude can draft placement via file edits or MCP. Freerouting or manual routing then finishes the 2-layer board easily, followed by kicad-cli DRC.

### Gaps
- The current Freerouting version and compatibility with KiCad 10 were not directly verified.
- DeepPCB and other AI routers were not covered by any source fetched.

---

## B7. STEP export for enclosure fit (SolidCraft / Bambu)

### Takeaway
KiCad 10 is the strongest option for STEP export. Its official libraries now ship STEP models only, and `kicad-cli pcb export step` can be scripted with options to include pads, tracks, silkscreen, and soldermask, substitute models, and exclude DNP parts. LCSC-derived 3D models come from easyeda2kicad. The resulting STEP imports into parametric CAD such as SolidCraft for enclosure design.

### Cited Findings
- KiCad 10 official libraries ship STEP files only, for better geometric accuracy, plus 386 new 3D models — [KiCad 10 release blog](https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/)
- `kicad-cli pcb export step` options: `--subst-models`, `--include-tracks` (slow), `--include-pads`, `--include-zones`, `--include-silkscreen`, `--include-soldermask`, `--board-only`, `--no-components`, `--no-dnp`, `--variant`, `--fuse-shapes`, `--user-origin`, `--no-optimize-step`. Also `stpz`, `brep`, `glb`, and `stl` exports, plus new 3D PDF — [KiCad docs: CLI](https://docs.kicad.org/10.0/en/cli/cli.html)
- easyeda2kicad pulls 3D models for LCSC parts (`--3d` / `--full`) — [easyeda2kicad](https://github.com/uPesy/easyeda2kicad.py)

### Inferences
- Workflow: run `kicad-cli pcb export step --subst-models --no-dnp --user-origin ...`, import the STEP into SolidCraft (which has an MCP server in this environment), and model the enclosure around the board. Alignment points are sensor ports, the USB-C opening, display window, and mounting holes. Then print on the Bambu printer.
- Check that easyeda2kicad 3D models are correctly oriented and offset before trusting enclosure clearances.

### Gaps
- EasyEDA Pro and Fusion Electronics STEP export quality were not compared in this pass.

---

## B8. EDA recommendation for AI-assisted design

### Takeaway
**Use KiCad 10.** It has open, text-based S-expression files Claude can read and edit, plus `kicad-cli` for headless ERC/DRC (JSON plus exit codes), Gerber/drill/pos/BOM, and STEP. It also has an official IPC API (kicad-python), community MCP servers including KiCad 10/IPC-based ones, JLCPCB plugins, and easyeda2kicad for LCSC footprints. Retire Eagle (past EOL June 2026) and don't continue in EasyEDA Pro (zipped JSON-Lines, browser-only API, no CLI). Optionally evaluate atopile as a code-first schematic front end, but it still ends in KiCad.

### Cited Findings
- KiCad 10 is current and 9.x is unmaintained — [KiCad blog](https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/); [GitHub releases](https://github.com/KiCad/kicad-source-mirror/releases)
- kicad-cli covers ERC, DRC, and all fab and 3D exports — [KiCad docs: CLI](https://docs.kicad.org/10.0/en/cli/cli.html)
- IPC API and kicad-python are the forward path; SWIG is deprecated — [KiCad dev docs](https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/)
- Eagle access ended June 7, 2026 — [Autodesk](https://www.autodesk.com/products/fusion-360/blog/eagle-to-autodesk-fusion-transition/)
- EasyEDA Pro format is ZIP plus JSON Lines with a browser-runtime API — [KiCad dev docs: EasyEDA format](https://dev-docs.kicad.org/en/import-formats/easyeda/index.html); [EasyEDA Pro API](https://prodocs.easyeda.com/en/api/reference/pro-api.html)
- Aisler supports KiCad 10 files directly — [Aisler community](https://community.aisler.net/t/kicad-10-is-live-and-100-supported-by-aisler/5567)

### Inferences
Comparison matrix for an AI-assisted workflow (synthesized from the findings above):

| Tool | Text format an AI can edit | Headless CLI (ERC/DRC/fab) | JLC/LCSC integration | STEP for enclosure | AI/MCP ecosystem | Status, Nov 2026 | Verdict |
|---|---|---|---|---|---|---|---|
| **KiCad 10** | Yes (S-expressions) | Yes (kicad-cli, JSON, exit codes, jobsets) | Plugins plus easyeda2kicad | Excellent (STEP-only libs, CLI export) | Multiple MCP servers; IPC API | Active, free | **Recommended** |
| EasyEDA Pro | Partially (.epro = zip + JSONL) | No | Native, best-in-class | Not assessed here | Browser extension API; "api-skill" repo (unverified) | Active, free | Not recommended for an AI workflow |
| Eagle | XML (historic) | Limited | Via ULPs | n/a | None | **EOL June 2026** | Retire |
| Fusion Electronics | Proprietary cloud | Limited / not assessed | Via libraries | Native MCAD | Not assessed | Active, subscription | Only if already in Fusion |
| atopile (+ KiCad) | Yes (.ato) | Yes (`ato build`), then KiCad | Parametric picking (supplier not confirmed on page) | Via KiCad | CLAUDE.md/AGENTS.md in repo | Active, OSS; WSL on Windows | Optional front end |
| tscircuit | Yes (TSX) | Yes (npm toolchain) | Not verified | Not verified | AI-first positioning | Active, OSS, less proven | Experimental |

### Gaps
- No head-to-head hands-on comparison of Claude-driven KiCad MCP servers was found. Recommend a quick trial of one server (Konnect-EDA or kicad-claude-mcp) against plain file editing plus kicad-cli before committing.
