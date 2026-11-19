"""Rendering: the palette tokens from the parameters, the ports and the README swatch from the tokens."""

from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined

from copper_design import palette, tokens

OUTPUTS = (
    ("ports/herdr/copper-{mode}.json", "herdr.json.j2"),
    ("docs/swatch-{mode}.svg", "swatch.svg.j2"),
)
"""What `render` writes: a path below the output root and its template, once per mode."""


def environment() -> Environment:
    """The templates shipped with the package; a name a template uses but the context lacks raises."""
    return Environment(
        loader=PackageLoader("copper_design", "templates"),
        undefined=StrictUndefined,
        autoescape=True,
        keep_trailing_newline=True,
    )


def context(mode: str) -> dict[str, Any]:
    """What every template gets: the mode, its colours by name, the base colours in palette order."""
    colours = tokens.colours(mode)
    bases = [name for name in colours if f"{name}-1" in colours]
    return {"mode": mode, "c": colours, "bases": bases}


def palette_files() -> dict[str, str]:
    """The palette token files written from the parameter file, by file name."""
    palettes = palette.build(palette.load_parameters())
    return {tokens.palette_file(mode): tokens.dump(tokens.palette_document(palettes[mode])) for mode in palette.MODES}


def outputs() -> dict[str, str]:
    """The ports and the README swatch rendered from the tokens, by path below the output root."""
    env = environment()
    rendered: dict[str, str] = {}
    for mode in palette.MODES:
        values = context(mode)
        for path, template in OUTPUTS:
            rendered[path.format(mode=mode)] = env.get_template(template).render(values)
    return rendered
