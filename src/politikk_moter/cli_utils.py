"""CLI helpers for common flag/env handling."""

from __future__ import annotations

import os
import sys
from typing import Optional, Sequence


def _argv(args: Optional[Sequence[str]] = None) -> Sequence[str]:
    return args if args is not None else sys.argv


def is_debug_mode(args: Optional[Sequence[str]] = None) -> bool:
    argv = _argv(args)
    return "--debug" in argv or "--test" in argv


def is_force_send(args: Optional[Sequence[str]] = None) -> bool:
    return "--force" in _argv(args)


def is_test_mode(args: Optional[Sequence[str]] = None, env: Optional[dict[str, str]] = None) -> bool:
    argv = _argv(args)
    env_map = env if env is not None else os.environ
    testing = env_map.get("TESTING", "").lower()
    return ("--debug" in argv or "--test" in argv) or testing in {"true", "1", "yes"}
