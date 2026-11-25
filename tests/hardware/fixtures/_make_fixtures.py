"""Regenerates the netlist / board fixtures in this directory.

Run `python _make_fixtures.py` from this folder. The output mimics the structure of
`kicad-cli sch export netlist --format kicadsexpr` (KiCad 10): `(export (design ..)
(components (comp (ref) (value) (fields (field (name N) V)) ..)) (nets (net (code) (name)
(node (ref) (pin) (pinfunction) (pintype)))))`. Each variant differs from `good.net` by one
deliberate violation. Not collected by pytest (leading underscore).
"""
from pathlib import Path

HERE = Path(__file__).parent


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def netlist(comps, nets):
    """comps: [(ref, value, {field: value})]; nets: [(name, [(ref, pin, pinfunction|None)])]."""
    o = ["(export", '\t(version "E")', "\t(design", '\t\t(source "fixture.kicad_sch")',
         '\t\t(tool "Eeschema 10.0.8")', "\t)", "\t(components"]
    for ref, value, fields in comps:
        o += ["\t\t(comp", f"\t\t\t(ref {q(ref)})", f"\t\t\t(value {q(value)})", "\t\t\t(fields"]
        for k, v in fields.items():
            o.append(f"\t\t\t\t(field (name {q(k)}) {q(v)})")
        o += ["\t\t\t)", "\t\t)"]
    o += ["\t)", "\t(nets"]
    for code, (name, nodes) in enumerate(nets, 1):
        o += ["\t\t(net", f"\t\t\t(code {q(code)})", f"\t\t\t(name {q(name)})"]
        for ref, pin, func in nodes:
            o += ["\t\t\t(node", f"\t\t\t\t(ref {q(ref)})", f"\t\t\t\t(pin {q(pin)})"]
            if func:
                o.append(f"\t\t\t\t(pinfunction {q(func)})")
            o += ['\t\t\t\t(pintype "passive")', "\t\t\t)"]
        o.append("\t\t)")
    o += ["\t)", ")", ""]
    return "\n".join(o)


def base():
    comps = {
        "U1": ("ESP32-C6-MINI-1", {"Role": "MCU"}),
        "J1": ("SEN66", {"Role": "J_SEN66", "LCSC": "C1001"}),
        "J2": ("USB_C", {"Role": "J_USB"}),
        "R1": ("5.1k", {}), "R2": ("5.1k", {}),
        "R3": ("4.7k", {}), "R4": ("4.7k", {}),
        "R5": ("10k", {}), "R9": ("10k", {}),
        "C1": ("10u", {}), "C2": ("22u", {}), "C3": ("100n", {}),
    }
    nets = {
        "+3V3": [("U1", "2", "3V3"), ("J1", "1", None), ("R3", "2", None), ("R4", "2", None),
                 ("R5", "2", None), ("R9", "2", None), ("C1", "1", None), ("C2", "1", None),
                 ("C3", "1", None)],
        "GND": [("U1", "1", "GND"), ("J1", "2", None), ("J1", "5", None), ("R1", "2", None),
                ("R2", "2", None), ("C1", "2", None), ("C2", "2", None), ("C3", "2", None)],
        "I2C_SDA": [("U1", "6", "IO6"), ("J1", "3", None), ("R3", "1", None)],
        "I2C_SCL": [("U1", "7", "IO7"), ("J1", "4", None), ("R4", "1", None)],
        "BUTTON": [("U1", "9", "IO9"), ("R5", "1", None)],
        "STRAP15": [("U1", "15", "IO15"), ("R9", "1", None)],
        "USB_CC1": [("J2", "A5", None), ("R1", "1", None)],
        "USB_CC2": [("J2", "B5", None), ("R2", "1", None)],
        "unconnected-(J1-Pad6)": [("J1", "6", None)],
    }
    return comps, nets


def write(name, comps, nets):
    text = netlist([(r, *comps[r]) for r in comps], list(nets.items()))
    (HERE / name).write_text(text, encoding="utf-8", newline="\n")


def drop(comps, nets, ref):
    """Remove component `ref` from the parts and from every net."""
    del comps[ref]
    for k in nets:
        nets[k] = [x for x in nets[k] if x[0] != ref]


