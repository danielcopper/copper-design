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
2025.10 JSON ([ADR-0002](docs/adr/0002-dtcg-tokens-and-python-generator.md)).

### Artwork

Icons and illustrations: files, not **tokens**. Which files may enter this repository is decided in
[ADR-0004](docs/adr/0004-design-system-step-by-step.md).

### Palette

All colours of copper for one **mode**: one **scale** per **base colour**. The palette carries no meaning beyond the job
of each **step**; meaning is what a **role** adds. Each mode has its own palette file.

### Base colour

A colour the palette carries a scale of: the neutral, or one hue such as blue or red. A base colour names a family, not
one colour; its scale holds the colours.

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

A named meaning that two or more consumers share, such as `text.primary` or `accent.solid`, defined per mode as a
reference to a palette step. A role may point to a different step in each mode where the two work differently. Role
names say what a colour is for, never which consumer or person uses it.

### Consumer

An app or theme that takes its colours, dimensions or artwork from copper, for example a Home Assistant theme, a
calendar app or a weather app. A consumer pins a release and updates by moving the pin.

### Port

The generator's output for one target, in that target's own format: a Home Assistant base theme, Android `colors.xml`
and Kotlin, a terminal theme. A port is generic — the shared tokens, nothing that belongs to one consumer — and is
committed under `ports/<target>/`. It is never edited by hand; it equals what the generator renders.

### Component colour

A colour only one consumer uses, such as a dashboard card's tint or the colour of an app's launcher icon. It stays with
that consumer and is defined there by reference to palette steps or roles. Once a second consumer needs it, it becomes a
role.
