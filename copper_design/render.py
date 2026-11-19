"""Rendering the ports and the README swatch from the tokens, through the Jinja2 templates."""

import json
from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined, TemplateError

from copper_design import palette, tokens

HERDR_TEMPLATE = "herdr.json.j2"
OUTPUTS = (
    ("ports/herdr/copper-{mode}.json", HERDR_TEMPLATE),
    ("docs/swatch-{mode}.svg", "swatch.svg.j2"),
)
"""What `render` writes: a path below the output root and its template, once per mode."""


class RenderError(ValueError):
    """A template failed to render, or rendered a file its format refuses."""


def environment() -> Environment:
    """The templates shipped with the package; a name a template uses but the context lacks raises.

    Autoescaping is on for the HTML and SVG templates' sake; the JSON template
    writes its values through the ``tojson`` filter, which escapes for JSON.
    """
    return Environment(
        loader=PackageLoader("copper_design", "templates"),
        undefined=StrictUndefined,
        autoescape=True,
        keep_trailing_newline=True,
    )


def context(mode_tokens: tokens.ModeTokens) -> dict[str, Any]:
    """What every template gets: the mode, its colours by name, the base colours in palette order."""
    return {"mode": mode_tokens.mode, "c": mode_tokens.colours, "bases": list(mode_tokens.bases)}


def render(env: Environment, template: str, mode_tokens: tokens.ModeTokens) -> str:
    """One template rendered for one mode; a JSON result is parsed, so a broken one raises here."""
    try:
        text = env.get_template(template).render(context(mode_tokens))
    except TemplateError as error:
        raise RenderError(f"{template} ({mode_tokens.mode}): {error}") from error
    if template.endswith(".json.j2"):
        try:
            json.loads(text)
        except json.JSONDecodeError as error:
            raise RenderError(f"{template} ({mode_tokens.mode}) rendered no valid JSON: {error}") from error
    return text


def outputs() -> dict[str, str]:
    """The ports and the README swatch rendered from the tokens, by path below the output root."""
    env = environment()
    rendered: dict[str, str] = {}
    for mode in palette.MODES:
        mode_tokens = tokens.load(mode)
        for path, template in OUTPUTS:
            rendered[path.format(mode=mode)] = render(env, template, mode_tokens)
    return rendered
