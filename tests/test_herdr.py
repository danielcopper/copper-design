"""The herdr port: copper-light.json and copper-dark.json in herdr's theme format.

herdr 0.1.16 reads ``themes/<name>.json``: ``background``, ``foreground``,
``selection`` and an optional ``cursor`` as ``#rrggbb``, ``ansi`` as 16 of them,
and an optional ``colors`` that overrides its panel colours by name with
``#rrggbb`` or ``#rrggbbaa``. It takes a theme as light when the background's
luminance (Rec. 709 weights over the 8-bit channels) is above one half.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest
from coloraide import Color

from copper_design import palette

_ROOT = Path(__file__).resolve().parents[1]
_HEX = re.compile(r"^#[0-9a-f]{6}$")
# The names herdr resolves into its theme, which `colors` may override (herdr
# 0.1.16, src/settings.rs, `resolve`), less the ANSI slots the file sets.
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


def _theme(mode: str) -> dict[str, Any]:
    return json.loads((_ROOT / "ports" / "herdr" / f"copper-{mode}.json").read_text(encoding="utf-8"))


def _is_light(hex_colour: str) -> bool:
    red, green, blue = (int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue > 0.5


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_theme_is_in_herdrs_format(mode: str) -> None:
    theme = _theme(mode)
    assert set(theme) == {"background", "foreground", "selection", "cursor", "ansi", "colors"}
    for key in ("background", "foreground", "selection", "cursor"):
        assert _HEX.match(theme[key]), f"{key}: {theme[key]}"
    assert len(theme["ansi"]) == 16
    assert all(_HEX.match(colour) for colour in theme["ansi"]), theme["ansi"]
    assert set(theme["colors"]) <= _PANEL_NAMES, set(theme["colors"]) - _PANEL_NAMES
    assert all(_HEX.match(colour) for colour in theme["colors"].values()), theme["colors"]


@pytest.mark.parametrize("mode", palette.MODES)
def test_herdr_takes_the_theme_for_its_mode(mode: str) -> None:
    assert _is_light(_theme(mode)["background"]) == (mode == "light")


@pytest.mark.parametrize("mode", palette.MODES)
def test_every_ansi_colour_reaches_3_to_1_on_the_terminal_background(mode: str) -> None:
    theme = _theme(mode)
    short = {
        f"ansi{index}": round(ratio, 2)
        for index, colour in enumerate(theme["ansi"])
        if (ratio := Color(colour).contrast(theme["background"])) < 3
    }
    assert not short, f"{mode}: below 3:1 on {theme['background']}: {short}"


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_terminal_text_reaches_4_5_on_its_background_and_selection(mode: str) -> None:
    theme = _theme(mode)
    assert Color(theme["foreground"]).contrast(theme["background"]) >= 4.5
    assert Color(theme["foreground"]).contrast(theme["selection"]) >= 4.5
