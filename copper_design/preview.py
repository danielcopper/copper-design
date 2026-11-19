"""The preview page: palette, roles, their contrast, colour-blindness views, the herdr theme and the Material 3
colour scheme, per mode.

The page is for judging the look before a release; it is written to a path the
caller names and not committed. The contrast checks are copper_design.contrast's
and copper_design.material's.
"""

import json
from collections.abc import Mapping
from typing import Any

from coloraide import Color

from copper_design import contrast, material, palette, render, tokens

CVD = ("protan", "deutan", "tritan")


def simulate(hex_colour: str, kind: str) -> str:
    """How a colour looks with a colour-vision deficiency (protan, deutan, tritan)."""
    return Color(hex_colour).filter(kind).convert("srgb").fit("srgb").to_string(hex=True)


def _with_label(hex_colour: str, colours: Mapping[str, str]) -> tuple[str, str]:
    """A colour and the neutral end (step 1 or 12) that reads best on it."""
    ends = (colours["neutral-1"], colours[f"neutral-{palette.STEPS}"])
    return hex_colour, max(ends, key=lambda end: contrast.ratio(end, hex_colour))


def material_data(mode: palette.Mode, colour_scheme: Mapping[str, str]) -> dict[str, Any]:
    """The Material 3 colour scheme of one mode: each role with its source and colour, each pair's contrast."""
    roles = []
    for role in material.ROLES:
        own, name = material.source(role, mode)
        roles.append({"name": role, "source": name if own == mode else f"{own}: {name}", "hex": colour_scheme[role]})
    pairs = [
        {"check": check, "text": colour_scheme[check.foreground], "fill": colour_scheme[check.background]}
        for check in material.checks(colour_scheme)
    ]
    return {"version": material.MATERIAL3, "roles": roles, "pairs": pairs}


def mode_data(
    mode_tokens: tokens.ModeTokens, herdr: dict[str, Any], colour_scheme: Mapping[str, str]
) -> dict[str, Any]:
    """Everything the page shows for one mode; colour_scheme is its Material 3 colour scheme."""
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
        "herdr": herdr,
        "ansi": [(hex_colour, contrast.ratio(hex_colour, herdr["background"])) for hex_colour in herdr["ansi"]],
        "material": material_data(mode_tokens.mode, colour_scheme),
    }


def page() -> str:
    """The preview page as HTML."""
    env = render.environment()
    by_mode: dict[palette.Mode, tokens.ModeTokens] = {mode: tokens.load(mode) for mode in palette.MODES}
    colours: dict[palette.Mode, Mapping[str, str]] = {mode: loaded.colours for mode, loaded in by_mode.items()}
    modes = []
    for mode, mode_tokens in by_mode.items():
        herdr = json.loads(render.render(env, render.HERDR_TEMPLATE, mode_tokens))
        modes.append(mode_data(mode_tokens, herdr, material.scheme(mode, colours)))
    return render.render_template(env, "preview.html.j2", "both modes", modes=modes)
