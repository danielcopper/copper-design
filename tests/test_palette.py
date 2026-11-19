"""The palette: computed from the parameter file, and the committed palette tokens equal to it."""

import copy
from typing import Any

import pytest

from copper_design import palette, render, tokens

# The approved palette's values, taken from the prototype it was chosen from:
# each base colour's step 1, its main value (step 9) and step 12, per mode.
APPROVED = {
    "light": {
        "neutral": ("#fffaf3", "#918c9e", "#464261"),
        "blue": ("#f9fcff", "#1c689e", "#014068"),
        "green": ("#f9fdf8", "#5e8755", "#284622"),
        "teal": ("#f7fdfd", "#489c9b", "#004747"),
        "yellow": ("#fffbf6", "#e5b474", "#553600"),
        "orange": ("#fffbf9", "#c17c54", "#5e2e0f"),
        "red": ("#fffafb", "#b15b72", "#632537"),
        "violet": ("#fdfbff", "#8d65b4", "#4a2d66"),
    },
    "dark": {
        "neutral": ("#14121d", "#8885a3", "#e0def4"),
        "blue": ("#0f1519", "#71b8f4", "#d0e8fe"),
        "green": ("#111511", "#94bf8a", "#daead7"),
        "teal": ("#0f1515", "#89dcdb", "#d0ebea"),
        "yellow": ("#17130e", "#f4c282", "#f3e2cc"),
        "orange": ("#18120f", "#eea67d", "#f9ded0"),
        "red": ("#191113", "#ee91a9", "#fddae1"),
        "violet": ("#151219", "#c59cef", "#ecdefc"),
    },
}


@pytest.fixture(scope="module")
def built() -> dict[str, palette.Palette]:
    return palette.build(palette.load_parameters())


def test_the_palette_has_the_approved_values(built: dict[str, palette.Palette]) -> None:
    for mode, scales in APPROVED.items():
        assert list(built[mode]) == list(scales), f"{mode}: base colours or their order differ"
        for name, (first, main, last) in scales.items():
            scale = built[mode][name]
            assert len(scale) == palette.STEPS
            assert (scale[0], scale[8], scale[11]) == (first, main, last), f"{mode} {name}"


def test_the_committed_palette_tokens_equal_the_generator_output() -> None:
    for name, text in render.palette_files().items():
        committed = tokens.directory().joinpath(name).read_text(encoding="utf-8")
        assert committed == text, f"{name} differs from the parameter file's output; run `mise run render`"


def _parameters() -> dict[str, Any]:
    return copy.deepcopy(palette.load_parameters())


def test_a_curve_without_12_values_is_refused() -> None:
    parameters = _parameters()
    parameters["curve"]["dark"]["chroma"] = parameters["curve"]["dark"]["chroma"][:11]
    with pytest.raises(ValueError, match=r"curve\.dark\.chroma: needs 12 values"):
        palette.build(parameters)


def test_a_neutral_curve_without_12_values_is_refused() -> None:
    parameters = _parameters()
    parameters["neutral"]["light"]["hue"] = [*parameters["neutral"]["light"]["hue"], 290]
    with pytest.raises(ValueError, match=r"neutral\.light\.hue: needs 12 values"):
        palette.build(parameters)


@pytest.mark.parametrize("step", ["0", "13", "nine"])
def test_a_hue_exception_outside_the_steps_is_refused(step: str) -> None:
    parameters = _parameters()
    parameters["hue"]["blue"]["light"] = {step: 0.5}
    with pytest.raises(ValueError, match=r"hue\.blue\.light: .* is not a step 1-12"):
        palette.build(parameters)


def test_a_hue_exception_moves_only_its_step(built: dict[str, palette.Palette]) -> None:
    parameters = _parameters()
    parameters["hue"]["red"]["dark"] = {"3": 0.5}
    moved = palette.build(parameters)["dark"]["red"]
    assert moved[2] != built["dark"]["red"][2]
    assert moved[:2] + moved[3:] == built["dark"]["red"][:2] + built["dark"]["red"][3:]
