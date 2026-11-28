"""Check a KiCad netlist against hardware/interface.yaml.

Input is the netlist from `kicad-cli sch export netlist --format kicadsexpr`.
Usage (PyYAML is the only non-stdlib dependency, used to read the interface file):

    uv run --with pyyaml python tools/hw/check_netlist.py NETLIST INTERFACE

Prints one error per line and exits 1 when there are any. Errors about parts or nets that are
absent from the netlist start with the word "missing", so callers can tell an unfinished
schematic from a real violation.

Rule groups (select a subset with a top-level `checks:` list in the interface file;
absent means all):
    signals      1. every `signals` entry: the MCU pin IO<n> sits on the net of that name
    connectors   2. every `connectors` entry: the part whose `Role` field matches has pin i on net i
    usb_cc       3. USB_CC1 / USB_CC2 each reach GND through their own 5.1 k +/-1 % resistor
    i2c_pullups  4. I2C_SDA / I2C_SCL each have a 4.7 k +/-1 % resistor to +3V3
    bulk_caps    5. +3V3 carries >= 2 capacitors of >= 10 uF to GND, >= 22 uF in total
    straps       6. BUTTON has a pull-up to +3V3; GPIO8 and GPIO15 are unconnected or carry
                    only pull resistors

The MCU is the component whose `Role` field is `MCU`; its pins are found by pinfunction
`IO<n>` / `GPIO<n>` (case-insensitive).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

from sexpr import atom, child, children, parse, parse_value

ALL_GROUPS = ("signals", "connectors", "usb_cc", "i2c_pullups", "bulk_caps", "straps")
CC_OHMS, CC_TOL = 5100.0, 0.01
PULLUP_OHMS, PULLUP_TOL = 4700.0, 0.01
BULK_MIN_F, BULK_TOTAL_F, BULK_MIN_COUNT = 10e-6, 22e-6, 2
STRAP_GPIOS = (8, 15)
_EPS = 1e-12


def _pin_name(pinfunction: str | None, pin: str | None) -> str | None:
    """KiCad 10 writes pinfunction as "<pin name>_<pin number>"; strip that suffix (only that one)."""
    suffix = f"_{pin}"
    if pinfunction and pin and pinfunction.endswith(suffix) and len(pinfunction) > len(suffix):
        return pinfunction[: -len(suffix)]
    return pinfunction


class Netlist:
    """Components and nets of a kicadsexpr netlist."""

    def __init__(self, text: str):
        tree = parse(text)
        self.comps: dict[str, dict] = {}
        for comp in children(child(tree, "components") or [], "comp"):
            ref = atom(comp, "ref")
            fields = {}
            for f in children(child(comp, "fields") or [], "field"):
                name = atom(f, "name")
                if name is not None:
                    fields[name] = f[2] if len(f) > 2 and isinstance(f[2], str) else ""
            self.comps[ref] = {"value": atom(comp, "value", ""), "fields": fields}
        self.nets: dict[str, list[tuple[str, str, str | None]]] = {}
        self.pin_net: dict[tuple[str, str], str] = {}
        for net in children(child(tree, "nets") or [], "net"):
            name = atom(net, "name", "")
            nodes = []
            for node in children(net, "node"):
                ref, pin = atom(node, "ref"), atom(node, "pin")
                nodes.append((ref, pin, _pin_name(atom(node, "pinfunction"), pin)))
                self.pin_net[(ref, pin)] = name
            self.nets[name] = nodes

    # -- lookups -----------------------------------------------------------------------------
    def by_role(self, role: str) -> str | None:
        for ref, c in self.comps.items():
            if c["fields"].get("Role") == role:
                return ref
        return None

    def find_nets(self, name: str) -> list[str]:
        """Nets named exactly `name` or `<sheet path>/name`."""
        return [n for n in self.nets if n == name or n.endswith("/" + name)]

    def net(self, name: str, errors: list[str], what: str) -> str | None:
        """Resolve `name` to one net; append a missing/ambiguous error and return None if not."""
        found = self.find_nets(name)
        if not found:
            errors.append(f"missing net {name} ({what})")
            return None
        if len(found) > 1:
            errors.append(f"ambiguous net {name} ({what}): matches {', '.join(sorted(found))}")
            return None
        return found[0]

    def other_pin_net(self, ref: str, net: str) -> str | None:
        """For a 2-pin part with a node on `net`, the net of its other pin."""
        mine = [p for r, p, _ in self.nets[net] if r == ref]
        others = [n for (r, p), n in self.pin_net.items() if r == ref and p not in mine]
        return others[0] if others else None

    def parts_on(self, net: str, prefix: str) -> list[str]:
        """Refs `<prefix><digits>` with a node on `net` (once each, in netlist order)."""
        seen: list[str] = []
        for ref, _, _ in self.nets[net]:
            if re.fullmatch(prefix + r"\d+", ref) and ref not in seen:
                seen.append(ref)
        return seen

    def value(self, ref: str) -> float | None:
        try:
            return parse_value(self.comps[ref]["value"])
        except (KeyError, ValueError):
            return None

    def is_net(self, actual: str | None, wanted: str) -> bool:
        return actual is not None and (actual == wanted or actual.endswith("/" + wanted))

    def is_nc(self, ref: str, pin: str) -> bool:
        net = self.pin_net.get((ref, pin))
        return net is None or net.startswith("unconnected-") or len(self.nets[net]) == 1


def _pin_gpio(pinfunction: str | None) -> int | None:
    m = re.fullmatch(r"(?:gp)?io(\d+)", pinfunction or "", re.IGNORECASE)
    return int(m.group(1)) if m else None


def _mcu_pins(nl: Netlist, mcu: str) -> dict[int, str]:
    """GPIO number -> net name for every connected MCU IO pin."""
    out = {}
    for net, nodes in nl.nets.items():
        for ref, _, func in nodes:
            n = _pin_gpio(func)
            if ref == mcu and n is not None:
                out[n] = net
    return out


def _within(value: float | None, target: float, tol: float) -> bool:
    return value is not None and abs(value - target) <= target * tol + _EPS


def check_signals(nl: Netlist, iface: dict) -> list[str]:
    errors: list[str] = []
    signals = iface.get("signals") or {}
    mcu = nl.by_role("MCU")
    if mcu is None:
        return ["missing MCU part (no component with Role = MCU)"] if signals else []
    pins = _mcu_pins(nl, mcu)
    for name, gpio in signals.items():
        m = re.fullmatch(r"GPIO(\d+)", str(gpio))
        if not m:
            errors.append(f"signal {name}: cannot read GPIO number from {gpio!r}")
            continue
        n = int(m.group(1))
        net = nl.net(name, errors, f"signal {name}")
        if net is None:
            continue
        if not nl.is_net(pins.get(n), name):
            where = pins.get(n)
            errors.append(f"signal {name}: MCU pin IO{n} should be on net {name}, "
                          + (f"found on {where}" if where else "found unconnected"))
    return errors


def check_connectors(nl: Netlist, iface: dict) -> list[str]:
    errors: list[str] = []
    for role, nets in (iface.get("connectors") or {}).items():
        ref = nl.by_role(role)
        if ref is None:
            errors.append(f"missing connector part {role} (no component with Role = {role})")
            continue
        for i, wanted in enumerate(nets, 1):
            pin = str(i)
            if wanted == "NC":
                if not nl.is_nc(ref, pin):
                    errors.append(f"{role} pin {pin} ({ref}): should be NC, found on "
                                  f"{nl.pin_net[(ref, pin)]}")
                continue
            actual = nl.pin_net.get((ref, pin))
            if not nl.is_net(actual, wanted):
                errors.append(f"{role} pin {pin} ({ref}): expected {wanted}, found "
                              f"{actual if actual and not nl.is_nc(ref, pin) else 'NC'}")
    return errors


def _resistors_to(nl: Netlist, net: str, rail: str, target: float, tol: float) -> list[str]:
    """Resistors on `net` whose other pin is on `rail` and whose value is within tolerance."""
    return [r for r in nl.parts_on(net, "R")
            if nl.is_net(nl.other_pin_net(r, net), rail) and _within(nl.value(r), target, tol)]


def _shorted_cc_nets(nl: Netlist) -> list[str]:
    """Nets that carry both CC pins (A5 and B5) of the same connector."""
    return sorted({net for (ref, pin), net in nl.pin_net.items()
                   if pin == "A5" and nl.pin_net.get((ref, "B5")) == net})


def check_usb_cc(nl: Netlist, iface: dict) -> list[str]:
    errors: list[str] = []
    shorted = _shorted_cc_nets(nl)
    if shorted:  # a real violation, not an unfinished schematic: do not say "missing"
        return [f"USB_CC1 and USB_CC2 are shorted together (A5 and B5 share net {n}); "
                f"CC2 needs its own net and 5.1 k resistor" for n in shorted]
    used: set[str] = set()
    for cc in ("USB_CC1", "USB_CC2"):
        net = nl.net(cc, errors, "USB-C CC pin")
        if net is None:
            continue
        own = [r for r in _resistors_to(nl, net, "GND", CC_OHMS, CC_TOL) if r not in used]
        if not own:
            errors.append(f"{cc}: no own 5.1 k (+/-1 %) resistor to GND")
        else:
            used.add(own[0])
    return errors


def check_i2c_pullups(nl: Netlist, iface: dict) -> list[str]:
    errors: list[str] = []
    for sig in ("I2C_SDA", "I2C_SCL"):
        net = nl.net(sig, errors, "I2C line")
        if net is not None and not _resistors_to(nl, net, "+3V3", PULLUP_OHMS, PULLUP_TOL):
            errors.append(f"{sig}: no 4.7 k (+/-1 %) pull-up resistor to +3V3")
    return errors


def check_bulk_caps(nl: Netlist, iface: dict) -> list[str]:
    errors: list[str] = []
    net = nl.net("+3V3", errors, "supply rail")
    if net is None:
        return errors
    caps = [nl.value(c) for c in nl.parts_on(net, "C") if nl.is_net(nl.other_pin_net(c, net), "GND")]
    bulk = [v for v in caps if v is not None and v >= BULK_MIN_F - _EPS]
    total = sum(bulk)
    if len(bulk) < BULK_MIN_COUNT or total < BULK_TOTAL_F - _EPS:
        errors.append(f"+3V3: needs >= {BULK_MIN_COUNT} bulk capacitors of >= 10 uF to GND and "
                      f">= 22 uF in total, found {len(bulk)} totalling {total * 1e6:g} uF")
    return errors


def check_straps(nl: Netlist, iface: dict) -> list[str]:
    errors: list[str] = []
    net = nl.net("BUTTON", errors, "boot button")
    if net is not None and not [r for r in nl.parts_on(net, "R")
                                if nl.is_net(nl.other_pin_net(r, net), "+3V3")]:
        errors.append("BUTTON: no pull-up resistor to +3V3")
    mcu = nl.by_role("MCU")
    if mcu is None:
        return errors + ["missing MCU part (no component with Role = MCU)"]
    pins = _mcu_pins(nl, mcu)
    for n in STRAP_GPIOS:
        net = pins.get(n)
        if net is None or net.startswith("unconnected-"):
            continue
        foreign = sorted({r for r, _, f in nl.nets[net]
                          if not (r == mcu and _pin_gpio(f) == n) and not re.fullmatch(r"R\d+", r)})
        if foreign:
            errors.append(f"GPIO{n} (strapping pin): must be unconnected or carry only a pull "
                          f"resistor, but net {net} also has {', '.join(foreign)}")
    return errors


_RULES = {
    "signals": check_signals,
    "connectors": check_connectors,
    "usb_cc": check_usb_cc,
    "i2c_pullups": check_i2c_pullups,
    "bulk_caps": check_bulk_caps,
    "straps": check_straps,
}


def check_netlist(netlist: Path, interface: Path) -> list[str]:
    """Return error strings for `netlist` against `interface`; empty when clean."""
    nl = Netlist(Path(netlist).read_text(encoding="utf-8"))
    iface = yaml.safe_load(Path(interface).read_text(encoding="utf-8")) or {}
    groups = iface.get("checks", list(ALL_GROUPS))
    errors = [f"unknown check group {g!r} in interface `checks` (known: {', '.join(ALL_GROUPS)})"
              for g in groups if g not in _RULES]
    for g in ALL_GROUPS:
        if g in groups:
            errors += _RULES[g](nl, iface)
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    errors = check_netlist(Path(argv[0]), Path(argv[1]))
    for e in errors:
        print(e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
