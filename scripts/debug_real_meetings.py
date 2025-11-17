#!/usr/bin/env python3
"""Debug-verktøy for å vise møtene som faktisk blir funnet fra scraping."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from politikk_moter.models import ensure_meeting  # pylint: disable=import-error
from politikk_moter.scraper import scrape_all_meetings  # pylint: disable=import-error

def print_real_meetings():
    """Vis alle møter som faktisk blir funnet fra scraping"""
    print("🔍 Finner alle møter fra scraping...")
    
    meetings = [ensure_meeting(m) for m in scrape_all_meetings()]
    
    print(f"\n📊 Totalt funnet: {len(meetings)} møter")
    print("\n🏛️ Møter fra de forskjellige kildene:")
    
    # Grupper etter kommune
    by_kommune = {}
    for meeting in meetings:
        kommune = meeting.kommune or 'Ukjent'
        by_kommune.setdefault(kommune, []).append(meeting)
    
    for kommune, kommune_meetings in by_kommune.items():
        print(f"\n📍 {kommune}: {len(kommune_meetings)} møter")
        
        # Vis første 5 møter fra hver kommune
        for i, meeting in enumerate(kommune_meetings[:5]):
            print(f"  {i+1}. {meeting.date or 'TBD'} {meeting.time or 'TBD'} - {meeting.title or 'Ingen tittel'}")
        
        if len(kommune_meetings) > 5:
            print(f"  ... og {len(kommune_meetings) - 5} til")

if __name__ == "__main__":
    print_real_meetings()
