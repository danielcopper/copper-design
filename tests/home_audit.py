"""The audit that keeps the suite off the real home; tests/conftest.py installs it for every run.

The real home is the account's (from the password database), not HOME, which
the suite points elsewhere and a child run inherits. The hook looks at the path
arguments of the calls in EVENTS: those that open a file or a database, read a
directory, or create, write, move or remove one. It places a path given
relative to a directory descriptor through /proc/self/fd and skips one it
cannot place there (no /proc, or ``os.open`` with ``dir_fd``, whose audit event
carries no descriptor). It records an access under the real home outside the
paths the run itself lives in, and it never raises: a path it cannot resolve is
judged by its text, one it cannot even read is skipped. Child processes are not
watched; they inherit the temporary HOME.
"""

import os
import pwd
import sys
from pathlib import Path

REAL_HOME = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
ROOT = Path(__file__).resolve().parents[1]

# Each audited call and where its arguments hold paths: (path index, the index
# of the directory descriptor it is relative to, or None).
EVENTS: dict[str, tuple[tuple[int, int | None], ...]] = {
    "open": ((0, None),),
    "os.listdir": ((0, None),),
    "os.scandir": ((0, None),),
    "os.mkdir": ((0, 2),),
    "os.rename": ((0, 2), (1, 3)),
    "os.remove": ((0, 1),),
    "os.rmdir": ((0, 1),),
    "shutil.rmtree": ((0, 1),),
    "os.symlink": ((0, None), (1, 2)),
    "os.link": ((0, 2), (1, 3)),
    "os.chmod": ((0, 2),),
    "os.chown": ((0, 3),),
    "os.utime": ((0, 3),),
    "os.truncate": ((0, None),),
    "os.setxattr": ((0, None),),
    "os.removexattr": ((0, None),),
    "sqlite3.connect": ((0, None),),
}


def allowed_roots() -> tuple[Path, ...]:
    """The paths the run itself lives in: this repository, the interpreter and the import path."""
    entries = [ROOT, Path(sys.prefix), Path(sys.base_prefix), *(Path(entry) for entry in sys.path if entry)]
    return tuple({entry.resolve() for entry in entries})


def check_roots(home: Path, roots: tuple[Path, ...]) -> None:
    """Raise if an allowed root is the home or holds it: the audit would then see nothing."""
    wide = [root for root in roots if home.is_relative_to(root)]
    if wide:
        raise ValueError(f"allowed roots {wide} would allow all of the real home {home}")


def _place(path: object, descriptor: object) -> Path | None:
    """Where a path argument points, as well as it can be told without raising."""
    if not isinstance(path, str | bytes | os.PathLike):
        return None
    try:
        text = os.fsdecode(path)
    except Exception:  # a path object whose __fspath__ fails: the hook must not raise for it
        return None
    if isinstance(descriptor, int) and descriptor >= 0 and not os.path.isabs(text.replace("\0", "")):
        try:
            text = os.path.join(os.readlink(f"/proc/self/fd/{descriptor}"), text)
        except OSError:
            return None
    try:
        return Path(os.path.realpath(text))
    except (OSError, ValueError, RuntimeError):
        return Path(os.path.abspath(text))


class HomeAudit:
    """Records every access the audit hook sees under the real home outside the allowed roots."""

    def __init__(self, home: Path, allowed: tuple[Path, ...]) -> None:
        self.home = home
        self.allowed = allowed
        self.touched: list[str] = []

    def strays(self, path: object, descriptor: object = None) -> bool:
        """Whether an access to this path is one the suite must not make."""
        placed = _place(path, descriptor)
        if placed is None or not placed.is_relative_to(self.home):
            return False
        return not any(placed.is_relative_to(root) for root in self.allowed)

    def hook(self, event: str, args: tuple[object, ...]) -> None:
        for index, descriptor in EVENTS.get(event, ()):
            if index < len(args):
                fd = args[descriptor] if descriptor is not None and descriptor < len(args) else None
                if self.strays(args[index], fd):
                    self.touched.append(f"{event} {args[index]!r}")
