#!/usr/bin/env python3
"""Scraper som sender Slack-varsel til alternativ webhook."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from politikk_moter.scraper import (  # pylint: disable=import-error
    filter_meetings_by_date_range,
    format_slack_message,
    scrape_all_meetings,
)


def send_to_slack_with_webhook(message: str, webhook_env: str = 'SLACK_WEBHOOK_URL_SECONDARY', force_send: bool = False) -> bool:
    """Send melding til en spesifikk Slack webhook (angi env var navn).

    Args:
        message: formatert Slack-meldingstekst
        webhook_env: navnet på miljøvariabelen som inneholder webhook-URL
        force_send: hvis True, overstyrer test-modus
    """
    webhook_url = os.getenv(webhook_env)
    if not webhook_url:
        print(f"⚠️  {webhook_env} environment variable ikke satt — ingen sending utført")
        return False

    # Test-modus beskytter mot utilsiktet sending
    is_test_mode = (
        '--debug' in sys.argv or
        '--test' in sys.argv or
        os.getenv('TESTING', '').lower() in ['true', '1', 'yes']
    )

    if is_test_mode and not force_send:
        print("🚫 Test-modus: Viser melding uten å sende til sekundær kanal")
        print("=" * 40)
        print(message)
        print("=" * 40)
        return True

    payload = {
        'text': message,
        'username': 'Politikk-bot-secondary',
        'icon_emoji': ':classical_building:'
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        print("✅ Melding sendt til sekundær Slack-kanal")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Feil ved sending til sekundær Slack-kanal: {e}")
        return False


def main():
    """Kjør sekundær scraper: hent møter, filtrer og send til alternativ Slack-kanal."""
    force_send = '--force' in sys.argv
    debug_mode = '--debug' in sys.argv or '--test' in sys.argv

    print("🏛️  Starter sekundær scraping av politiske møter...")

    # Gjenbruk eksisterende scraping-logikk
    all_meetings = scrape_all_meetings()
    filtered_meetings = filter_meetings_by_date_range(all_meetings, days_ahead=9)

    print(f"📊 Totalt funnet {len(all_meetings)} møter — filtrert til {len(filtered_meetings)} for de neste 10 dagene")

    # Lag Slack-melding
    slack_message = format_slack_message(filtered_meetings)

    # Send til sekundær Slack-kanal
    sent = send_to_slack_with_webhook(slack_message, webhook_env='SLACK_WEBHOOK_URL_SECONDARY', force_send=force_send)

    if not debug_mode and not sent:
        sys.exit(1)


if __name__ == '__main__':
    main()
