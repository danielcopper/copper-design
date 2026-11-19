"""The suite runs with a home of its own and never touches the real one.

Before any test or fixture runs, HOME and the XDG base directories point into a
temporary directory. An audit hook then watches the whole run: any file opened,
listed, created, renamed or removed under the real home fails the run at its
end, except under the paths the run itself lives in (this repository, the
interpreter and the import path), which may sit below the home.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

REAL_HOME = Path.home().resolve()
_ROOT = Path(__file__).resolve().parents[1]
_EVENTS = {"open", "os.listdir", "os.scandir", "os.mkdir", "os.rename", "os.remove", "os.rmdir", "shutil.rmtree"}
_HOME_VARIABLES = ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME")


def _allowed_roots() -> tuple[Path, ...]:
    entries = [_ROOT, Path(sys.prefix), Path(sys.base_prefix), *(Path(entry) for entry in sys.path if entry)]
    return tuple({entry.resolve() for entry in entries})


class HomeAudit:
    """Records every access the audit hook sees under the real home outside the allowed roots."""

    def __init__(self, home: Path, allowed: tuple[Path, ...]) -> None:
        self.home = home
        self.allowed = allowed
        self.touched: list[str] = []

    def strays(self, path: object) -> bool:
        """Whether an access to this path is one the suite must not make."""
        if not isinstance(path, str | bytes | os.PathLike):
            return False
        try:
            resolved = Path(os.fsdecode(path)).resolve()
        except (OSError, ValueError):
            # Not a path the hook can place (too long, a null byte); the call
            # it watches raises on its own, and the hook must never raise.
            return False
        if not resolved.is_relative_to(self.home):
            return False
        return not any(resolved.is_relative_to(root) for root in self.allowed)

    def hook(self, event: str, args: tuple[object, ...]) -> None:
        if event in _EVENTS and args and self.strays(args[0]):
            self.touched.append(f"{event} {args[0]!r}")


_AUDIT = HomeAudit(REAL_HOME, ())
_TEMPORARY_HOME = Path(tempfile.mkdtemp(prefix="copper-design-home-"))


def pytest_configure() -> None:
    for variable in _HOME_VARIABLES:
        os.environ[variable] = str(_TEMPORARY_HOME / variable.lower())
    _AUDIT.allowed = _allowed_roots()
    sys.addaudithook(_AUDIT.hook)


def pytest_sessionfinish(session: pytest.Session) -> None:
    shutil.rmtree(_TEMPORARY_HOME, ignore_errors=True)
    if _AUDIT.touched:
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            reporter.ensure_newline()
            reporter.write_line(f"the suite touched the real home: {_AUDIT.touched[:20]}", red=True)
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


@pytest.fixture
def home_audit() -> HomeAudit:
    return _AUDIT
