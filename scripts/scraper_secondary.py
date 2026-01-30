#!/usr/bin/env python3
"""Scraper som sender Slack-varsel til alternativ webhook."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import requests


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _bootstrap_package() -> None:
    root = Path(__file__).resolve().parents[1]
    src_dir = root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def send_to_slack_with_webhook(
    message: str,
    webhook_env: str = "SLACK_WEBHOOK_URL_SECONDARY",
    force_send: bool = False,
    test_mode: bool = False,
) -> bool:
    """Send melding til en spesifikk Slack webhook (angi env var navn).

    Args:
        message: formatert Slack-meldingstekst
        webhook_env: navnet på miljøvariabelen som inneholder webhook-URL
        force_send: hvis True, overstyrer test-modus
    """
    webhook_url = os.getenv(webhook_env)
    if not webhook_url:
        logger.warning("⚠️  %s environment variable ikke satt — ingen sending utført", webhook_env)
        return False

    if test_mode and not force_send:
        logger.info("🚫 Test-modus: Viser melding uten å sende til sekundær kanal")
        logger.info("%s", "=" * 40)
        logger.info("%s", message)
        logger.info("%s", "=" * 40)
        return True

    payload = {
        'text': message,
        'username': 'Politikk-bot-secondary',
        'icon_emoji': ':classical_building:'
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("✅ Melding sendt til sekundær Slack-kanal")
        return True
    except requests.exceptions.RequestException as e:
        logger.error("❌ Feil ved sending til sekundær Slack-kanal: %s", e)
        return False


def main():
    """Kjør sekundær scraper: hent møter, filtrer og send til alternativ Slack-kanal."""
    _bootstrap_package()
    from politikk_moter.cli_utils import is_debug_mode, is_force_send, is_test_mode
    from politikk_moter.scraper import (
        filter_meetings_by_date_range,
        format_slack_message,
        scrape_all_meetings,
    )

    force_send = is_force_send()
    debug_mode = is_debug_mode()
    test_mode = is_test_mode()

    logger.info("🏛️  Starter sekundær scraping av politiske møter...")

    # Gjenbruk eksisterende scraping-logikk
    all_meetings = scrape_all_meetings()
    filtered_meetings = filter_meetings_by_date_range(all_meetings, days_ahead=9)

    logger.info(
        "📊 Totalt funnet %s møter — filtrert til %s for de neste 10 dagene",
        len(all_meetings),
        len(filtered_meetings),
    )

    # Lag Slack-melding
    slack_message = format_slack_message(filtered_meetings)

    # Send til sekundær Slack-kanal
    sent = send_to_slack_with_webhook(
        slack_message,
        webhook_env="SLACK_WEBHOOK_URL_SECONDARY",
        force_send=force_send,
        test_mode=test_mode,
    )

    if not debug_mode and not sent:
        sys.exit(1)


if __name__ == '__main__':
    main()
