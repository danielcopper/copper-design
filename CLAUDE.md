# copper-design

copper is one design system for several consumers (a Home Assistant theme, Android apps, terminal and self-hosted app
themes), filled step by step ([ADR-0004](docs/adr/0004-design-system-step-by-step.md)). For colours this repository will
hold the palette and the shared roles as DTCG 2025.10 JSON per mode, the Python generator that renders them through
Jinja2 templates, and the generic ports it produces under `ports/<target>/`. Consumers pin a release.

The terms are in [GLOSSARY.md](GLOSSARY.md); use them, and update an entry when a term's meaning changes. The decisions
are in [docs/adr/](docs/adr/).

## Where decisions live

Work starts from an issue: open questions under `## To decide` (one checkbox each, checked off with a pointer like
`→ D1` once answered), decisions under `## Decisions` (appended; a changed one is struck through and re-added with its
date). A hard-to-reverse, surprising trade-off also gets an ADR in `docs/adr/` (front matter `status`, `decided`,
`updated`), linked from the issue. Every `## Done when` item becomes a test seen failing first. The PR body repeats the
decisions and becomes the squash commit. The `decisions` CI check enforces the linked issue's `## Decisions` and
`## To decide`, the ADR format, this section's heading and that `.github/ISSUE_TEMPLATE/planned_change.yml` stays
identical to the shared form ([rules](https://github.com/danielcopper/.github#the-decisions-check)); the rest is for
review.

## Pipeline

- **Gate**: `mise run gate` (tests, ruff check and format, basedpyright, `deno fmt --check`, markdownlint): what CI
  checks on a pull request, less the Python 3.12 and 3.13 test legs, the SonarQube Cloud gate, the PR title and the
  `decisions` check. On a fresh checkout or worktree `mise trust && mise run setup` first.
- **Review checks**: `ruff check <files>`, `ruff format --check <files>`, `basedpyright <files>`,
  `deno fmt --check <files>`
- **Worktree task**: `mise run worktree-new` (a global mise task from the owner's dotfiles, not in this repository)
- **Agent rules**:
  - This repository is public: committed text names no person and nothing of a private setup (calendar names or ids,
    Home Assistant entity or dashboard names, hostnames, a consumer's own file names or paths). Consumers are named by
    kind: "a Home Assistant theme", "a calendar app", "a weather app".
  - An icon or illustration is committed only after its provenance is checked for that file
    ([ADR-0004](docs/adr/0004-design-system-step-by-step.md)).
  - Scratch files go in the agent's scratchpad, never inside the worktree.
  - Absolute paths in every command (`git -C <worktree>`, `<worktree>/.venv/bin/…`); the shell's working directory
    resets between calls.
  - Run the gate once; never start a second run while one is still going.
