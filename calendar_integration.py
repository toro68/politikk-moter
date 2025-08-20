#!/usr/bin/env python3
"""
Google Calendar integration for politiske møter.
"""

import os
import json
import tempfile
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Kalender-ID for politiske møter
CALENDAR_ID = "c_635df6a653ea35ad30afe385c7271817d5e0b664b38d65aa08642226f7b5e355@group.calendar.google.com"

class GoogleCalendarIntegration:
    """Håndterer Google Calendar API-integrasjon."""
    
    def __init__(self):
        self.service = None
        self.calendar_id = CALENDAR_ID
        
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
            
        except json.JSONDecodeError as e:
            print(f"❌ Ugyldig JSON i GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
            return False
        except Exception as e:
            print(f"❌ Google Calendar autentiseringsfeil: {e}")
            return False
    
    def create_meeting_event(self, meeting: Dict) -> Optional[str]:
        """Opprett et kalenderevent for et møte."""
        if not self.service:
            print("❌ Google Calendar service ikke tilgjengelig")
            return None
        
        try:
            # Bygg event-data
            event_data = self._build_event_data(meeting)
            
            # Opprett event
            event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event_data
            ).execute()
            
            event_id = event.get('id')
            print(f"✅ Kalenderevent opprettet: {meeting['title']} ({event_id})")
            return event_id
            
        except HttpError as e:
            print(f"❌ Google Calendar API-feil for '{meeting['title']}': {e}")
            return None
        except Exception as e:
            print(f"❌ Uventet feil ved opprettelse av kalenderevent: {e}")
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
        description += f"\nAutomatisk lagt til av Dagsorden-bot"
        
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
            
            events_result = self.service.events().list(
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
            
        except Exception as e:
            print(f"⚠️  Kunne ikke sjekke om event eksisterer: {e}")
            return False

def add_meetings_to_google_calendar(meetings: List[Dict], test_mode: bool = False) -> int:
    """
    Hovedfunksjon for å legge til møter i Google Calendar.
    
    Args:
        meetings: Liste med møter
        test_mode: Hvis True, skriv ut hva som ville blitt gjort uten å faktisk gjøre det
    
    Returns:
        Antall møter lagt til
    """
    if test_mode:
        print("🧪 TEST-MODUS: Google Calendar-integrasjon")
        print(f"Ville lagt til {len(meetings)} møter i kalender:")
        for meeting in meetings:
            print(f"  📅 {meeting['date']} {meeting.get('time', 'ingen tid')} - {meeting['title']} ({meeting['kommune']})")
        return len(meetings)
    
    calendar_integration = GoogleCalendarIntegration()
    return calendar_integration.add_meetings_to_calendar(meetings)

def main():
    """Test Google Calendar-integrasjon."""
    test_meetings = [
        {
            'title': 'Test-møte',
            'date': '2025-08-21',
            'time': '10:00',
            'location': 'Rådhuset',
            'kommune': 'Test kommune',
            'url': 'https://example.com'
        }
    ]
    
    print("🧪 Tester Google Calendar-integrasjon...")
    result = add_meetings_to_google_calendar(test_meetings, test_mode=True)
    print(f"Test fullført: {result} møter ville blitt lagt til")

if __name__ == '__main__':
    main()
