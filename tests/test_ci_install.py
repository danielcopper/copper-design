"""How CI installs the locked deps, and what the scan in CI reads.

These tests pin mise.toml's `setup` command and its flags, that every install
in the workflows but the `package` job's and every install in mise.toml's tasks
is that command, that each other workflow job that runs Python tools (as
`_PYTHON_TOOLS` names them) installs with it, that CI runs mise.toml's uv, and
that the scan's sources hold the workflows and pyproject.toml apart from the
tests. Why each flag is there is in mise.toml's `setup` task; why the scan reads
those paths is in sonar-project.properties.

ci.yml's `package` job builds and installs the wheel instead, for the reason
its comment gives; every command it runs is pinned here (`_PACKAGE_COMMANDS`),
on the requires-python floor, with the build backend at an exact pin.

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
# (pip, pip3, pip3.12), `python -m pip` with or without the space, uv's pip
# commands but `uv pip compile` (it resolves and writes a file, installing
# nothing), uv's sync, add, run, tool and build commands (a build installs its
# backend), uvx, pipx, poetry, pipenv, and setup-python's `pip-install` input.
_INSTALLER = re.compile(
    r"\bpip[\d.]*\s+install\b|-m\s*pip\b|\buv\s+pip\s+(?!compile\b)|\buv\s+(?:sync|add|run|tool|build)\b|\buvx\b"
    r"|\bpipx\b|\bpoetry\b"
    r"|\bpipenv\b"
    r"|\bpip-install\s*:"
)
# A job runs Python tools when it sets up uv or runs `python -m`, pytest, ruff or basedpyright.
_PYTHON_TOOLS = re.compile(r"astral-sh/setup-uv@|\bpython\s+-m\b|\bpytest\b|\bruff\s|\bbasedpyright\b")
_JOB = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")
_SETUP_UV = "astral-sh/setup-uv@"
_PACKAGE_JOB = "ci.yml:package"
_PACKAGE_COMMANDS = [
    "uv build --wheel --out-dir dist --build-constraints build-constraints.txt --require-hashes",
    "uv export --locked --no-emit-project --output-file /tmp/runtime.txt",
    "uv venv /tmp/clean",
    "uv pip install --python /tmp/clean --no-build --require-hashes --requirements /tmp/runtime.txt",
    "uv pip install --python /tmp/clean --no-build --no-deps dist/*.whl",
    '/tmp/clean/bin/python -I -c "import importlib.metadata as m, copper_design as c;'
    " assert c.__file__.startswith('/tmp/clean/'), c.__file__; assert m.version('copper-design') == c.__version__\"",
    '/tmp/clean/bin/python -I -m copper_design palette --root "$GITHUB_WORKSPACE"',
    '/tmp/clean/bin/python -I -m copper_design render --root "$GITHUB_WORKSPACE"',
    "/tmp/clean/bin/python -I -m copper_design preview /tmp/preview.html",
    'git -C "$GITHUB_WORKSPACE" status --porcelain',
    'test -z "$(git -C "$GITHUB_WORKSPACE" status --porcelain)"',
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


def test_the_setup_command_installs_the_locked_wheels_only() -> None:
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


def _commands(job: list[str]) -> list[str]:
    """A job's shell commands in order: each `run:` line, or each line of a `run: |` block.

    A block runs on across blank lines and ends at the first line indented no
    deeper than its `run:` key.
    """
    commands: list[str] = []
    block = None
    for line in job:
        indent = len(line) - len(line.lstrip())
        if block is not None and (not line.strip() or indent > block):
            if line.strip():
                commands.append(line.strip())
            continue
        block = None
        text = line.strip().removeprefix("- ")
        if text.startswith("run:"):
            rest = text.removeprefix("run:").strip()
            if rest == "|":
                block = indent
            else:
                commands.append(rest)
    return commands


def test_the_package_job_runs_exactly_its_pinned_commands() -> None:
    job = _jobs()[_PACKAGE_JOB]
    assert _commands(job) == _PACKAGE_COMMANDS
    # From outside the checkout, so the import cannot come from the tree.
    assert any(line.strip() == "working-directory: /tmp" for line in job)


def test_a_run_block_runs_on_across_blank_lines() -> None:
    job = ["      - name: x", "        run: |", "          first", "", "          second", "      - run: third"]
    assert _commands(job) == ["first", "second", "third"]


def test_the_package_job_installs_only_with_its_pinned_commands() -> None:
    # Every installer anywhere in the job, a `with:` input such as setup-python's
    # `pip-install` included, is one of the pinned commands.
    installs = [text for line in _jobs()[_PACKAGE_JOB] if _INSTALLER.search(text := _code(line))]
    assert installs, "the package job installs nothing"
    strays = [text for text in installs if text not in _PACKAGE_COMMANDS]
    assert not strays, f"installs the package job does not pin: {strays}"


def _keys(lines: list[str], indent: int) -> list[str]:
    """The keys written at one indent, a step's leading `- ` counted as indent."""
    keys = []
    for line in lines:
        text = line[indent:] if line[:indent].strip(" -") == "" and len(line) > indent else ""
        match = re.match(r"([A-Za-z_-]+):", text)
        if match and not line[indent - 1 : indent].isalnum():
            keys.append(match.group(1))
    return keys


