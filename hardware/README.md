# airQ v3 hardware

| Path | What |
|---|---|
| `src/<board>/` | **Design source**: the text files the boards are made from (edit these) |
| `kicad/<board>/` | KiCad 10 projects, **generated** from `src/<board>/` (open these, do not edit the schematics) |
| `kicad/lib/` | `airq` symbol, footprint and 3D library ([README](kicad/lib/README.md)) |
| `bom/parts.csv` | LCSC parts table: JLC Economic status, stock, boards |
| `interface.yaml` | GPIOs, I²C addresses and connector pinouts shared with the firmware |

Boards: `main` (the main board) and `tongue` (the sense tongue: SHT45 and VEML7700 on a 22 × 13 mm
board cabled to the main board's `J_QWIIC_TONGUE`, see below). Both follow the same scheme.

## Toolchain

### Route: an in-repo generator (route c)

The boards are written as YAML in `hardware/src/<board>/`. A small Python generator in `tools/hw/` turns
them into a native KiCad 10 project (hierarchical schematic, board, project settings, library tables), then
runs `kicad-cli` for ERC, DRC, netlist, JLC BOM/CPL, and KiCad's bundled Python for the Specctra DSN.

Why this route: of the three candidates of the plan, it is the only one that passes all five criteria
on this machine without a system change.

| Criterion | How it is met |
|---|---|
| 1. Diffable source the assistant edits reliably | Short YAML files: parts, their pins → net names, page and board positions. The generator rejects unknown keys, pins without a net, off-grid or touching pins with one message per problem. |
| 2. Native KiCad 10 schematic **and** board | KiCad itself saves the schematic sheets and the board (`kicad-cli sch/pcb upgrade --force`, then DRC's `--save-board`), so those files are in KiCad 10.0's own format. The project's library tables resolve every symbol and footprint. |
| 3. ERC and DRC with `kicad-cli` | `kicad-cli sch erc` and `kicad-cli pcb drc --schematic-parity` run on the generated project. |
| 4. JLC BOM and CPL with LCSC numbers | Every part carries an `LCSC` field. `kicad-cli sch export bom` writes JLC's columns, and `pcb export pos` gives the CPL (`tools/hw/jlc.py`). |
| 5. Runs on this Windows machine | Plain Python (uv) + KiCad 10 for Windows. No WSL. |

Rejected candidates:
- **(a) KiCad MCP server** (`greg3001/kicad-claude-mcp`, `mixelpixx/KiCAD-MCP-Server`): it has to be added to
  Claude Code's configuration and needs a session restart, which needs the owner's approval. Subagents
  working on the plan could not use it mid-plan either. The design would also live in KiCad's files
  only, with no short source to review.
- **(b) atopile**: it compiles to a KiCad *board* only and writes no schematic. That fails criterion 2, and it
  cannot feed the schematic-based gates of Task 4 (ERC, netlist check, BOM check). On Windows it would also
  need WSL, a system change. Skipped without installing anything.

### Install

- **KiCad 10.0** (10.0.8 here): the installer from <https://www.kicad.org/download/>. The per-user Windows
  install puts `kicad-cli.exe` and KiCad's Python (with `pcbnew`) in `%LOCALAPPDATA%\Programs\KiCad\10.0\bin`.
  `tools/hw/kicad_env.py` finds them there, in `%ProgramFiles%`, on macOS and Linux, or through the
  `KICAD_CLI` / `KICAD_PYTHON` environment variables. kicad-cli is not needed on PATH.
- **uv** (0.11 here), which provides Python and the YAML reader:
  `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows) or
  `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS, Linux).
- Nothing else for the build. Routing the main board (Task 5) used **Freerouting 2.5.0**, the official
  release JAR from <https://github.com/freerouting/freerouting/releases/tag/v2.5.0>
  (`freerouting-2.5.0.jar`, SHA-256 `f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7`), run with
  Java 25 from `build/tools/` (not committed). It is needed only to route a board again, see "Main board
  layout" below.

### Build and check a board

```
uv run --with pyyaml python tools/hw/build.py main
```

It takes about 4 s. It rewrites `hardware/kicad/main/` and writes to `build/` (not committed):
`main.net` (netlist), `main-erc.json`, `main-drc.json`, `main-bom.csv` (JLC BOM), `main-cpl.csv` (JLC CPL),
`main.dsn` (Specctra DSN for Freerouting). It prints an ERC/DRC summary, lists parts without a placement
entry and Edge.Cuts items drawn in KiCad, and exits 1 on any ERC error or any DRC error other than unrouted
connections; add `--routed` for a routed board (both boards are). Afterwards `git status` shows only what the source
change caused; a rebuild without source changes leaves it clean.

The plan's gates, run on the result (`kicad-cli` = the full path above on Windows):

```
kicad-cli sch erc --severity-error --exit-code-violations hardware/kicad/main/airq-main.kicad_sch
kicad-cli sch export netlist --format kicadsexpr -o build/main.net hardware/kicad/main/airq-main.kicad_sch
uv run --with pyyaml python tools/hw/check_netlist.py build/main.net hardware/interface.yaml
uv run python tools/hw/check_bom.py build/main-bom.csv hardware/bom/parts.csv
kicad-cli pcb drc --severity-error --exit-code-violations --schematic-parity hardware/kicad/main/airq-main.kicad_pcb
uv run python tools/hw/check_board.py hardware/kicad/main/airq-main.kicad_pcb --max-w 60 --max-h 30
uv run --with pytest --with pyyaml pytest tests
```

To look at the result without the GUI: `kicad-cli sch export pdf -o build/main-sch.pdf …kicad_sch` and
`kicad-cli pcb render --rotate "-45,0,30" -o build/main.png …kicad_pcb`.

The sense tongue builds the same way (`build.py tongue --routed`: it is routed) and has its own gates:
it has no MCU, USB or pull-ups, so `check_netlist` runs against its interface subset
`hardware/src/tongue/interface.yaml` (`checks: [connectors]`, a copy of `J_QWIIC_TONGUE` that
`tests/test_interface.py` keeps equal to `hardware/interface.yaml`), and the size limit is 22 × 14 mm:

```
uv run --with pyyaml python tools/hw/check_netlist.py build/tongue.net hardware/src/tongue/interface.yaml
uv run python tools/hw/check_board.py hardware/kicad/tongue/airq-tongue.kicad_pcb --max-w 22 --max-h 14
uv run python tools/hw/check_bom.py build/tongue-bom.csv hardware/bom/parts.csv
```

Tongue layout (`hardware/src/tongue/layout.yaml`; mechanical data for the enclosure in
`hardware/interface.yaml`, `mechanical.tongue`): the long top edge (−Y) is the front edge, behind the
intake lip. The SHT45 sits near it at the left end, the VEML7700 looks out of it at the right end, and the
Qwiic cable leaves the opposite long edge. The SHT45 sits on an island cut free by a 1.0 mm milled
slot on three sides, joined to the board only by a 2.4 mm neck that carries its four 0.2 mm traces. The
board-owned rule area `SHT45_ISOLATION` bans vias and pours over the island, slot and neck; a custom DRC
rule bans other parts' pads there; `tests/hardware/test_tongue.py` checks that every track within 1.5 mm
of the sensor is one of its own. The routing, the B.Cu ground pour (body only) and the rule area were
written into the board file once, like routing done in KiCad, and are kept by every rebuild.

Main board layout (`hardware/src/main/layout.yaml`; mechanical data for the enclosure in
`hardware/interface.yaml`, `mechanical.main`, checked against the board by
`tests/hardware/test_main_board.py`). 60 × 30 mm; the front edge is the bottom edge (+Y), so left and right in
KiCad's top view are left and right for someone in front of the device.

- **Rear edge (y = 0):** the M2 hole H1, the USB-C receptacle (mouth flush with the edge) with its ESD part and
  CC resistors behind it, then the 5 V → 3.3 V buck in a row (U2, C1 straddling VIN and GND, L1, the output
  caps). The ESP32-C6-WROOM-1 sits in the rear-right corner; its 6 mm antenna strip hangs over the rear
  edge, feed point toward the right edge. The rule area `ANTENNA_KEEPOUT` (Espressif's keep-out: ≥ 15 mm
  toward −X, 2 mm toward +X, the strip plus 0.5 mm of board) bans all copper and pours on both layers.
- **Front edge (y = 30):** the four side-emitting LEDs in chain order left to right (D1, D2 = the mini's CO₂
  half; D3, D4 = the PM2.5 half) with the FPC between the halves (an 18 mm gap for the light-guide
  divider), J_LED_EXT and, at the front-right, the side-push button.
- **Left edge:** J_SEN66, J_QWIIC_AUX and, at the front-left corner, J_QWIIC_TONGUE, mouths out of the edge.
- Pressure sensor and LED buffer on the left, away from the module and the buck; the e-ink panel's
  capacitors in a row behind the FPC, its boost circuit (L2, Q1, diodes) between the FPC and the module;
  the unfitted J_AUX_UART pads across the middle-left; H2 at the front-right, next to the button.
- **Copper:** GND pours on both layers over the whole board (except the rule areas), about 85 stitching
  vias. Other rule areas: no top tracks under the module (its signals leave through vias), no top tracks
  or vias under the USB-C shell, no copper in the button's "prohibited area", no tracks or vias round
  the screw heads. A custom rule ties J1's ground pins solidly to the pours.

**How it was routed** (one-off, like routing in KiCad; the items live in the board file): the critical
nets were drawn first (the buck's VIN/GND/SW/BST loop, the FB divider and its sense line, USB D+/D− from
the connector through the ESD part to the module as a pair, module and LED decoupling, the VBUS feed);
Freerouting 2.5.0 then routed every other net except GND from the DSN that `build.py` writes
(`tools/hw/kicad_dsn.py BOARD OUT.dsn`; GND moved to a net class Freerouting was told to ignore, power nets
at 0.3 mm, a 0.35 mm keep-out band inside the outline); the session was imported with
`tools/hw/kicad_dsn.py --import-ses BOARD IN.ses`, one-sided vias it left were removed, and the pours and
stitching vias were added. To change the routing: edit it in KiCad (then rebuild and commit), or start
again from an unrouted board the same way.

### How the pipeline works

1. `design.py` reads `src/<board>/` and checks its structure.
2. The project libraries are copied into `build/kicad-lib/` in the current KiCad format (`kicad-cli sym/fp
   upgrade`); `airq` is kept in easyeda2kicad's older format in the repository.
3. `gen_sch.py` writes the root sheet (one sheet symbol per source sheet) and the sheets; `gen_project.py`
   writes the library tables, `.kicad_pro` and `.kicad_dru` (these are written by the generator, not
   re-saved by KiCad). KiCad re-saves each sheet.
4. kicad-cli exports the netlist.
5. `gen_pcb.py` builds the board **from that netlist**, like KiCad's "Update PCB from Schematic": every pad
   net, value, field and schematic link (`path`) is what KiCad derives from the schematic, so DRC's
   schematic-parity check holds. Footprints come fresh from the libraries. KiCad re-saves the board.
6. ERC; DRC with parity after refilling every zone (`--refill-zones --save-board`: the board is saved with
   the new fills, so its pours always match its footprints); BOM, CPL and DSN (`kicad_dsn.py`, the only
   code that needs `pcbnew`).

The output is deterministic: every UUID is a uuid5 of a stable name (project, reference, pin), and KiCad's
zone fill is repeatable, so a rebuild without source changes leaves the committed files byte-identical,
routed or not.

### Regeneration contract

| File | Written by | Owned by the generator (rebuilt from the source) | Kept on rebuild |
|---|---|---|---|
| `*.kicad_sch` | generator, then saved by KiCad | everything | nothing: edits made in KiCad are lost |
| `sym-lib-table`, `fp-lib-table`, `*.kicad_dru` | generator | everything | nothing |
| `*.kicad_pro` | generator (JSON, sorted keys, 2-space indent) | `board.design_settings.rules` and `.rule_severities`, `erc.rule_severities`, `net_settings.classes` and `.netclass_patterns`: replaced whole, so a rule or severity removed from the source is removed here and KiCad's default applies | every other setting (track/via presets, plot settings, ...) |
| `*.kicad_pcb` | generator, then saved by KiCad (upgrade, then DRC with zone refill) | footprints (re-made from the library, placed from `layout.yaml`), the Edge.Cuts outline and cutouts of `layout.yaml`, title block, page setup | tracks, arcs, vias, zones (pours, keep-outs) with fresh fills, other drawings and text, Edge.Cuts items drawn in KiCad |

- **Routed boards.** The committed boards hold their routing. A rebuild keeps it, so the
  committed board stays what a rebuild produces. A schematic change that moves a net leaves its old tracks
  in place, and DRC reports them.
- **Placement** lives in `layout.yaml`. A part moved by hand in KiCad must be copied back there, or the
  next rebuild moves it back. A part without a placement entry keeps its board position, or is parked
  to the right of the outline, packed in rows by its courtyard and pads so parked parts never overlap;
  the build lists it.
- **Board edges.** The outer outline (a rectangle, or a polygon for notched corners) and internal cutouts
  (milled slots) belong in `layout.yaml`. The generator recognises its own Edge.Cuts items by their UUIDs; any
  other Edge.Cuts item (drawn in KiCad) is never deleted: the build keeps it and lists it, so it can be moved
  into `layout.yaml`. If the generated outline on the board differs from `layout.yaml` (expected right after
  editing `layout.yaml`; otherwise it was edited in KiCad), the build replaces it and says so.
- **KiCad GUI saves.** A save in KiCad can rewrite any of these files; it rewrites `.kicad_pro` with its full
  settings set in its own JSON layout. Rebuild once afterwards (the table says what the rebuild resets and
  what it keeps) and commit the result; the guard test below fails until then.
- **Commit** the regenerated `hardware/kicad/<board>/` files with the source change.
  `tests/hardware/test_kicad_pipeline.py` copies the committed project into a scratch folder, rebuilds it,
  and fails if any file changes or if the committed set differs from the files the build writes.

### Design source format

`src/<board>/project.yaml`: `project` (KiCad project name), `title`, `company`, `rev`, `output` (the KiCad
folder), `sheets` (page order; each is `<name>.yaml`), `power_symbols` (net → power symbol, e.g.
`GND: power:GND`), `libraries` (project symbol/footprint libraries), `erc_severities` (overrides) and
`interface` (path of the interface contract, `../../interface.yaml`; see "Pins from interface.yaml" below).

`src/<board>/<sheet>.yaml`: `title`, `paper` (A4, A3), `notes` (`{text, at, size}` page text) and `parts`.
Each part, keyed by its reference:

| Key | Meaning |
|---|---|
| `symbol` | `library:name` (`airq:…`, or a KiCad stock library such as `Device:R`) |
| `at` | `[x, y]` of the symbol anchor on the page in mm, Y down; pins must land on the 1.27 mm grid |
| `rot`, `mirror` | 0/90/180/270 counter-clockwise; `x` (top↔bottom) or `y` (left↔right) |
| `stub` | optional wire length (mm) between each pin and its label, for symbols with short pins; or a mapping `{pin number or name: length}` for some pins only (e.g. `{DOUT: 7.62}`, a label clear of a crowded neighbour) |
| `fields_at` | optional page offsets (mm, from `at`, Y down) of field texts, e.g. `{Reference: [0, -12.7], Role: [0, 15.24]}`; placed fields read horizontally |
| `value`, `footprint`, `lcsc` | override the symbol's Value / Footprint / LCSC fields |
| `fields` | extra fields, e.g. `{Role: J_SEN66}` (interface.yaml keys). `Role` is shown on the sheet (under the value, or at `fields_at.Role`), so two parts of one kind (J_QWIIC_TONGUE, J_QWIIC_AUX) can be told apart; other extra fields are hidden |
| `dnp` | `true` or `false`; `true` for parts not fitted (left out of the JLC BOM and CPL) |
| `pins` | pin → net name for **every** pin; `NC` for unused pins (no-connect flag). A key is a pin number, or a pin name, which covers every pin with that name (`GND: GND` for all of a module's ground pins). A list is allowed when pins are numbered 1..n. Each pin gets its net once |

**Pins from interface.yaml.** When `project.yaml` names `interface`, a part with a `Role` field takes nets
from it and the sheet must not repeat them: `Role: MCU` wires each `signals` entry (`I2C_SDA: GPIO6`) to the
part's pin named `IO6`/`GPIO6`, and a `Role` that is a `connectors` key wires pins 1..n of that part in the
listed order. So connector pinouts and the GPIO map are written once, in `hardware/interface.yaml`, and
`check_netlist` checks the result against the same file. The sheet still lists the part's other pins
(supply, mounting tabs). A `Role` that is neither `MCU` nor a `connectors` key is an error.

**Stacked pins** (pins of one part on the same point, as KiCad draws a module's ground pins, hidden behind
one visible pin) must share a net; they get one marker.

Drawing style: no wires between parts. Each pin ends in its net's marker, pointing away from the symbol: a
power symbol for `power_symbols` nets, a global label for a net used on more than one sheet, a local label
otherwise, or a no-connect flag. **A net name is one net across the whole board** (prefix block-local nets,
e.g. `BUCK_SW`, so two sheets never share a name by accident). ERC power flags are ordinary parts:
`"#FLG01": {symbol: power:PWR_FLAG, at: …, pins: [+5V]}`.

`src/<board>/layout.yaml`: `board` (`width` and `height` for a rectangle, or `outline`: a list of `[x, y]`
points for any other shape such as notched corners; `cutouts`: a list of such polygons for internal slots;
`origin` = page position of the coordinate origin; `thickness`), `rules` (KiCad board constraints, mm), `netclasses` (`Default` plus named classes with `nets`
patterns), `drc_severities`, `custom_rules` (KiCad custom DRC rules, written to `<project>.kicad_dru`) and
`placement` (`REF: [x, y, rotation]`, mm from the board's top-left corner, Y down; KiCad's grid origin is set
there; or `REF: {at: [x, y, rotation], ref: ...}` to place the part's reference text: `ref: [dx, dy]` or
`[dx, dy, angle]` puts its centre dx, dy mm from the part's origin in board axes, upright (or at `angle`),
and `ref: hide` hides it). Every key is checked: unknown keys, rule or net-class names, non-numbers, and a
placement for a part that is not in the sheets are errors. The JLC CPL is measured from the bottom-left corner of the outline's bounding box (KiCad's
drill/place origin), Y up.

### What the generator adds to every project

- The library tables list the `airq` library and each KiCad stock library the design uses (with
  `${KICAD10_SYMBOL_DIR}` / `${KICAD10_FOOTPRINT_DIR}` paths), so the project resolves even without KiCad's
  global library tables. This machine has none, and kicad-cli then reports "does not include the symbol
  library 'Device'". A stock entry has the same name and path as KiCad's default global entry.
- ERC/DRC severities raised to **error**: DRC schematic parity (`missing_footprint`, `extra_footprint`,
  `duplicate_footprints`, `footprint_symbol_mismatch`, `net_conflict`), `lib_footprint_mismatch` and ERC
  `lib_symbol_mismatch`. KiCad has them as warnings, so `--severity-error` would otherwise pass a board that
  no longer matches its schematic or its library.

### Limits (for later tasks)

- Symbols: single unit, no derived (`extends`) symbols; stacked pins only with one net. Footprints: on F.Cu,
  and no zones or groups inside a footprint (KiCad's stock `RF_Module:ESP32-C6-MINI-1` has a keep-out zone:
  support it if ruling R22 reverts). A footprint that does not exist is reported with the part, before the
  schematic is written.
- Footprint edits made in KiCad (moved silkscreen text) are not kept; the footprint is re-made from the library.
  Place reference text from `layout.yaml` (`ref:`) instead; footprint silkscreen that lands on a board edge
  is fixed in the library (the main board's edge parts, library README fix 21).
- Edge.Cuts shapes from `layout.yaml` are straight-sided polygons (no arcs): a milled slot gets the router
  bit's radius at its ends anyway.
- Schematic readability is checked by eye: export the PDF after changing positions.
