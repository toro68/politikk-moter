"""Utilities for formatting scraper output."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Mapping, Sequence, Union, Optional

from .models import Meeting, ensure_meeting

TURNUS_CALENDAR_SOURCE = "calendar:turnus"


def _is_turnus_meeting(meeting: Meeting) -> bool:
    source = getattr(meeting, "source", None)
    if source == TURNUS_CALENDAR_SOURCE:
        return True
    kommune = (meeting.kommune or "").strip().lower()
    return kommune == "turnus"


MeetingInput = Union[Meeting, Mapping[str, object]]


def format_slack_message(
    meetings: Sequence[MeetingInput],
    *,
    heading_suffix: Optional[str] = None,
    expected_kommuner: Optional[Sequence[str]] = None,
) -> str:
    """Render a Slack message for an iterable of meetings."""
    normalized = [ensure_meeting(m) for m in meetings]

    heading = "📅 *Politiske møter de neste 10 dagene*"
    if heading_suffix:
        heading += f" – {heading_suffix}"

    message = f"{heading}\n\n"

    if not normalized:
        message += "Ingen møter funnet i perioden.\n"
        normalized_meetings: Sequence[Meeting] = []
    else:
        normalized_meetings = normalized

    non_turnus_meetings = [m for m in normalized_meetings if not _is_turnus_meeting(m)]
    turnus_meetings = [m for m in normalized_meetings if _is_turnus_meeting(m)]

    current_date = None
    kommune_counts = defaultdict(int)
    for meeting in non_turnus_meetings:
        meeting_date = datetime.strptime(meeting.date, '%Y-%m-%d')

        # Ny dato-overskrift
        if current_date != meeting.date:
            current_date = meeting.date
            date_str = meeting_date.strftime('%A %d. %B %Y')

            # Norske dagnavn
            date_str = date_str.replace('Monday', 'Mandag')
            date_str = date_str.replace('Tuesday', 'Tirsdag')
            date_str = date_str.replace('Wednesday', 'Onsdag')
            date_str = date_str.replace('Thursday', 'Torsdag')
            date_str = date_str.replace('Friday', 'Fredag')
            date_str = date_str.replace('Saturday', 'Lørdag')
            date_str = date_str.replace('Sunday', 'Søndag')

            message += f"\n*{date_str}*\n"

        display_title = f"{meeting.title} ({meeting.kommune})"
        if meeting.url:
            display_title = f"<{meeting.url}|{display_title}>"

        if meeting.time:
            message += f"• {display_title} - kl. {meeting.time}\n"
        else:
            message += f"• {display_title}\n"

        if meeting.location and meeting.location != "Ikke oppgitt":
            message += f"  {meeting.location}\n"

        kommune_counts[meeting.kommune or 'Ukjent kommune'] += 1

    for meeting in turnus_meetings:
        kommune_counts[meeting.kommune or 'Ukjent kommune'] += 1

    if expected_kommuner:
        for kommune in expected_kommuner:
            kommune_counts.setdefault(kommune, 0)

    if kommune_counts:
        message += "\n*Oppsummering per kommune*\n"
        for kommune in sorted(kommune_counts):
            count = kommune_counts[kommune]
            label = "møte" if count == 1 else "møter"
            message += f"• {kommune}: {count} {label}\n"

    if turnus_meetings:
        message += "\n*Turnus*\n"
        for meeting in turnus_meetings:
            meeting_date = datetime.strptime(meeting.date, '%Y-%m-%d')
            date_str = meeting_date.strftime('%A %d. %B %Y')
            date_str = date_str.replace('Monday', 'Mandag')
            date_str = date_str.replace('Tuesday', 'Tirsdag')
            date_str = date_str.replace('Wednesday', 'Onsdag')
            date_str = date_str.replace('Thursday', 'Torsdag')
            date_str = date_str.replace('Friday', 'Fredag')
            date_str = date_str.replace('Saturday', 'Lørdag')
            date_str = date_str.replace('Sunday', 'Søndag')

            line = f"• {date_str}: {meeting.title}"
            if meeting.time:
                line += f" - kl. {meeting.time}"
            message += f"{line}\n"
            if meeting.location and meeting.location != "Ikke oppgitt":
                message += f"  {meeting.location}\n"

    return message