# The package job's own keys and each step's, in order: nothing may make a step
# conditional, tolerate failure, change its shell or its environment, and only
# the generator step runs from outside the checkout.
_PACKAGE_JOB_KEYS = ["runs-on", "timeout-minutes", "steps"]
_PACKAGE_STEP_KEYS = [
    ["uses"],
    ["uses", "with"],
    ["uses", "with"],
    ["name", "run"],
    ["name", "run"],
    ["name", "working-directory", "run"],
]


def test_the_package_job_and_its_steps_hold_only_their_pinned_keys() -> None:
    job = _jobs()[_PACKAGE_JOB]
    assert _keys(job, 4) == _PACKAGE_JOB_KEYS
    assert [_keys(step, 8) for step in _steps(job)] == _PACKAGE_STEP_KEYS
    (generator,) = [step for step in _steps(job) if "working-directory" in _keys(step, 8)]
    assert "        working-directory: /tmp" in generator


# The build backend's hashed constraint: mise.toml's `lock` task writes it from
# pyproject's [build-system] requires with this command, and the package job
# builds against it with --require-hashes.
_BUILD_CONSTRAINTS = "build-constraints.txt"
_LOCK_BUILD_CONSTRAINTS = (
    "python -c 'import tomllib; "
    'print(*tomllib.load(open("pyproject.toml", "rb"))["build-system"]["requires"], sep="\\n")\''
    " | uv pip compile - --generate-hashes --universal --no-header --no-annotate --quiet"
    " --output-file build-constraints.txt"
)


def test_the_lock_task_writes_the_build_constraints() -> None:
    assert _LOCK_BUILD_CONSTRAINTS in _task_lines(_mise()["tasks"]["lock"]["run"])


def test_the_build_constraints_pin_the_build_backend_with_hashes() -> None:
    requires = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["build-system"]["requires"]
    text = (_ROOT / _BUILD_CONSTRAINTS).read_text(encoding="utf-8").replace("\\\n", " ")
    entries = [line.split() for line in text.splitlines() if line.strip() and not line.startswith("#")]
    assert {entry[0] for entry in entries} == set(requires)
    for entry in entries:
        hashes = [part for part in entry[1:] if part.startswith("--hash=sha256:")]
        assert hashes and len(hashes) == len(entry) - 1, f"{entry[0]}: not every option is a sha256 hash"


def test_compiling_requirements_is_no_install_but_installing_is() -> None:
    assert not _INSTALLER.search("uv pip compile - --generate-hashes --output-file build-constraints.txt")
    assert _INSTALLER.search("uv pip install --python /tmp/clean x")
    assert _INSTALLER.search("uv pip sync requirements.txt")


def test_the_package_job_runs_on_the_requires_python_floor() -> None:
    project = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    floor = project["requires-python"].removeprefix(">=")
    versions = re.findall(r'^\s+python-version:\s*"([^"]+)"', "\n".join(_jobs()[_PACKAGE_JOB]), re.MULTILINE)
    assert versions == [floor, floor]


def test_the_build_backend_is_pinned_exactly() -> None:
    requires = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["build-system"]["requires"]
    assert requires, "pyproject names no build backend"
    loose = [
        requirement for requirement in requires if not re.fullmatch(r"[A-Za-z0-9_.-]+==[0-9][0-9A-Za-z.]*", requirement)
    ]
    assert not loose, f"build requirements without an exact pin: {loose}"


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
