"""The roles reach their contrast in both modes, by copper_design.contrast's criteria.

The criteria are pinned here to issue 5's Done-when and decisions: the kinds and
their needs, the backdrops, every role of the token files in exactly one kind,
and the one exception, the decorative ``border``. An exception that no longer
falls short fails, so the list cannot go stale.
"""

import pytest
from coloraide import Color

from copper_design import contrast, palette, tokens


def test_the_criteria_are_the_issues() -> None:
    assert contrast.NEEDS == {"text": 4.5, "graphic": 3.0}
    assert contrast.BACKDROPS == ("bg", "surface")
    kinds = {kind: {role for role, own in contrast.KINDS.items() if own == kind} for kind in contrast.NEEDS}
    assert kinds["text"] == {"text", "text-muted", "text-subtle"}
    assert kinds["graphic"] == {"accent", "border", "border-strong", "success", "warning", "error", "info"}
    assert set(contrast.EXCEPTIONS) == {("border", "bg"), ("border", "surface")}
    assert set(contrast.STATES) == {"success", "warning", "error", "info"}
    assert set(contrast.SITS_ON) == {("on-accent", "accent"), ("text", "selection")}


def test_every_on_fill_role_is_measured_on_its_fill() -> None:
    on_fill = {role for role, kind in contrast.KINDS.items() if kind == "on-fill"}
    assert on_fill
    assert on_fill <= {foreground for foreground, _ in contrast.SITS_ON}


@pytest.mark.parametrize("mode", palette.MODES)
def test_every_role_has_exactly_one_kind(mode: palette.Mode) -> None:
    # KINDS is a dict, so no role has two; this holds that every role has one
    # and that no kind names a role the token files lack.
    assert set(tokens.load(mode).roles) == set(contrast.KINDS)


@pytest.mark.parametrize("mode", palette.MODES)
def test_every_role_reaches_its_contrast(mode: palette.Mode) -> None:
    checks = contrast.checks(tokens.colours(mode))
    measured = [role for role, kind in contrast.KINDS.items() if kind in contrast.NEEDS]
    assert len(checks) == len(measured) * len(contrast.BACKDROPS) + len(contrast.SITS_ON)
    unexcused = [
        f"{c.foreground} on {c.background}: {c.ratio:.2f}:1 < {c.need}"
        for c in checks
        if not c.passes and not c.exception
    ]
    assert not unexcused, f"{mode}: {unexcused}"
    stale = [(c.foreground, c.background) for c in checks if c.exception and c.passes]
    assert not stale, f"{mode}: these exceptions reach their contrast now; drop them: {stale}"


@pytest.mark.parametrize("mode", palette.MODES)
def test_bg_alt_is_darker_than_the_content(mode: palette.Mode) -> None:
    # Issue 5, D9: sidebars and bars are darker than the surfaces beside them,
    # and in light mode darker than bg too (in dark mode bg is the darkest step).
    colours = tokens.colours(mode)
    luminance = {role: Color(colours[role]).luminance() for role in ("bg-alt", "bg", "surface")}
    assert luminance["bg-alt"] < luminance["surface"]
    if mode == "light":
        assert luminance["bg-alt"] < luminance["bg"]
    else:
        assert luminance["bg-alt"] <= luminance["bg"]
