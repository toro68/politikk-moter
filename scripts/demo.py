#!/usr/bin/env python3
"""Demo-versjon som viser hvordan Slack-meldingen ser ut uten å sende til Slack."""

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



def demo_slack_message():
    """Generer og vis demo Slack-melding."""
    _bootstrap_package()
    from politikk_moter.mock_data import get_mock_meetings
    from politikk_moter.scraper import (
        filter_meetings_by_date_range,
        format_slack_message,
        scrape_all_meetings,
    )
    logger.info("🎭 Demo: Politiske møter Slack-melding")
    logger.info("%s", "=" * 50)
    
    # Hent møter
    meetings = scrape_all_meetings()
    logger.info("\nTotalt møter: %s", len(meetings))
    
    # Filtrer for neste 10 dager
    filtered_meetings = filter_meetings_by_date_range(meetings, days_ahead=9)
    logger.info("Møter neste 10 dager: %s", len(filtered_meetings))
    
    # Bruk mock-data hvis ingen møter funnet
    if not filtered_meetings:
        logger.warning("\n⚠️  Ingen møter i neste 10-dagers periode. Bruker mock-data...")
        mock_meetings = get_mock_meetings()
        filtered_meetings = filter_meetings_by_date_range(mock_meetings, days_ahead=9)
        logger.info("Lastet %s mock-møter for de neste 10 dagene", len(filtered_meetings))
    
    # Generer Slack-melding
    slack_message = format_slack_message(filtered_meetings)
    
    logger.info("\n📱 SLACK-MELDING:")
    logger.info("%s", "=" * 50)
    logger.info("%s", slack_message)
    logger.info("%s", "=" * 50)
    
    logger.info("\n✅ Demo fullført!")
    logger.info("\nFor å sende til ekte Slack:")
    logger.info("1. Sett opp Slack webhook")
    logger.info("2. Kjør: export SLACK_WEBHOOK_URL='din_webhook_url'")
    logger.info("3. Kjør: python scraper.py")

if __name__ == '__main__':
    demo_slack_message()
