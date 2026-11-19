"""The DTCG 2025.10 token files: writing the palette's, reading all through the resolver.

The palette files hold one group per base colour: its 12 steps as colour objects
(tokens ``1`` to ``12``) and its main value, step 9, as the group's root token
(``$root``). The role files hold one token per role, each a reference to a
palette step. The resolver file (``copper.resolver.json``) selects the light or
the dark files by its ``mode`` modifier.

Reading follows the resolver module's stages: the input is checked against the
modifiers, the sources are merged in resolution order, and only then are the
references resolved. This reader covers what copper's own files use: references
within the resolver document and to token files beside it, curly-brace
references, and colours in sRGB.
"""

import json
import re
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from typing import Any

from coloraide import Color

from copper_design.palette import MODES, Palette

RESOLVER = "copper.resolver.json"
_REFERENCE = re.compile(r"^\{([^{}]+)\}$")
_HEX = re.compile(r"^#[0-9a-f]{6}$")
_ROOT = "$root"


class TokenError(ValueError):
    """A token file or the resolver breaks the format or references what is not there."""


def directory() -> Traversable:
    """The token files shipped with the package."""
    return files("copper_design").joinpath("tokens")


def palette_file(mode: str) -> str:
    return f"palette.{mode}.tokens.json"


def colour_value(hex_colour: str) -> dict[str, Any]:
    """A DTCG colour object for an sRGB ``#rrggbb``: its components to 4 places, the hex as fallback."""
    components = [round(component, 4) for component in Color(hex_colour).coords()]
    return {"colorSpace": "srgb", "components": components, "hex": hex_colour}


def palette_document(palette: Palette) -> dict[str, Any]:
    """One mode's palette as a DTCG document: a group per base colour, its main value step 9."""
    return {
        name: {
            "$type": "color",
            _ROOT: {"$value": f"{{{name}.9}}"},
            **{str(step): {"$value": colour_value(hex_colour)} for step, hex_colour in enumerate(scale, start=1)},
        }
        for name, scale in palette.items()
    }


