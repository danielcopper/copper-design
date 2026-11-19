"""The preview page: palette, roles, their contrast, colour-blindness views and the herdr theme, per mode.

The page is for judging the look before a release; it is written to a path the
caller names and not committed.
"""

import json
from dataclasses import dataclass

from coloraide import Color

from copper_design import palette, render, tokens

TEXT_ROLES = ("text", "text-muted", "text-subtle")
"""Roles that are text: 4.5:1 against the backgrounds (WCAG 2.2, 1.4.3)."""

GRAPHIC_ROLES = ("accent", "border", "success", "warning", "error", "info")
"""Roles that are graphics or component parts: 3:1 against the backgrounds (WCAG 2.2, 1.4.11)."""

BACKDROPS = ("bg", "surface")
"""The backgrounds every text and graphic role is measured on."""

CVD = ("protan", "deutan", "tritan")


@dataclass(frozen=True)
class RoleRow:
    name: str
    reference: str
    hex: str
    need: float | None
    ratios: tuple[float, ...]
    """The contrast against each of BACKDROPS, in that order."""

    @property
    def passes(self) -> bool:
        return self.need is None or min(self.ratios) >= self.need


def contrast(foreground: str, background: str) -> float:
    """The WCAG 2.x contrast ratio of two sRGB colours."""
    return Color(foreground).contrast(background)


def simulate(hex_colour: str, kind: str) -> str:
    """How a colour looks with a colour-vision deficiency (protan, deutan, tritan)."""
    return Color(hex_colour).filter(kind).convert("srgb").fit("srgb").to_string(hex=True)


def _need(name: str) -> float | None:
    if name in TEXT_ROLES:
        return 4.5
    if name in GRAPHIC_ROLES:
        return 3.0
    return None


def _with_label(hex_colour: str, colours: dict[str, str]) -> tuple[str, str]:
    """A colour and the neutral end (step 1 or 12) that reads best on it."""
    ends = (colours["neutral-1"], colours["neutral-12"])
    return hex_colour, max(ends, key=lambda end: contrast(end, hex_colour))


def mode_data(mode: str) -> dict[str, object]:
    """Everything the page shows for one mode."""
    colours = tokens.colours(mode)
    tree = tokens.flatten(tokens.merged({"mode": mode}))
    roles = [token for path, token in tree.items() if "." not in path]
    rows = [
        RoleRow(
            name=token.path,
            reference=token.reference or "",
            hex=colours[token.path],
            need=_need(token.path),
            ratios=tuple(contrast(colours[token.path], colours[backdrop]) for backdrop in BACKDROPS),
        )
        for token in roles
    ]
    bases = render.context(mode)["bases"]
    named = [*bases[1:], "success", "warning", "error", "info"]
    herdr = json.loads(render.outputs()[f"ports/herdr/copper-{mode}.json"])
    return {
        "mode": mode,
        "c": colours,
        "bases": bases,
        "scales": {
            name: [_with_label(colours[f"{name}-{step}"], colours) for step in range(1, palette.STEPS + 1)]
            for name in bases
        },
        "roles": rows,
        "on_accent": contrast(colours["on-accent"], colours["accent"]),
        "cvd": {
            "names": named,
            "rows": [("normal", [colours[name] for name in named])]
            + [(kind, [simulate(colours[name], kind) for name in named]) for kind in CVD],
        },
        "herdr": herdr,
        "ansi": [(hex_colour, contrast(hex_colour, herdr["background"])) for hex_colour in herdr["ansi"]],
    }


def page() -> str:
    """The preview page as HTML."""
    template = render.environment().get_template("preview.html.j2")
    return template.render(modes=[mode_data(mode) for mode in palette.MODES], backdrops=BACKDROPS)
