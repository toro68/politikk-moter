#!/usr/bin/env python3
"""Debug-skript for Hjelmeland kommune: henter HTML og viser hva parseren finner."""

from __future__ import annotations

import sys
from pathlib import Path

import requests


def _bootstrap_package() -> None:
    root = Path(__file__).resolve().parents[1]
    src_dir = root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def fetch_html(url: str) -> str:
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.text


def main() -> None:
    _bootstrap_package()
    from politikk_moter.scraper import MoteParser

    url = (
        "https://www.hjelmeland.kommune.no/politikk/moteplan-og-sakspapir/innsyn-moteplan/"
    )
    print(f"🔗 Henter {url}")

    html = fetch_html(url)
    print(f"✅ HTML lastet (lengde: {len(html)})")

    parser = MoteParser()
    meetings = parser.parse_acos_site(url, "Hjelmeland kommune")

    print(f"🧾 Parseren fant {len(meetings)} møter")
    for idx, meeting in enumerate(meetings[:10], start=1):
        title = meeting.get("title")
        date = meeting.get("date")
        time = meeting.get("time")
        location = meeting.get("location")
        print(f"{idx}. {date} {time or ''} – {title} ({location})")

    if len(meetings) > 10:
        print(f"... og {len(meetings) - 10} til")


if __name__ == "__main__":
    main()
