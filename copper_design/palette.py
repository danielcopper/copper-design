"""The palette, computed from the parameter file (parameters.toml).

Each base colour gets a scale of 12 steps per mode: the neutral from curves of
its own, every hue from the shared lightness and chroma curves of its mode, its
own hue and peak chroma, and the steps whose lightness it moves. Each step is
set in OKLCH and fitted into sRGB.
"""

import tomllib
from importlib.resources import files
from typing import Any

from coloraide import Color

MODES = ("light", "dark")
STEPS = 12

type Scale = list[str]
"""The 12 steps of one base colour in one mode, as ``#rrggbb``, step 1 first."""

type Palette = dict[str, Scale]
"""One mode's scales by base colour, the neutral first."""


def fit_hex(lightness: float, chroma: float, hue: float) -> str:
    """An OKLCH colour fitted into sRGB, as ``#rrggbb``.

    Ray-trace gamut mapping keeps lightness and hue and lowers chroma until the
    colour fits, so a step's lightness holds even where a hue cannot reach its
    chroma in sRGB.
    """
    colour = Color("oklch", [lightness, chroma, hue]).fit("srgb", method="raytrace").convert("srgb")
    return colour.to_string(hex=True)


def load_parameters() -> dict[str, Any]:
    """The parameter file shipped with the package."""
    return tomllib.loads(files("copper_design").joinpath("parameters.toml").read_text(encoding="utf-8"))


def _curve(table: dict[str, Any], key: str, where: str) -> list[float]:
    values = table.get(key)
    if not isinstance(values, list) or len(values) != STEPS:
        raise ValueError(f"{where}.{key}: needs {STEPS} values, one per step")
    return [float(value) for value in values]


def _neutral(parameters: dict[str, Any], mode: str) -> Scale:
    table = parameters["neutral"][mode]
    where = f"neutral.{mode}"
    curves = zip(
        _curve(table, "lightness", where), _curve(table, "chroma", where), _curve(table, "hue", where), strict=True
    )
    return [fit_hex(lightness, chroma, hue) for lightness, chroma, hue in curves]


def _hue(parameters: dict[str, Any], name: str, mode: str) -> Scale:
    spec = parameters["hue"][name]
    curve = parameters["curve"][mode]
    lightness = _curve(curve, "lightness", f"curve.{mode}")
    shares = _curve(curve, "chroma", f"curve.{mode}")
    for step, value in spec.get(mode, {}).items():
        if not step.isdigit() or not 1 <= int(step) <= STEPS:
            raise ValueError(f"hue.{name}.{mode}: {step!r} is not a step 1-{STEPS}")
        lightness[int(step) - 1] = float(value)
    return [
        fit_hex(step_lightness, spec["chroma"] * share, spec["hue"])
        for step_lightness, share in zip(lightness, shares, strict=True)
    ]


def build(parameters: dict[str, Any]) -> dict[str, Palette]:
    """Both modes' palettes, by mode, from the given parameters."""
    return {
        mode: {"neutral": _neutral(parameters, mode)}
        | {name: _hue(parameters, name, mode) for name in parameters["hue"]}
        for mode in MODES
    }
