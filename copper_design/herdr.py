"""The herdr port's mapping, and the colours herdr resolves from a theme file.

``COLORS`` is the mapping as data: the keys the theme's ``colors`` sets, each
with its copper source per mode; the template, the tests and the preview read
it alike. tests/test_herdr.py's docstring says why the table reads as it does.

herdr derives its panel colours from the theme's terminal background and lets
``colors`` override any of them by name. The port leaves the panel surfaces to
that derivation (issue 12, D1), so the tests and the preview compute them here:
``is_light``, ``mix`` and ``resolve`` port herdr v0.1.16's functions of those
names in ``src/settings.rs``, and ``checks`` measures the panel text on what
``resolve`` returns. A herdr release that changes them changes this file with
the pin.
"""

import math
import struct
from collections.abc import Mapping
from typing import Any

from copper_design import contrast
from copper_design.palette import Mode

HERDR = "0.1.16"
"""The herdr version whose ``resolve`` this file ports."""


def _colors(dim: str) -> tuple[tuple[str, str], ...]:
    return (
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


COLORS: dict[Mode, tuple[tuple[str, str], ...]] = {"light": _colors("text-subtle"), "dark": _colors("neutral-10")}
"""Per mode, the keys the theme's ``colors`` sets, in the file's order, each with its copper source."""

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

SURFACES = ("surface", "canvas", "chrome", "popover", "raised")
"""The opaque panel surfaces herdr derives."""

PANEL_TEXT = ("foreground", "muted", "dim")
"""The panels' text, drawn on every surface herdr derives."""

PAIRS = (*((text, surface) for surface in SURFACES for text in PANEL_TEXT), ("solid_foreground", "solid"))
"""The text measured against what it sits on, by surface: the panel text on each surface, then a solid button's."""


def template_context(mode: Mode) -> dict[str, Any]:
    """What the herdr template gets beside the mode's context: the ``colors`` mapping of that mode."""
    return {"herdr_colors": COLORS[mode]}


def set_by_theme(theme: Mapping[str, Any]) -> set[str]:
    """The names a theme file sets, outside ``colors`` and in it; herdr derives the rest."""
    return {*FROM_FILE, *theme.get("colors", {})}


def checks(resolved: Mapping[str, str]) -> list[contrast.Check]:
    """Each pair's contrast in a resolved theme, in PAIRS's order, with the text need."""
    return [
        contrast.Check(text, ground, contrast.NEEDS["text"], contrast.ratio(resolved[text], resolved[ground]))
        for text, ground in PAIRS
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
    """Every colour herdr resolves from a theme file, NAMES in order, then the file's ``colors`` applied over them."""
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
