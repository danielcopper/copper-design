"""The token files are valid DTCG 2025.10, and the resolver selects light or dark.

Every palette colour is a colour object, every role a reference that resolves to
a palette step, no reference chain is a cycle, and the resolver's ``mode``
modifier selects the light or the dark files.
"""

import json
import re
from typing import Any

import pytest

from copper_design import palette, tokens

ROLES = {
    "bg",
    "bg-alt",
    "surface",
    "surface-raised",
    "border",
    "text",
    "text-muted",
    "text-subtle",
    "accent",
    "on-accent",
    "selection",
    "success",
    "warning",
    "error",
    "info",
}
BASES = ["neutral", "blue", "green", "teal", "yellow", "orange", "red", "violet"]
STEP_NAMES = {str(step) for step in range(1, palette.STEPS + 1)}


def _document(name: str) -> dict[str, Any]:
    return json.loads(tokens.directory().joinpath(name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("mode", palette.MODES)
def test_every_palette_colour_is_a_colour_object(mode: str) -> None:
    document = _document(tokens.palette_file(mode))
    assert list(document) == BASES
    for name, group in document.items():
        assert group["$type"] == "color", name
        assert set(group) == {"$type", "$root"} | STEP_NAMES, name
        assert group["$root"] == {"$value": f"{{{name}.9}}"}, f"{name}: the main value is not step 9"
    flat = tokens.flatten(document)
    steps = {path: token for path, token in flat.items() if not path.endswith(".$root")}
    assert len(steps) == len(BASES) * palette.STEPS
    for path, token in steps.items():
        assert token.type == "color", path
        assert token.reference is None, path
        tokens.check_colour(path, token.value)
        assert set(token.value) == {"colorSpace", "components", "hex"}, path


@pytest.mark.parametrize("mode", palette.MODES)
def test_every_role_is_a_reference_to_a_palette_step(mode: str) -> None:
    document = _document(f"roles.{mode}.tokens.json")
    assert set(document) == ROLES
    step = re.compile(rf"^\{{({'|'.join(BASES)})\.([1-9]|1[0-2])\}}$")
    for name, token in document.items():
        assert set(token) <= {"$value", "$description"}, name
        assert step.match(token["$value"]), f"{name}: {token['$value']} is not a reference to a palette step"


@pytest.mark.parametrize("mode", palette.MODES)
def test_every_reference_resolves_to_a_colour_without_a_cycle(mode: str) -> None:
    flat = tokens.flatten(tokens.merged({"mode": mode}))
    resolved = tokens.resolve(flat)
    assert resolved.keys() == flat.keys()
    for path, token in resolved.items():
        assert token.type == "color", path
        tokens.check_colour(path, token.value)


def test_the_resolver_selects_light_or_dark() -> None:
    palettes = palette.build(palette.load_parameters())
    for mode in palette.MODES:
        colours = tokens.colours(mode)
        for name, scale in palettes[mode].items():
            assert [colours[f"{name}-{step}"] for step in range(1, palette.STEPS + 1)] == scale, f"{mode} {name}"
            assert colours[name] == scale[8], f"{mode}: {name} is not its step 9"
        roles = _document(f"roles.{mode}.tokens.json")
        for role, token in roles.items():
            assert colours[role] == colours[token["$value"].strip("{}").replace(".", "-")], f"{mode} {role}"
    assert tokens.colours("light")["bg"] != tokens.colours("dark")["bg"]


def test_the_resolver_refuses_an_input_it_does_not_declare() -> None:
    with pytest.raises(tokens.TokenError, match="invalid context 'dim' for modifier 'mode'"):
        tokens.merged({"mode": "dim"})
    with pytest.raises(tokens.TokenError, match="unknown modifier 'theme'"):
        tokens.merged({"mode": "light", "theme": "light"})
    with pytest.raises(tokens.TokenError, match="missing modifier 'mode'"):
        tokens.merged({})
    with pytest.raises(tokens.TokenError, match="no mode 'dim'"):
        tokens.colours("dim")


_COLOUR = {"colorSpace": "srgb", "components": [1, 0, 0], "hex": "#ff0000"}


def test_a_reference_cycle_is_refused() -> None:
    tree = {"a": {"$value": "{b}"}, "b": {"$value": "{c}"}, "c": {"$value": "{a}"}}
    with pytest.raises(tokens.TokenError, match="reference cycle: a -> b -> c -> a"):
        tokens.resolve(tokens.flatten(tree))


def test_a_reference_to_no_token_is_refused() -> None:
    tree = {"red": {"$type": "color", "1": {"$value": _COLOUR}}, "accent": {"$value": "{red.2}"}}
    with pytest.raises(tokens.TokenError, match=r"accent: refers to \{red\.2\}, which is no token"):
        tokens.resolve(tokens.flatten(tree))


def test_a_reference_to_another_type_is_refused() -> None:
    tree = {
        "size": {"$type": "dimension", "$value": {"value": 4, "unit": "px"}},
        "accent": {"$type": "color", "$value": "{size}"},
    }
    with pytest.raises(tokens.TokenError, match="accent: a color token refers to a dimension token"):
        tokens.resolve(tokens.flatten(tree))


def test_a_token_holding_tokens_is_refused() -> None:
    tree = {"red": {"$type": "color", "$value": _COLOUR, "1": {"$value": _COLOUR}}}
    with pytest.raises(tokens.TokenError, match="red: a token cannot hold tokens or groups"):
        tokens.flatten(tree)


def test_a_name_with_a_period_is_refused() -> None:
    with pytest.raises(tokens.TokenError, match=r"red\.1: a name may not hold"):
        tokens.flatten({"red.1": {"$type": "color", "$value": _COLOUR}})


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ({"colorSpace": "oklch", "components": [0.5, 0.1, 30]}, "not a colour object in sRGB"),
        ({"colorSpace": "srgb", "components": [1, 0]}, "components must be three numbers 0-1"),
        ({"colorSpace": "srgb", "components": [1.2, 0, 0]}, "components must be three numbers 0-1"),
        ({"colorSpace": "srgb", "components": [1, 0, 0], "alpha": 2}, "alpha must be a number 0-1"),
        ({"colorSpace": "srgb", "components": [1, 0, 0], "hex": "#fe0000"}, "does not match the components"),
        ({"colorSpace": "srgb", "components": [1, 0, 0], "name": "red"}, "unknown colour properties"),
        ("#ff0000", "not a colour object in sRGB"),
    ],
)
def test_a_colour_that_is_no_valid_colour_object_is_refused(value: object, message: str) -> None:
    with pytest.raises(tokens.TokenError, match=message):
        tokens.check_colour("red.1", value)
