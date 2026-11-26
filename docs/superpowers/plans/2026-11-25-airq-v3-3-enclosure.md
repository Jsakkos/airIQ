# airQ v3 Plan 3: Enclosures implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Printable, measurement-correct "Paper" enclosures for both models, built as parametric SolidCraft designs and exported as STEP and 3MF:
- **airQ:** 95 × 55 × 48 mm wedge
- **airQ mini:** about 66 × 50 × 42 mm

Both come with light guides, gaskets and test coupons.

**Architecture:**
- Each model is one SolidCraft design whose sizes are named parameters: shared names, different values.
- Reference parts are inserted as components so every check runs against real geometry:
  - the PCB STEP files (Plan 2)
  - a dimensioned SEN66 model
  - the e-ink panel
  - the SFA40 breakout
- The checks are SolidCraft queries (`measure`, `body_topology`, `check_parameters`, interference/clearance), recorded in a table in `enclosure/README.md`. Physical fit is confirmed by the owner printing coupons first.

**Tech stack:**
- SolidCraft ≥ 0.48, driven through its MCP tools. Before modelling, load its skill reference: `skill_reference {"skill":"solidcraft-modeling"}`.
- Bambu Studio for slicing. Printing is done by the owner.

**Spec:** `docs/superpowers/specs/2026-11-25-airq-v3-design.md` (§5, §6.5, §6.6, §6.9). The mockups `.superpowers/brainstorm/3444-1795627844/content/shape-variants.html` (card 0, Paper) and `screenless.html` (split light) set the look.

**Prerequisites:**
- Plan 2 Task 7 provides `hardware/step/*.step` and `interface.yaml` `mechanical.*`.
- Tasks 1–2 can start earlier, using placeholder boards sized to the Plan 2 limits (60 × 30 mm and 22 × 14 mm).

## Global constraints

- **Look ("Paper"):**
  - matte warm-white body, crisp edges (chamfers, not big fillets)
  - one orange accent dot that is also the button
  - slot vents along the lower front lip
  - no visible fasteners on the front or sides
- **airQ:** outer envelope 95 × 55 × 48 mm (±1 mm). Front face tilted 30° back from vertical. 2.9″ screen window, a 30 mm LED line under the screen, and the orange dot at top-right.
- **airQ mini:** outer envelope ≤ 66 × 50 × 42 mm. Front face tilted 24° back. A split light band, two halves of about 21 mm with a gap of at least 4 mm, with **"CO₂"** and **"PM2.5"** debossed 0.4 mm deep under the left and right halves respectively. Orange dot at top-right, and a light-sensor window.
- **Air and heat:**
  - The sensor zone is low and the electronics zone high, with an internal wall between them.
  - The SEN66 lies flat, with its ports never facing up or down.
  - Each SEN66 port is sealed to its own grille with a TPU gasket, and the ports are sealed from each other and from the case interior.
  - The intake grille sits in the lower front lip. The SEN66 outlet grille is at the lower rear behind a baffle. The electronics exhaust is at the upper rear.
  - The tongue board sits in the intake air, at least 20 mm from the ESP32 module and the buck converter.
  - **No opening's lower edge is less than 10 mm above the shell's bottom plane**, without counting the feet.
  - Each grille's open area is at least 2× the area of the port it serves.
  - The SEN66 sits on 1 mm foam and isn't wrapped.
- **Formaldehyde (airQ only):** a sealed pocket for the SFA40 breakout in the sensor zone, with its own grille to room air.
- **Printing:**
  - Walls at least 1.6 mm (default 1.8 mm). Floor 2.0 mm.
  - Grille slots 1.2 mm wide, or 45° louvres.
  - Heat-set inserts (M2) are entered from underneath, with felt feet covering the screws.
  - The shell prints face down on textured PEI.
- **Clearance parameters:** `clr_align` (0.15 mm), `clr_remove` (0.20 mm) and `clr_snap` (0.25 mm). The coupon results (Task 2) override these defaults.
- **Materials:** ASA if the printer is enclosed, PETG otherwise. Light guides in clear or natural PETG. Gaskets in TPU 95A.

