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
