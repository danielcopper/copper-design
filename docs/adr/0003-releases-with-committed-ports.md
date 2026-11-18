---
status: accepted
decided: 2026-11-18
updated: 2026-11-18
---

# Releases carry committed ports, and consumers pin a release

## Context

The ports ([ADR-0001](0001-mixed-layering.md)) have to reach the consumers, which live in their own repositories and
build with their own tools: Gradle for the Android apps, a theme file for Home Assistant. A consumer must get a colour
change on purpose, at a moment it chooses, and be able to say which version of copper it carries.

## Decision

**release-please cuts versioned releases, the generated ports are committed here, and each consumer pins a release.**

- The generic ports are committed under `ports/<target>/`; a test holds each one equal to the generator's output, so a
  change to the tokens or a template shows in the same pull request as the ports it moves.
- release-please versions the repository from its Conventional Commits and tags each release.
- A consumer that takes a port as it is copies it at a pinned tag and checks its copy against that tag. A consumer that
  adds component colours installs the generator at a pinned tag and renders its own file from the port and its own
  template, checked the same way.
- A fix is the next release; there are no maintenance branches, since every consumer moves its pin forward when it is
  ready.

## Consequences

- A release's diff shows every colour it changes, in every target's own format.
- Every consumer carries a version, and moving it is a change in that consumer's own repository, reviewed there.
- The ports are generated files under version control: a pull request that changes the tokens or a template also changes
  the committed ports, and the equality test fails until it does.

## Alternatives considered

**Consumers generate at build time.** Each consumer's build would run the generator and need its toolchain: the Android
builds would need Python. And no file here would show a token change in a target's format, so the review of that change
would not see its effect on any target.
