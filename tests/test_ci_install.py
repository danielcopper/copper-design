"""How CI installs the dev deps, and what the scan in CI reads.

These tests pin mise.toml's `setup` command and its flags, that every install
in the workflows and in mise.toml's tasks is that command, that each workflow
job that runs Python tools (as `_PYTHON_TOOLS` names them) installs with it,
that CI runs mise.toml's uv, and
that the scan's sources hold the workflows and pyproject.toml apart from the
tests. Why each flag is there is in mise.toml's `setup` task; why the scan reads
those paths is in sonar-project.properties.

One job is the exception: ci.yml's `package` installs the built wheel into a
clean venv, as a consumer would, so `setup`'s command, which leaves the project
out, cannot serve it. Its installs are pinned here instead: the runtime deps
exported from uv.lock and installed with their hashes, then the wheel without
deps, both wheels only.

The workflows are read line by line, not as YAML: a job is a key two spaces in
under `jobs:`, a step a list item under its `steps:`, which is how every
workflow here is written.
"""

import re
import tomllib
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOWS = _ROOT / ".github" / "workflows"

# Commands that install Python packages: `pip install` under any pip name
# (pip, pip3, pip3.12), `python -m pip` with or without the space, uv's pip,
# sync, add, run and tool commands, uvx, pipx, poetry, pipenv, and
# setup-python's `pip-install` input.
_INSTALLER = re.compile(
    r"\bpip[\d.]*\s+install\b|-m\s*pip\b|\buv\s+(?:pip|sync|add|run|tool)\b|\buvx\b|\bpipx\b|\bpoetry\b|\bpipenv\b"
    r"|\bpip-install\s*:"
)
# A job runs Python tools when it sets up uv or runs `python -m`, pytest, ruff or basedpyright.
_PYTHON_TOOLS = re.compile(r"astral-sh/setup-uv@|\bpython\s+-m\b|\bpytest\b|\bruff\s|\bbasedpyright\b")
_JOB = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")
_SETUP_UV = "astral-sh/setup-uv@"
_PACKAGE_JOB = "ci.yml:package"
_PACKAGE_EXPORT = "uv export --locked --no-emit-project --output-file /tmp/runtime.txt"
_PACKAGE_INSTALLS = [
    "uv pip install --python /tmp/clean --no-build --require-hashes --requirements /tmp/runtime.txt",
    "uv pip install --python /tmp/clean --no-build --no-deps dist/*.whl",
]


def _mise() -> dict[str, Any]:
    return tomllib.loads((_ROOT / "mise.toml").read_text(encoding="utf-8"))


def _setup_command() -> str:
    command = _mise()["tasks"]["setup"]["run"]
    assert isinstance(command, str)
    return command


def _code(line: str) -> str:
    """A workflow line without list dash and `run:` key; empty for a comment."""
    text = line.strip().removeprefix("- ").removeprefix("run:").strip()
    return "" if text.startswith("#") else text


def _workflow_lines() -> list[tuple[str, str]]:
    return [
        (workflow.name, line)
        for workflow in sorted(_WORKFLOWS.glob("*.y*ml"))
        for line in workflow.read_text(encoding="utf-8").splitlines()
    ]


def _jobs() -> dict[str, list[str]]:
    """Each workflow job's lines, keyed `<file>:<job>`."""
    jobs: dict[str, list[str]] = {}
    for workflow in sorted(_WORKFLOWS.glob("*.y*ml")):
        in_jobs, current = False, None
        for line in workflow.read_text(encoding="utf-8").splitlines():
            if not line.startswith(" ") and line.strip():
                in_jobs, current = line.rstrip() == "jobs:", None
            elif in_jobs and (match := _JOB.match(line)):
                current = f"{workflow.name}:{match.group(1)}"
                jobs[current] = []
            elif current:
                jobs[current].append(line)
    return jobs


def _steps(job: list[str]) -> list[list[str]]:
    """A job's steps, each as its lines."""
    steps: list[list[str]] = []
    indent = None
    for line in job:
        stripped = line.lstrip()
        if indent is None and stripped.startswith("- "):
            indent = len(line) - len(stripped)
        if indent is not None and stripped.startswith("- ") and len(line) - len(stripped) == indent:
            steps.append([])
        if steps:
            steps[-1].append(line)
    return steps


def _task_lines(run: object) -> list[str]:
    """The shell lines of a mise task's `run`: a string, or a list of strings and task references."""
    scripts = run if isinstance(run, list) else [run]
    return [line.strip() for script in scripts if isinstance(script, str) for line in script.splitlines()]


