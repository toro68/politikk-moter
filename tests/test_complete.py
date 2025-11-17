#!/usr/bin/env python3
"""High-level tests for the politikk_moter scraper package."""

import sys
import textwrap
import types
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# pylint: disable=redefined-outer-name,unused-argument

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))

from politikk_moter import scraper  # noqa: E402  # pylint: disable=wrong-import-position,import-error
from politikk_moter.mock_data import get_mock_meetings  # noqa: E402  # pylint: disable=wrong-import-position,import-error
from politikk_moter.models import ensure_meeting  # noqa: E402  # pylint: disable=wrong-import-position,import-error


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
    titles = [meeting.title for meeting in filtered]

    assert titles == ["Kommunestyremøte", "Formannskap"], "Kun møter i 10-dagers vindu forventes"


def test_format_slack_message_includes_titles():
    """Slack-meldingen skal inneholde viktige felt fra møtedata."""
    sample_meetings = get_mock_meetings()[:2]
    message = scraper.format_slack_message(sample_meetings)

    assert "Politiske møter" in message
    for meeting in sample_meetings:
        assert meeting["title"] in message
        assert meeting["kommune"] in message

    assert "*Oppsummering per kommune*" in message
    assert "• Sauda kommune: 2 møter" in message


def test_format_slack_message_summarizes_multiple_kommuner():
    sample_meetings = [
        {
            "title": "Formannskapet",
            "date": "2025-10-01",
            "time": "10:00",
            "location": "Rådhuset",
            "kommune": "Sauda kommune",
            "url": "https://example.com/sauda",
            "raw_text": "Formannskapet",
        },
        {
            "title": "Kommunestyre",
            "date": "2025-10-02",
            "time": "12:00",
            "location": "Kommunestyresalen",
            "kommune": "Strand kommune",
            "url": "https://example.com/strand",
            "raw_text": "Kommunestyre",
        },
        {
            "title": "Eldreråd",
            "date": "2025-10-03",
            "time": None,
            "location": "Rådhuset",
            "kommune": "Sauda kommune",
            "url": "https://example.com/eldrerad",
            "raw_text": "Eldreråd",
        },
    ]

    message = scraper.format_slack_message(sample_meetings)

    assert "*Oppsummering per kommune*" in message
    assert "• Sauda kommune: 2 møter" in message
    assert "• Strand kommune: 1 møte" in message


def test_split_meetings_for_turnus_uses_named_kommuner():
    meetings = [
        ensure_meeting({"title": "Turnus", "date": "2025-01-01", "kommune": "Stavanger kommune"}),
        ensure_meeting({"title": "Andre", "date": "2025-01-01", "kommune": "Sauda kommune"}),
    ]

    turnus, other = scraper.split_meetings_for_turnus(meetings)

    assert [m.title for m in turnus] == ["Turnus"]
    assert [m.title for m in other] == ["Andre"]


def test_split_meetings_for_turnus_includes_calendar_source():
    meetings = [
        ensure_meeting(
            {
                "title": "Turnuskalender",
                "date": "2025-02-01",
                "kommune": "Manuelt lagt til",
                "source": "calendar:turnus",
            }
        ),
        ensure_meeting({"title": "Andre", "date": "2025-02-01", "kommune": "Sauda kommune"}),
    ]

    turnus, other = scraper.split_meetings_for_turnus(meetings)

    assert [m.title for m in turnus] == ["Turnuskalender"]
    assert [m.title for m in other] == ["Andre"]


def test_build_slack_batches_skips_second_when_no_other_meetings():
    meetings = [
        ensure_meeting({"title": "Turnus", "date": "2025-03-01", "kommune": "Stavanger kommune"})
    ]

    batches = scraper.build_slack_batches(meetings)

    assert len(batches) == 1
    assert batches[0][0] == "turnus"


def test_build_slack_batches_omits_empty_turnus_bucket():
    meetings = [
        ensure_meeting({"title": "Andre", "date": "2025-04-01", "kommune": "Sauda kommune"})
    ]

    batches = scraper.build_slack_batches(meetings)

    assert len(batches) == 1
    assert batches[0][0] == "ovrige"


def test_build_slack_batches_returns_placeholder_when_no_meetings():
    batches = scraper.build_slack_batches([])

    assert len(batches) == 1
    assert batches[0][0] == "alle"
    assert batches[0][1] == []


