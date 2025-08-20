#!/usr/bin/env python3
"""
Vis detaljer om reelle møter fra scraping
"""
from scraper import scrape_all_meetings

def show_real_meeting_details():
    """Vis detaljert informasjon om reelle møter"""
    meetings = scrape_all_meetings()
    
    print("🔍 REELLE MØTER FUNNET:")
    print("=" * 50)
    
    # Grupper etter kommune
    by_kommune = {}
    for meeting in meetings:
        kommune = meeting.get('kommune', 'Ukjent')
        if kommune not in by_kommune:
            by_kommune[kommune] = []
        by_kommune[kommune].append(meeting)
    
    for kommune, kommune_meetings in by_kommune.items():
        print(f"\n📍 {kommune}: {len(kommune_meetings)} møter")
        print("-" * 40)
        
        # Vis første 10 møter med full detalj
        for i, meeting in enumerate(kommune_meetings[:10]):
            print(f"{i+1}. Dato: {meeting.get('date', 'TBD')}")
            print(f"   Tid: {meeting.get('time', 'TBD')}")
            print(f"   Tittel: {meeting.get('title', 'Ingen tittel')}")
            print(f"   Sted: {meeting.get('location', 'Ikke oppgitt')}")
            print()
        
        if len(kommune_meetings) > 10:
            print(f"   ... og {len(kommune_meetings) - 10} møter til")
        print()

if __name__ == "__main__":
    show_real_meeting_details()
