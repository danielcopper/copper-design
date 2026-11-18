---
status: accepted
decided: 2026-11-18
updated: 2026-11-18
---

# Tokens are DTCG 2025.10 JSON per mode; a Python generator renders them through Jinja2 templates

## Context

The palette and the roles ([ADR-0001](0001-mixed-layering.md)) need a file format, and something has to turn those files
into each target's format: YAML for a Home Assistant theme, XML and Kotlin for Android, the config formats of terminals
and self-hosted apps. The Design Tokens Community Group published the first stable version of its format, 2025.10: typed
tokens, references between them, colours with an explicit colour space such as OKLCH, and a resolver module that selects
between token sets — the way it expresses modes.

The generator is also a consumer's tool, not only this repository's: a consumer with component colours of its own
installs it at a pinned tag and renders its file from a port and its own template.

## Decision

**The tokens are DTCG 2025.10 JSON, one file per mode; the generator is Python with Jinja2 templates.**

- The palette and the roles are separate files per mode — `palette.light.tokens.json`, `palette.dark.tokens.json`,
  `roles.light.tokens.json`, `roles.dark.tokens.json` — and a resolver file selects between the modes.
- The generator is a Python package in this repository, installable from a git tag. Each port is a Jinja2 template fed
  with the resolved tokens of a mode.

## Consequences

- Any tool that reads DTCG 2025.10, including its colour and resolver modules, can read the tokens; nothing about them
  is particular to this generator.
- Adding a target is adding a template, plus a converter where the target spells colours in a way the templates do not
  have yet.
- The generator, its tests and the consumers that render with it need Python only.

## Alternatives considered

**Style Dictionary 5.** It reads DTCG and brings a library of transforms and formats, mostly for web, iOS and Android.
Rejected because it runs on JavaScript: every consumer that renders with the generator would need a JavaScript runtime
(Node.js 22 or later for Style Dictionary 5.8) and npm packages for one step, while this repository runs Deno only for
its Markdown checks. Most targets here — a Home Assistant theme, terminal and app themes — are not among its built-in
formats and would be custom formats written in JavaScript either way. Its DTCG 2025.10 support is still in progress: it
reads the colour module's values (since 5.3), but not the resolver module, and it has no modes of its own. A later move
to it would keep the token files and wire the two modes in its configuration, one build per mode, in place of the
resolver file.

**An own YAML format.** Shorter to write by hand, but no specification: references, types, colour spaces and modes would
be conventions of this repository alone, documented and validated here, and no other tool would read the files.
