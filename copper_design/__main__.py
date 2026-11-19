"""The generator's command line: ``python -m copper_design <command>``.

- ``palette`` writes the palette token files from the parameter file, into the
  package's token directory.
- ``render`` writes the ports and the README swatch from the tokens, below the
  given root (the current directory by default).
- ``preview PATH`` writes the preview page.
"""

import argparse
from collections.abc import Sequence
from pathlib import Path

from copper_design import preview, render, tokens


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(path)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m copper_design", description="copper's generator")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("palette", help="write the palette token files from the parameter file")
    render_parser = commands.add_parser("render", help="write the ports and the README swatch from the tokens")
    render_parser.add_argument("--root", type=Path, default=Path(), help="where to write (default: here)")
    preview_parser = commands.add_parser("preview", help="write the preview page")
    preview_parser.add_argument("path", type=Path, help="the HTML file to write")
    args = parser.parse_args(argv)

    if args.command == "palette":
        directory = Path(str(tokens.directory()))
        for name, text in render.palette_files().items():
            _write(directory / name, text)
    elif args.command == "render":
        for relative, text in render.outputs().items():
            _write(args.root / relative, text)
    else:
        _write(args.path, preview.page())


if __name__ == "__main__":
    main()
