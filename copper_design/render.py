"""Rendering the ports and the README swatch from the tokens, through the Jinja2 templates."""

import json
import traceback
import xml.etree.ElementTree as ElementTree
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined, TemplateSyntaxError, select_autoescape

from copper_design import material, palette, tokens

type PerMode = Mapping[palette.Mode, str]
"""A path below the output root for each mode."""


def each_mode(pattern: str) -> PerMode:
    """A path pattern with ``{mode}`` filled in for each mode."""
    return {mode: pattern.format(mode=mode) for mode in palette.MODES}


ANDROID_VALUES: dict[palette.Mode, str] = {"light": "values", "dark": "values-night"}
"""The Android resource directory of each mode: the system takes values-night in dark mode."""

HERDR_TEMPLATE = "herdr.json.j2"
OUTPUTS: tuple[tuple[PerMode, str], ...] = (
    (each_mode("ports/herdr/copper-{mode}.json"), HERDR_TEMPLATE),
    (
        {mode: f"ports/android/res/{values}/copper_colors.xml" for mode, values in ANDROID_VALUES.items()},
        "copper_colors.xml.j2",
    ),
    (each_mode("docs/swatch-{mode}.svg"), "swatch.svg.j2"),
)
"""What `render` writes once per mode: each mode's path below the output root, and the template."""

type ExtraContext = Callable[[material.ColoursByMode], dict[str, Any]]
"""What a template rendered for both modes gets beside the modes' contexts, from both modes' colours."""

KOTLIN = "ports/android/kotlin/dev/cupr/design"
BOTH_MODES_OUTPUTS: tuple[tuple[str, str, ExtraContext | None], ...] = (
    (f"{KOTLIN}/CopperColors.kt", "CopperColors.kt.j2", None),
    (f"{KOTLIN}/CopperColorScheme.kt", "CopperColorScheme.kt.j2", material.template_context),
)
"""What `render` writes once, from both modes' tokens: a path below the output root, the template and what else
it gets."""


class RenderError(ValueError):
    """A template failed to render, or rendered a file its format refuses."""


def environment() -> Environment:
    """The templates shipped with the package; a name a template uses but the context lacks raises.

    Autoescaping is on for the HTML, SVG and XML templates and off for the
    JSON template, which writes every value through the ``tojson`` filter
    instead (tests/test_render.py holds it to that), and for the Kotlin
    templates, which write only token names, modes, Material role names, the
    material3 version and colours, none of them with a character Kotlin would
    need escaped.
    """
    env = Environment(
        loader=PackageLoader("copper_design", "templates"),
        undefined=StrictUndefined,
        autoescape=select_autoescape(
            enabled_extensions=("html.j2", "svg.j2", "xml.j2"), default_for_string=True, default=False
        ),
        keep_trailing_newline=True,
    )
    env.filters.update(
        kotlin_name=kotlin_name, kotlin_colour=kotlin_colour, android_name=android_name, android_colour=android_colour
    )
    return env


def kotlin_name(name: str) -> str:
    """A port name as a Kotlin property: ``bg-alt`` is ``bgAlt``, ``blue-9`` is ``blue9``."""
    first, *rest = name.split("-")
    return first + "".join(word[:1].upper() + word[1:] for word in rest)


def kotlin_colour(hex_colour: str) -> str:
    """An opaque ``#rrggbb`` as a Compose colour: ``Color(0xFFRRGGBB)``."""
    return f"Color(0xFF{hex_colour[1:].upper()})"


def android_name(name: str) -> str:
    """A port name as an Android resource name: ``bg-alt`` is ``copper_bg_alt``, ``blue-9`` is ``copper_blue_9``."""
    return "copper_" + name.replace("-", "_")


def android_colour(hex_colour: str) -> str:
    """An opaque ``#rrggbb`` as an Android colour resource writes it, alpha first: ``#FFRRGGBB``."""
    return f"#FF{hex_colour[1:].upper()}"


