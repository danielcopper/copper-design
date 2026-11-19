---
status: accepted
decided: 2026-11-19
updated: 2026-11-19
amends: [0001]
---

# Named colours plus a small set of general UI roles

## Context

[ADR-0001](0001-mixed-layering.md) put three layers here — palette, roles, generic ports — and defined a role as a
meaning two or more consumers share. The prototype the palette was chosen from carried roles of that kind: besides
general ones (backgrounds, text, an accent) it had a calendar's colours, a five-step value scale, three water levels and
a lit-light fill for a dashboard, each defined because a consumer needed it.

The common colour schemes that serve many apps — Catppuccin, Rosé Pine, base16 — do it differently: they publish named
colours and a small set of general roles (base, surface, text, a few accents), and each port or app maps its own
meanings onto those. A role set that grows with every consumer's domain would make the first release carry names that
only make sense inside one app, and every new domain colour a change and a release here.

## Decision

**copper publishes named colours and a small set of general UI roles; domain colours stay with the app that uses them.**

- Each base colour has a main value per mode under its plain name (`blue`, step 9) and its 12 steps (`blue-1` …
  `blue-12`): the named colours.
- The roles are general UI meanings: backgrounds (`bg`, `bg-alt`, `surface`, `surface-raised`), `border`, text (`text`,
  `text-muted`, `text-subtle`), `accent`, `on-accent`, `selection` and the states `success`, `warning`, `error`, `info`.
  Each is a reference to a palette step per mode.
- Domain colours — a calendar's colours, a weather scale, a dashboard's lit-light fill — are component colours of the
  app that uses them, picked there from the named colours.

This narrows ADR-0001's roles from "meanings two consumers share" to general UI meanings. ADR-0001's rule that a
component colour moves here once a second consumer needs it now moves it here as a named colour or a new general role,
not as a domain role.

## Consequences

- A port for a new target maps its slots onto named colours and general roles, as the common schemes' ports do; a
  terminal theme's ANSI colours, for example, are named colours.
- Two apps that share a domain meaning (say a colour for weekends) each pick the named colour for it, so they can drift;
  this repository does not hold them to one choice.
- The role set stays small and stable, so a consumer can rely on every role existing in every release.

## Alternatives considered

**Carry the prototype's domain roles** (calendar, scale, water, lit-light). They match what the consumers use today, but
name one app's domain in the shared layer, grow with every new app, and would have to be renamed or dropped when that
app's design moves.
