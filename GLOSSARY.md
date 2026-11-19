# GLOSSARY.md — copper domain glossary

This file is a glossary. It defines the canonical meaning of project-specific terms so that conversations, issues, PRs,
and code stay aligned. It is _not_ a spec or design doc; architectural decisions live in `docs/adr/`.

When a term resolves during a discussion, it gets added here. When a term's meaning changes, the entry gets rewritten —
not appended to.

## Terms

### Asset kind

One kind of thing copper holds: colours, dimensions such as corner radius and spacing, icons, illustrations. Icons and
illustrations together are **artwork**.

### Token

A named, typed value that the generator renders into **ports**, such as a palette step or a role. Colour tokens are DTCG
2025.10 JSON ([ADR-0002](docs/adr/0002-dtcg-tokens-and-python-generator.md)): a palette file and a role file per
**mode**, and a resolver file that selects the mode.

### Artwork

Icons and illustrations: files, not **tokens**. Which files may enter this repository is decided in
[ADR-0004](docs/adr/0004-design-system-step-by-step.md).

### Palette

All colours of copper for one **mode**: one **scale** per **base colour**. The palette carries no meaning beyond the job
of each **step**; meaning is what a **role** adds. Each mode has its own palette file, which the generator writes from
the **parameter file**.

### Parameter file

The source of the palette's values (`copper_design/parameters.toml`): per hue its OKLCH hue angle and peak chroma, per
mode the lightness and chroma curves over the 12 steps, the neutral's own curves, and the steps a hue moves off the
shared curve. The palette tokens are generated from it and never edited by hand.

### Base colour

A colour the palette carries a scale of: the neutral, or one of the hues blue, green, teal, yellow, orange, red and
violet. A base colour names a family, not one colour; its scale holds the colours. One is added when a port needs it;
the **parameter file** lists what that takes.

### Named colour

A base colour's main value, under its plain name (`blue`, which is its step 9), or one of its steps (`blue-1` …
`blue-12`), in one mode. Ports and consumers pick from the named colours what the **roles** do not cover, such as a
terminal's ANSI colours or a calendar's colours.

### Scale

The 12 colours of one base colour in one mode, ordered by step from the background end to the text end. The hues share
one OKLCH lightness curve per mode, so a step looks about equally light across them, with deliberate exceptions on the
solid and text steps: a hue may move its solid steps (9–10) to suit the text that sits on them or to stay apart from a
neighbouring hue, and in light mode step 11 is staggered by hue, so the hues stay apart with red-green colour blindness.
The neutral scale has a curve of its own.

### Step

A position 1–12 on a scale. Each step has a fixed job, the same on every scale and in both modes (the Radix Colors
model):

- 1–2: backgrounds (the app's, then a subtle one)
- 3–5: component backgrounds (at rest, hovered, pressed or selected)
- 6–8: borders (subtle, at rest, strong or hovered)
- 9–10: solid fills (at rest, hovered)
- 11: low-contrast text
- 12: high-contrast text

A colour is picked by its step's job, never by how it looks.

### Mode

Light or dark. Each mode has its own palette and its own role values; a step keeps its job in both, but its colour is
set for each mode on its own, never derived by inverting the other.

### Role

A general UI meaning, such as `text-muted` or `accent`, defined per mode as a reference to a palette step. copper has a
small, fixed set: backgrounds (`bg`, `bg-alt`, `surface`, `surface-raised`), borders (`border`, the quiet edge of cards
and dividers, and `border-strong`, the edge that identifies a control), text (`text`, `text-muted`, `text-subtle`),
`accent`, `on-accent`, `selection` and the states `success`, `warning`, `error`, `info`
([ADR-0005](docs/adr/0005-named-colours-and-general-roles.md)). A role may point to a different step in each mode where
the two work differently. Role names say what a colour is for in any interface, never which consumer, domain or person
uses it.

### Consumer

An app or theme that takes its colours, dimensions or artwork from copper, for example a Home Assistant theme, a
calendar app or a weather app. A consumer pins a release and updates by moving the pin.

### Port

The generator's output for one target, in that target's own format: a Home Assistant base theme, Android `colors.xml`
and Kotlin, a terminal theme. A port is generic — the shared tokens, nothing that belongs to one consumer — and is
committed under `ports/<target>/`. It is never edited by hand; it equals what the generator renders.

### Component colour

A colour of one consumer's own, such as a dashboard card's tint, a calendar's colours or the colour of an app's launcher
icon. It stays with that consumer and is defined there by reference to **named colours** or roles. What happens when a
second consumer needs it is decided in [ADR-0005](docs/adr/0005-named-colours-and-general-roles.md).
