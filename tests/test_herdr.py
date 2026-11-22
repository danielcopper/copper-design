"""The herdr port: copper-light.json and copper-dark.json in herdr's theme format.

herdr 0.1.16 reads ``themes/<name>.json``: ``background``, ``foreground``,
``selection`` and an optional ``cursor`` as ``#rrggbb``, ``ansi`` as 16 of them,
and an optional ``colors`` that overrides its panel colours by name with
``#rrggbb`` or ``#rrggbbaa``. It takes a theme as light by the background's
luminance (copper_design.herdr's ``is_light``). This docstring is the one
description of the theme file's format here, and of why the port's colours
are as they are; the template points to it, and copper_design.herdr holds the
``colors`` mapping and ports how herdr resolves a theme.

The port: the terminal is a surface (a pane on the canvas), so its background
is the ``surface`` role. ANSI order: black, red, green, yellow, blue, magenta
(violet), cyan (teal), white, then the bright eight.

herdr derives its panel colours from the terminal background
(copper_design.herdr ports how): the chrome (sidebars, bars) and the canvas
(behind cards) step away from it, darker in dark mode and toward a warm grey in
light mode, popovers and raised surfaces lighter in dark mode, and hover, the
selected row (``selected``), borders and inputs are translucent. ``colors``
leaves those to herdr, as herdr's presets do (issue 12, D1), and sets only what
carries meaning (copper_design.herdr's ``COLORS``):

- the accent and the text on it: ``accent`` and ``accent_foreground`` are
  ``accent`` and ``on-accent``. ``ring`` stays herdr's: a neutral grey, not the
  accent, that herdr draws as the hover edge of a choice the accent does not
  mark and hands to mods as their ``ring``.
- the agent states: ``working``, ``blocked`` and ``done`` are ``warning``,
  ``error`` and ``success``; ``idle`` and ``unknown`` take ``dim``'s colour,
  since herdr derives them, like ``dim``, as a grey between its background and
  its text (in dark mode the same grey as ``dim``).
- the panels' text (issue 12, D2 and D3), so it matches the terminal's:
  ``foreground`` and ``solid`` (a solid button's fill) are ``text``, ``muted``
  is ``text-muted``, ``dim`` is ``text-subtle`` in light mode. In dark mode
  ``dim`` is neutral step 10, a step above ``text-subtle``: herdr lifts its dark
  popover and raised surfaces toward white, and ``text-subtle`` falls short of
  the text need (copper_design.contrast) on them. Each reaches it on every
  opaque surface herdr derives (copper_design.herdr's ``checks``); light
  neutral step 10 is set so that ``text-subtle`` reaches it on herdr's light
  chrome (parameters.toml). The text on a solid button, ``solid_foreground``,
  stays herdr's (white in light mode, the background darkened in dark mode) and
  reaches it on ``text``.

``colors`` also carries colours for herdr's mods (issue 15, D4), under keys
prefixed ``copper-`` so that none collides with a name a later herdr resolves
(copper_design.herdr's ``for_mods``): each base colour's main value
(``copper-blue``) and its steps 3 and 4, the tinted backgrounds, and 6 and 7,
the borders (``copper-blue-3``), the neutral's included, so that a mod draws a
grey badge or chip as it draws a coloured one; then the roles that reach herdr
no other way, ``bg``, ``bg-alt``, ``surface-raised``, ``border``,
``border-strong`` and ``info`` (``copper-bg``). herdr 0.1.16 hands every key of
``colors`` to its mods, a name it resolves or not, though its documentation
names only its own; the port of ``resolve`` does the same, so a herdr release
that changes it shows when the pin moves.

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

from copper_design import contrast, herdr, palette, tokens

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

# What herdr v0.1.16 derives from these backgrounds, worked out by hand from its
# src/settings.rs: in dark mode canvas, chrome and solid_foreground are the
# background 16%, 32% and 28% toward black, popover and raised 6% and 9% toward
# white; in light mode canvas and chrome are 20% and 60% toward #e8e8e2, raised
# 3.5% toward black, popover the background and solid_foreground white.
_DERIVED_BY_HAND = {
    "#fffaf3": {
        "surface": "#fffaf3",
        "canvas": "#faf6f0",
        "chrome": "#f1efe9",
        "popover": "#fffaf3",
        "raised": "#f6f1ea",
        "solid_foreground": "#ffffff",
    },
    "#191724": {
        "surface": "#191724",
        "canvas": "#15131e",
        "chrome": "#111018",
        "popover": "#272531",
        "raised": "#2e2c38",
        "solid_foreground": "#12111a",
    },
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
    unknown = {key for key in theme["colors"] if key not in herdr.NAMES and not key.startswith("copper-")}
    assert not unknown, f"{mode}: neither a name herdr resolves nor a colour for mods: {unknown}"
    assert all(_HEX.match(colour) for colour in theme["colors"].values()), theme["colors"]


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_theme_carries_coppers_colours_for_mods(mode: palette.Mode) -> None:
    loaded = tokens.load(mode)
    c = loaded.colours
    expected = {
        **{
            f"copper-{name}{suffix}": c[f"{name}{suffix}"]
            for name in loaded.bases
            for suffix in ("", "-3", "-4", "-6", "-7")
        },
        **{f"copper-{role}": c[role] for role in ("bg", "bg-alt", "surface-raised", "border", "border-strong", "info")},
    }
    colors = _theme(mode)["colors"]
    assert {key: value for key, value in colors.items() if key.startswith("copper-")} == expected


def test_the_port_of_herdrs_resolve_passes_coppers_colours_for_mods_through() -> None:
    # herdr 0.1.16 inserts every key of the file's ``colors`` into the theme it
    # hands to mods (``for (k, v) in overrides { t.insert(k.clone(), v.clone()) }``),
    # a name it resolves or not.
    colors = {"copper-orange": "#ff8800", "copper-blue-3": "#112233", "accent": "#445566"}
    theme = {
        "background": "#191724",
        "foreground": "#808080",
        "selection": "#808080",
        "ansi": ["#808080"] * 16,
        "colors": colors,
    }
    resolved = herdr.resolve(theme)
    assert list(resolved) == [*herdr.NAMES, "copper-orange", "copper-blue-3"]
    assert {key: resolved[key] for key in colors} == colors


@pytest.mark.parametrize("mode", palette.MODES)
def test_herdr_hands_mods_every_colour_the_theme_carries_for_them(mode: palette.Mode) -> None:
    colors = _theme(mode)["colors"]
    resolved = herdr.resolve(_theme(mode))
    for_mods = {key: value for key, value in colors.items() if key.startswith("copper-")}
    assert for_mods, mode
    assert {key: resolved[key] for key in for_mods} == for_mods


def test_the_port_of_herdrs_mix_rounds_as_herdr_does() -> None:
    # Per channel: 25, 23 and 36 times 0.68 are 17, 15.64 and 24.48.
    assert herdr.mix("#191724", "#000000", 0.32) == "#111018"
    # Half rounds away from zero, as Rust's f32::round does.
    assert herdr.mix("#010101", "#000000", 0.5) == "#010101"
    # In 32-bit floats 5 * 0.94 + 30 * 0.06 is 6.5 and rounds up; in 64-bit
    # floats it is 6.4999... and would round down.
    assert herdr.mix("#050505", "#1e1e1e", 0.06) == "#070707"


@pytest.mark.parametrize(("background", "derived"), _DERIVED_BY_HAND.items())
def test_the_port_of_herdrs_resolve_derives_the_surfaces_worked_out_by_hand(
    background: str, derived: dict[str, str]
) -> None:
    theme = {"background": background, "foreground": "#808080", "selection": "#808080", "ansi": ["#808080"] * 16}
    resolved = herdr.resolve(theme)
    assert {key: resolved[key] for key in derived} == derived


def test_the_port_of_herdrs_resolve_returns_every_name_in_order() -> None:
    theme = {"background": "#191724", "foreground": "#808080", "selection": "#808080", "ansi": ["#808080"] * 16}
    assert list(herdr.resolve(theme)) == list(herdr.NAMES)


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
    assert Color(theme["foreground"]).contrast(theme["background"]) >= contrast.NEEDS["text"]
    assert Color(theme["foreground"]).contrast(theme["selection"]) >= contrast.NEEDS["text"]


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_chrome_and_the_canvas_herdr_derives_stand_apart_from_the_terminal(mode: palette.Mode) -> None:
    resolved = herdr.resolve(_theme(mode))
    chrome, canvas, terminal = (Color(resolved[key]).luminance() for key in ("chrome", "canvas", "background"))
    assert chrome < canvas < terminal, {key: resolved[key] for key in ("chrome", "canvas", "background")}


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_panel_text_takes_coppers_text_roles(mode: palette.Mode) -> None:
    c = tokens.colours(mode)
    colors = _theme(mode)["colors"]
    dim = c["text-subtle"] if mode == "light" else c["neutral-10"]
    assert [colors[key] for key in ("foreground", "solid", "muted", "dim")] == [
        c["text"],
        c["text"],
        c["text-muted"],
        dim,
    ]


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_accent_and_the_agent_states_take_coppers_roles(mode: palette.Mode) -> None:
    c = tokens.colours(mode)
    colors = _theme(mode)["colors"]
    assert {key: colors[key] for key in ("accent", "accent_foreground", "working", "blocked", "done")} == {
        "accent": c["accent"],
        "accent_foreground": c["on-accent"],
        "working": c["warning"],
        "blocked": c["error"],
        "done": c["success"],
    }


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_panel_text_and_a_solid_buttons_reach_the_text_need_on_what_herdr_derives(mode: palette.Mode) -> None:
    resolved = herdr.resolve(_theme(mode))
    checks = herdr.checks(resolved)
    assert {(check.foreground, check.background) for check in checks} == {
        *(
            (text, surface)
            for text in ("foreground", "muted", "dim")
            for surface in ("surface", "canvas", "chrome", "popover", "raised")
        ),
        ("solid_foreground", "solid"),
    }
    assert {check.need for check in checks} == {contrast.NEEDS["text"]}
    short = {
        f"{check.foreground} {resolved[check.foreground]} on {check.background} {resolved[check.background]}": round(
            check.ratio, 2
        )
        for check in checks
        if not check.passes
    }
    assert not short, f"{mode}: below the text need: {short}"


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_fill_grey_stands_apart_from_the_background(mode: palette.Mode) -> None:
    # Close to the background, but a fill: equal to it, it would draw nothing.
    theme = _theme(mode)
    (fill,) = [theme["ansi"][i] for fill_mode, i in _FILL_GREYS if fill_mode == mode]
    assert Color(fill).contrast(theme["background"]) >= 1.1


@pytest.mark.parametrize("mode", palette.MODES)
def test_idle_and_unknown_take_dims_colour(mode: palette.Mode) -> None:
    colors = _theme(mode)["colors"]
    assert colors["idle"] == colors["unknown"] == colors["dim"]