def board(w, h, parts):
    edge = ""
    for a, b in [("0 0", f"{w} 0"), (f"{w} 0", f"{w} {h}"), (f"{w} {h}", f"0 {h}"), (f"0 {h}", "0 0")]:
        edge += (f"\t(gr_line\n\t\t(start {a})\n\t\t(end {b})\n\t\t(stroke\n\t\t\t(width 0.05)\n"
                 f'\t\t\t(type default)\n\t\t)\n\t\t(layer "Edge.Cuts")\n\t)\n')
    return ('(kicad_pcb\n\t(version 20250907)\n\t(generator "pcbnew")\n\t(general\n'
            '\t\t(thickness 1.6)\n\t)\n\t(layers\n\t\t(0 "F.Cu" signal)\n\t\t(2 "B.Cu" signal)\n'
            '\t\t(25 "Edge.Cuts" user)\n\t)\n' + edge + "".join(parts) + ")\n")


def footprint(ref, layer, x, y):
    return (f'\t(footprint "R_0402"\n\t\t(layer "{layer}")\n\t\t(at {x} {y})\n'
            f'\t\t(property "Reference" "{ref}"\n\t\t\t(at 0 0 0)\n\t\t\t(layer "F.SilkS")\n\t\t)\n'
            '\t\t(fp_rect\n\t\t\t(start -0.5 -0.25)\n\t\t\t(end 0.5 0.25)\n'
            '\t\t\t(layer "F.Fab")\n\t\t)\n\t)\n')


def main():
    c, n = base()
    write("good.net", c, n)

    c, n = base()  # rule 1: MCU IO6 / IO7 land on the swapped nets
    n["I2C_SDA"][0], n["I2C_SCL"][0] = ("U1", "7", "IO7"), ("U1", "6", "IO6")
    write("swapped_i2c.net", c, n)

    c, n = base()  # rule 2: SEN66 connector pins mirrored
    for net in n.values():
        for i, (r, p, f) in enumerate(net):
            if r == "J1":
                net[i] = (r, str(7 - int(p)), f)
    n["unconnected-(J1-Pad6)"] = [("J1", "1", None)]
    write("mirrored_sen66.net", c, n)

    c, n = base()  # rule 3: CC1 and CC2 tied together, one resistor for both
    n["USB_CC1"].append(("J2", "B5", None))
    del n["USB_CC2"]
    drop(c, n, "R2")
    write("shared_cc.net", c, n)

    c, n = base()  # rule 3: wrong CC2 resistor value
    c["R2"] = ("10k", {})
    write("cc_wrong_value.net", c, n)

    c, n = base()  # rule 4: no SCL pull-up
    drop(c, n, "R4")
    write("no_i2c_pullup.net", c, n)

    c, n = base()  # rule 5: only 10 uF of bulk on +3V3
    drop(c, n, "C2")
    write("no_bulk.net", c, n)

    c, n = base()  # rule 6: no BUTTON pull-up
    drop(c, n, "R5")
    write("no_button_pullup.net", c, n)

    c, n = base()  # rule 6: GPIO8 drives an LED instead of being left alone
    c["D1"] = ("LED", {})
    n["LED8"] = [("U1", "8", "IO8"), ("D1", "1", None)]
    write("strap_led.net", c, n)

    c, n = base()  # hierarchical sheet: local nets carry a sheet path prefix
    for old in ("I2C_SDA", "I2C_SCL", "BUTTON", "USB_CC1", "USB_CC2"):
        n["/main/" + old] = n.pop(old)
    write("hier.net", c, n)

    c, n = base()  # two nets both ending in /I2C_SDA
    c["TP1"] = ("TP", {})
    n["/a/I2C_SDA"] = n.pop("I2C_SDA")
    n["/b/I2C_SDA"] = [("TP1", "1", None)]
    write("ambiguous.net", c, n)

    c, n = base()  # rule 2: pin 6 of the SEN66 connector is NC but wired to a test point
    c["TP1"] = ("TP", {})
    del n["unconnected-(J1-Pad6)"]
    n["Net-(J1-Pad6)"] = [("J1", "6", None), ("TP1", "1", None)]
    write("nc_connected.net", c, n)

    # Sense tongue: just a Qwiic connector
    tc = {"J1": ("QWIIC", {"Role": "J_QWIIC_TONGUE"})}
    tn = {"GND": [("J1", "1", None)], "+3V3": [("J1", "2", None)],
          "I2C_SDA": [("J1", "3", None)], "I2C_SCL": [("J1", "4", None)]}
    write("tongue.net", tc, tn)

    ok = [footprint("R1", "F.Cu", 10, 10), footprint("R2", "F.Cu", 20, 10)]
    bottom = [footprint("R1", "F.Cu", 10, 10), footprint("R2", "B.Cu", 20, 10)]
    for name, text in [("board_ok", board(60, 30, ok)), ("board_61x30", board(61, 30, ok)),
                       ("board_bottom_part", board(60, 30, bottom))]:
        (HERE / (name + ".kicad_pcb")).write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
