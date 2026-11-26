"""Shared helpers for the enclosure generators: parameters, named features and dof-0 sketches.

A generator builds a `Script`: the list of SolidCraft commands an MCP `batch` takes and
`solidcraft-cli run` runs (`{"commands": [...]}`). The script starts from an empty design named
after the part, so `component.insert_design` gives the component that name.

Conventions every generator follows (and tests/enclosure checks):
- every size is a named parameter with a comment saying where it comes from; feature fields and
  sketch points are expressions over those parameters, so the design follows them;
- every feature and sketch has a unique name (no "Sketch1"), every body is named;
- sketches are closed polylines and circles whose points are expressions over parameters, so
  they solve at dof 0 without dimensions (a point fixed by an expression cannot flip side the way
  a dimension driven through 0 can); `encbuild` fails the build on any sketch above dof 0;
- feature ids are counted here (each feature and each sketch takes the next id, as SolidCraft
  numbers them), so configuration rules can name features by id.

Pure Python: nothing here needs SolidCraft.
"""
from __future__ import annotations

import ast
import json
import math
import operator
import re
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENCLOSURE = REPO / "enclosure"
INTERFACE = REPO / "hardware" / "interface.yaml"

NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@lru_cache(maxsize=1)
def interface() -> dict:
    """hardware/interface.yaml, parsed (PyYAML)."""
    import yaml
    return yaml.safe_load(INTERFACE.read_text(encoding="utf-8"))


def mechanical(board: str) -> dict:
    """interface.yaml `mechanical.<board>` (main, tongue)."""
    return interface()["mechanical"][board]


def num(value: float) -> str:
    """A number as SolidCraft expression text: no exponent, no trailing zeros."""
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


# --- expression evaluation (the subset the generators write) -------------------------------

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow}
_UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {"sqrt": math.sqrt, "abs": abs, "min": min, "max": max, "sin": math.sin,
          "cos": math.cos, "tan": math.tan}
_UNIT = re.compile(r"(?<=[0-9.])\s*mm\b")


def evaluate(expr: str | float, values: dict[str, float]) -> float:
    """Value of a generator expression in mm: numbers, parameter names, pi, + - * / ^ and
    sqrt/abs/min/max/sin/cos/tan. A trailing "mm" on a number is dropped; other units are refused."""
    if isinstance(expr, (int, float)):
        return float(expr)
    text = _UNIT.sub("", expr).replace("^", "**")
    if re.search(r"\b(deg|rad|cm|in|ft|m)\b", text):
        raise ValueError(f"unit not handled by the generator evaluator: {expr!r}")

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id == "pi":
                return math.pi
            if node.id in values:
                return values[node.id]
            raise KeyError(f"unknown parameter {node.id!r} in {expr!r}")
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
            return _BIN[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](ev(node.operand))
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in _FUNCS and not node.keywords):
            return float(_FUNCS[node.func.id](*[ev(a) for a in node.args]))
        raise ValueError(f"unsupported expression {expr!r}")

    return ev(ast.parse(text, mode="eval"))


def names_in(expr: str | float) -> set[str]:
    """Parameter names an expression uses."""
    if not isinstance(expr, str):
        return set()
    return {n for n in NAME_RE.findall(_UNIT.sub("", expr)) if n not in ("pi", *_FUNCS)}


# --- the script ----------------------------------------------------------------------------

@dataclass
class Param:
    name: str
    expression: str      # as SolidCraft stores it ("55.2 mm", "L - 2 * inset", "0")
    value: float         # mm (or unitless)
    unit: str            # "mm" or "" (unitless)
    comment: str


