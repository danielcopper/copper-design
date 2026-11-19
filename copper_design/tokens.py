"""The DTCG 2025.10 token files: writing the palette's, reading all through the resolver.

The palette files hold one group per base colour: its 12 steps as colour objects
(tokens ``1`` to ``12``) and its main value, step 9, as the group's root token
(``$root``). The role files hold one token per role, each a reference to a
palette step. The resolver file (``copper.resolver.json``) selects the light or
the dark files by its ``mode`` modifier.

Reading follows the resolver module's stages: the input is checked against the
modifiers, the sources are merged in resolution order, and only then are the
references resolved. The reader takes the resolver module's sets, inline
sources and modifier defaults as well, which copper's own resolver does not
use, so a resolver that layers other token files under or over copper's reads
with it too. It takes references within the resolver document and to token
files beside it, curly-brace references, and opaque colours in sRGB.

Everything it reads is checked, and anything it does not understand raises a
TokenError naming the file or the token's path: an unknown ``$`` property, an
empty group, a token and a group of one name, two paths that the ports would
spell alike.
"""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from typing import Any

from coloraide import Color

from copper_design.palette import MAIN_STEP, MODES, Mode, Palette, build, load_parameters

RESOLVER = "copper.resolver.json"
_REFERENCE = re.compile(r"^\{([^{}]+)\}$")
_HEX = re.compile(r"^#[0-9a-f]{6}$")
_HEX_FALLBACK = re.compile(r"^#[0-9a-fA-F]{6}$")
_ROOT = "$root"
_COMMON_KEYS = {"$type", "$description", "$extensions", "$deprecated"}
_TOKEN_KEYS = {"$value", *_COMMON_KEYS}
_GROUP_KEYS = _COMMON_KEYS


class TokenError(ValueError):
    """A token file or the resolver breaks the format or references what is not there."""


def directory() -> Traversable:
    """The token files shipped with the package."""
    return files("copper_design").joinpath("tokens")


def palette_file(mode: Mode) -> str:
    return f"palette.{mode}.tokens.json"


def colour_value(hex_colour: str) -> dict[str, Any]:
    """A DTCG colour object for an sRGB ``#rrggbb``: its components to 4 places, the hex as fallback."""
    if not _HEX.match(hex_colour):
        raise TokenError(f"{hex_colour!r} is not a lowercase #rrggbb")
    components = [round(component, 4) for component in Color(hex_colour).coords()]
    return {"colorSpace": "srgb", "components": components, "hex": hex_colour}


def palette_document(palette: Palette) -> dict[str, Any]:
    """One mode's palette as a DTCG document: a group per base colour, its main value its root token."""
    return {
        name: {
            "$type": "color",
            _ROOT: {"$value": f"{{{name}.{MAIN_STEP}}}"},
            **{str(step): {"$value": colour_value(hex_colour)} for step, hex_colour in enumerate(scale, start=1)},
        }
        for name, scale in palette.items()
    }


def dump(document: dict[str, Any]) -> str:
    """A token document as the committed files spell it."""
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def palette_files() -> dict[str, str]:
    """The palette token files written from the parameter file, by file name."""
    palettes = build(load_parameters())
    return {palette_file(mode): dump(palette_document(palettes[mode])) for mode in MODES}


