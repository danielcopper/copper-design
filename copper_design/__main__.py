"""The generator's command line: ``python -m copper_design <command>``.

- ``palette`` writes the palette token files from the parameter file, below the
  given root (the repository's root: the current directory by default).
- ``render`` writes the ports and the README swatch from the tokens, below the
  given root (the current directory by default).
- ``preview PATH`` writes the preview page.

A broken parameter file, token file or template ends the run with its message
and exit status 1.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from copper_design import preview, render, tokens

TOKEN_DIRECTORY = Path("copper_design") / "tokens"
"""Where `palette` writes, below its root."""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(path)


def _run(args: argparse.Namespace) -> None:
    if args.command == "palette":
        for name, text in tokens.palette_files().items():
            _write(args.root / TOKEN_DIRECTORY / name, text)
    elif args.command == "render":
        for relative, text in render.outputs().items():
            _write(args.root / relative, text)
    else:
        _write(args.path, preview.page())


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m copper_design", description="copper's generator")
    commands = parser.add_subparsers(dest="command", required=True)
    palette_parser = commands.add_parser("palette", help="write the palette token files from the parameter file")
    palette_parser.add_argument("--root", type=Path, default=Path(), help="the repository's root (default: here)")
    render_parser = commands.add_parser("render", help="write the ports and the README swatch from the tokens")
    render_parser.add_argument("--root", type=Path, default=Path(), help="where to write (default: here)")
    preview_parser = commands.add_parser("preview", help="write the preview page")
    preview_parser.add_argument("path", type=Path, help="the HTML file to write")
    args = parser.parse_args(argv)
    try:
        _run(args)
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
