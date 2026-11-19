"""The token files are valid DTCG 2025.10, and the resolver selects light or dark.

Every palette colour is a colour object, every role a reference that resolves to
a palette step, no reference chain is a cycle, and the resolver's ``mode``
modifier selects the light or the dark files.
"""

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from copper_design import palette, tokens

ROLES = {
    "bg",
    "bg-alt",
    "surface",
    "surface-raised",
    "border",
    "border-strong",
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
def test_every_palette_colour_is_a_colour_object(mode: palette.Mode) -> None:
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
def test_every_role_is_a_reference_to_a_palette_step(mode: palette.Mode) -> None:
    document = _document(f"roles.{mode}.tokens.json")
    assert set(document) == ROLES
    step = re.compile(rf"^\{{({'|'.join(BASES)})\.([1-9]|1[0-2])\}}$")
    for name, token in document.items():
        assert set(token) <= {"$value", "$description"}, name
        assert step.match(token["$value"]), f"{name}: {token['$value']} is not a reference to a palette step"


def test_the_role_files_name_the_same_roles_with_the_same_descriptions() -> None:
    light, dark = (_document(f"roles.{mode}.tokens.json") for mode in palette.MODES)
    assert list(light) == list(dark)
    assert {name: token["$description"] for name, token in light.items()} == {
        name: token["$description"] for name, token in dark.items()
    }


def test_the_resolvers_contexts_are_the_modes() -> None:
    resolver = _document(tokens.RESOLVER)
    assert tuple(resolver["modifiers"]["mode"]["contexts"]) == palette.MODES


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_loaded_mode_knows_its_bases_and_roles(mode: palette.Mode) -> None:
    loaded = tokens.load(mode)
    assert loaded.mode == mode
    assert list(loaded.bases) == BASES
    roles = _document(f"roles.{mode}.tokens.json")
    assert loaded.roles == {name: token["$value"].strip("{}") for name, token in roles.items()}


@pytest.mark.parametrize("mode", palette.MODES)
def test_every_reference_resolves_to_a_colour_without_a_cycle(mode: palette.Mode) -> None:
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
    with pytest.raises(tokens.TokenError, match="no input for modifier 'mode', which has no default"):
        tokens.merged({})
    with pytest.raises(tokens.TokenError, match="input for modifier 'mode' must be a string"):
        tokens.merged(json.loads('{"mode": 1}'))


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


@pytest.mark.parametrize(
    ("tree", "message"),
    [
        ({"red": {"$type": "color", "$value": _COLOUR, "1": {"$value": _COLOUR}}}, "red: a token cannot hold ['1']"),
        ({"bg": {"$value": "{red.1}", "$valeu": "x"}}, "bg: a token cannot hold ['$valeu']"),
        ({"bg": {"$valeu": "{red.1}"}}, "bg: unknown group properties ['$valeu']"),
        (
            {"$x": {"1": {"$value": _COLOUR}}, "red": {"1": {"$value": _COLOUR}}},
            "the token tree: unknown group properties",
        ),
        ({"red": {"$type": "color"}}, "red: an empty group"),
        ({"red": {}}, "red: an empty group"),
        ({"red": {"$type": 1, "1": {"$value": _COLOUR}}}, "red: $type must be a string"),
        ({"red": {"$root": {"$type": "color"}}}, "red.$root: a root token needs a $value"),
        ({"red": 5}, "red: neither a token nor a group"),
    ],
)
def test_a_tree_that_breaks_the_format_is_refused(tree: dict[str, Any], message: str) -> None:
    with pytest.raises(tokens.TokenError, match=re.escape(message)):
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
        ({"colorSpace": "srgb", "components": [1, 0, 0], "alpha": 2}, "alpha must be 1"),
        ({"colorSpace": "srgb", "components": [1, 0, 0], "alpha": 0.2}, "alpha must be 1"),
        ({"colorSpace": "srgb", "components": [1, 0, 0], "alpha": True}, "alpha must be 1"),
        ({"colorSpace": "srgb", "components": [True, 0, 0]}, "components must be three numbers 0-1"),
        ({"colorSpace": "srgb", "components": [1, 0, 0], "hex": "#f00"}, "is not #rrggbb"),
        ({"colorSpace": "srgb", "components": [1, 0, 0], "hex": 255}, "is not #rrggbb"),
        ({"colorSpace": "srgb", "components": [1, 0, 0], "hex": "#fe0000"}, "does not match the components"),
        ({"colorSpace": "srgb", "components": [1, 0, 0], "name": "red"}, "unknown colour properties"),
        ("#ff0000", "not a colour object in sRGB"),
    ],
)
def test_a_colour_that_is_no_valid_colour_object_is_refused(value: object, message: str) -> None:
    with pytest.raises(tokens.TokenError, match=message):
        tokens.check_colour("red.1", value)


