#!/usr/bin/env python3
"""Verktøy for å vise detaljer om reelle møter fra scraping."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from politikk_moter.models import ensure_meeting  # pylint: disable=import-error
from politikk_moter.scraper import scrape_all_meetings  # pylint: disable=import-error


def show_real_meeting_details() -> None:
    """Vis detaljert informasjon om reelle møter."""
    meetings = [ensure_meeting(m) for m in scrape_all_meetings()]

    print("🔍 REELLE MØTER FUNNET:")
    print("=" * 50)

    by_kommune = {}
    for meeting in meetings:
        kommune = meeting.kommune or "Ukjent"
        by_kommune.setdefault(kommune, []).append(meeting)

    for kommune, kommune_meetings in by_kommune.items():
        print(f"\n📍 {kommune}: {len(kommune_meetings)} møter")
        print("-" * 40)

        for i, meeting in enumerate(kommune_meetings[:10]):
            print(f"{i + 1}. Dato: {meeting.date or 'TBD'}")
            print(f"   Tid: {meeting.time or 'TBD'}")
            print(f"   Tittel: {meeting.title or 'Ingen tittel'}")
            print(f"   Sted: {meeting.location or 'Ikke oppgitt'}")
            print()

        if len(kommune_meetings) > 10:
            print(f"   ... og {len(kommune_meetings) - 10} møter til")


if __name__ == "__main__":
    show_real_meeting_details()
