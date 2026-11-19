"""The herdr port: copper-light.json and copper-dark.json in herdr's theme format.

herdr 0.1.16 reads ``themes/<name>.json``: ``background``, ``foreground``,
``selection`` and an optional ``cursor`` as ``#rrggbb``, ``ansi`` as 16 of them,
and an optional ``colors`` that overrides its panel colours by name with
``#rrggbb`` or ``#rrggbbaa``. It takes a theme as light when the background's
luminance (Rec. 709 weights over the 8-bit channels) is above one half. This
docstring is the one description of that format here; the template points to it.

ANSI order: black, red, green, yellow, blue, magenta, cyan, white, then the
bright eight. Every ANSI colour reaches 3:1 on the terminal background except
the grey on the background's side (D7): black in dark mode and white in light
mode are fills close to the background, as in the common schemes, and the
colours stay readable on them. Each bright colour is lighter than its normal
one (D8), except light mode's white pair, whose bright twin has to be darker to
stay readable on a light background.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest
from coloraide import Color

from copper_design import palette

_COLOURS = (1, 2, 3, 4, 5, 6)
"""The six colours' ANSI slots, red to cyan; each bright one is eight later."""

# (mode, ANSI slot): why it may stay below 3:1 on the terminal background.
_FILL_GREYS = {
    ("dark", 0): "black is a fill close to the background, behind the colours (a status bar's black on green)",
    ("light", 7): "white is a fill close to the background, behind the colours",
}
# (mode, normal slot): why its bright twin may be darker.
_DARKER_BRIGHT = {
    ("light", 7): "white is a fill near the light background; a bright white readable on it has to be darker",
}

_ROOT = Path(__file__).resolve().parents[1]
_HEX = re.compile(r"^#[0-9a-f]{6}$")
# The names herdr resolves into its theme, which `colors` may override (its
# src/settings.rs, `resolve`), less the ANSI slots the file sets.
_PANEL_NAMES = {
    "background",
    "terminal_foreground",
    "foreground",
    "surface",
    "canvas",
    "chrome",
    "popover",
    "raised",
    "hover",
    "selected",
    "border",
    "input",
    "muted",
    "dim",
    "accent",
    "accent_foreground",
    "solid",
    "solid_foreground",
    "ring",
    "selection",
    "cursor",
    "working",
    "blocked",
    "done",
    "idle",
    "unknown",
}


def _theme(mode: palette.Mode) -> dict[str, Any]:
    return json.loads((_ROOT / "ports" / "herdr" / f"copper-{mode}.json").read_text(encoding="utf-8"))


def _is_light(hex_colour: str) -> bool:
    red, green, blue = (int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue > 0.5


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_theme_is_in_herdrs_format(mode: palette.Mode) -> None:
    theme = _theme(mode)
    assert set(theme) == {"background", "foreground", "selection", "cursor", "ansi", "colors"}
    for key in ("background", "foreground", "selection", "cursor"):
        assert _HEX.match(theme[key]), f"{key}: {theme[key]}"
    assert len(theme["ansi"]) == 16
    assert all(_HEX.match(colour) for colour in theme["ansi"]), theme["ansi"]
    assert set(theme["colors"]) <= _PANEL_NAMES, set(theme["colors"]) - _PANEL_NAMES
    assert all(_HEX.match(colour) for colour in theme["colors"].values()), theme["colors"]


@pytest.mark.parametrize("mode", palette.MODES)
def test_herdr_takes_the_theme_for_its_mode(mode: palette.Mode) -> None:
    assert _is_light(_theme(mode)["background"]) == (mode == "light")


@pytest.mark.parametrize("mode", palette.MODES)
def test_every_ansi_colour_reaches_3_to_1_on_the_terminal_background(mode: palette.Mode) -> None:
    theme = _theme(mode)
    ratios = {index: Color(colour).contrast(theme["background"]) for index, colour in enumerate(theme["ansi"])}
    short = {f"ansi{i}": round(r, 2) for i, r in ratios.items() if r < 3 and (mode, i) not in _FILL_GREYS}
    assert not short, f"{mode}: below 3:1 on {theme['background']}: {short}"
    stale = [i for (fill_mode, i) in _FILL_GREYS if fill_mode == mode and ratios[i] >= 3]
    assert not stale, f"{mode}: these fill greys reach 3:1 now; drop their exception: {stale}"


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_colours_stay_readable_on_the_fill_grey(mode: palette.Mode) -> None:
    theme = _theme(mode)
    (fill,) = [theme["ansi"][i] for fill_mode, i in _FILL_GREYS if fill_mode == mode]
    for slot in (*_COLOURS, *(i + 8 for i in _COLOURS)):
        ratio = Color(theme["ansi"][slot]).contrast(fill)
        assert ratio >= 3, f"{mode}: ansi{slot} on the fill grey {fill}: {ratio:.2f}:1"


@pytest.mark.parametrize("mode", palette.MODES)
def test_every_bright_colour_is_lighter_than_its_normal_one(mode: palette.Mode) -> None:
    ansi = _theme(mode)["ansi"]
    darker = [
        f"ansi{i + 8} {ansi[i + 8]} vs ansi{i} {ansi[i]}"
        for i in range(8)
        if (mode, i) not in _DARKER_BRIGHT and Color(ansi[i + 8]).luminance() <= Color(ansi[i]).luminance()
    ]
    assert not darker, f"{mode}: bright not lighter: {darker}"
    stale = [
        i
        for (bright_mode, i) in _DARKER_BRIGHT
        if bright_mode == mode and Color(ansi[i + 8]).luminance() > Color(ansi[i]).luminance()
    ]
    assert not stale, f"{mode}: drop the exception for {stale}"


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_terminal_text_reaches_4_5_on_its_background_and_selection(mode: palette.Mode) -> None:
    theme = _theme(mode)
    assert Color(theme["foreground"]).contrast(theme["background"]) >= 4.5
    assert Color(theme["foreground"]).contrast(theme["selection"]) >= 4.5


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_chrome_stands_apart_from_the_terminal(mode: palette.Mode) -> None:
    theme = _theme(mode)
    assert theme["colors"]["chrome"] != theme["background"]
    assert Color(theme["colors"]["chrome"]).luminance() < Color(theme["background"]).luminance()
