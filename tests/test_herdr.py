"""The herdr port: copper-light.json and copper-dark.json in herdr's theme format.

herdr 0.1.16 reads ``themes/<name>.json``: ``background``, ``foreground``,
``selection`` and an optional ``cursor`` as ``#rrggbb``, ``ansi`` as 16 of them,
and an optional ``colors`` that overrides its panel colours by name with
``#rrggbb`` or ``#rrggbbaa``. It takes a theme as light when the background's
luminance (Rec. 709 weights over the 8-bit channels) is above one half. This
docstring is the one description of that format here; the template points to it.

The port: the terminal is a surface (a pane on the canvas), so its background
is the ``surface`` role. ANSI order: black, red, green, yellow, blue, magenta
(violet), cyan (teal), white, then the bright eight.

herdr derives its panel colours from the terminal background
(copper_design.herdr ports how): the chrome (sidebars, bars) and the canvas
(behind cards) step away from it, darker in dark mode and toward a warm grey in
light mode, popovers and raised surfaces lighter in dark mode, and hover,
selection, borders and inputs are translucent. ``colors`` leaves those to herdr,
as herdr's own themes do (issue 12, D1), and sets only what carries meaning:

- the accent and the text on it: ``accent`` and ``accent_foreground`` are
  ``accent`` and ``on-accent``. ``ring`` stays herdr's: a neutral grey, not the
  accent, that herdr draws as the hover edge of a choice the accent does not
  mark and hands to mods as their ``ring``.
- the agent states: ``working``, ``blocked`` and ``done`` are ``warning``,
  ``error`` and ``success``; ``idle`` and ``unknown`` are ``text-subtle``, as
  ``dim``, since herdr derives them as its own dim grey.
- the panels' text (issue 12, D2), so it matches the terminal's: ``foreground`` and
  ``solid`` (a solid button's fill) are ``text``, ``muted`` is ``text-muted``,
  ``dim`` is ``text-subtle``. Each reaches 4.5:1, its kind's need
  (copper_design.contrast), on every opaque surface herdr derives, except the
  pairs ``_SHORT_ON_A_SURFACE`` names, still open; the text on a solid button, ``solid_foreground``, stays
  herdr's (white in light mode, the background darkened in dark mode) and
  reaches 4.5:1 on ``text``.

The ANSI colours:

- Every ANSI colour reaches 3:1 on the terminal background, except the grey on
  the background's side (issue 5, D7): black in dark mode and white in light
  mode are fills close to the background, as in the common schemes, and the
  colours stay readable on them.
- Each bright colour is lighter than its normal one (D8). Dark mode takes the
  solid steps (9) and, for the bright colours, the text steps (11); yellow and
  teal lift their solid steps above step 11, so their bright colours take the
  lifted step 10. Light mode takes the text steps (11) and, for the bright
  colours, the hovered solid steps (10); yellow's solid steps are too light for
  3:1, so yellow takes its text steps (12, then 11), and blue's step 10 is
  darker than its step 11, so bright blue takes step 9.
- The greys: in dark mode black is the fill (neutral 6), bright black neutral 9,
  white and bright white neutral 11 and 12; light mode mirrors it, with black and
  bright black neutral 12 and 11, white the fill (neutral 3) and bright white
  neutral 9.
- One pair is the named exception to D8: in light mode bright white is a grey
  readable on the background (3:1), darker than the white fill, since programs
  use bright white as text.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest
from coloraide import Color

from copper_design import herdr, palette

_COLOURS = (1, 2, 3, 4, 5, 6)
"""The six colours' ANSI slots, red to cyan; each bright one is eight later."""