class Script:
    """A SolidCraft command script under construction."""

    def __init__(self, design: str):
        self.design = design
        self.commands: list[dict] = [{"command": "file.new", "params": {"name": design}}]
        self.params: dict[str, Param] = {}
        self.features: dict[str, int] = {}      # feature and sketch names -> id
        self.bodies: list[str] = []             # body names, in creation order
        self.sketches: list[str] = []
        self.next_id = 1
        self._sketch: str | None = None

    # parameters
    def param(self, name: str, value: float | str, comment: str, unit: str = "mm",
              favorite: bool = False) -> str:
        """Add a user parameter. `value` is a number (in `unit`) or an expression over earlier
        parameters. `comment` says where the value comes from (shown in SolidCraft's table)."""
        if not NAME_RE.fullmatch(name):
            raise ValueError(f"bad parameter name {name!r}")
        if name in self.params:
            raise ValueError(f"parameter {name!r} defined twice")
        if not comment.strip():
            raise ValueError(f"parameter {name!r} needs a comment saying where it comes from")
        if isinstance(value, str):
            unknown = names_in(value) - set(self.params)
            if unknown:
                raise KeyError(f"{name}: unknown parameters {sorted(unknown)}")
            expression, numeric = value, evaluate(value, self.values())
        else:
            numeric = float(value)
            expression = f"{num(numeric)} {unit}".strip()
        self.params[name] = Param(name, expression, numeric, unit, comment)
        params = {"name": name, "expression": expression, "comment": comment}
        if unit != "mm":
            params["unit"] = unit
        if favorite:
            params["favorite"] = True
        self.commands.append({"command": "parameters.add", "params": params})
        return name

    def values(self) -> dict[str, float]:
        return {n: p.value for n, p in self.params.items()}

    def v(self, expr: str | float) -> float:
        """Numeric value of an expression over the parameters (for picks and expectations)."""
        return evaluate(expr, self.values())

    def _check_exprs(self, *exprs):
        for e in exprs:
            unknown = names_in(e) - set(self.params)
            if unknown:
                raise KeyError(f"unknown parameters {sorted(unknown)} in {e!r}")

    # raw commands
    def cmd(self, command: str, **params) -> dict:
        """Any command that does not make a feature or a sketch."""
        step = {"command": command, "params": params}
        self.commands.append(step)
        return step

    def _feature(self, command: str, name: str, params: dict, body: str | None = None) -> int:
        if self._sketch is not None:
            raise RuntimeError(f"{name}: sketch {self._sketch} is still open")
        if self.next_id is None:
            raise RuntimeError(f"{name}: feature ids are no longer known (after a STEP import)")
        if not name or name in self.features:
            raise ValueError(f"feature name {name!r} missing or used twice")
        params = {**params, "name": name}
        if body is not None:
            if body in self.bodies:
                raise ValueError(f"body name {body!r} used twice")
            params["body_name"] = body
            self.bodies.append(body)
        self.commands.append({"command": command, "params": params})
        fid = self.next_id
        self.features[name] = fid
        self.next_id += 1
        return fid

    # features (fields are expressions over the parameters)
    def box(self, name: str, corner, size, body: str | None = None, operation: str = "new",
            targets: list[str] | None = None) -> int:
        """solid.box from its minimum corner [x, y, z] with size [dx, dy, dz]."""
        self._check_exprs(*corner, *size)
        params = {"corner": list(corner), "length": size[0], "width": size[1], "height": size[2],
                  "operation": operation}
        if targets:
            params["targets"] = targets
        return self._feature("solid.box", name, params, body if operation == "new" else None)

    def cylinder(self, name: str, base, diameter, height, axis="Z", body: str | None = None,
                 operation: str = "new", targets: list[str] | None = None) -> int:
        """solid.cylinder: `base` is the centre of the bottom face."""
        self._check_exprs(*base, diameter, height)
        params = {"base": list(base), "diameter": diameter, "height": height, "axis": axis,
                  "operation": operation}
        if targets:
            params["targets"] = targets
        return self._feature("solid.cylinder", name, params, body if operation == "new" else None)

    def fillet(self, name: str, edges: list[list[float]], radius, body: str | None = None) -> int:
        """solid.fillet. Edge picks are plain numbers (the pick then follows its edge)."""
        self._check_exprs(radius)
        params = {"edges": [[round(c, 6) for c in e] for e in edges], "radius": radius}
        if body:
            params["body"] = body
        return self._feature("solid.fillet", name, params)

    def extrude(self, name: str, sketch: str, distance, body: str | None = None,
                operation: str = "new", targets: list[str] | None = None, **extra) -> int:
        self._check_exprs(distance)
        params = {"sketch": sketch, "distance": distance, "operation": operation, **extra}
        if targets:
            params["targets"] = targets
        return self._feature("solid.extrude", name, params, body if operation == "new" else None)

    def revolve(self, name: str, sketch: str, origin, direction, angle: str,
                body: str | None = None, operation: str = "new",
                targets: list[str] | None = None) -> int:
        """solid.revolve of a sketch about the axis through `origin` (expressions) along
        `direction` (numbers). The profile leaves its sketch plane the way the sketch's normal
        points (SolidCraft's default `sketch_normal` convention), whichever way `direction` points."""
        self._check_exprs(*origin)
        params = {"sketch": sketch, "axis": {"origin": list(origin), "dir": list(direction)},
                  "angle": angle, "operation": operation}
        if targets:
            params["targets"] = targets
        return self._feature("solid.revolve", name, params, body if operation == "new" else None)

    def combine(self, name: str, target: str, tools: list[str], operation: str = "join") -> int:
        """solid.combine: the tool bodies are used up."""
        fid = self._feature("solid.combine", name, {"target": target, "tools": tools,
                                                    "operation": operation})
        for t in tools:
            self.bodies.remove(t)
        return fid

    def rename_body(self, old: str, new: str):
        self.bodies[self.bodies.index(old)] = new
        self.cmd("body.rename", body=old, name=new)

    # sketches
    @contextmanager
    def sketch(self, name: str, plane, offset: str | float | None = None):
        """A named sketch on `plane` ("XY", "XZ", "YZ" or {origin, x_dir, y_dir}), moved along
        its normal by `offset`. Yields a `Sketch`; on exit the sketch is solved (the build
        checks dof 0) and finished."""
        params = {"plane": plane}
        if offset is not None:
            self._check_exprs(offset)
            params["offset"] = offset
        self._feature("sketch.create", name, params)
        self.sketches.append(name)
        self._sketch = name
        try:
            yield Sketch(self)
        finally:
            self._sketch = None
        self.cmd("sketch.solve")
        self.cmd("sketch.finish")

    # configurations
    def configuration(self, param: str, rows: dict[str, tuple[str, list[str]]],
                      default: str):
        """Configuration rows that set `param` and suppress features, plus rules so that
        changing `param` alone switches the suppressions (SolidCraft 0.48 runs the rules on a
        parameter change).

        rows: {row name: (param value, [features suppressed in that row])}."""
        switched = sorted({f for _, sup in rows.values() for f in sup}, key=self.features.get)
        for f in switched:
            if f not in self.features:
                raise KeyError(f"no feature {f!r}")
        self.cmd("config.configure", params=[param], features=switched)
        for i, (row, (value, suppressed)) in enumerate(rows.items()):
            values = {f"param:{param}": value}
            values.update({f"suppress:{f}": "true" if f in suppressed else "false"
                           for f in switched})
            if i == 0:
                self.cmd("config.row", name="Default", rename=row, values=values)
            else:
                self.cmd("config.row", name=row, values=values)
        values = [v for v, _ in rows.values()]
        rules = [{"id": f"{param}-values", "name": f"{param} is one of {', '.join(values)}",
                  "condition": {"type": "always"},
                  "effect": {"type": "allow_parameter_values", "parameter": param,
                             "expressions": values}}]
        for row, (value, suppressed) in rows.items():
            for f in switched:
                rules.append({
                    "id": f"{row}:{f}", "name": f"{row}: {'suppress' if f in suppressed else 'keep'} {f}",
                    "condition": {"type": "parameter", "parameter": param, "operator": "eq",
                                  "expression": value},
                    "effect": {"type": "drive_suppression", "feature": self.features[f],
                               "value": f in suppressed}})
        self.cmd("config.rule", rules=rules)
        self.cmd("config.activate", row=default)

    # output
    def to_dict(self) -> dict:
        if self._sketch is not None:
            raise RuntimeError(f"sketch {self._sketch} still open")
        return {"commands": self.commands}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=1)


