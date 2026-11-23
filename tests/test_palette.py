"""The palette: computed from the parameter file, checked against its schema, and the committed tokens equal to it."""

import re
import tomllib
from importlib.resources import files
from pathlib import Path
from typing import Any

import pytest

from copper_design import palette, tokens

# The approved palette, all 12 steps of every base colour per mode. It is the
# prototype's palette it was chosen from, with one deliberate change: light
# neutral step 10 is #6b677e; parameters.toml says why.
APPROVED: dict[palette.Mode, dict[str, tuple[str, ...]]] = {
    "light": {
        "neutral": (
            "#fffaf3",
            "#faf4ed",
            "#f2e9e1",
            "#ebe1d8",
            "#e3d9d0",
            "#dacec7",
            "#c6bec5",
            "#afacb8",
            "#918c9e",
            "#6b677e",
            "#635f7c",
            "#464261",
        ),
        "blue": (
            "#f9fcff",
            "#f0f8ff",
            "#deefff",
            "#cce7ff",
            "#b9dcfb",
            "#a5d0f5",
            "#88beeb",
            "#5da5e0",
            "#1c689e",
            "#095c92",
            "#185f92",
            "#014068",
        ),
        "green": (
            "#f9fdf8",
            "#f2f9f0",
            "#e5f1e2",
            "#d7e9d4",
            "#c9dfc4",
            "#b9d4b3",
            "#a1c29a",
            "#81ac78",
            "#5e8755",
            "#537b4a",
            "#466c3e",
            "#284622",
        ),
        "teal": (
            "#f7fdfd",
            "#edfafa",
            "#dcf2f1",
            "#cceae9",
            "#b9e0e0",
            "#a5d5d4",
            "#88c4c4",
            "#5baeae",
            "#489c9b",
            "#3a8f8f",
            "#0d6868",
            "#004747",
        ),
        "yellow": (
            "#fffbf6",
            "#fef5eb",
            "#f9ead9",
            "#f3e0c7",
            "#ecd3b4",
            "#e3c59f",
            "#d6b081",
            "#c49454",
            "#e5b474",
            "#dbaa6b",
            "#a2773b",
            "#553600",
        ),
        "orange": (
            "#fffbf9",
            "#fff4ef",
            "#fee8dc",
            "#fadccc",
            "#f5ceba",
            "#edbfa6",
            "#e1a98a",
            "#d28b63",
            "#c17c54",
            "#b47049",
            "#985a35",
            "#5e2e0f",
        ),
        "red": (
            "#fffafb",
            "#fff3f6",
            "#ffe5ea",
            "#ffd7df",
            "#fac8d3",
            "#f3b8c5",
            "#e8a0b1",
            "#da7e96",
            "#b15b72",
            "#a44f67",
            "#7f3149",
            "#632537",
        ),
        "violet": (
            "#fdfbff",
            "#f9f4ff",
            "#f2e8ff",
            "#ebdbfd",
            "#e2cef9",
            "#d7bef3",
            "#c6a8e8",
            "#b289dc",
            "#8d65b4",
            "#8159a7",
            "#744f98",
            "#4a2d66",
        ),
    },
    "dark": {
        "neutral": (
            "#14121d",
            "#191724",
            "#1f1d2e",
            "#26233a",
            "#2d2a42",
            "#35314b",
            "#423e59",
            "#57546f",
            "#8885a3",
            "#9794b2",
            "#aaa7c5",
            "#e0def4",
        ),
        "blue": (
            "#0f1519",
            "#141d24",
            "#1a2834",
            "#1e3243",
            "#223d53",
            "#294b67",
            "#366285",
            "#5792c3",
            "#71b8f4",
            "#80c3fc",
            "#8cc4f4",
            "#d0e8fe",
        ),
        "green": (
            "#111511",
            "#181d17",
            "#21291f",
            "#283425",
            "#2f402c",
            "#3a4e35",
            "#4c6646",
            "#74986c",
            "#94bf8a",
            "#a0ca97",
            "#a6c99f",
            "#daead7",
        ),
        "teal": (
            "#0f1515",
            "#141e1e",
            "#1a2a2a",
            "#1e3535",
            "#224140",
            "#284f4f",
            "#356767",
            "#559a99",
            "#89dcdb",
            "#96e5e4",
            "#8ccbcb",
            "#d0ebea",
        ),
        "yellow": (
            "#17130e",
            "#211b13",
            "#2e2518",
            "#3b2e1c",
            "#49371f",
            "#5a4325",
            "#755831",
            "#ac844f",
            "#f4c282",
            "#fccd90",
            "#ddb685",
            "#f3e2cc",
        ),
        "orange": (
            "#18120f",
            "#231a15",
            "#31231b",
            "#402b1f",
            "#4e3324",
            "#603e2b",
            "#7d523a",
            "#b87c5b",
            "#eea67d",
            "#f6b08a",
            "#e9af8f",
            "#f9ded0",
        ),
        "red": (
            "#191113",
            "#24181b",
            "#332025",
            "#42272e",
            "#512f37",
            "#643944",
            "#824a58",
            "#bf7285",
            "#ee91a9",
            "#f89eb4",
            "#f1a5b7",
            "#fddae1",
        ),
        "violet": (
            "#151219",
            "#1e1924",
            "#2a2233",
            "#362a42",
            "#423352",
            "#513e65",
            "#695183",
            "#9c7ac0",
            "#c59cef",
            "#cfa8f8",
            "#cdadf1",
            "#ecdefc",
        ),
    },
}


