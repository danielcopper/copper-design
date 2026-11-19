"""The Android port: Compose colours, Material 3 colour schemes and colour resources (issue 10, D1-D5).

CI does not compile the Kotlin (D5); these tests read the committed files
instead. ``CopperColors.kt`` and ``copper_colors.xml`` carry exactly the named
colours and roles of the tokens, per mode. ``CopperColorScheme.kt`` sets every
role of material3's ``ColorScheme`` exactly once per scheme, each to the colour
copper_design.material's table names. Every pair of copper_design.material's
PAIRS reaches 4.5:1: material3's own pairs of a colour and its ``on`` colour,
onSurface and onSurfaceVariant on every surface, the inverse pairs, the fixed
pairs, and primary, secondary, tertiary and error drawn as text on the
background, the surface and every surface container.
"""

import re
import xml.etree.ElementTree as ElementTree
from collections.abc import Mapping
from pathlib import Path

import pytest

from copper_design import material, palette, render, tokens
from copper_design.material import Role

_ROOT = Path(__file__).resolve().parents[1]
_PORT = _ROOT / "ports" / "android"
_KOTLIN = _PORT / "kotlin" / "dev" / "cupr" / "design"

# material3 1.4.0 (copper_design.material.MATERIAL3 says why that version): the
# parameters of its ColorScheme constructor and of lightColorScheme and
# darkColorScheme (commonMain/androidx/compose/material3/ColorScheme.kt).
_MATERIAL3_ROLES = [
    "primary",
    "onPrimary",
    "primaryContainer",
    "onPrimaryContainer",
    "inversePrimary",
    "secondary",
    "onSecondary",
    "secondaryContainer",
    "onSecondaryContainer",
    "tertiary",
    "onTertiary",
    "tertiaryContainer",
    "onTertiaryContainer",
    "background",
    "onBackground",
    "surface",
    "onSurface",
    "surfaceVariant",
    "onSurfaceVariant",
    "surfaceTint",
    "inverseSurface",
    "inverseOnSurface",
    "error",
    "onError",
    "errorContainer",
    "onErrorContainer",
    "outline",
    "outlineVariant",
    "scrim",
    "surfaceBright",
    "surfaceDim",
    "surfaceContainer",
    "surfaceContainerHigh",
    "surfaceContainerHighest",
    "surfaceContainerLow",
    "surfaceContainerLowest",
    "primaryFixed",
    "primaryFixedDim",
    "onPrimaryFixed",
    "onPrimaryFixedVariant",
    "secondaryFixed",
    "secondaryFixedDim",
    "onSecondaryFixed",
    "onSecondaryFixedVariant",
    "tertiaryFixed",
    "tertiaryFixedDim",
    "onTertiaryFixed",
    "onTertiaryFixedVariant",
]

_KOTLIN_COLOUR = re.compile(r"^Color\(0xFF([0-9A-F]{6})\)$")
_ANDROID_COLOUR = re.compile(r"^#FF([0-9A-F]{6})$")


def _block(text: str, opening: str) -> str:
    """The text between an opening ``...(`` and its closing parenthesis."""
    start = text.index(opening) + len(opening)
    depth = 1
    for index in range(start, len(text)):
        depth += {"(": 1, ")": -1}.get(text[index], 0)
        if depth == 0:
            return text[start:index]
    raise AssertionError(f"no closing parenthesis after {opening!r}")


def _arguments(block: str) -> list[tuple[str, str]]:
    """A Kotlin call's named arguments, one per line, in order (duplicates kept)."""
    arguments = []
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.fullmatch(r"(\w+) = (.+),", line)
        assert match, f"not one named argument per line: {line!r}"
        arguments.append((match[1], match[2]))
    return arguments


def _expected_names(mode: palette.Mode) -> list[str]:
    """The port names of one mode's tokens in their order: each base colour and its steps, then the roles."""
    loaded = tokens.load(mode)
    named = [name for base in loaded.bases for name in (base, *(f"{base}-{step}" for step in range(1, 13)))]
    return [*named, *loaded.roles]


def _by_mode() -> dict[palette.Mode, Mapping[str, str]]:
    """Both modes' colours by port name."""
    return {mode: tokens.colours(mode) for mode in palette.MODES}


