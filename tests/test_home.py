"""The suite's own home: HOME is a temporary directory, and the audit sees the real one.

tests/conftest.py sets the home up and installs the audit from tests/home_audit.py.
"""

import os
import pwd
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from home_audit import REAL_HOME, ROOT, HomeAudit, allowed_roots, check_roots

_ROOT = ROOT


def test_the_suite_runs_with_a_home_of_its_own() -> None:
    assert Path.home().resolve() != REAL_HOME
    for variable in ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
        assert not Path(os.environ[variable]).resolve().is_relative_to(REAL_HOME), variable


def test_the_audit_flags_paths_under_the_real_home_only(home_audit: HomeAudit) -> None:
    assert home_audit.strays(REAL_HOME / ".config" / "some-app" / "settings.json")
    assert home_audit.strays(str(REAL_HOME))
    assert not home_audit.strays(_ROOT / "pyproject.toml")
    assert not home_audit.strays(Path(os.environ["HOME"]) / "file")
    assert not home_audit.strays(3)
    assert not home_audit.strays("a\0b")


def test_the_audit_records_an_access_it_flags() -> None:
    audit = HomeAudit(REAL_HOME, (_ROOT,))
    audit.hook("open", (str(REAL_HOME / ".bashrc"), "r", 0))
    audit.hook("open", (str(_ROOT / "README.md"), "r", 0))
    audit.hook("os.chdir", (str(REAL_HOME),))
    assert audit.touched == [f"open {str(REAL_HOME / '.bashrc')!r}"]


