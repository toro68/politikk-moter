#!/usr/bin/env python3
"""Google Calendar integration for politiske møter."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

try:  # Local imports when running as module
    from .kommuner import KOMMUNE_CONFIGS
except ImportError:  # pragma: no cover - fallback for direct script execution
    from kommuner import KOMMUNE_CONFIGS  # type: ignore

# Kalender-ID for politiske møter (tidligere standard)
CALENDAR_ID = "c_635df6a653ea35ad30afe385c7271817d5e0b664b38d65aa08642226f7b5e355@group.calendar.google.com"

# Registrer tilgjengelige kalendrer. Flere kan legges til ved å oppdatere dette oppslaget.
CALENDAR_SOURCES: Dict[str, Dict[str, Optional[str]]] = {
    "arrangementer_sa": {
        "calendar_id": CALENDAR_ID,
        "description": "Arrangementer i Stavanger Aftenblad sin kalender",
    },
    "regional_kultur": {
        # Tillat at kalender-ID hentes fra miljøvariabel for fleksibilitet.
        "env": "GOOGLE_CALENDAR_REGIONAL_KULTUR_ID",
        "description": "Regional kulturkalender (eksempel)",
    },
    "turnus": {
        "env": "GOOGLE_CALENDAR_TURNUS_ID",
        "description": "Turnuskalender for politisk desk",
    },
}


def _build_calendar_keyword_map() -> Dict[str, str]:
    """Lag et oppslag for å gjenkjenne kommune-navn i kalendertekster."""
    keywords: Dict[str, str] = {}
    for config in KOMMUNE_CONFIGS:
        lower_name = config.name.lower()
        variants = {lower_name}
        if lower_name.endswith(" kommune"):
            variants.add(lower_name[: -len(" kommune")])
        variants.update({variant.replace(" kommune", "").strip() for variant in list(variants)})
        variants.update({variant.replace(" ", "") for variant in list(variants)})
        for variant in variants:
            if not variant or len(variant) < 2:
                continue
            keywords.setdefault(variant, config.name)
    return keywords


CALENDAR_KOMMUNE_KEYWORDS = _build_calendar_keyword_map()


def _infer_kommune_from_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    normalized = text.lower()
    for keyword, kommune_name in CALENDAR_KOMMUNE_KEYWORDS.items():
        if keyword in normalized:
            return kommune_name
    return None


def _canonicalize_kommune_name(candidate: Optional[str], *extra_texts: str) -> str:
    """Forsøk å kartlegge kandidattekst til et kjent kommunenavn."""
    for blob in (candidate, *extra_texts):
        kommune = _infer_kommune_from_text(blob)
        if kommune:
            return kommune
    if candidate:
        return candidate
    return "Manuelt lagt til"

class GoogleCalendarIntegration:
    """Håndterer Google Calendar API-integrasjon."""
    
    def __init__(self, calendar_id: str):
        self.service: Any = None
        self.calendar_id = calendar_id or CALENDAR_ID
        
    def authenticate(self) -> bool:
        """Autentiser med Google Calendar API via service account."""
        try:
            # Hent service account credentials fra miljøvariabel
            credentials_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            if not credentials_json:
                print("❌ GOOGLE_SERVICE_ACCOUNT_JSON environment variable ikke satt")
                return False
            
            # Parse JSON credentials
            credentials_info = json.loads(credentials_json)
            
            # Opprett credentials objekt
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/calendar']
            )
            
            # Bygg Calendar service
            self.service = build('calendar', 'v3', credentials=credentials)
            
            print("✅ Google Calendar API autentisering vellykket")
            return True
            
        except json.JSONDecodeError as exc:
            print(f"❌ Ugyldig JSON i GOOGLE_SERVICE_ACCOUNT_JSON: {exc}")
            return False
        except Exception as exc:  # pylint: disable=broad-except
            print(f"❌ Google Calendar autentiseringsfeil: {exc}")
            return False
    
    def get_calendar_meetings(self, days_ahead: int = 9) -> List[Dict]:
        """Hent møter fra Google Calendar for de neste dagene."""
        if not self.service:
            print("❌ Google Calendar service ikke tilgjengelig")
            return []
        
        try:
            # Sett tidsramme: i dag + neste N dager
            now = datetime.now()
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = today + timedelta(days=days_ahead + 1)
            
            time_min = today.isoformat() + 'Z'
            time_max = end_date.isoformat() + 'Z'
            
            # Hent events fra kalenderen
            events_result = self.service.events().list(  # pylint: disable=no-member
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime',
                maxResults=250
            ).execute()
            
            events = events_result.get('items', [])
            
            # Konverter til vårt møte-format
            meetings = []
            for event in events:
                meeting = self._convert_calendar_event_to_meeting(event)
                if meeting:
                    meetings.append(meeting)
            
            print(f"📅 Hentet {len(meetings)} møter fra Google Calendar")
            return meetings
            
        except Exception as exc:  # pylint: disable=broad-except
            print(f"❌ Feil ved henting fra Google Calendar: {exc}")
            return []
    
    def _convert_calendar_event_to_meeting(self, event) -> Optional[Dict]:
        """Konverter Google Calendar event til vårt møte-format."""
        try:
            # Hent møte-info
            title = event.get('summary', 'Kalender-møte')
            description = event.get('description', '')
            location = event.get('location', 'Ikke oppgitt')
            
            # Parse start-tid
            start = event.get('start', {})
            if 'dateTime' in start:
                # Timed event
                start_datetime = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                meeting_date = start_datetime.strftime('%Y-%m-%d')
                meeting_time = start_datetime.strftime('%H:%M')
            elif 'date' in start:
                # All-day event
                meeting_date = start['date']
                meeting_time = None
            else:
                return None
            
            # Finn kommune-navn (standard til "Manuelt lagt til")
            kommune = "Manuelt lagt til"

            # Prøv å parse kommune fra beskrivelse eller tittel
            kommune_match = re.search(r'Kommune:\s*([^,\n\r]+)', description, re.IGNORECASE)
            if kommune_match:
                kommune = kommune_match.group(1).strip()
            elif 'kommune' in title.lower():
                # Forsøk å finne kommune-navn i tittel
                parts = title.split('(')
                if len(parts) > 1:
                    potential_kommune = parts[-1].rstrip(')')
                    if 'kommune' in potential_kommune.lower():
                        kommune = potential_kommune
            
            # Hent event URL hvis tilgjengelig
            event_url = event.get('htmlLink', '')
            
            search_blob = " ".join(filter(None, [title, description, location]))
            kommune = _canonicalize_kommune_name(kommune, search_blob)

            return {
                'title': title,
                'date': meeting_date,
                'time': meeting_time,
                'location': location,
                'kommune': kommune,
                'url': event_url,
                'raw_text': f"Google Calendar: {title}"
            }
            
        except Exception as exc:  # pylint: disable=broad-except
            print(f"⚠️  Kunne ikke konvertere kalenderevent: {exc}")
            return None
    
    def _build_event_data(self, meeting: Dict) -> Dict:
        """Bygg event-data for Google Calendar."""
        # Parse meeting date
        meeting_date = datetime.strptime(meeting['date'], '%Y-%m-%d')
        
        # Håndter tid
        if meeting.get('time'):
            # Parse tid (format: HH:MM)
            time_parts = meeting['time'].split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            
            start_time = meeting_date.replace(hour=hour, minute=minute)
            # Anta 2 timer varighet hvis ikke spesifisert
            end_time = start_time + timedelta(hours=2)
        else:
            # Hele dagen event hvis ingen tid oppgitt
            start_time = meeting_date
            end_time = meeting_date + timedelta(days=1)
        
        # Bygg beskrivelse
        description = f"Møte: {meeting['title']}\n"
        description += f"Kommune: {meeting['kommune']}\n"
        if meeting.get('location') and meeting['location'] != "Ikke oppgitt":
            description += f"Sted: {meeting['location']}\n"
        if meeting.get('url'):
            description += f"Mer info: {meeting['url']}\n"
        description += "\nAutomatisk lagt til av Dagsorden-bot"
        
        # Event-data
        event_data = {
            'summary': f"{meeting['title']} ({meeting['kommune']})",
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Europe/Oslo',
            } if meeting.get('time') else {
                'date': start_time.strftime('%Y-%m-%d'),
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Europe/Oslo',
            } if meeting.get('time') else {
                'date': end_time.strftime('%Y-%m-%d'),
            },
            'source': {
                'title': 'Politiske møter scraper',
                'url': meeting.get('url', '')
            }
        }
        
        # Legg til lokasjon hvis tilgjengelig
        if meeting.get('location') and meeting['location'] != "Ikke oppgitt":
            event_data['location'] = meeting['location']
        
        return event_data
    
    def add_meetings_to_calendar(self, meetings: List[Dict]) -> int:
        """Legg til møter i Google Calendar."""
        if not self.authenticate():
            return 0
        
        added_count = 0
        
        for meeting in meetings:
            # Sjekk om event allerede eksisterer for å unngå duplikater
            if self._event_exists(meeting):
                print(f"⏭️  Event eksisterer allerede: {meeting['title']} ({meeting['date']})")
                continue
            
            event_id = self.create_meeting_event(meeting)
            if event_id:
                added_count += 1
        
        print(f"📅 Totalt lagt til {added_count} nye møter i Google Calendar")
        return added_count
    
    def _event_exists(self, meeting: Dict) -> bool:
        """Sjekk om et event allerede eksisterer i kalenderen."""
        if not self.service:
            return False
        
        try:
            # Søk etter events på samme dato med samme tittel
            meeting_date = datetime.strptime(meeting['date'], '%Y-%m-%d')
            time_min = meeting_date.isoformat() + 'T00:00:00Z'
            time_max = (meeting_date + timedelta(days=1)).isoformat() + 'T00:00:00Z'
            
            events_result = self.service.events().list(  # pylint: disable=no-member
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Sjekk om noen event har samme tittel og kommune
            meeting_summary = f"{meeting['title']} ({meeting['kommune']})"
            for event in events:
                if event.get('summary') == meeting_summary:
                    return True
            
            return False
            
        except Exception as exc:  # pylint: disable=broad-except
            print(f"⚠️  Kunne ikke sjekke om event eksisterer: {exc}")
            return False

    def create_meeting_event(self, meeting: Dict) -> Optional[str]:
        """Opprett et event i kalenderen og returner event-ID."""
        if not self.service:
            return None

        event_data = self._build_event_data(meeting)
        try:
            created_event = (
                self.service.events()  # pylint: disable=no-member
                .insert(calendarId=self.calendar_id, body=event_data)
                .execute()
            )
            return created_event.get("id")
        except HttpError as exc:
            print(f"❌ Feil ved oppretting av kalender-event: {exc}")
            return None

def get_calendar_meetings(days_ahead: int = 9, test_mode: bool = False) -> List[Dict]:
    """
    Hovedfunksjon for å hente møter fra Google Calendar.
    
    Args:
        days_ahead: Antall dager frem i tid å hente møter for
        test_mode: Hvis True, returner mock-data i stedet for å kontakte API
    
    Returns:
        Liste med møter fra kalenderen
    """
    if test_mode:
        print("🧪 TEST-MODUS: Google Calendar-lesing")
        # Returner noen mock calendar-møter for testing
        today = datetime.now().date()
        return [
            {
                'title': 'Test calendar-møte',
                'date': (today + timedelta(days=1)).strftime('%Y-%m-%d'),
                'time': '14:00',
                'location': 'Kontoret',
                'kommune': 'Manuelt lagt til',
                'url': 'https://calendar.google.com/calendar',
                'raw_text': 'Google Calendar: Test calendar-møte',
                'source': 'calendar:default',
            }
        ]
    
    calendar_integration = GoogleCalendarIntegration(CALENDAR_ID)
    if not calendar_integration.authenticate():
        return []
    
    meetings = calendar_integration.get_calendar_meetings(days_ahead)
    for meeting in meetings:
        meeting.setdefault('source', 'calendar:default')
    return meetings


def _resolve_calendar_id(source_id: str) -> Optional[str]:
    source = CALENDAR_SOURCES.get(source_id)
    if not source:
        print(f"⚠️  Ukjent kalender-kilde: {source_id}")
        return None

    calendar_id = source.get("calendar_id")
    if calendar_id:
        return calendar_id

    env_name = source.get("env")
    if env_name:
        env_value = os.getenv(env_name, "").strip()
        if env_value:
            return env_value
        print(f"⚠️  Kalender-ID ikke satt for {source_id}. Sett miljøvariabelen {env_name}.")
    return None


def get_calendar_meetings_for_sources(
    source_ids: Sequence[str],
    *,
    days_ahead: int = 9,
    test_mode: bool = False,
) -> List[Dict]:
    """Hent møter fra én eller flere kalenderkilder."""
    if test_mode:
        print("🧪 TEST-MODUS: Google Calendar-lesing (flere kilder)")
        today = datetime.now().date()
        meetings: List[Dict] = []
        for idx, source_id in enumerate(source_ids or ["arrangementer_sa"]):
            meetings.append(
                {
                    "title": f"Test calendar-møte ({source_id})",
                    "date": (today + timedelta(days=idx + 1)).strftime("%Y-%m-%d"),
                    "time": "14:00",
                    "location": "Kontoret",
                    "kommune": "Manuelt lagt til",
                    "url": "https://calendar.google.com/calendar",
                    "raw_text": f"Google Calendar ({source_id})",
                    "source": f"calendar:{source_id}",
                }
            )
        return meetings

    meetings: List[Dict] = []
    for source_id in source_ids:
        calendar_id = _resolve_calendar_id(source_id)
        if not calendar_id:
            continue

        calendar_integration = GoogleCalendarIntegration(calendar_id)
        if not calendar_integration.authenticate():
            continue

        for meeting in calendar_integration.get_calendar_meetings(days_ahead):
            meeting.setdefault("source", f"calendar:{source_id}")
            meetings.append(meeting)
    return meetings

def main():
    """Test Google Calendar-integrasjon."""
    print("🧪 Tester Google Calendar-lesing...")
    result = get_calendar_meetings(days_ahead=9, test_mode=True)
    print(f"Test fullført: {len(result)} møter hentet fra kalender")
    for meeting in result:
        print(f"  📅 {meeting['date']} {meeting.get('time', 'hele dagen')} - {meeting['title']} ({meeting['kommune']})")

if __name__ == '__main__':
    main()
