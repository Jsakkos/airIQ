# airQ v3 KiCad parts library (`airq`)

Project library for the main board and the sense tongue.

| File | Contents |
|---|---|
| `airq.kicad_sym` | symbols (library nickname `airq`) |
| `airq.pretty/` | footprints (library nickname `airq`) |
| `airq.3dshapes/` | STEP models, referenced as `${KIPRJMOD}/../lib/airq.3dshapes/<name>.step`, so they resolve from both `hardware/kicad/main/` and `hardware/kicad/tongue/` |

The part numbers, library class and JLC Economic status of every placed part are in `hardware/bom/parts.csv`
(checked 2026-11-25; the `boards` column says which board uses each part).

## How it was made

Fetched on 2026-11-25 with easyeda2kicad 1.0.1, one LCSC number at a time, with a pause between parts
(EasyEDA answers HTTP 403 when it is hit too fast):

```
easyeda2kicad --full --lcsc_id=<LCSC> --output hardware/kicad/lib/airq
```

Then the hand fixes listed below were applied. Every footprint was opened with KiCad 10
(`kicad-cli fp export svg`, `kicad-cli sym export svg`), and a throwaway board holding all 19 footprints was
exported with `kicad-cli pcb export step` from a `main/` sibling folder: every model resolved, with no
missing-model warnings.

EasyEDA footprints keep JLC's placement orientation, which keeps the CPL rotations simple (Task 7).

## MCU and pressure sensor (ruling R22, owner-confirmed)

The spec pins the ESP32-C6-MINI-1-N4 (C5736265) and the BMP585 (C18184976). JLC lists both as **"Standard Only"**
for PCBA, so they would move the main-board order off the Economic tier. Ruling R22: on 2026-11-25 the
owner confirmed option A, so the board uses two Economic-eligible substitutes:

| Role | Confirmed (Economic) | Swap-back (Standard tier) |
|---|---|---|
| MCU | ESP32-C6-WROOM-1-N8, C5366877: symbol `airq:ESP32-C6-WROOM-1-N8`, footprint `airq:WIRELM-SMD_ESP32-C6-WROOM-1` | ESP32-C6-MINI-1-N4, C5736265: stock `RF_Module:ESP32-C6-MINI-1` symbol and footprint (ruling R11; it carries Espressif's keep-out and a STEP model) |
| Pressure | MS5611-01BA03, C15639: `airq:MS561101BA03-50` / `airq:SENSORS-SMD_MS5611-01BA03` | BMP585, C18184976: `airq:BMP585_C18184976` / `airq:LGA-9_L3.3-W3.3-P1.10-TL`. Kept in this library but not hand-checked; check its pad map if R22 reverts |

To swap back (each part is one entry in the source: `U3` and `U4` in `hardware/src/main/mcu.yaml`):
- **MCU:** copy the stock `RF_Module:ESP32-C6-MINI-1` symbol into `airq.kicad_sym` and rename its pins 30 `RXD0` → `IO17` and
  31 `TXD0` → `IO16`, as was done for the WROOM (fix 7). `check_netlist` and the generator find MCU pins only by `IO<n>`/`GPIO<n>`
  names, and every other interface pin of that symbol is already named `IO<n>`. Its stacked GND pins are fine (the generator
  draws one marker for stacked pins that share a net). Keep the stock footprint `RF_Module:ESP32-C6-MINI-1`, but its antenna
  keep-out zone needs `tools/hw/gen_pcb.py` to support zones inside footprints (hardware/README.md, Limits), or the keep-out
  drawn on the board instead.
  In `U3`: change `symbol`, `footprint` and `lcsc`. Its pins are keyed by name (`GND`, `3V3`, `EN`, `IO8`, `IO12`, `IO13`, `NC`)
  and its GPIO signals come from `interface.yaml` (`Role: MCU`), so they carry over; delete the `IO10`/`IO11` lines (WROOM-only)
  and add `IO14: NC`.
- **Pressure sensor:** in `U4`, change `symbol` (`airq:BMP585_C18184976`), and write its pin map: SCX/SDX to `I2C_SCL`/`I2C_SDA`,
  VDD and VDDIO to `+3V3`, VSSIO/VSS to `GND`, CSB to `+3V3` (I²C), SDO to set the address, INT `NC`, pad 9 per the datasheet.
  Set its pin types and hand-check its pad map first (table below). Add a 100 nF for VDDIO.
- Then replace the two parts.csv lines.
Both substitutes expose the same interface nets: every GPIO in `interface.yaml` exists on the WROOM-1 (datasheet v1.4,
Table 3-1). The MS5611 answers at I²C 0x77 (CSB low) or 0x76 (CSB high), not the BMP585's 0x46. The contract and firmware now use
0x77 (`interface.yaml`, `pins.yaml`); the board ties CSB to GND.

## Parts in this library

| LCSC | MPN | Symbol | Footprint | STEP | Board |
|---|---|---|---|---|---|
| C5366877 | ESP32-C6-WROOM-1-N8 | ESP32-C6-WROOM-1-N8 | WIRELM-SMD_ESP32-C6-WROOM-1 | ESP32-S3-WROOM-1_standin-for-ESP32-C6-WROOM-1 (see fixes) | main |
| C15639 | MS561101BA03-50 | MS561101BA03-50 | SENSORS-SMD_MS5611-01BA03 | SENSORS-SMD_MS5611-01BA03 | main |
| C2765186 | TYPE-C 16PIN 2MD(073) | TYPE-C16PIN2MD | USB-C-SMD_TYPE-C-16PIN-2MD-073 | USB-C-SMD_TYPE-C-6PIN-2MD-073 (EasyEDA's file name; it is the 16-pin body) | main |
| C7519 | USBLC6-2SC6 (ST) | USBLC6-2SC6 | SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL | SOT-23-6_… | main |
| C90061 | TPS562201DDCR | TPS562201DDCR | SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BR | SOT-23-6_… | main |
| C98362 | WPN4020H3R3MT (3.3 µH) | WPN4020H3R3MT | IND-SMD_L4.0-W4.0_WPN4020H | IND-SMD_L4.0-W4.0_WPN4020H | main |
| C5378721 | SK6812SIDE-A | SK6812SIDE-A_C5378721 | LED-SMD_4P-L4.0-W1.6-L | LED-SMD_4P-L4.0-W1.6-L | main |
| C7484 | SN74AHCT1G125DBVR | SN74AHCT1G125DBVR | SOT-23-5_L3.0-W1.7-P0.95-LS2.8-BR | SOT-23-5_… | main |
| C133065 | SM06B-GHS-TB (JST GH 6) | SM06B-GHS-TB | CONN-TH_SM06B-GHS-TB-LF-SN (all SMD, despite the name) | CONN-SMD_GH1.25-WS-6P | main |
| C160404 | SM04B-SRSS-TB (JST SH 4, Qwiic) | SM04B-SRSS-TB | CONN-SMD_4P-P1.00_SM04B-SRSS-TB-LF-SN | CONN-SMD_SR1.00-WS-4P | main + tongue |
| C160403 | SM03B-SRSS-TB (JST SH 3) | SM03B-SRSS-TB | CONN-SMD_SM03B-SRSS-TB-LF-SN-P | CONN-SMD_SR1.00-WS-3P | main |
| C2856831 | FPC-05FB-24PH20 (XUNPU) | FPC-05FB-24PH20 | FPC-SMD_24P-P0.50_FPC-05FB-24PH20 | same name | main |
| C110293 | SKRTLAE010 (Alps) | SKRTLAE010 | KEY-SMD_SKRTLAE010 | KEY-SMD_L4.6-W3.4-H3.4 | main |
| C135276 | SMNR4030-470MT (47 µH, EPD boost) | SMNR4030-470MT | IND-SMD_L4.0-W4.0_SMNR4020 (4030 land pattern) | KiCad stock L_APV_ANR4030, 3.0 mm (fix 20) | main |
| C20917 | AO3400A (EPD Q1) | AO3400A | SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR | SOT-23-3P_… | main |
| C8598 | B5819W SL (EPD D1–D3) | B5819W_C8598 | SOD-123_L2.7-W1.6-LS3.7-RD-1 | SOD-123_… | main |
| C5221601 | SHT45-AD1B-R2 | SHT45-AD1B-R2 | DFN-4_L1.5-W1.5-P0.8-TL-EP (die pad removed, see fixes) | DFN-4_L1.5-W1.5-P0.8 | tongue |
| C504893 | VEML7700-TR | VEML7700-TR | LED-SMD_4P-L6.8-W2.4_VEML7700-TR | same name | tongue |
| C18184976 | BMP585 (swap-back only) | BMP585_C18184976 | LGA-9_L3.3-W3.3-P1.10-TL | same name | — |

**Stock KiCad 10 libraries** (ruling R11): the passives use `Resistor_SMD:R_0402_1005Metric` / `R_0603_1608Metric` and
`Capacitor_SMD:C_0402_1005Metric` / `C_0603_1608Metric` / `C_0805_2012Metric`, with the LCSC numbers in parts.csv
(C25744, C25900, C25905, C25779, C22935, C22939, C1525, C15849, C1779, C15850, C45783). The swap-back MCU uses `RF_Module:ESP32-C6-MINI-1`.

**VEML7700: -TR kept, not -TT** (ruling R25). Vishay's VEML7700 datasheet (doc. 84286, Rev. 1.5, 23-Mar-2021, Ordering
Information) lists VEML7700-TR as "Tape and reel, MOQ 2300, **Side view**" and VEML7700-TT as "Tape and reel, MOQ 2200,
**Top view**". It has separate "TAPING SIDE VIEW (-TR VERSION)" and "TAPING TOP VIEW (-TT VERSION)" drawings, and
separate proposed pad layouts (side view: 4 × 0.7 × 1.4 mm; top view: 4 × 0.7 × 1.6 mm). The EasyEDA footprints differ to match
(TR body 6.8 × 2.35 mm; TT body 6.8 × 3.0 mm with pad 1 at the opposite end). So -TT is a different mounting
orientation, not just different packaging. The plan wants the sensor looking out of the front edge, which is the side-view -TR.
Its stock is only 308 (enough for 10 boards plus attrition).

## Hand fixes applied after the fetch

1. **STEP models**: every footprint's `(model …)` points to `${KIPRJMOD}/../lib/airq.3dshapes/<name>.step` (EasyEDA wrote
   a working-directory-relative `.wrl` path). The unreferenced `.wrl` files were deleted.