# (mode, ANSI slot): why it may stay below 3:1 on the terminal background.
_FILL_GREYS = {
    ("dark", 0): "black is a fill close to the background, behind the colours (a status bar's black on green)",
    ("light", 7): "white is a fill close to the background, behind the colours",
}
# (mode, normal slot): why its bright twin may be darker.
_DARKER_BRIGHT = {
    ("light", 7): "bright white is a grey readable on the background (3:1), darker than the white fill",
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


# The panel colours the theme leaves to herdr's own derivation from the
# terminal background (issue 12, D1), with the two it derives that go with
# them: ``ring``, a neutral edge, and ``solid_foreground``, the text on a solid
# button.
_LEFT_TO_HERDR = {
    "surface",
    "canvas",
    "chrome",
    "popover",
    "raised",
    "hover",
    "selected",
    "border",
    "input",
    "ring",
    "solid_foreground",
}


_PANEL_TEXT = ("foreground", "muted", "dim")
"""The panels' text keys the theme sets; herdr draws them on its derived surfaces."""

_OPEN = "open (issue 12): whether the panels' dim text takes a stronger step than text-subtle"
# (mode, text key, derived surface): why it may stay below 4.5:1.
_SHORT_ON_A_SURFACE = {
    ("light", "dim", "chrome"): f"{_OPEN}; herdr mixes the light chrome 60% toward a warm grey",
    ("dark", "dim", "popover"): f"{_OPEN}; herdr lifts the dark popover 6% toward white",
    ("dark", "dim", "raised"): f"{_OPEN}; herdr lifts the dark raised surface 9% toward white",
}


def _theme(mode: palette.Mode) -> dict[str, Any]:
    return json.loads((_ROOT / "ports" / "herdr" / f"copper-{mode}.json").read_text(encoding="utf-8"))


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


def test_the_port_of_herdrs_mix_rounds_as_herdr_does() -> None:
    # Per channel: 25, 23 and 36 times 0.68 are 17, 15.64 and 24.48.
    assert herdr.mix("#191724", "#000000", 0.32) == "#111018"
    # Half rounds away from zero, as Rust's f32::round does.
    assert herdr.mix("#010101", "#000000", 0.5) == "#010101"


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_theme_sets_no_panel_surface_colour(mode: palette.Mode) -> None:
    assert not set(_theme(mode)["colors"]) & _LEFT_TO_HERDR, set(_theme(mode)["colors"]) & _LEFT_TO_HERDR


@pytest.mark.parametrize("mode", palette.MODES)
def test_herdr_takes_the_theme_for_its_mode(mode: palette.Mode) -> None:
    assert herdr.is_light(_theme(mode)["background"]) == (mode == "light")


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
def test_the_chrome_and_the_canvas_herdr_derives_stand_apart_from_the_terminal(mode: palette.Mode) -> None:
    resolved = herdr.resolve(_theme(mode))
    chrome, canvas, terminal = (Color(resolved[key]).luminance() for key in ("chrome", "canvas", "background"))
    assert chrome < canvas < terminal, {key: resolved[key] for key in ("chrome", "canvas", "background")}


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_panel_text_reaches_4_5_on_every_surface_herdr_derives(mode: palette.Mode) -> None:
    resolved = herdr.resolve(_theme(mode))
    ratios = {
        (key, surface): Color(resolved[key]).contrast(resolved[surface])
        for key in _PANEL_TEXT
        for surface in herdr.SURFACES
    }
    short = {
        f"{key} {resolved[key]} on {surface} {resolved[surface]}": round(ratio, 2)
        for (key, surface), ratio in ratios.items()
        if ratio < 4.5 and (mode, key, surface) not in _SHORT_ON_A_SURFACE
    }
    assert not short, f"{mode}: below 4.5:1: {short}"
    stale = [
        (key, surface)
        for (short_mode, key, surface) in _SHORT_ON_A_SURFACE
        if short_mode == mode and ratios[key, surface] >= 4.5
    ]
    assert not stale, f"{mode}: these reach 4.5:1 now; drop their exception: {stale}"


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_text_on_a_solid_button_reaches_4_5(mode: palette.Mode) -> None:
    resolved = herdr.resolve(_theme(mode))
    assert Color(resolved["solid_foreground"]).contrast(resolved["solid"]) >= 4.5


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_fill_grey_stands_apart_from_the_background(mode: palette.Mode) -> None:
    # Close to the background, but a fill: equal to it, it would draw nothing.
    theme = _theme(mode)
    (fill,) = [theme["ansi"][i] for fill_mode, i in _FILL_GREYS if fill_mode == mode]
    assert Color(fill).contrast(theme["background"]) >= 1.1
