#!/usr/bin/env python3
"""Check that configured kommune URLs respond (HTTP status < 400)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

import requests


def _bootstrap_package() -> None:
    root = Path(__file__).resolve().parents[1]
    src_dir = root / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


@dataclass(frozen=True)
class UrlCheck:
    name: str
    url: str


def _get_configured_urls() -> Sequence[UrlCheck]:
    _bootstrap_package()
    from politikk_moter.kommuner import get_kommune_configs  # pylint: disable=import-error

    configs = get_kommune_configs([])
    seen: set[str] = set()
    checks: List[UrlCheck] = []
    for config in configs:
        url = str(config.get("url") or "").strip()
        name = str(config.get("name") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        checks.append(UrlCheck(name=name or url, url=url))
    return checks


def check_urls(checks: Iterable[UrlCheck]) -> int:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        }
    )

    failures: List[str] = []
    for item in checks:
        try:
            response = session.get(item.url, timeout=20, allow_redirects=True)
            status = response.status_code
            final_url = response.url
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
            ok = status < 400
            marker = "OK" if ok else "FAIL"
            print(f"{marker} {status} {item.name} {item.url} -> {final_url} [{content_type or 'unknown'}]")
            if not ok:
                failures.append(f"{item.name}: {item.url} ({status})")
        except requests.RequestException as exc:
            print(f"FAIL ERR {item.name} {item.url} ({exc.__class__.__name__}: {exc})")
            failures.append(f"{item.name}: {item.url} ({exc.__class__.__name__})")

    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    return 0


def main() -> None:
    checks = _get_configured_urls()
    raise SystemExit(check_urls(checks))


if __name__ == "__main__":
    main()