class Sketch:
    """Drawing helpers for an open sketch. Every point is given as expressions over the
    parameters, which fixes it (dof 0) and makes it follow them."""

    def __init__(self, script: Script):
        self.s = script

    def _point(self, pt) -> list:
        x, y = pt
        self.s._check_exprs(x, y)
        if not (names_in(x) or names_in(y)):
            raise ValueError(f"point {pt!r} names no parameter, so it would not be fixed")
        return [x, y]

    def polyline(self, points, closed: bool = True):
        """A closed polygon through `points` [(x, y), ...] (sketch coordinates)."""
        self.s.cmd("sketch.line", points=[self._point(p) for p in points], closed=closed)

    def rect(self, x0, y0, x1, y1):
        self.polyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])

    def circle(self, center, diameter):
        self.s._check_exprs(diameter)
        self.s.cmd("sketch.circle.center", center=self._point(center), diameter=diameter)

    def text(self, content: str, at, height, expression: bool = False, align: str = "center"):
        """Text outlines with the baseline starting at `at` (expressions) and capital height
        `height`. `content` is the words, or with `expression=True` a text expression over the
        parameters (`"number(clr_t1, 2)"`, `"'L' + number(w, 1)"`), so a label follows its value.
        The glyph outlines extrude like any profile (a deboss is a cut); the sketch solves at dof 0."""
        self.s._check_exprs(height)
        self._point(at)
        key = "text_expression" if expression else "text"
        self.s.cmd("sketch.text", **{key: content}, at=list(at), height=height, align=align)
