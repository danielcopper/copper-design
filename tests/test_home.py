"""The suite's own home (tests/conftest.py): HOME is a temporary directory, and the audit sees the real one."""

import os
from pathlib import Path

from conftest import REAL_HOME, HomeAudit

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


def test_the_audit_records_an_access_it_flags() -> None:
    audit = HomeAudit(REAL_HOME, (_ROOT,))
    audit.hook("open", (str(REAL_HOME / ".bashrc"), "r", 0))
    audit.hook("open", (str(_ROOT / "README.md"), "r", 0))
    audit.hook("os.chdir", (str(REAL_HOME),))
    assert audit.touched == [f"open {str(REAL_HOME / '.bashrc')!r}"]