def _scan_paths(key: str) -> set[str]:
    for line in (_ROOT / "sonar-project.properties").read_text(encoding="utf-8").splitlines():
        name, _, value = line.partition("=")
        if name.strip() == key:
            return {path.strip().rstrip("/") for path in value.split(",") if path.strip()}
    return set()


def test_the_setup_command_installs_the_locked_dev_wheels_only() -> None:
    command = _setup_command().split()
    assert command[:2] == ["uv", "sync"]
    # --locked, not --frozen: --frozen installs a stale lock without a word.
    assert "--locked" in command
    assert "--no-build" in command
    assert "--no-install-project" in command
    assert ["--extra", "dev"] in [command[i : i + 2] for i in range(len(command) - 1)]
    assert (_ROOT / "uv.lock").is_file()


def test_every_ci_install_runs_the_setup_command() -> None:
    commands = [
        (job, text)
        for job, lines in _jobs().items()
        if job != _PACKAGE_JOB
        for line in lines
        if _INSTALLER.search(text := _code(line))
    ]
    assert any(job.startswith("ci.yml:") for job, _ in commands), "ci.yml installs nothing"
    setup = _setup_command()
    strays = [f"{job}: {text}" for job, text in commands if text != setup]
    assert not strays, f"installs other than `{setup}`: {strays}"


def test_every_workflow_install_is_in_a_job() -> None:
    # The test above reads jobs; an install outside one (a workflow-level key)
    # would slip past it.
    in_jobs = sum(1 for lines in _jobs().values() for line in lines if _INSTALLER.search(_code(line)))
    everywhere = sum(1 for _, line in _workflow_lines() if _INSTALLER.search(_code(line)))
    assert in_jobs == everywhere


def test_the_package_job_installs_the_wheel_with_the_locked_runtime_deps() -> None:
    lines = [_code(line) for line in _jobs()[_PACKAGE_JOB]]
    assert [line for line in lines if _INSTALLER.search(line)] == _PACKAGE_INSTALLS
    # The requirements come from uv.lock, which --locked holds to pyproject, and
    # carry their hashes (uv export writes them unless told --no-hashes).
    assert _PACKAGE_EXPORT in lines
    assert lines.index(_PACKAGE_EXPORT) < lines.index(_PACKAGE_INSTALLS[0])
    for install in _PACKAGE_INSTALLS:
        assert "--no-build" in install.split()
        assert "--python /tmp/clean" in install, "not into the clean venv"


def test_every_job_running_python_tools_installs_with_the_setup_command() -> None:
    setup = _setup_command()
    python_jobs = {
        name: lines
        for name, lines in _jobs().items()
        if name != _PACKAGE_JOB and any(_PYTHON_TOOLS.search(_code(line)) for line in lines)
    }
    assert python_jobs, "no workflow job runs Python tools"
    missing = [name for name, lines in python_jobs.items() if not any(_code(line) == setup for line in lines)]
    assert not missing, f"jobs that run Python tools without `{setup}`: {missing}"


def test_every_mise_install_runs_the_setup_command() -> None:
    setup = _setup_command().split()
    lines = [
        line for task in _mise()["tasks"].values() for line in _task_lines(task.get("run")) if _INSTALLER.search(line)
    ]
    assert len(lines) > 1, "no task besides `setup` installs"
    # Into another venv than .venv: setup's command with `--active`, aimed at it
    # by a VIRTUAL_ENV prefix.
    aimed = re.compile(r"^VIRTUAL_ENV=\S+ (uv sync) --active( .*)$")
    strays = [line for line in lines if aimed.sub(r"\1\2", line).split() != setup]
    assert not strays, f"installs other than `{' '.join(setup)}`: {strays}"


def test_ci_sets_up_the_uv_mise_pins() -> None:
    pin = str(_mise()["tools"]["uv"])
    steps = [step for job in _jobs().values() for step in _steps(job) if any(_SETUP_UV in line for line in step)]
    assert steps, "no workflow step sets up uv"
    versions = [re.findall(r"^\s+version:\s*\"?([^\"\s#]+)", "\n".join(step), re.MULTILINE) for step in steps]
    assert versions == [[pin]] * len(steps), f"setup-uv versions {versions}, mise.toml pins {pin}"


def test_the_scan_reads_the_workflows_and_pyproject() -> None:
    sources = _scan_paths("sonar.sources")
    assert {"copper_design", ".github", "pyproject.toml"} <= sources
    tests = _scan_paths("sonar.tests")
    assert tests == {"tests"}
    overlap = [s for s in sources for t in tests if s == t or s.startswith(f"{t}/") or t.startswith(f"{s}/")]
    assert not overlap, f"counted as sources and tests: {overlap}"
