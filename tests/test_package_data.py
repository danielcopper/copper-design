"""The package ships every data file the generator reads.

The generator reads the parameter file, the token files and the templates
through importlib.resources, so an installed package must carry them:
pyproject's ``[tool.setuptools.package-data]`` names them by pattern. A data
file no pattern matches would be left out of the wheel, and the CI ``package``
job, which renders from an installed wheel, would fail only there.
"""

import tomllib
from fnmatch import fnmatch
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PACKAGE = _ROOT / "copper_design"


def test_every_data_file_of_the_package_is_package_data() -> None:
    pyproject = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    patterns = pyproject["tool"]["setuptools"]["package-data"]["copper_design"]
    data = [
        path.relative_to(_PACKAGE).as_posix()
        for path in _PACKAGE.rglob("*")
        if path.is_file() and path.suffix not in {".py", ".pyc"} and "__pycache__" not in path.parts
    ]
    assert data, "the package holds no data files"
    missing = [name for name in data if not any(fnmatch(name, pattern) for pattern in patterns)]
    assert not missing, f"not package data, so not in the wheel: {missing}"
