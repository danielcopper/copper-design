"""Material 3's colour scheme from copper's roles and named colours: the Android port's mapping.

Each role of Material 3's ``ColorScheme`` takes a copper role or a named colour,
by the job of its step (issue 10, D3). ``SCHEME`` is the one table of that
mapping: the Kotlin template, the contrast checks and the preview all read it.
A source is a copper port name (``accent``, ``blue-4``) in the scheme's own
mode, or ``<mode>:<name>`` for a colour of the other mode (the inverse roles)
or of one mode for both (the fixed roles and the scrim).
"""

from collections.abc import Mapping
from typing import cast

from copper_design import contrast
from copper_design.palette import MODES, Mode

MATERIAL3 = "1.4.0"
"""The material3 version whose ColorScheme ROLES follows: the one Compose BOM 2026.09.00 resolves to."""

ROLES = (
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
)
"""Every role of material3's ColorScheme, in the order of its constructor."""

# Why the table reads as it does:
# - primary is the accent with on-accent on it; every accent colour follows its
#   pattern: the solid step 9 with step 1 on it (neutral 1 in light mode, the
#   hue's own step 1 in dark mode, as on-accent), the container on the hovered
#   component step 4 with the text step 12 on it. Light violet 9 and red 9 reach
#   only 4.35:1 and 4.39:1 with neutral 1 on them, so light tertiary and error
#   take the solid's second step, 10; blue 9 passes and stays.
# - secondary is the neutral, the quieter accent: its solid step that carries
#   neutral 1 at 4.5:1, 10 in light mode (9 reaches 3.1:1), 9 in dark mode.
# - tertiary is violet, about where Material's hue rotation from blue lands;
#   error is red.
# - background and surface are bg: Material's surface is the app's ground under
#   its components, which lift off it in the surface containers. copper's own
#   surface role (cards on bg) is lighter than bg in light mode, while
#   Material's containers darken in light mode, so it is no container here.
# - The containers come from the neutral steps in order: lighter to darker in
#   light mode (Lowest 1, Low 2, Container 3, High 4, Highest 4), darker to
#   lighter in dark mode (1 to 5). Material's light containers span about ten
#   tones (100 to 90), roughly steps 1-4, and its filled text field puts
#   onSurfaceVariant (text-muted) on Highest; text-muted reaches 4.5:1 on light
#   steps 1-4 only, so High and Highest share step 4. surfaceDim is dimmer than
#   surface and surfaceBright brighter, as Material's are: in light mode Dim is
#   step 4 under the same rule and Bright is bg, in dark mode Dim is bg and
#   Bright step 6, above Highest.
# - surfaceVariant is surface-raised, a component background on a surface; its
#   text is text-muted. The outlines are border-strong and border.
# - The inverse roles are the other mode's: its surface, its text and its
#   accent.
# - The fixed roles are the same in both modes and come from the light mode's
#   steps, as Material takes them from its light tones: Fixed step 3, FixedDim
#   step 4, one step stronger, onFixed step 12 and onFixedVariant step 11.
#   Material's tones put onFixedVariant on both Fixed and FixedDim, and step 11
#   reaches 4.5:1 on the neutral and violet only up to step 4.
# - scrim is the darkest colour copper has, the dark mode's neutral 1, in both
#   modes (Material's is black, drawn at 32% opacity).
# - surfaceTint is primary, Material's default; components of this material3
#   version take their containers from the surface containers, and only an
#   explicit tonal elevation mixes the tint into surface.
SCHEME: dict[str, tuple[str, str]] = {
    # role: (light source, dark source)
    "primary": ("accent", "accent"),
    "onPrimary": ("on-accent", "on-accent"),
    "primaryContainer": ("blue-4", "blue-4"),
    "onPrimaryContainer": ("blue-12", "blue-12"),
    "inversePrimary": ("dark:accent", "light:accent"),
    "secondary": ("neutral-10", "neutral-9"),
    "onSecondary": ("neutral-1", "neutral-1"),
    "secondaryContainer": ("neutral-4", "neutral-4"),
    "onSecondaryContainer": ("neutral-12", "neutral-12"),
    "tertiary": ("violet-10", "violet-9"),
    "onTertiary": ("neutral-1", "violet-1"),
    "tertiaryContainer": ("violet-4", "violet-4"),
    "onTertiaryContainer": ("violet-12", "violet-12"),
    "background": ("bg", "bg"),
    "onBackground": ("text", "text"),
    "surface": ("bg", "bg"),
    "onSurface": ("text", "text"),
    "surfaceVariant": ("surface-raised", "surface-raised"),
    "onSurfaceVariant": ("text-muted", "text-muted"),
    "surfaceTint": ("accent", "accent"),
    "inverseSurface": ("dark:surface", "light:surface"),
    "inverseOnSurface": ("dark:text", "light:text"),
    "error": ("red-10", "error"),
    "onError": ("neutral-1", "red-1"),
    "errorContainer": ("red-4", "red-4"),
    "onErrorContainer": ("red-12", "red-12"),
    "outline": ("border-strong", "border-strong"),
    "outlineVariant": ("border", "border"),
    "scrim": ("dark:neutral-1", "dark:neutral-1"),
    "surfaceBright": ("bg", "neutral-6"),
    "surfaceDim": ("neutral-4", "bg"),
    "surfaceContainer": ("neutral-3", "neutral-3"),
    "surfaceContainerHigh": ("neutral-4", "neutral-4"),
    "surfaceContainerHighest": ("neutral-4", "neutral-5"),
    "surfaceContainerLow": ("neutral-2", "neutral-2"),
    "surfaceContainerLowest": ("neutral-1", "neutral-1"),
    "primaryFixed": ("light:blue-3", "light:blue-3"),
    "primaryFixedDim": ("light:blue-4", "light:blue-4"),
    "onPrimaryFixed": ("light:blue-12", "light:blue-12"),
    "onPrimaryFixedVariant": ("light:blue-11", "light:blue-11"),
    "secondaryFixed": ("light:neutral-3", "light:neutral-3"),
    "secondaryFixedDim": ("light:neutral-4", "light:neutral-4"),
    "onSecondaryFixed": ("light:neutral-12", "light:neutral-12"),
    "onSecondaryFixedVariant": ("light:neutral-11", "light:neutral-11"),
    "tertiaryFixed": ("light:violet-3", "light:violet-3"),
    "tertiaryFixedDim": ("light:violet-4", "light:violet-4"),
    "onTertiaryFixed": ("light:violet-12", "light:violet-12"),
    "onTertiaryFixedVariant": ("light:violet-11", "light:violet-11"),
}
"""Each Material role's copper source, for light and for dark mode."""

