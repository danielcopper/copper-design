"""The version has four copies, and release-please writes all of them.

release-please keeps the released version in .release-please-manifest.json and
writes the next one into pyproject.toml (its python strategy), into
``copper_design.__version__`` (a generic ``extra-files`` entry in
release-please-config.json, which finds the line by its
``x-release-please-version`` annotation) and into uv.lock's entry for the
project itself (a ``toml`` entry, which finds the value by a JSONPath). These
tests make drift between pyproject.toml, ``__version__`` and uv.lock a red test,
and a release PR runs them, so once main's ruleset requires the test checks, a
release that bumps one spelling without the others cannot merge. No installed
distribution's metadata is compared here: the venv holds the locked deps, not
the project (mise.toml's `setup` task says why); the `package` job in
.github/workflows/ci.yml compares the installed wheel's metadata version with
``__version__``.
"""

import json
import tomllib
from pathlib import Path
from typing import Any

import copper_design

_ROOT = Path(__file__).resolve().parents[1]
_ANNOTATION = "x-release-please-version"


def _project() -> dict[str, Any]:
    return tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def _pyproject_version() -> str:
    return _project()["version"]


def _extra_files() -> list[str | dict[str, str]]:
    config = json.loads((_ROOT / "release-please-config.json").read_text(encoding="utf-8"))
    return [entry for package in config["packages"].values() for entry in package.get("extra-files", [])]


def _is_generic(entry: str | dict[str, str]) -> bool:
    return isinstance(entry, str) or entry.get("type") == "generic"


def test_the_package_speaks_the_pyproject_version() -> None:
    assert _pyproject_version() == copper_design.__version__


def test_every_extra_file_carries_the_annotation_on_its_version_line() -> None:
    # release-please's generic updater rewrites only annotated lines; a moved
    # file or a lost annotation would leave that copy behind without a word.
    # A bare path is a generic entry; uv.lock's typed entry is held below.
    paths = [entry if isinstance(entry, str) else entry["path"] for entry in _extra_files() if _is_generic(entry)]
    assert paths, "release-please-config.json names no generic extra-files"
    version = _pyproject_version()
    for path in paths:
        extra_file = _ROOT / path
        assert extra_file.is_file(), f"{path} does not exist"
        annotated = [line for line in extra_file.read_text(encoding="utf-8").splitlines() if _ANNOTATION in line]
        assert annotated, f"{path} has no line carrying {_ANNOTATION}"
        assert all(version in line for line in annotated), f"{path}: an annotated line is not the version line"


def test_the_lock_holds_the_pyproject_version_for_the_project() -> None:
    # `uv sync --locked` refuses a lock whose project entry lags pyproject.toml,
    # which is every install in CI.
    lock = tomllib.loads((_ROOT / "uv.lock").read_text(encoding="utf-8"))
    entries = [package for package in lock["package"] if package["name"] == _project()["name"]]
    assert len(entries) == 1, f"uv.lock has {len(entries)} entries named {_project()['name']}"
    assert entries[0]["version"] == _pyproject_version()


def test_the_lock_extra_file_points_at_the_project_entry() -> None:
    # A JSONPath that matches nothing only logs a warning in release-please, so
    # a renamed project would leave uv.lock behind. release-please parses the
    # TOML into tagged values, each scalar an object holding it under `value`,
    # so a filter compares `@.name.value`, not `@.name`.
    entries = [entry for entry in _extra_files() if isinstance(entry, dict) and entry.get("path") == "uv.lock"]
    assert entries == [
        {
            "type": "toml",
            "path": "uv.lock",
            "jsonpath": f"$.package[?(@.name.value=='{_project()['name']}')].version",
        }
    ]
