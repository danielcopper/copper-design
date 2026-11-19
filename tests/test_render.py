"""The committed ports and the README swatch equal what the generator renders, and the command line writes them."""

import re
from pathlib import Path

import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, PackageLoader

from copper_design import palette, render, tokens
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
    with pytest.raises(render.RenderError, match=r"^broken\.svg\.j2 \(dark\): .*no-such-role"):
        render.render(env, "broken.svg.j2", tokens.load("dark"))


def test_a_json_template_rendering_no_valid_json_is_refused() -> None:
    env = _env_with("broken.json.j2", '{"background": {{ c["bg"] }}}')
    with pytest.raises(render.RenderError, match=r"^broken\.json\.j2 \(light\) rendered no valid JSON"):
        render.render(env, "broken.json.j2", tokens.load("light"))
