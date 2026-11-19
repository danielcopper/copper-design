# copper-design

copper is one design system for several apps. This repository is its single source: what two or more apps share will
live here, and a generator will render its tokens into each target's own format. It is filled step by step: colours
first, then dimensions such as corner radius and spacing, then icons and illustrations.

## Consumers

A consumer is anything that takes its colours, dimensions or artwork from copper: a Home Assistant theme, Android apps
such as a calendar app and a weather app, and later terminal and self-hosted app themes. Each one pins a release of this
repository and updates by moving the pin.

## How it is built

For colours:

- **Palette**: eight base colours (a neutral and seven hues), each a scale of 12 steps with a fixed job per step, set in
  OKLCH separately for light and dark mode.
- **Roles**: the meanings two or more consumers share, such as primary text or an accent fill, each pointing at a
  palette step per mode.
- **Tokens**: palette and roles as [DTCG 2025.10](https://www.designtokens.org/) JSON, one file per mode.
- **Ports**: a Python generator with Jinja2 templates renders the tokens into generic ports, one per target (a Home
  Assistant base theme, Android `colors.xml` and Kotlin, and so on), committed under `ports/<target>/`.

An icon or illustration enters only once its provenance is checked. The terms are defined in [GLOSSARY.md](GLOSSARY.md),
the decisions behind this layout in [docs/adr/](docs/adr/).

## Status

The palette's direction is chosen: the mood follows the measured properties of Rosé Pine (a warm, paper-like light mode,
a violet-grey dark mode, dusty and muted colours), not its colours. The colour token files, the generator and the ports
come next; this repository holds the project setup so far.

## Development

The tasks run through [mise](https://mise.jdx.dev/), which brings Python, uv and Deno.

```sh
mise trust
mise run setup   # the dev dependencies from uv.lock into .venv
mise run lock    # rewrite uv.lock after a dependency in pyproject.toml changed
mise run test    # the tests
mise run lint    # ruff, basedpyright, Markdown format and Markdown lint
mise run gate    # test, then lint; CLAUDE.md (Pipeline) says which CI checks it leaves out
```

## License

MIT, see [LICENSE](LICENSE).