@pytest.fixture(scope="module")
def built() -> dict[palette.Mode, palette.Palette]:
    return palette.build(palette.load_parameters())


def test_the_palette_has_the_approved_values(built: dict[palette.Mode, palette.Palette]) -> None:
    assert list(built) == list(APPROVED)
    for mode, scales in APPROVED.items():
        assert list(built[mode]) == list(scales), f"{mode}: base colours or their order differ"
        for name, scale in scales.items():
            assert tuple(built[mode][name]) == scale, f"{mode} {name}"


def test_the_committed_palette_tokens_equal_the_generator_output() -> None:
    for name, text in tokens.palette_files().items():
        committed = tokens.directory().joinpath(name).read_text(encoding="utf-8")
        assert committed == text, f"{name} differs from the parameter file's output; run `mise run render`"


def _raw() -> dict[str, Any]:
    """The shipped parameter file as parsed TOML, for a test to break."""
    return tomllib.loads(files("copper_design").joinpath(palette.PARAMETER_FILE).read_text(encoding="utf-8"))


def test_the_shipped_parameters_pass_their_schema() -> None:
    parameters = palette.parse(_raw())
    assert list(parameters.hues) == ["blue", "green", "teal", "yellow", "orange", "red", "violet"]


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (lambda raw: raw.update(colour={}), "unknown keys ['colour']"),
        (lambda raw: raw.pop("curve"), "missing ['curve']"),
        (lambda raw: raw["neutral"].update(drak=raw["neutral"]["dark"]), "neutral: unknown keys ['drak']"),
        (lambda raw: raw["neutral"].pop("dark"), "neutral: missing ['dark']"),
        (lambda raw: raw["curve"]["dark"].update(chroam=[]), "curve.dark: unknown keys ['chroam']"),
        (
            lambda raw: raw["curve"]["dark"].update(chroma=raw["curve"]["dark"]["chroma"][:11]),
            "curve.dark.chroma: needs 12 values",
        ),
        (
            lambda raw: raw["neutral"]["light"].update(hue=[*raw["neutral"]["light"]["hue"], 290]),
            "neutral.light.hue: needs 12 values",
        ),
        (
            lambda raw: raw["neutral"]["light"]["lightness"].__setitem__(3, 1.2),
            "neutral.light.lightness[3]: 1.2 is outside 0.0-1.0",
        ),
        (
            lambda raw: raw["neutral"]["dark"]["chroma"].__setitem__(0, -0.01),
            "neutral.dark.chroma[0]: -0.01 is outside",
        ),
        (lambda raw: raw["neutral"]["dark"]["hue"].__setitem__(0, 1000), "neutral.dark.hue[0]: 1000 is outside"),
        (
            lambda raw: raw["curve"]["light"]["lightness"].__setitem__(0, True),
            "curve.light.lightness[0]: needs a number, not True",
        ),
        (
            lambda raw: raw["curve"]["light"]["chroma"].__setitem__(0, "x"),
            "curve.light.chroma[0]: needs a number, not 'x'",
        ),
        (lambda raw: raw["curve"].update(light=[]), "curve.light: needs a table"),
        (lambda raw: raw["hue"]["blue"].pop("chroma"), "hue.blue: missing ['chroma']"),
        (lambda raw: raw["hue"]["blue"].update(ligth={}), "hue.blue: unknown keys ['ligth']"),
        (lambda raw: raw["hue"]["blue"].update(angle=-5), "hue.blue.angle: -5 is outside"),
        (lambda raw: raw["hue"]["blue"].update(chroma=0.5), "hue.blue.chroma: 0.5 is outside"),
        (lambda raw: raw["hue"]["blue"].update(light={"0": 0.5}), "hue.blue.light: unknown keys ['0']"),
        (lambda raw: raw["hue"]["blue"].update(light={"13": 0.5}), "hue.blue.light: unknown keys ['13']"),
        (lambda raw: raw["hue"]["blue"].update(light={"9": 1.5}), "hue.blue.light.9: 1.5 is outside"),
        (lambda raw: raw["hue"].update(neutral=raw["hue"]["blue"]), "hue.neutral: a hue's name is lowercase letters"),
        (lambda raw: raw["hue"].update({"$x": raw["hue"]["blue"]}), "hue.$x: a hue's name is lowercase letters"),
        (lambda raw: raw["hue"].update({"blue.dark": raw["hue"]["blue"]}), "hue.blue.dark: a hue's name"),
        (lambda raw: raw.update(hue={}), "hue: needs a table of hues"),
    ],
)
def test_a_parameter_file_that_breaks_its_schema_is_refused(edit: Any, message: str) -> None:
    raw = _raw()
    edit(raw)
    with pytest.raises(palette.ParameterError, match=re.escape(message)):
        palette.parse(raw)


