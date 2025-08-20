#!/usr/bin/env python3
"""
Test parser med kjent møtedata fra fetch_webpage.
"""

from scraper import MoteParser
import re
from datetime import datetime

def test_with_known_data():
    """Test parseren med møtedata vi vet eksisterer."""
    
    # Møtedata fra Sauda kommune (hentet via fetch_webpage tidligere)
    sauda_sample = """
Ungdomsrådet, 20.08.2025, kl. 09:00
Tid: 09:00
Sted: Formannskapssalen
3 saker 21. august 2025

Eldrerådet, 21.08.2025, kl. 10:00
Tid: 10:00
Sted: Formannskapssalen
12 saker 26. august 2025

Utvalg for areal, næring og kultur, 26.08.2025, kl. 12:00
Tid: 12:00
Sted: Kommunestyresalen
2 saker 27. august 2025

Administrasjonsutvalget, 27.08.2025, kl. 10:00
Tid: 10:00
Sted: Kommunestyresalen
3 saker 27. august 2025

Formannskapet, 27.08.2025, kl. 11:00
Tid: 11:00
Sted: Kommunestyresalen
"""

    # Strand kommune data
    strand_sample = """
Klagenemnd for eiendomsskatt, 26.08.2025, kl. 09:00
Tid: 09:00
Sted: Møterom - Heiahornet
7 saker 26. august 2025

Forvaltningsutvalget, 27.08.2025, kl. 16:00
Tid: 16:00
Sted: Kommunestyresalen
164 saker 27. august 2025

Kommunestyret - temamøte, 27.08.2025, kl. 18:00
Tid: 18:00
Sted: Kommunestyresalen
"""

    parser = MoteParser()
    
    print("🧪 Testing parser med kjent møtedata...\n")
    
    # Test direkte tekstparsing
    test_samples = [
        ("Sauda kommune", sauda_sample),
        ("Strand kommune", strand_sample)
    ]
    
    all_meetings = []
    
    for kommune_name, sample_text in test_samples:
        print(f"Tester {kommune_name}:")
        
        # Del opp tekst i linjer og test hver linje
        lines = sample_text.strip().split('\n')
        meetings = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Sjekk om linjen har en dato
            if re.search(r'\d{1,2}\.\d{1,2}\.202[45]', line):
                print(f"  Tester linje: {line}")
                
                # Lag en mock HTML-element
                class MockElement:
                    def get_text(self, strip=True):
                        return line
                    def find(self, tags):
                        return None
                    @property 
                    def name(self):
                        return 'div'
                
                meeting = parser._extract_meeting_from_element(MockElement(), kommune_name)
                if meeting:
                    meetings.append(meeting)
                    print(f"    ✅ Møte funnet: {meeting['title']} - {meeting['date']} {meeting['time']}")
                else:
                    print(f"    ❌ Ingen møte ekstrahert")
        
        all_meetings.extend(meetings)
        print(f"  Total møter fra {kommune_name}: {len(meetings)}\n")
    
    print(f"🎯 Total møter funnet: {len(all_meetings)}")
    
    if all_meetings:
        print("\nAlle møter:")
        for meeting in all_meetings:
            print(f"  - {meeting['kommune']}: {meeting['title']} ({meeting['date']} {meeting['time'] or 'ukjent tid'})")

if __name__ == '__main__':
    test_with_known_data()
