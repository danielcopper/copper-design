---
status: accepted
decided: 2026-11-18
updated: 2026-11-19
amended-by: [0004, 0005]
---

# Palette, roles and generic ports live here; component colours stay with their consumer

## Context

Several consumers — a Home Assistant theme, a calendar app, a weather app, later terminal and self-hosted app themes —
draw from one colour scheme. Until now each kept its own copy: an app's built-in palette and its Android resources were
copied by hand from the Home Assistant theme, and nothing checked that the copies still agreed.

A central repository can hold more or less of what each consumer needs. At one end it holds only the palette, and every
consumer maps palette steps to its own uses. At the other it holds every colour every consumer draws, down to a single
dashboard card's tint. The colours at that far end change with the consumer's own work: a dashboard's component colours
move whenever the dashboard is reworked, far more often than the palette.

## Decision

**This repository holds three layers; the fourth stays with the consumer.**

1. **Palette**: one scale of 12 steps per base colour, per mode.
2. **Roles**: the meanings two or more consumers share, as data, each a reference to a palette step per mode. Role names
   are neutral: they say what a colour is for, never which consumer or person uses it.
3. **Generic ports**: the generator's output per target (a Home Assistant base theme, Android resources, terminal and
   app themes), holding palette and roles and nothing that belongs to one consumer.
4. **Component colours** — a colour only one consumer uses, such as a dashboard component's tint or an app's launcher
   icon — stay in that consumer and reference palette steps or roles.

A component colour that a second consumer needs moves here and becomes a role.

## Consequences

- A consumer's own design work changes its own repository only; this one releases when the palette, a shared role or a
  port changes.
- A consumer that adds component colours needs a way to combine them with a port: it renders its own file from the port
  and its own template ([ADR-0003](0003-releases-with-committed-ports.md)).
- Colours that are not shared are not reviewed here, so two consumers can drift in a colour neither has promoted to a
  role. Promoting it is the remedy.

## Alternatives considered

**Palette only.** Every consumer would map steps to meanings on its own, so "primary text" or "accent fill" would be
decided once per consumer and could disagree — the drift this repository exists to end.

**Every colour here.** Every dashboard change would need a change and a release here before the dashboard could use it,
and this repository would carry names that only make sense inside one consumer.

## Amendment — the shared/own split holds for every asset kind

This record was written for colours alone. [ADR-0004](0004-design-system-step-by-step.md) makes the repository a design
system and applies this record's split between what is shared here and what stays with one consumer to every asset kind.
Icons are an asset kind of their own there, so the launcher icon in the fourth layer above stands for its colour only;
where the icon file lives is decided under ADR-0004.

## Amendment — roles are general UI roles

[ADR-0005](0005-named-colours-and-general-roles.md) narrows the second layer: the roles are a small set of general UI
meanings (backgrounds, border, text, accent, selection, states), beside the named colours — each base colour's main
value and its steps. A meaning two consumers share but that belongs to their domain, such as a calendar's colours, is
not a role; each consumer picks it from the named colours. A component colour a second consumer needs moves here as a
named colour or a general role.
