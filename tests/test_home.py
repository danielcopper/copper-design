"""The suite's own home: HOME is a temporary directory, and the audit sees the real one.

tests/conftest.py sets the home up and installs the audit from tests/home_audit.py.
"""

import os
import pwd
import shutil
from pathlib import Path

import pytest
from home_audit import REAL_HOME, HomeAudit, allowed_roots, check_roots

_ROOT = Path(__file__).resolve().parents[1]


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


def test_the_real_home_is_the_accounts_not_homes() -> None:
    # HOME points elsewhere during the run, so the audit takes the account's own.
    assert Path(pwd.getpwuid(os.getuid()).pw_dir).resolve() == REAL_HOME


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
    pytester.makepyfile(
        test_probe=(
            "import os\nfrom home_audit import REAL_HOME\n\ndef test_probe() -> None:\n    os.listdir(REAL_HOME)\n"
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