def _copper_colours() -> dict[str, dict[str, str]]:
    """CopperColors.kt's values: per mode, each property and its ``#rrggbb``."""
    text = (_KOTLIN / "CopperColors.kt").read_text(encoding="utf-8")
    result: dict[str, dict[str, str]] = {}
    for mode in palette.MODES:
        body = re.search(
            rf"^    private object {mode.capitalize()} : CopperColors\(\) \{{\n(.*?)^    \}}$", text, re.M | re.S
        )
        assert body, f"no object for {mode} mode"
        overrides = []
        for line in body[1].splitlines():
            match = re.fullmatch(r"        override val (\w+) = (.+)", line)
            assert match, f"{mode}: not one override per line: {line!r}"
            overrides.append((match[1], match[2]))
        assert len({name for name, _ in overrides}) == len(overrides), f"{mode}: a colour named twice"
        values: dict[str, str] = {}
        for name, value in overrides:
            match = _KOTLIN_COLOUR.match(value)
            assert match, f"{mode}.{name}: {value} is no opaque Compose colour"
            values[name] = f"#{match[1].lower()}"
        result[mode] = values
    return result


def test_the_android_port_is_the_kotlin_and_the_resources_for_light_and_dark() -> None:
    assert {relative for relative in render.outputs() if relative.startswith("ports/android/")} == {
        "ports/android/kotlin/dev/cupr/design/CopperColors.kt",
        "ports/android/kotlin/dev/cupr/design/CopperColorScheme.kt",
        "ports/android/res/values/copper_colors.xml",
        "ports/android/res/values-night/copper_colors.xml",
    }


def test_the_kotlin_files_are_in_the_package_dev_cupr_design() -> None:
    for name in ("CopperColors.kt", "CopperColorScheme.kt"):
        text = (_KOTLIN / name).read_text(encoding="utf-8")
        assert re.search(r"^package dev\.cupr\.design$", text, re.MULTILINE), name


def test_copper_colors_declares_every_colour_it_sets() -> None:
    text = (_KOTLIN / "CopperColors.kt").read_text(encoding="utf-8")
    declared = re.findall(r"^    abstract val (\w+): Color$", text, re.MULTILINE)
    assert len(declared) == len(set(declared))
    for mode, values in _copper_colours().items():
        assert list(values) == declared, mode


def test_copper_colors_light_and_dark_are_the_modes_objects() -> None:
    text = (_KOTLIN / "CopperColors.kt").read_text(encoding="utf-8")
    companion = re.findall(r"^        val (\w+): CopperColors get\(\) = (\w+)$", text, re.MULTILINE)
    assert companion == [(mode, mode.capitalize()) for mode in palette.MODES]


@pytest.mark.parametrize("mode", palette.MODES)
def test_copper_colors_carries_exactly_the_named_colours_and_roles(mode: palette.Mode) -> None:
    colours = tokens.colours(mode)
    expected = {render.kotlin_name(name): colours[name] for name in _expected_names(mode)}
    assert _copper_colours()[mode] == expected


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_resources_carry_exactly_the_named_colours_and_roles(mode: palette.Mode) -> None:
    path = _PORT / "res" / render.ANDROID_VALUES[mode] / "copper_colors.xml"
    root = ElementTree.parse(path).getroot()
    assert root.tag == "resources"
    entries = list(root)
    assert all(entry.tag == "color" and set(entry.attrib) == {"name"} for entry in entries)
    values: dict[str, str] = {}
    for entry in entries:
        name, value = entry.attrib["name"], entry.text or ""
        assert name not in values, f"{mode}: {name} twice"
        match = _ANDROID_COLOUR.match(value)
        assert match, f"{mode}: {name} = {value!r} is no opaque #FFRRGGBB"
        values[name] = f"#{match[1].lower()}"
    colours = tokens.colours(mode)
    expected = {f"copper_{name.replace('-', '_')}": colours[name] for name in _expected_names(mode)}
    assert values == expected


def test_the_resources_are_light_in_values_and_dark_in_values_night() -> None:
    assert render.ANDROID_VALUES == {"light": "values", "dark": "values-night"}


def test_the_role_list_is_material3s() -> None:
    assert list(material.ROLES) == _MATERIAL3_ROLES
    assert material.MATERIAL3 == "1.4.0"
    assert list(material.SCHEME) == sorted(material.SCHEME, key=_MATERIAL3_ROLES.index)
    assert set(material.SCHEME) == set(_MATERIAL3_ROLES)


def _schemes() -> dict[str, list[tuple[str, str]]]:
    text = (_KOTLIN / "CopperColorScheme.kt").read_text(encoding="utf-8")
    return {mode: _arguments(_block(text, f"{mode}ColorScheme(")) for mode in palette.MODES}


@pytest.mark.parametrize("mode", palette.MODES)
def test_each_scheme_sets_every_material3_role_exactly_once(mode: palette.Mode) -> None:
    roles = [role for role, _ in _schemes()[mode]]
    twice = sorted({role for role in roles if roles.count(role) > 1})
    assert not twice, f"{mode}: set more than once: {twice}"
    missing = [role for role in _MATERIAL3_ROLES if role not in roles]
    assert not missing, f"{mode}: not set: {missing}"
    unknown = sorted(set(roles) - set(_MATERIAL3_ROLES))
    assert not unknown, f"{mode}: no role of material3 {material.MATERIAL3}: {unknown}"


