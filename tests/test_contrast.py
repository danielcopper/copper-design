"""The roles' contrast (WCAG 2.2): text 4.5:1 (1.4.3), graphics and component parts 3:1 (1.4.11).

Each text and graphic role is measured against ``bg`` and ``surface`` in both
modes. A pair that falls short is listed in EXCEPTIONS with its reason; an
exception that no longer falls short fails too, so the list cannot go stale.
"""

import pytest
from coloraide import Color

from copper_design import palette, tokens

TEXT = ("text", "text-muted", "text-subtle")
GRAPHIC = ("accent", "border", "success", "warning", "error", "info")
BACKDROPS = ("bg", "surface")

# (mode, role, backdrop): why it may fall short.
EXCEPTIONS = {
    ("light", "text-subtle", "bg"): (
        "4.49:1, short of 4.5 by 0.01. The step is the approved palette's tertiary text (neutral 10, 4.7:1 on "
        "surface); the next step up is neutral 11, which text-muted already takes."
    ),
    **{
        (mode, "border", backdrop): (
            "A border separates surfaces and comes from the border steps (6-8), which stay below 3:1 by their "
            "job; the first neutral step that reaches 3:1 is the solid fill (9). WCAG 1.4.11 asks 3:1 only of a "
            "boundary that is needed to identify a control."
        )
        for mode in palette.MODES
        for backdrop in BACKDROPS
    },
}


def _ratio(foreground: str, background: str) -> float:
    return Color(foreground).contrast(background)


def _pairs() -> list[tuple[str, str, str, float]]:
    return [
        (mode, role, backdrop, need)
        for mode in palette.MODES
        for roles, need in ((TEXT, 4.5), (GRAPHIC, 3.0))
        for role in roles
        for backdrop in BACKDROPS
    ]


@pytest.mark.parametrize(("mode", "role", "backdrop", "need"), _pairs())
def test_a_role_reaches_its_contrast_on_the_backgrounds(mode: str, role: str, backdrop: str, need: float) -> None:
    colours = tokens.colours(mode)
    ratio = _ratio(colours[role], colours[backdrop])
    if (mode, role, backdrop) in EXCEPTIONS:
        assert ratio < need, f"{mode} {role} on {backdrop} reaches {ratio:.2f}:1 now; drop its exception"
    else:
        assert ratio >= need, f"{mode} {role} on {backdrop}: {ratio:.2f}:1, needs {need}:1"


def test_every_exception_names_a_measured_pair() -> None:
    measured = {(mode, role, backdrop) for mode, role, backdrop, _ in _pairs()}
    assert set(EXCEPTIONS) <= measured


@pytest.mark.parametrize("mode", palette.MODES)
def test_text_on_accent_and_on_selection_reaches_4_5(mode: str) -> None:
    colours = tokens.colours(mode)
    assert _ratio(colours["on-accent"], colours["accent"]) >= 4.5
    assert _ratio(colours["text"], colours["selection"]) >= 4.5
