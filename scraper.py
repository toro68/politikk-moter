#!/usr/bin/env python3
"""Entrypoint for running the politikk_moter scraper from the repository root."""

from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap_package() -> None:
    """Ensure the packaged sources under ``src/`` are importable."""
    root = Path(__file__).resolve().parent
    src_dir = root / "src"
    if str(src_dir) not in sys.path and src_dir.exists():
        sys.path.insert(0, str(src_dir))


def main() -> None:
    _bootstrap_package()
    from politikk_moter.scraper import main as package_main  # pylint: disable=import-error

    package_main()


if __name__ == "__main__":
    main()
