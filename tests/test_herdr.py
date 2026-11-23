"""The herdr port: copper-light.json and copper-dark.json in herdr's theme format.

herdr 0.1.17 reads ``themes/<name>.json``: ``background``, ``foreground``,
``selection`` and an optional ``cursor`` as ``#rrggbb``, ``ansi`` as 16 of them,
and an optional ``colors`` that overrides its panel colours by name with
``#rrggbb`` or ``#rrggbbaa``. It takes a theme as light by the background's
luminance (copper_design.herdr's ``is_light``). This docstring is the one
description of the theme file's format here, and of why the port's colours
are as they are; the template points to it, and copper_design.herdr holds the
``colors`` mapping and ports how herdr resolves a theme.

The port: the terminal is a pane on the canvas. ANSI order: black, red, green,
yellow, blue, magenta (violet), cyan (teal), white, then the bright eight.

The panel levels (issue 15, D1, D2 and D5) are copper steps the port picks per
mode (copper_design.herdr's ``COLORS``), not copper's roles, and follow herdr's
own build, where the sidebar is part of the frame: in dark mode the sidebar
(``chrome``) and ``canvas`` share neutral step 1, the terminal, ``surface`` and
popovers step 3, and ``raised`` (buttons, chips, the open sub-agent, a hunk
header) step 5; in light mode the sidebar and ``canvas`` share neutral step 3,
the terminal, ``surface`` and popovers step 1, and ``raised`` is violet step 3:
between white and neutral step 3, the last step on which ``dim`` reaches the
text need, the grey scale holds only two levels 1.12:1 apart, and the terminal,
the sidebar and ``raised`` need three. What herdr derives from the terminal
background instead leaves the sidebar and ``canvas`` 1.04 to 1.11:1 from the
terminal, and the window reads as one surface.

The selected row (``selected``) is an opaque blue tint (D3), as most interfaces
and Material's ``primaryContainer`` mark a selection: blue step 4 in dark mode,
step 3 in light mode. ``hover`` stays herdr's translucent layer, transient and
quiet. ``border`` and ``input`` (the stronger edge of an input) are ``border``
and ``border-strong``, which keep copper's hue where herdr's are white or black
at low alpha.

Which levels herdr 0.1.17 draws on or beside each other is read from its source
(its layouts, its frame and mods, its window's fills). The pairs it sets apart
by a border are listed, not measured: the pane in its frame and the sidebar
column on ``canvas``, popovers and menus over the app, key caps on a selected
row; the sidebar and ``canvas`` share a step, and so do the terminal and a
popover. The pairs it draws edge to edge, the selected row and ``raised`` each
on the sidebar, on the terminal and on a popover, stand at least 1.12:1 apart
by luminance, what two neutral steps reach at the dark end, or, where one side
is a tint, 3 apart in OKLab (times 100), about what one neutral step apart
reaches at these levels.

Beside the levels, ``colors`` sets what carries meaning (copper_design.herdr's
``COLORS``):

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
  ``dim`` is neutral step 10, a step above ``text-subtle``, which falls short
  of the text need (copper_design.contrast) on the dark popovers and cards
  (step 5). Each reaches it on every panel level, the selected row included
  (copper_design.herdr's ``checks``); light neutral step 10 is set so that
  ``text-subtle`` reaches it on the light step-3 levels (issue 15, D5,
  parameters.toml). The text on a solid button, ``solid_foreground``, stays
  herdr's (white in light mode, the background darkened in dark mode) and
  reaches it on ``text``.

``colors`` also carries colours for herdr's mods (issue 15, D4), under keys
prefixed ``copper-`` so that none collides with a name a later herdr resolves
(copper_design.herdr's ``for_mods``): each base colour's main value
(``copper-blue``) and its steps 3 and 4, the tinted backgrounds, and 6 and 7,
the borders (``copper-blue-3``), the neutral's included, so that a mod draws a
grey badge or chip as it draws a coloured one; then the roles that reach herdr
no other way, ``bg``, ``bg-alt``, ``surface-raised``, ``border``,
``border-strong`` and ``info`` (``copper-bg``). herdr 0.1.17 hands every key of
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
# What the theme leaves to herdr; the docstring says why.
_LEFT_TO_HERDR = {"hover", "ring", "solid_foreground"}

# The copper colour of each panel level herdr reads, and of the terminal (the
# file's ``background``): neutral steps, light ``raised`` a violet tint and the
# selected row a blue tint (issue 15, D2, D3 and D5).
_LEVELS = {
    "dark": {
        "background": "neutral-3",
        "surface": "neutral-3",
        "chrome": "neutral-1",
        "canvas": "neutral-1",
        "raised": "neutral-5",
        "popover": "neutral-3",
        "selected": "blue-4",
    },
    "light": {
        "background": "neutral-1",
        "surface": "neutral-1",
        "chrome": "neutral-3",
        "canvas": "neutral-3",
        "raised": "violet-3",
        "popover": "neutral-1",
        "selected": "blue-3",
    },
}

# The pairs herdr 0.1.17 draws edge to edge, without a border, each with where
# it draws one (issue 15, D2): the selected row and ``raised`` on the sidebar,
# on the terminal and on popovers. Each stands at least 1.12:1 apart by
# luminance, or, where one side is a tint (no neutral step), _HUE_DISTANCE apart
# in OKLab.
_EDGE_TO_EDGE = {
    ("selected", "chrome"): "defaults/mods/tabs/main.js:137, a panel button in the tab row (:144)",
    ("selected", "background"): "defaults/mods/changes/main.js:218, the open file in the changes panel (:206)",
    ("selected", "popover"): "defaults/mods/menu/main.js:152, a menu's current item (:129)",
    ("raised", "chrome"): "defaults/mods/agents/main.js:200, the open sub-agent in the agent list (:425)",
    ("raised", "background"): "defaults/mods/changes/main.js:196, a hunk header in the changes panel (:206)",
    ("raised", "popover"): "defaults/mods/confirm/main.js:49, a confirmation's Cancel button (:40)",
}
# The pairs herdr 0.1.17 sets apart by a border, so not held to a distance.
_OVERLAY = "src/window.rs:4881, an overlay drawn with a border and a shadow"
_BORDERED = {
    (
        "chrome",
        "canvas",
    ): "defaults/layouts/main.json:14-17 and :27, the sidebar column beside a border-coloured divider",
    ("background", "canvas"): "defaults/layouts/main.json:111-119, the pane in a frame with a border",
    ("popover", "chrome"): _OVERLAY,
    ("popover", "background"): _OVERLAY,
    ("popover", "canvas"): _OVERLAY,
    ("raised", "selected"): "defaults/frame/palette/main.js:239, a key cap with a border on a selected row (:266)",
}
_HUE_DISTANCE = 3.0
"""The OKLab distance (times 100) a pair with a tint keeps (issue 15, D2): about what one neutral step apart reaches
at the levels used (1.7 to 3.2), so a tint stands apart from its neighbour at least as far as the next neutral step
would."""


def _oklab_distance(a: str, b: str) -> float:
    """The Euclidean distance of two colours in OKLab, times 100."""
    return Color(a).delta_e(b, method="ok") * 100


# What herdr v0.1.17 derives from these backgrounds, worked out by hand from its
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
    # herdr 0.1.17 inserts every key of the file's ``colors`` into the theme it
    # hands to mods, a name it resolves or not (src/settings.rs:360,
    # ``for (k, v) in overrides { t.insert(k.clone(), v.clone()) }``).
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
def test_the_theme_leaves_hover_ring_and_the_text_on_a_solid_button_to_herdr(mode: palette.Mode) -> None:
    assert not set(_theme(mode)["colors"]) & _LEFT_TO_HERDR, set(_theme(mode)["colors"]) & _LEFT_TO_HERDR


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_panel_levels_take_their_copper_colours(mode: palette.Mode) -> None:
    c = tokens.colours(mode)
    resolved = herdr.resolve(_theme(mode))
    assert {key: resolved[key] for key in _LEVELS[mode]} == {key: c[name] for key, name in _LEVELS[mode].items()}


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_borders_take_coppers_border_roles(mode: palette.Mode) -> None:
    c = tokens.colours(mode)
    colors = _theme(mode)["colors"]
    assert (colors["border"], colors["input"]) == (c["border"], c["border-strong"])


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_levels_herdr_draws_edge_to_edge_stand_apart(mode: palette.Mode) -> None:
    resolved = herdr.resolve(_theme(mode))

    def tint(level: str) -> bool:
        return not _LEVELS[mode][level].startswith(f"{palette.NEUTRAL}-")

    close = {}
    for a, b in _EDGE_TO_EDGE:
        if tint(a) or tint(b):
            measure, need = _oklab_distance(resolved[a], resolved[b]), _HUE_DISTANCE
        else:
            measure, need = contrast.ratio(resolved[a], resolved[b]), 1.12
        if measure < need:
            close[f"{a} {resolved[a]} | {b} {resolved[b]}"] = f"{measure:.3f} < {need}"
    assert not close, f"{mode}: too close: {close}"


def test_the_bordered_pairs_are_listed_apart_from_the_measured_ones() -> None:
    levels = set(_LEVELS["dark"])
    assert not set(_BORDERED) & set(_EDGE_TO_EDGE), set(_BORDERED) & set(_EDGE_TO_EDGE)
    assert {level for pair in (*_BORDERED, *_EDGE_TO_EDGE) for level in pair} <= levels


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
def test_the_panel_text_and_a_solid_buttons_reach_the_text_need_on_every_level(mode: palette.Mode) -> None:
    resolved = herdr.resolve(_theme(mode))
    checks = herdr.checks(resolved)
    assert {(check.foreground, check.background) for check in checks} == {
        *(
            (text, surface)
            for text in ("foreground", "muted", "dim")
            for surface in ("surface", "canvas", "chrome", "popover", "raised", "selected")
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