def _read(name: str) -> dict[str, Any]:
    try:
        document = json.loads(directory().joinpath(name).read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise TokenError(f"{name}: no such token file") from error
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TokenError(f"{name}: cannot be read as JSON: {error}") from error
    if not isinstance(document, dict):
        raise TokenError(f"{name}: not a JSON object")
    return document


def _check_sources(sources: object, where: str) -> None:
    if not isinstance(sources, list):
        raise TokenError(f"{RESOLVER}: {where} needs a list of sources")
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise TokenError(f"{RESOLVER}: {where}[{index}] is not an object")
        if "$ref" in source and not isinstance(source["$ref"], str):
            raise TokenError(f"{RESOLVER}: {where}[{index}].$ref is not a string")


def _check_resolver(resolver: dict[str, Any]) -> None:
    """The resolver document's shape: version, sets, modifiers and resolution order."""
    if resolver.get("version") != "2025.10":
        raise TokenError(f"{RESOLVER}: version must be 2025.10")
    sets = resolver.get("sets", {})
    modifiers = resolver.get("modifiers", {})
    if not isinstance(sets, dict) or not isinstance(modifiers, dict):
        raise TokenError(f"{RESOLVER}: sets and modifiers must be objects")
    for name, body in sets.items():
        if not isinstance(body, dict):
            raise TokenError(f"{RESOLVER}: set {name!r} is not an object")
        _check_sources(body.get("sources"), f"set {name!r}")
    for name, body in modifiers.items():
        contexts = body.get("contexts") if isinstance(body, dict) else None
        if not isinstance(contexts, dict) or not contexts:
            raise TokenError(f"{RESOLVER}: modifier {name!r} needs a non-empty contexts object")
        for context, sources in contexts.items():
            _check_sources(sources, f"modifier {name!r} context {context!r}")
        if "default" in body and body["default"] not in contexts:
            raise TokenError(f"{RESOLVER}: modifier {name!r} has a default that is none of its contexts")
    order = resolver.get("resolutionOrder")
    if not isinstance(order, list) or not order:
        raise TokenError(f"{RESOLVER}: resolutionOrder needs a non-empty list")
    for index, item in enumerate(order):
        if not isinstance(item, dict) or not isinstance(item.get("$ref"), str):
            raise TokenError(f"{RESOLVER}: resolutionOrder[{index}] is not a reference to a set or modifier")


def _pointer(document: dict[str, Any], pointer: str) -> Any:
    node: Any = document
    for part in pointer.removeprefix("#/").split("/"):
        if not isinstance(node, dict) or part not in node:
            raise TokenError(f"{RESOLVER}: {pointer} points nowhere")
        node = node[part]
    return node


def _sources(resolver: dict[str, Any], sources: list[Any], sets: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    """Token documents from a set's or a context's sources, in order; ``sets`` are the sets being expanded."""
    documents: list[dict[str, Any]] = []
    for source in sources:
        ref = source.get("$ref")
        if ref is None:
            documents.append(source)
        elif ref.startswith("#/sets/"):
            if ref in sets:
                raise TokenError(f"{RESOLVER}: set cycle: {' -> '.join((*sets, ref))}")
            documents.extend(_sources(resolver, _pointer(resolver, ref)["sources"], (*sets, ref)))
        elif ref.startswith("#/"):
            raise TokenError(f"{RESOLVER}: a source may point at a set or a file, not {ref}")
        else:
            documents.append(_read(ref))
    return documents


def _is_token(node: object) -> bool:
    return isinstance(node, dict) and "$value" in node


def _merge(into: dict[str, Any], document: dict[str, Any], prefix: str = "") -> None:
    """Merge a token document into another: groups merge, a later token replaces an earlier one.

    A token and a group of the same name do not merge: one would silently drop
    the other, so that raises.
    """
    for key, value in document.items():
        old = into.get(key)
        if old is None or (key.startswith("$") and key != _ROOT):
            into[key] = json.loads(json.dumps(value))
        elif _is_token(old) != _is_token(value):
            raise TokenError(f"{prefix}{key}: a token and a group of the same name")
        elif _is_token(value) or not isinstance(value, dict) or not isinstance(old, dict):
            into[key] = json.loads(json.dumps(value))
        else:
            _merge(old, value, f"{prefix}{key}.")


def _check_inputs(modifiers: dict[str, Any], inputs: Mapping[str, object]) -> None:
    """The input names declared modifiers and one of their contexts, as a string (the resolver module's rules)."""
    for name, context in inputs.items():
        if name not in modifiers:
            raise TokenError(f"unknown modifier {name!r}")
        if not isinstance(context, str):
            raise TokenError(f"input for modifier {name!r} must be a string, not {context!r}")
        if context not in modifiers[name]["contexts"]:
            raise TokenError(f"invalid context {context!r} for modifier {name!r}")


def _selected(resolver: dict[str, Any], ref: str, inputs: dict[str, str]) -> list[dict[str, Any]]:
    """The token documents one resolution-order item contributes: a set's, or a modifier's selected context's."""
    if ref.startswith("#/sets/"):
        return _sources(resolver, _pointer(resolver, ref)["sources"], (ref,))
    if not ref.startswith("#/modifiers/"):
        raise TokenError(f"{RESOLVER}: resolutionOrder refers to {ref}, not to a set or modifier")
    name = ref.removeprefix("#/modifiers/")
    modifier = _pointer(resolver, ref)
    context = inputs.get(name, modifier.get("default"))
    if context is None:
        raise TokenError(f"no input for modifier {name!r}, which has no default")
    return _sources(resolver, modifier["contexts"][context])


def merged(inputs: dict[str, str]) -> dict[str, Any]:
    """The token tree the resolver selects for the given inputs, references not yet resolved."""
    resolver = _read(RESOLVER)
    _check_resolver(resolver)
    _check_inputs(resolver.get("modifiers", {}), inputs)
    tree: dict[str, Any] = {}
    for item in resolver["resolutionOrder"]:
        for document in _selected(resolver, item["$ref"], inputs):
            _merge(tree, document)
    if not tree:
        raise TokenError(f"{RESOLVER}: selects no tokens for {inputs}")
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


def _own_type(node: dict[str, Any], where: str, inherited: str | None) -> str | None:
    value = node.get("$type", inherited)
    if value is not None and not isinstance(value, str):
        raise TokenError(f"{where}: $type must be a string, not {value!r}")
    return value


def flatten(tree: dict[str, Any]) -> dict[str, Token]:
    """Every token of a tree by path, each with its type inherited from its groups."""
    tokens: dict[str, Token] = {}

    def token(node: dict[str, Any], path: str, group_type: str | None) -> None:
        unknown = sorted(set(node) - _TOKEN_KEYS)
        if unknown:
            raise TokenError(f"{path}: a token cannot hold {unknown}")
        tokens[path] = Token(path, _own_type(node, path, group_type), node["$value"])

    def walk(group: dict[str, Any], prefix: str, inherited: str | None) -> None:
        where = prefix.removesuffix(".") or "the token tree"
        group_type = _own_type(group, where, inherited)
        unknown = sorted(key for key in group if key.startswith("$") and key not in _GROUP_KEYS | {_ROOT})
        if unknown:
            raise TokenError(f"{where}: unknown group properties {unknown}")
        children = [name for name in group if not name.startswith("$") or name == _ROOT]
        if not children:
            raise TokenError(f"{where}: an empty group")
        for name in children:
            node = group[name]
            path = f"{prefix}{name}"
            if not isinstance(node, dict):
                raise TokenError(f"{path}: neither a token nor a group")
            if any(char in name for char in "{}."):
                raise TokenError(f"{path}: a name may not hold '{{', '}}' or '.'")
            if "$value" in node:
                token(node, path, group_type)
            elif name == _ROOT:
                raise TokenError(f"{path}: a root token needs a $value")
            else:
                walk(node, f"{path}.", group_type)

    walk(tree, "", None)
    return tokens


def check_colour(path: str, value: Any) -> str:
    """An opaque DTCG sRGB colour object's ``#rrggbb``; raises unless it is valid and its hex agrees."""
    if not isinstance(value, dict) or value.get("colorSpace") != "srgb":
        raise TokenError(f"{path}: not a colour object in sRGB: {value!r}")
    unknown = set(value) - {"colorSpace", "components", "alpha", "hex"}
    if unknown:
        raise TokenError(f"{path}: unknown colour properties {sorted(unknown)}")
    components = value.get("components")
    if (
        not isinstance(components, list)
        or len(components) != 3
        or not all(isinstance(c, int | float) and not isinstance(c, bool) and 0 <= c <= 1 for c in components)
    ):
        raise TokenError(f"{path}: components must be three numbers 0-1, not {components!r}")
    alpha = value.get("alpha", 1)
    if isinstance(alpha, bool) or alpha != 1:
        raise TokenError(f"{path}: alpha must be 1, not {alpha!r}: the ports take opaque colours")
    hex_colour = Color("srgb", components).to_string(hex=True)
    fallback = value.get("hex", hex_colour)
    if not isinstance(fallback, str) or not _HEX_FALLBACK.match(fallback):
        raise TokenError(f"{path}: hex {fallback!r} is not #rrggbb")
    if fallback.lower() != hex_colour:
        raise TokenError(f"{path}: hex {fallback} does not match the components ({hex_colour})")
    return hex_colour


def resolve(tokens: dict[str, Token]) -> dict[str, Token]:
    """Every token with its reference chain followed to the value at its end.

    The result keeps each token's path and gives it the type and value of the
    token its chain ends at. A reference to a missing token or a cycle raises.
    A token that states its type (its own or a group's) must end at a token of
    that type; one that states none, such as a role, takes the type it ends at.
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


def port_name(path: str) -> str:
    """The name the ports use for a token path: ``blue.9`` is ``blue-9``, ``blue.$root`` is ``blue``."""
    return path.removesuffix(f".{_ROOT}").replace(".", "-")


@dataclass(frozen=True)
class ModeTokens:
    """One mode's tokens, resolved."""

    mode: Mode
    colours: dict[str, str]
    """Every colour by its port name, as ``#rrggbb``."""
    bases: tuple[str, ...]
    """The base colours (the palette's groups), in palette order, the neutral first."""
    roles: dict[str, str]
    """Every role (a top-level token) and the path it refers to."""


def load(mode: Mode) -> ModeTokens:
    """One mode's tokens, as the resolver selects and resolves them."""
    tree = merged({"mode": mode})
    flat = flatten(tree)
    colours: dict[str, str] = {}
    paths: dict[str, str] = {}
    for path, token in resolve(flat).items():
        if token.type != "color":
            kind = "an untyped" if token.type is None else f"a {token.type}"
            raise TokenError(f"{path}: {kind} token; copper holds colours only")
        name = port_name(path)
        if name in paths:
            raise TokenError(f"{paths[name]} and {path} are both {name!r} in the ports")
        paths[name] = path
        colours[name] = check_colour(path, token.value)
    bases = tuple(name for name, node in tree.items() if not _is_token(node))
    roles = {name: flat[name].reference or "" for name, node in tree.items() if _is_token(node)}
    return ModeTokens(mode, colours, bases, roles)


def colours(mode: Mode) -> dict[str, str]:
    """One mode's colours by the names the ports use, as ``#rrggbb``."""
    return load(mode).colours
