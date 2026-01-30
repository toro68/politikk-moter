#!/usr/bin/env python3
"""Debug-verktøy for å vise møtene som faktisk blir funnet fra scraping."""

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



def print_real_meetings():
    """Vis alle møter som faktisk blir funnet fra scraping"""
    _bootstrap_package()
    from politikk_moter.models import ensure_meeting
    from politikk_moter.scraper import scrape_all_meetings
    logger.info("🔍 Finner alle møter fra scraping...")
    
    meetings = [ensure_meeting(m) for m in scrape_all_meetings()]
    
    logger.info("\n📊 Totalt funnet: %s møter", len(meetings))
    logger.info("\n🏛️ Møter fra de forskjellige kildene:")
    
    # Grupper etter kommune
    by_kommune = {}
    for meeting in meetings:
        kommune = meeting.kommune or 'Ukjent'
        by_kommune.setdefault(kommune, []).append(meeting)
    
    for kommune, kommune_meetings in by_kommune.items():
        logger.info("\n📍 %s: %s møter", kommune, len(kommune_meetings))
        
        # Vis første 5 møter fra hver kommune
        for i, meeting in enumerate(kommune_meetings[:5]):
            logger.info(
                "  %s. %s %s - %s",
                i + 1,
                meeting.date or "TBD",
                meeting.time or "TBD",
                meeting.title or "Ingen tittel",
            )
        
        if len(kommune_meetings) > 5:
            logger.info("  ... og %s til", len(kommune_meetings) - 5)

if __name__ == "__main__":
    print_real_meetings()