2. **ESP32-C6-WROOM-1 EPAD vias**: the footprint had 12 unnumbered plated holes (0.3 mm drill, 0.5 mm pad) in the EPAD
   ("Via for thermal pad" in the datasheet's Figure 11-1). They are now pad `29` (the EPAD/GND pin, like the 9 EPAD sub-pads 29–37),
   copper only, with no paste and no mask opening. DRC and the netlist now see them as GND. (Copper 0.6 mm since fix 16.)
3. **ESP32-C6-WROOM-1 3D body**: EasyEDA has no model for C5366877. The footprint uses a copy of KiCad 10's stock
   `RF_Module.3dshapes/ESP32-S3-WROOM-1.step` as a mechanical stand-in, saved as
   `ESP32-S3-WROOM-1_standin-for-ESP32-C6-WROOM-1.step`. Its body measures 18.0 × 25.5 × 3.1 mm (STEP extents),
   the same as the C6-WROOM-1 datasheet's 18 ± 0.2 × 25.5 ± 0.2 × 3.1 ± 0.15 mm (Figure 10-1).
   It is placed with offset (0, +2.99, 0) mm: the module's top edge is at footprint y = −15.74 and the body is 25.5 mm long, so its centre
   is 2.99 mm above the footprint origin. A `kicad-cli pcb render` of a test board confirmed that the body sits on the
   pads and silkscreen outline. It is a stand-in only: the S3 body has an extra row of castellations along the
   bottom edge that the C6 module does not have. The model is from the KiCad library (CC BY-SA 4.0 with the KiCad libraries exception).
4. **Locating pegs → non-plated**: the USB-C's 2 pegs (0.70 mm) and the SKRTLAE010's 2 guide-boss holes (0.90 mm) were
   `thru_hole` with drill = pad size. They are now `np_thru_hole` (the Alps land pattern says "2-ø0.9 holes"; the
   SHOU HAN drawing shows ø0.65 pegs, and EasyEDA's 0.70 holes are kept).
5. **SHT45 land pattern**: the pads now follow Sensirion's recommended land pattern (SHT4x datasheet v3, April 2022, §5.3,
   Fig. 13): 4 pads 0.5 × 0.3 mm, 0.8 mm pitch, 1.3 mm between pad centres. The EasyEDA **die pad (pad 5) was removed**: Sensirion
   "recommends to not solder the central die pad" and says "there shall be no copper under the sensor other than at the pin pads".
   Symbol pin 5 was removed with it.
6. **USBLC6-2SC6 symbol pin names**: EasyEDA had named the pins "1"–"6". They now read I/O1, GND, I/O2, I/O2, VBUS, I/O1
   (ST datasheet, Figure 1).
7. **ESP32-C6-WROOM-1 UART pin names**: pin 24 was `RXD0` and is now `IO17`; pin 25 was `TXD0` and is now `IO16`. Per datasheet v1.4 Table 3-1, pin 24 = U0RXD/GPIO17
   and pin 25 = U0TXD/GPIO16. `tools/hw/check_netlist.py` maps MCU pins to GPIOs only through `IO<n>`/`GPIO<n>` names, and
   `interface.yaml` routes AUX_UART_TX/RX to GPIO16/GPIO17. Every MCU pin carrying an interface signal is now named `IO<n>`:
   IO2 (27), IO6 (6), IO7 (7), IO9 (15), IO12 (13), IO13 (14), IO16 (25), IO17 (24), IO18–IO23 (16–21).
8. **`LCSC` field**: easyeda2kicad names the property `LCSC Part`. It is renamed to `LCSC` in every symbol and footprint, so that
   the schematic BOM has a single LCSC column, shared with the stock passives that get an `LCSC` field in Task 4.
9. **Footprint type (`attr`)**: `CONN-TH_SM06B-GHS-TB-LF-SN` (J_SEN66) was `through_hole` although all 8 pads are SMD. It is now
   `smd`, so it appears in the SMD placement/CPL export. The others were audited:
   - all footprints with only SMD pads are `smd`, as are SKRTLAE010 (SMD plus non-plated holes) and the WROOM-1 (SMD plus EPAD thermal vias);
   - the USB-C (12 SMD pads plus 4 plated shell legs) is **deliberately kept `smd`**. JLC places C2765186 on the SMT line (its part page
     data: `assemblyMode = smtWeld`, PCBA type "Economic and Standard"), and an `smd` type keeps it in the CPL export.
     KiCad may raise a footprint-type mismatch warning for it, and for the WROOM-1's via pads. That warning is expected.

10. **Pin electrical types of the power sub-circuit symbols** (Task 2): easyeda2kicad writes every pin as
    `unspecified` (and the USBLC6's as `input`), so ERC could not check them and reported the USBLC6 I/O pins
    as undriven. They now follow KiCad 10's stock symbols for the same parts:
    - `TYPE-C16PIN2MD` as `Connector:USB_C_Receptacle_USB2.0_16P`: GND, VBUS and shell (13, 14) `passive`;
      CC, D+/D−, SBU `bidirectional`;
    - `USBLC6-2SC6` as `Power_Protection:USBLC6-2P6`: all six pins `passive`;
    - `TPS562201DDCR` as `Regulator_Switching:TPS562200` (same pinout): GND and VIN `power_in`, SW `output`,
      VFB and EN `input`, VBST `passive`;
    - `WPN4020H3R3MT`: both pins `passive`.

    - `SHT45-AD1B-R2` (Task 6) as `Sensor_Humidity:SHT4x`: SDA `bidirectional`, SCL `input`, VDD and
      VSS `power_in`;
    - `VEML7700-TR` (Task 6), the same way: SDA `bidirectional`, SCL `input`, VDD and GND `power_in`;
    - `SM04B-SRSS-TB` (Task 6): all six pins `passive`, like KiCad's stock connectors.

    - Task 4, the rest of the main board, following KiCad's stock symbols for the same kind of part:
      `ESP32-C6-WROOM-1-N8` as `RF_Module:ESP32-C6-MINI-1` (GND pins 1, 28, 29 and 3V3 `power_in`, the stacked
      EPAD pins 30–37 `passive`, EN `input`, IO pins `bidirectional`, pin 22 NC `no_connect`);
      `MS561101BA03-50` (VDD, GND `power_in`; PS, CSB, SCLK `input`; SDO `tri_state`; SDI/SDA `bidirectional`);
      `SK6812SIDE-A_C5378721` (DIN `input`, DOUT `output`, VDD and GND `power_in`);
      `SN74AHCT1G125DBVR` as `74xGxx:74AHCT1G125` (OE and A `input`, Y `tri_state`, VCC and GND `power_in`);
      `AO3400A` as `Transistor_FET:AO3400A` (G `input`, S and D `passive`); `B5819W_C8598`, `SMNR4030-470MT`,
      `SKRTLAE010` (pins 1–3 were `input`), `SM06B-GHS-TB`, `SM03B-SRSS-TB` and `FPC-05FB-24PH20`: all `passive`.

    Every symbol used on a board now has typed pins.

11. **Courtyards of the sense-tongue parts** (Task 6, before their first placement): EasyEDA drew them round
    the body only (the SHT45's was a triangle). They are now closed rectangles covering body and pads plus
    0.25 mm: `DFN-4_L1.5-W1.5-P0.8-TL-EP` ±1.15 × ±1.00, `LED-SMD_4P-L6.8-W2.4_VEML7700-TR` x ±3.65,
    y −2.10…+1.15, `CONN-SMD_4P-P1.00_SM04B-SRSS-TB-LF-SN` x ±3.65, y −2.97…+3.09 mm.
12. **3D model placement** (Task 6; the enclosure is built from the board STEP, so this matters). Measured
    from the STEP vertices against the pads:
    - `CONN-SMD_SR1.00-WS-4P.step` (SM04B) sat 1.5 mm to +x (the left fitting nail stood outside the body)
      and 0.385 mm to −y (rearward) of its pads. Model offset now (−1.500, −0.385, 0) (KiCad's offset Y
      points up the screen): the contact tails sit on the contact pads, and the body then matches KiCad's
      stock `JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal` model to within 0.04 mm (body front, the
      mating face, at footprint y +2.51; 2.9 mm high).
    - `LED-SMD_4P-L6.8-W2.4_VEML7700-TR.step` was centred on z = 0 (half of its 3.0 mm height below the
      board) and 0.45 mm to +y of the silkscreen body outline. Model offset now (0, +0.450, +1.491): the
      body sits on the board, fills the silk outline (y −1.85…+0.50), and its lead feet are centred on the pads.
13. **VEML7700 window direction, checked against the vector drawing** (Task 6): Vishay doc. 84286 Rev. 1.8
    p. 10 is drawn in first-angle projection (its projection symbol shows the end view of the cone's small
    end to the right). In the side view, placed right of the front view, the J-leads and their 1 mm feet
    are on the left edge, which is the back of the part. In the top view, placed below the front view, the
    lead tops sit in a recess along the top edge, which is also the back. So the leads are on the back and
    the sensitive face is the front, the side opposite the leads. In the footprint the pads stick out
    behind the body at +y, so the window faces footprint **−y**, as the "Pad maps" table says. The
    sensitive-area centre is 1.95 mm above the seating plane and centred along the 6.8 mm length
    (application note 84323, Fig. 19); the half-sensitivity angle is about ±55°. Seen from the window,
    pin 1 is on the left, as in the datasheet photo.

14. **Reference prefixes** (Task 4): connectors are `J` (were `USB`, `CN`, `FPC` and `U` for the SM03B), the SK6812 `D`
    (was `LED`), the VEML7700 and the USBLC6 `U` (were `LED` and `D`). The schematic references come from the source
    anyway; this only changes what KiCad proposes when a part is placed by hand.
15. **ESP32-C6-WROOM-1 EPAD pins stacked** (Task 4): the 9 EPAD sub-pad pins 29–37 were drawn side by side on the
    symbol's top edge, which gave 9 crowded GND markers. They now sit on one point (pin 29 visible, 30–37 hidden and
    `passive`), as KiCad's stock module symbols do. The pad numbers and the footprint are unchanged.
16. **ESP32-C6-WROOM-1 EPAD thermal vias** (Task 4): pad `29`'s 12 via holes had 0.5 mm copper on a 0.3 mm drill, a
    0.10 mm annular ring, below the board's 0.15 mm minimum (`layout.yaml` rules), so DRC flagged each. Espressif's
    land pattern (datasheet v1.4, Figure 11-1) marks "Via for thermal pad" without dimensions, so they are now the board's
    own via, 0.6 mm on 0.3 mm (`Default` net class). They stay inside the EPAD copper, on GND.
17. **Courtyards of the main-board parts** (Task 5, before placement; as fix 11): EasyEDA drew them round the body
    only. Each is now a rectangle round body and pads plus 0.25 mm: WROOM-1 x ±9.75, y −16.00…10.10 (its pads stick
    out 0.5 mm past the body); USB-C x ±5.17, y −3.18…5.22; SOT-23-6 (TPS562201) ±2.15 × ±1.70; SOT-23-6 (USBLC6)
    ±1.70 × ±1.94; SOT-23-5 ±2.10 × ±1.70; SOT-23-3 ±1.75 × ±1.70; SOD-123 ±2.55 × ±1.10; MS5611 ±2.75 × ±2.30;
    SMNR4020 ±3.12 × ±2.25; WPN4020H ±2.60 × ±2.25; SK6812SIDE-A x ±2.55, y −0.86…1.61; FPC x ±8.55, y −2.47…4.13;
    SM06B x ±5.72, y −2.78…3.32; SM03B x ±3.30, y −2.97…3.19; SKRTLAE010 x ±2.83, y −2.13…2.30.
18. **SKRTLAE010 copper clear of its guide holes** (Task 5). Alps' land pattern (SKRT series basic information,
    "Land Dimensions", viewed from the mounting face; the EasyEDA footprint matches it) puts pads 1 and 3
    0.075 mm and the tabs 4 and 5 0.15 mm from the two ø0.9 mm guide-boss holes. JLCPCB's published minimum
    from a non-plated hole to copper is **0.2 mm** ("NPTH to Track: 0.2mm", jlcpcb.com/capabilities/pcb-capabilities,
    read 2026-11-25), so neither a relaxing DRC rule nor the vendor pattern as drawn is buildable as specified.
    Pads 1 and 3 are now custom pads with their hole-side corner cut by a chord ((±0.375, 0.323)–(±0.12, 0.9) in pad
    coordinates; 0.05 mm² of 1.35 mm² removed), and the tabs are 0.1 mm shorter on the hole side (0.8 × 1.3 mm at
    y 1.02). All copper is now ≥ 0.25 mm from the holes, KiCad's default hole clearance: no custom rule. The
    "prohibited area of copper tracks" between the tabs is a board rule area (`SW1_NO_COPPER`), as footprints here
    carry no zones.
19. **USB-C copper clear of its locating pegs** (Task 5). The vendor land pattern put the outer GND pads
    (A1B12/B1A12) 0.18 mm and the VBUS pads (A4B9/B4A9) 0.22 mm from the ø0.70 mm non-plated peg holes; Task 2 had
    allowed 0.15 mm with a footprint-scoped DRC rule. JLC's 0.2 mm NPTH-to-copper minimum (fix 18) rules that out,
    so the four pads are shortened at their inner (peg-side) end, A1B12/B1A12 by 0.07 mm (1.03 mm long) and
    A4B9/B4A9 by 0.04 mm (1.06 mm); their outer ends, where the contact tails are soldered, stay where the
    SHOU HAN drawing puts them. All copper is ≥ 0.25 mm from the pegs and the custom rule is gone.
20. **3D model placement of the main-board parts** (Task 5; the enclosure is built from the board STEP). Measured
    from the STEP vertices against the pads and silkscreen, then checked in the board's STEP export:
    - `USB-C-SMD_TYPE-C-6PIN-2MD-073.step` sat half below the board and 1.3 mm behind the mouth line: offset now
      (0, −1.305, 1.58). The shell is 8.94 × 7.35 × 3.16 mm (SHOU HAN drawing), mouth on the silkscreen front line,
      legs 1.0 mm below the body.
    - `LED-SMD_4P-L4.0-W1.6-L.step` (SK6812SIDE-A) was centred on z = 0 and on the pads: offset now (0, −0.56, 1.02),
      so the 4.0 × 1.6 × 2.0 body sits on the board with its light face on footprint y +1.36 (the silkscreen face).
    - `FPC-SMD_24P-P0.50_FPC-05FB-24PH20.step` sat 1.27 mm toward the mouth (its tails missed the pads): offset
      (0, 1.27, 0); the contacts now start on the pads and the mouth is the silkscreen front line (y +3.88).
    - `CONN-SMD_GH1.25-WS-6P.step` (SM06B, J_SEN66) had its origin on pin 1, as fix 12 found for the SM04B:
      offset (−3.125, 0, 0). `CONN-SMD_SR1.00-WS-3P.step` (SM03B): offset (−1.0, −0.385, 0), as the SM04B.
    - `SOD-123_L2.7-W1.6-LS3.7-RD-1.step` sat 0.6 mm below the board: offset (0, 0, 0.6).
    - L2 `IND-SMD_L4.0-W4.0_SMNR4020`: the SMNR4030-470MT is **3.0 mm** tall (Shun Xiang Nuo SMNR datasheet,
      dimension table: SMNR4030 A 4.0 ± 0.3, B 4.0 ± 0.3, C 3.0 max; land F 1.1, G 1.9, H 3.7, the same as the
      4020, so the pads stay). EasyEDA's model was the 2.0 mm 4020 body; the footprint now uses KiCad's stock
      `Inductor_SMD.3dshapes/L_APV_ANR4030.step` (4.0 × 4.0 × 3.0, a magnetic-resin-shielded 4030 like the SMNR).
21. **Silkscreen on the main board's edges** (Task 5): parts whose face is a board edge had silkscreen on or past
    it. Moved to F.Fab: the SK6812SIDE-A outline (its pin-1 dot stays), the FPC and USB-C mouth lines and the
    SKRTLAE010 actuator outline (their side lines are cut 0.5 mm short of the edge), the WROOM-1's antenna
    pattern and antenna-end outline (they hang over the board edge), the USB-C pin-1 dot (it sat on a shell leg).
    The SM06B's two short tab lines are cut back clear of the tab pads.
22. **USB-C shell legs soldered pin-in-paste** (final review): the four plated shell-leg slots (pads 13 and 14)
    were on `*.Cu *.Mask` only, so the stencil left them without paste, although JLC places C2765186 on its SMT
    line (fix 9). They now carry `F.Paste` too: an aperture the size of each pad (1.1 × 1.9 and 1.2 × 1.6 mm
    ovals), printed over the slot, so reflow solders the legs with the SMD pins. On the main board the "J1
    ground: solid to the pours" rule (`hardware/src/main/layout.yaml`) covers only J1's SMD ground pads; the legs
    keep thermal reliefs, so the pours do not sink the heat the paste in the slots needs.

## Pad maps checked by hand

Each check compares the footprint's pad numbers and positions (from the `.kicad_mod`) and the symbol's pin names with the manufacturer's document.

| Part | What was compared | Source | Result |
|---|---|---|---|
| ESP32-C6-WROOM-1 | Pin names 1–28 and EPAD; pad rows 17.5 mm apart, 1.27 mm pitch, pads 1.5 × 0.9 mm; pin 1 centre 7.49 mm from the antenna-end edge; EPAD centre 7.495 mm from the pin-1 side and 12.29 mm from the bottom edge; antenna strip 6.0 mm; numbering 1–14 down the left, 15–28 up the right | Espressif *ESP32-C6-WROOM-1 & WROOM-1U Datasheet* v1.4: Table 3-1, Fig. 10-1, Fig. 11-1 | **OK** (silkscreen body 25.58 mm vs 25.5 nominal) |
| MS5611-01BA03 | Pin table (1 VDD, 2 PS, 3 GND, 4 CSB, 5 CSB internal, 6 SDO, 7 SDI/SDA, 8 SCLK); top-view counter-clockwise numbering with a pin-1 mark; 1.25 mm pitch; pad rows | TE *MS5611-01BA03* datasheet 06/2017, pin configuration p. 15, recommended pad layout p. 16 | **OK**. The pads are 1.5 mm long on 2.6 mm centres vs the datasheet's 1.1 mm on 2.2 mm: same inner gap, longer outer toe. Kept, and noted. |
| SHT45-AD1B-R2 | Pins 1 SDA, 2 SCL, 3 VDD, 4 VSS; pin 1 top-left, counter-clockwise (transparent top view, Fig. 14); land pattern | Sensirion *SHT4x* datasheet v3, April 2022, §5.3–5.4 | **OK after fix 5** |
| VEML7700-TR | Pins 1 SCL, 2 VDD, 3 GND, 4 SDA; 1.27 mm pitch; pad 0.8 × 1.8 mm vs proposed 0.7 × 1.4 mm (side view); the sensitive face is on the side opposite the terminals' toe, i.e. toward footprint **−y**. Pin 1 is at footprint +x, so facing the window, pin 1 is on the left, as in the datasheet photo | Vishay doc. 84286 Rev. 1.4/1.5 p. 1 (pinning, photo) and p. 8 (package dimensions, proposed pad layouts) | **OK**. When placing it, the footprint's −y side faces the board edge. |
| USB-C (C2765186) | Pad names A1B12, A4B9, B8, A5, B7, A6, A7, B6, A8, B5, B4A9, B1A12 against the vendor's pin-assignment table; outer pads 6.40 apart, VBUS pads 4.80, signal pads 3.50, 0.5 mm pitch; shell legs 8.64 apart; pegs 5.78 apart | SHOU HAN *TYPE-C 16PIN 2MD(073)* drawing p. 1 (recommended PCB layout, pin assignments) | **OK**. A front/back mirror would only swap CC1↔CC2 and D+/D− pairs that are both used, so it would be harmless. |
| FPC-05FB-24PH20 | Insertion side and pin 1 (see below) | XUNPU series drawing *FPC 0.5PH H2.0 后翻双面接* (part FPC-05FB-NPH20; dimension table includes 24P) | **OK**, read from the series drawing; the 24-pin part's own PDF is corrupt |
| TPS562201DDCR | 1 GND, 2 SW, 3 VIN, 4 VFB, 5 EN, 6 VBST; counter-clockwise SOT-23-6, pin 6 opposite pin 1, pin-1 mark at pad 1 | TI SLVSD91D Table 4-1 / Fig. 4-1 | **OK** |
| SK6812SIDE-A | 1 DIN, 2 VDD, 3 DOUT, 4 GND; terminal widths 0.75 / 0.6 / 0.35 / 0.65 mm with 0.55 mm gaps match pads 1–4 (1.00 / 0.70 / 0.45 / 1.00 mm, same positions); the side view puts the terminals opposite the lens, so light leaves toward footprint **+y**; facing the light, DIN is on the left | OPSCO *SK6812SIDE-A-012* Rev. B/2 §4–5 | **OK**. Place the footprint's +y side toward the front edge. |
| SN74AHCT1G125DBVR | 1 OE, 2 A, 3 GND, 4 Y, 5 VCC; pin 5 opposite pin 1, pin 4 opposite pin 3 | TI SN74AHCT1G125 datasheet, DBV pinout | **OK** |
| USBLC6-2SC6 | 1 I/O1, 2 GND, 3 I/O2, 4 I/O2, 5 VBUS, 6 I/O1, counter-clockwise | ST USBLC6-2 datasheet, Fig. 1 | **OK** (names fixed, fix 6) |
| JST SM06B-GHS-TB | Circuit No. 1 is on the left in the side-entry front view (looking into the mating face). In the footprint the contact pads are at −y and the fitting tabs at +y (mating face toward +y); pad 1 at x = −3.13, i.e. on the left seen from the mating side; 1.25 mm pitch, A = 6.25 mm | JST *GH connector* catalogue p. 2 (shrouded header, side entry) and p. 1 (PC board layout) | **OK** |
| JST SM04B-SRSS-TB | Same check; pad 1 at x = −1.50; 1.0 mm pitch, A = 3.0 mm | JST *SH connector* catalogue p. 2 (shrouded header, side entry) | **OK** |
| JST SM03B-SRSS-TB | Same check; pad 1 at x = −1.00; A = 2.0 mm | JST *SH connector* catalogue p. 2 | **OK** |
| SKRTLAE010 (extra) | Pins 1 and 3 are common, 2 is the switched contact; 4 and 5 are mounting tabs; pad span 3.2 mm, holes 4.25 mm apart | Alps *SKRTLAE010* basic information, land dimensions and circuit diagram | **OK**. In the schematic, BUTTON goes to pin 2 and GND to pins 1 and 3; pins 4 and 5 are mechanical. Keep copper tracks out of the hatched area between the holes. |
| AO3400A | Symbol 1 G, 2 S, 3 D. Footprint: pads 1 and 2 on one side, pad 3 alone opposite, pin-1 mark at pad 1. Datasheet SOT23 top view: D alone on one side, G and S on the other, pin-1 dot at G, so G = 1, S = 2, D = 3 | Alpha & Omega *AO3400A* datasheet Rev 3 (Dec 2011), p. 1 SOT23 top/bottom view | **OK** |
| B5819W SL | Symbol pin 1 `-` = cathode (triangle apex and bar), pin 2 `+` = anode. Footprint pad 1 at −x, with the silkscreen cathode bar on the pad-1 side. Datasheet: SOD-123, "The marking bar indicates the cathode" | Jiangsu Changjiang (JCET) *B5817W–B5819W* SOD-123 datasheet, p. 1 | **OK** |

### FPC orientation (J_EPD, ruling R27)

- Panel (GDEY029T94 spec, drawing dated 2021/03/15): the FPC contacts are on the **display side**, with the stiffener on the back. The tail is 0.3 mm
  thick and 12.5 mm wide; with the display up and the tail pointing toward the connector, FPC pin 1 is on the right as seen from the panel. GoodDisplay's DESPI-C02 spec
  (Rev. 2.0, §3.2/§4.5) inserts the FPC display-side up into a "top or top/bottom contact" connector.
- Connector C2856831: XUNPU's series drawing (title "FPC 0.5PH H2.0 后翻双面接" = back-flip, double-sided contacts) shows
  the solder tails and the flip lid at the rear and the FPC entering from the front. The pin-1 mark ("A") is on the **right**, both in the top view
  (tails up) and in the front view looking into the mouth. The EasyEDA footprint matches: signal pads at y = −1.62, mounting
  pads and mouth toward +y, pad 1 at x = +5.75. The EasyEDA 3D model puts the black lid over the pad side.
- Result: with the panel FPC inserted **unfolded, display side up** (GoodDisplay's arrangement), FPC pin *i* lands on connector
  pin *i*, so the `J_EPD` order in `interface.yaml` maps 1:1. If the enclosure folds the FPC 180° behind the panel, the
  double-sided contacts still mate, but the pin order reverses (pin 1 ↔ 24). The schematic would then have to mirror the map.
- Source caveat: LCSC's PDF for C2856831 itself is corrupt (pdf.js: "Invalid or corrupted PDF file"). The check used the identical
  series drawing in the FPC-05FB-6PH20 (C2856827) datasheet, whose dimension table lists FPC-05FB-24PH20.
- Any route (final review): folds and twists turn the tail but never mirror it, so the order in J7 depends only on which face
  of the tail is up inside J7. Contacts (display side) up: pin *i* on pin *i*; contacts down: mirrored. The 180° fold above is
  one case: it leaves the contacts facing down.
- Panel tail (final review, GDEY029T94 spec section 4 drawing, p. 7): it leaves a short (36.7 mm) end of the panel, 14.40 mm long,
  12.50 mm wide, with a 6.20 mm stiffener; recorded in `hardware/interface.yaml` `mechanical.main.fpc.panel_tail`. In the airQ
  enclosure it does not reach J7, so it connects through an adapter and FFC (owner, 2026-11-26): `hardware/README.md`,
  "E-ink FPC fit (airQ)".

## Antenna keep-out (ESP32-C6-WROOM-1; applied in Task 5 as the board rule area `ANTENNA_KEEPOUT`)

From Espressif's *ESP32-C6 Hardware Design Guidelines*, "Positioning a Module on a Base Board", figure "Keepout Zone for
ESP32-C6 Module's Antenna (Antenna feed point on the right)", units mm:

- The 6.00 mm antenna strip at the module's end is the clearance area. It extends **at least 15 mm** past the module edge on the side away from
  the feed point, and **at most 2 mm** past the module edge on the feed-point side, where the board edge must be.
  The antenna end may sit **at most 1 mm** inside the board edge. No copper on any layer, no components, no traces in the clearance area.
- Preferred: the antenna strip overhangs the board edge (the guideline strongly recommends the antenna "outside the base board").
  Otherwise cut the board away beside and below the antenna. Put dense ground vias along the ground copper next to the clearance.
- In the end product, keep at least 15 mm clearance around the antenna in all directions inside the housing.
- On this module the feed point is on the **+x side** (pins 15–28): the EasyEDA antenna silkscreen's feed stub is at x ≈ +7.2…+7.6 mm.
  So the ≥ 15 mm extension goes toward −x (the pin 1–14 side). Check this against Espressif's module drawing when placing it.

## Open for owner review

Owner gate, 2026-11-25 ("Approve, option A"): both boards approved as laid out, with R22 confirmed (WROOM-1-N8 and MS5611),
the SKRTLAE010 and USB-C pad trims (fixes 18, 19), the SKRTLAE010 actuator direction and J7 at the front-edge centre. The FPC
contact side and pin 1 are verified for the unfolded, display-up insertion (R27 above). The final review then found that
the panel's tail does not reach J7 in the airQ enclosure; on 2026-11-26 the owner chose an adapter and FFC extension (option b,
no board change; `hardware/README.md`, "E-ink FPC fit (airQ)"), to be tested on the prototype before airQ boards are ordered
beyond the prototype round. Still open:

- **Side-emitting LED and side-looking VEML7700 directions** were derived from 2-D drawings: SK6812SIDE-A light toward footprint +y,
  VEML7700 window toward footprint −y (re-checked against the vector drawing in Task 6, fix 13). The EasyEDA 3D bodies have no
  visible lens, so the 3D viewer cannot show the window. Check against a physical part if one is at hand before the board is
  ordered (`hardware/README.md`, "Before each order").
- **Licence**: the EasyEDA-derived symbols, footprints and models come from the LCSC/EasyEDA library through easyeda2kicad.
  Their redistribution terms are EasyEDA's, not CC BY-SA; `hardware/LICENSE.md` ("Third-party content") states this. The owner
  should confirm that publishing them in a public repository is acceptable.
- **Library STEP size**: `airq.3dshapes/` holds about 34 MB of STEP text. Before the first push is the cheapest moment to switch
  to compressed `.stpZ` models.
- The WROOM-1 3D body is a stand-in (the S3-WROOM-1 body with the same outline). Good enough for the enclosure STEP, not for a
  photo-real render.