## Review focus

1. **The owner's printer prints tighter or looser than nominal:** every fit is a clearance parameter, and coupons are printed first. `check_parameters` proves the models rebuild across the range. Tested in Tasks 2–4.
2. **SEN66 exhaust or warm case air reaching its own intake:** the gasket faces touch the module, and the intake and outlet grilles are on different faces at least 20 mm apart. Tested in Tasks 3–4.
3. **LED light reaching the light-sensor window (auto-dim feedback), or bleeding between the mini's two halves:** an opaque wall at least 1.2 mm thick separates each light guide from the window, and the two halves from each other. Tested in Tasks 3–4.
4. **A unit used without its felt feet, on a desk that gives off VOCs:** grilles stay at least 10 mm above the shell's bottom plane even with the feet removed. Tested in Tasks 3–4.
5. **Pushing the USB-C cable in flexing the board or the shell:** a support boss sits within 8 mm of the USB-C connector, and the opening is chamfered 0.5 mm. Tested in Tasks 3–4.

---

### Task 1: Reference parts

**Files:**
- Create in `enclosure/reference/`:
  - `sen66.sc`: a box 55.2 × 25.6 × 21.3 mm with the inlet and outlet port faces modelled from the SEN6x datasheet's mechanical drawing, named bodies `sen66_body`, `sen66_inlet`, `sen66_outlet`
  - `epd-2.9.sc`: panel 79.0 × 36.7 × 1.0 mm, active area 66.9 × 29.1 mm placed per the GDEY029T94 drawing, plus the FPC tail
  - `sfa40-breakout.sc`: the SparkFun SFA40 board dimensions and the sensor opening position, from its product drawing
- Use `hardware/step/airq-main.step` and `airq-tongue.step` as they are. Until those exist, use placeholder boxes sized to `mechanical.*`, or to 60 × 30 × 1.6 mm and 22 × 14 × 1.6 mm.

**Interfaces:**
- Produces: component names `ref_sen66`, `ref_epd`, `ref_sfa40`, `ref_main`, `ref_tongue`. Tasks 3–4 insert these.

- [ ] **Step 1: Model the three reference parts.** Every size is a named parameter.
- [ ] **Step 2: Verify:** `measure {}` on each design. Expected: each bounding box matches its datasheet within ±0.1 mm.
- [ ] **Step 3: Commit** with the message `feat(enclosure): reference parts`.

### Task 2: Test coupons (the owner prints these early)

**Files:**
- Create: `enclosure/coupons.sc` and `enclosure/export/coupons.3mf`

**What the coupons contain:**
- **Clearance coupon:** pegs and holes at 0.10, 0.15, 0.20, 0.25 and 0.30 mm.
- **Grille coupon:** 1.0, 1.2 and 1.5 mm slots and 45° louvres, printed face down.
- **Insert boss:** an M2 heat-set insert boss.
- **Button flexure:** a flexure with its tactile-switch standoff.
- **Light-guide coupon:** a 3 × 2 mm clear bar with an LED pocket, and an opaque 1.2 mm divider test.

- [ ] **Step 1: Model the coupons and export the 3MF.** Verify by reopening it with `open`: the expected part count imports.
- [ ] **Step 2: Owner prints** on the target printer and material, then reports which clearance fits, whether the slots print cleanly, whether the flexure clicks, and whether light leaks past the divider.
- [ ] **Step 3: Record the results** in `enclosure/README.md` under "Coupon results", and set the default values of `clr_*`, `slot_w` and `flex_*`.
- [ ] **Step 4: Commit** with the message `feat(enclosure): print-test coupons and results`.

### Task 3: airQ enclosure

**Files:**
- Create: `enclosure/airq.sc`

**Parts (named bodies):**
- `shell`
- `base_plate`
- `zone_wall`
- `sen66_cradle`
- `gasket_in` and `gasket_out` (TPU)
- `baffle`
- `hcho_pocket`
- `tongue_mount`
- `light_guide`
- `button_flexure`
- `orange_dot` (a separate insert, or an AMS colour region)

