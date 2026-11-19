"""The colours herdr resolves from a theme file: a port of herdr v0.1.16's ``resolve`` (``src/settings.rs``).

herdr derives its panel colours from the theme's terminal background and lets
the file's ``colors`` override any of them by name. The herdr port leaves the
panel surfaces to that derivation (issue 12, D1), so the tests and the preview
compute them here, as v0.1.16 does: ``is_light`` (Rec. 709 weights over the
8-bit channels), ``mix`` (per channel, in 32-bit floats, rounded half away
from zero) and ``resolve`` (the light and dark branches, then the overrides).
A herdr release that changes them changes this file with the pin.
"""

import math
import struct
from collections.abc import Mapping
from typing import Any

HERDR = "0.1.16"
"""The herdr version whose ``resolve`` this file ports."""

SURFACES = ("surface", "canvas", "chrome", "popover", "raised")
"""The opaque panel surfaces herdr derives; its panel text (``foreground``, ``muted``, ``dim``) sits on them."""


def _f32(value: float) -> float:
    return struct.unpack("f", struct.pack("f", value))[0]


def _channels(hex_colour: str) -> tuple[int, int, int]:
    return int(hex_colour[1:3], 16), int(hex_colour[3:5], 16), int(hex_colour[5:7], 16)


def is_light(hex_colour: str) -> bool:
    """Whether herdr takes a background as light: Rec. 709 luminance of the 8-bit channels above one half."""
    red, green, blue = (
        _f32(_f32(weight) * _f32(channel / 255))
        for weight, channel in zip((0.2126, 0.7152, 0.0722), _channels(hex_colour), strict=True)
    )
    return _f32(_f32(red + green) + blue) > 0.5


def mix(a: str, b: str, t: float) -> str:
    """``a`` moved a fraction ``t`` toward ``b``, channel by channel, as herdr's ``mix`` computes it."""
    weight = _f32(t)
    rest = _f32(1 - weight)

    def channel(x: int, y: int) -> int:
        value = _f32(_f32(x * rest) + _f32(y * weight))
        return math.floor(value + 0.5)  # Rust's f32::round: half away from zero (the values are not negative)

    return "#" + "".join(f"{channel(x, y):02x}" for x, y in zip(_channels(a), _channels(b), strict=True))


def resolve(theme: Mapping[str, Any]) -> dict[str, str]:
    """Every named colour herdr resolves from a theme file (its ANSI slots left out), the file's ``colors`` applied."""
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
    resolved = {
        "background": bg,
        "terminal_foreground": theme["foreground"],
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
        "selection": theme["selection"],
        "cursor": theme.get("cursor", theme["foreground"]),
        "working": ansi[3],
        "blocked": ansi[1],
        "done": ansi[4],
        "idle": mix(bg, fg, 0.38),
        "unknown": mix(bg, fg, 0.38),
    }
    return resolved | dict(theme.get("colors", {}))
