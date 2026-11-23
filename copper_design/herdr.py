"""The herdr port's ``colors`` mapping, and the colours herdr resolves from a theme file.

``COLORS`` is the ``colors`` mapping as data: the names herdr resolves that
the theme's ``colors`` sets, each with its copper source per mode, and
``for_mods`` the keys it carries for herdr's mods beside them, each base
colour's text colour at ``MOD_TEXT_STEP`` or the step ``MOD_TEXT_STEPS``
names; the template renders both, and the terminal's background from
``terminal``.
tests/test_herdr.py's docstring says why the table reads as it does.

herdr derives the colours the theme file leaves out (``hover``, ``ring``,
``solid_foreground``) from its terminal background, so the tests and the
preview compute them here: ``is_light``, ``mix`` and ``resolve`` port herdr
v0.1.17's functions of those names in ``src/settings.rs``, and ``checks``
measures each pair of ``PAIRS``, or of ``mod_pairs``, on what ``resolve``
returns. A herdr release that changes them changes this file with the pin.
"""

import math
import struct
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from copper_design import contrast, tokens
from copper_design.palette import Mode

HERDR = "0.1.17"
"""The herdr version whose ``resolve`` this file ports."""


def _colors(
    *, surface: str, canvas: str, chrome: str, popover: str, raised: str, selected: str, dim: str
) -> tuple[tuple[str, str], ...]:
    return (
        ("surface", surface),
        ("canvas", canvas),
        ("chrome", chrome),
        ("popover", popover),
        ("raised", raised),
        ("selected", selected),
        ("border", "border"),
        ("input", "border-strong"),
        ("foreground", "text"),
        ("muted", "text-muted"),
        ("dim", dim),
        ("solid", "text"),
        ("accent", "accent"),
        ("accent_foreground", "on-accent"),
        ("working", "warning"),
        ("blocked", "error"),
        ("done", "success"),
        ("idle", dim),
        ("unknown", dim),
    )


COLORS: dict[Mode, tuple[tuple[str, str], ...]] = {
    "light": _colors(
        surface="neutral-1",
        canvas="neutral-3",
        chrome="neutral-3",
        popover="neutral-1",
        raised="violet-3",
        selected="blue-3",
        dim="text-subtle",
    ),
    "dark": _colors(
        surface="neutral-3",
        canvas="neutral-1",
        chrome="neutral-1",
        popover="neutral-3",
        raised="neutral-5",
        selected="blue-4",
        dim="neutral-10",
    ),
}
"""Per mode, the names herdr resolves that the theme's ``colors`` sets, in the file's order, each with its copper
source: the panel levels (``surface``, ``canvas``, ``chrome``, ``popover``, ``raised``) as neutral steps, light
``raised`` a violet tint, and the selected row a blue tint, then the borders, the text, the accent and the agent
states."""

MOD_PREFIX = "copper-"
"""The prefix of the keys the theme's ``colors`` carries for herdr's mods, beside the names herdr resolves; none of
herdr's names starts with it."""

MOD_STEPS = (3, 4, 6, 7)
"""The steps of each base colour carried for mods: the tinted backgrounds (3, 4) and the borders (6, 7)."""

MOD_TEXT = "text"
"""The suffix of each base colour's text colour for mods (``copper-blue-text``)."""

MOD_TEXT_STEP = 11
"""The step a base colour's text colour for mods takes (issue 18, D1): low-contrast text (GLOSSARY, Step), for a
label or chip coloured by hue, since step 11 carries more of the hue than high-contrast text (12). This is herdr's own
pick: the Android port puts step 12 on its containers, as Material's on-container text (copper_design.material)."""

MOD_TEXT_STEPS: dict[Mode, dict[str, int]] = {"light": {"yellow": 12, "orange": 12}, "dark": {}}
"""Per mode, the base colours whose text colour for mods takes another step than MOD_TEXT_STEP, with that step:
high-contrast text (12) where step 11 falls short of the text need on the colour's steps 3 and 4 or on the
terminal's background (``mod_pairs``); tests/test_herdr.py holds each entry to that."""


def mod_text_step(mode: Mode, base: str) -> int:
    """The step of ``base`` its text colour for mods takes in ``mode``: MOD_TEXT_STEPS's, else MOD_TEXT_STEP."""
    return MOD_TEXT_STEPS[mode].get(base, MOD_TEXT_STEP)


MOD_ROLES = ("bg", "bg-alt", "surface-raised", "border", "border-strong", "info")
"""The roles carried for mods, for them to name by role."""


def for_mods(mode_tokens: tokens.ModeTokens) -> tuple[tuple[str, str], ...]:
    """The keys the theme's ``colors`` carries for mods, each with its copper source: per base colour its main value,
    MOD_STEPS and its text colour (``mod_text_step``), then MOD_ROLES."""
    return (
        *(
            (f"{MOD_PREFIX}{name}", source)
            for base in mode_tokens.bases
            for name, source in (
                (base, base),
                *((f"{base}-{step}", f"{base}-{step}") for step in MOD_STEPS),
                (f"{base}-{MOD_TEXT}", f"{base}-{mod_text_step(mode_tokens.mode, base)}"),
            )
        ),
        *((f"{MOD_PREFIX}{role}", role) for role in MOD_ROLES),
    )


NAMES = (
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
)
"""Every colour name herdr resolves into its theme, less the ANSI slots, in ``resolve``'s order (a test holds the
two equal); ``colors`` may override any of them."""

FROM_FILE = {
    "background": "background",
    "terminal_foreground": "foreground",
    "selection": "selection",
    "cursor": "cursor",
}
"""The names herdr takes from the theme file outside ``colors``, each with its key in the file."""

LEVELS = ("surface", "canvas", "chrome", "popover", "raised", "selected")
"""The opaque panel levels, the selected row's included."""

