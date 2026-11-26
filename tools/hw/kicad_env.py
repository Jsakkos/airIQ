"""Find the KiCad 10 tools and stock libraries, and run kicad-cli (stdlib only).

Lookup order for `kicad-cli`: the KICAD_CLI environment variable, then PATH, then the default
install folders (Windows per-user and per-machine, macOS, Linux). KiCad's bundled Python (which
has the `pcbnew` module) is KICAD_PYTHON, else the interpreter next to kicad-cli on Windows/macOS,
else `python3` (Linux packages install `pcbnew` into the system Python). The stock symbol and
footprint folders honour KiCad's own KICAD10_SYMBOL_DIR / KICAD10_FOOTPRINT_DIR variables.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# The KiCad release the committed KiCad and fab files were written with. kicad-cli re-saves the
# schematics and boards and writes its version into the Gerber and drill headers, so a rebuild is
# byte-identical to the committed files on this release only: after a KiCad update, rebuild both
# boards, check them, commit the result and change this line (hardware/README.md, "Regeneration
# contract"). The stale-output guard test skips on any other version.
PINNED_VERSION = "10.0.8"

_CANDIDATES = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/KiCad/10.0/bin/kicad-cli.exe",
    Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "KiCad/10.0/bin/kicad-cli.exe",
    Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"),
    Path("/usr/bin/kicad-cli"),
    Path("/usr/local/bin/kicad-cli"),
]


class KicadNotFound(RuntimeError):
    pass


def kicad_cli() -> Path:
    env = os.environ.get("KICAD_CLI")
    if env:
        return Path(env)
    found = shutil.which("kicad-cli")
    if found:
        return Path(found)
    for c in _CANDIDATES:
        if c.is_file():
            return c
    raise KicadNotFound("kicad-cli not found: install KiCad 10 or set KICAD_CLI to its full path")


def kicad_python() -> Path:
    env = os.environ.get("KICAD_PYTHON")
    if env:
        return Path(env)
    cli = kicad_cli()
    for name in ("python.exe", "python3"):
        if (cli.parent / name).is_file():
            return cli.parent / name
    mac = cli.parents[1] / "Frameworks/Python.framework/Versions/Current/bin/python3"
    if mac.is_file():
        return mac
    return Path(shutil.which("python3") or sys.executable)


def _share_dir() -> Path:
    cli = kicad_cli().resolve()
    for share in (cli.parents[1] / "share/kicad", cli.parents[1] / "SharedSupport",
                  Path("/usr/share/kicad")):
        if share.is_dir():
            return share
    raise KicadNotFound(f"no KiCad share folder next to {cli}")


def stock_symbol_dir() -> Path:
    env = os.environ.get("KICAD10_SYMBOL_DIR")
    return Path(env) if env else _share_dir() / "symbols"


def stock_footprint_dir() -> Path:
    env = os.environ.get("KICAD10_FOOTPRINT_DIR")
    return Path(env) if env else _share_dir() / "footprints"


def kicad_version() -> str:
    """The installed kicad-cli's version, e.g. '10.0.8' (`kicad-cli version`)."""
    return run_cli("version").stdout.strip()


def run_cli(*args: str | Path, check: bool = True) -> subprocess.CompletedProcess:
    """Run kicad-cli with `args`; raise with its output when it fails and `check` is set."""
    proc = subprocess.run([str(kicad_cli()), *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        raise RuntimeError(f"kicad-cli {' '.join(map(str, args))} failed ({proc.returncode}):\n"
                           f"{proc.stdout}{proc.stderr}")
    return proc