def dump(document: dict[str, Any]) -> str:
    """A token document as the committed files spell it."""
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def _read(name: str) -> dict[str, Any]:
    try:
        document = json.loads(directory().joinpath(name).read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise TokenError(f"{name}: no such token file") from error
    if not isinstance(document, dict):
        raise TokenError(f"{name}: not a JSON object")
    return document


def _pointer(document: dict[str, Any], pointer: str) -> Any:
    node: Any = document
    for part in pointer.removeprefix("#/").split("/"):
        if not isinstance(node, dict) or part not in node:
            raise TokenError(f"{RESOLVER}: {pointer} points nowhere")
        node = node[part]
    return node


def _sources(resolver: dict[str, Any], sources: list[Any]) -> list[dict[str, Any]]:
    """Token documents from a set's or a context's sources, in order."""
    documents: list[dict[str, Any]] = []
    for source in sources:
        ref = source.get("$ref") if isinstance(source, dict) else None
        if ref is None:
            documents.append(source)
        elif ref.startswith("#/sets/"):
            documents.extend(_sources(resolver, _pointer(resolver, ref)["sources"]))
        elif ref.startswith("#/"):
            raise TokenError(f"{RESOLVER}: a source may point at a set or a file, not {ref}")
        else:
            documents.append(_read(ref))
    return documents


def _merge(into: dict[str, Any], document: dict[str, Any]) -> None:
    """Merge a token document into another: groups merge, a later token replaces an earlier one."""
    for key, value in document.items():
        old = into.get(key)
        if isinstance(value, dict) and "$value" not in value and isinstance(old, dict) and "$value" not in old:
            _merge(old, value)
        else:
            into[key] = json.loads(json.dumps(value))


def _check_inputs(modifiers: dict[str, Any], inputs: dict[str, str]) -> None:
    for name, context in inputs.items():
        if name not in modifiers:
            raise TokenError(f"unknown modifier {name!r}")
        if context not in modifiers[name]["contexts"]:
            raise TokenError(f"invalid context {context!r} for modifier {name!r}")


def _selected(resolver: dict[str, Any], item: dict[str, Any], inputs: dict[str, str]) -> list[dict[str, Any]]:
    """The token documents one resolution-order item contributes: a set's, or a modifier's selected context's."""
    ref = item.get("$ref", "")
    if ref.startswith("#/sets/"):
        return _sources(resolver, _pointer(resolver, ref)["sources"])
    if not ref.startswith("#/modifiers/"):
        raise TokenError(f"{RESOLVER}: resolutionOrder holds {item!r}, not a reference to a set or modifier")
    name = ref.removeprefix("#/modifiers/")
    modifier = _pointer(resolver, ref)
    context = inputs.get(name, modifier.get("default"))
    if context is None:
        raise TokenError(f"missing modifier {name!r}")
    return _sources(resolver, modifier["contexts"][context])


def merged(inputs: dict[str, str]) -> dict[str, Any]:
    """The token tree the resolver selects for the given inputs, references not yet resolved."""
    resolver = _read(RESOLVER)
    if resolver.get("version") != "2025.10":
        raise TokenError(f"{RESOLVER}: version must be 2025.10")
    _check_inputs(resolver.get("modifiers", {}), inputs)
    tree: dict[str, Any] = {}
    for item in resolver["resolutionOrder"]:
        for document in _selected(resolver, item, inputs):
            _merge(tree, document)
    return tree


@dataclass(frozen=True)
class Token:
    path: str
    """The token's path, dot-separated, ``$root`` included (``blue.$root``)."""
    type: str | None
    """Its own ``$type`` or its closest group's; None for a reference without one."""
    value: Any
    """Its ``$value`` as written: a value or a reference."""

    @property
    def reference(self) -> str | None:
        """The path a reference points to; None for a value."""
        match = _REFERENCE.match(self.value) if isinstance(self.value, str) else None
        return match.group(1) if match else None


def flatten(tree: dict[str, Any]) -> dict[str, Token]:
    """Every token of a tree by path, each with its type inherited from its groups."""
    tokens: dict[str, Token] = {}

    def walk(group: dict[str, Any], prefix: str, inherited: str | None) -> None:
        group_type = group.get("$type", inherited)
        for name, node in group.items():
            if name.startswith("$") and name != _ROOT:
                continue
            if not isinstance(node, dict):
                raise TokenError(f"{prefix}{name}: neither a token nor a group")
            if any(char in name for char in "{}."):
                raise TokenError(f"{prefix}{name}: a name may not hold '{{', '}}' or '.'")
            path = f"{prefix}{name}"
            if "$value" in node:
                children = [key for key in node if not key.startswith("$")]
                if children:
                    raise TokenError(f"{path}: a token cannot hold tokens or groups ({children})")
                tokens[path] = Token(path, node.get("$type", group_type), node["$value"])
            elif name == _ROOT:
                raise TokenError(f"{path}: a root token needs a $value")
            else:
                walk(node, f"{path}.", group_type)

    walk(tree, "", None)
    return tokens


def check_colour(path: str, value: Any) -> str:
    """A DTCG sRGB colour object's ``#rrggbb``; raises unless the object is valid and its hex agrees."""
    if not isinstance(value, dict) or value.get("colorSpace") != "srgb":
        raise TokenError(f"{path}: not a colour object in sRGB: {value!r}")
    components = value.get("components")
    if (
        not isinstance(components, list)
        or len(components) != 3
        or not all(isinstance(c, int | float) and 0 <= c <= 1 for c in components)
    ):
        raise TokenError(f"{path}: components must be three numbers 0-1, not {components!r}")
    unknown = set(value) - {"colorSpace", "components", "alpha", "hex"}
    if unknown:
        raise TokenError(f"{path}: unknown colour properties {sorted(unknown)}")
    alpha = value.get("alpha", 1)
    if not isinstance(alpha, int | float) or not 0 <= alpha <= 1:
        raise TokenError(f"{path}: alpha must be a number 0-1, not {alpha!r}")
    hex_colour = Color("srgb", components).to_string(hex=True)
    if "hex" in value and value["hex"] != hex_colour:
        raise TokenError(f"{path}: hex {value['hex']} does not match the components ({hex_colour})")
    if not _HEX.match(hex_colour):
        raise TokenError(f"{path}: {hex_colour} is not #rrggbb")
    return hex_colour


def resolve(tokens: dict[str, Token]) -> dict[str, Token]:
    """Every token with its reference chain followed to the value at its end.

    The result keeps each token's path and gives it the type and value of the
    token its chain ends at. A reference to a missing token, a cycle, or a chain
    that ends at a token of another type raises.
    """
    resolved: dict[str, Token] = {}

    def follow(path: str, chain: tuple[str, ...]) -> Token:
        if path in chain:
            raise TokenError(f"reference cycle: {' -> '.join((*chain, path))}")
        token = tokens.get(path)
        if token is None:
            raise TokenError(f"{chain[-1]}: refers to {{{path}}}, which is no token")
        target = token.reference
        if target is None:
            return token
        end = follow(target, (*chain, path))
        if token.type is not None and end.type != token.type:
            raise TokenError(f"{path}: a {token.type} token refers to a {end.type} token")
        return end

    for path in tokens:
        end = follow(path, ())
        resolved[path] = Token(path, end.type, end.value)
    return resolved


def colours(mode: str) -> dict[str, str]:
    """One mode's colours by the names the ports use, as ``#rrggbb``.

    A path's dots become hyphens and a root token takes its group's name:
    ``blue.9`` is ``blue-9``, ``blue.$root`` is ``blue``, the role ``bg`` is ``bg``.
    """
    if mode not in MODES:
        raise TokenError(f"no mode {mode!r}")
    result: dict[str, str] = {}
    for path, token in resolve(flatten(merged({"mode": mode}))).items():
        if token.type != "color":
            raise TokenError(f"{path}: a {token.type} token; copper holds colours only")
        result[path.removesuffix(f".{_ROOT}").replace(".", "-")] = check_colour(path, token.value)
    return result