@pytest.mark.parametrize("mode", palette.MODES)
def test_each_scheme_role_is_the_colour_the_mapping_names(mode: palette.Mode) -> None:
    colours = _copper_colours()
    by_mode = _by_mode()
    arguments = _schemes()[mode]
    assert [name for name, _ in arguments] == list(material.ROLES)
    for (name, value), role in zip(arguments, material.ROLES, strict=True):
        match = re.fullmatch(r"CopperColors\.(light|dark)\.(\w+)", value)
        assert match, f"{mode}: {name} = {value} is no copper colour"
        resolved = material.resolve(role, mode, by_mode)
        assert (match[1], match[2]) == (resolved.mode, render.kotlin_name(resolved.name)), role
        assert colours[match[1]][match[2]] == resolved.hex, role


def test_the_ports_spell_names_and_colours_as_kotlin_and_android_do() -> None:
    assert [render.kotlin_name(name) for name in ("bg-alt", "blue-9", "on-accent", "neutral")] == [
        "bgAlt",
        "blue9",
        "onAccent",
        "neutral",
    ]
    assert [render.android_name(name) for name in ("bg-alt", "blue-9", "on-accent")] == [
        "copper_bg_alt",
        "copper_blue_9",
        "copper_on_accent",
    ]
    assert render.kotlin_colour("#1c689e") == "Color(0xFF1C689E)"
    assert render.android_colour("#1c689e") == "#FF1C689E"
    colours = (_KOTLIN / "CopperColors.kt").read_text(encoding="utf-8")
    on_accent = tokens.colours("light")["on-accent"][1:].upper()
    assert f"        override val onAccent = Color(0xFF{on_accent})\n" in colours
    assert "        override val bgAlt = Color(0xFF" in colours
    schemes = (_KOTLIN / "CopperColorScheme.kt").read_text(encoding="utf-8")
    assert "            onSurfaceVariant = CopperColors.light.textMuted,\n" in schemes
    assert "            inversePrimary = CopperColors.dark.accent,\n" in schemes
    resources = (_PORT / "res" / "values" / "copper_colors.xml").read_text(encoding="utf-8")
    bg_alt = tokens.colours("light")["bg-alt"][1:].upper()
    assert f'    <color name="copper_bg_alt">#FF{bg_alt}</color>\n' in resources


def test_a_source_that_names_no_colour_is_refused_with_role_mode_and_value(monkeypatch: pytest.MonkeyPatch) -> None:
    by_mode = _by_mode()
    primary = material.SCHEME["primary"]
    monkeypatch.setitem(material.SCHEME, "primary", material.Row(material.Source("acent"), material.Source("accent")))
    with pytest.raises(ValueError, match=r"^primary \(light\): 'acent' names no light colour$"):
        material.scheme("light", by_mode)
    # The Kotlin template's context resolves too, so a render ends with the message, not with broken Kotlin.
    with pytest.raises(ValueError, match=r"^primary \(light\): 'acent' names no light colour$"):
        render.outputs()
    monkeypatch.setitem(material.SCHEME, "primary", primary)
    monkeypatch.setitem(
        material.SCHEME, "scrim", material.Row(material.Source("bg"), material.Source.parse("light:blue-13"))
    )
    with pytest.raises(ValueError, match=r"^scrim \(dark\): 'light:blue-13' names no light colour$"):
        material.template_context(by_mode)


def test_a_source_that_names_no_mode_is_refused() -> None:
    with pytest.raises(ValueError, match=r"^'dusk:accent' names no mode$"):
        material.Source.parse("dusk:accent")
    assert material.Source.parse("dark:accent") == material.Source("accent", "dark")
    assert material.Source.parse("blue-4") == material.Source("blue-4", None)
    assert str(material.Source("accent", "dark")) == "dark:accent"


def test_the_fixed_roles_and_the_scrim_are_the_same_in_both_modes() -> None:
    by_mode = _by_mode()
    light, dark = (material.scheme(mode, by_mode) for mode in palette.MODES)
    fixed: list[Role] = [*(role for role in material.ROLES if "Fixed" in role), "scrim"]
    assert len(fixed) == 13
    assert {role: light[role] for role in fixed} == {role: dark[role] for role in fixed}


