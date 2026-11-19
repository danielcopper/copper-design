"""The version has three copies, and release-please writes all of them.

release-please keeps the released version in .release-please-manifest.json and
writes the next one into pyproject.toml (its python strategy) and into
``copper_design.__version__`` (the ``extra-files`` entry in
release-please-config.json, which finds the line by its
``x-release-please-version`` annotation). These tests make drift between pyproject.toml
and ``__version__`` a red test, and a release PR runs them, so once main's ruleset
requires the test checks, a release that bumps one spelling without the other
cannot merge. No installed distribution's metadata is compared here: the venv
holds the locked deps, not the project (mise.toml's `setup` task says why); the
`package` job in .github/workflows/ci.yml compares the installed wheel's
metadata version with ``__version__``.
"""

import json
import tomllib
from pathlib import Path

import copper_design

_ROOT = Path(__file__).resolve().parents[1]
_ANNOTATION = "x-release-please-version"


def _pyproject_version() -> str:
    project = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return project["version"]


def test_the_package_speaks_the_pyproject_version() -> None:
    assert _pyproject_version() == copper_design.__version__


def test_every_extra_file_carries_the_annotation_on_its_version_line() -> None:
    # release-please's generic updater rewrites only annotated lines; a moved
    # file or a lost annotation would leave that copy behind without a word.
    config = json.loads((_ROOT / "release-please-config.json").read_text(encoding="utf-8"))
    paths = [path for package in config["packages"].values() for path in package.get("extra-files", [])]
    assert paths, "release-please-config.json names no extra-files"
    version = _pyproject_version()
    for path in paths:
        extra_file = _ROOT / path
        assert extra_file.is_file(), f"{path} does not exist"
        annotated = [line for line in extra_file.read_text(encoding="utf-8").splitlines() if _ANNOTATION in line]
        assert annotated, f"{path} has no line carrying {_ANNOTATION}"
        assert all(version in line for line in annotated), f"{path}: an annotated line is not the version line"
