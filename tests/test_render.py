"""The committed ports and the README swatch equal what the generator renders, and the command line writes them."""

import json
import re
from collections.abc import Mapping
from pathlib import Path

import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, PackageLoader

from copper_design import contrast, material, palette, preview, render, tokens
from copper_design.__main__ import main

_ROOT = Path(__file__).resolve().parents[1]


def test_the_committed_ports_and_swatch_equal_the_generator_output() -> None:
    for relative, text in render.outputs().items():
        path = _ROOT / relative
        assert path.is_file(), f"{relative} is not committed; run `mise run render`"
        assert path.read_text(encoding="utf-8") == text, f"{relative} differs from the tokens; run `mise run render`"


def test_every_file_under_ports_is_rendered() -> None:
    committed = {path.relative_to(_ROOT).as_posix() for path in (_ROOT / "ports").rglob("*") if path.is_file()}
    assert committed == {relative for relative in render.outputs() if relative.startswith("ports/")}


def test_the_herdr_port_is_the_light_and_dark_pair() -> None:
    assert {relative for relative in render.outputs() if relative.startswith("ports/herdr/")} == {
        "ports/herdr/copper-light.json",
        "ports/herdr/copper-dark.json",
    }


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_swatch_shows_each_base_colours_main_value_on_bg(mode: palette.Mode) -> None:
    svg = (_ROOT / "docs" / f"swatch-{mode}.svg").read_text(encoding="utf-8")
    loaded = tokens.load(mode)
    colours, bases = loaded.colours, list(loaded.bases)
    fills = re.findall(r'<rect [^>]*fill="(#[0-9a-f]{6})"', svg)
    assert fills == [colours["bg"]] + [colours[name] for name in bases]
    assert re.findall(r">([a-z]+)</text>", svg) == bases


def test_the_readme_embeds_the_swatch_for_light_and_dark() -> None:
    readme = (_ROOT / "README.md").read_text(encoding="utf-8")
    picture = re.search(r"<picture>(.*?)</picture>", readme, re.DOTALL)
    assert picture, "README.md has no <picture>"
    assert re.search(r'<source media="\(prefers-color-scheme: dark\)" srcset="docs/swatch-dark\.svg">', picture[1])
    assert re.search(r'<source media="\(prefers-color-scheme: light\)" srcset="docs/swatch-light\.svg">', picture[1])
    assert re.search(r'<img src="docs/swatch-light\.svg" alt="[^"]+">', picture[1])


def test_render_writes_the_ports_and_swatch_below_the_root(tmp_path: Path) -> None:
    main(["render", "--root", str(tmp_path)])
    for relative, text in render.outputs().items():
        assert (tmp_path / relative).read_text(encoding="utf-8") == text


def test_palette_writes_the_palette_tokens_below_the_root(tmp_path: Path) -> None:
    main(["palette", "--root", str(tmp_path)])
    for name, text in tokens.palette_files().items():
        assert (tmp_path / "copper_design" / "tokens" / name).read_text(encoding="utf-8") == text


def test_preview_writes_a_page_with_every_role_and_mode(tmp_path: Path) -> None:
    page = tmp_path / "preview" / "copper.html"
    main(["preview", str(page)])
    html = page.read_text(encoding="utf-8")
    assert "copper, light mode" in html
    assert "copper, dark mode" in html
    for mode in palette.MODES:
        for role in ("bg", "text-subtle", "on-accent", "info"):
            assert tokens.colours(mode)[role] in html
    assert re.search(r"on bg \(needs 3\.0\) exception", html), "the page marks no exception (border has one)"
    assert "FAILS" not in html
    # Light beside dark: both modes in one wrapping row.
    assert re.search(r"main \{ display: flex; flex-wrap: wrap; \}", html)
    assert html.count("<section ") == 2
    assert html.index("copper, light mode") < html.index("copper, dark mode")


