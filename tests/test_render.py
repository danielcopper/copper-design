"""The committed ports and the README swatch equal what the generator renders, and the command line writes them."""

import re
from pathlib import Path

import pytest

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
def test_the_swatch_shows_each_base_colours_main_value_on_bg(mode: str) -> None:
    svg = (_ROOT / "docs" / f"swatch-{mode}.svg").read_text(encoding="utf-8")
    colours = tokens.colours(mode)
    bases = render.context(mode)["bases"]
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


def test_palette_writes_the_palette_tokens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tokens, "directory", lambda: tmp_path)
    main(["palette"])
    for name, text in render.palette_files().items():
        assert (tmp_path / name).read_text(encoding="utf-8") == text


def test_preview_writes_a_page_with_every_role_and_mode(tmp_path: Path) -> None:
    page = tmp_path / "preview" / "copper.html"
    main(["preview", str(page)])
    html = page.read_text(encoding="utf-8")
    assert "copper, light mode" in html
    assert "copper, dark mode" in html
    for mode in palette.MODES:
        for role in ("bg", "text-subtle", "on-accent", "info"):
            assert tokens.colours(mode)[role] in html
    assert "(fails)" in html, "the page marks no role that falls short (border does)"