def context(mode_tokens: tokens.ModeTokens) -> dict[str, Any]:
    """What every template gets: the mode, its colours by name, the base colours in palette order, the roles."""
    return {
        "mode": mode_tokens.mode,
        "c": mode_tokens.colours,
        "bases": list(mode_tokens.bases),
        "roles": list(mode_tokens.roles),
    }


def both_modes_context(by_mode: Mapping[palette.Mode, tokens.ModeTokens]) -> dict[str, Any]:
    """What every template rendered once for both modes gets: each mode's context, in palette.MODES's order."""
    return {"modes": [context(by_mode[mode]) for mode in palette.MODES]}


def _where_in_template(template: str, error: BaseException) -> str:
    """Where in the template an error was raised: `` line N``, or `` (in <other> line N)``; nothing if unknown.

    A template's frames are its top-level code, its blocks and its macros. The
    last one is where the error was raised; when it belongs to another template
    (included, extended or imported), that template is named. A loader without
    file names (such as DictLoader) gives every template the same file name
    (``<template>``), so there another template's line is reported under the
    outer template.
    """
    if isinstance(error, TemplateSyntaxError):
        return f" line {error.lineno}"
    frames = [frame for frame in traceback.extract_tb(error.__traceback__) if _is_template_frame(frame.name)]
    if not frames:
        return ""
    last = frames[-1]
    name = Path(last.filename).name
    if last.filename != _NO_FILE_NAME and name != Path(template).name:
        return f" (in {name} line {last.lineno})"
    return f" line {last.lineno}"


_NO_FILE_NAME = "<template>"


def _is_template_frame(name: str) -> bool:
    """Whether a traceback frame is a template's own: Jinja2 names its top-level code, blocks and macros so."""
    return name in {"top-level template code", "template"} or name.startswith("block ")


def render_template(env: Environment, template: str, where: str, **values: Any) -> str:
    """A template rendered with the given values; a failure raises a RenderError naming template, line and where."""
    try:
        return env.get_template(template).render(values)
    except Exception as error:  # a template can raise anything its expressions do; all of it is the template's fault
        message = f"{type(error).__name__}: {error}"
        raise RenderError(f"{template}{_where_in_template(template, error)} ({where}): {message}") from error


def render(env: Environment, template: str, mode_tokens: tokens.ModeTokens) -> str:
    """One template rendered for one mode."""
    return render_template(env, template, mode_tokens.mode, **context(mode_tokens))


def _check_format(path: str, template: str, text: str) -> None:
    """A JSON or XML output parsed, so a template that renders a broken one raises."""
    if path.endswith(".json"):
        try:
            json.loads(text)
        except json.JSONDecodeError as error:
            raise RenderError(f"{path} ({template}) is no valid JSON: {error}") from error
    elif path.endswith(".xml"):
        try:
            ElementTree.fromstring(text)
        except ElementTree.ParseError as error:
            raise RenderError(f"{path} ({template}) is no well-formed XML: {error}") from error


def outputs() -> dict[str, str]:
    """The ports and the README swatch rendered from the tokens, by path below the output root.

    A JSON or XML output is parsed, so a template that renders a broken one raises here.
    """
    env = environment()
    rendered: dict[str, str] = {}
    by_mode: dict[palette.Mode, tokens.ModeTokens] = {mode: tokens.load(mode) for mode in palette.MODES}
    for mode, mode_tokens in by_mode.items():
        for paths, template in OUTPUTS:
            path = paths[mode]
            text = render(env, template, mode_tokens)
            _check_format(path, template, text)
            rendered[path] = text
    colours: material.ColoursByMode = {mode: mode_tokens.colours for mode, mode_tokens in by_mode.items()}
    for path, template, extra in BOTH_MODES_OUTPUTS:
        values = both_modes_context(by_mode) | (extra(colours) if extra else {})
        text = render_template(env, template, "both modes", **values)
        _check_format(path, template, text)
        rendered[path] = text
    return rendered
