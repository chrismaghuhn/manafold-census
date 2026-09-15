"""Direct entry point for the standalone offline Census Explorer."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from manafold_census.cli import main


def run(argv: Sequence[str] | None = None) -> int:
    """Delegate direct executable arguments to the existing Explorer CLI."""

    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "explorer":
        arguments = arguments[1:]
    return main(["explorer", *arguments])


if __name__ == "__main__":
    raise SystemExit(run())
