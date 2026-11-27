"""Build the enclosure designs: generator -> command script -> `solidcraft-cli run` -> .sc file.

Each design in DESIGNS is a generator module with `DESIGN` (the design's name, which
`component.insert_design` gives the component), `OUTPUT` (its .sc file, relative to enclosure/)
and `build() -> sclib.Script`. A design that is printed also has `EXPORTS`: a list of files
(.3mf, .step, .stl, ... relative to enclosure/) written beside the design on every build.

`build(name)` writes the script to enclosure/.build/<name>.json (gitignored), runs it, saves the
design without SolidCraft's model cache (the cache records timings, so saves would differ every
run) to enclosure/.build/<OUTPUT>, checks every sketch solved at dof 0, and copies the file to
enclosure/<OUTPUT> when it is at most COMMIT_LIMIT bytes and its contents changed. A design
larger than that stays in enclosure/.build/ (ruling R8: keep committed designs light).

Exports: `solidcraft-cli run --out` writes each of the design's EXPORTS into enclosure/.build/
first (meshes at EXPORT_QUALITY), a 3MF is reopened to check it holds one part per body of the
design, and each file is copied to enclosure/ when its bytes changed. Task 5 reuses this for every
printed part: list its files in EXPORTS.

A design with `PRINT_PARTS` ({body: {turns: [(axis, degrees)...], ref?: body}}) exports one file pair
per part instead (`print_exports`): after the design is saved, each part is turned into its print
orientation, set on the bed (z = 0), and written alone. The saved design is not touched.
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

from sclib import ENCLOSURE

BUILD_DIR = ENCLOSURE / ".build"
COMMIT_LIMIT = 5 * 1024 * 1024          # R8: 5 MB
EXPORT_QUALITY = "standard"                 # mesh chord 2e-4 of a body's size (3MF, STL): 0.013 mm on a 66 mm plate
DEFAULT_CLI = Path(r"C:\Program Files\SolidCraft\solidcraft-cli.exe")

# design key -> generator module (enclosure/src/<module>.py)
DESIGNS = {
    "sen66": "ref_sen66",
    "epd-2.9": "ref_epd",
    "sfa40-breakout": "ref_sfa40",
    "fpc-adapter": "ref_fpc_adapter",
    "airq-main": "ref_pcb_main",
    "airq-tongue": "ref_pcb_tongue",
    "coupons": "coupons",
    "airq": "airq",
    "airq-mini": "airq_mini",
}


def module(name: str):
    return importlib.import_module(DESIGNS[name])


def cli_path() -> str | None:
    """solidcraft-cli: $SOLIDCRAFT_CLI, else on PATH, else the Windows install path."""
    env = os.environ.get("SOLIDCRAFT_CLI")
    if env:
        return env if Path(env).exists() else None
    found = shutil.which("solidcraft-cli")
    if found:
        return found
    return str(DEFAULT_CLI) if DEFAULT_CLI.exists() else None


def script_for(name: str, save_to: Path) -> dict:
    """The generator's commands plus the save and a closing measurement."""
    script = module(name).build().to_dict()
    script["commands"] += [
        {"command": "file.save", "params": {"path": str(save_to), "cache": False}},
        {"command": "inspect.measure", "params": {"summary": True}},
    ]
    return script


def run_script(script_path: Path, cli: str, json_out: Path, extra: list[str] = ()) -> list:
    """Run a command script; return the per-step results or raise with the failing step."""
    json_out.unlink(missing_ok=True)        # never read an earlier run's results
    proc = subprocess.run([cli, "run", str(script_path), "--results", "--quiet",
                           "--json-out", str(json_out), *extra],
                          capture_output=True, text=True)
    result = json.loads(json_out.read_text(encoding="utf-8")) if json_out.exists() else None
    if proc.returncode != 0 or not isinstance(result, list):
        detail = result.get("error") if isinstance(result, dict) else None
        raise RuntimeError(f"solidcraft-cli run {script_path.name} failed: "
                           f"{detail or proc.stderr.strip() or proc.stdout.strip()}")
    return result


def check_results(name: str, commands: list[dict], results: list) -> list[str]:
    """Fail on a sketch above dof 0; return the feature warnings."""
    warnings = []
    for step, res in zip(commands, results):
        if not isinstance(res, dict):
            continue
        if step["command"] == "sketch.solve" and (res.get("dof") != 0 or res.get("status") != "solved"):
            raise RuntimeError(f"{name}: a sketch did not solve at dof 0: {res}")
        if res.get("warning"):
            warnings.append(f"{res.get('name')}: {res['warning']}")
    return warnings


