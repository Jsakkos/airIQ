# Hardware licence

The contents of `hardware/` (schematics, PCB layouts, interface contract) and `enclosure/` (3D-printable enclosure files), except the
third-party content listed below, are licensed under the
[Creative Commons Attribution-ShareAlike 4.0 International licence (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/).

Legal code: <https://creativecommons.org/licenses/by-sa/4.0/legalcode>

Software in `firmware/` and `tools/` is covered by the MIT licence in the repository root.

## Third-party content

The CC BY-SA 4.0 grant above covers this project's own work. It does not relicense the third-party content
below, which keeps its own terms:

- **EasyEDA/LCSC library content.** In `hardware/kicad/lib/`, the symbols in `airq.kicad_sym`, the
  footprints in `airq.pretty/` and the STEP models in `airq.3dshapes/` (except the KiCad model named below)
  were fetched from the LCSC/EasyEDA component library with easyeda2kicad and then hand-edited
  (`hardware/kicad/lib/README.md`, "How it was made" and "Hand fixes applied after the fetch"). Their terms
  are EasyEDA's/LCSC's, not CC BY-SA 4.0. Copies of them are also embedded in the generated KiCad files in
  `hardware/kicad/main/` and `hardware/kicad/tongue/` (KiCad stores the symbols in each schematic and the
  footprints in each board) and in the board STEP models in `hardware/step/`.
- **KiCad library content.** `hardware/kicad/lib/airq.3dshapes/ESP32-S3-WROOM-1_standin-for-ESP32-C6-WROOM-1.step`
  is a copy of KiCad 10's `RF_Module.3dshapes/ESP32-S3-WROOM-1.step`. The generated KiCad files embed KiCad's
  stock symbols and footprints (for example `Device:R`, `power:GND`, `Resistor_SMD:R_0402_1005Metric`), and
  the board STEP models include that stand-in and KiCad's `Inductor_SMD.3dshapes/L_APV_ANR4030.step`. These
  are under the KiCad libraries' licence: CC BY-SA 4.0 with the KiCad libraries exception
  (<https://www.kicad.org/libraries/license/>).

Whether EasyEDA's terms allow this content to be redistributed in a public repository is an open question
for the project owner (`hardware/kicad/lib/README.md`, "Open for owner review"). This section only records
where each file comes from.
