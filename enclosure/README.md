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
| `src/enclosure_common.py` | Shared construction for both enclosures (shell, base plate, zone wall, cradle, gaskets, standoffs, tongue mount) |
| `src/airq.py` | The airQ enclosure's generator: `airq.sc` |
| `src/airq_check.py` | The airQ check design: every reference placed, cable keep-outs, air-path probes, the shell's sweep; interference, sections, gasket contact, distances |
| `src/board_sources.py` | Board positions read from their sources (R27): `interface.yaml` values and comment sizes, and `layout.yaml` placements with footprint courtyards (U2, U4) |
| `airq.sc` | The airQ enclosure design (committed) |
| `src/layout_study.py` | The layout studies' section arithmetic for both models (pure Python; `tests/enclosure/test_layout_study.py`) |
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
- **airQ mini.** It fits its hard maximum, 66 × 50 × 42, only with R15's vertical lower lip (15.5
  mm) and a horizontal board. Two figures fall short and are flagged:
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

**Print split (R24), orientation (fix round 2, N6) and materials (N3).**

| Part | Material | Prints | Supports |
|---|---|---|---|
| `shell` | shell material (ASA/PETG, warm white) | face down on textured PEI | none. Two small overhangs of about 60° are accepted: the rear boss's front disc (⌀6) and the HCHO window's rear edge |
| `base_plate` | shell material | floor down: every wall, post, rib and slot stands vertical; the screw counterbores are on the bed | none |
| `zone_wall` | an **opaque** filament (internal, any colour, e.g. black) | standing on its right end: the bent profile on the bed, the drawer and its grooves at the top, running vertical | one small support under the right boss notch's ledge, a 5 × 2 cantilever |
| `hcho_lid` | an opaque filament | top face down, posts up | none. The tongue pocket's floor bridges 13.3 mm |
| `gasket_out` | TPU 95A, opaque (black) | on its seat end | none |
| `gasket_in` | TPU 95A, opaque | standing on its floor end: the root foot and the 55° wiper are a vertical prism; the tip's lead-in faces up | none |
| `zone_seal`, `sen66_top_seal` | closed-cell foam, **black**, adhesive-backed (bought, cut) | – | – |
| `grommet_zone_a/_b` | TPU 95A, opaque | on an end face: the rib profile on the bed | none |
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
  9. light guides;
  10. shell, lowered along −z;
  11. feet.
- **Fastening:** three M2 screws into heat-set inserts in the shell.
  - Two front floor bosses take screws from underneath, the heads under the felt feet. On the way
    down the bosses pass the zone wall's notches, and they end up standing in the boss pockets.
  - One rear boss under the top wall at the rear left takes a screw through the rear wall (R29).
  - The counterbores leave 1.6 mm of floor under the heads.
- **Way on.** The check design sweeps the shell's bosses from their place up past the top, and
  copies the whole shell raised 1, 2, 4, 8, 16 and 32 mm. None of them meets the base, the zone
  wall, the board, the SEN66, the tongue, the SFA40 or the cable keep-outs. The panel and the
  adapter ride in the shell, so they are left out of that pairing.

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
- FFC: `ffc_len` into `j7_x0` … `j7_x1`. The 100 mm is about 45 of route plus a service loop of
  about 50, so the shell can lie beside the base while the FFC is plugged in;
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
keep-outs (`ko_*`), the air probes (`air_*`) and the shell's sweep (`sweep_*`, `shell_up_*`), at
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
| `light_guide` | clear PETG, standing on its leg ends or lying on its back (the legs are 2 mm bars) | **Opacity: every surface except the four entry windows (each LED face inset 0.4 / 0.2 / 0.2, 0.2 in front of it) and the exit tongue's front face is coated matt black (paint or vinyl tape), so no guide surface sees U4 (R13) or the crease.** Chosen over a printed opaque sleeve or a two-material print: the guide is only 2 mm thick and the coating costs no clearance |
| `crease_seal` | not printed: 0.3 mm black closed-cell foam tape, full width, 1.7 wide, on the lip's top | black |

