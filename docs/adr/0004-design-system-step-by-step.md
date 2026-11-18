---
status: accepted
decided: 2026-11-18
updated: 2026-11-18
amends: [0001]
---

# copper is a design system, filled one asset kind at a time

## Context

This repository was set up for colours alone ([ADR-0001](0001-mixed-layering.md)). Colours are not the only thing the
consumers copy by hand: the same illustrations are copied between a Home Assistant dashboard and a calendar app, weather
icons a Home Assistant setup draws with a palette of its own will be needed by a weather app, and the Home Assistant
theme already carries values that are not colours, such as corner radius and spacing. Each of these could get a
repository of its own or join this one.

Icons that move here will be drawn from the palette, so a palette change will often bring a change to the icons. And
this repository is public under MIT: a token is a value written here, but an icon or illustration is a file that may
come from elsewhere, and it may only be published here if its origin allows it.

## Decision

**copper-design is one design system, filled step by step: colours first, then dimensions such as corner radius and
spacing, then icons and illustrations, each kind through an issue of its own.**

- The layering of [ADR-0001](0001-mixed-layering.md) holds for every asset kind: what two or more consumers share lives
  here, what one consumer uses stays with that consumer and moves here once a second consumer needs it.
- An icon or illustration enters only after its provenance is checked for that file: made by the maintainer, or under a
  licence that allows publishing it here under MIT. A file whose origin is unclear stays out.
- All kinds share one release stream: release-please versions the repository as a whole, and the changelog says what
  changed. A consumer pins one release for everything it takes from here
  ([ADR-0003](0003-releases-with-committed-ports.md)).

## Consequences

- A consumer moves one pin for colours, dimensions and artwork alike. A release that changes only icons is still a new
  version for a consumer that takes only colours; the changelog tells that consumer whether moving its pin concerns it.
- Each new kind brings decisions of its own — its file format, how the ports carry it — taken in that kind's issue. This
  record fixes only the scope and the rules every kind shares.
- Every icon or illustration costs a provenance check before it is committed, and a file that fails it is redrawn or
  left with its consumer.

## Alternatives considered

**Separate repositories, one for the colours and one for the icons.** Each kind would release on its own, so a consumer
would not move for changes it does not take. Rejected because icons here will be drawn from the palette: a palette
change and the icon change it causes would land in two releases, and a consumer would have to move two pins in step and
know which versions belong together.
