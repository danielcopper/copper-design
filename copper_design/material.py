"""Material 3's colour scheme from copper's roles and named colours: the Android port's mapping.

Each role of Material 3's ``ColorScheme`` takes a copper role or a named colour,
by the job of its step (issue 10, D3). ``SCHEME`` is the one table of that
mapping: the Kotlin template, the contrast checks and the preview all read it,
through ``resolve``, which refuses a source that names no colour. A source is
written as a copper port name (``accent``, ``blue-4``) in the scheme's own mode,
or ``<mode>:<name>`` for a colour of the other mode (the inverse roles) or of
one mode for both (the fixed roles and the scrim).
"""

from collections.abc import Mapping
from typing import Any, Literal, NamedTuple, cast, get_args

from copper_design import contrast
from copper_design.palette import MODES, Mode

MATERIAL3 = "1.4.0"
"""The material3 version whose ColorScheme the Role type follows: the one Compose BOM 2026.09.00 resolves to."""

type Role = Literal[
    "primary",
    "onPrimary",
    "primaryContainer",
    "onPrimaryContainer",
    "inversePrimary",
    "secondary",
    "onSecondary",
    "secondaryContainer",
    "onSecondaryContainer",
    "tertiary",
    "onTertiary",
    "tertiaryContainer",
    "onTertiaryContainer",
    "background",
    "onBackground",
    "surface",
    "onSurface",
    "surfaceVariant",
    "onSurfaceVariant",
    "surfaceTint",
    "inverseSurface",
    "inverseOnSurface",
    "error",
    "onError",
    "errorContainer",
    "onErrorContainer",
    "outline",
    "outlineVariant",
    "scrim",
    "surfaceBright",
    "surfaceDim",
    "surfaceContainer",
    "surfaceContainerHigh",
    "surfaceContainerHighest",
    "surfaceContainerLow",
    "surfaceContainerLowest",
    "primaryFixed",
    "primaryFixedDim",
    "onPrimaryFixed",
    "onPrimaryFixedVariant",
    "secondaryFixed",
    "secondaryFixedDim",
    "onSecondaryFixed",
    "onSecondaryFixedVariant",
    "tertiaryFixed",
    "tertiaryFixedDim",
    "onTertiaryFixed",
    "onTertiaryFixedVariant",
]
"""A role of material3's ColorScheme."""
ROLES: tuple[Role, ...] = get_args(Role.__value__)
"""Every role of material3's ColorScheme, in the order of its constructor."""


class Source(NamedTuple):
    """Where a Material role's colour comes from in one mode."""

    name: str
    """A copper port name: a role (``accent``) or a named colour (``blue-4``)."""
    mode: Mode | None = None
    """The mode the colour is taken from; None for the scheme's own mode."""

    @classmethod
    def parse(cls, value: str) -> "Source":
        """A source as the table writes it: ``name`` or ``<mode>:<name>``."""
        own, separator, name = value.partition(":")
        if not separator:
            return cls(value)
        if own not in MODES:
            raise ValueError(f"{value!r} names no mode")
        return cls(name, cast(Mode, own))

    def __str__(self) -> str:
        return self.name if self.mode is None else f"{self.mode}:{self.name}"


class Row(NamedTuple):
    """A Material role's source in light and in dark mode."""

    light: Source
    dark: Source

    def of(self, mode: Mode) -> Source:
        return self.light if mode == "light" else self.dark


def _row(light: str, dark: str) -> Row:
    return Row(Source.parse(light), Source.parse(dark))


