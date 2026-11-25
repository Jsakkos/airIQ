from gen_pcb import footprint_node, generate_board, read_netlist
from sexpr import atom, child, children, parse

NETLIST = """(export (version "E")
  (components
    (comp (ref "U1") (value "U6") (footprint "test:SOT6_TEST")
      (fields (field (name "Footprint") "test:SOT6_TEST") (field (name "Datasheet") "")
              (field (name "Description") "six pins") (field (name "LCSC") "C0000")
              (field (name "Role") "MCU"))
      (property (name "Sheetname") (value "a")) (property (name "Sheetfile") (value "a.kicad_sch"))
      (sheetpath (names "/a/") (tstamps "/aaaa/")) (tstamps "u1u1"))
    (comp (ref "R1") (value "10k") (footprint "test:R_TEST")
      (fields (field (name "LCSC") "C1"))
      (property (name "dnp") (value "")) (property (name "Sheetfile") (value "a.kicad_sch"))
      (sheetpath (names "/a/") (tstamps "/aaaa/")) (tstamps "r1r1")))
  (nets
    (net (code "1") (name "GND") (class "Default")
      (node (ref "U1") (pin "1") (pinfunction "A") (pintype "input"))
      (node (ref "R1") (pin "2") (pintype "passive")))
    (net (code "2") (name "/a/SIG") (class "Default")
      (node (ref "R1") (pin "1") (pintype "passive")))
    (net (code "3") (name "unconnected-(U1-C-Pad3)") (class "Default")
      (node (ref "U1") (pin "3") (pinfunction "C") (pintype "input+no_connect")))))
"""
LAYOUT = {"board": {"width": 40, "height": 20, "origin": [100, 50]},
          "placement": {"U1": [10, 5, 90]}}


def _comps():
    return {c.ref: c for c in read_netlist(NETLIST)}


def test_read_netlist():
    u1, r1 = _comps()["U1"], _comps()["R1"]
    assert u1.path == "/aaaa/u1u1" and u1.sheetname == "/a/" and u1.sheetfile == "a.kicad_sch"
    assert u1.fields == {"Datasheet": "", "Description": "six pins", "LCSC": "C0000", "Role": "MCU"}
    assert u1.pins["1"] == ("GND", "A", "input") and not u1.dnp
    assert r1.dnp and r1.pins["1"] == ("/a/SIG", "", "passive")


def test_footprint_rotation_nets_and_links(libs):
    u1 = _comps()["U1"]
    fp = footprint_node("tp", u1, libs.footprint("test:SOT6_TEST"), 110.0, 55.0, 90.0)
    assert fp[1] == "test:SOT6_TEST" and child(fp, "at") == ["at", "110", "55", "90"]
    pads = {p[1]: p for p in children(fp, "pad")}
    assert child(pads["1"], "at") == ["at", "-1.2", "-0.95", "180"]   # library 90 + footprint 90
    assert child(pads[""], "at") == ["at", "0", "1.4", "90"]
    assert atom(pads["1"], "net") == "GND" and atom(pads["1"], "pinfunction") == "A"
    assert atom(pads["3"], "net") == "unconnected-(U1-C-Pad3)"
    assert atom(pads["2"], "net") is None and atom(pads[""], "net") is None
    props = {p[1]: p for p in children(fp, "property")}
    assert props["Reference"][2] == "U1" and props["Value"][2] == "U6"
    assert child(props["Reference"], "at") == ["at", "0", "-2.5", "90"]
    assert props["Role"][2] == "MCU" and props["LCSC"][2] == "C0000"
    assert child(child(fp, "fp_text"), "at") == ["at", "0", "0", "180"]
    assert atom(fp, "path") == "/aaaa/u1u1" and atom(fp, "sheetfile") == "a.kicad_sch"
    uuids = [atom(n, "uuid") for n in [fp, *children(fp, "pad"), *children(fp, "property")]]
    assert len(uuids) == len(set(uuids))


def test_footprint_uuids_are_stable_and_per_reference(libs):
    u1 = _comps()["U1"]
    a = footprint_node("tp", u1, libs.footprint("test:SOT6_TEST"), 0, 0, 0)
    b = footprint_node("tp", u1, libs.footprint("test:SOT6_TEST"), 5, 5, 180)
    assert atom(a, "uuid") == atom(b, "uuid")
    assert [atom(p, "uuid") for p in children(a, "pad")] == [atom(p, "uuid") for p in children(b, "pad")]
    u1.ref = "U2"
    c = footprint_node("tp", u1, libs.footprint("test:SOT6_TEST"), 0, 0, 0)
    assert atom(c, "uuid") != atom(a, "uuid")


def test_dnp_flag_reaches_the_footprint(libs):
    fp = footprint_node("tp", _comps()["R1"], libs.footprint("test:R_TEST"), 0, 0, 0)
    assert child(fp, "attr") == ["attr", "smd", "dnp"]


def _board(libs, existing=None, layout=LAYOUT):
    return generate_board("tp", "Test", "1", "", "hardware/src/tp/layout.yaml",
                          list(_comps().values()), layout, libs, existing)


def test_board_outline_origin_and_placement(libs):
    text, unplaced = _board(libs)
    tree = parse(text)
    assert atom(tree, "version") == "20260206"
    rect = child(tree, "gr_rect")
    assert child(rect, "start") == ["start", "100", "50"] and child(rect, "end") == ["end", "140", "70"]
    setup = child(tree, "setup")
    assert child(setup, "aux_axis_origin") == ["aux_axis_origin", "100", "70"]   # CPL origin
    fps = {next(p[2] for p in children(f, "property") if p[1] == "Reference"): f
           for f in children(tree, "footprint")}
    assert child(fps["U1"], "at") == ["at", "110", "55", "90"]
    assert unplaced == ["R1"] and child(fps["R1"], "at")[1:3] == ["150", "50"]   # parked
    assert text == _board(libs)[0]


def test_regeneration_keeps_routing_and_replaces_owned_items(libs):
    first, _ = _board(libs)
    routed = first.rstrip()[:-1] + """
  (segment (start 1 2) (end 3 4) (width 0.2) (layer "F.Cu") (net "GND") (uuid "s1"))
  (via (at 3 4) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net "GND") (uuid "v1"))
  (zone (net "GND") (layer "B.Cu") (uuid "z1") (polygon (pts (xy 0 0) (xy 1 0) (xy 1 1))))
  (gr_line (start 0 0) (end 9 9) (layer "Edge.Cuts") (uuid "old-edge"))
  (gr_text "note" (at 1 1 0) (layer "F.SilkS") (uuid "t1"))
)
"""
    moved = routed.replace('(at 150 50)', '(at 160 60 45)')   # R1, unplaced, moved by hand
    text, _ = _board(libs, moved)
    tree = parse(text)
    assert [atom(i, "uuid") for i in children(tree, "segment")] == ["s1"]
    assert [atom(i, "uuid") for i in children(tree, "via")] == ["v1"]
    assert [atom(i, "uuid") for i in children(tree, "zone")] == ["z1"]
    assert [atom(i, "uuid") for i in children(tree, "gr_text")] == ["t1"]
    assert children(tree, "gr_line") == [] and len(children(tree, "gr_rect")) == 1
    r1 = next(f for f in children(tree, "footprint") if f[1] == "test:R_TEST")
    assert child(r1, "at") == ["at", "160", "60", "45"]    # kept where it was moved to
    again, _ = _board(libs, text)
    assert again == text