def test_format_slack_message_supports_heading_suffix():
    message = scraper.format_slack_message([], heading_suffix="Turnuskommuner (ingen)")

    assert "Turnuskommuner" in message.splitlines()[0]
    assert "Ingen møter" in message


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
    def fake_parser():
        return EmptyParser()

    monkeypatch.setattr(scraper, "MoteParser", fake_parser)
    monkeypatch.setattr(scraper, "parse_eigersund_meetings", lambda *args, **kwargs: [])
    mock_data_module = types.ModuleType("politikk_moter.mock_data")
    mock_data_module.get_mock_meetings = lambda: dummy_meetings
    monkeypatch.setitem(sys.modules, "politikk_moter.mock_data", mock_data_module)
    kommune_configs = [{"name": "Test kommune", "url": "https://example.com", "type": "acos"}]

    meetings = scraper.scrape_all_meetings(kommune_configs=kommune_configs, calendar_sources=[])

    expected = [ensure_meeting(m) for m in dummy_meetings]
    actual = [ensure_meeting(m) for m in meetings]

    assert actual == expected


def test_send_to_slack_in_test_mode_avoids_network(monkeypatch):
    """send_to_slack skal returnere True i test-modus uten å kalle Slack."""

    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.com/hook")

    def fail_post(*_args, **_kwargs):  # pragma: no cover - skal ikke nås
        pytest.fail("Slack-webhook skulle ikke bli kalt i test-modus")

    monkeypatch.setattr(scraper.requests, "post", fail_post)

    result = scraper.send_to_slack("Testmelding")

    assert result is True


def test_run_pipeline_skips_when_webhook_missing(monkeypatch, dummy_meetings):
    """Pipelines uten webhook skal hoppe over sending i debug/test uten å feile."""

    pipeline = types.SimpleNamespace(
        key="test",
        description="Test pipeline",
        kommune_groups=("core",),
        calendar_sources=(),
        slack_webhook_env="MISSING_HOOK",
    )

    monkeypatch.delenv("MISSING_HOOK", raising=False)

    monkeypatch.setattr(
        scraper,
        "collect_meetings_for_pipeline",
        lambda *args, **kwargs: dummy_meetings,
    )

    called = {"value": False}

    def fail_send(*_args, **_kwargs):  # pragma: no cover - skal ikke trigges
        called["value"] = True
        return True

    monkeypatch.setattr(scraper, "send_to_slack", fail_send)

    result = scraper.run_pipeline(pipeline, debug_mode=False)

    assert result is True
    assert called["value"] is False


def test_run_pipeline_uses_fallback_webhook(monkeypatch, dummy_meetings):
    pipeline = types.SimpleNamespace(
        key="fallback",
        description="Fallback pipeline",
        kommune_groups=("core",),
        calendar_sources=(),
        slack_webhook_env="MISSING_HOOK",
    )

    monkeypatch.delenv("MISSING_HOOK", raising=False)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.com/fallback")

    monkeypatch.setattr(
        scraper,
        "collect_meetings_for_pipeline",
        lambda *args, **kwargs: dummy_meetings,
    )

    send_calls = {"count": 0, "env": None, "url": None}

    def fake_send(message, *, webhook_env, webhook_url, **_kwargs):
        send_calls["count"] += 1
        send_calls["env"] = webhook_env
        send_calls["url"] = webhook_url
        return True

    monkeypatch.setattr(scraper, "send_to_slack", fake_send)

    result = scraper.run_pipeline(pipeline, debug_mode=False)

    assert result is True
    assert send_calls["count"] >= 1
    assert send_calls["env"] == "SLACK_WEBHOOK_URL"
    assert send_calls["url"] == "https://example.com/fallback"


def test_extended_group_contains_sandnes():
    import importlib

    kommuner = importlib.import_module("politikk_moter.kommuner")
    configs = kommuner.get_kommune_configs(["extended"])
    names = {config["name"] for config in configs}

    assert "Sandnes kommune" in names


def test_stavanger_custom_cards_parsed(monkeypatch):
    """Stavanger sin kortvisning skal gi møter uten duplikater."""

    html = textwrap.dedent(
        """
        <html>
            <body>
                <div class="meeting-card">
                    <div class="meeting-info">
                        Områdeutvalg Nord: Hana, Riska og Sviland 16.10.2025 kl. 19:00
                    </div>
                    <div class="meeting-meta">
                        <span class="date">16.10.2025</span>
                        <span class="time">19:00</span>
                    </div>
                </div>
            </body>
        </html>
        """
    ).strip()

    parser = scraper.MoteParser()

    class FakeResponse:  # pylint: disable=too-few-public-methods
        status_code = 200

        def raise_for_status(self):
            return None

        @property
        def content(self):  # noqa: D401 - tilfredsstill requests API
            return html.encode("utf-8")

    monkeypatch.setattr(parser.session, "get", lambda *_args, **_kwargs: FakeResponse())

    meetings = parser.parse_custom_site(
        "https://stavanger-elm.digdem.no/motekalender", "Stavanger kommune"
    )

    assert len(meetings) == 1
    meeting = meetings[0]

    assert meeting["title"] == "Områdeutvalg Nord: Hana, Riska og Sviland"
    assert meeting["date"] == "2025-10-16"
    assert meeting["time"] == "19:00"
