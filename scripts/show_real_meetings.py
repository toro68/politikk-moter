#!/usr/bin/env python3
"""Verktøy for å vise detaljer om reelle møter fra scraping."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _bootstrap_package() -> None:
    root = Path(__file__).resolve().parents[1]
    src_dir = root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def show_real_meeting_details() -> None:
    """Vis detaljert informasjon om reelle møter."""
    _bootstrap_package()
    from politikk_moter.models import ensure_meeting
    from politikk_moter.scraper import scrape_all_meetings
    meetings = [ensure_meeting(m) for m in scrape_all_meetings()]

    logger.info("🔍 REELLE MØTER FUNNET:")
    logger.info("%s", "=" * 50)

    by_kommune = {}
    for meeting in meetings:
        kommune = meeting.kommune or "Ukjent"
        by_kommune.setdefault(kommune, []).append(meeting)

    for kommune, kommune_meetings in by_kommune.items():
        logger.info("\n📍 %s: %s møter", kommune, len(kommune_meetings))
        logger.info("%s", "-" * 40)

        for i, meeting in enumerate(kommune_meetings[:10]):
            logger.info("%s. Dato: %s", i + 1, meeting.date or "TBD")
            logger.info("   Tid: %s", meeting.time or "TBD")
            logger.info("   Tittel: %s", meeting.title or "Ingen tittel")
            logger.info("   Sted: %s", meeting.location or "Ikke oppgitt")
            logger.info("")

        if len(kommune_meetings) > 10:
            logger.info("   ... og %s møter til", len(kommune_meetings) - 10)


if __name__ == "__main__":
    show_real_meeting_details()