_SURFACES = (
    "background",
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
PAIRS: tuple[tuple[str, str], ...] = (
    ("onPrimary", "primary"),
    ("onPrimaryContainer", "primaryContainer"),
    ("onSecondary", "secondary"),
    ("onSecondaryContainer", "secondaryContainer"),
    ("onTertiary", "tertiary"),
    ("onTertiaryContainer", "tertiaryContainer"),
    ("onError", "error"),
    ("onErrorContainer", "errorContainer"),
    ("onBackground", "background"),
    *(("onSurface", surface) for surface in _SURFACES if surface != "background"),
    *(("onSurfaceVariant", surface) for surface in _SURFACES if surface != "background"),
    ("inverseOnSurface", "inverseSurface"),
    ("inversePrimary", "inverseSurface"),
    *(
        (f"on{family}Fixed{variant}", f"{family.lower()}Fixed{dim}")
        for family in ("Primary", "Secondary", "Tertiary")
        for variant in ("", "Variant")
        for dim in ("", "Dim")
    ),
)
"""Every pair of a colour (second) and the text on it (first) that reaches 4.5:1: Material's own pairs
(material3's contentColorFor), onSurfaceVariant on every surface and container as on surface, the snackbar's
action (inversePrimary on inverseSurface) and each fixed role's variant text on its fixed colours."""

NEED = contrast.NEEDS["text"]


def source(role: str, mode: Mode) -> tuple[Mode, str]:
    """A Material role's source in one mode: the mode its colour is taken from and the copper port name."""
    value = SCHEME[role][MODES.index(mode)]
    own, separator, name = value.partition(":")
    if not separator:
        return mode, value
    if own not in MODES:
        raise ValueError(f"{role}: {value!r} names no mode")
    return cast(Mode, own), name


def scheme(mode: Mode, colours: Mapping[Mode, Mapping[str, str]]) -> dict[str, str]:
    """One mode's colour scheme: every Material role, in ROLES's order, as ``#rrggbb``."""
    result: dict[str, str] = {}
    for role in ROLES:
        own, name = source(role, mode)
        result[role] = colours[own][name]
    return result


def checks(colours: Mapping[str, str]) -> list[contrast.Check]:
    """Every pair's contrast in one mode's colour scheme, in PAIRS's order."""
    return [contrast.Check(text, fill, NEED, contrast.ratio(colours[text], colours[fill])) for text, fill in PAIRS]