**Interfaces:**
- Consumes: Task 1 references, the Task 2 clearance defaults, and `interface.yaml` `mechanical.*` for hole positions and the connector edges.
- Produces: the parameter names `W`, `D`, `H`, `tilt_deg`, `wall`, `floor`, `grille_min_z`, `slot_w`, `clr_align`, `clr_remove`, `clr_snap`. Task 4 reuses them.

- [ ] **Step 1: Build the shell envelope** with W=95, D=55, H=48 and `tilt_deg`=30. Shell it to `wall`. Add the base plate with insert bosses at the board's mounting holes.
- [ ] **Step 2: Add the internals:**
  - the zone wall
  - the SEN66 cradle, with gasket seats and the baffle
  - the tongue mount behind the intake lip
  - the HCHO pocket with its own grille
  - main-board standoffs, with a support boss within 8 mm of USB-C
- [ ] **Step 3: Add the face features:**
  - the screen window over the e-ink active area, plus the panel pocket
  - a 30 mm LED slot under the screen, and the light guide
  - the orange dot and flexure, aligned to the button
  - the light-sensor window over the tongue's VEML7700, with an opaque wall at least 1.2 mm between it and the light guide
  - the intake slots, rear grilles and USB-C opening (0.5 mm chamfer)
- [ ] **Step 4: Verify, recording each value in the README check table:**
  - `measure {}` gives a bounding box of 95 × 55 × 48 mm ±1.
  - The interference check between every enclosure body and every `ref_*` component reports **0 interferences**.
  - With `body_topology` / `measure`, the lowest grille edge sits **≥ 10 mm** above the bottom plane, and each grille's open area is ≥ 2× its port area.
  - The intake and outlet grilles are ≥ 20 mm apart.
  - The tongue is ≥ 20 mm from the ESP32 and the buck converter.
  - `check_parameters {"set":{"wall":1.6}}` and `{"wall":2.4}`, and `clr_*` ±0.1, all rebuild with no errors.
- [ ] **Step 5: Commit** with the message `feat(enclosure): airQ parametric enclosure`.

### Task 4: airQ mini enclosure

**Files:**
- Create: `enclosure/airq-mini.sc`

**Parts:** the same as Task 3, minus `hcho_pocket` and the screen, plus `light_guide_co2`, `light_guide_pm` and `label_debossing`.

**Interfaces:**
- Consumes: the Task 3 parameter names, which this task reuses with the mini's values.

- [ ] **Step 1: Build the envelope** at ≤ 66 × 50 × 42 mm with `tilt_deg`=24. Main board above the SEN66, with the zone wall between them. Tongue mount behind the intake lip.
- [ ] **Step 2: Build the split light band:**
  - two light guides of about 21 mm each, separated by an opaque wall of at least 1.2 mm, with a visible gap of at least 4 mm
  - "CO₂" debossed 0.4 mm under the left half, "PM2.5" under the right
  - the light-sensor window, separated from both guides by opaque walls
- [ ] **Step 3: Verify:** the same checks as Task 3 Step 4 with the mini's envelope, plus a check that **no straight path of air or light** connects the two guides.
- [ ] **Step 4: Commit** with the message `feat(enclosure): airQ mini parametric enclosure`.

### Task 5: Exports and print/assembly guide

**Files:**
- Create in `enclosure/export/`: `airq-*.step`, `airq-*.3mf`, `airq-mini-*.step`, `airq-mini-*.3mf` (one file per printed part)
- Modify: `enclosure/README.md`, adding:
  - per part: orientation, material and supports
  - assembly order: inserts → base → SEN66 with gaskets → tongue → main board → cables → light guides → shell → feet
  - airing new prints for several days before trusting VOC readings
  - the check table filled in from Tasks 3–4

- [ ] **Step 1: Export every part** with `export` (STEP and 3MF). Verify by reopening each 3MF with `open`: one body per file, and the bounding boxes match the design.
- [ ] **Step 2: Owner test-prints** one airQ and one mini, assembles them with the prototype boards, and reports any fit issues. Fix them by changing parameters only, then re-export.
- [ ] **Step 3: Commit** with the message `feat(enclosure): exports and print/assembly guide`.
