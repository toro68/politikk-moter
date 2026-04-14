"""Network test that validates configured kommune URLs are reachable."""

from __future__ import annotations

import os

import pytest
import requests

from politikk_moter.kommuner import get_kommune_configs


pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(
        os.getenv("RUN_NETWORK_TESTS") != "1" or os.getenv("GITHUB_ACTIONS") == "true",
        reason="Set RUN_NETWORK_TESTS=1 to run live URL checks locally; skipped in GitHub Actions.",
    ),
]


def test_configured_kommune_urls_are_reachable() -> None:
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

    seen: set[str] = set()
    failures: list[str] = []

    for config in get_kommune_configs([]):
        name = str(config.get("name") or "").strip() or "unknown"
        url = str(config.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)

        try:
            response = session.get(url, timeout=20, allow_redirects=True)
            if response.status_code >= 400:
                failures.append(
                    f"{name}: {url} -> {response.status_code} ({response.url})"
                )
        except requests.RequestException as exc:
            failures.append(f"{name}: {url} -> {exc.__class__.__name__}: {exc}")

    assert not failures, "Broken kommune links:\n" + "\n".join(failures)