### Check table

Every row is measured on the geometry where the check design can (probes with `inspect.interference` and `inspect.clearance`); the rows that are arithmetic or analytic say so. Task 3b-2 completed it with the openings cut.

| Check | Rule | Value | How measured | Result |
|---|---|---|---|---|
| Bounding box (R22) | 95 × 55 × 48 ±1 (plan); R22: 95 × 55 × 51 | 95.00 × 55.00 × 51.00 (x −47.5 … 47.5, y 0 … 55, z 0 … 51) | `measure`, union of the bodies (`test_build_and_bounding_box`) | pass. **Why 51 and not 48 (R22):** the plan's 48 is for a pure single slope. With the 15 mm vertical lower lip that carries the intake slots (R15), the study needs 50.1; the zone wall's ledge between the slots and the LED slot takes 1 mm more. W and D are the plan's. Owner item (R22) |
| Interference with every `ref_*` | 0 overlapping volume (R9) | 0 pairs; 419 bodies checked (all six references, `ref_main`'s 308 included; the keep-outs, air probes incl. the ones in front of the openings, the FFC keep-out and the sweeps), 0 unchecked | `inspect.interference` on the check design at every squeeze 0; each reference's own internal overlaps excluded (`test_no_interference_with_the_references`) | pass |
| Shell's way on (I1) | the shell lowers along −z onto the assembled base | swept boss columns and the shell raised 1–32 mm: 0 overlap | as above (`sweep_*`, `shell_up_*`) | pass |
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
| Rebuild over the parameter range (`check_parameters`) | `wall` 1.6 and 2.4, each `clr_*` ±0.1: no errors | no feature errors or warnings, 19 bodies each (every opening included), volume back to the default after each. Open areas at those states, from the parameters: intake 155.8 / **151.9** (wall 1.6 / 2.4), 155.3 / **154.3** (`clr_remove` 0.1 / 0.3); outlet 664.3 and HCHO 66.1–72.8 hold | `parameters.change` + `document.inspect` walk (`test_rebuilds_over_wall_and_clearances`); areas from `airq_check.distances` with the constants moved | pass (rebuild). The intake rows' margin is 0.3 at the defaults; it is lost at wall 2.4 and `clr_remove` 0.3 (the rows run between the boss pockets, which move with both): owner item |
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
| Antenna to the SFA40 | its metal is kept out of the 15 mm too | 28.5 | as above | pass |
| Tongue to U3 / U2 | ≥ 20 | **21.26 / 29.71** (U2 from `layout.yaml` and its courtyard) | `inspect.clearance`: the tongue's envelope against the U3 and U2 probe solids | pass |
| Support boss near the USB-C (M7) | within 8 mm, stiff | H1: 7.7 to J1's centre, 3.2 to its shell; braced by the plenum plate, 2.1 mm free | as above | pass |
| Antenna end to the rear wall | inside the case | 0.58 mm at the default wall. At wall 2.4 the inner face reaches the strip, so D needs +0.1 there | arithmetic | pass at the default, note at wall 2.4 |
| Openings' lower edges (review focus 4) | every opening's lower edge ≥ 10 above z = 0, feet not counted | intake rows 10.0, light-sensor window 10.49, outlet 10.0, HCHO 10.0, exhaust 37.0, USB-C 30.48. Below the line the lip, the rear wall, the rail and the shell's right wall are whole (open volume 0) | cut features' lower edges (`test_openings_are_cut_where_the_parameters_say`); slabs z 0 … 10 over each wall are all material (probes `low_*`, `test_nothing_opens_below_the_10_mm_line`) | pass |
| Light-sensor window | in front of the VEML7700, free line to it | ⌀ 2.5 hole at x 16.4, z 11.74 (centre = the tongue's window, R27) in the lip's gap in the rows; open area 4.91 = π ⌀² / 4; the line from the window to the tongue's front edge is free (probe `air_lsw`, interference 0); window's lower edge 10.49 | `op_lsw` probe; `air_lsw` | pass |
| USB-C opening (review focus 5) | on J1's plug axis, passes the overmold, 0.5 chamfer | 12.9 × 7.4 (the 12.5 × 7 overmold + `clr_remove` a side) centred on x 1.4, z 34.18 (J1's axis); chamfer 0.5 on the outer edge: the wall keeps 5.408 mm³ over the chamfer's depth against 5.414 for the frustum; the probe 0.05 under the opening meets nothing, the one 0.05 over meets the 2.550 mm³ ring, so the opening is within 0.05 of its place and size; J1's shell axis is free to the outside (`air_usb_axis`); lower edge 30.48, 0.22 under the zone wall's top (opens only the dead-end 0.2 slit over the rib, not the sensor zone) | probes `usb_in`, `usb_out`, `usb_cham`, `air_usb_axis` (`test_usb_opening_fit_and_chamfer`) | pass; overmold size to confirm |
| Upper-rear exhaust | stays apart from the outlet (R26), faces free air | 14 slots 1.2 × 10 at x 9.4 … 41.8, z 37.0 … 47.0, above the antenna module (top 36.9), 168.0 mm²; 9.7 above the outlet grille's top, 1.55 from the USB-C opening | `op_exhaust` probe, `air_exhaust` | pass |
| Opaque walls (review focus 3; guide → VEML7700) | ≥ 1.2 of opaque path from any non-exit guide surface to the sensor | 1.20 to the sensor (through the ledge, `zone_seal` and the lip), 1.48 to the lip's window, 1.30 to the crease's open end (plugged by `crease_seal`); the guide's non-window surfaces are coated black | analytic section at the sensor's x with 3b-1's `light_paths` (`test_guide_light_stays_off_the_crease_the_sensor_and_u4`); not a ray trace | pass (margin 0 at the sensor: the slot's `led_f0` was raised 0.3 for it) |
| MS5611 line of sight (R13) | no straight line from the LEDs or the guide to U4's port | 0 of 196 LED-face samples and 0 of 196 entry-window samples reach U4; the LED bodies and the board stop them; the guide's other faces are coated | analytic ray against the LED and board boxes, `airq_check.ms5611_sight` | pass |
| Clearances are parameters (review focus 1) | every fit is a `clr_*` parameter, swept | `clr_align`, `clr_remove`, `clr_snap` ±0.1 and `wall` 1.6 / 2.4 rebuild every feature, the openings included; the shell nudged 0.05 meets only its datums | the rebuild walk and the nudge run above | pass |
| Intake and outlet separate, gasket faces touch (review focus 2) | no warm or exhaust air to the intake | grilles 51.4 apart on opposite faces (above); the outlet's ring, the inlet wiper, the pad and the seals touch the SEN66 at squeeze 0 and overlap by area × 0.05 at 0.05 | rows above (gaskets, grilles apart) | pass |
| Grilles without feet (review focus 4) | ≥ 10 with the feet off | see "Openings' lower edges" | as above | pass |
| Positions from their sources (R27) | read, not retyped | every board and reference position compared with `interface.yaml`, the references and `layout.yaml` | `test_positions_are_read_from_their_sources`, `test_generator_retypes_no_board_numbers` | pass |
| Intake and outlet grilles apart (review focus 2) | ≥ 20, on different faces | **51.4** between the intake slots' inner faces (y 1.8) and the outlet's (y 53.2), 55.0 outer face to outer face; the intake is in the lip's front face (faces −y), the outlet and the exhaust in the rear wall (+y), the HCHO grille in the right side (+x) | `inspect.clearance` between the probes `op_intake_l/r` and `op_outlet` (`test_distances_on_the_geometry`); the faces from the cuts' y (`test_openings_are_cut_where_the_parameters_say`) | pass |

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
