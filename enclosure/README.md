# airQ v3 enclosures

Parametric SolidCraft designs for the airQ and airQ mini enclosures (Plan 3,
`docs/superpowers/plans/2026-11-25-airq-v3-3-enclosure.md`), and the reference parts they are
checked against. The source is Python: generators under `src/` emit SolidCraft command scripts,
and `build.py` runs them to write the `.sc` designs. Open a `.sc` file in SolidCraft (0.48 or
later) to look at it. Every size is a named parameter in its Parameters table, and each
parameter's comment gives its source.

Contents:

- [Files](#files)
- [Building](#building)
- [Reference parts](#reference-parts)
- [Frames](#frames)
- [Using the references in an enclosure design](#using-the-references-in-an-enclosure-design)
- [Printing the coupons](#printing-the-coupons)
- [Coupon results](#coupon-results)
- [Sources](#sources)
- [To confirm](#to-confirm)

Later tasks add their own sections: the layout study and check table (Tasks 3 and 4), and the
print and assembly guide (Task 5). The print-test coupons (Task 2) are below.

## Files

| Path | What |
|---|---|
| `build.py` | Builds designs: `uv run --with pyyaml python enclosure/build.py <design>... \| all` |
| `src/sclib.py` | Shared generator helpers: parameters, named features, dof-0 sketches, configurations |
| `src/encbuild.py` | The design registry (`DESIGNS`) and the build: script, `solidcraft-cli run`, save, checks |
| `src/ref_*.py` | One generator per reference part (`ref_pcb.py` wraps the board STEP files) |
| `src/coupons.py` | The print-test coupons' generator |
| `coupons.sc` | The coupons design, built from `src/coupons.py` (committed) |
| `export/` | Printable exports (`coupons.3mf`, `coupons.step`), written by `build.py` (committed) |
| `reference/*.sc` | The reference designs, built from the generators (committed) |
| `.build/` | Generated scripts, run results and anything not committed (gitignored) |

## Building

```
uv run --with pyyaml python enclosure/build.py all          # every design
uv run --with pyyaml python enclosure/build.py sen66 epd-2.9
uv run --with pyyaml python enclosure/build.py --list
uv run --with pytest --with pyyaml pytest tests/enclosure   # the checks
```

`build.py` needs `solidcraft-cli`. It looks on `PATH`, then in `C:\Program Files\SolidCraft\`. Set
`SOLIDCRAFT_CLI` to use another copy. For each design it does the following:

1. Calls the generator. This is pure Python: the generator reads `hardware/interface.yaml` for
   anything recorded there and returns the command list. That is the same list an MCP `batch`
   call takes.
2. Writes the list to `.build/<design>.json` and runs it with `solidcraft-cli run`.
3. Saves the design to `.build/reference/` without SolidCraft's model cache. The cache records
   timings, so leaving it in would make every save differ.
4. Fails if any sketch is above dof 0.
5. Copies the file to its place (`reference/...` or `enclosure/`) if it is at most 5 MB and its
   contents changed (ruling R8). A larger design stays in `.build/`, and `build.py` says so.
6. Writes the design's exports, if its module has an `EXPORTS` list, into `.build/export/` through
   `solidcraft-cli run --out` (meshes at `EXPORT_QUALITY`, a chord of 2e-4 of each body's size).
   A `.3mf` is reopened with `solidcraft-cli eval`, and the build fails unless it holds one part
   per body of the design. Each export is copied to `export/` when its bytes changed. The same
   input gives the same bytes. Task 5 reuses this for every printed part: list its files in
   `EXPORTS` (for example `["export/airq-shell.3mf", "export/airq-shell.step"]`).

An unchanged design leaves the committed file untouched. When comparing builds, the random
identities SolidCraft gives configuration rows are ignored.

The tests in `tests/enclosure/` come in two groups:

- **Fast tests** (always run, CI included):
  - names, parameters and every size being a parameter expression;
  - the values read from `interface.yaml`;
  - the committed `.sc` files matching the generators. `document.json` is read straight from
    the zip container: parameters, and feature names and ids;
  - the boards' embedded STEP copies matching `hardware/step/`;
  - the 5 MB limit.
- **SolidCraft tests** (skipped where `solidcraft-cli` is missing, as in CI):
  - each bounding box against its datasheet, within 0.1 mm;
  - the EPD tail fold;
  - insertion as components;
  - committed designs being identical to a fresh build.

To see `.sc` changes as text in `git diff`, run
`git config diff.solidcraft.textconv "solidcraft-cli textconv"`. `.gitattributes` already routes
`*.sc` through that driver.

**Writing a generator.** Follow `ref_sen66.py`, and check the result with the `solidcraft-modeling`
and `solidcraft-checking` skills. The rules are these:

- **Parameters.** Every size is `Script.param(name, value, comment)`, where the comment gives the
  source. Feature fields and sketch points are expressions over the parameters. Edge picks
  (plain numbers) are the only exception.
- **Names.** Every feature, sketch and body is named.
- **Sketches.** Closed polylines and circles, with points given as expressions, solve at dof 0
  without dimensions.
- **Feature ids.** `Script` counts feature ids as SolidCraft assigns them, and
  `Script.configuration` uses them in its rules.
- **Registry.** Add the module to `encbuild.DESIGNS`.

## Reference parts

The sizes below are bounding boxes measured on the built designs. Each one matches its source
within 0.1 mm (`tests/enclosure/test_enclosure_designs.py`).

| Component | File | Bodies | Size (mm) | Source |
|---|---|---|---|---|
| `ref_sen66` | `reference/sen66.sc` | `sen66_body`, `sen66_inlet` (both inlets, one body of two pieces), `sen66_outlet` | 55.2 × 25.6 × 21.3 | Sensirion SEN6x datasheet v1.0, Fig. 8; inlet/outlet roles from the mechanical guide v0.9, Fig. 1 |
| `ref_epd` | `reference/epd-2.9.sc` | `epd_panel`, `epd_active_area`, `epd_tail_block`; tail flat: `epd_tail`, `epd_tail_stiffener`, `epd_tail_contacts`; tail folded: `epd_tail_folded`, `epd_tail_folded_stiffener`, `epd_tail_folded_contacts` | panel 79.0 × 36.7 × 1.2; with the flat tail 93.4 × 36.7 × 1.2; folded −4.6 … 79.0 × 36.7, z −1.55 … 1.2 | GoodDisplay GDEY029T94 spec Rev 1.0 §4 via `interface.yaml` `panel_tail`; Waveshare 2.9" V2 spec Rev 2.1 §1.3–1.4 |
| `ref_sfa40` | `reference/sfa40-breakout.sc` | `sfa40_board`, `sfa40_sensor`, `sfa40_opening`, `sfa40_qwiic_j1`, `sfa40_qwiic_j2` | 25.4 × 25.4 × 4.5 | SparkFun SEN-31669 layout and drawing; Sensirion SFA40 datasheet v1.1, Fig. 6 |
| `ref_fpc_adapter` | `reference/fpc-adapter.sc` | `fpc_adapter_pcb`, `fpc_adapter_zif_tail`, `fpc_adapter_zif_ffc` | 20 × 12 × 3.0 | Placeholder (R6): every size to confirm |
| `ref_main` | `reference/airq-main.sc` (3.6 MB) | 308 bodies from the STEP, board `airq-main_PCB` | board 60 × 30 × 1.51; all parts x 0 … 60, y −30.33 … 5.99, z 0 … 5.85 | `hardware/step/airq-main.step`, unchanged |
| `ref_tongue` | `reference/airq-tongue.sc` (0.5 MB) | 19 bodies, board `airq-tongue_PCB` | board 22 × 13 × 1.51; all parts 22 × 13 × 4.6 | `hardware/step/airq-tongue.step`, unchanged |

**SEN66 ports.** These are the areas of the port faces, as drawn (datasheet Fig. 8):

| Port | Area |
|---|---|
| Square inlet | 7.0 × 7.0 = 49.0 mm² |
| Round inlet | ⌀6.0, 28.3 mm² |
| Both inlets | 77.3 mm² |
| Outlet | ⌀20.5 circle, fan hub and spokes included: 330.1 mm² |

Sensirion's mechanical guide v0.92/v1.01 asks for at least 56 mm² (inlets) and 148 mm² (outlet)
of opening for each channel. These figures come from search snippets of that document, which
could not be opened (to confirm). The 56 and 148 are probably the net slit areas. The grille rule
("open area ≥ 2× the port it serves") is met with margin if it is applied to the drawn areas
above.

**EPD tail.** The `tail_folded` parameter switches the tail between its two states:

- **0, flat**, as the drawing shows it. This is the airQ mini.
- **1, folded** 180° behind the panel. This is the airQ (`interface.yaml` `fpc.airq_fit`).
  - Only the 8.2 mm next to the glass bends: a flat run of `fold_out`, then a half turn of inner
    radius `fold_r`, then back under the panel.
  - The stiffened 6.2 mm end lies flat under the panel. Its stiffener faces the panel, and its
    contacts face away from it (−z), ready for the adapter's ZIF.
  - The bent part is modelled at the root's full 15.31 mm width, as an envelope of the root and
    the flare.

The configuration rows `flat` and `folded` set `tail_folded`, and configuration rules make the
parameter switch the features on its own. Pick a state with `parameters.change`, or with
`component.insert_design {configuration: "folded"}`.

## Frames

Enclosure designs (ruling R3, used from Task 3 on):

- x = 0 at the width centre, +x to the user's right;
- y = 0 at the shell's front bottom edge, +y toward the rear (SolidCraft's front view looks
  along +y);
- z = 0 at the shell's bottom plane, without the feet.

Each reference part keeps its own natural frame, below, and the enclosure designs place it.

- **`ref_sen66`** uses the datasheet's own datums, so every number is the drawing's.
  - x runs along the 55.2 length, from the inlet end (x = 0) to the outlet end.
  - y runs across the 25.6 width, from the long edge nearer the square inlet (y = 0).
  - z runs through the 21.3 height, from the port face (z = 0) to the connector face.
  - All three ports open in the z = 0 face and face −z: square inlet x 3.2–10.2, y 2.8–9.8;
    round inlet ⌀6 at (6.7, 18.2); outlet ⌀20.5 at (42.4, 12.8). The ports must never face up or
    down in an enclosure, so the part is placed with z horizontal.
  - The 2 mm plinth (inset 1.2) is on the connector face, z 19.3–21.3.
  - The cable connector is on the connector face. The datasheet (Fig. 9) does not dimension it:
    scaled, it sits at x ≈ 17–29 (to confirm).
- **`ref_epd`** is the drawing's front view with z out of the page.
  - x runs along the 79.0 length, x = 0 at the short end the tail leaves, +x away from it.
  - y runs across the 36.7 width, y = 0 at the pin-24 long edge, +y toward the pin-1 edge.
  - z = 0 at the panel's back, +z toward the viewer.
  - The tail leaves toward −x at z 0.6–0.7 (flat).
  - Active area: x 9.10–76.00, y 3.82–32.88. View area: 67.50 × 29.66, 2.70 from the far end and
    3.52 from each long edge (parameters `va_*`, for the window).
- **`ref_sfa40`** uses the PCB references' STEP frame.
  - Origin at the board's top-left corner as SparkFun's layout draws it. x = KiCad X − 123.266,
    y = −(KiCad Y − 85.406), z = 0 at the board's bottom face.
  - The board spans x 0…25.4 and y −25.4…0. Parts sit on z = 1.6.
  - Qwiic J2 is on the −x edge and J1 on the +x edge. The unfitted 4-pin header row is at the −y
    edge.
  - The sensor opening faces +z at z 3.99: x 9.75–13.55, y −16.3…−9.1.
- **`ref_fpc_adapter`**:
  - origin at the centre of the board's bottom face;
  - x across the board, y along the signal path. The panel tail enters ZIF `tail` from −y, and
    the FFC enters ZIF `ffc` from +y;
  - z up, connectors on top.
- **`ref_main`, `ref_tongue`** are the STEP files' own frames, as `interface.yaml`
  `mechanical.<board>.step` records:
  - STEP x = X, y = −Y, z = Z + 1.6 in the layout frame (origin at the board's top-left corner;
    +Y toward the main board's front edge or the tongue's Qwiic edge);
  - board bottom at z = 0, top face at z = 1.6, the dielectric body z 0 … 1.51;
  - main board x 0…60, y −30…0, with the antenna strip to y +5.99. Tongue x 0…22, y −13…0.

## Using the references in an enclosure design

Insert each reference with `component.insert_design {path, configuration?, translate | matrix}`.
The component is named after the design (`ref_sen66`, …).

- **Link paths.** The link is stored relative to the host file.
- **Panel tail.** For the panel, pass `configuration: "folded"` (airQ) or `"flat"` (mini).
- **Inlet bodies.** An inserted copy splits a body of two pieces in two. The round inlet appears
  as `sen66_inlet (2)`.
- **File size (R8).** The host design embeds the inserted bodies. Inserting `ref_main` adds about
  5.5 MB (its bodies, as a 24.7 MB STEP blob), which puts an enclosure design over the 5 MB
  limit. Insert it only for the check run, into a design under `.build/`. The other references
  add a few kB each.
- **Rebuild after re-export.** The board designs embed the STEP files as git stores them (LF line
  endings). Re-run `build.py airq-main airq-tongue` after re-exporting `hardware/step/`; a test
  fails until you do.

## Printing the coupons

Print these before any enclosure. Their results set the clearance defaults the enclosures use
(`clr_align`, `clr_remove`, `clr_snap`, `slot_w`, `flex_*`), so the coupons are built to test the
fits the enclosures need (ruling R20). `export/coupons.3mf` holds every coupon as its own part (8
parts); `export/coupons.step` holds the same bodies. They are laid out flat on one 109.5 x 96.2 mm
sheet, spaced 6 mm apart, so print them together or drag them apart in the slicer. Solid, they come
to about 17 cm3 (about 21 g of PETG), less with infill.

**Material and settings.**

- Print in the material the enclosures will use: ASA if the printer is enclosed, PETG otherwise,
  on textured PEI, with the nozzle, layer height, walls and XY-compensation settings you will use
  for the enclosures. Change nothing between the coupons and the enclosures, or the results do not
  carry over. A 0.4 mm nozzle and 0.2 mm layers are assumed.
- No supports, no brim, no raft. Every coupon prints without supports in the orientation below.
- Colour: the shell's colour (warm white) for everything except the two clear bars.

| Part (3MF object) | Size (mm) | Orientation | Material |
|---|---|---|---|
| `coupon_clr_pegs` | 66 x 28 x 8 | as laid out: plate on the bed, pegs and tabs up | shell material |
| `coupon_clr_holes` | 66 x 28 x 3 | as laid out: plate on the bed, labels up | shell material |
| `coupon_grille` | 37.5 x 40 x 1.8 | **face down** on the textured PEI (the plate is flat on the bed; labels on top) | shell material |
| `coupon_insert` | 30 x 15 x 7 | as laid out: plate on the bed, bosses up | shell material |
| `coupon_flexure` | 44 x 11.3 x 4.9 | as laid out: standing on the bed, beams vertical. Print the beams with perimeters only (no infill reaches a 1 mm wall) | shell material |
| `coupon_lg_body` | 19.1 x 11.2 x 3.2 | as laid out: slots and pocket open upward | **opaque**: the shell's colour |
| `coupon_lg_bar_lit`, `coupon_lg_bar_dark` | 16 x 3 x 2 each | as laid out: lying on the 3 mm face | **clear or natural PETG** |

For a two-material or AMS print, assign the two bars to the clear filament and everything else to
the shell filament. On a single-material printer, print the two bars on their own (a second job in
clear PETG) and the rest in the shell material. The bars lie beside the body as they print: after
printing, drop one bar in each slot.

**What each coupon tests, and what to report.** The debossed number on each feature is its value in
mm. On the fit plates it is the per-side clearance, so a hole or slot is the peg or tab plus twice
that number.

| Coupon | What to do | Report |
|---|---|---|
| Clearance (pegs and holes, tabs and slots) | Push peg *n* into hole *n* and tab *n* into slot *n*, for each of 0.10, 0.15, 0.20, 0.25, 0.30. Round fits and rectangular fits are separate tests | For each fit type and each clearance: does not enter / enters only with force or a tool / enters by hand and holds without play / slides in and out freely / rattles. Name the tightest clearance that assembles by hand and the tightest that slides freely and releases without scraping, for each type. These pick `clr_align` (located part), `clr_remove` (part that lifts off) and `clr_snap` (latch) |
| Grille (3 slots at 1.0, 1.2, 1.5 mm; the back row are 45-degree louvres labelled L) | Look through the slots against a light, and probe each with a 1 mm feeler or a drill bit | Which widths print clean and open (no strings, no bridging, no closed slot), for straight and for louvre slots, and whether the louvres' overhang flank droops. Picks `slot_w` |
| Insert boss (M2 heat-set insert holes 3.1, 3.2, 3.3 mm, 4.0 deep; **sizes to confirm** with your inserts) | Heat in an M2 insert in each boss from its top (the enclosures enter it from underneath) with the iron you will use. Then turn an M2 screw in and out and try to pull the insert out | Which hole holds: insert seats flush, does not spin under a screwdriver, does not pull out by hand, and the boss neither cracks nor bulges. Note the insert length and brand |
| Button flexure (A with a stand-in for SW1, B without) | Press the pad's outer face (the face away from the board stub) with a fingertip, toward the stub. A: the pad closes up on the stand-in's actuator stub after 0.10 mm. B: the pad moves freely until the lug on its stop side meets the stop block, after 0.30 mm | Whether the pad returns fully after 50 presses and stays uncracked, whether it bottoms on the hard stop (B) and cannot press the stub any further (A), the feel and rough force, and the rest gap you can see at A. The stand-in is rigid, so the switch's own click cannot be felt: if you have a spare SKRTLAE010, hold it against the stub's position to judge the click (optional). Picks `flex_t`, `flex_gap` and the `flex_*` family |
| Light guide (3 x 2 mm clear bar, SK6812SIDE pocket, 1.2 mm opaque divider, a second bar past the divider) | Drop one bar in each slot, put an SK6812SIDE (or a phone torch held against the pocket) at the pocket end, and look at both bars in a dim room | Whether the lit bar glows evenly and the dark bar stays dark (light leaking past the divider, through the floor or through the top), with the shell colour and material you printed the body in. If it leaks, reprint the body in black and say so |

## Coupon results

**Pending owner print.** Nothing below has been measured. The plan's defaults stay in force until
the owner prints the coupons and reports: `clr_align` 0.15, `clr_remove` 0.20, `clr_snap` 0.25,
`slot_w` 1.2, `flex_*` as in `src/coupons.py`. When results arrive (Task 2 Step 3), fill the table
and change the defaults in `src/coupons.py` (and in the enclosure generators that read them),
rebuild and commit with `feat(enclosure): print-test coupons and results`.

| Test | Result | Decision | Default until then |
|---|---|---|---|
| Round peg and hole, 0.10 / 0.15 / 0.20 / 0.25 / 0.30 | pending owner print | tightest by hand: ?; tightest free: ? | `clr_align` 0.15, `clr_remove` 0.20, `clr_snap` 0.25 |
| Rectangular tab and slot, 0.10 / 0.15 / 0.20 / 0.25 / 0.30 | pending owner print | tightest by hand: ?; tightest free: ? | as above |
| Grille slots 1.0 / 1.2 / 1.5, straight | pending owner print | clean widths: ? | `slot_w` 1.2 |
| Grille 45-degree louvres 1.0 / 1.2 / 1.5 | pending owner print | clean widths: ?; flank droop: ? | `slot_w` 1.2 |
| M2 heat-set insert hole 3.1 / 3.2 / 3.3, 4.0 deep | pending owner print | holding hole: ? (insert: ?) | to confirm with the owner's inserts (R20) |
| Button flexure A (SW1 stand-in) | pending owner print | returns / cracks: ?; rest gap: ? | `flex_t` 1.0, `flex_gap` 0.10 |
| Button flexure B (hard stop) | pending owner print | bottoms at 0.30: ?; feel and force: ? | `flex_stop` 0.30 (gap + 0.20 travel) |
| Light guide, divider 1.2 | pending owner print | leak past the divider: ? | `divider` 1.2 |

## Sources

Every dimension comes from these documents; none of them is committed (R5).

| Part | Document | Where |
|---|---|---|
| SEN66 outline, ports | Sensirion, *SEN6x – Datasheet*, Version 1.0, October 2026 (read from the copy Digi-Key hosts; sensirion.com refused automated reads) | §5.1 "Package Outline", Figure 8, p. 56: 55.2 +0.2/−0.4 × 25.6 +0.1/−0.2 × 21.3 ±0.5; block 19.3 ±0.3; plinth inset 1.2; corner radii R2.8 (2×) and R4.3 (2×); square 3.2/10.2 × 2.8/9.8 (±0.1); ⌀6 ±0.2 at (6.7, 18.2); ⌀20.5 ±0.3 at (42.4 ±0.3, 12.8 ±0.2). Connector on the far face: §3, Table 16, and §5.2, Figure 9, p. 57 |
| SEN66 inlet/outlet roles | Sensirion, *SEN6x – Mechanical Design and Assembly Guidelines*, Version 0.9, December 2024 (LaskaKit's copy) | §1, Figure 1 "SEN6x package overview", p. 2: the square and round openings are the inlets, the fan grille the outlet; Figure 11, p. 10 (keep-clear areas) |
| SEN66 minimum opening areas | Same guide, Version 0.92 (January 2026) / 1.01 (July 2026), §2.1 "Coupling to Ambient" | A_in ≥ 56 mm², A_out ≥ 148 mm²: seen only in search snippets, to confirm |
| E-paper tail | GoodDisplay, *GDEY029T94 Product Specifications*, Rev 1.0 (2021/03/15), §4 "Mechanical Drawing of EPD module", p. 7 | Read into `hardware/interface.yaml` `mechanical.main.fpc.panel_tail` (Plan 2) and read from there: 14.40, 12.50, offset 0.60, root 15.31 from 11.98, gaps 10.97/10.42, contacts 24 × 0.5 × 3.66, stiffener 6.20 |
| E-paper outline, active area, thicknesses | Waveshare, *2.9inch e-Paper V2 Specification*, Rev 2.1 (2020/02/10), the same GoodDisplay panel and drawing | §1.3 "Mechanical Specifications", p. 4: 36.7 × 79.0 × 1.2 (T). §1.4 drawing, p. 5: 79.00 × 36.70; A.A 66.90 × 29.06, 3.00 from the far end, 3.82 from each long edge; V.A 67.50 × 29.66 (2.70, 3.52); narrow part 9.56; side view: panel 1.1 ±0.1, FPC 0.10 ±0.03, 0.3 ±0.03 at the stiffener; FPC 0.6 above the back (scaled) |
| E-paper thickness, active area | GoodDisplay product page GDEY029T94 (good-display.com/product/389.html, read 2026-11-26) | "79x36.7x1.2", active area "66.896x29.056" |
| E-paper hatched block | GoodDisplay drawing as above, scaled (`hardware/README.md`, "E-ink FPC fit (airQ)") | ≈4.6 past the outline, ≈2.3–7.4 from the pin-1 edge |
| SFA40 breakout board | SparkFun, *Formaldehyde Sensor - SFA40 (Qwiic)*, SEN-31669: product page "Board Dimensions" drawing and its KiCad layout, github.com/sparkfun/SparkFun_Qwiic_Formaldehyde_Sensor_SFA40, `Hardware/…SFA40.kicad_pcb` at commit 181b793 (2026-09-22) | 25.4 × 25.4 × 1.6; holes ⌀3.1 at 2.54 from the edges; U3 at the centre, turned 90°; J1/J2 at x 20.64/4.76, y 12.70 (KiCad, from the top-left corner) |
| SFA40 sensor and opening | Sensirion, *SFA40 Datasheet*, Version 1.1, April 2026 | §4.2 "Package Outline", Figure 6, p. 14: PCB 13 ±0.3 × 10 ±0.3 × 0.8 ±0.2; cap 10.05 × 8.45 × 1.59 ±0.2; opening 7.2 ±0.3 × 3.8 ±0.3, 4.15 ±0.3 from the PCB edge on the marking side. Pin 1: §2.6, Figure 2 |
| Qwiic connector body | This repository: `interface.yaml` `mechanical.main.j_qwiic_tongue.body` (6.0 × 4.95, 2.9 high) and `hardware/kicad/lib/README.md` fix 12 | The same JST SM04B-SRSS-TB part |
| FPC adapter | None: the owner's description (R6), about 20 × 12 mm with a ZIF at each end; ZIF size as J7 (`interface.yaml` `mechanical.main.fpc`) | All to confirm |
| Boards | `hardware/step/airq-main.step`, `airq-tongue.step` (Plan 2) | Frames: `interface.yaml` `mechanical.*.step` |
| SW1 stand-in (flexure coupon) | This repository: `interface.yaml` `mechanical.main.button` (Alps SKRTLAE010: side push, actuator 2.0 wide, tip 0.24 beyond the edge, centre 1.7 above the board top; the comment gives the body, 4.5 x 3.4, 3.3 high), with 0.2 mm travel and 1.6 N from the same comment | The actuator's height (1.0) is a guess |
| SK6812SIDE (light-guide coupon) | Ruling R20 and `interface.yaml` `mechanical.main.leds` (light centre 1.0 above the board) | Body 4.0 x 1.6 x 2.0, light face 4.0 x 2.0 |

## To confirm

These values are parameters, so a correction is a parameter change and a rebuild.

**SEN66**

- The minimum opening areas, 56 and 148 mm² (search snippets only).
- The connector position on the connector face (Figure 9 is not dimensioned).
- The side recesses: not modelled, so the body is their envelope.

**E-paper**

- The thickness: 1.2 is the specification's figure, but the side view gives 1.1 ±0.1. The plan
  says 1.0.
- The FPC height above the panel back (`tail_z`, 0.6, scaled from the side view).
- The hatched block: its position, and its thickness, which is taken as the panel's.
- The folded tail's `fold_out` (0.5) and `fold_r` (1.0). Check both on a real panel and adapter.

**SFA40**

- Which way the opening is offset (1.05 mm toward J2). This is derived by matching the
  datasheet's pin-1 corner to SparkFun's pad 1.
- The Qwiic mating faces, 0.52 mm inside the board edges. This is derived from SparkFun's pads
  and the JST body.

**FPC adapter**

- Every size (placeholder).

**Coupons**

- The M2 insert hole sizes (3.1 / 3.2 / 3.3 mm, 4.0 deep) and boss (6.0 mm): confirm with the
  owner's inserts. The test is the coupon.
- The SW1 actuator's height (`sw_act_h`, 1.0) and the body size (4.5 x 3.4 x 3.3, from the
  `interface.yaml` comment: the STEP part is named L4.6-W3.4-H3.4).
- The beam stiffness: a 1.0 x 4.9 x 12 mm PETG cantilever is about 0.3 N at the 0.30 mm stop (E
  about 1.5 GPa, an estimate). The print decides `flex_t`.
- The hard stop's 0.30 mm gap, and `flex_gap` 0.10, are at the limit of what a 0.4 mm nozzle
  resolves, so judge them by the stop engaging, not by measuring.

**Main board**

- The STEP model's button actuator reaches y −30.33, but `interface.yaml` (Alps drawing) gives
  −30.24. That is 0.09 mm, within the 0.1 tolerance.