def union(boxes) -> dict:
    """The bounding box of several {min, max} boxes."""
    boxes = list(boxes)
    return {"min": [min(b["min"][i] for b in boxes) for i in range(3)],
            "max": [max(b["max"][i] for b in boxes) for i in range(3)]}


def entry(z: zipfile.ZipFile, name: str) -> bytes:
    """A container file's contents, with what SolidCraft makes up afresh on every build left
    out: configuration rows get random identities (`configs.row_identities`)."""
    data = z.read(name)
    if name != "document.json":
        return data
    doc = json.loads(data)
    doc.get("configs", {}).pop("row_identities", None)
    return json.dumps(doc, sort_keys=True).encode()


def same_contents(a: Path, b: Path) -> bool:
    """Two .sc containers hold the same design (the zip bytes may differ)."""
    if not (a.exists() and b.exists()):
        return False
    if a.read_bytes() == b.read_bytes():
        return True
    with zipfile.ZipFile(a) as za, zipfile.ZipFile(b) as zb:
        names = sorted(za.namelist())
        return names == sorted(zb.namelist()) and all(entry(za, n) == entry(zb, n) for n in names)


def exports_of(name: str) -> list[str]:
    """The files a design exports (paths relative to enclosure/), none for a reference part."""
    return list(getattr(module(name), "EXPORTS", []))


