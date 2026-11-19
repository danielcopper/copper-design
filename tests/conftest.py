"""The suite runs with a home of its own and never touches the real one.

Before any test or fixture runs, HOME and the XDG base directories point into a
temporary directory. The audit hook of tests/home_audit.py then watches the
whole run, and an access under the real home fails it at its end, with the
accesses listed in the summary.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from home_audit import REAL_HOME, HomeAudit, allowed_roots, check_roots

pytest_plugins = ["pytester"]

_HOME_VARIABLES = ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME")


_AUDIT = HomeAudit(REAL_HOME, ())
_TEMPORARY_HOME = Path(tempfile.mkdtemp(prefix="copper-design-home-"))


def pytest_configure() -> None:
    for variable in _HOME_VARIABLES:
        os.environ[variable] = str(_TEMPORARY_HOME / variable.lower())
    _AUDIT.allowed = allowed_roots()
    check_roots(REAL_HOME, _AUDIT.allowed)
    sys.addaudithook(_AUDIT.hook)


def pytest_sessionfinish(session: pytest.Session) -> None:
    shutil.rmtree(_TEMPORARY_HOME, ignore_errors=True)
    if _AUDIT.touched:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    if _AUDIT.touched:
        terminalreporter.section("real home", red=True)
        terminalreporter.write_line(f"the suite touched the real home: {_AUDIT.touched[:20]}", red=True)


@pytest.fixture
def home_audit() -> HomeAudit:
    return _AUDIT
