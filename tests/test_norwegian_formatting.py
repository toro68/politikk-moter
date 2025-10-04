# pylint: disable=import-error
"""Test Norwegian date and time formatting in Slack messages."""

import pytest
from politikk_moter.scraper import format_slack_message


@pytest.mark.parametrize("month_num, norwegian_month", [
    ('01', 'januar'),
    ('02', 'februar'),
    ('03', 'mars'),
    ('04', 'april'),
    ('05', 'mai'),
    ('06', 'juni'),
    ('07', 'juli'),
    ('08', 'august'),
    ('09', 'september'),
    ('10', 'oktober'),
    ('11', 'november'),
    ('12', 'desember'),
])
def test_norwegian_month_names(month_num, norwegian_month):
    """Verify that all month names are translated to Norwegian."""
    meetings = [
        {
            'title': 'Testmøte',
            'date': f'2025-{month_num}-15',
            'time': '14:00',
            'kommune': 'Test kommune',
            'url': 'https://example.com',
            'location': 'Ikke oppgitt'
        }
    ]
    
    message = format_slack_message(meetings)
    
    # Check that the Norwegian month name is present
    assert norwegian_month in message.lower(), \
        f"Month name '{norwegian_month}' not found in message: {message}"
    
    # Check that English month names are NOT present
    english_months = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
    for english_month in english_months:
        assert english_month not in message, \
            f"English month name '{english_month}' found in message: {message}"


def test_norwegian_weekday_names():
    """Verify that weekday names are translated to Norwegian."""
    # Test one meeting for each weekday (using known dates)
    meetings = [
        {'title': 'Mandag', 'date': '2025-10-13', 'time': '10:00',  # Monday
         'kommune': 'Test', 'url': 'https://example.com', 'location': 'Ikke oppgitt'},
        {'title': 'Tirsdag', 'date': '2025-10-14', 'time': '10:00',  # Tuesday
         'kommune': 'Test', 'url': 'https://example.com', 'location': 'Ikke oppgitt'},
        {'title': 'Onsdag', 'date': '2025-10-15', 'time': '10:00',  # Wednesday
         'kommune': 'Test', 'url': 'https://example.com', 'location': 'Ikke oppgitt'},
        {'title': 'Torsdag', 'date': '2025-10-16', 'time': '10:00',  # Thursday
         'kommune': 'Test', 'url': 'https://example.com', 'location': 'Ikke oppgitt'},
        {'title': 'Fredag', 'date': '2025-10-17', 'time': '10:00',  # Friday
         'kommune': 'Test', 'url': 'https://example.com', 'location': 'Ikke oppgitt'},
        {'title': 'Lørdag', 'date': '2025-10-18', 'time': '10:00',  # Saturday
         'kommune': 'Test', 'url': 'https://example.com', 'location': 'Ikke oppgitt'},
        {'title': 'Søndag', 'date': '2025-10-19', 'time': '10:00',  # Sunday
         'kommune': 'Test', 'url': 'https://example.com', 'location': 'Ikke oppgitt'},
    ]
    
    message = format_slack_message(meetings)
    
    # Check that all Norwegian weekday names are present
    norwegian_weekdays = ['Mandag', 'Tirsdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lørdag', 'Søndag']
    for weekday in norwegian_weekdays:
        assert weekday in message, \
            f"Norwegian weekday '{weekday}' not found in message"
    
    # Check that English weekday names are NOT present
    english_weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for weekday in english_weekdays:
        assert weekday not in message, \
            f"English weekday '{weekday}' found in message"


def test_klepp_october_meeting():
    """Specific test for Klepp meetings in October (the user's reported issue)."""
    meetings = [
        {
            'title': 'Formannskapet',
            'date': '2025-10-13',
            'time': '16:00',
            'kommune': 'Klepp kommune',
            'url': 'https://opengov.360online.com/Meetings/KLEPP/Meetings/Details/111111',
            'location': 'Ikke oppgitt'
        }
    ]
    
    message = format_slack_message(meetings)
    
    # The date should be formatted as "Mandag 13. oktober 2025" (not "October")
    assert 'oktober' in message.lower(), \
        f"Norwegian 'oktober' not found in message: {message}"
    assert 'October' not in message, \
        f"English 'October' found in message when it should be 'oktober': {message}"
    assert 'Mandag' in message, \
        f"Norwegian weekday 'Mandag' not found in message: {message}"
