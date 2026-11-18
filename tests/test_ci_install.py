"""CI installs the dev deps from uv.lock, and the scan in CI reads the workflows.

Every install step in the workflows runs the command of mise.toml's `setup`
task, so CI and a local venv hold the same versions; that command installs from
the lock, fails when the lock is out of date with pyproject.toml, and takes
wheels only. The scan's sources take in the workflows and pyproject.toml, so
SonarQube Cloud measures how CI installs and what the project depends on on
every run, not only in an automatic analysis.
"""

import re
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOWS = _ROOT / ".github" / "workflows"

# Any command that installs Python packages, whichever tool runs it.
_INSTALLER = re.compile(r"\b(?:pip3?\s+install|-m\s+pip\b|uv\s+(?:pip|sync|add|run|tool)\b|pipx\b|poetry\b|pipenv\b)")


def _setup_command() -> str:
    tasks = tomllib.loads((_ROOT / "mise.toml").read_text(encoding="utf-8"))["tasks"]
    return tasks["setup"]["run"]


def _install_commands() -> list[tuple[str, str]]:
    """Each workflow line outside a comment that installs packages, by file."""
    commands: list[tuple[str, str]] = []
    for workflow in sorted(_WORKFLOWS.glob("*.y*ml")):
        for line in workflow.read_text(encoding="utf-8").splitlines():
            text = line.strip().removeprefix("- ").removeprefix("run:").strip()
            if not text.startswith("#") and _INSTALLER.search(text):
                commands.append((workflow.name, text))
    return commands


def _scan_paths(key: str) -> set[str]:
    for line in (_ROOT / "sonar-project.properties").read_text(encoding="utf-8").splitlines():
        name, _, value = line.partition("=")
        if name.strip() == key:
            return {path.strip().rstrip("/") for path in value.split(",") if path.strip()}
    return set()


def test_the_setup_command_installs_the_locked_wheels_only() -> None:
    command = _setup_command().split()
    assert command[:2] == ["uv", "sync"]
    # --locked, not --frozen: --frozen installs a stale lock without a word.
    assert "--locked" in command
    assert "--no-build" in command
    assert (_ROOT / "uv.lock").is_file()


def test_every_ci_install_runs_the_setup_command() -> None:
    commands = _install_commands()
    assert any(name == "ci.yml" for name, _ in commands), "ci.yml installs nothing"
    setup = _setup_command()
    strays = [f"{name}: {text}" for name, text in commands if text != setup]
    assert not strays, f"installs other than `{setup}`: {strays}"


def test_the_scan_reads_the_workflows_and_pyproject() -> None:
    sources = _scan_paths("sonar.sources")
    assert {"copper_design", ".github", "pyproject.toml"} <= sources
    tests = _scan_paths("sonar.tests")
    assert tests == {"tests"}
    overlap = [s for s in sources for t in tests if s == t or s.startswith(f"{t}/") or t.startswith(f"{s}/")]
    assert not overlap, f"counted as sources and tests: {overlap}"
