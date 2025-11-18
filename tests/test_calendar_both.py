import pytest

from src.politikk_moter import calendar_integration


def test_both_calendar_sources_parsed():
    # Build meetings from sample data for both 'arrangementer_sa' and 'turnus' calendars.
    arr_meetings = calendar_integration.get_calendar_meetings_for_sources(['arrangementer_sa'], test_mode=True)
    turnus_meetings = calendar_integration.get_calendar_meetings_for_sources(['turnus'], test_mode=True)

    # There should be at least one arrangement and at least one turnus entry in test_mode fixtures.
    assert isinstance(arr_meetings, list), "arrangementer output should be a list"
    assert isinstance(turnus_meetings, list), "turnus output should be a list"

    # Ensure at least one Meeting from each source and that their 'source' attribute reflects the calendar.
    assert any(m.get('source', '').startswith('calendar:arrangementer') or m.get('source') == 'calendar:arrangementer_sa' for m in arr_meetings), (
        "No meetings from 'arrangementer' calendar were detected or labelled correctly"
    )
    assert any(m.get('source', '').startswith('calendar:turnus') or m.get('source') == 'calendar:turnus' for m in turnus_meetings), (
        "No meetings from 'turnus' calendar were detected or labelled correctly"
    )