# Why the table reads as it does:
# - primary is the accent with on-accent on it; the other colour roles follow
#   its pattern. A colour role is a fill with step 1 on it (neutral 1 in light
#   mode, the hue's own step 1 in dark mode, as on-accent) and also text on the
#   app's grounds (Material draws a text field's error text in error, a
#   selected tab or a text button in primary, a selected navigation label in
#   secondary), so it takes the first step from 9 that reaches 4.5:1 both ways,
#   on surface Highest included. That is step 9 for blue in light mode and for
#   every hue in dark mode. In light mode neutral, violet and red 9 and 10 fall
#   short as text (on Highest, step 4, neutral 10 reaches 3.97:1, violet 10
#   4.16:1, red 10 4.19:1), so secondary, tertiary and error take their text
#   step 11. In dark mode neutral 9 reaches only 3.90:1 on Highest, step 5, so
#   secondary takes 10.
#   The containers are the hovered component step 4 with the text step 12 on it.
# - secondary is the neutral, the quieter accent; tertiary is violet, about
#   where Material's hue rotation from blue lands; error is red.
# - background and surface are bg: Material's surface is the app's ground under
#   its components, which lift off it in the surface containers. copper's own
#   surface role (cards on bg) is lighter than bg in light mode, while
#   Material's containers darken in light mode, so it is no container here.
# - The containers come from the neutral steps in order: lighter to darker in
#   light mode (Lowest 1, Low 2, Container 3, High 4, Highest 4), darker to
#   lighter in dark mode (1 to 5). Material's light containers span about ten
#   tones (100 to 90), roughly steps 1-4, and its filled text field puts
#   onSurfaceVariant (text-muted) on Highest; text-muted reaches 4.5:1 on light
#   steps 1-4 only, so High and Highest share step 4.
# - surfaceDim is never lighter than surface and surfaceBright never darker, and
#   one of them equals surface, as in Material's baseline: in light mode Bright
#   is surface (bg) and Dim is step 4, under the containers' rule; in dark mode
#   Dim is surface (bg) and Bright is step 6, above Highest.
# - surfaceVariant is surface-raised, a component background on a surface; its
#   text is text-muted. The outlines are border-strong and border.
# - The inverse roles are the other mode's: its surface, its text and its
#   accent.
# - The fixed roles are the same in both modes and come from the light mode's
#   steps, as Material takes them from its light tones: Fixed step 3, FixedDim
#   step 4, one step stronger, onFixed step 12 and onFixedVariant step 11.
#   Material's tones put onFixedVariant on both Fixed and FixedDim, and step 11
#   reaches 4.5:1 on the neutral and violet only up to step 4.
# - scrim is the dark mode's neutral 1, its background, in both modes
#   (Material's is black, drawn at 32% opacity).
# - surfaceTint is primary, Material's default; components of this material3
#   version take their containers from the surface containers, and only an
#   explicit tonal elevation mixes the tint into surface.
SCHEME: dict[Role, Row] = {
    "primary": _row("accent", "accent"),
    "onPrimary": _row("on-accent", "on-accent"),
    "primaryContainer": _row("blue-4", "blue-4"),
    "onPrimaryContainer": _row("blue-12", "blue-12"),
    "inversePrimary": _row("dark:accent", "light:accent"),
    "secondary": _row("neutral-11", "neutral-10"),
    "onSecondary": _row("neutral-1", "neutral-1"),
    "secondaryContainer": _row("neutral-4", "neutral-4"),
    "onSecondaryContainer": _row("neutral-12", "neutral-12"),
    "tertiary": _row("violet-11", "violet-9"),
    "onTertiary": _row("neutral-1", "violet-1"),
    "tertiaryContainer": _row("violet-4", "violet-4"),
    "onTertiaryContainer": _row("violet-12", "violet-12"),
    "background": _row("bg", "bg"),
    "onBackground": _row("text", "text"),
    "surface": _row("bg", "bg"),
    "onSurface": _row("text", "text"),
    "surfaceVariant": _row("surface-raised", "surface-raised"),
    "onSurfaceVariant": _row("text-muted", "text-muted"),
    "surfaceTint": _row("accent", "accent"),
    "inverseSurface": _row("dark:surface", "light:surface"),
    "inverseOnSurface": _row("dark:text", "light:text"),
    "error": _row("red-11", "error"),
    "onError": _row("neutral-1", "red-1"),
    "errorContainer": _row("red-4", "red-4"),
    "onErrorContainer": _row("red-12", "red-12"),
    "outline": _row("border-strong", "border-strong"),
    "outlineVariant": _row("border", "border"),
    "scrim": _row("dark:neutral-1", "dark:neutral-1"),
    "surfaceBright": _row("bg", "neutral-6"),
    "surfaceDim": _row("neutral-4", "bg"),
    "surfaceContainer": _row("neutral-3", "neutral-3"),
    "surfaceContainerHigh": _row("neutral-4", "neutral-4"),
    "surfaceContainerHighest": _row("neutral-4", "neutral-5"),
    "surfaceContainerLow": _row("neutral-2", "neutral-2"),
    "surfaceContainerLowest": _row("neutral-1", "neutral-1"),
    "primaryFixed": _row("light:blue-3", "light:blue-3"),
    "primaryFixedDim": _row("light:blue-4", "light:blue-4"),
    "onPrimaryFixed": _row("light:blue-12", "light:blue-12"),
    "onPrimaryFixedVariant": _row("light:blue-11", "light:blue-11"),
    "secondaryFixed": _row("light:neutral-3", "light:neutral-3"),
    "secondaryFixedDim": _row("light:neutral-4", "light:neutral-4"),
    "onSecondaryFixed": _row("light:neutral-12", "light:neutral-12"),
    "onSecondaryFixedVariant": _row("light:neutral-11", "light:neutral-11"),
    "tertiaryFixed": _row("light:violet-3", "light:violet-3"),
    "tertiaryFixedDim": _row("light:violet-4", "light:violet-4"),
    "onTertiaryFixed": _row("light:violet-12", "light:violet-12"),
    "onTertiaryFixedVariant": _row("light:violet-11", "light:violet-11"),
}
"""Each Material role's copper source, in light and in dark mode."""