def eval_bodies(path: Path, cli: str, json_out: Path) -> dict:
    """Reopen a file (.3mf, .step, .sc) and return {body name: bounding box} of what imports."""
    json_out.unlink(missing_ok=True)
    proc = subprocess.run([cli, "eval", str(path), "--quiet", "--json-out", str(json_out)],
                          capture_output=True, text=True)
    if proc.returncode != 0 or not json_out.exists():
        raise RuntimeError(f"solidcraft-cli eval {path.name} failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return {b["name"]: b["bbox"] for b in json.loads(json_out.read_text(encoding="utf-8"))["bodies"]}


def part_of(mod, path) -> str:
    """The printed body a PRINT_PARTS export file holds: its name without the module's FILE_PREFIX
    (default `<DESIGN>-`, so `airq-shell` is `shell` and the mini's `airq-mini-shell` is `shell`)."""
    prefix = getattr(mod, "FILE_PREFIX", f"{mod.DESIGN}-")
    return Path(path).stem.removeprefix(prefix)


def print_turns(mod) -> list[dict]:
    """The solid.move steps that put every printed part in its print orientation."""
    steps = []
    for part, spec in mod.PRINT_PARTS.items():
        for axis, deg in spec["turns"]:
            steps.append({"command": "solid.move", "params": {
                "bodies": [part], "origin": [0, 0, 0],
                "axis": [1.0 if axis == "x" else 0.0, 1.0 if axis == "y" else 0.0, 1.0 if axis == "z" else 0.0],
                "angle": f"{deg} deg", "name": f"print_turn_{part}_{axis}{deg}"}})
    return steps


def print_boxes(name: str, design: Path, cli: str, json_out: Path) -> dict:
    """{part: {min, max, volume}} with every printed part turned into its print orientation,
    before the move onto the bed."""
    mod = module(name)
    script = BUILD_DIR / f"{name}.print_turns.json"
    script.write_text(json.dumps({"commands": print_turns(mod)}), encoding="utf-8")
    json_out.unlink(missing_ok=True)
    proc = subprocess.run([cli, "eval", str(script), "--in", str(design), "--quiet", "--json-out", str(json_out)],
                          capture_output=True, text=True)
    if proc.returncode != 0 or not json_out.exists():
        raise RuntimeError(f"print orientation of {name} failed: {proc.stderr.strip() or proc.stdout.strip()}")
    bodies = {b["name"]: b for b in json.loads(json_out.read_text(encoding="utf-8"))["bodies"]}
    return {part: {**bodies[part]["bbox"], "volume": bodies[part]["volume_mm3"]} for part in mod.PRINT_PARTS}


def print_exports(name: str, design: Path, cli: str) -> dict:
    """Write each printed part of a design with PRINT_PARTS, turned into its print orientation and
    set on the bed, to enclosure/.build/export/airq-<part>.{3mf,step}. Returns {part: expected box
    {min, max} on the bed} (what the file must reopen as)."""
    mod = module(name)
    boxes = print_boxes(name, design, cli, BUILD_DIR / f"{name}.print_boxes.json")
    commands = print_turns(mod)
    expected = {}
    for part, spec in mod.PRINT_PARTS.items():
        lift = -boxes[spec.get("ref", part)]["min"][2]
        b = boxes[part]
        expected[part] = {"min": [b["min"][0], b["min"][1], b["min"][2] + lift],
                          "max": [b["max"][0], b["max"][1], b["max"][2] + lift], "volume": b["volume"]}
        commands.append({"command": "solid.move", "params": {"bodies": [part], "translate": [0, 0, f"{lift:.9f}"],
                                                             "name": f"print_bed_{part}"}})
    for rel in mod.EXPORTS:
        part = part_of(mod, rel)
        target = (BUILD_DIR / rel).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.unlink(missing_ok=True)
        params = {"bodies": [part], "path": str(target)}
        if target.suffix == ".3mf":
            params["quality"] = EXPORT_QUALITY
        commands.append({"command": "file.export", "params": params})
    script = BUILD_DIR / f"{name}.print_exports.json"
    script.write_text(json.dumps({"commands": commands}, indent=1), encoding="utf-8")
    run_script(script, cli, BUILD_DIR / f"{name}.print_exports.results.json", ["--in", str(design)])
    return expected


def build(name: str, cli: str | None = None, commit: bool = True) -> dict:
    """Build one design. Returns {design, file, bytes, committed, bodies, warnings, exports}, where
    exports is [{file, bytes, committed, parts}] (parts: bodies a 3MF reopens as, else None)."""
    cli = cli or cli_path()
    if not cli:
        raise RuntimeError("solidcraft-cli not found (set SOLIDCRAFT_CLI)")
    mod = module(name)
    if hasattr(mod, "prepare"):
        mod.prepare()                       # inputs the script reads (staged STEP files)
    built = BUILD_DIR / mod.OUTPUT
    built.parent.mkdir(parents=True, exist_ok=True)
    if built.exists():
        built.unlink()
    script = script_for(name, built.resolve())
    script_path = BUILD_DIR / f"{name}.json"
    script_path.write_text(json.dumps(script, indent=1), encoding="utf-8")
    exports = [(BUILD_DIR / rel, ENCLOSURE / rel) for rel in exports_of(name)]
    per_part = hasattr(mod, "PRINT_PARTS")
    extra = []
    for built_export, _ in ([] if per_part else exports):
        built_export.parent.mkdir(parents=True, exist_ok=True)
        built_export.unlink(missing_ok=True)
        extra += ["--out", str(built_export.resolve())]
    if exports and not per_part:
        extra += ["--quality", EXPORT_QUALITY]
    results = run_script(script_path, cli, BUILD_DIR / f"{name}.results.json", extra)
    warnings = check_results(name, script["commands"], results)
    measure = results[-1]
    bodies = {b["name"]: b["bbox"] for b in measure["bodies"]}
    size = built.stat().st_size
    target = ENCLOSURE / mod.OUTPUT
    committed = commit and size <= COMMIT_LIMIT
    if committed and not same_contents(built, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(built, target)
    expected = print_exports(name, built, cli) if per_part else None
    done = []
    for built_export, target_export in exports:
        parts = None
        if built_export.suffix == ".3mf":
            parts = eval_bodies(built_export, cli, BUILD_DIR / f"{name}.{built_export.stem}.parts.json")
            if len(parts) != (1 if per_part else len(bodies)):
                raise RuntimeError(f"{name}: {built_export.name} reopens with {len(parts)} parts, "
                                   f"the design has {len(bodies)} bodies")
        keep = commit and built_export.stat().st_size <= COMMIT_LIMIT
        if keep and not (target_export.exists() and target_export.read_bytes() == built_export.read_bytes()):
            target_export.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(built_export, target_export)
        done.append({"file": target_export if keep else built_export, "bytes": built_export.stat().st_size,
                     "committed": keep, "parts": parts,
                     "expected": expected[part_of(mod, built_export)] if per_part else None})
    return {"design": mod.DESIGN, "file": target if committed else built, "bytes": size,
            "committed": committed, "bodies": bodies, "warnings": warnings, "exports": done}