def test_a_broken_parameter_file_ends_the_run_with_its_message(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    def broken() -> dict[str, str]:
        raise palette.ParameterError("parameters.toml: hue.blue: missing ['chroma']")

    monkeypatch.setattr(tokens, "palette_files", broken)
    with pytest.raises(SystemExit) as exit_info:
        main(["palette", "--root", str(tmp_path)])
    assert exit_info.value.code == 1
    assert capsys.readouterr().err == "error: parameters.toml: hue.blue: missing ['chroma']\n"


def _env_with(template: str, text: str) -> Environment:
    env = render.environment()
    env.loader = ChoiceLoader([DictLoader({template: text}), PackageLoader("copper_design", "templates")])
    return env


def test_a_template_naming_a_missing_colour_names_template_and_mode() -> None:
    env = _env_with("broken.svg.j2", '{{ c["no-such-role"] }}')
    with pytest.raises(render.RenderError, match=r"^broken\.svg\.j2 line 1 \(dark\): UndefinedError: .*no-such-role"):
        render.render(env, "broken.svg.j2", tokens.load("dark"))


def test_a_template_error_names_its_line() -> None:
    env = _env_with("broken.svg.j2", "<svg>\n\n{{ 1 // 0 }}")
    with pytest.raises(render.RenderError, match=r"^broken\.svg\.j2 line 3 \(dark\): ZeroDivisionError: "):
        render.render(env, "broken.svg.j2", tokens.load("dark"))


def test_a_template_error_in_a_block_names_its_line() -> None:
    env = _env_with("broken.svg.j2", "<svg>\n{% block body %}\n\n{{ 1 // 0 }}\n{% endblock %}")
    with pytest.raises(render.RenderError, match=r"^broken\.svg\.j2 line 4 \(dark\): ZeroDivisionError: "):
        render.render(env, "broken.svg.j2", tokens.load("dark"))


def test_a_template_error_in_an_included_template_names_that_template(tmp_path: Path) -> None:
    (tmp_path / "outer.svg.j2").write_text("<svg>\n{% include 'inner.svg.j2' %}\n", encoding="utf-8")
    (tmp_path / "inner.svg.j2").write_text("<g>\n\n{{ 1 // 0 }}\n", encoding="utf-8")
    env = render.environment()
    env.loader = FileSystemLoader(tmp_path)
    with pytest.raises(render.RenderError, match=r"^outer\.svg\.j2 \(in inner\.svg\.j2 line 3\) \(light\): "):
        render.render(env, "outer.svg.j2", tokens.load("light"))


def test_a_template_raising_anything_names_template_and_mode() -> None:
    env = _env_with("broken.svg.j2", "{{ 1 // 0 }}")
    # The error's type, not its text: the interpreter words the message (3.12 and 3.14 differ).
    with pytest.raises(render.RenderError, match=r"^broken\.svg\.j2 line 1 \(light\): ZeroDivisionError: ") as raised:
        render.render(env, "broken.svg.j2", tokens.load("light"))
    assert isinstance(raised.value.__cause__, ZeroDivisionError)


def test_a_json_output_that_is_no_valid_json_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    env = _env_with("broken.json.j2", '{"background": {{ c["bg"] }}}')
    monkeypatch.setattr(render, "environment", lambda: env)
    monkeypatch.setattr(render, "OUTPUTS", ((render.each_mode("x-{mode}.json"), "broken.json.j2"),))
    with pytest.raises(render.RenderError, match=r"^x-light\.json \(broken\.json\.j2\) is no valid JSON"):
        render.outputs()


def test_an_xml_output_that_is_not_well_formed_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    env = _env_with("broken.xml.j2", "<resources><color>{{ c['bg'] }}</resources>")
    monkeypatch.setattr(render, "environment", lambda: env)
    monkeypatch.setattr(render, "OUTPUTS", ((render.each_mode("x-{mode}.xml"), "broken.xml.j2"),))
    with pytest.raises(render.RenderError, match=r"^x-light\.xml \(broken\.xml\.j2\) is no well-formed XML"):
        render.outputs()


def test_a_broken_preview_template_ends_the_run_with_its_message(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    env = _env_with("preview.html.j2", "{{ modes[0].no_such_key }}")
    monkeypatch.setattr(render, "environment", lambda: env)
    with pytest.raises(SystemExit) as exit_info:
        main(["preview", str(tmp_path / "page.html")])
    assert exit_info.value.code == 1
    assert capsys.readouterr().err.startswith("error: preview.html.j2 line 1 (both modes): UndefinedError: ")


def test_autoescaping_covers_the_html_svg_and_xml_templates_only() -> None:
    autoescape = render.environment().autoescape
    assert callable(autoescape)
    assert autoescape("preview.html.j2")
    assert autoescape("swatch.svg.j2")
    assert autoescape("copper_colors.xml.j2")
    assert not autoescape("herdr.json.j2")
    assert not autoescape("CopperColors.kt.j2")


_LITERAL_CHOICE = r'\s*"[^"]*"\s+if\s+(?:(?!\belse\b)[^"])*?(?:\s+else\s+"[^"]*")?\s*'


def _not_through_tojson(text: str) -> list[str]:
    """The expressions of a JSON template that write a value without tojson.

    A value goes through tojson; a quoted literal, written under a condition
    with no ``else`` or chosen against another quoted literal (a comma between
    items), needs none. The condition ends at the word ``else``, so a value
    after it (``"x" if a else c.bg``) is caught. Expressions may span lines.
    """
    expressions = re.findall(r"\{\{(.*?)\}\}", text, re.DOTALL)
    return [
        expression
        for expression in expressions
        if not re.search(r"\|\s*tojson\s*$", expression) and not re.fullmatch(_LITERAL_CHOICE, expression)
    ]


def test_the_tojson_guard_sees_every_value() -> None:
    assert not _not_through_tojson('{{ c["bg"] | tojson }}{{ "," if not loop.last }}')
    assert not _not_through_tojson('{{ "," if not loop.last else "" }}')
    assert _not_through_tojson('{{ c["bg"] }}') == [' c["bg"] ']
    assert _not_through_tojson('{{ "x" if a else c["bg"] }}')
    assert _not_through_tojson('{{ "x" if a else c.bg }}')
    assert _not_through_tojson('{{ "x" if a else mode }}')
    assert _not_through_tojson("{{ mode }}")
    assert _not_through_tojson('{{\n  c["bg"]\n}}')


def test_the_json_templates_write_every_value_through_tojson() -> None:
    templates = Path(render.__file__).parent / "templates"
    found = list(templates.glob("*.json.j2"))
    assert found
    for template in found:
        text = template.read_text(encoding="utf-8")
        assert "{{" in text, template.name
        loose = _not_through_tojson(text)
        assert not loose, f"{template.name}: values not written through tojson: {loose}"


def _colours_by_mode() -> dict[palette.Mode, Mapping[str, str]]:
    return {mode: tokens.colours(mode) for mode in palette.MODES}


@pytest.mark.parametrize("mode", palette.MODES)
def test_the_preview_shows_colour_blindness_views_of_the_hues_and_states(mode: palette.Mode) -> None:
    loaded = tokens.load(mode)
    herdr = json.loads(render.render(render.environment(), render.HERDR_TEMPLATE, loaded))
    names = preview.mode_data(loaded, herdr, _colours_by_mode())["cvd"]["names"]
    hues = ["blue", "green", "teal", "yellow", "orange", "red", "violet"]
    assert names == [*hues, "success", "warning", "error", "info"]


def test_the_preview_shows_the_material3_scheme_in_light_and_dark(tmp_path: Path) -> None:
    page = tmp_path / "copper.html"
    main(["preview", str(page)])
    html = page.read_text(encoding="utf-8")
    assert html.count("<h2>Material 3 colour scheme</h2>") == 2
    sections = html.split("copper, dark mode")
    assert len(sections) == 2
    by_mode = _colours_by_mode()
    sources = {}
    for mode, section in zip(palette.MODES, sections, strict=True):
        scheme = material.scheme(mode, by_mode)
        swatches = re.findall(
            r'<span class="chip" style="background: (#[0-9a-f]{6});[^"]*"></span>\s*'
            r'<div><div class="mono">(\w+)</div><div class="mono"[^>]*>([^<]*)</div>',
            section,
        )
        assert [(hex_colour, role) for hex_colour, role, _ in swatches] == [
            (scheme[role], role) for role in material.ROLES
        ], mode
        sources[mode] = {role: source for _, role, source in swatches}
        pairs = re.findall(
            r'class="m3-pair[^"]*" style="background: (#[0-9a-f]{6}); color: (#[0-9a-f]{6});'
            r'[^"]*">\s*<div>(\w+)</div>\s*<div class="mono">on (\w+): ([0-9.]+)</div>',
            section,
        )
        assert pairs == [
            (scheme[fill], scheme[text], text, fill, f"{contrast.ratio(scheme[text], scheme[fill]):.2f}")
            for text, fill in material.PAIRS
        ], mode
    # A source is the copper name, after its mode where that is not the scheme's own.
    light, dark = by_mode["light"], by_mode["dark"]
    assert sources["light"]["primary"] == f"accent {light['accent']}"
    assert sources["light"]["inversePrimary"] == f"dark: accent {dark['accent']}"
    assert sources["light"]["primaryFixed"] == f"light: blue-3 {light['blue-3']}"
    assert sources["dark"]["primary"] == f"accent {dark['accent']}"
    assert sources["dark"]["inversePrimary"] == f"light: accent {light['accent']}"
    assert sources["dark"]["primaryFixed"] == f"light: blue-3 {light['blue-3']}"
    assert sources["dark"]["surfaceBright"] == f"neutral-6 {dark['neutral-6']}"