_SURFACES: tuple[Role, ...] = (
    "surface",
    "surfaceDim",
    "surfaceBright",
    "surfaceContainerLowest",
    "surfaceContainerLow",
    "surfaceContainer",
    "surfaceContainerHigh",
    "surfaceContainerHighest",
    "surfaceVariant",
)
"""Every surface onSurface and onSurfaceVariant are measured on."""
GROUNDS: tuple[Role, ...] = (
    "background",
    "surface",
    "surfaceContainerLowest",
    "surfaceContainerLow",
    "surfaceContainer",
    "surfaceContainerHigh",
    "surfaceContainerHighest",
)
"""The grounds the colour roles are measured on as text: the app's background, its surface and its containers."""
COLOURS_AS_TEXT: tuple[Role, ...] = ("primary", "secondary", "tertiary", "error")
"""The colour roles Material also draws as text on the grounds."""

_TEXT_ON_SURFACES: tuple[tuple[Role, Role], ...] = tuple(
    (text, surface) for text in ("onSurface", "onSurfaceVariant") for surface in _SURFACES
)
_COLOURS_ON_GROUNDS: tuple[tuple[Role, Role], ...] = tuple(
    (colour, ground) for colour in COLOURS_AS_TEXT for ground in GROUNDS
)
PAIRS: tuple[tuple[Role, Role], ...] = (
    ("onPrimary", "primary"),
    ("onPrimaryContainer", "primaryContainer"),
    ("onSecondary", "secondary"),
    ("onSecondaryContainer", "secondaryContainer"),
    ("onTertiary", "tertiary"),
    ("onTertiaryContainer", "tertiaryContainer"),
    ("onError", "error"),
    ("onErrorContainer", "errorContainer"),
    ("onBackground", "background"),
    *_TEXT_ON_SURFACES,
    ("inverseOnSurface", "inverseSurface"),
    ("inversePrimary", "inverseSurface"),
    *_COLOURS_ON_GROUNDS,
    ("onPrimaryFixed", "primaryFixed"),
    ("onPrimaryFixed", "primaryFixedDim"),
    ("onPrimaryFixedVariant", "primaryFixed"),
    ("onPrimaryFixedVariant", "primaryFixedDim"),
    ("onSecondaryFixed", "secondaryFixed"),
    ("onSecondaryFixed", "secondaryFixedDim"),
    ("onSecondaryFixedVariant", "secondaryFixed"),
    ("onSecondaryFixedVariant", "secondaryFixedDim"),
    ("onTertiaryFixed", "tertiaryFixed"),
    ("onTertiaryFixed", "tertiaryFixedDim"),
    ("onTertiaryFixedVariant", "tertiaryFixed"),
    ("onTertiaryFixedVariant", "tertiaryFixedDim"),
)
"""The pairs of a colour (second) and the text drawn on it (first) that must reach 4.5:1:

- material3's own pairs (its ``contentColorFor``): each colour with its ``on``
  colour, surface, Dim, Bright and every surface container with onSurface,
  and each fixed colour with its onFixed;
- onSurface and onSurfaceVariant on surface, Dim, Bright, every surface
  container and surfaceVariant;
- the snackbar's action, inversePrimary, on inverseSurface;
- primary, secondary, tertiary and error as text on background, surface and
  every surface container (GROUNDS);
- each fixed role's variant text on its Fixed and FixedDim colours.
"""

NEED = contrast.NEEDS["text"]


class Resolved(NamedTuple):
    """A Material role's colour in one mode: the mode and the copper name it is taken from, and its ``#rrggbb``."""

    mode: Mode
    name: str
    hex: str


type ColoursByMode = Mapping[Mode, Mapping[str, str]]
"""Both modes' colours by port name, as tokens.ModeTokens.colours holds them."""


def resolve(role: Role, mode: Mode, colours: ColoursByMode) -> Resolved:
    """A Material role's colour in one mode; a source that names no colour of its mode raises a ValueError."""
    source = SCHEME[role].of(mode)
    own = source.mode or mode
    hex_colour = colours[own].get(source.name)
    if hex_colour is None:
        raise ValueError(f"{role} ({mode}): {str(source)!r} names no {own} colour")
    return Resolved(own, source.name, hex_colour)


def resolved(mode: Mode, colours: ColoursByMode) -> dict[Role, Resolved]:
    """Every Material role's colour in one mode, in ROLES's order."""
    return {role: resolve(role, mode, colours) for role in ROLES}


def scheme(mode: Mode, colours: ColoursByMode) -> dict[Role, str]:
    """One mode's colour scheme: every Material role, in ROLES's order, as ``#rrggbb``."""
    return {role: colour.hex for role, colour in resolved(mode, colours).items()}


def template_context(colours: ColoursByMode) -> dict[str, Any]:
    """What the colour scheme template gets: the material3 version and per mode each role's mode and copper name."""
    return {
        "material3": MATERIAL3,
        "schemes": [
            {
                "mode": mode,
                "roles": [(role, colour.mode, colour.name) for role, colour in resolved(mode, colours).items()],
            }
            for mode in MODES
        ],
    }


def checks(colour_scheme: Mapping[Role, str]) -> list[contrast.Check]:
    """Every pair's contrast in one mode's colour scheme, in PAIRS's order."""
    return [
        contrast.Check(text, fill, NEED, contrast.ratio(colour_scheme[text], colour_scheme[fill]))
        for text, fill in PAIRS
    ]
