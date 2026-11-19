"""The palette, computed from the parameter file (parameters.toml).

Each base colour gets a scale of 12 steps per mode: the neutral from curves of
its own, every hue from the shared lightness and chroma curves of its mode, its
own hue angle and peak chroma, and the steps whose lightness it moves. Each step is
set in OKLCH and fitted into sRGB.

The parameter file is checked as a whole before anything is computed: an
unknown key, a missing one, a value of the wrong type or out of range raises a
ParameterError that names the key's path.
"""

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from typing import Any, Literal, get_args

from coloraide import Color

type Mode = Literal["light", "dark"]
MODES: tuple[Mode, ...] = get_args(Mode.__value__)
STEPS = 12
STEP_NAMES = frozenset(str(step) for step in range(1, STEPS + 1))
"""The steps' names in the parameter file and the token files: "1" to "12"."""
MAIN_STEP = 9
"""The step a base colour's plain name stands for: its solid fill at rest."""

PARAMETER_FILE = "parameters.toml"
NEUTRAL = "neutral"
_NAME = re.compile(r"^[a-z]+$")

type Scale = list[str]
"""The 12 steps of one base colour in one mode, as ``#rrggbb``, step 1 first."""

type Palette = dict[str, Scale]
"""One mode's scales by base colour, the neutral first."""


class ParameterError(ValueError):
    """The parameter file breaks its schema; the message names the key's path."""


@dataclass(frozen=True)
class NeutralCurves:
    lightness: tuple[float, ...]
    chroma: tuple[float, ...]
    hue: tuple[float, ...]


@dataclass(frozen=True)
class Curve:
    lightness: tuple[float, ...]
    chroma: tuple[float, ...]
    """Per step, a share of the hue's peak chroma."""


@dataclass(frozen=True)
class Hue:
    angle: float
    """The OKLCH hue angle, in degrees."""
    chroma: float
    """The peak chroma, which the curve's shares scale."""
    lightness: Mapping[Mode, Mapping[int, float]]
    """Per mode, the steps whose lightness leaves the shared curve."""


@dataclass(frozen=True)
class Parameters:
    neutral: Mapping[Mode, NeutralCurves]
    curve: Mapping[Mode, Curve]
    hues: Mapping[str, Hue]


# The ranges a value may take: OKLCH lightness 0-1, chroma 0-0.4 (beyond sRGB
# and Display P3), hue in degrees, and a chroma share up to twice the peak.
_LIGHTNESS = (0.0, 1.0)
_CHROMA = (0.0, 0.4)
_HUE = (0.0, 360.0)
_SHARE = (0.0, 2.0)


def _table(value: object, where: str, keys: set[str], *, required: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ParameterError(f"{where}: needs a table")
    unknown = sorted(set(value) - keys)
    if unknown:
        raise ParameterError(f"{where}: unknown keys {unknown}; allowed: {sorted(keys)}")
    missing = sorted((keys if required is None else required) - set(value))
    if missing:
        raise ParameterError(f"{where}: missing {missing}")
    return value


def _number(value: object, where: str, bounds: tuple[float, float]) -> float:
    low, high = bounds
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ParameterError(f"{where}: needs a number, not {value!r}")
    if not low <= value <= high:
        raise ParameterError(f"{where}: {value} is outside {low}-{high}")
    return float(value)


def _curve(value: object, where: str, bounds: tuple[float, float]) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != STEPS:
        raise ParameterError(f"{where}: needs {STEPS} values, one per step")
    return tuple(_number(item, f"{where}[{index}]", bounds) for index, item in enumerate(value))


def _steps(value: object, where: str) -> dict[int, float]:
    table = _table(value, where, set(STEP_NAMES), required=set())
    return {int(step): _number(item, f"{where}.{step}", _LIGHTNESS) for step, item in table.items()}


def parse(raw: dict[str, Any]) -> Parameters:
    """The parameter file's contents, checked against its schema."""
    where = PARAMETER_FILE
    top = _table(raw, where, {"neutral", "curve", "hue"})
    neutral_modes = _table(top["neutral"], f"{where}: neutral", set(MODES))
    curve_modes = _table(top["curve"], f"{where}: curve", set(MODES))
    neutral: dict[Mode, NeutralCurves] = {}
    curve: dict[Mode, Curve] = {}
    for mode in MODES:
        at = f"{where}: neutral.{mode}"
        table = _table(neutral_modes[mode], at, {"lightness", "chroma", "hue"})
        neutral[mode] = NeutralCurves(
            _curve(table["lightness"], f"{at}.lightness", _LIGHTNESS),
            _curve(table["chroma"], f"{at}.chroma", _CHROMA),
            _curve(table["hue"], f"{at}.hue", _HUE),
        )
        at = f"{where}: curve.{mode}"
        table = _table(curve_modes[mode], at, {"lightness", "chroma"})
        curve[mode] = Curve(
            _curve(table["lightness"], f"{at}.lightness", _LIGHTNESS), _curve(table["chroma"], f"{at}.chroma", _SHARE)
        )
    hue_tables = top["hue"]
    if not isinstance(hue_tables, dict) or not hue_tables:
        raise ParameterError(f"{where}: hue: needs a table of hues")
    hues: dict[str, Hue] = {}
    for name, spec in hue_tables.items():
        at = f"{where}: hue.{name}"
        if not _NAME.match(name) or name == NEUTRAL:
            raise ParameterError(f"{at}: a hue's name is lowercase letters and not {NEUTRAL!r}")
        table = _table(spec, at, {"angle", "chroma", *MODES}, required={"angle", "chroma"})
        hues[name] = Hue(
            _number(table["angle"], f"{at}.angle", _HUE),
            _number(table["chroma"], f"{at}.chroma", _CHROMA),
            {mode: _steps(table[mode], f"{at}.{mode}") for mode in MODES if mode in table},
        )
    return Parameters(neutral, curve, hues)


def load_parameters() -> Parameters:
    """The parameter file shipped with the package, checked."""
    try:
        raw = tomllib.loads(files("copper_design").joinpath(PARAMETER_FILE).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ParameterError(f"{PARAMETER_FILE}: {error}") from error
    return parse(raw)


def fit_hex(lightness: float, chroma: float, hue: float) -> str:
    """An OKLCH colour fitted into sRGB, as ``#rrggbb``.

    Ray-trace gamut mapping keeps lightness and hue and lowers chroma until the
    colour fits, so a step's lightness holds even where a hue cannot reach its
    chroma in sRGB.
    """
    colour = Color("oklch", [lightness, chroma, hue]).fit("srgb", method="raytrace").convert("srgb")
    return colour.to_string(hex=True)


def _neutral(curves: NeutralCurves) -> Scale:
    return [fit_hex(*step) for step in zip(curves.lightness, curves.chroma, curves.hue, strict=True)]


def _hue(spec: Hue, curve: Curve, mode: Mode) -> Scale:
    lightness = list(curve.lightness)
    for step, value in spec.lightness.get(mode, {}).items():
        lightness[step - 1] = value
    return [
        fit_hex(step_lightness, spec.chroma * share, spec.angle)
        for step_lightness, share in zip(lightness, curve.chroma, strict=True)
    ]


def build(parameters: Parameters) -> dict[Mode, Palette]:
    """Both modes' palettes, by mode, the neutral first."""
    return {
        mode: {NEUTRAL: _neutral(parameters.neutral[mode])}
        | {name: _hue(spec, parameters.curve[mode], mode) for name, spec in parameters.hues.items()}
        for mode in MODES
    }