def test_the_inverse_roles_are_the_other_modes() -> None:
    by_mode = _by_mode()
    for mode, other in zip(palette.MODES, reversed(palette.MODES), strict=True):
        scheme = material.scheme(mode, by_mode)
        assert scheme["inverseSurface"] == by_mode[other]["surface"]
        assert scheme["inverseOnSurface"] == by_mode[other]["text"]
        assert scheme["inversePrimary"] == by_mode[other]["accent"]


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_surface_containers_run_in_materials_order(mode: palette.Mode) -> None:
    # Lowest to Highest: lighter to darker in light mode, darker to lighter in
    # dark mode, as Material's tones run; light mode's High and Highest share
    # step 4 (copper_design.material says why).
    containers: list[Role] = [
        "surfaceContainerLowest",
        "surfaceContainerLow",
        "surfaceContainer",
        "surfaceContainerHigh",
        "surfaceContainerHighest",
    ]
    steps = [material.SCHEME[role].of(mode) for role in containers]
    assert steps == [
        material.Source(f"neutral-{step}") for step in ([1, 2, 3, 4, 4] if mode == "light" else [1, 2, 3, 4, 5])
    ]
    assert material.SCHEME["surface"].of(mode) == material.SCHEME["background"].of(mode) == material.Source("bg")


def test_the_colour_roles_take_the_step_that_reads_as_text_on_every_container() -> None:
    # copper_design.material says why: the first step from 9 that reaches 4.5:1
    # as a fill under step 1 and as text on surface Highest.
    colour_roles: list[Role] = ["primary", "secondary", "tertiary", "error"]
    light = [str(material.SCHEME[role].light) for role in colour_roles]
    dark = [str(material.SCHEME[role].dark) for role in colour_roles]
    assert light == ["accent", "neutral-11", "violet-11", "red-11"]
    assert dark == ["accent", "neutral-10", "violet-9", "error"]


def test_every_pair_is_measured_where_material_pairs_it() -> None:
    pairs = set(material.PAIRS)
    # material3's contentColorFor: each colour and the text it gives for it.
    content_colour_for = {
        "primary": "onPrimary",
        "secondary": "onSecondary",
        "tertiary": "onTertiary",
        "background": "onBackground",
        "error": "onError",
        "primaryContainer": "onPrimaryContainer",
        "secondaryContainer": "onSecondaryContainer",
        "tertiaryContainer": "onTertiaryContainer",
        "errorContainer": "onErrorContainer",
        "inverseSurface": "inverseOnSurface",
        "surface": "onSurface",
        "surfaceVariant": "onSurfaceVariant",
        "surfaceBright": "onSurface",
        "surfaceContainer": "onSurface",
        "surfaceContainerHigh": "onSurface",
        "surfaceContainerHighest": "onSurface",
        "surfaceContainerLow": "onSurface",
        "surfaceContainerLowest": "onSurface",
        "surfaceDim": "onSurface",
        "primaryFixed": "onPrimaryFixed",
        "primaryFixedDim": "onPrimaryFixed",
        "secondaryFixed": "onSecondaryFixed",
        "secondaryFixedDim": "onSecondaryFixed",
        "tertiaryFixed": "onTertiaryFixed",
        "tertiaryFixedDim": "onTertiaryFixed",
    }
    missing = {(text, fill) for fill, text in content_colour_for.items()} - pairs
    assert not missing, missing
    # onSurface and onSurfaceVariant on every surface and container, the
    # snackbar's action, and each fixed role's variant text on its fixed colours.
    surfaces = [role for role in material.ROLES if role.startswith("surface") and role != "surfaceTint"]
    assert len(surfaces) == 9
    assert {(text, fill) for text in ("onSurface", "onSurfaceVariant") for fill in surfaces} <= pairs
    assert ("inversePrimary", "inverseSurface") in pairs
    # The colour roles as text on the background, the surface and every
    # container: a text field's error text, a selected tab or a text button's
    # label, a selected navigation label.
    grounds = ["background", "surface", *(role for role in surfaces if role.startswith("surfaceContainer"))]
    assert len(grounds) == 7
    for colour in ("primary", "secondary", "tertiary", "error"):
        assert {(colour, ground) for ground in grounds} <= pairs, colour
    for family in ("primary", "secondary", "tertiary"):
        variant = f"on{family.capitalize()}FixedVariant"
        assert {(variant, f"{family}Fixed"), (variant, f"{family}FixedDim")} <= pairs
    assert len(pairs) == len(material.PAIRS)


@pytest.mark.parametrize("mode", palette.MODES)
def test_every_pair_of_a_colour_and_the_text_on_it_in_pairs_reaches_4_5_to_1(mode: palette.Mode) -> None:
    by_mode = _by_mode()
    checks = material.checks(material.scheme(mode, by_mode))
    assert len(checks) == len(material.PAIRS)
    assert {check.need for check in checks} == {4.5}
    short = [f"{c.foreground} on {c.background}: {c.ratio:.2f}:1" for c in checks if not c.passes]
    assert not short, f"{mode}: {short}"