def test_an_opaque_colour_with_an_uppercase_hex_is_read() -> None:
    value = {"colorSpace": "srgb", "components": [1, 0, 0], "alpha": 1, "hex": "#FF0000"}
    assert tokens.check_colour("red.1", value) == "#ff0000"


@pytest.mark.parametrize("hex_colour", ["#FF0000", "#f00", "red"])
def test_a_colour_value_is_written_only_from_a_lowercase_hex(hex_colour: str) -> None:
    with pytest.raises(tokens.TokenError, match="is not a lowercase #rrggbb"):
        tokens.colour_value(hex_colour)


def _colour(red: float) -> dict[str, Any]:
    return {"$type": "color", "$value": {"colorSpace": "srgb", "components": [red, 0, 0]}}


type WriteResolver = Callable[..., None]


@pytest.fixture
def resolver_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> WriteResolver:
    """A token directory of the test's own: the fixture writes its resolver and token files."""
    monkeypatch.setattr(tokens, "directory", lambda: tmp_path)

    def write(resolver: dict[str, Any], **files: object) -> None:
        (tmp_path / tokens.RESOLVER).write_text(json.dumps({"version": "2025.10", **resolver}), encoding="utf-8")
        for name, document in files.items():
            (tmp_path / f"{name}.json").write_text(json.dumps(document), encoding="utf-8")

    return write


def test_sources_merge_group_by_group(resolver_dir: WriteResolver) -> None:
    resolver_dir(
        {
            "sets": {"s": {"sources": [{"red": {"1": _colour(0.1)}}, {"red": {"2": _colour(0.2)}}]}},
            "resolutionOrder": [{"$ref": "#/sets/s"}],
        },
    )
    assert set(tokens.merged({})["red"]) == {"1", "2"}


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ({"bg": {"1": _colour(0.1)}}, {"bg": _colour(0.2)}),
        ({"bg": _colour(0.2)}, {"bg": {"1": _colour(0.1)}}),
    ],
)
def test_a_token_and_a_group_of_one_name_do_not_merge(
    resolver_dir: WriteResolver, first: dict[str, Any], second: dict[str, Any]
) -> None:
    resolver_dir({"sets": {"s": {"sources": [first, second]}}, "resolutionOrder": [{"$ref": "#/sets/s"}]})
    with pytest.raises(tokens.TokenError, match="bg: a token and a group of the same name"):
        tokens.merged({})


def _mode_resolver(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "modifiers": {"mode": {"contexts": {"light": [document], "dark": [document]}}},
        "resolutionOrder": [{"$ref": "#/modifiers/mode"}],
    }


def test_two_paths_the_ports_spell_alike_are_refused(resolver_dir: WriteResolver) -> None:
    resolver_dir(_mode_resolver({"blue": {"9": _colour(0.5)}, "blue-9": _colour(0.6)}))
    with pytest.raises(tokens.TokenError, match=re.escape("blue.9 and blue-9 are both 'blue-9' in the ports")):
        tokens.load("light")


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ({"size": {"$value": 4}}, "size: an untyped token; copper holds colours only"),
        ({"size": {"$type": "dimension", "$value": {"value": 4, "unit": "px"}}}, "size: a dimension token"),
    ],
)
def test_a_token_that_is_no_colour_is_refused(
    resolver_dir: WriteResolver, document: dict[str, Any], message: str
) -> None:
    resolver_dir(_mode_resolver(document))
    with pytest.raises(tokens.TokenError, match=message):
        tokens.load("light")


def test_sets_and_contexts_merge_in_order_with_the_last_token_winning(resolver_dir: WriteResolver) -> None:
    resolver_dir(
        {
            "sets": {"base": {"sources": [{"$ref": "base.json"}, {"b": _colour(0.2)}]}},
            "modifiers": {
                "mode": {"contexts": {"light": [{"a": _colour(0.5)}], "dark": [{"a": _colour(0.9)}]}, "default": "dark"}
            },
            "resolutionOrder": [{"$ref": "#/sets/base"}, {"$ref": "#/modifiers/mode"}],
        },
        base={"a": _colour(0.1), "b": _colour(0.1), "c": _colour(0.1)},
    )
    tree = tokens.merged({})
    assert {name: token["$value"]["components"][0] for name, token in tree.items()} == {"a": 0.9, "b": 0.2, "c": 0.1}
    assert tokens.merged({"mode": "light"})["a"]["$value"]["components"][0] == 0.5


