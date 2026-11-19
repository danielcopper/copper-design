"""The DTCG 2025.10 token files: writing the palette's, reading all through the resolver.

The palette files hold one group per base colour: its 12 steps as colour objects
(tokens ``1`` to ``12``) and its main value, step 9, as the group's root token
(``$root``). The role files hold one token per role, each a reference to a
palette step. The resolver file (``copper.resolver.json``) selects the light or
the dark files by its ``mode`` modifier.

Reading follows the resolver module's stages: the input is checked against the
modifier, the selected context's files are merged in order, and only then are
the references resolved. The reader takes what copper's resolver uses and
refuses the rest of the resolver module: one modifier whose contexts list token
files beside the resolver, and a resolution order that is that modifier. Token
values are opaque colours in sRGB or curly-brace references.

Everything it reads is checked, and anything it does not understand raises a
TokenError naming the file or the token's path: an unknown ``$`` property, an
empty group, a name the ports cannot carry, a token and a group of one name,
two paths that the ports would spell alike.
"""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from typing import Any

from coloraide import Color

from copper_design.palette import MAIN_STEP, MODES, NEUTRAL, Mode, Palette, build, load_parameters

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


_RESOLVER_KEYS = {"$schema", "name", "version", "description", "modifiers", "resolutionOrder"}
_FILE = re.compile(r"^[A-Za-z0-9_.-]+\.json$")


def _context_files(context: str, sources: object) -> list[str]:
    """A context's token files: a non-empty list of ``{"$ref": "<file>.json"}`` beside the resolver."""
    files: list[str] = []
    for source in sources if isinstance(sources, list) else [None]:
        ref = source.get("$ref") if isinstance(source, dict) and set(source) == {"$ref"} else None
        if not isinstance(ref, str) or not _FILE.match(ref):
            raise TokenError(f"{RESOLVER}: context {context!r} needs a list of token files, not {source!r}")
        files.append(ref)
    if not files:
        raise TokenError(f"{RESOLVER}: context {context!r} lists no token files")
    return files


def _resolver() -> tuple[str, dict[str, list[str]]]:
    """The resolver's one modifier: its name and each context's token files, in order."""
    resolver = _read(RESOLVER)
    unknown = sorted(set(resolver) - _RESOLVER_KEYS)
    if unknown:
        raise TokenError(f"{RESOLVER}: copper's resolver holds no {unknown}")
    if resolver.get("version") != "2025.10":
        raise TokenError(f"{RESOLVER}: version must be 2025.10")
    modifiers = resolver.get("modifiers")
    if not isinstance(modifiers, dict) or len(modifiers) != 1:
        raise TokenError(f"{RESOLVER}: needs exactly one modifier")
    ((name, modifier),) = modifiers.items()
    if not isinstance(modifier, dict) or set(modifier) - {"description", "contexts"}:
        raise TokenError(f"{RESOLVER}: modifier {name!r} holds only a description and its contexts")
    contexts = modifier.get("contexts")
    if not isinstance(contexts, dict) or not contexts:
        raise TokenError(f"{RESOLVER}: modifier {name!r} needs a non-empty contexts object")
    files_by_context = {context: _context_files(context, sources) for context, sources in contexts.items()}
    if resolver.get("resolutionOrder") != [{"$ref": f"#/modifiers/{name}"}]:
        raise TokenError(f"{RESOLVER}: resolutionOrder must be the one modifier, #/modifiers/{name}")
    return name, files_by_context


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


def merged(inputs: Mapping[str, object]) -> dict[str, Any]:
    """The token tree the resolver selects for the given input, references not yet resolved."""
    name, contexts = _resolver()
    unknown = sorted(set(inputs) - {name})
    if unknown:
        raise TokenError(f"unknown modifier {unknown[0]!r}")
    if name not in inputs:
        raise TokenError(f"no input for modifier {name!r}")
    context = inputs[name]
    if not isinstance(context, str):
        raise TokenError(f"input for modifier {name!r} must be a string, not {context!r}")
    if context not in contexts:
        raise TokenError(f"invalid context {context!r} for modifier {name!r}")
    tree: dict[str, Any] = {}
    for file in contexts[context]:
        _merge(tree, _read(file))
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


_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
"""copper's token and group names: lowercase letters and digits, words joined by hyphens, as the ports spell them."""

_PROPERTY_TYPES: dict[str, tuple[type, ...]] = {
    "$description": (str,),
    "$extensions": (dict,),
    "$deprecated": (bool, str),
}


def _check_properties(node: dict[str, Any], where: str) -> None:
    for key, kinds in _PROPERTY_TYPES.items():
        if key in node and not isinstance(node[key], kinds):
            raise TokenError(f"{where}: {key} must be {' or '.join(kind.__name__ for kind in kinds)}")


def flatten(tree: dict[str, Any]) -> dict[str, Token]:
    """Every token of a tree by path, each with its type inherited from its groups."""
    tokens: dict[str, Token] = {}

    def token(node: dict[str, Any], path: str, group_type: str | None) -> None:
        unknown = sorted(set(node) - _TOKEN_KEYS)
        if unknown:
            raise TokenError(f"{path}: a token cannot hold {unknown}")
        _check_properties(node, path)
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
        _check_properties(group, where)
        for name in children:
            node = group[name]
            path = f"{prefix}{name}"
            if not isinstance(node, dict):
                raise TokenError(f"{path}: neither a token nor a group")
            if name == _ROOT and not prefix:
                raise TokenError(f"{path}: a root token belongs in a group")
            if name != _ROOT and not _NAME.match(name):
                raise TokenError(f"{path!r}: a name is lowercase letters and digits, words joined by hyphens")
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
    colours: Mapping[str, str]
    """Every colour by its port name, as ``#rrggbb``."""
    bases: tuple[str, ...]
    """The base colours (the palette's groups), in palette order, the neutral first."""
    roles: Mapping[str, str]
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
    if not bases or bases[0] != NEUTRAL:
        raise TokenError(f"the palette must start with the {NEUTRAL}, not {bases[:1]}")
    roles: dict[str, str] = {}
    for name, node in tree.items():
        if _is_token(node):
            reference = flat[name].reference
            if reference is None:
                raise TokenError(f"{name}: a role is a reference to a palette step, not {node['$value']!r}")
            roles[name] = reference
    return ModeTokens(mode, colours, bases, roles)


def colours(mode: Mode) -> Mapping[str, str]:
    """One mode's colours by the names the ports use, as ``#rrggbb``."""
    return load(mode).colours