PANEL_TEXT = ("foreground", "muted", "dim")
"""The panels' text, drawn on every panel level."""

PAIRS = (*((text, level) for level in LEVELS for text in PANEL_TEXT), ("solid_foreground", "solid"))
"""The text measured against what it sits on, by level: the panel text on each level, then a solid button's."""


def mod_pairs(bases: Sequence[str]) -> tuple[tuple[str, str], ...]:
    """The text colours for mods measured against what they sit on: each on its base colour's steps 3 and 4 (the
    tinted backgrounds), then each on the terminal's background."""
    return (
        *((f"{MOD_PREFIX}{base}-{MOD_TEXT}", f"{MOD_PREFIX}{base}-{step}") for base in bases for step in (3, 4)),
        *((f"{MOD_PREFIX}{base}-{MOD_TEXT}", "background") for base in bases),
    )


def terminal(mode: Mode) -> str:
    """The copper source of the terminal's background, the theme file's ``background``: ``surface``'s, since herdr
    sets ``surface`` to the terminal's background (its src/settings.rs, ``resolve``)."""
    return dict(COLORS[mode])["surface"]


def template_context(mode_tokens: tokens.ModeTokens) -> dict[str, Any]:
    """What the herdr template gets beside the mode's context: the terminal's colour and the ``colors`` mapping of
    that mode, COLORS and then the colours for mods."""
    mode = mode_tokens.mode
    return {"herdr_terminal": terminal(mode), "herdr_colors": (*COLORS[mode], *for_mods(mode_tokens))}


def set_by_theme(theme: Mapping[str, Any]) -> set[str]:
    """The names a theme file sets, outside ``colors`` and in it; herdr derives the rest."""
    return {*FROM_FILE, *theme.get("colors", {})}


def checks(resolved: Mapping[str, str], pairs: Iterable[tuple[str, str]] = PAIRS) -> list[contrast.Check]:
    """Each pair's contrast in a resolved theme, PAIRS or ``mod_pairs``, in their order, with the text need."""
    return [
        contrast.Check(text, ground, contrast.NEEDS["text"], contrast.ratio(resolved[text], resolved[ground]))
        for text, ground in pairs
    ]


def _f32(value: float) -> float:
    return struct.unpack("f", struct.pack("f", value))[0]


def _channels(hex_colour: str) -> tuple[int, int, int]:
    return int(hex_colour[1:3], 16), int(hex_colour[3:5], 16), int(hex_colour[5:7], 16)


def is_light(hex_colour: str) -> bool:
    """Whether herdr takes a background as light: the Rec. 709 luminance of its 8-bit channels, in 32-bit floats,
    above one half."""
    red, green, blue = (
        _f32(_f32(weight) * _f32(channel / 255))
        for weight, channel in zip((0.2126, 0.7152, 0.0722), _channels(hex_colour), strict=True)
    )
    return _f32(_f32(red + green) + blue) > 0.5


def mix(a: str, b: str, t: float) -> str:
    """``a`` moved a fraction ``t`` toward ``b``, channel by channel in 32-bit floats, rounded half away from zero."""
    weight = _f32(t)
    rest = _f32(1 - weight)

    def channel(x: int, y: int) -> int:
        value = _f32(_f32(x * rest) + _f32(y * weight))
        return math.floor(value + 0.5)  # Rust's f32::round: half away from zero (the values are not negative)

    return "#" + "".join(f"{channel(x, y):02x}" for x, y in zip(_channels(a), _channels(b), strict=True))


def resolve(theme: Mapping[str, Any]) -> dict[str, str]:
    """Every colour herdr resolves from a theme file, NAMES in order, then the file's ``colors`` applied over them:
    a name of NAMES replaced, any other key added after them in the file's order."""
    bg = theme["background"]
    ansi = theme["ansi"]
    light = is_light(bg)
    fg = "#1b1b1e" if light else "#eeeeef"
    if light:
        warm = "#e8e8e2"
        popover, raised = bg, mix(bg, "#000000", 0.035)
        hover, selected, border, edge = "#0000000c", "#00000012", "#00000017", "#00000026"
        canvas, chrome = mix(bg, warm, 0.2), mix(bg, warm, 0.6)
    else:
        popover, raised = mix(bg, "#ffffff", 0.06), mix(bg, "#ffffff", 0.09)
        hover, selected, border, edge = "#ffffff0e", "#ffffff17", "#ffffff18", "#ffffff24"
        canvas, chrome = mix(bg, "#000000", 0.16), mix(bg, "#000000", 0.32)
    derived = {
        "background": theme[FROM_FILE["background"]],
        "terminal_foreground": theme[FROM_FILE["terminal_foreground"]],
        "foreground": fg,
        "surface": bg,
        "canvas": canvas,
        "chrome": chrome,
        "popover": popover,
        "raised": raised,
        "hover": hover,
        "selected": selected,
        "border": border,
        "input": edge,
        "muted": mix(bg, fg, 0.66 if light else 0.6),
        "dim": mix(bg, fg, 0.46 if light else 0.38),
        "accent": ansi[4],
        "accent_foreground": bg,
        "solid": fg,
        "solid_foreground": "#ffffff" if light else mix(bg, "#000000", 0.28),
        "ring": mix(bg, fg, 0.7),
        "selection": theme[FROM_FILE["selection"]],
        "cursor": theme.get(FROM_FILE["cursor"], theme[FROM_FILE["terminal_foreground"]]),
        "working": ansi[3],
        "blocked": ansi[1],
        "done": ansi[4],
        "idle": mix(bg, fg, 0.38),
        "unknown": mix(bg, fg, 0.38),
    }
    return derived | dict(theme.get("colors", {}))