@pytest.mark.parametrize("content", [b"[neutral\n", b"# \xe9\n", None, "directory"])
def test_an_unreadable_parameter_file_names_itself(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, content: bytes | str | None
) -> None:
    # Broken TOML, bytes that are no UTF-8, a missing file, a directory in its place.
    path = tmp_path / palette.PARAMETER_FILE
    if isinstance(content, bytes):
        path.write_bytes(content)
    elif content == "directory":
        path.mkdir()
    monkeypatch.setattr(palette, "files", lambda _package: tmp_path)
    with pytest.raises(palette.ParameterError, match=r"^parameters\.toml: "):
        palette.load_parameters()


def test_a_hue_exception_moves_only_its_step(built: dict[palette.Mode, palette.Palette]) -> None:
    raw = _raw()
    raw["hue"]["red"]["dark"] = {"3": 0.5}
    moved = palette.build(palette.parse(raw))["dark"]["red"]
    assert moved[2] != built["dark"]["red"][2]
    assert moved[:2] + moved[3:] == built["dark"]["red"][:2] + built["dark"]["red"][3:]


@pytest.mark.parametrize("step", ["1", "12"])
def test_a_hue_exception_may_move_the_first_and_last_step(step: str) -> None:
    raw = _raw()
    raw["hue"]["red"]["dark"] = {step: 0.5}
    assert palette.parse(raw).hues["red"].lightness["dark"] == {int(step): 0.5}
