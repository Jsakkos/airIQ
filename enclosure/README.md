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
- [Layout studies](#layout-studies)
- [airQ enclosure](#airq-enclosure)
- [airQ mini enclosure](#airq-mini-enclosure)
- [Print and assembly guide (airQ)](#print-and-assembly-guide-airq)
- [Print and assembly guide (airQ mini)](#print-and-assembly-guide-airq-mini)
- [Sources](#sources)
- [To confirm](#to-confirm)

The print and assembly guides (Task 5) are under "Print and assembly guide (airQ)" and "Print and
assembly guide (airQ mini)". The airQ mini (69.5 × 50 × 42, owner decision R51) is described under
"airQ mini enclosure". The print-test coupons (Task 2) are below.

## Files

| Path | What |
|---|---|
| `build.py` | Builds designs: `uv run --with pyyaml python enclosure/build.py <design>... \| all` |
| `src/sclib.py` | Shared generator helpers: parameters, named features, dof-0 sketches, configurations |
| `src/encbuild.py` | The design registry (`DESIGNS`) and the build: script, `solidcraft-cli run`, save, checks |
| `src/ref_*.py` | One generator per reference part (`ref_pcb.py` wraps the board STEP files) |
| `src/coupons.py` | The print-test coupons' generator |
| `src/enclosure_common.py` | Shared construction for both enclosures (shell, base plate, zone wall, cradle, gaskets, standoffs, tongue mount) |
| `src/airq.py` | The airQ enclosure's generator: `airq.sc` |
| `src/airq_check.py` | The airQ check design: every reference placed, cable keep-outs, air-path probes, the shell's sweep; interference, sections, gasket contact, distances |
| `src/board_sources.py` | Board positions read from their sources (R27): `interface.yaml` values and comment sizes, and `layout.yaml` placements with footprint courtyards (U2, U4) |
| `airq.sc` | The airQ enclosure design (committed) |
| `src/airq_mini.py` | The airQ mini's generator: `airq-mini.sc` (the airQ's construction, the sensor zone mirrored) |
| `src/airq_mini_face.py` | The airQ mini's face (Task 4b): the split light band (slots, two guides, ribs, `guide_stop`) and the labels |
| `src/airq_mini_check.py` | The airQ mini's check design, on `airq_check`'s helpers: references, keep-outs, probes, sweeps, passage slabs; the band's light checks (delivery trace, no path between the guides, R13, opaque paths) |
| `airq-mini.sc` | The airQ mini enclosure design (committed) |
| `src/layout_study.py` | The layout studies' section arithmetic for both models (pure Python; `tests/enclosure/test_layout_study.py`) |
| `coupons.sc` | The coupons design, built from `src/coupons.py` (committed) |
| `export/` | Printable exports, written by `build.py` (committed): `coupons.3mf` / `.step`, `airq-<part>.3mf` / `.step` for each printed airQ part and `airq-mini-<part>.3mf` / `.step` for each printed airQ mini part, in its print orientation |
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

A design with a `PRINT_PARTS` table (the airQ and the airQ mini) exports one file pair per printed part instead
(`encbuild.print_exports`): after the design is saved, each part is turned into its print orientation
and set on the bed, and written alone, so the saved design is not touched. The build fails unless each
3MF reopens with exactly one part. `tests/enclosure/test_airq_exports.py` (and `test_airq_mini_exports.py`) also
check every file's box and volume against the design's body. The file prefix comes from the module
(`airq-` or `airq-mini-`).

**Toolchain.** The committed designs were built with SolidCraft 0.50.0 (save format `solidcraft/69`)
and the tests that compare a fresh build with the committed files assume that toolchain: a different
SolidCraft can write different bytes for the same design (R38).

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
fits the enclosures need (ruling R20). `export/coupons.3mf` holds every coupon as its own part (9
parts); `export/coupons.step` holds the same bodies. They are laid out flat on one 124 x 116.5 mm
sheet, spaced 6 mm apart, so print them together or drag them apart in the slicer. Solid, they come
to about 19.5 cm3 (about 25 g of PETG), less with infill.

The defaults live in one place, `src/clearances.py` (`CLR_ALIGN`, `CLR_REMOVE`, `CLR_SNAP`,
`SLOT_W`, `WALL`, `FLEX_T`, `FLEX_LEN`, `FLEX_GAP`, and `add_params(script)`, which adds them as
commented parameters). The coupons import it, and so should the enclosure generators (Tasks 3-5),
so the results change the numbers once.

**Material and settings.**

- Print in the material the enclosures will use: ASA if the printer is enclosed, PETG otherwise,
  on textured PEI, with the nozzle, layer height, walls and XY-compensation settings you will use
  for the enclosures. Change nothing between the coupons and the enclosures, or the results do not
  carry over. A 0.4 mm nozzle and 0.2 mm layers are assumed.
- No supports, no brim, no raft. Every coupon prints without supports in the orientation below.
- Colour: the enclosure's own matte warm-white material for everything except the three clear bars.
  The light-guide test must use the real wall material and colour: the walls of the enclosures are
  that material, so a black coupon would say nothing about them.

| Part (3MF object) | Size (mm) | Orientation | Material |
|---|---|---|---|
| `coupon_clr_pegs` | 76 x 28 x 8 | as laid out: plate on the bed, pegs and tabs up | shell material |
| `coupon_clr_holes` | 76 x 28 x 3 | as laid out: plate on the bed, labels up | shell material |
| `coupon_grille` | 42 x 44 x 1.8 | **face down** on the textured PEI: the plate lies flat on the bed and the labels, on the top face, read normally from above (no mirroring) | shell material |
| `coupon_insert` | 30 x 17 x 7 | as laid out: plate on the bed, bosses up, holes opening upward (see "Insert orientation") | shell material |
| `coupon_flexure` | 44 x 13.3 x 4.9 | as laid out: standing on the bed, beams vertical. Print the beams with perimeters only (no infill reaches a 1 mm wall) | shell material |
| `coupon_lg_body` | 19.1 x 16.5 x 3.2 | as laid out: slots and pocket open upward | **the shell's warm-white material** |
| `coupon_lg_bar_lit`, `coupon_lg_bar_dark`, `coupon_lg_bar_dark_2` | 16 x 3 x 2 each | as laid out: lying on the 3 mm face | **clear or natural PETG** |

For a two-material or AMS print, assign the three bars to the clear filament and everything else to
the shell filament. On a single-material printer, print the bars on their own (a second job in
clear PETG) and the rest in the shell material. The bars lie beside the body as they print: after
printing, drop the lit bar in the middle slot and one dark bar in each outer slot.

**Reading the labels.** The labels are debossed 0.4 mm deep in a 5 mm capital height, which keeps
the strokes at the nozzle's width, and carry no units. They are a convenience: the order below is
the key, so the coupons stay usable if a label fills in.

| Coupon | Label | Order |
|---|---|---|
| Clearance plates | clearance per side in hundredths of a mm: 10 = 0.10 mm | left to right: 0.10, 0.15, 0.20, 0.25, 0.30. Back row (far from the labels): rectangular tabs and slots. Row nearest the labels: round pegs and holes. A hole or slot is the peg or tab plus twice the clearance |
| Grille | slot width in tenths of a mm: 10 = 1.0 mm; **L** = louvre | left to right: 1.0, 1.2, 1.5 mm. Front row (labels under the slots): straight slots. Back row (labels above): 45-degree louvres. Three slots per width |
| Insert bosses | hole diameter in tenths of a mm: 31 = 3.1 mm | left to right: 3.1, 3.2, 3.3 mm |
| Flexure | A, B | A (left) has the SW1 stand-in; B (right) is free |
| Light guide | none | slots, front to back: dark bar behind the 2.0 mm divider, lit bar, dark bar behind the 1.2 mm divider. Bars 1, 2, 3 in the 3MF are `coupon_lg_bar_lit`, `coupon_lg_bar_dark` (1.2 mm side), `coupon_lg_bar_dark_2` (2.0 mm side) |

"Front" is the edge at y = 0 (the bottom of the picture in a top view).

**What each coupon tests, and what to report.**

| Coupon | What to do | Report |
|---|---|---|
| Clearance (pegs and holes, tabs and slots) | Push peg *n* into hole *n* and tab *n* into slot *n*, for each of 0.10, 0.15, 0.20, 0.25, 0.30. Round fits and rectangular fits are separate tests | For each fit type and each clearance: does not enter / enters only with force or a tool / enters by hand and holds without play / slides in and out freely / rattles. Then the rule below |
| Grille (3 slots at 1.0, 1.2, 1.5 mm; the back row are 45-degree louvres labelled L) | Look through the slots against a light, and probe each with a 1 mm feeler or a drill bit | Which widths print clean and open (no strings, no bridging, no closed slot), for straight and for louvre slots, and whether the louvres' overhang flank droops. Picks `slot_w` |
| Insert boss (M2 heat-set insert holes 3.1, 3.2, 3.3 mm, 4.0 deep; **sizes to confirm** with your inserts) | Heat in an M2 insert in each boss from its top with the iron you will use. Then turn an M2 screw in and out and try to pull the insert out | Which hole holds: insert seats flush, does not spin under a screwdriver, does not pull out by hand, and the boss neither cracks nor bulges. Note the insert length and brand |
| Button flexure (A with a stand-in for SW1, B without) | Press the pad's outer face (the face away from the board stub) with a fingertip, toward the stub. A: the pad closes up on the stand-in's actuator stub after 0.10 mm. B: the pad moves freely until the lug on its stop side meets the stop block, after 0.30 mm | Whether the pad returns fully after 50 presses and stays uncracked, whether it bottoms on the hard stop (B) and cannot press the stub any further (A), the feel and rough force, and the rest gap you can see at A. The stand-in is rigid, so the switch's own click cannot be felt: if you have a spare SKRTLAE010, hold it against the stub's position to judge the click (optional). Picks `flex_t`, `flex_gap` and the `flex_*` family |
| Light guide (3 x 2 mm clear bar, SK6812SIDE pocket, opaque dividers of 1.2 mm on one side of the pocket and 2.0 mm on the other) | Drop the bars in, put an SK6812SIDE (or a phone torch held against the pocket) at the pocket end, and look at all three bars in a dim room | Whether the lit bar glows evenly, and whether each dark bar stays dark (light leaking past its divider, through the floor or through the top). If the 1.2 mm side leaks, say whether the 2.0 mm side stops it, and **the wall thickness that does**: Tasks 3-4 then use that thickness, or a dark liner, for the light-guide walls. Do not reprint in black: the enclosure walls are the warm-white material |

**Which orientation each result applies to.** Every fit plate, the grille and the insert plate print
flat, with their holes and slots along z (vertical). Round holes with their axis along z are the
most accurate holes a printer makes. The results for the round hole therefore apply to features
printed that way (base-plate bosses and pins). The shell prints face down on its tilted front, so
its holes and bosses are inclined to the bed, and holes along an inclined axis print slightly
smaller and rougher. The coupons do not test that: treat the `clr_*` and insert results as the
best case, check the first shell print (Task 5 Step 2), and widen the shell's holes if it needs it.

**Insert orientation.** The enclosures enter the heat-set inserts from underneath, into bosses
that stand on the shell's inner face. The coupon bosses stand on a plate with the hole opening
upward, which is the printing orientation of a base-plate boss. It says which hole diameter holds
the insert in a vertical hole. It does not say what an inclined shell boss needs: the result
applies to vertical bosses only, and the shell's bosses are confirmed by the first shell print.

## Coupon results

**Pending owner print.** Nothing below has been measured. The plan's defaults stay in force until
the owner prints the coupons and reports: `clr_align` 0.15, `clr_remove` 0.20, `clr_snap` 0.25,
`slot_w` 1.2, `flex_*` as in `src/clearances.py`. When results arrive (Task 2 Step 3), fill the
table and change the defaults in `src/clearances.py`, rebuild and commit with
`feat(enclosure): print-test coupons and results`.

**Rule for the three clearances.** Taken from the owner's answers, per fit type (round, rectangular),
using the larger of the two types:

- `clr_align` = the tightest clearance that assembles by hand and holds without play (a located part).
- `clr_remove` = the tightest clearance that slides in and out freely without scraping (a part that lifts off).
- `clr_snap` = `clr_remove` + 0.05 mm, until snap geometry is tested.

No snap or latch geometry is on the coupons, so `clr_snap` rests on a plain fit plus that margin. It
is not measured: test it with the first enclosure print.

| Test | Result | Decision | Default until then |
|---|---|---|---|
| Round peg and hole, 0.10 / 0.15 / 0.20 / 0.25 / 0.30 | pending owner print | tightest by hand: ?; tightest free: ? | `clr_align` 0.15, `clr_remove` 0.20, `clr_snap` 0.25 |
| Rectangular tab and slot, 0.10 / 0.15 / 0.20 / 0.25 / 0.30 | pending owner print | tightest by hand: ?; tightest free: ? | as above |
| Grille slots 1.0 / 1.2 / 1.5, straight | pending owner print | clean widths: ? | `slot_w` 1.2 |
| Grille 45-degree louvres 1.0 / 1.2 / 1.5 | pending owner print | clean widths: ?; flank droop: ? | `slot_w` 1.2 |
| M2 heat-set insert hole 3.1 / 3.2 / 3.3, 4.0 deep (vertical bosses only) | pending owner print | holding hole: ? (insert: ?) | to confirm with the owner's inserts (R20) |
| Button flexure A (SW1 stand-in) | pending owner print | returns / cracks: ?; rest gap: ? | `flex_t` 1.0, `flex_gap` 0.10 |
| Button flexure B (hard stop) | pending owner print | bottoms at 0.30: ?; feel and force: ? | `flex_stop` 0.30 (gap + 0.20 travel) |
| Light guide, 1.2 mm divider (shell material and colour) | pending owner print | leak: ? | `divider` 1.2 |
| Light guide, 2.0 mm divider (shell material and colour) | pending owner print | leak: ?; thickness that stops it: ? | `divider_thick` 2.0 |

## Layout studies

These are the layout studies (ruling R14) that every feature of the two enclosures is placed from.
- **Source.** The numbers come from `src/layout_study.py`, which is pure Python.
  `uv run --with pyyaml python enclosure/src/layout_study.py` prints them, and
  `tests/enclosure/test_layout_study.py` pins the conclusions.
- **Models.** Each model is a `Model` preset, `AIRQ` or `MINI`. A variant is written
  `dataclasses.replace(MINI, lip=15.5)`.

**Status (2026-11-26): the owner must decide both envelopes.** Ruling R22 (controller, 2026-11-26)
has chosen the lower-lip layout for both models: the airQ at 95 × 55 × 51 with a 15 mm lip, and the
mini with a 15.5 mm lip. It is the owner's to reverse. The other options below stay documented for
the owner. The airQ is built on R22's layout ("airQ enclosure" below).
- **airQ.** The main board, the SEN66 and the panel do not fit 95 × 55 × 48 mm (±1) when the
  whole front is sloped. The only poses within a few millimetres break the air and heat rules.
  The options are below.
- **airQ mini.** Superseded by "airQ mini (Task 4)" below: with the airQ's construction as built
  (SEN66 ports to the rear, the outlet plenum, the board's plugs) the mini is **blocked** at 66 × 50
  × 42; the smallest rule-keeping envelope found is 69.5 × 50 × 42. The addendum's first finding
  was that it fits only with R15's vertical lower lip (15.5 mm) and a horizontal board, with two
  figures short:
  - the antenna is about 5 mm from the SEN66 (R12 asks for 15);
  - the outlet grille has 442 mm² open (R18 asks for 660, with a floor of 296).

**How the numbers are found.** The main board is modelled as a rigid side section: the outline,
over all x, of its parts from `interface.yaml`.
- **Pose.** The section is tilted by α (front edge down) and placed by its front-bottom corner.
- **Constraints.** Each one is a half-plane, so every pose is an exact 2-D linear problem:
  - the rear wall (with a hood, the board's rear edge instead);
  - the top wall;
  - the front: behind the lip and the slope, behind the panel's back on the airQ, and behind
    the light guide in front of the LED faces and J7;
  - the SEN66 below the board, with the zone wall between.
- **Depth.** The smallest depth is found by bisection.

**Coordinates.**
- The enclosure frame is R3's.
- `lip` is the height of the vertical lower lip under the slope (0 = none).
- s is the distance up the slope from its bottom edge.
- t is the depth behind the slope's outer surface.
- f is the distance along the whole front from its bottom edge.

**Fixed inputs.**

| # | Item | Value | Source |
|---|---|---|---|
| 1 | Envelope | airQ 95 × 55 × 48, front 30°; mini at most 66 × 50 × 42, front 24° | plan, spec §5 |
| 2 | Margins | wall 1.8, floor 2.0, zone wall 1.8 with 0.3 air gaps, part-to-wall gaps 0.2 | plan, `src/clearances.py` |
| 3 | SEN66 | 55.2 (x) × 21.3 (y) × 25.6 (z) on 1 mm foam, so z 3.0 to 28.6. Behind it, 5 mm for the cable plug or the outlet plenum; in front, 3 mm for the inlet gasket | R17, `ref_sen66` |
| 4 | Zone rule | over the SEN66 the board's bottom is at least 28.6 + 0.3 + 1.8 + 0.3 = 31.0, and no part of the board is below the SEN66's top | global constraints |
| 5 | Tongue | 13 deep, lying in the intake air in front of the SEN66's ports, top at z 14.6 | `interface.yaml` tongue |
| 6 | Main board | 30 deep, plus the 6.0 antenna strip past the rear edge: 36.0. Parts up to 4.25; the LEDs and J7 on the front edge, 2.0 high | `interface.yaml` |
| 7 | airQ panel | 36.7 up the face, its back at t 2.2 (1.0 window lip + 1.2 panel). A 2.0 light guide between it and the LED faces | R16, R11, R20 |
| 8 | Mini front | no panel; 1.0 in front of the LED faces for the guides' entry and holder | plan Task 4 |
| 9 | USB-C | mouth on the rear edge; the plug's 7 mm overmold (to confirm) must pass through the rear wall | `interface.yaml` |

### airQ

**Board pose, whole front sloped.** For each tilt α (front edge down), the table gives the
smallest depth D at which the board fits. It uses the default margins; walls of 1.6 and gaps of
0.2 save 0.4 to 0.7 mm.

| α | Pose | D needed | Lowest board point (SEN66 top 28.6) | USB-C plug | SW1 and the dot | Antenna strip behind the panel |
|---|---|---|---|---|---|---|
| 0° | horizontal, above the SEN66 | 63.3 | 31.0, above | through the rear wall, z 34 | push axis 30° off the face normal: dot at s 39.6 | 28 mm |
| 10° | tilted | 62.2 | 29.5, above | rear, z 39 | 40°: dot at s 36.5 | 25 mm |
| 15° | tilted | 61.3 | 28.9, above | rear, z 42 | 45°: dot at s 35.0 | 23 mm |
| 20° | tilted | 60.3 | 28.6, level | through the top wall | 50°: dot at s 33.6 | 21 mm |
| 30° | tilted | 63.7 | 23.9, below | top | 60°: dot at s 25.3 | 16 mm |
| 45° | tilted | 62.1 | 17.2, below | top | 75°: no dot can press it | 9 mm |
| 55° | tilted | 58.8 | 13.8, below | top | 85°: none | 4 mm |
| 60° | parallel behind the panel | 56.9 | 12.5, below | top | along the face: none | 1.4 mm |

What the table says:

- **At 95 × 55 × 48 no pose fits.** Over the SEN66 the horizontal board's top face is at z 32.6,
  and its LEDs reach z 34.6. At that height the panel's back is already at y 22.5. With the 2 mm
  light guide in front of the LEDs, the front edge is at y 25.3 and the antenna end at y 61.3.
  That is 8.1 mm past the rear wall's inner face, and 6.3 mm outside the case.
- **Within a few millimetres (D up to 59) only the steep poses fit** (α 55° or more, about
  parallel to the face). Each of them has four problems:
  - It breaks the zone rule: the board's lower edge is 15 to 16 mm below the SEN66's top.
  - It takes the USB-C plug through the top face.
  - SW1's push axis runs along the face, so the top-right dot would need a linkage of about 25 mm.
  - It puts the antenna strip 1 to 4 mm behind the e-ink panel (spec §6.8: away from the panel).
- **Keeping the zone rule and a rear USB-C needs D ≥ 61.3** (tilted 15°) or 63.3 (horizontal),
  with the whole front sloped.

**Front face**, independent of the pose, from the bottom up:

1. The 10 mm line, at s 11.55.
2. Two slot rows (1.2 slots, 1.6 bars), s 11.55 to 15.55.
3. 1.2 of face, then the 1.2 mm LED slot.
4. 1.2 of face, then the panel pocket (0.2 clearance) and the panel.

| H | Arrangement | Panel s | Top limit | Spare | Intake open area (≥ 154.5) |
|---|---|---|---|---|---|
| 48 | LED slot above the slots | 19.35 to 56.05 | 54.39 | −1.66: does not fit | 161.3 |
| 48 | LED line in the top slot row | 16.95 to 53.65 | 54.39 | 0.74 | 121.0, short (R18) |
| 50 | LED slot above the slots | 19.35 to 56.05 | 56.70 | 0.65 | 161.3 |

**Minimum envelopes.** These are W × D × H; H is 48 or what the face needs, whichever is
larger.

| Layout | Envelope | What changes |
|---|---|---|
| Horizontal board, whole front sloped | 95 × 63.3 × 49.5 | 8.3 deeper: a deeper wedge with the same silhouette |
| Board tilted 15°, whole front sloped | 95 × 61.3 × 49.5 | the USB-C enters 15° downward; the board needs tilted standoffs; the dot is lower (s 35) |
| Horizontal board, 14.5 mm vertical lower lip | 95 × 55 × 50.1 | the slots move to a vertical lip under the 30° screen face, as on the mini (and like mockup card 2's lip); the top is 34.5 deep |
| Horizontal board, rear antenna hood | 95 × 57.3 × 49.5, plus a 6 mm hood | a bump about 22 × 8 mm on the rear at z 31 to 38; the USB-C mouth sits at the rear wall |
| Hood and a 4 mm lower lip | 95 × 55 × 49.5, plus a 6 mm hood | both of the above, each smaller |

Tilting the board 5° to 15° shortens the lip by 1 to 3.5 mm. Every layout in this table:
- keeps the zone rule;
- takes the USB-C through the rear wall;
- puts the dot on SW1's push axis;
- leaves room for the tongue in front of the SEN66;
- keeps the antenna 18 to 19 mm from the SEN66 and 23 to 28 mm behind the panel's plane.

**Options for the owner.**

1. **95 × 55 × 50 with a 14.5 mm vertical lower lip (recommended).**
   - The footprint and depth stay as agreed, and the height grows by 2 mm.
   - The front is no longer one slope. The slots sit in a vertical band at the bottom, and the
     LED slot and the screen on the 30° face above it.
   - The mini needs the same lip (R15), so the two models share one front. Spec §6.9 asks for
     this: "both models are parametric variants of one design wherever possible".
   - The dot is 67 % up the face, and SW1's tip is 3.2 mm behind it.
2. **95 × 63.5 × 50 with the whole front sloped.** The board lies horizontal above the SEN66. The
   case is 8.5 mm deeper and keeps the mockup's silhouette; the top grows from 27.3 to 34.6 mm
   deep.
   - **Dot.** It sits 69 % up the face, on SW1's push axis. SW1's tip is 3.2 mm behind the face's
     inner surface, which is the direct flexure the coupon tests. The mockup's dot is about 79 %
     up the face; raising it there costs about 2.2 mm more depth.
   - **USB-C.** The plug goes straight in through the rear wall, into a well 6.2 mm deep.
   - **Antenna.** It is 28 mm behind the panel's plane and 16.5 mm from the SEN66 in x alone.
   - **Zone wall.** It runs over the SEN66 and steps down in front of it to meet the face between
     the slots and the LED slot. The light guide, the FFC and the adapter sit behind the panel,
     so they stay in the electronics zone.
3. **95 × 61.5 × 50, the board tilted 15°.**
4. **95 × 57.5 × 50 with a rear antenna hood,** or 95 × 55 × 50 with the hood and a 4 mm lip.

Not offered: the parallel pose inside 95 × 57 × 48. It breaks the zone rule, and the spec does
not allow loosening the air and heat rules.

**Whole-front-sloped layout (option 2), plan view** (x; the lip layout is the same across x):

| Part | x |
|---|---|
| Panel (tail on the user's left, hatched block from −45.5) | −40.9 to 38.1 |
| Window centre | +1.65 |
| Main board | −14.8 to 45.2 |
| SW1 and the dot (⌀4 dot, 0.7 mm clear of the pocket wall) | 42.2 |
| LEDs D1 to D4 | −2.2, 2.9, 25.1, 30.2. The 30 mm line under the window, x −13.4 to 16.7, collects them |
| J7 | 6.3 to 21.8 |
| USB-C | 1.4 |
| Antenna strip | 26.2 to 44.2 |
| SEN66 | −45.5 to 9.7 |

**Whole-front-sloped layout (option 2), side section** (y to the right, z up, not to scale):

```
 z
 50 |                   +------------------- top wall ------------------+
    |   dot s 40 ->    /| board z 31.4-33.0, parts to 37.2         ant  | antenna end y 61.5
 33 |   panel         / | SW1  LEDs J7 ============== U3 ===========[##]| USB-C mouth y 55.5 (well)
 31 |   s 19.4-56.1  /  +---- zone wall z 28.9-30.7, steps down --------+
    |   guide       /      +----------------------+                     |
 15 |   LED slot   /       | SEN66  z 3.0-28.6    |  cable / outlet     | outlet grille, z >= 10
 10 |   slots     / intake |        y 21.3 deep   |  plenum             |
    |   lip      /  plenum +------ foam 1.0 ------+                     |
  2 |___________/________ base plate, floor 2.0 ________________________|
  0 +------------------------------------------------------------------------- y
    0          10        20        30        40        50        60   63.5
```


### airQ mini

The hard maximum is 66 × 50 × 42, with the front 24° from vertical (owner decision, spec §5).
The interior is 62.4 wide, so the 60 mm board is centred with 1.2 mm each side. The SEN66 (55.2)
cannot move away from the antenna in x.

**Board pose, whole front sloped** (default margins):

| α | D needed | Lowest board point (SEN66 top 28.6) | USB-C plug | Antenna to SEN66 |
|---|---|---|---|---|
| 0° | 56.7 | 31.0, above | rear, z 34 | 4.8 |
| 5° | 56.4 | 30.2, above | rear, z 37 | 5.8 |
| 10° | 57.4 | 29.1, above | through the top wall | 7.3 |
| 15° to 55° | 56.5 to 66.5 | below | top | 5 to 7 |
| 60° | 54.3 | 6.5, below | top | 4.7 |

With the whole front sloped, no tilt fits 50 deep: R15's slightly tilted board is not enough.
The horizontal board's front edge stands at y 18.7, which puts its antenna end at y 54.7. The
case would need to be 6.7 mm deeper than its maximum.

**Minimum envelopes:**

| Layout | Envelope | Notes |
|---|---|---|
| Horizontal board, whole front sloped | 66 × 56.7 × 42 | 6.7 over the maximum |
| Board tilted 5° | 66 × 56.4 × 42 | 6.4 over |
| **Horizontal board, 15.5 mm vertical lower lip (R15)** | **66 × 49.8 × 42** | **fits**; the minimum lip is 15.0 |
| Horizontal board, rear antenna hood | 66 × 50.7 × 42, plus a 6 mm hood | 0.7 over, and the tongue no longer fits in front of the SEN66 |
| Hood and a 2 mm lower lip | 66 × 49.8 × 42, plus a 6 mm hood | fits, but the tongue does not fit in front of the SEN66 |

**The fitting layout** (66 × 50 × 42, a 15.5 mm lip, the board horizontal):

| # | Item | Position |
|---|---|---|
| 1 | Front | vertical lip z 0 to 15.5, then 29.0 of 24° slope; f runs from 0 to 44.5; the top is 38.2 deep |
| 2 | Slots | three rows of 4 × 12.4 mm slots from z 10, at f 10.0 to 16.8, the third row just above the crease; 178.6 mm² open (≥ 154.5) |
| 3 | Light-sensor window | on the lip by the slots, in front of the tongue's VEML7700 (the tongue sits behind the lip, in the intake air). The mockup puts it top left; that would need a light pipe down to the tongue |
| 4 | Light band | at the LEDs' height, f about 34.9 to 36.9 (straight guides). CO₂ half x −25.35 to −4.35, over D1 and D2 (x −17.4, −12.3); PM2.5 half x 1.95 to 22.95, over D3 and D4 (x 9.9, 15.0); gap 6.3 (≥ 4) |
| 5 | Labels | "CO₂" and "PM2.5" debossed 0.4 deep and 5 mm tall, under their halves; f 28 to 33 has room |
| 6 | Orange dot | x 27.0 (SW1), f 36.6 (82 % up the face); 2.05 mm of wall to the PM2.5 half; SW1's tip 1.2 behind the face's inner surface |
| 7 | Board | horizontal, bottom z 31.5, front edge y 12.0, antenna end y 48.0 |
| 8 | SEN66 | x −31.0 to 24.2, y 18.2 to 39.5 (the tongue and the inlet gasket in front), z 3.0 to 28.6 |
| 9 | USB-C | x −13.8, z 34.7, straight out the rear through a 6.2 mm well; 18.6 mm from the antenna in x |

**Flags (owner items).**
- **R12, antenna.** It is about 5 mm from the SEN66: the strip stands over the SEN66's end, 4.5
  mm above its top. If the tongue moved elsewhere and the SEN66 went fully forward, it would be
  10.7 mm. 15 mm cannot be reached. Check RSSI on the prototype.
- **R18, outlet grille.** The whole lower rear, 58.4 × 18.9 mm at 40 % open, gives 441.5 mm².
  That is below 2 × 330.1 = 660.1, and above the floor of 296.
- **Tongue.** It is 28 mm from U3 and 29 mm from U2 (the rule is ≥ 20).

### airQ mini (Task 4): re-check with the airQ's construction

**Owner decision (2026-11-27, R51): option 1, 69.5 × 50 × 42.** The model built on it is under
"airQ mini enclosure" below. It raises the lip to 18.0 for the intake rows and the SEN66's plug;
the rest is this study's place a.

**Status (2026-11-27, Task 4a): BLOCKED at 66 × 50 × 42, owner decision (spec §10).** The
addendum above placed the SEN66 ports-forward with the tongue lying in front of it. Since then
the airQ's construction has settled: the SEN66 faces its ports to the rear (R31, because R25's
outlet path cannot run along the module's front), the outlet plenum sits behind a plate, and the
board's standoffs and plugs are modelled. With that construction the mini fails two rules in
its hard maximum. Neither is a margin question. A case 3.5 mm wider (69.5 × 50 × 42) keeps
every rule; see "Ways out" below.

`uv run --with pyyaml python enclosure/src/layout_study.py --mini` prints the numbers below
(`layout_study.mini_recheck`). `tests/enclosure/test_layout_study.py` pins them, with
independent arithmetic for the key ones.

**Fixed for the re-check** (the airQ's values, `airq.py`):
- The lip is 15.5 (the smallest that fits 50 is 15.01), and the board is horizontal.
- The board's bottom is at z 31.0 (the zone rule). Its front edge is at y 12.01, as far back as
  the antenna strip allows (11.79 … 12.01 is the whole range).
- The board sits against the right wall (`clr_remove` 0.2), which gives the left-edge plugs the
  most room.
- The zone wall's slant hugs the slope (t = wall + `clr_remove`). The mini has no panel in
  front of it, so the SEN66's front top corner may come forward to y 10.19.
- The SEN66 stands against the left rail with its ports to the rear and its inlet end against
  the intake passage. The passage, 3.4 wide (58.8 tub − 0.2 − 55.2), is the only way from the
  front of the sensor zone to the port gap.
- The port gap is 3.0 (80.7 mm² ≥ 77.3), the plate 1.6, the ring 24.0 OD.
- The outlet grille has 1.2 slots at a 2.4 pitch, 2 mm inside the plenum: 23 slots.

**SEN66 pose, decided by the numbers.**
- **Ports forward is impossible.** The outlet's 330.1 mm² would have to come back past the
  module to the lower rear. Beside it there is 91.5 mm² (the 3.4 passage), over it 16.6 mm²
  (the 0.3 gap under the zone wall), and under it nothing.
- **Ports to the rear (R31) is the only pose.** The plenum must carry the larger branch's share
  of the grille (13 of 23 slots: 186.6 mm²), so it needs 7.03 deep.
- **H1 lands in the ring.** H1, the USB-C's support boss, stands at x −20.45, y 39.41. That is
  inside the outlet ring's x span (−28.4 … −4.4) when the inlet end is right, and in front of the
  inlets when it is left. So H1 cannot stand in the port gap. Three places remain:

| Place of the SEN66 | Front face y | Plenum (≥ 7.03) | Room in front of the deepest module | Antenna to SEN66 (R12) |
|---|---|---|---|---|
| a: H1's post in the plenum, behind the plate | 11.16 | 11.14 | 8.66 | 10.35 |
| b: H1's pilot boss hung under the zone wall, on the plate's top; the ring passes 0.20 under it | 14.31 | 7.99 | 11.81 | 7.55 |
| c: as far back as the plenum allows, H1 ignored (for comparison) | 15.27 | 7.03 | 12.77 | 6.75 |

In front of the module go the SEN66's plug and its cable's bend (6.94) and its pad and seat
(4.2), side by side in x. Every place has room for them.

**Blocker 1: the tongue has no place in the intake air** (global rule: the tongue sits in the
intake air, at least 20 mm from U3 and U2).

Whichever way the tongue lies, its VEML7700 faces the lip only when the tongue's 13 mm depth runs
along y. Its Qwiic plug then leaves the rear edge along +y too. So it needs 17.56 of free y from
the lip at some x and z. Only two places could offer that: in front of the module, or beside it.

- **Lying flat in front of the SEN66.** It needs 17.56 from the lip: 0.5 of air, 12.36 to its
  Qwiic socket's mating face, 4.5 for the plug, and 0.2. The most any place leaves is 12.77, so
  it is 4.8 to 8.9 mm short.
- **On edge in the intake passage.** It is 1.6 + 3.0 thick and 22 tall, so it blocks 101 mm² of
  the passage's 91.5: R25 asks 77.3. At the right end it would also sit 10.5 from U3.
- **Beside the module:** there is 3.4 mm. **Over or under it:** nothing.
- **In the slope's space in front of the zone wall:** that space is the electronics zone. To
  make room there for the tongue lying flat (17.1 behind the slope's inner face), the zone wall's
  slant would sit 17.4 behind the slope. The SEN66's front would then be at y 27.05 and its port
  face at 48.35, past the rear wall's inner face (48.2), before the port gap, plate and plenum.
  This is hand arithmetic, not in `mini_recheck`.

**Blocker 2: the board's sensor plugs have no room.**
- J2 (the SEN66's cable, JST GH) and J4 (Qwiic, which the tongue would use, because J3 is
  blocked as in the airQ) come out of the board's left edge.
- With the board against the right wall, their mating faces are 2.35 and 2.64 from the shell's
  side wall, less `clr_remove`. With the board centred, 1.35 and 1.64.
- J3 comes out of the front edge, 1.57 from the slope's inner face.
- The airQ's plug envelope (plug plus the cable's bend) is 5.0, to confirm with the cables. A
  side-entry plug stands out of its receptacle, whose body alone is 4.86 deep. So 2.35 does not
  take one, and the SEN66 cannot be plugged in.
- Thinning the side wall to the plan's minimum 1.6 adds only 0.2.
- The conclusion does not hang on the 5.0 envelope. Even a 3.0 plug-and-bend envelope needs W ≥
  66.65 (`mini_recheck(plug_out=3.0)`).

**Ways out (owner decision; never loosen the air and heat rules, spec §10):**

| Option | Envelope | What changes | Rules |
|---|---|---|---|
| **1 (smallest found)** | **69.5 × 50 × 42** (W +3.5) | The board against the right wall: J2 and J4 get 5.85 and 6.14 mm. The SEN66 against the right rail, inlet end left; the intake passage at its left end is 6.9 wide. The tongue stands on edge in the passage, in the intake stream, VEML7700 facing the lip window. H1's post stands in the plenum (place a), its back trimmed below its pilot as in the airQ. | passage 84.4 ≥ 77.3 with the tongue in it; tongue to U3 41.6, to U2 31.6; R25 plenum 11.14 ≥ 7.25, at H1 253.6 ≥ 41.3; room in front 8.66 ≥ 6.94; R12 10.35 and R18 498.2 mm² are shortfalls (owner items, as before) |
| 2 | 69 × 56 × 42 | The tongue lies flat in front of the SEN66 (D ≥ 55.75). The plugs still need W ≥ 68.65 | larger than option 1 |
| 3 | 66 × 56 × 42 + a board revision | J2 and J4 move off the left edge (PCB, not this plan); the tongue flat in front | changes the shared board |
| – | 66 × 50 × 42 | not possible without breaking the tongue rule or R25, or without a way to plug in the SEN66 | – |

Option 1 keeps D and H and the 24° front. The width the owner described as "the same width" as
the mockup grows by 3.5 mm.

### What the owner's questions buy

The table gives the depth needed (mm) with the whole front sloped, for the horizontal board and
for the smallest tilt that keeps the rules. It then gives the lower lip that would fit the target
depth (airQ 55, mini 50) with a horizontal board.

| Change | airQ horizontal | airQ best tilt | airQ lip for 55 | mini horizontal | mini best tilt | mini lip for 50 |
|---|---|---|---|---|---|---|
| As planned | 63.3 | 61.3 (15°) | 14.4 | 56.7 | 56.4 (5°) | 15.0 |
| SEN66 lying flat, 21.3 tall (breaks Sensirion's orientation rule; information only) | 60.8 | 58.7 (20°) | 10.1 | 54.8 | 54.2 (10°) | 10.7 |
| Walls 1.6 everywhere | 63.0 | 61.0 (15°) | 13.8 | 56.2 | 55.8 (5°) | 13.9 |
| airQ front at 25° | 59.2 | 57.4 (15°) | 9.0 | – | – | – |

- **SEN66 lying flat.** It saves 2 to 2.5 mm of depth, or 4 mm of lip. Even then, neither model
  fits its target without a lip.
- **1.6 mm walls.** They save less than 0.6 mm.
- **25° airQ front.** It saves about 4 mm of depth. But the shorter face needs H 51.4 (+3.4) to
  hold the slots, the LED line and the panel.

## airQ enclosure

`airq.sc`, built from `src/airq.py` with the shared construction in `src/enclosure_common.py`
(Task 4 reuses it with the mini's values). Board positions come from `src/board_sources.py`
(R27). Task 3a builds the body and the internals; Task 3b-1 adds the face features and 3b-2 the base openings and the full check table.

**Layout (R22).** The envelope is 95 × 55 × 51 with a 15 mm vertical lower lip. The study's lip
row needed 95 × 55 × 50.1. Rounding the lip to 15 still fits D 55, which needs 54.62. The face
needs 1 mm more than the study gave, for the zone wall's ledge between the intake slots and the
LED slot, so H is 51. The board lies horizontal above the standing SEN66, with the zone wall
between.

**SEN66 pose: ports to the rear (fix round 1, judgement call).** The module stands (R17: long
axis along x, port face vertical) with its port face to the REAR and its inlet end on the user's
right (square inlet high, round inlet low), against the left rail: x −43.7 … 11.5, y 18.4 … 39.7,
z 3.0 … 28.6.
- **Why.** With the ports forward (3a's first pose) the outlet must run along the module's front
  in the sensor zone, which lies under the zone wall's slant. From the ledge back to the port face
  that space is 211 mm² in section, and 305 mm² even with the strip under the ledge
  (`layout_study.front_layer`). The outlet needs 330.1 (R25). The module cannot move back: H1's
  standoff stands behind it.
- **Outlet.** It blows straight back through `gasket_out`, a TPU ring (bore ⌀21.0, 346 mm²) seated
  1 mm deep in the plenum plate. Behind the plate is the outlet plenum, 8.9 mm deep and as wide as
  the space between the rails, and the outlet grille in the lower rear wall. The plate is the
  baffle in front of the grille.
- **Inlets.** The sensor zone is the intake plenum, and the intake slots in the lower front lip
  are its only opening. The inlets draw from it through the 3.0 mm gap between the port face and
  the plate (80.7 mm²). `gasket_in`, a TPU wiper on the port face between the inlets and the ring,
  runs from its groove in the floor to the zone wall and separates the port groups.
- **Antenna (R12).** 16.7 mm from the SEN66.

**How the SEN66 is held (fix round 2, review I3(b)).** The module is 21.3 ± 0.5 deep
(datasheet Fig. 8), so a seal squeezed between a fixed front and the plate would open by up to
0.35 mm. Instead the **port face is the datum**:
- **Rear stop.** The port face rests on the land of `gasket_out` (`ring_preload` 0: the ring is a
  hard stop, not a squeeze). The seals therefore see the same port face at 20.8, 21.3 and 21.8.
- **Front pad.** `sen66_pad`, a 10 × 10 foam pad 3.2 thick free (`pad_t`), is stuck on the
  module's connector face (its plinth) on the outlet's axis. It presses the module onto the ring.
  It is 44 % compressed at the nominal depth, 28 % at 20.8 and 60 % at 21.8 (26–53 % once the
  seat's give is counted). The low right rail is only a guide: it stays `clr_align` in front of a
  21.8 module.
- **Pad seat (fix round 3, B1).** The pad bears on a 2.4 plate (`seat_t`) from the floor,
  joined to the left side rail along its height and standing just behind the cables' riser and
  run.
  - Taken as two cantilevers (from the floor and from the side rail, PETG at 1.8 GPa), it is about
    77 N/mm. It gives 0.06 at the pad's least force and 0.19 at its most (15 N), and its root
    stress across the layers at 15 N is 6.6 MPa.
  - Its top follows the zone wall's slant, 0.8 under it, so it stays clear of the drawer grommet's
    squeezed face.
  - A 45° lead-in on its back edge (B4) meets the pad's free front face at every module depth, so
    the pad is squeezed gradually as the module goes down.
- **No tipping or yaw, the land loaded all round (round 3).** The pad's force passes through the
  ring's centre. `gasket_in` is a soft 55° wiper (0.8 thick, 6.1 long, 0.5 preload): it pushes
  0.28–0.54 N (TPU 95A at 26–50 MPa), 25.5 mm from the ring's axis. The ring's reaction must stay
  inside the land's kern, (r_o² + r_i²)/(4 r_o) = 5.3 mm, so that the land stays loaded all round.
  That needs a pad force of at least 3.1 N. With a 1.5 margin, the **pad spec** is:
  - at least 4.7 N (47 kPa) at its least compression (26 %);
  - at most 15 N (150 kPa) at its most (60 %);
  - so a foam whose force rises at most 3.2× between those compressions.

  The ring is a hard stop of TPU 95A at 0.05–0.15 MPa, so it closes little of the print's
  waviness: check the first print for outlet leaks (README "To confirm").
- **Front clearances at 21.8.**
  - The connector face is 0.15 behind the right rail.
  - The plinth's top front edge is 0.39 behind the zone wall's slant. The plinth is inset 1.2,
    which `sen_y0` (set by the block's edge) does not count.
  - The plug and its cable's bend move forward with the connector face (B2). A 0.6 pocket in the
    slant's underside over them (`plug_room_d`) keeps them 0.29 clear of the zone wall; the slant
    keeps 1.2 there.
- **Check.** The check design puts the front of a 21.8 module (plinth, block, plug and bend) and of
  a 20.8 module against the cradle, the zone wall, the pad and both gaskets, with the port faces
  on the ring. Only the pad meets them, by 1.9 and 0.9 mm free
  (`test_sen66_at_its_depth_extremes`). `airq_check.sen66_hold` gives the arithmetic
  (`test_sen66_held_over_its_depth_tolerance`, `test_pad_seat_is_stiff_and_tied`).
- **Inlet seal's root (B3).** The wiper's root is a 2.0 foot squeezed 0.05 into its slot in the
  plate on its sides and back, so there is no bypass round it and no travel to eat the preload.
  Its tip has a 45° lead-in at the top (0.8, B4), so the module's bottom edge pushes it back as
  the module goes down.

**The sealed sensor zone (I2, I3).** `base_plate` is the whole footprint and the sensor zone's
tub, in one print: floor, front lip, rear wall, the side rails under the zone wall's profile, the
boss pockets, the plenum plate and its rib on the rear wall, the cradle, the HCHO pocket and its
chimney, and the standoffs with collars.
- **Zone wall.** It rests on the tub's rim: laps on the rails, the boss pockets, the plate, the rib
  and the standoff collars. At the front the intake slots leave no room for a lap, so `zone_seal`
  seals the ledge against the lip. It is a closed-cell foam strip, 1.6 free and 25 % compressed,
  pushing 3–9 N along 77.8 mm (fix round 3). TPU 95A at 20 % would have pushed hundreds of newtons
  and bowed the slotted lip. It sits on the standoffs' spigots, and pads on its top
  reach the board, so the board's two M2 screws clamp it (fix round 2, N5): it cannot lift off its
  laps.
- **Base to shell (fix round 2, N1).** The shell has two datums. It stands on the floor (z), where
  the screws clamp it, and its side walls end against the full-width rear wall's front face (y).
  Everywhere else it keeps `clr_remove` from the base:
  - its side walls end 0.2 behind the lip's inner face;
  - the lip is recessed 0.2 round the front bosses;
  - its slope stops 0.2 above the lip's top. That leaves a 0.2 parting line at the crease, which
    opens into the electronics zone above the ledge seal, not into the sensor zone.

  The check design nudges copies of the shell 0.05 each way. Only the copies pushed back and down
  meet the base, and only on the rear wall's face and the floor (`test_shell_nudged_meets_the_base_only_on_its_datums`).
  So a shell or base printed up to `clr_remove` off size still goes together.
- **Bosses.** The front boss pockets keep the shell's floor bosses out of the sensor zone.
- **The space beside the ring (fix round 3).** Between the port face and the plate, left of the
  inlet wiper and outside the ring, lies a dead space. It only matters if the ring leaks.
  - It reached the inlets' side through the 0.3 gap over the module, round the wiper's tip: a
    5 mm path with up to 6.4 mm² of section.
  - `sen66_top_seal` closes that path: a 0.6 closed-cell foam strip across the module's top at the
    wiper's tip, from the port face to the connector face, 17–67 % compressed over the module's
    height tolerance and pushing 4–15 N near H1.
  - The dead space now reaches only the front plenum, 21 mm forward through the 0.2 gap at the
    module's left end (5.1 mm²) and the 0.3 gap over its left part. From there the air is ≥ 80 mm
    of intake stream (114–411 mm² of section) from the inlets.
  - Ring and wiper are therefore a seal and a baffle against recirculation, with no short way
    round.

**HCHO pocket (R26).** The SFA40 lies flat at the front right (x 13.4 … 38.8, y 9.8 … 35.2),
opening up. Two pins (front right, rear left) go through its holes.
- **Lid.** `hcho_lid` closes the pocket, with laps on its walls, the lip rib and three shelves.
  Four posts on the lid press the board down. Two **M2 × 6** self-tapping pan-head screws come
  from under the floor, through the SFA40's front-left and rear-right holes, into two of the posts,
  and clamp the board and the lid to the base (fix round 2, N5).
  - Their tips end at z 6.4: in the pilots (which end at 7.1), with 2.8 of thread in the posts, and
    under the tongue's pocket (8.19). An M2 × 8 would come through the lid under the tongue (round
    3, B5).
  - Their heads sit in 0.4 counterbores, with 1.6 of floor left, so they stand 1.2 under the
    floor.
  - The felt feet (`foot_t` 2.0, ⌀10) are thicker than that and are not over them. The front feet
    cover the shell's screws, the rear feet sit at the rear corners
    (`test_sfa40_screws_and_feet`).
- **Grille.** A chimney in front of H2 takes the air to the HCHO grille: five slots in the right
  rail, behind a window in the shell's right side wall, from the 10 mm line up (67.8 mm² open,
  ≥ 54.7).
- **Window (fix round 2, N2).** The window's top steps up with the slots: each step covers its
  slot and half a bar each side, and stops 0.6 over it. Behind every point of the window stands
  the right rail or the zone wall's end face. The check design fills a 0.5 slab behind each step
  and finds it backed everywhere but at the slot (`test_hcho_window_is_backed`).
- **Rear wall.** It stays whole for the outlet grille.

The alternatives, with numbers:

| Alternative | Outlet grille open, 40 % / 50 % (mm²) | Meets 660.1 | Why not |
|---|---|---|---|
| 3a as built: SFA40 standing at the rear left, its grille in the rear wall | 408 / 522 | no | the pocket and its plug room take the rear wall's left 34 mm |
| Narrower pocket, the plug leaving upward | 454 / 567 | no | 25.4 of board + 5 of plug > 26.9 from the floor to the zone wall: it does not fit |
| Higher open fraction (1.2 slots, 1.2 bars) | 522 (with the 3a pocket) | no | not enough alone |
| Upper-rear exhaust kept separate | adds nothing | no | the rear wall above the zone wall is the electronics zone's exhaust; joining it would open the outlet path to the case air |
| SFA40 along the right side wall, low side grille (ports forward) | 658 / 817 | – | H2's standoff stands where the board would; with the ports forward the outlet path has at most 305 mm² (R25) |
| **Chosen: ports to the rear; SFA40 flat at the front right under the tongue, its grille in the right side** | – / **664.3** (32 slots) | **yes** | 40 % over the plenum's 83.8 mm would give 581, so the grille is 50 % open |

`layout_study.hcho_alternatives` computes the table, counting whole slots.

**Tongue (M4).** It lies on the HCHO lid, turned 180°, 4.6 mm behind the lip (x 12.8 … 34.8,
y 6.4 … 19.4, z 8.2).
- **Held (fix round 2, N5).** A 0.4 pocket in the lid's top locates it, with `clr_align` round the
  board. A pad under the zone wall's ledge holds it down: the pad sits over the VEML7700's top,
  `clr_align` above it, and the zone wall is clamped. The pad also shades the sensor from above.
- **Air.** The intake slots in front of it feed a 4.6 mm channel. The channel's side exits
  (2 × 24.0 mm²) pass more than those slots' open area (35.3 mm²).
- **Distances.** It is 20.9 mm from U3 and 29.5 mm from U2 (≥ 20).
- **Light sensor.** Its VEML7700 sets the light-sensor window (x 16.4, z 11.7).

**Cables (I2).** Keep-outs in the check design hold the plugs and the routes. Every cable goes in
with both plugs on (fix round 2). The plug envelopes are taken no larger than the receptacle bodies
they enter (`interface.yaml`): Qwiic 6.0 × 2.95, GH 10.75 × 4.25, to confirm.
- **SEN66 → J2.** The cable leaves the connector on the module's connector face (front) and goes
  down, then left along the floor in front of the module. It rises through the zone wall's
  **drawer**, left of the adapter and behind the folded tail, and runs over the zone wall to J2.
  - The drawer is a notch in the slant at the left, open to the zone wall's left end, so both
    cables are laid in from the side. No plug passes it; the GH plug passes no closed opening at
    all.
  - `grommet_zone_a/_b` (front and rear halves, split along the cables) are closed round the cables
    first, then slid in together from the left over the left rail.
    - Ribs in the notch's grooves hold them across the wall. The ribs stand 0.45 proud of the
      printed face at any squeeze (round 3, B6).
    - They bear on the rail and the notch's end with `drawer_squeeze` 0.05 (18–35 N on the front
      face).
    - Where the boss notch leaves the zone wall a 2.3 mm sliver, a key on the left boss pocket's
      back wall (a 1.4 × 0.5 ridge in a groove in the sliver) takes their push. It carries 10–20 N
      at 1.7–3.3 MPa (`airq_check.seal_forces`).
    - The shell's side wall stops them sliding out.
  - The grommets' bores are 0.2 under the cables' diameters (`bore_squeeze`), so they hug the
    cables. Sleeve the GH cable's six wires with heat-shrink through the drawer so they are round.
- **Tongue and SFA40 → J4.** J3 cannot take a plug in the airQ: the panel and the light guide
  stand 1.4 mm into the plug's path at the board's front edge (owner item). The tongue therefore
  chains through the SFA40's two Qwiic ports, on the same I2C nets (`interface.yaml`
  J_QWIIC_TONGUE = J_QWIIC_AUX):
  - SFA40 J1 → tongue, through the lid's hole. The hole is 6.4 × 3.35, the Qwiic plug + 0.2 a side,
    so the lid goes on over the cable. `grommet_tongue_a/_b` (left and right halves) close round
    the cable, each with a flange on the lid and a barb under it.
  - SFA40 J2 → the pocket's left wall → along the floor → the drawer → J4. The wall's J4 notch is
    open at its top, so the cable is laid in. `grommet_j4_a/_b` (lower and upper halves) straddle
    the wall with flanges, the floor under them and the lid over them. They squeeze the notch's
    faces by `grommet_squeeze` 0.1, but meet the floor and the lid only at contact, so they do not
    lift the lid (round 3, B6).
  - Check: the plug's section swept through the lid's hole meets nothing of the lid, and the
    drawer and the J4 notch are open from the cable's place out past their edges
    (`test_plugs_pass_their_openings`).

**Print split (R24), orientation (fix round 2, N6) and materials (N3).** The orientations and the supports to use are the
table in "Print and assembly guide (airQ)", section 2, which the exports follow; this table gives the reasons and is not
kept in step with it.

| Part | Material | Prints | Supports |
|---|---|---|---|
| `shell` | shell material (ASA/PETG, warm white) | face down on textured PEI | none. Two small overhangs of about 60° are accepted: the rear boss's front disc (⌀6) and the HCHO window's rear edge |
| `base_plate` | shell material | floor down: every wall, post, rib and slot stands vertical; the screw counterbores are on the bed | none |
| `zone_wall` | an **opaque** filament (internal, any colour, e.g. black) | standing on its right end: the bent profile on the bed, the drawer and its grooves at the top, running vertical | one small support under the right boss notch's ledge, a 5 × 2 cantilever |
| `hcho_lid` | an opaque filament | top face down, posts up | none. The tongue pocket's floor bridges 13.3 mm |
| `gasket_out` | TPU 95A, opaque (black) | on its seat end | none |
| `gasket_in` | TPU 95A, opaque | standing on its floor end: the root foot and the 55° wiper are a vertical prism; the tip's lead-in faces up | none |
| `zone_seal`, `sen66_top_seal` | closed-cell foam, **black**, adhesive-backed (bought, cut) | – | – |
| `grommet_zone_a/_b` | TPU 95A, opaque | see the guide, section 2 | none |
| `grommet_j4_a/_b`, `grommet_tongue_a/_b` | TPU 95A, opaque | on the split face, the half-channel on the bed | none; the tongue halves' 0.4 barbs overhang 0.5 |
| `sen66_foam`, `sen66_pad` | PU foam, cut (bought) | – | – |

- **TPU and foam sizes.** Each part is sized at contact plus its own squeeze, and the check design
  sets them all to 0:
  - the J4 and lid grommets' sealing faces, `grommet_squeeze` 0.1 (4 %);
  - the drawer's, `drawer_squeeze` 0.05;
  - the bores, `bore_squeeze` 0.2;
  - the wiper, `wiper_squeeze` 0.5, and its root, `root_squeeze` 0.05;
  - the foams, `pad_squeeze`, `seal_squeeze` and `top_seal_squeeze`, modelled free;
  - the ring is a stop (`ring_preload` 0).
- **Opaque near the light paths (N3).** The light-sensor window sits 2.6 below the LED line.
  Inside, the barriers between the light guide and the tongue's channel are the ledge and
  `zone_seal`, so both are opaque: black foam, and a dark filament for the zone wall. Natural TPU
  and warm-white plastic at 1.2 pass light. Task 3b's
  opaque-wall check must include this path: guide → ledge/`zone_seal` → the channel in front of
  the tongue → the VEML7700. It must also keep the guide's light off the 0.2 parting line at the
  crease (N1), which opens just under the LED slot.
- **Order:**
  1. inserts;
  2. base;
  3. `gasket_in` down its slot (root first) and `gasket_out` into its seat;
  4. SFA40 with its two cables plugged in: lay the J4 cable in the wall's notch on
     `grommet_j4_a`, add `grommet_j4_b`, put on the lid (the tongue cable through its hole), then
     drive the two M2 × 6 screws from under the floor and fit `grommet_tongue_a/_b` round the cable;
  5. tongue in its pocket, its cable plugged in;
  6. `sen66_pad` stuck on the SEN66's connector face on the outlet's axis, `sen66_top_seal` across
     its top at the wiper's tip; lower the SEN66, pressed back against the ring, past the seat's
     and the wiper's lead-ins, with its cable plugged in;
  7. zone wall, with `zone_seal` stuck on its ledge's front face, onto the spigots and the key; lay
     the two cables into the drawer from its open end, close `grommet_zone_a/_b` round them, and
     slide the pair in together;
  8. board, then the cables into J2 and J4, and the board's two screws, which clamp the zone wall;
  9. the FFC into J7 (contacts up, latch closed; the shell is off, so J7 is open from above);
  10. on the shell, upside down on the bench: the panel taped (0.1 mm tape) into its pocket, its tail
      folded into the adapter, `crease_seal` (0.3 mm black foam tape) stuck on the lip's top (the
      base's side, see the table above), the bare clear `light_guide` (no cladding; see "Shell face: print and
      finish") pushed tongue-first into the LED slot from inside and stuck to the panel's back with a
      0.2 mm adhesive pad (the bar's gap to the panel): it hangs by its tongue and the pad until the
      shell is on; the black foam `led_mask` stuck to the panel's back in front of D3 and D4, and the black
      foam `gap_stop` (1.3 wide) in the gap between the D1 and D2 feet, 0.2 clear of each (both also on a 0.2 mm
      adhesive pad);
  11. the FFC's free end into the adapter's ZIF with the shell held 12 mm over the base (the lift the
      FFC allows with both ends plugged in, with 3.8 mm to spare over the 2 mm allowance, 3.2 for the
      shortest FFC), then the shell lowered along −z;
  12. feet.
- **Fastening:** three M2 screws into heat-set inserts in the shell.
  - Two front floor bosses take screws from underneath, the heads under the felt feet. On the way
    down the bosses pass the zone wall's notches, and they end up standing in the boss pockets.
  - One rear boss under the top wall at the rear left takes a screw through the rear wall (R29).
  - The counterbores leave 1.6 mm of floor under the heads.
- **Way on.** The check design sweeps the shell's bosses from their place up past the top, and
  copies the whole shell raised 1, 2, 4, 8, 16 and 32 mm, with what rides in it: the light guide,
  `led_mask` and `gap_stop` (`guide_up_*`, `mask_up_*`, `stop_up_*`). None of them meets the base, the
  zone wall, the board, the SEN66, the tongue, the SFA40 or the cable keep-outs (the FFC's included).
  The panel and the adapter ride in the shell, so they are left out of that pairing.

**USB-C support (M7).** H1, 7.7 mm from J1's centre, is joined to the plenum plate, which spans
the base between the rails from the floor to the zone wall. Above that, the clamped zone wall
(its pad and spigot seat) fills the 2.1 mm up to the board. The plug's push goes J1 → board → H1's
screw → zone wall pad and H1's spigot → H1 → plate → floor and rails.

**Bodies** (volume in mm³; size and minimum corner in mm; at the default squeezes):

| Body | Volume | Size | Min corner | What, material |
|---|---|---|---|---|
| `shell` | 15737 | 95.00 × 54.88 × 49.00 | −47.5, 0.12, 2.0 | 30° face, top and sides (R24); three M2 insert bosses; the panel pocket; the HCHO window |
| `base_plate` | 29343 | 95.00 × 55.00 × 49.00 | −47.5, 0, 0 | the tub: floor, lip, rear wall, side rails, boss pockets, plenum plate and rib (the plan's `baffle` and outlet duct), cradle (`sen66_cradle`: the pad's seat tied to the side rail, the guide rail), HCHO pocket and chimney (`hcho_pocket`), SFA40 pins and screw holes, standoffs H1 and H2 with collars and spigots, the HCHO grille, screw counterbores, the J4 notch, the sliver key |
| `zone_wall` | 9046 | 91.00 × 50.00 × 18.06 | −45.5, 3.0, 12.94 | ledge behind the lip, slanted part behind the panel, horizontal part over the SEN66 and the plenum; the cable drawer; the pocket over the SEN66's plug; the pads the board clamps; the tongue hold-down |
| `sen66_top_seal` | 43 | 3.39 × 21.30 × 0.60 | −7.09, 18.44, 28.6 | foam strip across the SEN66's top at the wiper's tip (shown free). Closed-cell foam, black |
| `zone_seal` | 149 | 77.80 × 1.60 × 1.20 | −38.9, 1.4, 13.8 | the ledge's seal against the lip (shown free). Closed-cell foam, black |
| `sen66_foam` | 1176 | 55.20 × 21.30 × 1.00 | −43.7, 18.44, 2.0 | the 1 mm foam under the SEN66 |
| `gasket_out` | 424 | 24.00 × 4.00 × 24.00 | −42.9, 39.74, 3.8 | outlet ring, from the port face (its stop) to its seat in the plate. TPU 95A |
| `gasket_in` | 197 | 6.44 × 4.55 × 27.90 | −6.09, 39.24, 1.0 | the 55° wiper between the inlets and the ring, its root foot in the plate. TPU 95A |
| `sen66_pad` | 320 | 10.00 × 3.20 × 10.00 | −35.9, 16.65, 10.8 | the foam pad pressing the SEN66 onto the ring (shown free) |
| `hcho_lid` | 1337 | 27.90 × 37.74 × 4.99 | 11.65, 2.0, 3.6 | the HCHO pocket's lid: the SFA40's hold-downs (two with pilots for the screws from below) and the tongue's pocket (the plan's `tongue_mount`) |
| `grommet_zone_a/_b` | 63 each | 8.95 × 2.80 × 7.77 | −45.5, 9.80 / 12.60, 14.65 / 18.72 | the drawer's halves, round the SEN66 and Qwiic cables. TPU 95A |
| `grommet_j4_a/_b` | 25 / 47 | 3.20 × 5.60 × 2.00 / 3.39 | 10.85, 2.6, 2.0 / 4.0 | lower and upper halves in the pocket's J4 notch. TPU 95A |
| `grommet_tongue_a/_b` | 24 each | 4.00 × 4.95 × 2.20 | 22.1 / 26.1, 33.39, 6.99 | left and right halves in the lid's hole. TPU 95A |

**Parameters Task 3b and Task 4 use.** The plan's names are `W`, `D`, `H`, `tilt_deg`, `wall`,
`grille_min_z`, `slot_w`, `clr_align`, `clr_remove`, `clr_snap`, plus `lip` and `gasket_squeeze`.
The plan's `floor` is named `floor_t`, because SolidCraft reserves `floor` (a function). The
positions 3b needs (M6):
- panel and its pocket: `panel_x0`, `panel_s0`, `bezel`, `window_xc`, `pocket_x0`, `pocket_x1`;
- LED slot and light guide: `led_f0`, `led_h_slot`, `led_len`, `led_z`, `guide_t`;
- adapter: `adapter_x`, `adapter_s`, `adapter_t`;
- FFC: a 73 mm 24-pin 0.5 mm FFC (a custom length, R49), same-side contacts (Type A), 3.5 mm inserted at each end
  (about 3.5 mm goes inside J7: `hardware/README.md`, "E-ink FPC fit (airQ)", the reach analysis, lines 167 and 176),
  into `j7_x0` … `j7_x1`. Its seated route is 66.0 mm of centre line, so route and insertions fill the 73 mm. The fold
  jig's jog (`ffc_s_c3`, the C run's place up the slope) can go from 9.80 (the run 0.3 over the ledge) to 11.96 (crease
  3's far corner where layer D's bend to J7 starts), so it takes routes of 63.8 … 68.1 mm, an FFC of 70.8 … 75.1 mm at
  3.5 inserted: no common stock length (50, 60, 70, 80, 100) fits. At both ends of the vendor's ±1 mm and of an
  insertion of 3.0 … 4.0 the jog takes the difference (72 mm at 4.0: `ffc_s_c3` 11.87; 74 mm at 3.0: 9.87), so there
  is no slack and no bow. It lets the shell be held 12 mm over the base with both ends plugged in: the chain is 5.8 mm
  longer than the straight distance (3.8 over that plus the 2 mm allowance), 3.5 for the shortest FFC (72 mm) and 3.2
  at 72 mm with 4.0 inserted. At J7 the contacts are
  up and pin 1 is on the right, so pin i is on pin i (the adapter is taken as 1:1, both ZIFs on its panel side). The
  route has three 45° direction-change folds (R42: at most three, made once at assembly over a fold jig, never
  re-flexed);
- dot and flexure on SW1's push axis: `sw_x`, `sw_z`, `dot_f`, `dot_d`;
- light-sensor window: `lsw_x`, `lsw_z`, `lsw_d`, and its gap in the slot rows, `lsw_gap_x0` …
  `lsw_gap_x1`;
- intake rows: `slot_row1_z`, `slot_row2_z`, `row_x0` … `row_x1` (between the boss pockets) and
  `slot_bar`. With 1.2 bars they give 154.8 mm² open;
- outlet grille: `out_gx0` … `out_gx1`, `out_gz0` … `out_gz1`, `out_pitch` 2.4, `out_n` 32;
- upper-rear exhaust: `exh_x0` … `exh_x1`, `exh_z0` … `exh_z1`, kept apart from the outlet;
- USB-C: `usb_x`, `usb_z`, `usb_well` (6.6), `usb_chamfer`; 3b-2 adds `usb_plug_w` / `usb_plug_h` (the overmold, 12.5 × 7, to confirm) and `usb_open_w` / `usb_open_h`;
- 3b-2 counts: `in_n_l` 5 and `in_n_r` 2 intake slots per row in the two spans (lengths `in_len_l`, `in_len_r` derived), `exh_n` 14 exhaust slots.

The board's front edge `board_y0` is the study's binding constraint, written as an expression: the
corner of the LED faces, with the panel and the light guide in front of it.

**Check design.** `uv run --with pyyaml python enclosure/src/airq_check.py --run` builds
`.build/airq-check.sc` (`ref_main` only there, R8). It holds the six references, the cable
keep-outs (`ko_*`), the air probes (`air_*`) and the shell's sweep (`sweep_*`, `shell_up_*`, and the raised
copies of what rides in it, `guide_up_*`, `mask_up_*`, `stop_up_*`), at
`gasket_squeeze` 0. The script then:
1. runs the interference check;
2. measures the probes' sections;
3. checks the gaskets' contact;
4. prints the distances.

`tests/enclosure/test_airq.py` repeats it.

### Base openings (Task 3b-2)

All cut in `base_plate` by `airq.openings` (`enclosure/src/airq.py`), after every join. Each
position is a parameter 3a fixed; 3b-2 adds only the slot counts and the USB-C sizes. Open areas
are measured on the geometry (probe volume less its overlap with the base, over the wall's
thickness; `airq_check.opening_probes`).

| Opening | Where | Open area (mm²) | Lowest edge z | Source |
|---|---|---|---|---|
| Intake slot rows | lower front lip (y 0 … 1.8), two rows z 10.0 … 11.2 and 12.4 … 13.6, 5 + 2 slots per row either side of the window's gap, x −37.7 … 37.7 | 154.80 | 10.0 | `airq.py:294` |
| Light-sensor window | lip, ⌀ 2.5 at x 16.4, z 11.74, in the rows' gap, in front of the tongue's VEML7700 | 4.91 | 10.49 | `airq.py:296` |
| Outlet grille | lower rear wall, 32 slots, x −41.9 … 33.7, z 10.0 … 27.3, behind the plenum plate | 664.32 | 10.0 | `airq.py:298` |
| Electronics exhaust | upper rear wall, 14 slots, x 9.4 … 41.8, z 37.0 … 47.0 | 168.00 | 37.0 | `airq.py:302` |
| HCHO grille | right rail, 5 slots (3a), behind the window in the shell's side wall | 67.81 | 10.0 | `airq.py:454` |
| USB-C opening | rear wall, 12.9 × 7.4 on J1's axis (x 1.4, z 34.18), 0.5 chamfer on the outside | – | 30.48 | `airq.py:308` |

### Shell face (Task 3b-1): print and finish

| Part | Print | Finish / material |
|---|---|---|
| `shell` | face down on textured PEI; the adapter holder's arm hangs free and needs support, reached from the open bottom before the panel goes in | warm white; the panel is bonded to the bezel's back with 0.1 mm tape (no rear retainer) |
| `orange_dot` | same job as the shell, an AMS colour region: it prints first, on the bed, flush with the face (a 0.6 deep recess in the flexure beam's tip) | orange |
| `light_guide` | clear PETG; its orientation is a first-print item (To confirm): printed on its +x end, supports only on the two feet's +x end faces (R54); see the print table | **Bare: no coating, cladding or paint on any face (R45).** Total internal reflection at the two facets and the faces needs bare PETG facing air; the bar's front sits 0.2 from the panel (an adhesive pad fills the gap and is the only contact). It is lit by D1 and D2 only; every line from a bare face to U4 is stopped by the zone wall, the LED bodies, the board or `gap_stop` (R13 row), and the line's evenness and dim ends are a print item (To confirm) |
| `led_mask` | not printed: black closed-cell foam block in front of D3 and D4, 0.2 from their faces, stuck on the panel's back | black; stops D3's and D4's light but about 2 % of their emission (2.0 / 2.1 %: 0.8 sideways, 0.6 up, 0.6 down), which passes its edges through the 0.2 gap into the case at grazing angles (`airq_check.mask_leak`); no straight line from there reaches the light sensor, the lip's window or the crease through less than 1.2 of opaque material, nor U4 (the faces emit away from it). Firmware drives all four alike |
| `gap_stop` | not printed: black closed-cell foam strip, 1.3 wide, between the D1 and D2 feet (0.2 clear of each, so their total internal reflection stays), from 3 below the foot facet to 0.2 in front of the LEDs, stuck on the panel's back | black; stops the straight lines from the D2 foot's tail-side face through the gap between D1 and D2 to U4 (R13, R50) |
| `crease_seal` | not printed: 0.3 mm black closed-cell foam tape, full width, 1.7 wide, on the lip's top | black |

### Check table

Every row is measured on the geometry where the check design can (probes with `inspect.interference` and `inspect.clearance`); the rows that are arithmetic or analytic say so. Task 3b-2 completed it with the openings cut.

| Check | Rule | Value | How measured | Result |
|---|---|---|---|---|
| Bounding box (R22) | 95 × 55 × 48 ±1 (plan); R22: 95 × 55 × 51 | 95.00 × 55.00 × 51.00 (x −47.5 … 47.5, y 0 … 55, z 0 … 51) | `measure`, union of the bodies (`test_build_and_bounding_box`) | pass. **Why 51 and not 48 (R22):** the plan's 48 is for a pure single slope. With the 15 mm vertical lower lip that carries the intake slots (R15), the study needs 50.1; the zone wall's ledge between the slots and the LED slot takes 1 mm more. W and D are the plan's. Owner item (R22) |
| Interference with every `ref_*` | 0 overlapping volume (R9) | 0 pairs; 433 bodies checked (all six references, `ref_main`'s 308 included; the keep-outs, air probes incl. the ones in front of the openings, the FFC keep-out and the sweeps), 0 unchecked | `inspect.interference` on the check design at every squeeze 0; each reference's own internal overlaps excluded (`test_no_interference_with_the_references`) | pass |
| Shell's way on (I1) | the shell lowers along −z onto the assembled base | swept boss columns, and the shell, the light guide, `led_mask` and `gap_stop` raised 1–32 mm: 0 overlap | as above (`sweep_*`, `shell_up_*`, `guide_up_*`, `mask_up_*`, `stop_up_*`) | pass |
| Shell clearance (N1, review focus 1) | `clr_remove` off the datums | nudged 0.05: forward, sideways and up 0; back 8.46 mm³ only at y 53.20–53.25 (the rear wall's face); down 10.93 mm³ only at z 1.95–2.00 (the floor) | shell copies moved ±0.05 against the base, the zone wall and the seal (`test_shell_nudged_meets_the_base_only_on_its_datums`) | pass |
| Gaskets touch the SEN66 and the lip | zero gap, zero overlap (R9) | 0 at squeeze 0; at 0.05: ring 5.30, wiper 1.75, ledge seal 4.67, pad 5.00, top seal 3.62 mm³ (contact area × 0.05) | interference at every squeeze 0 and 0.05 (`test_gaskets_touch_what_they_seal`) | pass |
| Seal over the SEN66's depth (I3(b)) | the seals hold at 21.3 ± 0.5, no tipping, the land loaded all round | port face on the ring at every depth; pad 28 / 44 / 60 % compressed (26–53 % with the seat's give); a 21.8 front (plinth, block, plug, bend) meets only the pad (1.9 free), a 20.8 front still meets it (0.9); 0.15 to the guide rail, 0.39 to the slant, the plug 0.29 under the slant's pocket; wiper 0.28–0.54 N, so the ring's reaction stays in the land's kern (5.3) for a pad ≥ 3.1 N; spec 4.7 N at 26 %, ≤ 15 N at 60 % | `ext_*` probes; `sen66_hold` (`test_sen66_at_its_depth_extremes`, `test_sen66_held_over_its_depth_tolerance`, `test_plug_room_at_the_deepest_module`) | pass; the pad's foam to confirm (47–150 kPa) |
| Pad seat (B1) | stiff, tied, not creeping | 2.4 plate joined to the side rail: about 77 N/mm, 0.19 give and 6.6 MPa across the layers at 15 N; 45° lead-in met by the pad at every depth; top 0.8 under the slant | `sen66_hold` (`test_pad_seat_is_stiff_and_tied`) | pass (beam estimate) |
| Inlet seal (B3, B4) | root squeezed, tip lead-in | 2.0 root, 0.05 a side and back (touch 5.51 mm³ at 0.05); 0.8 lead-in at the tip's top > 0.5 preload | `test_inlet_seal_root_and_lead_in`, touch run | pass |
| SFA40 screws and feet (B5) | the screws stay in the posts, the heads clear the desk | M2 × 6: tip z 6.4 in pilots to 7.1, 2.8 of thread, 1.8 under the tongue's pocket; heads 1.2 under the floor, feet 2.0, not over them | `test_sfa40_screws_and_feet` | pass (feet to confirm) |
| Seal forces (round 3) | nothing bows or cracks | zone seal (foam, 25 %) 3–9 N; drawer front 18–35 N, 10–20 N on the sliver, key at 1.7–3.3 MPa; J4 grommet on the lid 0 (contact); top seal 4–15 N | `airq_check.seal_forces` (`test_seal_forces_stay_small`) | pass (estimates) |
| Space beside the ring (round 3) | no short way from it to the inlets | the gap over the module is closed at the wiper's tip; the space reaches only the front plenum, 21 mm through 5.1 + 11 mm² of slits, ≥ 80 mm of intake stream from the inlets | `test_space_beside_the_ring_is_closed` | pass |
| Grommets (I2, N4, B6) | split, squeezed, held | six halves; each touches its opening at 0 and overlaps it at its squeeze (0.32–1.34 mm³ at 0.05); drawer ribs 0.45 proud of the printed face; bores 0.2 under the cables | touch run (`test_grommets_touch_what_they_seal`, `test_grommets_squeeze_and_are_held`) | pass |
| Plugs through their openings (I2) | every plug fits every closed opening it passes | the lid's hole 6.4 × 3.35 passes the Qwiic plug 6.0 × 2.95 (0.2 a side); the drawer and the J4 notch are open to an edge, so no plug passes them | the plug's section swept through the lid; open-edge probes (`test_plugs_pass_their_openings`) | pass |
| Gravity-only parts (N5) | held, not just resting | zone wall clamped by the board's screws; lid and SFA40 by two screws from below; tongue in its pocket under a pad (`clr_align`) | `test_gravity_parts_are_held` | pass |
| HCHO window (N2) | does not open the electronics zone | each step backed by the rail and the zone wall but at its slot (fill = need: 2.80, 5.29, 7.79, 10.28, 10.22 mm³); 0 against the shell | `win_*` probes (`test_hcho_window_is_backed`) | pass |
| Rebuild over the parameter range (`check_parameters`) | `wall` 1.6 and 2.4, each `clr_*` ±0.1: no errors | no feature errors or warnings, 21 bodies each (every opening included), volume back to the default after each. Open areas at those states, from the parameters: intake 155.8 / **151.9** (wall 1.6 / 2.4), 155.3 / **154.3** (`clr_remove` 0.1 / 0.3); outlet 664.3 and HCHO 66.1–72.8 hold | `parameters.change` + `document.inspect` walk (`test_rebuilds_over_wall_and_clearances`); areas from `airq_check.distances` with the constants moved | pass (rebuild). The intake rows' margin is 0.3 at the defaults; it is lost at wall 2.4 and `clr_remove` 0.3 (the rows run between the boss pockets, which move with both): owner item |
| Intake path (R25) | ≥ 77.3 | gap at the inlets 80.7; in front of the SEN66 114.4; over the HCHO lid 411.6 | free probe boxes, sections from `measure` (`test_air_paths_are_free_sections`) | pass |
| Outlet path (R25) | ≥ 330.1 | ring bore 346.4; plenum branches (section / share of 330.1 by grille slots): ring to H1 235.7 / 226.9, at H1 204.6 / 185.7, right of H1 224.1 / 165.1 | as above | pass |
| HCHO path (R25) | ≥ 27.4 (the SFA40's opening) | over the cap 35.6; window into the chimney 47.2; chimney 30.3 | as above | pass |
| Outlet grille (R18, R26) | ≥ 660.1 (2 × 330.1), lower edge ≥ 10 | **664.32** measured (32 slots × 1.2 × 17.3, x −41.9 … 33.7, z 10.0 … 27.3, in the rear wall behind the plenum plate); 2.01 × the port | open area = (probe volume − overlap with `base_plate`) / wall, probe `op_outlet` (`test_openings_measured_open_areas`); the air behind it (probe `air_outlet_grille`, 3 mm deep over the slots) is free | pass, margin 4.2 |
| Intake rows (R18, M6) | ≥ 154.5 (2 × 77.3), lower edge ≥ 10, only slots facing free air | **154.80** measured (14 slots in two rows, 5 + 2 per row each side of the light-sensor window, 1.2 high, 1.2 bars, z 10.0 … 13.6 under the ledge at 13.8); 2.00 × the port. The air behind all of them is free to the tongue's front edge (probe `air_slots_front`, 4.6 deep); the slots in front of the tongue (x 12.8 … 34.8) breathe through the 4.6 channel and its exits (M4: exits 48.0 ≥ 35.3) | `op_intake_l/r` probes as above; `air_slots_front` interference 0 | pass, small margin 0.3 |
| HCHO grille (R26) | ≥ 2 × the SFA40's opening (54.7), lower edge ≥ 10, aligned with the shell's window | **67.81** measured (5 slots 4.16, 9.15, 14.14, 19.13, 21.24; z from 10.0, tops follow the zone wall's underside less 1.2), 2.5 × the opening. The shell's side window covers each slot's step (N2 probes `win_0 … win_4`: 0 against the shell, rail and zone wall behind it) | `op_hcho_1 … 5` probes (cut in 3a); `test_hcho_window_is_backed` | pass |
| Tongue's slots (M4) | the slots in front of the tongue stay open | channel exits 48.0 ≥ the slots' 35.3 | probes `air_tongue_*` | pass |
| Antenna to SEN66 (R12) | ≥ 15 | **17.39** between the antenna strip's probe solid (`cl_antenna`, from `interface.yaml`) and the SEN66's body; 16.72 as the box arithmetic | `inspect.clearance` on the check design (`test_distances_on_the_geometry`); `airq_check.distances` | pass |
| Antenna to the USB plug and cable (R12) | ≥ 15 | **18.55** to the 12.5 × 7 overmold out the rear (`usb_plug_w`, `usb_plug_h`, typical, to confirm) | `inspect.clearance`, probe `cl_usb_plug` | pass |
| Antenna to the inserts and screws (R12) | ≥ 15 | **45.54** (the three shell insert bosses), **21.6** (the standoffs' M2 screws) | `inspect.clearance`, probes `cl_boss_*`, `cl_screw_*` | pass |
| Antenna to the SFA40 | its metal is kept out of the 15 mm too | 28.5 | arithmetic from the parameters (`airq_check.distances`), not measured on the geometry | pass |
| Tongue to U3 / U2 | ≥ 20 | **21.26 / 29.71** (U2 from `layout.yaml` and its courtyard) | arithmetic on the parameters: `inspect.clearance` between probe boxes built from them (the kernel measures the boxes, not a model of the part's shape) | pass |
| Support boss near the USB-C (M7) | within 8 mm, stiff | H1: 7.7 to J1's centre, 3.2 to its shell; braced by the plenum plate, 2.1 mm free | arithmetic from the parameters (`airq_check.distances`), not measured on the geometry | pass |
| Antenna end to the rear wall | inside the case | 0.58 mm at the default wall. At wall 2.4 the inner face reaches the strip, so D needs +0.1 there | arithmetic | pass at the default, note at wall 2.4 |
| Openings' lower edges (review focus 4) | every opening's lower edge ≥ 10 above z = 0, feet not counted | intake rows 10.0, light-sensor window 10.49, outlet 10.0, HCHO 10.0, exhaust 37.0, USB-C 30.48; the shell's: screen window 21.38 (at the face), LED slot 15.40 (inner edge), flexure U-slot 23.01 (inner edge). Below the line the lip, the rear wall, the rail and the shell's right wall are whole (open volume 0) | cut features' lower edges (`test_openings_are_cut_where_the_parameters_say`, `test_shell_openings_are_above_the_10_mm_line`: arithmetic from the parameters); slabs z 0 … 10 over each wall are all material (probes `low_*`, `test_nothing_opens_below_the_10_mm_line`) | pass |
| Light-sensor window | in front of the VEML7700, free line to it | ⌀ 2.5 hole at x 16.4, z 11.74 (centre = the tongue's window, R27) in the lip's gap in the rows; open area 4.91 = π ⌀² / 4; the line from the window to the tongue's front edge is free (probe `air_lsw`, interference 0); window's lower edge 10.49 | `op_lsw` probe; `air_lsw` | pass |
| USB-C opening (review focus 5) | on J1's plug axis, passes the overmold, 0.5 chamfer | 12.9 × 7.4 (the 12.5 × 7 overmold + `clr_remove` a side) centred on x 1.4, z 34.18 (J1's axis); chamfer 0.5 on the outer edge: the wall keeps 5.408 mm³ over the chamfer's depth against 5.414 for the frustum; the probe 0.05 under the opening meets nothing, the one 0.05 over meets the 2.550 mm³ ring, so the opening is within 0.05 of its place and size; J1's shell axis is free to the outside (`air_usb_axis`); lower edge 30.48, 0.22 under the zone wall's top (opens only the dead-end 0.2 slit over the rib, not the sensor zone) | probes `usb_in`, `usb_out`, `usb_cham`, `air_usb_axis` (`test_usb_opening_fit_and_chamfer`) | pass; overmold size to confirm |
| Upper-rear exhaust | stays apart from the outlet (R26), faces free air | 14 slots 1.2 × 10 at x 9.4 … 41.8, z 37.0 … 47.0, above the antenna module (top 36.9), 168.0 mm²; 9.7 above the outlet grille's top, 1.55 from the USB-C opening | `op_exhaust` probe, `air_exhaust` | pass |
| Light-guide delivery (R48) | D1 and D2 each deliver ≥ 3 % of their emission to the exit, every face bare (no cladding) | bare: D1 **4.27 %**, D2 **4.00 %**; with the 0.2 adhesive pad over the bar's front (worst case): 3.96 / 3.71 %. Every delivered ray reflects at least twice (foot facet, then bottom facet): no straight line runs from an entry face to the exit. Lit x −10.1 … 10.3 of the exit's −13.2 … 16.5 (middle 90 % −6.1 … 7.1); the ends get no direct light | 3-D Monte Carlo ray trace of the guide's four prisms as built: 20 000 Lambertian rays per LED face, Snell and Fresnel at the entry and the exit, TIR at 39.6° on every face, the rest lost (`airq_check.guide_delivery`, `test_guide_delivers_light_to_the_exit`); analytic, not a print | pass; the dim ends and the evenness: owner print item (To confirm) |
| Opaque walls (review focus 3; guide → VEML7700) | ≥ 1.2 of opaque path from any non-exit guide surface to the sensor | 1.20 to the sensor (through the ledge, `zone_seal` and the lip), 1.48 to the lip's window, 1.29 to the crease's front (plugged by `crease_seal`); sources: every non-exit surface of the bare guide and the four LED faces (D3, D4 behind `led_mask`) | analytic 2-D section at the sensor's x with `light_paths` (`test_guide_light_stays_off_the_crease_the_sensor_and_u4`); not a ray trace | pass (margin 0 at the sensor: the slot's `led_f0` was raised 0.3 for it) |
| MS5611 line of sight (R13, R50) | no straight line from the LEDs or the guide to U4's port | 0 of 98 samples on the feet's entry faces (D1, D2, whole faces) and 0 of 21,588 samples on every exposed face of the guide's four prisms whose outward half-space holds U4, the side and end faces included (every 0.25 along x, 41 along each profile edge, a 61 × 61 grid on each end), reach it: the zone wall, the LED bodies, the board, `led_mask` and `gap_stop` stop them. Without `gap_stop`, 125 of them (on the D2 foot's tail-side face, through the D1–D2 gap) would. The 196 LED-face samples: U4 is behind the faces' emission hemisphere (−y) | exact straight lines against the obstacles' boxes, prisms and the zone wall's section, `airq_check.ms5611_sight`, `guide_surface_sight` (`test_guide_light_stays_off_the_crease_the_sensor_and_u4`; arithmetic, not a ray trace in SolidCraft) | pass |
| Clearances are parameters (review focus 1) | every fit is a `clr_*` parameter, swept | `clr_align`, `clr_remove`, `clr_snap` ±0.1 and `wall` 1.6 / 2.4 rebuild every feature, the openings included; the shell nudged 0.05 meets only its datums; the light guide's fits are `clr_align` (tongue in its slot) and `clr_remove` (to the shell, the panel's pad gap, the LED faces) | the rebuild walk and the nudge run above (measured); the guide's fits by arithmetic (`test_guide_fits_come_from_the_clearances`) | pass |
| Intake and outlet separate, gasket faces touch (review focus 2) | no warm or exhaust air to the intake | grilles 51.4 apart on opposite faces (above); the outlet's ring, the inlet wiper, the pad and the seals touch the SEN66 at squeeze 0 and overlap by area × 0.05 at 0.05 | rows above (gaskets, grilles apart) | pass |
| Grilles without feet (review focus 4) | ≥ 10 with the feet off | see "Openings' lower edges" | as above | pass |
| Positions from their sources (R27) | read, not retyped | every board and reference position compared with `interface.yaml`, the references and `layout.yaml` | `test_positions_are_read_from_their_sources`, `test_generator_retypes_no_board_numbers` | pass |
| Intake and outlet grilles apart (review focus 2) | ≥ 20, on different faces | **51.4** between the intake slots' inner faces (y 1.8) and the outlet's (y 53.2), 55.0 outer face to outer face; the intake is in the lip's front face (faces −y), the outlet and the exhaust in the rear wall (+y), the HCHO grille in the right side (+x) | arithmetic: `inspect.clearance` between probe boxes built from the parameters (D − 2·wall), not a model of the part; the faces from the cuts' y (`test_openings_are_cut_where_the_parameters_say`) | pass |

## airQ mini enclosure

The owner chose **69.5 × 50 × 42** (R51): option 1 of "airQ mini (Task 4)" above, the smallest
envelope that keeps every rule. `src/airq_mini.py` builds `airq-mini.sc` on the airQ's
construction: the shell (face, top, sides, printed face down), the base U (floor, lip, rear wall
and the sealed sensor tub), the zone wall, the board above the standing SEN66 and the seals. The
sensor zone is the airQ's mirrored: `enclosure_common` builds it with `hand` +1. Task 4a built the
body and internals. Task 4b added the split light band, the labels, the light-sensor window, the dot
and flexure, the openings and the rest of the check table, on the positions 4a named ("Face and
openings (Task 4b)" below). Task 5b exports every printed part: see "Print and assembly guide (airQ mini)".

Build it with `uv run --with pyyaml python enclosure/build.py airq-mini`, and check it with
`uv run --with pyyaml python enclosure/src/airq_mini_check.py --run`.

### Layout (place a of the study, inlet end left)

| Part | Where (mm) | Source |
|---|---|---|
| Envelope | 69.5 × 50 × 42, 24° face, lower lip **18.0** | R51; the lip is a judgement call (below) |
| Board | horizontal, bottom z 31.0, front edge y 12.01, x −27.25 … 32.75 (against the right wall, `clr_remove`) | `mini_recheck`: the zone rule and the antenna strip's end 0.2 inside the rear wall |
| SEN66 | standing (R17), ports to the rear, inlet end left (square inlet low): x −24.25 … 30.95, y 11.16 … 32.46 | `mini_recheck` place a: the plate just in front of H1's post |
| Intake passage | between the left rail and the module's left end: 6.9 wide, 26.9 tall | study |
| Port gap, plate, plenum | gap 3.0 (y 32.46 … 35.46), plate 1.6, plenum 11.14 deep with H1's post in it (a web joins the post to the plate) | study |
| Outlet ring | x 18.15, z 15.8, bore 21.0 | `ref_sen66` |
| Inlet seal (wiper) | its root 1 mm right of the inlets (x −13.05), the blade leaning 55° to the right | the airQ's, mirrored |
| Tongue | on edge in the passage: board back x −29.2, parts toward the module (0.35 off its end), y 12.9 … 25.9, z 2.15 … 24.15; VEML7700 window at (−25.65, 13.15, 20.5) | below |
| Cables | J2 (SEN66) and J4 (the tongue's Qwiic, R30) leave the board's left edge; both pass the zone wall in one drawer (x −32.75 … −27.2, y 25.31 … 33.11) over the passage's rear | below |
| Bosses | front floor bosses ±30.95, y 4.8 (screws from below, under felt feet); rear boss x −30.45, z 37.7, through the rear wall (R29) | `enclosure_common` (R10b) |

### Judgement calls (Task 4a)

- **Lip 18.0, not the study's 15.5.**
  - The intake rows must open under the zone wall's ledge. At 15.5 only two 1.2 mm rows fit
    between the 10 mm line and the ledge (14.3). Over the 47.5 mm the lip offers between the
    light-sensor window and the right boss pocket, that gives about 105 mm². This is short of
    R18's 154.5 and of its 112 floor.
  - At 18.0 there are three rows (top 16.0, ledge 16.8): 3 × 4 slots × 10.98 × 1.2 =
    **158.0 mm²**.
  - At 15.5, the deepest module's plug corner also sits 0.68 mm inside the slant at place a. At
    18.0 the plug and the cable's bend clear the zone wall by at least `clr_remove`. This is
    measured: a 21.8 mm module's front meets only the pad.
  - A taller lip moves the slope forward at every height, so the board, the antenna and place a
    do not change. R12 stays 10.35 and the outlet stays 498.2.
  - Owner look item: the lip is 43 % of the height, against 37 % at 15.5.
- **The zone wall's slant hugs the slope.** `zw_tf` is `wall + clr_remove`, as in the study: the
  mini has no panel or FFC in front of it. Its ledge therefore ends at y 3.6, in front of the
  boss pockets' back walls (y 8.0 … 9.6).
  - The pockets' inner and back walls rise to the slant's underside, so the slant laps on them.
  - The rails start under the flat part (`rails(slant_front=True)`).
  - The pockets stay on the electronics side; the sensor zone stays closed.
- **H2 has no post.** H2 (x 30.15, y 19.21) lies over the SEN66. Its screw (M2 × 3) goes into
  a blind pilot in the zone wall's pad: 1.6 deep, 0.5 of zone wall left under it, 1.4 mm of
  thread. H1 keeps the airQ's post, collar and spigot, and it is the USB-C support boss (7.73 mm
  from the USB-C's centre).
- **The tongue stands with its VEML7700 high.** With its VEML7700 looking forward and its parts
  toward the module, its handedness puts the 22 mm edge with the VEML7700 at the top. The flipped
  board would face its parts to the rail, and the VEML7700 would look into the left boss pocket.
  - The VEML7700 sits at z 20.5, 12 mm behind the lip.
  - The light-sensor window goes low on the lip, left of the slot rows (`lsw_x` −24.75,
    `lsw_z` 14.0). The line between their centres passes 1.75 under the ledge's back edge (the
    ray from the window's top edge passes 0.28 under it): about 30° down, inside the sensor's
    55° half-angle.
  - 4b places and checks the window.
- **The tongue's mount is a pin (`tongue_mount`).**
  - The pin's spigot sits in a blind hole in the left rail, 0.6 of rail left behind it, so there
    is no leak.
  - Its collar spaces the board's back `clr_align` off.
  - Its shank goes through the tongue's mounting hole.
  - The module's left end, 0.35 away, keeps the tongue on the pin.
  - The floor, 0.15 under the tongue's bottom edge, stops it turning (under 1°).
  - It blocks only 4.4 × 1.8 of the passage.
- **The cables' route.**
  - The SEN66 cable runs from its plug down to the floor and left along the front.
  - It passes behind the left boss pocket into the passage's front and rises in front of the
    tongue (the passage's mouth keeps 89.6 mm² beside it).
  - It runs back over the tongue's top edge and goes up through the drawer to J2.
  - The tongue's Qwiic cable leaves its plug's rear and goes straight up the drawer to J4.
  - A vertical riser across the passage would take 3 × 26.9 mm² of it. So the drawer sits at the
    passage's rear, behind the tongue's plug, and nothing rises beside the tongue.
- **The drawer is a notch in the zone wall's flat part, open to its left end.** The split grommet
  (round 2: three pieces split across y through the two cables' axes, as the airQ's) is squeezed by the
  notch's front and rear faces; the cables go in first with their plugs on, then the pieces, which rest on
  the left rail.
- **The cradle.**
  - The pad's seat lies right of the plug (x 5.75 … 27.75), joined to the right boss pocket's
    inner wall. It does not reach the rail, where it met the shell's right boss: the check design
    found that overlap.
  - The seat's top is its 45° lead-in. It ends 0.9 under the slant.
  - There is no front guide rail: the SEN66 cable runs there.
  - A left stop (1.6 × 2 × 4) at the module's rear-left corner locates its inlet end.
- **Felt feet are ⌀7.5, not the airQ's ⌀10.** They cover the ⌀4.4 heads and stay inside the side
  and front faces. The airQ's ⌀10 overhang is its deferred R35 minor.

### Face and openings (Task 4b)

`src/airq_mini_face.py` builds the band and the labels; `airq_mini.openings` cuts the openings; the
dot and flexure are the airQ's (`airq_face.flex_params`, `flexure`, `orange_dot`) on the mini's SW1.

**The split light band.** In the mini the LEDs stand level with the band, 3.1 mm behind the face
wall's inner face (4a's `led_f` carries their light centre horizontally to the face), so each guide is
a short clear block with a straight path from each LED to its exit:

| Part | What | Fits |
|---|---|---|
| Band slots | through the face wall, perpendicular to it: CO₂ x −22.35 … −1.85, PM2.5 x 4.95 … 25.45, 20.5 long, 2.0 high along the slope (z ≈ 32.7 … 34.5 on the face) | `band_*` (4a; `band_half` 20.5, a judgement call below) |
| `light_guide_co2`, `light_guide_pm` | clear PETG, three prisms each: the **bar** (the tongue in its slot, exit face 0.3 behind the face; the flange behind the wall that stops it going out the front; the body back to y 10.46) and two **feet** that reach back from the bar to the entry faces at y 11.71, in front of their LEDs (D1, D2 / D3, D4), inside each LED face's outline (0.6 in from its −x edge, 0.2 from its +x edge, 0.2 from its top and bottom) | tongue `clr_align` in the slot (sides and ends); flange `clr_align` behind the wall; bar `clr_align` in front of `guide_stop`; feet `clr_align` in the stop's windows; entry faces `clr_remove` + 0.1 in front of the LEDs. Every face bare: no coat, no cladding, no adhesive |
| Band ribs (shell) | the **divider** fills the visible gap (6.8 between the slots) from inside the face wall back to the stop, z 31.08 up to the wall; an **end rib** (1.2) beyond each half's outer end | joined to the shell; 0.38 over the zone wall's top, 1.4 in front of the board's edge |
| `guide_stop` | black closed-cell foam, adhesive, die-cut (bought): 50.2 × 5.1 × **1.2 including the adhesive (+0.1 / −0)**, y 10.61 … 11.81, z 31.08 … 36.15, stuck on the three ribs' back faces, four windows round the feet, 1.6 webs over and between them (review M3) | its back face `clr_remove` in front of the board's edge, the LEDs and J7 (0.1 at 1.3). A thinner stop leaves the feet's entry faces proud of its back face: lines between the guides and to U4 then pass behind it (review round 2) |
| Hold-down pads (shell, review I1) | under the three band ribs and one left of them (x −27.4 … −23.55), standing on the zone wall's flat top (z 30.7, y 7.84 … 10.61) in front of the board's edge | at contact (`hold_squeeze` 0): with H1's clamp they hold the zone wall down against the top seal (`seal_forces`) |

Retention: each guide is caught between the face wall (its flange) and `guide_stop` (its bar's back),
`clr_align` each way, and between the ribs in x. Assembly: shell face down, drop each guide into its
slot, press the stop onto the ribs over the feet.

**Labels** (`label_debossing`): "CO₂" under the left half and "PM2.5" under the right, debossed 0.4,
5 mm tall (the Task 2 coupon's legible size), on the face at f 27.88 … 32.88. The font's own subscript
₂ is 0.58 of the cap height (strokes about 0.40, at the 0.4 nozzle's limit), so the subscript is a plain
4.0 mm "2" (0.8 of the cap height, strokes about 0.54; review M7), its baseline 1.0 under the label's.
It is still under the coupon's 5 mm finding: a first-print check (To confirm).

**Dot and flexure.** The orange dot (⌀4, an AMS colour region) at x 29.75 on SW1's push axis (z 34.3),
top right of the PM2.5 half. The beam is the face wall's 1.0 skin, 4.9 wide (the coupon's), 14.5 long from its root to past the
dot, cut free by a 0.5 U slot; a ⌀2.4 rod from its inner face ends 0.10 in front of SW1's actuator and
bottoms on SW1's body after 0.34 of travel: 0.04 after the switch has bottomed, so the switch's body is
the hard stop (no printed stop gap). Face down, the rod stands 24° off the vertical and the beam is the first layers.

**Openings** (all in `base_plate` but the shell's band slots and U slot):

| Opening | Where | Open area (mm²) | Lowest edge z | Source |
|---|---|---|---|---|
| Intake rows | lip, 3 rows × 4 slots 10.98 × 1.2, z 10.0 … 16.0 under the ledge (16.8), x −22.55 … 24.95 | 158.04 (all facing free air, 2.32 deep to the SEN66 cable's bend) | 10.0 | `airq_mini.py` `openings` |
| Light-sensor window | lip, ⌀2.0 at x −24.75, z 14.0, left of the rows, in front of the VEML7700 (about 30° off its axis) | 3.14 | 13.0 | 4a's `lsw_*` |
| Outlet grille | lower rear wall, 24 slots 1.2 × 17.3, x −29.15 … 27.25, z 10.0 … 27.3, behind the plenum plate | 498.24 (R18 shortfall: < 660.1, > the 296 floor; owner item) | 10.0 | 4a's `out_*` |
| Upper-rear exhaust | 13 slots 1.2 × 7.3, x −2.8 … 27.2, z 31.7 … 39.0, over the zone wall | 113.88 drawn; 84.0 face free air (the six slots over the antenna strip face it 0.2 away below z 35.85) | 31.7 | 4a's `exh_*` |
| USB-C opening | rear wall, 12.9 × 7.4 on J1's axis (x −11.05, z 34.18), 0.5 chamfer outside; H1's post is the support boss (7.73 from J1's centre) | – | 30.48 | 4a's `usb_*` |
| Band slots (shell) | see above | 41.0 each | 31.96 (inner edge) | `airq_mini_face.band_slots` |
| Flexure U slot (shell) | x 26.8 … 32.7 round the beam | – | 22.6 (inner edge) | `airq_face.flexure` |

### Judgement calls (Task 4b)

- **Judgement call: each guide is a bar with two feet, behind a black foam stop.** The LEDs face the
  band's line from 3.1 mm behind the wall, so a block fills the path, but its back would see the
  MS5611 (U4, 22 mm behind the LEDs at their height) over the board everywhere but in front of the
  LEDs. Only the feet, inside each LED face's outline, reach the entry plane; the bar's back and the
  feet's sides are behind `guide_stop` (R13; without it 4,251 of 24,125 samples would see U4).
- **Judgement call: the stop is bought foam, not a rib of the shell.** A printed back wall would sit
  between the guide and its slot on the way in. Foam stuck on the ribs after the guides are in place
  also retains them (no adhesive on a guide, no cladding).
- **Judgement call: the feet's entry faces 0.1 in front of the stop's back face (`lg_ein`).** Coplanar,
  a line between the two halves' feet could run along the stop's back face, behind the divider.
- **Judgement call: `band_half` 20.5, not 21.** At 21 the PM2.5 half's end rib would run 0.1 into the
  flexure's U slot and the face between them would be 1.1 (< 1.2 opaque). At 20.5 both halves stay
  centred on their LEDs: rib 0.15 clear of the slot, 1.35 of face.
- **Judgement call: the CO₂ label's subscript is a separate 4.0 mm "2"** (above; 3.5 before review M7).
- **Judgement call: the exhaust keeps 4a's positions** (z 31.7 … 39.0). The six slots over the
  antenna strip face it 0.2 away below z 35.85; the table counts only the 84.0 mm² facing free air.

### Fix round 1 (review of Task 4)

- **The zone wall is held down at the front (I1).** The board's one screw (H1) clamps it in the mini (H2 is a
  blind pilot, no post), so the shell now holds its front: four pads (under the band ribs, and one left of
  them) stand on its flat top at contact. `airq_mini_check.seal_forces` redoes the airQ's analysis for the
  mini: the top seal pushes up 4.3 N (soft foam, ≤ 30 kPa at 25 %, now the spec) to 14.5 N (firm); the push
  lies 8.2 mm inside the holds' polygon, so every hold pushes down (H1 42 %, the right rib 21 %, the divider
  16 %, the left rib 11 %, the left pad 11 %). As a 20 mm strip between the pads and H1 (the wider plate and
  the board ignored: a bound) the zone wall lifts ≤ 0.09 at the seal and ≤ 0.035 at the plenum plate's lap
  with the soft foam (0.18 / 0.067 firm), and the seal keeps ≥ 34 % compression (20 %). The rail fronts' and
  the boss-pocket rises' laps are under or beside the pads. The drawer grommet's bottom now lands on the rail
  at contact (`drawer_floor_squeeze` 0): squeezed, it would push the zone wall up beside the drawer, outside
  the holds.
- **The intake throat (M1).** All the intake turns into the passage round the left boss pocket's outer corner;
  a 0.9 chamfer there (1.63 of wall left across it) and `intake_throat` (per-z gap to the SEN66's front-left,
  less the cable over its height): **97.5** mm² nominal, **87.1** at the tolerance corner (module on its left
  stop, 21.8 deep), against 77.3. At wall 2.4 it is 57.4: owner item with the intake rows.
- **The drawer grommet's split is pressed shut (M2; superseded in round 2, below).** The outer half reaches the shell's side wall with
  `drawer_squeeze` (a 0.4 lead-in on its top outer edge for the wall coming down past it), so the wall presses
  it onto the inner half and the inner half onto the notch's closed end: the cables' push in the bores cannot
  open the split.
- **`guide_stop`** (M3): 1.6 webs over its windows (top at z 36.15); 1.2 thick including the adhesive, **+0.1 / −0** (round 2: at 1.0 the no-path check finds 2,116 lines in air and R13 99 samples reaching U4).
- **The tongue's pin stays in its hole (M4).** Its shank runs on to `clr_remove` from the SEN66's left end (as
  the left stop): it can slide out at most 0.8 (the tip's gap, the module's float to the right rail, a 0.4 short
  module) of its 1.0 engagement.
- **Opaque parts (M5).** The zone wall is printed in an **opaque filament** (black or dark grey): the light
  checks count it opaque (the 1.92 path to the VEML7700 crosses it). The band's end ribs (1.2) and the gap's
  edges are warm-white shell material, which the Task 2 coupon needed 2.0 of: at 2.0 the gap's dark middle is
  2.8 of its 6.8 (1.2: 4.4), and the end ribs only keep light from the case (no sensor behind them). Recorded
  as a first-print look item; the alternative is an AMS black region round the band.
- **H2's screw is an M2 × 3 (M6).** One 1 mm longer goes through the pilot's 0.5 skin and the 0.3 gap into the
  SEN66's housing (`h2_screw_len`).
- **The CO₂ subscript is 4.0 (M7)**: a first-print check.

### Bodies

| Body | Material | Volume (mm³) | Box min (x, y, z) | Box max (x, y, z) |
|---|---|---|---|---|
| shell | PETG / ASA (warm white) | 14176.3 | −34.75, 0.09, 2.00 | 34.75, 50.00, 42.00 |
| orange_dot | PETG, orange (AMS region of the shell's job) | 7.5 | 27.75, 6.44, 32.23 | 31.75, 8.62, 36.13 |
| light_guide_co2 | PETG, clear / natural | 172.0 | −22.20, 6.87, 31.48 | −2.00, 11.71, 34.60 |
| light_guide_pm | PETG, clear / natural | 172.0 | 5.10, 6.87, 31.48 | 25.30, 11.71, 34.60 |
| guide_stop | black closed-cell foam (bought) | 273.4 | −23.55, 10.61, 31.08 | 26.65, 11.81, 36.15 |
| base_plate | PETG / ASA | 19853.1 | −34.75, 0.00, 0.00 | 34.75, 50.00, 40.00 |
| zone_wall | PETG / ASA, an **opaque filament** (black or dark grey: the light checks count it opaque, review M5) | 5942.7 | −32.75, 2.19, 16.80 | 32.75, 48.00, 31.00 |
| tongue_mount | PETG | 46.6 | −32.15, 21.00, 4.35 | −24.45, 25.60, 8.95 |
| gasket_out | TPU 95A | 424.1 | 6.15, 32.46, 3.80 | 30.15, 36.46, 27.80 |
| gasket_in | TPU 95A | 197.3 | −13.10, 31.96, 1.00 | −6.66, 36.51, 28.90 |
| grommet_zone_a | TPU 95A | 39.1 | −32.95, 24.86, 28.90 | −29.50, 33.56, 30.70 |
| grommet_zone_b | TPU 95A | 22.9 | −29.50, 24.86, 28.90 | −27.20, 33.56, 30.70 |
| sen66_pad | foam (bought) | 320.0 | 13.15, 9.36, 10.80 | 23.15, 12.56, 20.80 |
| sen66_foam | foam (bought) | 1175.8 | −24.25, 11.16, 2.00 | 30.95, 32.46, 3.00 |
| sen66_top_seal | closed-cell foam (bought) | 43.4 | −9.05, 11.16, 28.60 | −5.66, 32.46, 29.20 |
| zone_seal | closed-cell foam (bought) | 100.4 | −26.15, 1.40, 16.80 | 26.15, 3.00, 18.00 |

The seals are modelled free (their squeeze as printed or bought). The check design sets every
squeeze to 0.

### Check table (airQ mini)

Task 4a started this table; Task 4b completed it with the openings, the band, the window, the dot and
the no-straight-path check. "How" says how each value was got: **measured** on the geometry (the check
design, `airq_mini_check --run`), **analytic** (a model of the physics in Python, not a print) or
**arithmetic** (from the parameters, or exact lines against the parts' prisms in Python).

| Check | Rule | Value | How | Result |
|---|---|---|---|---|
| Bounding box | 69.5 × 50 × 42 (R51) | 69.50 × 50.00 × 42.00, 16 bodies | **measured**: `measure`, union of the bodies (`test_build_and_bounding_box`) | pass |
| Interference with every `ref_*` | 0 (R9) | 0 pairs; 413 bodies (`ref_sen66`, `ref_tongue`, `ref_main` with its 308, the guides, the stop, the keep-outs, the air probes incl. those behind the openings, the sweeps), 0 unchecked | **measured**: `inspect.interference` at every squeeze 0 (`test_no_interference_with_the_references`) | pass |
| Shell's way on (I1) | lowers along −z | boss columns swept; the shell, both guides and `guide_stop` raised 1–32 mm: 0 | **measured** (`sweep_*`, `shell_up_*`, `gco2_up_*`, `gpm_up_*`, `gstop_up_*`) | pass |
| Shell clearance (N1, review focus 1) | `clr_remove` off the datums | nudged 0.05: forward, sideways, up 0; back 6.84 mm³ only at y 48.20–48.25 (rear wall); down 10.03 mm³ only at z 1.95–2.00 (floor) and 1.81 on the zone wall's top under the hold-down pads (review I1) | **measured** (`test_shell_nudged_meets_the_base_only_on_its_datums`) | pass |
| Seals touch (R9, review focus 2) | zero gap, zero overlap | at 0.05: ring 5.30, wiper 1.75, wiper root 5.51, ledge seal 3.14, pad 5.00, top seal 3.62, grommets 0.33 / 0.96 (zone wall), 0.63 (rail), 0.62 (outer half on the shell's side wall, review M2); the shell's hold-down pads on the zone wall 1.81 (review I1) mm³ | **measured**: squeeze 0, then 0.05 (`test_seals_touch_what_they_seal`) | pass |
| Port groups sealed (I3) | inlets apart from the outlet and the case | ring round the outlet into the plate; wiper between the inlets and the ring; top seal over the module at the wiper's tip; sensor tub one print, the zone wall lapped on it and held down (next row), the ledge sealed to the lip | **measured** (touch run); the closure **analytic** (next row) | pass |
| Zone wall held down (review I1) | the top seal, the zone seal and the laps stay closed | H1's clamp and four shell pads at contact (touch 0.05 run: the pads overlap the zone wall; the −z nudge meets it only on its top). Top seal 4.3 N (soft foam, the spec) … 14.5 N (firm), 8.2 mm inside the holds, every hold pushing down (H1 42 %, pads 11–21 %); lift ≤ 0.09 at the seal, ≤ 0.035 at the plenum plate's lap (firm: 0.18 / 0.067), seal ≥ 34 % compressed (firm 20 %); zone seal 1.9–6.3 N and the drawer grommet's faces 5.3–10.2 N push sideways (no lift); the grommet's bottom at contact (0 N up) | **measured** (pads touch, nudge); forces and lift **analytic**: rigid plate on equal springs for the split, a 20 mm PETG strip between the pads and H1 for the lift, the plate's width and the board ignored (a bound; `seal_forces`, `test_zone_wall_is_held_down`) | pass; the pads' contact and the laps: first-print check |
| SEN66 depth extremes (I3(b)) | 21.3 ± 0.5 held, nothing but the pad met | 21.8 front (plinth, block, plug, bend) meets only the pad, 1.90 deep; 20.8 still meets it, 0.90 | **measured**: `ext_*` probes (`test_sen66_at_its_depth_extremes`) | pass |
| Intake path (R25) | ≥ 77.3 | port gap 80.7; in front of the module, over its cable 101.6; passage mouth beside the cable's drop 89.6 | **measured**: free probes (`test_air_paths_are_free_sections`) | pass |
| Intake throat (R25, review M1) | ≥ 77.3 | the turn into the passage round the left boss pocket's chamfered corner: **97.5** nominal, **87.1** at the tolerance corner (module on its left stop, 21.8 deep), the SEN66 cable counted as blocking its whole height | **arithmetic**: per-z gap to the SEN66's front-left (foam, block, plinth, corner fillets), 0.01 steps (`intake_throat`, `test_intake_throat_keeps_r25`) | pass (57.4 at wall 2.4: below) |
| Passage with the tongue in it (R25) | ≥ 77.3 | at the VEML7700 125.4, middle 144.5, pin 121.8 (its shank now runs to the module, review M4), socket 129.9, plug 145.2, Qwiic turn **107.8**, left stop 112.7 | **measured**: 0.5 mm slabs across the passage against the tongue's STEP, its pin and the cables' keep-outs (`test_passage_keeps_r25_with_the_real_tongue_in_it`) | pass. As an envelope (4.6 × 22, collar, cable) it is 69.1 on paper (**arithmetic**); the real board is sparse |
| Outlet path (R25) | ring ≥ 330.1; branches ≥ their share | ring 346.4; plenum left of the ring 297.1 ≥ 192.6; behind H1 166.7 ≥ 41.3 | **measured** probes; shares **arithmetic** (slots left of the cut) | pass |
| R18 intake | ≥ 154.5, only slots facing free air | **158.04** (12 slots 10.98 × 1.2, three rows z 10.0 … 16.0); the air behind every slot is free to 0.1 in front of the SEN66 cable bend's keep-out (2.32 deep; probe `air_slots_front` 0) | **measured**: `op_intake` (probe volume − overlap) / wall (`test_openings_measured_open_areas`) | pass (margin 3.5) |
| R18 outlet | ≥ 660.1 (floor 296) | **498.24** (24 slots × 1.2 × 17.3); the air behind it free (`air_outlet_grille`) | **measured**: `op_outlet` | owner item (R18 shortfall, as the study) |
| Light-sensor window | in front of the VEML7700, a free line to it | ⌀2.0 at x −24.75, z 14.0; open 3.14; 12 free boxes along its line to the VEML7700's window (`air_lsw_*`), which passes under the ledge (z 15.5 at its front face, ledge 16.8), right of the boss pocket; about 30° off the sensor's axis | **measured** (`op_lsw`, `air_lsw_*`); the line's height **arithmetic** (`test_labels_and_light_sensor_window`) | pass; lux to calibrate on the prototype |
| Upper-rear exhaust | over the zone wall, apart from the outlet (R26), facing free air | 13 slots 1.2 × 7.3, z 31.7 … 39.0: 113.88 drawn, **84.0** facing free air (`air_exhaust_left`, `air_exhaust_top`: 0); 4.4 above the outlet's top | **measured** (`op_exhaust`, air probes) | pass |
| USB-C opening (review focus 5) | on J1's axis, passes the overmold, 0.5 chamfer, support boss | 12.9 × 7.4 on x −11.05, z 34.18; the probe 0.05 under it meets nothing, the one 0.05 over meets the 2.550 mm³ ring; the chamfer leaves 5.408 mm³ against 5.414 for the frustum; J1's axis free (`air_usb_axis`); H1's post (the support boss) 7.73 from J1's centre | **measured**: `usb_in`, `usb_out`, `usb_cham` (`test_usb_opening_fit_and_chamfer`); H1 **arithmetic** | pass; overmold size to confirm |
| 10 mm rule (review focus 4) | every opening's lower edge ≥ 10, feet not counted, shell openings included | intake 10.0, window 13.0, outlet 10.0, exhaust 31.7, USB-C 30.48; the shell's band slots 31.96 and the flexure's U slot 22.6 (inner edges). Slabs z 0 … 10 over the lip, the rear wall, both rails and both shell side walls are all material (the left rail less the tongue pin's blind hole, 1.0 deep, 0.6 of rail behind it) | **measured**: `low_*` probes (`test_nothing_opens_below_the_10_mm_line`); the edges **arithmetic** (`test_openings_are_cut_where_the_parameters_say`, `test_dot_and_flexure_on_sw1s_axis`) | pass |
| Intake to outlet (review focus 2) | ≥ 20, different faces | **46.4** between the intake's and the outlet's inner faces; intake in the lip (front, −y), outlet and exhaust in the rear wall (+y) | **measured**: `inspect.clearance` between the opening probes (`test_intake_and_outlet_apart`) | pass |
| R12 antenna to SEN66 | ≥ 15 (maximise) | **10.35** | **measured**: `inspect.clearance` | owner item (RSSI on the prototype) |
| R12 antenna to USB plug, inserts, screws | ≥ 15 | 18.55, 41.25, 21.6 | **measured** | pass |
| Tongue to U3 / U2 | ≥ 20 | 39.27 / 24.18 | **measured** | pass |
| Tongue in the intake air | in the intake stream | in the passage, which every inlet draws through | **analytic**: the passage is the only way from the slots to the port gap (the study) | pass |
| Split band | two halves about 21, gap ≥ 4, opaque wall ≥ 1.2 | 20.5 each (CO₂ over D1/D2, PM2.5 over D3/D4, centred); visible gap 6.8, filled by the divider rib (6.8); end ribs 1.2; `guide_stop` 1.2; 1.35 of face between the PM2.5 slot and the flexure's slot | slots **measured** (`fp_slot_*` open, `fp_ring_*` 3.842 mm³ each = the slot's exact size); walls **arithmetic** (`test_opaque_walls`) | pass |
| `guide_stop` tolerance (review round 2) | the light checks hold over its tolerance | specified 1.2 **+0.1 / −0** including the adhesive; at 1.3: no-path 0 lines in air, hull 0 uncovered, R13 0 samples reach U4, its back face 0.1 from the board and the LEDs; at 1.0 (the old −0.2) 2,116 lines in air and 99 samples reach U4 | **arithmetic** (`test_stop_tolerance_keeps_the_light_checks`) | pass |
| No straight path between the guides | no line of air or light from one guide to the other | sampled: 326,041 lines from every exposed face of `light_guide_co2` to every exposed face of `light_guide_pm`: 0 in air, the least through **6.80** of opaque (the divider's width). Exact: the convex hull of the guides' profile (30,655 points at 0.02) lies wholly inside the rib, the face wall and the stop over the whole divider gap, so every line crosses ≥ 6.8 of opaque | **arithmetic**: exact straight lines against the parts' prisms (`guide_to_guide`, `test_no_straight_path_between_the_guides`) | pass |
| The gap stays dark | ≥ 1.2 of opaque from either guide to the gap's face | ≥ **1.20** from every guide face to the gap's outer face over its middle 4.4 (all but 1.2 at each slot's end, where the slot's own end wall is the light's way); at the coupon's 2.0 for warm white, its middle **2.8** (review M5) | **arithmetic** (`gap_dark`, `test_visible_gap_stays_dark`) | pass at 1.2 (dark 4.4 ≥ 4); first-print look item at 2.0 |
| Light delivery (R40, R48) | each LED ≥ 3 % to its exit, every face bare | D1 **10.68 %**, D2 **10.37 %**, D3 **10.64 %**, D4 **10.53 %** of their emission; about half of the delivered rays straight (no reflection). Lit x: CO₂ −18.44 … −5.47 (middle 90 % −16.27 … −7.49) of the visible −22.35 … −1.85; PM2.5 9.13 … 21.75 (90 %: 10.91 … 19.87) of 4.95 … 25.45: the halves' last ≈ 4 mm at each end get no direct light | **analytic**: 3-D Monte Carlo ray trace of each guide's three prisms as built, 20 000 Lambertian rays per LED, Snell and Fresnel at the entry and the exit, TIR at 39.6° on every face, the rest lost (`guide_delivery`, `test_guides_deliver_light_with_every_face_bare`); not a print | pass; the dim ends and the evenness: owner print item |
| No cladding on light-path faces (R40, R48) | no coat, no optical contact | every guide face bare; the nearest solids `clr_align` away (wall, slot, ribs, stop), the LEDs `clr_remove` + 0.1 | **arithmetic** (`test_guide_fits_come_from_the_clearances`) | pass |
| Opaque walls to the light sensor (review focus 3) | ≥ 1.2 of opaque from any guide face or LED face to the VEML7700, its window and the crease | sensor **1.92** (through the zone wall), the window's outer face **3.30**, the crease's front **6.44**; counted: the lip, the zone wall (ledge, slant, flat part), `zone_seal` (foam), the shell's wall (less the labels' 0.4) and ribs, `guide_stop`; the crease's 0.2 parting line as air | **arithmetic**: exact straight lines against the parts' prisms (`light_paths`, `test_light_stays_off_the_sensor_its_window_and_the_crease`); not a ray trace | pass |
| MS5611 line of sight (R13, R50) | no straight line from a LED or guide face to U4 | 0 of **24,125** samples on every exposed face of both guides whose outward half-space holds U4's port (bars, feet, sides, ends, entry faces; every 0.25 along x, 41 along each profile edge, a 61 × 61 grid on each end) reach it: the LED bodies, the board, the ribs and `guide_stop` stop them. Without `guide_stop` 4,251 would. The LED faces emit away from U4 | **arithmetic** (`ms5611_sight`, `test_ms5611_sees_no_led_or_guide`) | pass |
| Labels | "CO₂" and "PM2.5", 0.4 deep, ≥ 5 tall | 5.0 tall, the subscript 4.0 (review M7; first-print check); debossed exactly 0.4 (the 0.05 under them is all shell); letters 19.4 / 32.9 mm² | **measured**: `fp_label_*` probes (`test_face_probes`) | pass |
| Dot and flexure | on SW1's axis, stop on SW1's body, printable face down | dot at x 29.75, z 34.3 (SW1's actuator); beam the 1.0 skin (`fp_beam` 3.9 mm³ = 3.9 × 1 × 1.0); rod end 0.10 in front of the actuator (`fp_pad_end` 0.1, `fp_pad_gap` 0); stop 0.34, 0.04 past the switch's travel; rod 24° off vertical face down | **measured** probes; the stop **arithmetic** (`test_dot_and_flexure_on_sw1s_axis`) | pass; feel at the first print (R43) |
| Plug room | 5.0 envelope | J2 5.85, J4 6.14 | **arithmetic**; plug keep-outs **measured** clear of `ref_main` | pass |
| Cables installable with plugs on | split grommets, open-edge drawer | drawer open to the zone wall's left end: way out 0; the split pressed shut by the shell's side wall (the outer half touches it: 0.05 run), the bottom at contact on the rail (review M2) | **measured**: `edge_drawer` (`test_drawer_opens_to_the_side`), touch run; the split **arithmetic** (`test_drawer_grommet_split_is_pressed_shut`) | pass |
| Tongue pin retained (review M4) | the pin stays in its blind hole | its tip `clr_remove` from the SEN66's end: out at most 0.8 of its 1.0 | **arithmetic** (`test_tongue_on_edge_in_the_passage`) | pass |
| H2 screw | does not open the zone, does not reach the SEN66 | blind pilot 1.6 in pad + wall, 0.5 left; **M2 × 3 only** (1.4 of thread): 1 mm longer reaches the SEN66 (review M6) | **arithmetic** (`test_h2_lies_over_the_sen66_so_it_has_no_post`) | pass; screw length in the guide and BOM (5b) |
| Clearances are parameters (review focus 1) | every fit a `clr_*` parameter | the guides' fits `clr_align` / `clr_remove` (no literal gap but `lg_ein` 0.1, a sight-line choice); the stop and ribs `clr_remove` off the board, J7 and the zone wall | **arithmetic** (`test_guide_fits_come_from_the_clearances`) | pass |
| Rebuild (`check_parameters`) | `wall` 1.6 / 2.4, `clr_*` ±0.1 | no errors or warnings, 16 bodies, volume back to the default each time | **measured**: `parameters.change` walk (`test_rebuilds_over_wall_and_clearances`) | pass (rebuild) |
| … at those states | the rules keep | intake 159.5 / **153.7** (wall 1.6 / 2.4), 158.8 / 157.3 (`clr_remove` 0.1 / 0.3); passage 7.3 / **5.7**; the intake throat at wall 2.4 **57.4** (47.9 at its tolerance corner), under 77.3 (review M1; the old "≈ 75 at the Qwiic turn" was not the narrowest place); J2 room 6.25 / **4.65**; collar 2.2 / 0.6; at wall 2.4 the band's slot is 0.6 deeper and the LEDs 0.6 nearer (the board follows the rear wall), so the guide's bar tops out at z 33.65 (0.95 under the LEDs' top, `lg_z1`) and the ribs sit `clr_remove` over the zone wall (`rib_z0`); `guide_stop` keeps 1.2 | **arithmetic** from the parameters | wall 2.4 loses the intake, the intake throat (R25) and the J2 margins (owner item, as the airQ's intake at wall 2.4) |
| Felt feet | cover the heads, stay on the face | ⌀7.5 at the front screws, 2.0 thick over 1.2 of head | **arithmetic** (`test_feet_cover_the_screw_heads`) | pass (feet to confirm) |

## Print and assembly guide (airQ)

For one airQ (95 × 55 × 51 mm). The airQ mini (69.5 × 50 × 42, R51) has its own guide, "Print and assembly guide (airQ mini)", below; where the two differ on purpose (foam, feet, the zone wall's and `gasket_in`'s orientation) the mini's guide says so.
Everything below comes from the design and its checks. **Nothing has been printed yet**: the owner's
test print (section 6) is the next step.

### 1. Files

`export/airq-<part>.3mf` and `export/airq-<part>.step`, one file per printed part, written by
`uv run --with pyyaml python enclosure/build.py airq` (the `PRINT_PARTS` table in `src/airq.py` sets
each part's orientation). Each part is already in its **print orientation, sitting on the bed
(z = 0)**, so a 3MF drops straight into Bambu Studio. A part is turned about the world origin and
moved in z only, so its x and y are still the assembly's. Every file is far under 5 MB (R8); the
largest is `airq-base_plate.step`, about 1 MB. Print the 3MF. The STEP is for other CAD.

`shell` and `orange_dot` are one print job: import both and keep their relative place. The dot is an
AMS colour region, flush with the shell's face.

### 2. Printed parts

Material: **ASA if the printer is enclosed, PETG otherwise** ("shell material"). No part needs a
raft; the light guide, `gasket_in` and the tongue grommets want a brim or mouse ears (small
contact, see the table). Layer height, walls and infill are the owner's choice: the design does not depend
on them.

| Part (file) | Qty | Material | Print orientation | Supports |
|---|---|---|---|---|
| `shell` | 1 | shell material, warm white | **face down** on textured PEI: the 30° face on the bed (95 × 69 × 52.6 mm as printed) | **one support, under the adapter holder's arm** (a 62 mm² flat underside at z 5.4, reached from the open bottom). The rest is accepted without support: the face's 0.8 chamfer along the bed edge (132 mm², z 0 … 0.7), a strip under the top wall's inner edge (108 mm², about 30° off horizontal, 95 wide, z 1.6 … 26), the two rear-boss and HCHO-window overhangs of about 60°, and thin symmetric wall strips of 54–60° at the sides (each 24–33 mm²: x ±45.7 … 47.5 at y −14 … −3 and at y −35 … −19). Check them in the slicer preview |
| `orange_dot` | 1 | orange, an AMS colour region of the shell job | as the shell: it prints first, on the bed, flush with the face (a 0.6 deep recess in the flexure's tip) | none |
| `base_plate` | 1 | shell material | floor down, as designed (95 × 55 × 49) | none, but it bridges (649 mm² of flat ceilings above the bed, z 0.4 … 48.9): the intake slots' ceilings (up to 9.4 mm long, in the 1.8 lip), the outlet grille's and the exhaust's slots (1.2 wide, in the rear wall), the USB-C opening's ceiling (12.9 mm wide, z 37.9: the longest bridge, 12.8 measured) and the counterbores. Use bridge settings; the 12.9 mm one is a first-print item |
| `zone_wall` | 1 | an **opaque** filament (black or dark: it is a light barrier) | standing on its right end: the bent profile on the bed, the drawer at the top (18 × 50 × 91 as printed) | one small support under the right boss notch's ledge (a 5 × 2 cantilever) |
| `hcho_lid` | 1 | an opaque filament | top face down, posts up | none (the tongue pocket's floor bridges 13.3 mm) |
| `light_guide` | 1 | **clear or natural PETG**, bare: no paint, coat or cladding on any face (R45) | **standing on its +x end face** (19.3 × 15.3 × 29.7 as printed). Every face of the guide carries some light, so no orientation is scar-free; on its end every optical face (exit, entry faces, both facets, back) is a vertical wall or a facet at 45° or better, except the two feet's +x end faces (R54) | **Supports only under the two feet's +x end faces** (33.7 mm² each, 67.5 mm² in all; `test_light_guide_hangs_only_the_named_faces`). Each is one TIR face of its foot and carries about **35–38 % of the delivered rays** (D1 foot +x end 743 of 1,944 = 38 %, D2 foot +x end 688 = 35 %; the 3-D trace, `airq_check.guide_delivery`). Nothing else hangs: the exit, entry faces, facets and back stay free of support and bare. Contact is 9.4 mm² and the part is 29.7 tall: use a **brim** (or mouse ears) and slow, cool printing. Clear or natural PETG on a smooth plate. First-print item (To confirm): the best orientation is decided at the first print; also try it entry-plane down on a smooth plate, and report brightness
| `gasket_out` | 1 | TPU 95A, opaque (black) | on its seat end (the end that goes into the plate): 24 × 24 × 4 | none |
| `gasket_in` | 1 | TPU 95A, opaque | standing on its floor end: the root foot and the 55° wiper are a vertical prism, the tip's lead-in faces up (27.9 tall) | none. **Brim or mouse ears:** only 7.1 mm² touches the bed |
| `grommet_zone_a`, `_b` | 1 each | TPU 95A, opaque | on the large slanted end face (8.95 × 7.9 × 1.85 as printed); the half-bores lean 30° | none |
| `grommet_j4_a`, `_b` | 1 each | TPU 95A, opaque | split face on the bed, the half-channel down | none |
| `grommet_tongue_a`, `_b` | 1 each | TPU 95A, opaque | split face on the bed (4 tall, 3.3 mm² of contact) | none (the 0.4 barbs overhang 0.5). **Brim or mouse ears** |

TPU: dry the filament and print slowly. The TPU parts are sized with their own squeeze already in
(`gasket_squeeze` and the others; the check design sets them to 0).

(`gasket_in` is the same part as the mini's `gasket_in`, 6.44 × 4.55 × 27.9. The mini prints it on its side, 29.3 mm² of bed and nothing hanging, instead of standing on 7.1 mm²: worth trying here too.)

**Bought, not printed:** `sen66_foam`, `sen66_pad`, `zone_seal`, `sen66_top_seal`, `crease_seal`,
`led_mask`, `gap_stop`. They are cut and stuck on as the assembly says (sizes in "Bodies" above).
Not exported either: the references, the FFC and cable keep-outs and the air probes, which exist only
in the check design.

**Airing.** A new print gives off VOCs, which the SEN66 and the SFA40 would read as air quality. Air
the finished shell, base, zone wall and lid for **several days**, in a ventilated room and out of the
sun, before you trust any VOC or formaldehyde reading. Expect the first days of readings after
closing the case to be high.

### 3. Bought parts, one airQ

| Part | Qty | Notes |
|---|---|---|
| M2 heat-set inserts, 4.0 deep | 3 | In the shell's bosses (hole `insert_d` 3.2; the insert coupon decides it) |
| M2 screws, pan head, head ⌀ ≤ 4.4 | 3 | Shell to base: two from under the floor (front bosses), one through the rear wall (R29). **M2 × 5**: the front hole takes at most 5.6, the rear one 5.0 (use × 4 if the rear one bottoms out). To confirm |
| M2 × 6 self-tapping screws, pan head | 4 | Two clamp the main board and the zone wall into the standoffs' 1.7 pilots (7 deep: × 6 gives 3.6 of thread); two hold the SFA40 and the lid from under the floor (B5: not × 8) |
| Felt feet, ⌀ 10, at least 2.0 thick | 4 | Two at the front cover the screws' heads, two at the rear corners |
| SEN66 module | 1 | 55.2 × 25.6 × 21.3 ± 0.5 |
| SFA40 Qwiic breakout (SparkFun SEN-31669) | 1 | It must have two Qwiic sockets (R30) |
| E-paper panel GDEY029T94, 2.9 in | 1 | Taped into the bezel with 0.1 mm tape |
| FPC adapter, 24-pin 0.5 mm, both ZIFs on the panel side, pins 1:1 | 1 | The model's 12 × 20 mm is a placeholder: choose one, then check it against the holder |
| FFC, **73 mm custom length**, 24-pin 0.5 mm, Type A, 12.5 wide, 0.3 thick, foldable | 1 | ± 1 mm (R49): no stock length fits. Check all 24 conductors after the folds |
| Boards: main and tongue | 1 each | From `hardware/` |
| Qwiic cable, JST SH 4-pin | 2 | Tongue to the SFA40's second socket, and SFA40 to J4. Modelled ⌀ 2.4; the grommets' bores are 0.2 under it |
| SEN66 cable, JST GH 6-pin | 1 | Modelled ⌀ 3.0; the connector's place on the module is to confirm |
| PU foam, adhesive: `sen66_foam` 55.2 × 21.3 × 1 | 1 | Under the SEN66 |
| PU foam, adhesive: `sen66_pad` 10 × 10 × 3.2 | 1 | **Spec:** at least 4.7 N at 26 % compression, at most 15 N at 60 % (47–150 kPa); medium microcellular |
| Closed-cell foam, black, adhesive: `zone_seal` 77.8 × 1.6 × 1.2 and `sen66_top_seal` 3.4 × 21.3 × 0.6 | 1 + 1 | 30–100 kPa at 25 %. (The airQ mini's top seal is softer, at most 30 kPa: do not mix the two stocks) |
| Foam tape, black closed-cell, 0.3 thick: `crease_seal` 95 × 1.7 | 1 | On the lip's top |
| Black closed-cell foam: `led_mask` 9.5 × 2.9 × 4.1 and `gap_stop` 1.3 × 5.0 × 5.6 | 1 + 1 | Stuck to the panel's back on 0.2 mm adhesive pad |
| Adhesive pad, 0.2 mm | 3 | Light guide to panel (the only contact), `led_mask`, `gap_stop` |
| Tape, double-sided, 0.1 mm | 1 | Panel into its pocket |

### 4. Assembly order

Keep the base and the shell separate until step 11.

1. **Inserts.** Heat the three M2 inserts into the shell's bosses (4.0 deep).
2. **Base.** Check the printed base: the slots, the pockets and the standoffs' pilots are clean.
3. **Gaskets.** `gasket_in` down its slot, root first. `gasket_out` into its seat in the plenum plate.
4. **SFA40.** Plug its two cables in. Lay the J4 cable in the wall's notch on `grommet_j4_a`, add
   `grommet_j4_b`, put on `hcho_lid` (the tongue cable through its hole), then drive the two M2 × 6
   screws from under the floor. Fit `grommet_tongue_a/_b` round the cable.
5. **Tongue.** In its pocket in the lid, its cable plugged in.
6. **SEN66.** Stick `sen66_foam` under it, `sen66_pad` on its connector face on the outlet's axis and
   `sen66_top_seal` across its top at the wiper's tip. Lower it, pressed back against the ring, past
   the seat's and the wiper's lead-ins, with its cable plugged in.
7. **Zone wall.** With `zone_seal` stuck on its ledge's front face, onto the spigots and the key. Lay
   the two cables into the drawer from its open end, close `grommet_zone_a/_b` round them and slide
   the pair in together.
8. **Main board.** Then the cables into J2 and J4, and the board's two M2 × 6 screws, which also
   clamp the zone wall.
9. **FFC into J7**, contacts up, latch closed. The shell is off, so J7 is open from above.
10. **Shell, upside down on the bench.**
    - The panel taped into its pocket, its tail folded into the adapter.
    - `crease_seal` on the lip's top (the base's side).
    - The bare clear `light_guide` pushed tongue-first into the LED slot from inside and stuck to the
      panel's back with the 0.2 mm adhesive pad. It hangs by its tongue and the pad until the shell is on.
    - `led_mask` on the panel's back in front of D3 and D4, and `gap_stop` between the D1 and D2 feet
      (0.2 clear of each), both on a 0.2 mm adhesive pad.
11. **Close.** Push the FFC's free end into the adapter's ZIF with the shell held 12 mm over the base.
    Make the FFC's three 45° folds once, over a fold jig, and never flex them again (R42). Lower the
    shell along −z: it stands on the floor, and its sides end against the rear wall. Drive the three
    M2 screws.
12. **Feet.** Stick the four felt feet on, the front two over the screw heads.

**Before power.** Check all 24 FFC conductors for continuity after the folds. The SEN66 must not move
when you press its connector face toward the front.

### 5. Check table

The check table is under "airQ enclosure" → "Check table" below. Each row gives the rule, the value,
how it was measured (on the geometry, or arithmetic) and the result. Re-run the checks with
`uv run --with pyyaml python enclosure/src/airq_check.py --run` and
`uv run --with pytest --with pyyaml pytest tests/enclosure`.

### 6. The owner's test print (next step, not done)

Plan 3 Task 5 Step 2 (ruling R7) needs a printer and the prototype boards, so it has not happened.
Print one airQ from the 3MF files, assemble it with the prototype boards and report. Fix any fit by
**changing parameters only**, then rebuild (`build.py airq`) and re-export. Print the coupons first
if their results (`clr_*`) are still pending.

What to look for:

- **Fits.** The shell on the base (the 0.2 parting line round the lip, the way on), the inserts, the
  screws' lengths, the zone wall's laps, the SEN66 in its cradle, the SFA40 with its lid, every grommet.
- **FFC.** Whether a 73 mm FFC reaches both ZIFs, how the three folds fall, whether the adapter's ZIF
  can be reached at a 12 mm lift, and continuity afterwards.
- **Button.** SW1 through the flexure and the dot: the push is crisp and the beam does not hold the
  switch closed (the stop is the switch body). The face-down flexure at 30° has no coupon, so this
  print is its test.
- **Light guide.** Brightness and evenness along the 30 mm line. The model gives about 4 % delivery
  and light only at x −10 … 10 mm, so expect dim ends of about 9 mm each. Keep the slot, shorten it
  to about 20 mm, or roughen a facet. The best orientation is decided at the first print: try it on its +x end and entry-plane down on a smooth plate, and report which is brighter.
- **Gasket seal.** The outlet ring (smoke at the grille with the SEN66 running: nothing leaks into the
  space beside the ring), the wiper, the pad's force, the seals.
- **Parts list.** Confirm every row of section 3: screw lengths, the insert hole size, the pad foam,
  the SEN66 connector and cable, the adapter, the FFC vendor.
- **Air.** Wait several days before judging VOC readings, and check the Wi-Fi RSSI (R12).

## Print and assembly guide (airQ mini)

For one airQ mini (69.5 × 50 × 42 mm, R51): the screenless wedge with the split CO₂ / PM2.5 light band. Everything
below comes from the design and its checks (Task 5b). **Nothing has been printed yet**: the owner's test print
(section 6) is the next step. The airQ's guide ("Print and assembly guide (airQ)") is the model; where the mini
differs on purpose, this guide says so.

**Owner items that stay open** (all are parameters or look items, none is hidden by the exports):

- **Envelope 69.5 × 50 × 42** (R51), with the **18.0 mm lip** (the study's 15.5 leaves too little for three intake rows).
- **R12:** the antenna is **10.35 mm** from the SEN66 (the rule asks 15). Check the Wi-Fi RSSI on the prototype.
- **R18:** the outlet grille opens **498 mm²** (the rule 660.1, the floor 296). Confirm against Sensirion's guide.
- **Wall 2.4:** at `wall` 2.4 the intake falls to 153.7 mm² (rule 154.5), the intake throat to 57.4 mm² (rule 77.3) and
  J2's room to 4.65 mm. The exports are at the default wall (1.8): do not thicken it without a rebuild.

### 1. Files

`export/airq-mini-<part>.3mf` and `export/airq-mini-<part>.step`, one file per printed part (11 parts, 22 files),
written by `uv run --with pyyaml python enclosure/build.py airq-mini` (the `PRINT_PARTS` table in `src/airq_mini.py`
sets each part's orientation). Each part is already in its **print orientation, sitting on the bed (z = 0)**, so a
3MF drops straight into Bambu Studio. A part is turned about the world origin and moved in z only, so its x and y
are still the assembly's. Every file is under 5 MB (R8); the largest is `airq-mini-base_plate.step`, 0.7 MB. Print
the 3MF. The STEP is for other CAD.

`shell` and `orange_dot` are one print job: import both and keep their relative place. The dot is an AMS colour
region, flush with the shell's face. Everything else prints alone.

The bodies of `airq-mini.sc` are 16: 11 printed (the files above) and 5 bought (`zone_seal`, `sen66_foam`,
`sen66_pad`, `sen66_top_seal`, `guide_stop`). `tests/enclosure/test_airq_mini_exports.py` fails if a body is in
neither list.

### 2. Printed parts

Material: **ASA if the printer is enclosed, PETG otherwise** ("shell material"). No part needs a raft. Layer height,
walls and infill are the owner's choice: the design does not depend on them. Sizes are as printed (x × y × z).
"Hangs" means a face steeper than 45° from the bed over the bed; the numbers are measured on each committed 3MF
(`tests/enclosure/test_airq_mini_exports.py`).

| Part (file `airq-mini-…`) | Qty | Material | Print orientation | Supports |
|---|---|---|---|---|
| `shell` | 1 | shell material, warm white | **face down** on textured PEI: the 24° face on the bed (turn x +114; 69.5 × 56.2 × 50.5 mm). 1,590 mm² on the bed | **None planned; 314 mm² hangs and is accepted. Check it in the slicer preview.** It is: the face's 0.8 chamfer along the bed edge (93 mm², z 0 … 0.7); the debossed labels' and the dot's recess ceilings (53 and 12.5 mm², 0.4 and 0.6 up: they bridge, by design); the side walls' lower front ends (2 × 29 mm², x ±33 … ±34.8, z 1.7 … 8.3) and the front boss notches (2 × 27 and 2 × 8 mm², z 5.4 … 12.4), all ceilings 24° above horizontal on a 1.8 mm wall edge; the rear boss's face (26 mm², z 29 … 32). If the side walls' ends droop, add a support under each |
| `orange_dot` | 1 | orange, an AMS colour region of the shell job | as the shell: it prints first, on the bed, flush with the face (a 0.6 deep recess in the flexure's tip). 4.0 × 4.0 × 0.6 | none |
| `base_plate` | 1 | shell material | floor down, as designed (69.5 × 50 × 40). 3,445 mm² on the bed | none, but it bridges (517 mm² of flat or shallow ceilings above the bed): the intake rows' slots (3 rows × 4 slots, 10.98 mm wide, 1.8 deep in the lip: 237 mm²), the outlet grille's 24 slots (151 mm², 1.2 wide, in the rear wall at z 27.3), the exhaust's 13 slots (28 mm², z 39.0), the USB-C opening's ceiling (12.9 mm wide at z 37.9, 17 mm²: the longest bridge), the two screw counterbores (2 × 10.6 mm², 0.4 up), a 7.4 × 6.0 flat ceiling in the plenum (22 mm², z 27.7, x −22.4 … −15) and the outlet ring seat's lead-in (about 29 mm², 43° from the vertical, z 23 … 28). Use bridge settings; the 12.9 mm one is a first-print item |
| `zone_wall` | 1 | an **opaque** filament (black or dark: it is a light barrier, review M5) | **on its slanted face** (the face that hugs the shell's; turn x +114; 65.5 × 31.0 × 37.4). 772 mm² on the bed. Not the airQ's end-standing (73 mm² under a 65 mm wall) and not flat top down (that floats 2,555 mm² 0.3 over its 31.0 rises) | none. 125 mm² hangs, all shallow ceilings 24° above horizontal and within 1.8 of the bed: the ledge tip (67 mm², the seat of `zone_seal`), the boss notches' ledges (2 × 20 mm²), plus the drawer notch's three groove faces (10 mm², z 23 … 24) and slivers. The flat top (the pads' face) and the underside (the top seal's face) print as steps on walls 24° off the vertical: check their flatness with the feeler at the first print |
| `light_guide_co2`, `light_guide_pm` | 1 each | **clear or natural PETG**, bare: no paint, coat or cladding on any face (R40, R48) | **exit face down on a smooth plate** (turn x +114; 20.2 × 4.1 × 4.4 mm). The exit face is the first layer: 34.3 mm² on the bed. Every TIR face is a vertical wall or a wall leaning up | **Supports only under the two flange fronts** (34.6 mm² in all: 22.5 over the slot and 12.1 under it, parallel to the exit face and 1.6 above it; 0.6 … 1.1 mm wide ledges that may print without any). They carry **none of the light**: of the 5,081 rays each half delivers, 0 touch them (`test_supports_touch_none_of_the_light`). No support touches the exit, an entry face or a TIR face. The faces that do carry light are printed as layer steps, not supported: the entry faces (all 5,081 delivered rays cross them; they face up at 24° from the bed, so they print as shallow steps: the roughest optical faces, a look item), the tongue's lower side (16 %), the feet's bottoms (13 % and 11 %), the feet's ends (3 % each) and the tongue's upper side (1 %). No brim needed (34 mm² contact); a brim of 3 lines helps if the 4 mm tall part lifts. First-print item: the best orientation is decided at the first print (section 6) |
| `gasket_out` | 1 | TPU 95A, opaque (black) | on its seat end (the end that goes into the plate): 24 × 24 × 4 | none |
| `gasket_in` | 1 | TPU 95A, opaque | **on its side** (turn y −90): 27.9 × 4.55 × 6.44, 29.3 mm² on the bed, the 55° wiper lying flat | none (nothing hangs). The airQ's identical part stands on 7.1 mm²; this is easier |
| `grommet_zone_a`, `grommet_zone_c` | 1 each | TPU 95A, opaque | flat as designed: 5.6 × 2.8 / 2.5 × 1.8, the half-bores vertical, 10.1 / 9.6 mm² on the bed | none (each rib's underside, 2.5 mm², 0.7 up) |
| `grommet_zone_b` | 1 | TPU 95A, opaque | flat as designed: 5.6 × 3.5 × 1.8, a half-bore on each face, 14.6 mm² on the bed | none (nothing hangs) |
| `tongue_mount` | 1 (print 3: the pin is 7.7 tall) | shell material | standing on the spigot's end (turn y −90): 4.6 × 4.6 × 7.7, **2.8 mm² on the bed** | none, but **brim or mouse ears**: the collar's underside ring (13.8 mm², 1.4 wide, 1.0 above the bed) hangs round the spigot |

TPU: dry the filament and print slowly. The TPU parts are sized with their own squeeze already in (the check design
sets every squeeze to 0).

**Bought, not printed** (all in "Bodies" above): `zone_seal`, `sen66_foam`, `sen66_pad`, `sen66_top_seal` and
`guide_stop` (die-cut foam). Not exported either: the references, the cable keep-outs and the air probes, which
exist only in the check design.

**Airing.** A new print gives off VOCs, which the SEN66 would read as air quality. Air the finished shell, base
and zone wall for **several days**, in a ventilated room and out of the sun, before you trust any VOC reading.
Expect the first days of readings after closing the case to be high.

### 3. Bought parts, one airQ mini

| Part | Qty | Notes |
|---|---|---|
| M2 heat-set inserts, 4.0 deep | 3 | In the shell's bosses: two at the front, one at the rear (hole `insert_d` 3.2; the insert coupon decides it) |
| M2 screws, pan head, head ⌀ ≤ 4.4 | 3 | Shell to base: two from under the floor (front bosses), one through the rear wall (R29). **M2 × 5**, as the airQ's identical bosses (the front hole takes at most 5.6, the rear one 5.0). To confirm |
| M2 × 6 self-tapping screw, pan head | 1 | **H1**: the board, the zone wall and its pad into the standoff's 6.0 deep pilot (board 1.6 + pad 0.3 + wall 1.8, so 2.3 of thread in the post). It also clamps the zone wall |
| M2 × **3** screw, pan head, self-tapping | 1 | **H2**: into a blind pilot, 1.6 deep, in the pad and the zone wall (0.5 of wall left under it). **M2 × 3 only, 1.4 of thread.** An M2 × 4, or the airQ's M2 × 6, goes through the 0.5 skin and the 0.3 gap into the SEN66's housing (review M6) |
| Felt feet, ⌀ 7.5, at least 2.0 thick | 4 | Two at the front cover the screws' heads, two at the rear corners (the airQ's are ⌀ 10) |
| SEN66 module | 1 | 55.2 × 25.6 × 21.3 ± 0.5, standing, ports to the rear, inlet end left |
| Boards: main and tongue | 1 each | From `hardware/` |
| SEN66 cable, JST GH 6-pin | 1 | Modelled ⌀ 3.0. Its route is about 85 mm (plug, along the floor in front of the module, up the passage's front, over the tongue, up the drawer to J2): choose the length to fit, with no slack in the passage or the throat (review M9) |
| Qwiic cable, JST SH 4-pin | 1 | Tongue to **J4** directly (the mini has no SFA40 breakout). Modelled ⌀ 2.4; the grommets' bores are 0.2 under it |
| PU foam, adhesive: `sen66_foam` 55.2 × 21.3 × 1 | 1 | Under the SEN66 |
| PU foam, adhesive: `sen66_pad` 10 × 10 × 3.2 | 1 | **Spec:** at least 4.7 N at 26 % compression, at most 15 N at 60 % (47–150 kPa); medium microcellular. On the SEN66's connector face on the outlet's axis |
| Closed-cell foam, black, adhesive: `zone_seal` 52.3 × 1.6 × 1.2 | 1 | 30–100 kPa at 25 %. On the zone wall's ledge front face |
| Closed-cell foam, black, adhesive, **soft**: `sen66_top_seal` 3.4 × 21.3 × 0.6 | 1 | **At most 30 kPa at 25 %** (the mini's spec, review I1): the zone wall is held down by only H1's clamp and four pads, so the seal pushes up 4.3 N at most (firm foam would push 14.5 N). **The airQ's top seal is 30–100 kPa: do not mix the two stocks.** To confirm with the foam bought |
| Closed-cell foam, black, **die-cut**, adhesive: `guide_stop` | 1 | **1.2 mm thick including the adhesive, +0.1 / −0**: its front is stuck on the ribs, so a thicker stop moves its back face toward the board (at 1.3 still 0.1 from the board's edge, the LEDs and J7), and a thinner one leaves the light guides' feet standing proud of it (light then reaches the other half and the MS5611). Do not use a thinner foam. Outline 50.2 × 5.07 (x −23.55 … 26.65, z 31.08 … 36.15 as modelled), **four windows 3.5 × 1.9** (x −16.2 … −12.7, −11.1 … −7.6, 11.1 … 14.6, 16.2 … 19.7; z 32.65 … 34.55), webs 1.6 over and between them (`airq_mini_face.stop_windows`). Stuck on the three ribs' back faces |
| USB-C cable | 1 | To J1 through the rear wall's opening (12.9 × 7.4); overmold size to confirm |

None of the airQ's panel parts is used: no e-paper, FFC, adapter, SFA40, lid, `crease_seal`, `led_mask`,
`gap_stop` or adhesive pad (every light-guide face stays bare).

### 4. Assembly order

Keep the base and the shell separate until step 9.

1. **Inserts.** Heat the three M2 inserts into the shell's bosses (4.0 deep).
2. **Base.** Check the printed base: the intake and outlet slots, the pockets, the standoff's pilot and the tongue
   pin's blind hole in the left rail are clean. Press `tongue_mount`'s spigot into that hole (1.0 deep; it can slide
   out at most 0.8, and the SEN66's end holds it once the module is in).
3. **Gaskets.** `gasket_in` down its slot, root first. `gasket_out` into its seat in the plenum plate.
4. **Tongue, before the SEN66.** The pin is 7.7 long and the passage between the rail and the module is 6.9, so the
   tongue cannot go on after the module. Slide it on the pin by its mounting hole (parts toward where the module's
   end will be, the VEML7700 forward), with its Qwiic cable plugged in.
5. **SEN66.** Stick `sen66_foam` under it, `sen66_pad` on its connector face on the outlet's axis and
   `sen66_top_seal` across its top at the wiper's tip. Plug the GH cable into it, then lower it, pressed back against
   the ring, past the seat's and the wiper's lead-ins. Lay both cables toward the drawer (the SEN66 cable over the
   tongue).
6. **Zone wall.** With `zone_seal` stuck on its ledge's front face, onto the standoff's spigot and the key. Lay the
   two cables into the drawer from its open end (the SEN66 cable in front), then slide the three grommet pieces in
   from the open end over the left rail, holding each cable back as its piece passes it: `grommet_zone_a` in front
   of the SEN66 cable, `_b` between the cables, `_c` behind the Qwiic. Their ribs (on a and c) run in the notch's
   grooves; the notch's front and rear faces squeeze the stack, so both splits close round the cables.
7. **Main board.** Then the cables into J2 and J4, and the screws: **H1 an M2 × 6** (which also clamps the zone
   wall), **H2 an M2 × 3**.
8. **Shell, face down on the bench.**
    - Drop each bare clear light guide into its slot from inside, tongue first (`light_guide_co2` left,
      `light_guide_pm` right; they are the same shape).
    - Press `guide_stop` onto the three ribs' back faces over the four feet (windows 0.15 clear of each).
    - Check that the dot and its flexure move freely.
9. **Close.** Lower the shell along −z onto the base: it stands on the floor, the guides' entry faces stop 0.3 in front
   of the LEDs, and the four pads touch the zone wall's top. Drive the three M2 screws. Check the pads with a feeler
   (0.05 mm: they must bear, and the zone wall's laps must stay shut).
10. **Feet.** Stick the four felt feet on, the front two over the screw heads.

**Before power.** The SEN66 must not move when you press its connector face toward the front. Check that J2 and J4
are seated and that the GH cable is not pinched in the passage.

### 5. Check table

The check table is under "airQ mini enclosure" → "Check table (airQ mini)" above. Each row gives the rule, the
value, how it was measured (on the geometry, analytic, or arithmetic) and the result. Re-run the checks with
`uv run --with pyyaml python enclosure/src/airq_mini_check.py --run` and
`uv run --with pytest --with pyyaml pytest tests/enclosure`.

### 6. The owner's test print (next step, not done)

Plan 3 Task 5 Step 2 (ruling R7) needs a printer and the prototype boards, so it has not happened. Print one airQ
mini from the 3MF files, assemble it with the prototype boards and report. Fix any fit by **changing parameters
only**, then rebuild (`build.py airq-mini`) and re-export. Print the coupons first if their results (`clr_*`) are
still pending.

What to look for:

- **Fits.** The shell on the base (the 0.2 parting line, the way on), the inserts, the screws' lengths, the zone
  wall's laps and its drawer, the SEN66 in its cradle, the tongue on its pin, every grommet.
- **Zone-wall pads (review I1).** With a 0.05 feeler: each of the four pads bears on the zone wall's top, the rail
  fronts', the boss pockets' and the plenum plate's laps stay shut, and the top seal and `zone_seal` keep their
  compression. Also the zone wall's flat top and underside, which print as steps on a leaning wall.
- **Seal.** The outlet ring (smoke at the grille with the SEN66 running: nothing leaks into the space beside the
  ring), the wiper, the pad's force, the soft top seal.
- **Light band.** Both halves' brightness and evenness: the model gives about 10.5 % delivery per LED and light only
  at x −18.4 … −5.5 (CO₂, the middle 90 % at −16.3 … −7.5 of the visible −22.35 … −1.85) and 9.1 … 21.8 (PM2.5, 10.9 …
  19.9 of 4.95 … 25.45), so each half's last 4 mm get no direct light and **the dark ends** will look dim. The gap
  between the halves must stay dark (6.8 mm; at warm-white 1.2 its middle is 4.4, at the coupon's 2.0 only 2.8) and no
  light should show across it. Print both guides and report how the exit faces look (smooth plate: clear; textured:
  diffuse). **Best orientation:** the export is exit face down; also try **entry faces down** (10.2 mm² on the bed,
  supports under the back face, 63 mm², which carries none of the light) and **on an end** (12.2 mm², no support at
  all), and report which is brightest.
- **Labels.** "CO₂" and "PM2.5" read at 5 mm, and the **CO₂ subscript (a 4.0 mm "2", strokes about 0.54)**, which is
  under the coupon's 5 mm finding (review M7).
- **Sensor window.** The VEML7700 sees the desk through the ⌀2.0 window, about 30° off its axis (review M8): the lux
  reading, with the LEDs on and off.
- **Button.** SW1 through the flexure and the dot: the push is crisp and the beam does not hold the switch closed (the
  stop is the switch body, 0.04 past its travel). The face-down flexure at 24° has no coupon, so this print is its test.
- **H2.** The M2 × 3 holds in its 1.4 mm of thread, and does not reach the SEN66.
- **Parts list.** Confirm every row of section 3: screw lengths, the insert hole size, the foam (the top seal's
  softness above all), the SEN66 connector and cable, the USB-C overmold.
- **Air.** Wait several days before judging VOC readings, and check the Wi-Fi RSSI (R12, 10.35 mm).

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

These values are parameters, so a correction is a parameter change and a rebuild. The owner's test
print ("Print and assembly guide (airQ)", section 6) is what settles most of them.

**Owner decisions and items**

- **Envelope (R22).** The airQ is 95 × 55 × 51, not the plan's 48: the 15 mm lip that carries the
  intake slots needs it. The pure single slope would be 95 × 63.5 × 50.
- **Rear screw (R29).** One M2 screw head shows on the back (a felt dot could cover it).
- **Tongue Qwiic (R30).** J3 cannot take a plug in the airQ, so the tongue chains through the SFA40
  breakout's second Qwiic socket to J4. Confirm the chosen breakout has two sockets.
- **FFC (R49).** Order a custom 73 mm ± 1 mm, 24-pin 0.5 mm, Type A, foldable FFC.
- **Light-guide print.** Its orientation (the guide proposes its +x end; also try it entry-plane down on a smooth plate, report brightness) and the evenness of the
  30 mm line, as under "The light guide" below.
- **`gap_stop`.** The 1.3 mm foam strip sits in a 1.7 mm gap between the D1 and D2 feet, 0.2 clear
  of each: a touch kills the total internal reflection there. Check its placement on the print.
- **Mask light.** About 2 % of D3's and D4's light passes `led_mask`'s edges into the case.
- **Licence and repo size (R19).** `enclosure/` is CC-BY-SA 4.0; the STEP wrappers are 4.1 MB each.
- **Mini.**
  - Envelope 69.5 × 50 × 42 (R51).
  - Lip 18.0, a look item.
  - R12 10.35 mm: an RSSI check on the prototype.
  - Outlet grille 498 mm² against 660.1: R18, confirm with Sensirion's guide.
  - The VEML7700 sees its window about 30° off-axis: calibrate lux on the prototype. Its line runs about 30°
    down and meets the desk about 26 mm in front of the lip, so the sensor reads that patch of desk, which the
    band partly lights (review M8): calibrate with the LEDs on and off, and consider blanking the LEDs during
    the sensor's integration (a firmware option).
  - The H2 screw takes 1.4 mm of thread in the zone wall: **M2 × 3 only** (an M2 × 4 or the airQ's M2 × 6 reaches
    the SEN66's housing, review M6); check the hold on the print. It is in the guide's list (section 3).
  - The first print's orientations (Task 5b, "Print and assembly guide (airQ mini)" section 6): the light guides
    exit face down (also try entry face down and on the end), the zone wall on its slanted face, `gasket_in` on
    its side, the shell's shallow ceilings (side-wall ends, boss notches) without support.
  - The tongue's Qwiic and SEN66 cable sizes: see "airQ mini enclosure".
  - The SEN66 cable's route is about 85 mm (its plug, along the floor in front of the module, up the passage's
    front, over the tongue, up the drawer to J2): its slack has no recorded place and must stay out of the
    R25-tight passage and throat; choose the cable length to fit (review M9).
  - The tongue's SHT45 faces the SEN66's inlet end about 2.8 mm away: check on the prototype that the module's
    warmth does not bias it (review M9).
  - The zone wall's hold-down pads touch its top at contact (review I1): check with a feeler at the first print
    that the pads bear and the laps (rail fronts, boss-pocket rises, plenum plate) stay shut; the top seal's
    foam is soft (≤ 30 kPa at 25 %, to confirm with the foam bought).
  - The CO₂ label's 4.0 mm subscript (strokes about 0.54) is under the coupon's 5 mm finding: check it reads at
    the first print (review M7).
  - The band's end ribs and the gap's edges are 1.2 of warm-white (the coupon needed 2.0): at 2.0 the gap's dark
    middle is 2.8 of 6.8; look at the first print (review M5).

**FFC and adapter (3b)**

- The adapter: a 24-pin 0.5 mm FPC adapter with both ZIFs on the panel side, pins 1:1 (straight through) and its
  size (placeholder 12 × 20; the FFC ZIF's slot level, 1.0 above the board). A crossed or opposite-side adapter flips
  the contact-side outcome.
- The FFC: 24-pin 0.5 mm, 73 mm, Type A (contacts on the same side at both ends), 12.5 wide, 0.3 thick, 3.5 inserted
  (hardware/README.md:167, :176); a custom length: confirm a vendor makes 73 mm at ±1 mm (the jog takes 70.8 … 75.1 mm
  at 3.5 inserted, 72 … 74 at 3.0 … 4.0, with about 0.1 mm to spare at the extreme corners: 70 and 60 are too short, 80
  and 100 leave 5 and 25 mm of slack with no room for a bow);
  choose an FFC whose datasheet allows folding (three 45° direction-change folds, made once over a jig), or a
  factory-folded one; and check continuity of all 24 conductors on the prototype after the folds, before power.
- **Owner ordering item (R49):** order the FFC as a custom length, 73 mm ±1 mm (24-pin, 0.5 mm pitch, Type A, 0.3 thick,
  foldable), from a vendor that makes custom lengths; no stock length fits the route. If the vendor's tolerance is wider
  than ±1 mm, or the insertion differs from 3.0 … 4.0, re-check the fit (`ffc_len`, `ffc_len_tol`, `ffc_insert_tol`;
  `test_ffc_route_length_and_service_lift`).
- The light guide (R48): print it and look. The 3-D trace (`airq_check.guide_delivery`, every face bare) gives D1 4.3 %
  and D2 4.0 % of their emission at the exit (4.0 / 3.7 % with the adhesive pad over the bar's front), but lights only
  x −10.1 … 10.3 of the 30 mm line (x −13.35 … 16.65; the middle 90 % of the light falls in x −6.1 … 7.1). The ends,
  x −13.2 … −10.1 and 10.3 … 16.5 (about 9 mm), get no direct light and will look dim. Owner print/look item: keep the
  30 mm slot (the plan; a rough facet or a diffuser strip may spread the light) or shorten the visible slot to the lit
  span (about 20 mm, x −10 … 10.5). Also the tongue's fit in its slot (0.15 a side), the facets' print quality and the
  0.2 adhesive pad.
- Deferred to the prototype: how the shell is lifted with the FFC in (layer D curls about 7.5 mm at a 12–15 mm lift; creases
  1 and 2 must not re-flex); whether the adapter's ZIF can be reached at that lift; the stack of `flex_gap` against the
  y tolerances (a negative stack holds SW1 closed, the stop being the switch); SW1's stem protrusion against the 2.4 mm
  rod landing on the body; where the fold jig puts the three folds.
- The button: a coupon of the face-down flexure with the rod at 30° (not yet made); the rod's end bottoms on SW1's body
  0.04 after the switch has bottomed.

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

**airQ cables and plugs** (the check design's keep-outs are envelopes)

- The SEN66's connector: its place on the connector face (x 17–29 from the inlet end, scaled) and
  its mating direction. The keep-out takes a plug 5 mm out of the face with its cable bending down.
- The plugs' sizes (JST GH 6-pin, JST SH Qwiic) and the cables' diameters (`cable_gh_d` 3.0,
  `cable_qw_d` 2.4). The SFA40's rear plug has about 3.0 mm before the pocket's rear wall.
- J3 (the tongue's Qwiic on the main board) cannot take a plug in the airQ: the panel and the
  light guide stand in its path. The tongue chains through the SFA40 to J4 instead (owner item; a
  PCB change could move J3).
- The plug envelopes (`qw_plug_w` × `qw_plug_t` 6.0 × 2.95, `gh_plug_w` × `gh_plug_t`
  10.75 × 4.25) are the receptacle bodies' sections from `interface.yaml`, taken as upper bounds.
  The lid's hole is sized from them.

**airQ SEN66 hold (fix round 2)**

- The pad's foam (`sen66_pad`, 3.2 free, 10 × 10). It must give at least 4.7 N (47 kPa) at 26 %
  compression and at most 15 N (150 kPa) at 60 %, so its force may rise at most 3.2× in between.
  For example, a medium microcellular PU foam with adhesive: check its compression-force curve.
  Check it on the first build: the module must not move when pressed toward the front.
- The ring is a hard stop of TPU 95A at 0.05–0.15 MPa, so it closes little of the print's
  waviness. Check the first print for leaks from the outlet into the space beside the ring, for
  example with smoke at the outlet grille while the SEN66 runs.
- TPU 95A's modulus (26–50 MPa assumed) sets the wiper's push (0.28–0.54 N).
- The seals' foam (`zone_seal` 1.6, `sen66_top_seal` 0.6): closed-cell, black, adhesive-backed,
  30–100 kPa at 25 %.
- The SFA40's screws: M2 × 6 self-tapping pan head (head 1.6) from below, into 1.7 pilots in the
  lid's posts. The felt feet: at least 2.0 thick.

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