@pytest.mark.parametrize(
    ("resolver", "message"),
    [
        ({"version": "2025.06", "resolutionOrder": []}, "version must be 2025.10"),
        ({}, "resolutionOrder needs a non-empty list"),
        ({"resolutionOrder": []}, "resolutionOrder needs a non-empty list"),
        ({"resolutionOrder": ["#/sets/s"]}, "resolutionOrder[0] is not a reference to a set or modifier"),
        ({"resolutionOrder": [{"$ref": 3}]}, "resolutionOrder[0] is not a reference to a set or modifier"),
        ({"resolutionOrder": [{"$ref": "#/tokens/x"}]}, "resolutionOrder refers to #/tokens/x"),
        ({"resolutionOrder": [{"$ref": "#/sets/s"}], "sets": {"s": {}}}, "set 's' needs a list of sources"),
        (
            {"resolutionOrder": [{"$ref": "#/sets/s"}], "sets": {"s": {"sources": ["a.json"]}}},
            "set 's'[0] is not an object",
        ),
        (
            {"resolutionOrder": [{"$ref": "#/sets/s"}], "sets": {"s": {"sources": [{"$ref": 1}]}}},
            "set 's'[0].$ref is not a string",
        ),
        ({"resolutionOrder": [{"$ref": "#/sets/s"}], "sets": []}, "sets and modifiers must be objects"),
        ({"resolutionOrder": [{"$ref": "#/sets/s"}], "sets": {"s": 1}}, "set 's' is not an object"),
        (
            {"resolutionOrder": [{"$ref": "#/modifiers/m"}], "modifiers": {"m": {}}},
            "modifier 'm' needs a non-empty contexts",
        ),
        (
            {"resolutionOrder": [{"$ref": "#/modifiers/m"}], "modifiers": {"m": {"contexts": {}}}},
            "modifier 'm' needs a non-empty contexts",
        ),
        (
            {
                "resolutionOrder": [{"$ref": "#/modifiers/m"}],
                "modifiers": {"m": {"contexts": {"a": [], "b": []}, "default": "c"}},
            },
            "modifier 'm' has a default that is none of its contexts",
        ),
        (
            {
                "resolutionOrder": [{"$ref": "#/modifiers/m"}],
                "modifiers": {"m": {"contexts": {"a": [], "b": []}, "default": "a"}},
            },
            "selects no tokens",
        ),
        (
            {
                "resolutionOrder": [{"$ref": "#/sets/a"}],
                "sets": {"a": {"sources": [{"$ref": "#/sets/b"}]}, "b": {"sources": [{"$ref": "#/sets/a"}]}},
            },
            "set cycle: #/sets/a -> #/sets/b -> #/sets/a",
        ),
        (
            {"resolutionOrder": [{"$ref": "#/sets/s"}], "sets": {"s": {"sources": [{"$ref": "bad.json"}]}}},
            "bad.json: cannot be read as JSON",
        ),
        (
            {"resolutionOrder": [{"$ref": "#/sets/s"}], "sets": {"s": {"sources": [{"$ref": "latin.json"}]}}},
            "latin.json: cannot be read as JSON",
        ),
        (
            {"resolutionOrder": [{"$ref": "#/sets/s"}], "sets": {"s": {"sources": [{"$ref": "folder"}]}}},
            "folder: cannot be read as JSON",
        ),
        ({"resolutionOrder": [{"$ref": "#/sets/missing"}]}, "#/sets/missing points nowhere"),
        ({"resolutionOrder": [{"name": "inline", "type": "set", "sources": []}]}, "not a reference to a set"),
        (
            {"resolutionOrder": [{"$ref": "#/sets/s"}], "sets": {"s": {"sources": [{"$ref": "absent.json"}]}}},
            "absent.json: no such token file",
        ),
        (
            {"resolutionOrder": [{"$ref": "#/sets/s"}], "sets": {"s": {"sources": [{"$ref": "#/modifiers/m"}]}}},
            "a source may point at a set or a file, not #/modifiers/m",
        ),
        (
            {"resolutionOrder": [{"$ref": "#/sets/s"}], "sets": {"s": {"sources": [{"$ref": "list.json"}]}}},
            "list.json: not a JSON object",
        ),
    ],
)
def test_a_broken_resolver_is_refused(
    resolver_dir: WriteResolver, tmp_path: Path, resolver: dict[str, Any], message: str
) -> None:
    resolver_dir(resolver, list=[])
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    (tmp_path / "latin.json").write_bytes(b'{"x": "\xe9"}')
    (tmp_path / "folder").mkdir()
    with pytest.raises(tokens.TokenError, match=re.escape(message)):
        tokens.merged({})
