"""The preview page: palette, roles, their contrast, colour-blindness views, the herdr theme and the Material 3
colour scheme, per mode.

The page is for judging the look before a release; it is written to a path the
caller names and not committed. The contrast checks are copper_design.contrast's
and copper_design.material's; the herdr panels are drawn as herdr resolves the
theme (copper_design.herdr).
"""

import json
from collections.abc import Mapping
from typing import Any

from coloraide import Color

from copper_design import contrast, herdr, material, palette, render, tokens

CVD = ("protan", "deutan", "tritan")


def simulate(hex_colour: str, kind: str) -> str:
    """How a colour looks with a colour-vision deficiency (protan, deutan, tritan)."""
    return Color(hex_colour).filter(kind).convert("srgb").fit("srgb").to_string(hex=True)


def _with_label(hex_colour: str, colours: Mapping[str, str]) -> tuple[str, str]:
    """A colour and the neutral end (step 1 or 12) that reads best on it."""
    ends = (colours["neutral-1"], colours[f"neutral-{palette.STEPS}"])
    return hex_colour, max(ends, key=lambda end: contrast.ratio(end, hex_colour))


def material_data(mode: palette.Mode, colours: material.ColoursByMode) -> dict[str, Any]:
    """The Material 3 colour scheme of one mode: each role with its source and colour, each pair's contrast.

    A source is the copper name, after the mode it is taken from where that is the other mode or one mode for both.
    """
    resolved = material.resolved(mode, colours)
    roles = [
        {
            "name": role,
            "source": colour.name if material.SCHEME[role].of(mode).mode is None else f"{colour.mode}: {colour.name}",
            "hex": colour.hex,
        }
        for role, colour in resolved.items()
    ]
    colour_scheme: dict[material.Role, str] = {role: colour.hex for role, colour in resolved.items()}
    pairs = [
        {"check": check, "text": colour_scheme[text], "fill": colour_scheme[fill]}
        for (text, fill), check in zip(material.PAIRS, material.checks(colour_scheme), strict=True)
    ]
    return {"version": material.MATERIAL3, "roles": roles, "pairs": pairs}


def _grounds(resolved: Mapping[str, str], pairs: tuple[tuple[str, str], ...]) -> list[dict[str, Any]]:
    """Per ground of the pairs, in their order, the checks of the text on it."""
    checks = herdr.checks(resolved, pairs)
    return [
        {
            "name": ground,
            "hex": resolved[ground],
            "texts": [(check, resolved[check.foreground]) for check in checks if check.background == ground],
        }
        for ground in dict.fromkeys(ground for _, ground in pairs)
    ]


def herdr_data(theme: Mapping[str, Any], bases: tuple[str, ...]) -> dict[str, Any]:
    """The colours herdr resolves from a theme, each with whether the theme or herdr sets it, and per ground in
    copper_design.herdr's PAIRS, then in its ``mod_pairs`` of the base colours, the checks of the text on it."""
    resolved = herdr.resolve(theme)
    set_by_theme = herdr.set_by_theme(theme)
    return {
        "version": herdr.HERDR,
        "resolved": resolved,
        "colours": [
            (key, hex_colour, "theme" if key in set_by_theme else "herdr") for key, hex_colour in resolved.items()
        ],
        "grounds": _grounds(resolved, herdr.PAIRS),
        "mod_grounds": _grounds(resolved, herdr.mod_pairs(bases)),
    }


def mode_data(
    mode_tokens: tokens.ModeTokens, herdr_theme: dict[str, Any], colours_by_mode: material.ColoursByMode
) -> dict[str, Any]:
    """Everything the page shows for one mode; its Material 3 scheme takes from both modes' colours."""
    colours = mode_tokens.colours
    checks = contrast.checks(colours)
    named = [*(name for name in mode_tokens.bases if name != palette.NEUTRAL), *contrast.STATES]
    return {
        "mode": mode_tokens.mode,
        "c": colours,
        "bases": mode_tokens.bases,
        "scales": {
            name: [_with_label(colours[f"{name}-{step}"], colours) for step in range(1, palette.STEPS + 1)]
            for name in mode_tokens.bases
        },
        "roles": [
            {
                "name": role,
                "reference": reference,
                "hex": colours[role],
                "kind": contrast.KINDS.get(role, "unclassified"),
                "checks": [check for check in checks if check.foreground == role],
            }
            for role, reference in mode_tokens.roles.items()
        ],
        "states": contrast.STATES,
        "cvd": {
            "names": named,
            "rows": [("normal", [colours[name] for name in named])]
            + [(kind, [simulate(colours[name], kind) for name in named]) for kind in CVD],
        },
        "herdr": herdr_theme,
        "herdr_panels": herdr_data(herdr_theme, mode_tokens.bases),
        "ansi": [
            (hex_colour, contrast.ratio(hex_colour, herdr_theme["background"])) for hex_colour in herdr_theme["ansi"]
        ],
        "material": material_data(mode_tokens.mode, colours_by_mode),
    }


def page() -> str:
    """The preview page as HTML."""
    env = render.environment()
    by_mode: dict[palette.Mode, tokens.ModeTokens] = {mode: tokens.load(mode) for mode in palette.MODES}
    colours: material.ColoursByMode = {mode: loaded.colours for mode, loaded in by_mode.items()}
    modes = []
    for mode_tokens in by_mode.values():
        herdr_theme = json.loads(render.render_output(env, render.HERDR_TEMPLATE, mode_tokens))
        modes.append(mode_data(mode_tokens, herdr_theme, colours))
    return render.render_template(env, "preview.html.j2", "both modes", modes=modes)