def test_the_real_home_is_the_accounts_not_homes(tmp_path: Path) -> None:
    # A run whose HOME points elsewhere (a child of this suite) still finds the account's own home.
    result = subprocess.run(
        [sys.executable, "-c", "import home_audit; print(home_audit.REAL_HOME)"],
        env={**os.environ, "HOME": str(tmp_path), "PYTHONPATH": str(Path(__file__).parent)},
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == str(Path(pwd.getpwuid(os.getuid()).pw_dir).resolve())


@pytest.mark.parametrize(
    ("event", "args"),
    [
        ("os.rename", (str(_ROOT / "a"), str(REAL_HOME / "b"), None, None)),
        ("os.symlink", (str(_ROOT / "a"), str(REAL_HOME / "b"), None)),
        ("os.link", (str(_ROOT / "a"), str(REAL_HOME / "b"), None, None)),
        ("os.chmod", (str(REAL_HOME / "b"), 0o600, None)),
        ("os.chown", (str(REAL_HOME / "b"), 0, 0, None)),
        ("os.utime", (str(REAL_HOME / "b"), None, None, None)),
        ("os.truncate", (str(REAL_HOME / "b"), 0)),
        ("open", (str(REAL_HOME / "x\0y"), "r", 0)),
        ("open", (str(REAL_HOME / "b"), "r", 0)),
        ("os.listdir", (str(REAL_HOME),)),
        ("os.scandir", (str(REAL_HOME),)),
        ("os.mkdir", (str(REAL_HOME / "b"), 0o777, None)),
        ("os.remove", (str(REAL_HOME / "b"), None)),
        ("os.rmdir", (str(REAL_HOME / "b"), None)),
        ("shutil.rmtree", (str(REAL_HOME / "b"), None)),
        ("os.setxattr", (str(REAL_HOME / "b"), "user.x", b"1", 0)),
        ("os.removexattr", (str(REAL_HOME / "b"), "user.x")),
        ("sqlite3.connect", (str(REAL_HOME / "b.db"),)),
    ],
)
def test_the_audit_sees_every_path_a_call_writes(event: str, args: tuple[object, ...]) -> None:
    audit = HomeAudit(REAL_HOME, (_ROOT,))
    audit.hook(event, args)
    assert audit.touched, f"{event} {args} went unrecorded"


def test_the_audit_places_a_path_relative_to_a_directory_descriptor(tmp_path: Path) -> None:
    # A stand-in home, so the test opens no directory of the real one.
    audit = HomeAudit(tmp_path, ())
    descriptor = os.open(tmp_path, os.O_RDONLY)
    try:
        audit.hook("os.mkdir", ("new", 0o777, descriptor))
        audit.hook("os.mkdir", ("new", 0o777, None))
    finally:
        os.close(descriptor)
    assert audit.touched == ["os.mkdir 'new'"]


def test_an_allowed_root_holding_the_real_home_is_refused() -> None:
    check_roots(REAL_HOME, allowed_roots())
    for root in (REAL_HOME, REAL_HOME.parent, Path("/")):
        with pytest.raises(ValueError, match="would allow all of the real home"):
            check_roots(REAL_HOME, (_ROOT, root))


def _suite_copy(pytester: pytest.Pytester) -> None:
    for name in ("conftest.py", "home_audit.py"):
        shutil.copy(Path(__file__).with_name(name), pytester.path / name)


def test_a_run_that_touches_the_real_home_fails_and_says_so(pytester: pytest.Pytester) -> None:
    _suite_copy(pytester)
    # Opening a path under the real home that does not exist: the audit sees the call, the home is left alone.
    pytester.makepyfile(
        test_probe=(
            "from home_audit import REAL_HOME\n\ndef test_probe() -> None:\n"
            "    try:\n        open(REAL_HOME / '.copper-design-probe-missing')\n"
            "    except OSError:\n        pass\n"
        )
    )
    result = pytester.runpytest_subprocess("-p", "no:cacheprovider")
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    assert any(line.startswith("the suite touched the real home: ") for line in result.outlines), result.outlines


def test_a_run_that_keeps_off_the_real_home_passes(pytester: pytest.Pytester) -> None:
    _suite_copy(pytester)
    pytester.makepyfile(
        test_probe="from pathlib import Path\n\ndef test_probe() -> None:\n    Path.home().mkdir(exist_ok=True)\n"
    )
    result = pytester.runpytest_subprocess("-p", "no:cacheprovider")
    assert result.ret == pytest.ExitCode.OK, result.outlines


class _BrokenPath:
    def __fspath__(self) -> str:
        raise RuntimeError("no path")


def test_the_audit_never_raises_on_a_path_it_cannot_read() -> None:
    audit = HomeAudit(REAL_HOME, (_ROOT,))
    audit.hook("open", (_BrokenPath(), "r", 0))
    assert audit.touched == []


def test_a_run_whose_import_path_holds_the_real_home_is_refused(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    _suite_copy(pytester)
    pytester.makepyfile(test_probe="def test_probe() -> None:\n    pass\n")
    monkeypatch.setenv("PYTHONPATH", "/")
    result = pytester.runpytest_subprocess("-p", "no:cacheprovider")
    assert result.ret != pytest.ExitCode.OK
    assert "would allow all of the real home" in "\n".join(result.errlines + result.outlines)


def test_an_access_in_another_plugins_session_end_still_fails_the_run(pytester: pytest.Pytester) -> None:
    _suite_copy(pytester)
    pytester.makepyfile(
        late=(
            "from home_audit import REAL_HOME\n\n"
            "def pytest_sessionfinish() -> None:\n"
            "    try:\n        open(REAL_HOME / '.copper-design-probe-missing')\n"
            "    except OSError:\n        pass\n"
        ),
        test_probe="def test_probe() -> None:\n    pass\n",
    )
    result = pytester.runpytest_subprocess("-p", "no:cacheprovider", "-p", "late")
    assert result.ret == pytest.ExitCode.TESTS_FAILED, result.outlines


def test_a_temporary_home_that_cannot_be_removed_is_reported(pytester: pytest.Pytester) -> None:
    _suite_copy(pytester)
    pytester.makepyfile(
        test_probe=(
            "from pathlib import Path\n\n"
            "def test_probe() -> None:\n"
            "    locked = Path.home() / 'locked'\n"
            "    locked.mkdir(parents=True)\n"
            "    (locked / 'file').write_text('x')\n"
            "    locked.chmod(0o500)\n"
            "    (Path(__file__).parent / 'home.txt').write_text(str(Path.home()))\n"
        )
    )
    try:
        result = pytester.runpytest_subprocess("-p", "no:cacheprovider")
    finally:
        home = Path((pytester.path / "home.txt").read_text())
        (home / "locked").chmod(stat.S_IRWXU)
        shutil.rmtree(home)
    assert any(line.startswith("could not remove the temporary home") for line in result.outlines), result.outlines
