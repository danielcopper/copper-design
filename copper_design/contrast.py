"""The roles' contrast criteria (WCAG 2.2): text 4.5:1 (1.4.3), graphics and component edges 3:1 (1.4.11).

Every role has one kind. Text and graphic roles are measured against each
backdrop, and a few roles against the role they sit on. A pair that may fall
short is an exception with its reason. The preview shows these checks, and
tests/test_contrast.py holds the tokens to them.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from coloraide import Color

type Kind = Literal["background", "text", "graphic", "on-fill"]

KINDS: dict[str, Kind] = {
    "bg": "background",
    "bg-alt": "background",
    "surface": "background",
    "surface-raised": "background",
    "selection": "background",
    "border": "graphic",
    "border-strong": "graphic",
    "text": "text",
    "text-muted": "text",
    "text-subtle": "text",
    "accent": "graphic",
    "on-accent": "on-fill",
    "success": "graphic",
    "warning": "graphic",
    "error": "graphic",
    "info": "graphic",
}
"""Each role's kind; every role has exactly one."""

STATES = ("success", "warning", "error", "info")

NEEDS: dict[Kind, float] = {"text": 4.5, "graphic": 3.0}
"""The contrast a text or graphic role needs against each backdrop."""

BACKDROPS = ("bg", "surface")
"""The backgrounds every text and graphic role is measured on."""

SITS_ON = (("on-accent", "accent"), ("text", "selection"))
"""Text measured against the role it sits on, with the text need: every on-fill role on its fill, and text on
selection."""

_DECORATIVE_BORDER = (
    "border is the quiet, decorative edge of cards and dividers; WCAG 1.4.11 asks 3:1 only of an edge that identifies "
    "a control, which is border-strong's job."
)
EXCEPTIONS: dict[tuple[str, str], str] = {
    ("border", "bg"): _DECORATIVE_BORDER,
    ("border", "surface"): _DECORATIVE_BORDER,
}
"""(role, backdrop) pairs that may fall short, in both modes, and why."""


@dataclass(frozen=True)
class Check:
    foreground: str
    background: str
    need: float
    ratio: float
    exception: str | None = None
    """Why this pair may fall short, if it may."""

    @property
    def passes(self) -> bool:
        return self.ratio >= self.need


def ratio(foreground: str, background: str) -> float:
    """The WCAG 2.x contrast ratio of two sRGB colours."""
    return Color(foreground).contrast(background)


def checks(colours: Mapping[str, str]) -> list[Check]:
    """Every contrast check for one mode's colours, in role order."""

    def check(foreground: str, background: str, need: float) -> Check:
        return Check(
            foreground,
            background,
            need,
            ratio(colours[foreground], colours[background]),
            EXCEPTIONS.get((foreground, background)),
        )

    result = [
        check(role, backdrop, NEEDS[kind]) for role, kind in KINDS.items() if kind in NEEDS for backdrop in BACKDROPS
    ]
    result += [check(foreground, background, NEEDS["text"]) for foreground, background in SITS_ON]
    return result
