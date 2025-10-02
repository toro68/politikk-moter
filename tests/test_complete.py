#!/usr/bin/env python3
"""High-level tests for the politikk_moter scraper package."""

import os
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))

from politikk_moter import scraper  # noqa: E402  # pylint: disable=wrong-import-position
from politikk_moter.mock_data import get_mock_meetings  # noqa: E402  # pylint: disable=wrong-import-position


@pytest.fixture(autouse=True)
def enable_test_mode(monkeypatch):
    """Forsikre at testene kjører i trygg test-modus."""
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setattr(scraper.sys, "argv", ["pytest"], raising=False)
    yield
    monkeypatch.delenv("TESTING", raising=False)


@pytest.fixture
def dummy_meetings():
    """Tilby et sett deterministiske møter for testene."""
    today = datetime.now().date()
    return [
        {
            "title": "Kommunestyremøte",
            "date": today.strftime("%Y-%m-%d"),
            "time": "10:00",
            "location": "Rådhuset",
            "kommune": "Test kommune",
            "url": "https://example.com/meeting/today",
            "raw_text": "Kommunestyremøte"
        },
        {
            "title": "Formannskap",
            "date": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
            "time": "12:00",
            "location": "Kommunestyresalen",
            "kommune": "Test kommune",
            "url": "https://example.com/meeting/formannskap",
            "raw_text": "Formannskap"
        },
        {
            "title": "Helseutvalg",
            "date": (today + timedelta(days=15)).strftime("%Y-%m-%d"),
            "time": None,
            "location": "Helsehuset",
            "kommune": "Test kommune",
            "url": "https://example.com/meeting/helse",
            "raw_text": "Helseutvalg"
        },
    ]


def test_filter_meetings_by_date_range_limits_window(dummy_meetings):
    """filter_meetings_by_date_range skal filtrere bort møter utenfor perioden."""
    filtered = scraper.filter_meetings_by_date_range(dummy_meetings, days_ahead=10)
    titles = [meeting["title"] for meeting in filtered]

    assert titles == ["Kommunestyremøte", "Formannskap"], "Kun møter i 10-dagers vindu forventes"


def test_format_slack_message_includes_titles():
    """Slack-meldingen skal inneholde viktige felt fra møtedata."""
    sample_meetings = get_mock_meetings()[:2]
    message = scraper.format_slack_message(sample_meetings)

    assert "Politiske møter" in message
    for meeting in sample_meetings:
        assert meeting["title"] in message
        assert meeting["kommune"] in message


def test_scrape_all_meetings_falls_back_to_mock(monkeypatch, dummy_meetings):
    """Når scraping ikke gir resultater skal mock-data brukes som fallback."""

    class EmptyParser:
        def parse_acos_site(self, *args, **kwargs):
            return []

        def parse_custom_site(self, *args, **kwargs):
            return []

    monkeypatch.setattr(scraper, "CALENDAR_AVAILABLE", False, raising=False)
    monkeypatch.setattr(scraper, "PLAYWRIGHT_AVAILABLE", False, raising=False)
    monkeypatch.setattr(scraper, "EIGERSUND_AVAILABLE", False, raising=False)
    monkeypatch.setattr(scraper, "MoteParser", lambda: EmptyParser())
    monkeypatch.setattr(scraper, "parse_eigersund_meetings", lambda *args, **kwargs: [])
    mock_data_module = types.ModuleType("politikk_moter.mock_data")
    mock_data_module.get_mock_meetings = lambda: dummy_meetings
    monkeypatch.setitem(sys.modules, "politikk_moter.mock_data", mock_data_module)
    monkeypatch.setattr(
        scraper,
        "KOMMUNE_URLS",
        [{"name": "Test kommune", "url": "https://example.com", "type": "acos"}],
        raising=False,
    )

    meetings = scraper.scrape_all_meetings()

    assert meetings == dummy_meetings


def test_send_to_slack_in_test_mode_avoids_network(monkeypatch):
    """send_to_slack skal returnere True i test-modus uten å kalle Slack."""

    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.com/hook")

    def fail_post(*args, **kwargs):  # pragma: no cover - skal ikke nås
        pytest.fail("Slack-webhook skulle ikke bli kalt i test-modus")

    monkeypatch.setattr(scraper.requests, "post", fail_post)

    result = scraper.send_to_slack("Testmelding")

    assert result is True
