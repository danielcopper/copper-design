"""Rendering the ports and the README swatch from the tokens, through the Jinja2 templates."""

import json
from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

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

    Autoescaping is on for the HTML and SVG templates and off for the JSON
    template, which writes every value through the ``tojson`` filter instead
    (tests/test_render.py holds it to that).
    """
    return Environment(
        loader=PackageLoader("copper_design", "templates"),
        undefined=StrictUndefined,
        autoescape=select_autoescape(enabled_extensions=("html.j2", "svg.j2"), default_for_string=True, default=False),
        keep_trailing_newline=True,
    )


def context(mode_tokens: tokens.ModeTokens) -> dict[str, Any]:
    """What every template gets: the mode, its colours by name, the base colours in palette order."""
    return {"mode": mode_tokens.mode, "c": mode_tokens.colours, "bases": list(mode_tokens.bases)}


def render_template(env: Environment, template: str, where: str, **values: Any) -> str:
    """A template rendered with the given values; any failure in it raises a RenderError naming template and where."""
    try:
        return env.get_template(template).render(values)
    except Exception as error:  # a template can raise anything its expressions do; all of it is the template's fault
        raise RenderError(f"{template} ({where}): {error}") from error


def render(env: Environment, template: str, mode_tokens: tokens.ModeTokens) -> str:
    """One template rendered for one mode."""
    return render_template(env, template, mode_tokens.mode, **context(mode_tokens))


def outputs() -> dict[str, str]:
    """The ports and the README swatch rendered from the tokens, by path below the output root.

    A JSON output is parsed, so a template that renders broken JSON raises here.
    """
    env = environment()
    rendered: dict[str, str] = {}
    for mode in palette.MODES:
        mode_tokens = tokens.load(mode)
        for pattern, template in OUTPUTS:
            path = pattern.format(mode=mode)
            text = render(env, template, mode_tokens)
            if path.endswith(".json"):
                try:
                    json.loads(text)
                except json.JSONDecodeError as error:
                    raise RenderError(f"{path} ({template}) is no valid JSON: {error}") from error
            rendered[path] = text
    return rendered
