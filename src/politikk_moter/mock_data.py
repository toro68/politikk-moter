#!/usr/bin/env python3
"""
Mockdata for testing og demo av Slack-integrasjon.
Denne kan erstattes med ekte scraping når sidene blir mer tilgjengelige.
"""

from datetime import datetime, timedelta
from typing import List, Dict

def get_mock_meetings() -> List[Dict]:
    """Returnerer mock møtedata for testing og demo."""
    
    # Basert på ekte data fra fetch_webpage
    today = datetime.now().date()
    
    mock_meetings = [
        {
            'title': 'Ungdomsrådet',
            'date': '2025-08-20',
            'time': '09:00',
            'location': 'Formannskapssalen',
            'kommune': 'Sauda kommune',
            'raw_text': 'Ungdomsrådet, 20.08.2025, kl. 09:00'
        },
        {
            'title': 'Eldrerådet',
            'date': '2025-08-21',
            'time': '10:00',
            'location': 'Formannskapssalen',
            'kommune': 'Sauda kommune',
            'raw_text': 'Eldrerådet, 21.08.2025, kl. 10:00'
        },
        {
            'title': 'Klagenemnd for eiendomsskatt',
            'date': '2025-08-26',
            'time': '09:00',
            'location': 'Møterom - Heiahornet',
            'kommune': 'Strand kommune',
            'raw_text': 'Klagenemnd for eiendomsskatt, 26.08.2025, kl. 09:00'
        },
        {
            'title': 'Utvalg for areal, næring og kultur',
            'date': '2025-08-26',
            'time': '12:00',
            'location': 'Kommunestyresalen',
            'kommune': 'Sauda kommune',
            'raw_text': 'Utvalg for areal, næring og kultur, 26.08.2025, kl. 12:00'
        },
        {
            'title': 'Administrasjonsutvalget',
            'date': '2025-08-27',
            'time': '10:00',
            'location': 'Kommunestyresalen',
            'kommune': 'Sauda kommune',
            'raw_text': 'Administrasjonsutvalget, 27.08.2025, kl. 10:00'
        },
        {
            'title': 'Forvaltningsutvalget',
            'date': '2025-08-27',
            'time': '16:00',
            'location': 'Kommunestyresalen',
            'kommune': 'Strand kommune',
            'raw_text': 'Forvaltningsutvalget, 27.08.2025, kl. 16:00'
        },
        {
            'title': 'Formannskapet',
            'date': '2025-08-27',
            'time': '11:00',
            'location': 'Kommunestyresalen',
            'kommune': 'Sauda kommune',
            'raw_text': 'Formannskapet, 27.08.2025, kl. 11:00'
        },
        {
            'title': 'Kommunestyret - temamøte',
            'date': '2025-08-27',
            'time': '18:00',
            'location': 'Kommunestyresalen',
            'kommune': 'Strand kommune',
            'raw_text': 'Kommunestyret - temamøte, 27.08.2025, kl. 18:00'
        },
        {
            'title': 'Rådet for mennesker med nedsatt funksjonsevne',
            'date': '2025-09-17',
            'time': '13:00',
            'location': 'Kommunestyresalen',
            'kommune': 'Strand kommune',
            'raw_text': 'Rådet for mennesker med nedsatt funksjonsevne, 17.09.2025, kl. 13:00'
        },
        {
            'title': 'Kommunestyret',
            'date': '2025-09-15',
            'time': '09:00',
            'location': 'Kommunestyresalen',
            'kommune': 'Sauda kommune',
            'raw_text': 'Kommunestyret, 15.09.2025, kl. 09:00'
        },
        {
            'title': 'Kontrollutvalget',
            'date': '2025-09-18',
            'time': '15:00',
            'location': 'Møterom Heiahornet',
            'kommune': 'Strand kommune',
            'raw_text': 'Kontrollutvalget, 18.09.2025, kl. 15:00'
        },
        {
            'title': 'Levekårsutvalget',
            'date': '2025-09-24',
            'time': '18:00',
            'location': 'Kommunestyresalen',
            'kommune': 'Strand kommune',
            'raw_text': 'Levekårsutvalget, 24.09.2025, kl. 18:00'
        },
        {
            'title': 'Styremøte Bymiljøpakken',
            'date': '2025-08-22',
            'time': '10:00',
            'location': 'Stavanger',
            'kommune': 'Bymiljøpakken',
            'raw_text': 'Styremøte Bymiljøpakken, 22.08.2025, kl. 10:00'
        },
        {
            'title': 'Fylkesting',
            'date': '2025-08-28',
            'time': '09:00',
            'location': 'Fylkestinget',
            'kommune': 'Rogaland fylkeskommune',
            'raw_text': 'Fylkesting, 28.08.2025, kl. 09:00'
        },
        {
            'title': 'Formannskapet',
            'date': '2025-09-05',
            'time': '14:00',
            'location': 'Fylkeshuset',
            'kommune': 'Rogaland fylkeskommune',
            'raw_text': 'Formannskapet, 05.09.2025, kl. 14:00'
        },
        {
            'title': 'Fylkesting',
            'date': '2025-08-22',
            'time': '10:00',
            'location': 'Fylkestinget',
            'kommune': 'Rogaland fylkeskommune',
            'raw_text': 'Fylkesting, 22.08.2025, kl. 10:00'
        },
        {
            'title': 'Utvalg for transport og infrastruktur',
            'date': '2025-08-23',
            'time': '13:00',
            'location': 'Møterom A',
            'kommune': 'Rogaland fylkeskommune',
            'raw_text': 'Utvalg for transport og infrastruktur, 23.08.2025, kl. 13:00'
        }
    ]
    
    # Legg til noen fremtidige møter basert på dagens dato
    future_meetings = []
    base_date = today + timedelta(days=1)
    
    for i in range(3):
        meeting_date = base_date + timedelta(days=i*7)  # Ukentlige møter
        future_meetings.append({
            'title': f'Formannskapet',
            'date': meeting_date.strftime('%Y-%m-%d'),
            'time': '14:00',
            'location': 'Kommunestyresalen',
            'kommune': 'Demo kommune',
            'raw_text': f'Automatisk generert møte for demo'
        })
    
    return mock_meetings + future_meetings

if __name__ == '__main__':
    meetings = get_mock_meetings()
    print(f"Mock meetings: {len(meetings)}")
    for meeting in meetings:
        print(f"  {meeting['date']} - {meeting['title']} ({meeting['kommune']})")
