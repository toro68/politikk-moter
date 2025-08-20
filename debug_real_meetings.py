#!/usr/bin/env python3
"""
Debug script for å se de faktiske møtene som blir funnet fra scraping
"""
import asyncio
from scraper import scrape_all_meetings

def print_real_meetings():
    """Vis alle møter som faktisk blir funnet fra scraping"""
    print("🔍 Finner alle møter fra scraping...")
    
    meetings = scrape_all_meetings()
    
    print(f"\n📊 Totalt funnet: {len(meetings)} møter")
    print("\n🏛️ Møter fra de forskjellige kildene:")
    
    # Grupper etter kommune
    by_kommune = {}
    for meeting in meetings:
        kommune = meeting.get('kommune', 'Ukjent')
        if kommune not in by_kommune:
            by_kommune[kommune] = []
        by_kommune[kommune].append(meeting)
    
    for kommune, kommune_meetings in by_kommune.items():
        print(f"\n📍 {kommune}: {len(kommune_meetings)} møter")
        
        # Vis første 5 møter fra hver kommune
        for i, meeting in enumerate(kommune_meetings[:5]):
            print(f"  {i+1}. {meeting.get('date', 'TBD')} {meeting.get('time', 'TBD')} - {meeting.get('title', 'Ingen tittel')}")
        
        if len(kommune_meetings) > 5:
            print(f"  ... og {len(kommune_meetings) - 5} til")

if __name__ == "__main__":
    print_real_meetings()
