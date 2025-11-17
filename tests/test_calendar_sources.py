"""Tests som sikrer at kalenderkildene er korrekt konfigurert."""

from __future__ import annotations

from politikk_moter import calendar_integration as cal  # pylint: disable=import-error


EXPECTED_SOURCES = {
    "arrangementer_sa",
    "regional_kultur",
    "turnus",
}


def test_all_calendar_sources_present() -> None:
    assert set(cal.CALENDAR_SOURCES) == EXPECTED_SOURCES


def test_arrangementer_sa_uses_default_id() -> None:
    source = cal.CALENDAR_SOURCES["arrangementer_sa"]
    assert source["calendar_id"] == cal.CALENDAR_ID


def test_regional_kultur_uses_env_override() -> None:
    source = cal.CALENDAR_SOURCES["regional_kultur"]
    assert source.get("env") == "GOOGLE_CALENDAR_REGIONAL_KULTUR_ID"


def test_turnus_calendar_requires_env_override() -> None:
    source = cal.CALENDAR_SOURCES["turnus"]
    assert source.get("env") == "GOOGLE_CALENDAR_TURNUS_ID"
    assert source.get("calendar_id") is None


def test_resolve_calendar_id_finds_default_when_set(monkeypatch) -> None:
    calendar_id = cal._resolve_calendar_id("arrangementer_sa")  # pylint: disable=protected-access
    assert calendar_id == cal.CALENDAR_ID

    monkeypatch.setenv("GOOGLE_CALENDAR_REGIONAL_KULTUR_ID", "abc123@example.com")
    calendar_id_env = cal._resolve_calendar_id("regional_kultur")  # pylint: disable=protected-access
    assert calendar_id_env == "abc123@example.com"

    monkeypatch.setenv("GOOGLE_CALENDAR_TURNUS_ID", "turnus@example.com")
    calendar_id_turnus = cal._resolve_calendar_id("turnus")  # pylint: disable=protected-access
    assert calendar_id_turnus == "turnus@example.com"


def test_calendar_event_infers_kommune_from_title() -> None:
    integration = cal.GoogleCalendarIntegration(cal.CALENDAR_ID)
    event = {
        "summary": "Sirdal ungdomsråd",
        "description": "",
        "location": "",
        "start": {"date": "2025-11-24"},
    }

    meeting = integration._convert_calendar_event_to_meeting(event)  # pylint: disable=protected-access

    assert meeting is not None
    assert meeting["kommune"] == "Sirdal kommune"


def test_calendar_event_infers_kommune_from_location() -> None:
    integration = cal.GoogleCalendarIntegration(cal.CALENDAR_ID)
    event = {
        "summary": "Politisk møte",
        "description": "",
        "location": "Møterommet, Klepp kommune",
        "start": {"date": "2025-11-24"},
    }

    meeting = integration._convert_calendar_event_to_meeting(event)  # pylint: disable=protected-access

    assert meeting is not None
    assert meeting["kommune"] == "Klepp kommune"


def test_turnus_calendar_defaults_to_turnus_label() -> None:
    meetings = cal.get_calendar_meetings_for_sources(["turnus"], test_mode=True)
    assert meetings
    assert meetings[0]["kommune"] == "Turnus"
