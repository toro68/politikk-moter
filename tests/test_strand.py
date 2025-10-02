#!/usr/bin/env python3
"""
Test med en enkelt kommune-side som skal ha møter.
"""

import requests
from bs4 import BeautifulSoup
import re

def test_working_site():
    """Test en side som definitivt skal ha møter."""
    url = "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/politiske-moter-og-sakspapirer/politisk-motekalender/"
    
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        response = session.get(url, timeout=15)
        response.raise_for_status()
        
        print(f"Status: {response.status_code}")
        print(f"Content-Length: {len(response.content)}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Søk etter møteoverskrifter fra det jeg så i webscraping
        meeting_headers = soup.find_all('h4')
        print(f"\nH4-headers funnet: {len(meeting_headers)}")
        
        for i, header in enumerate(meeting_headers[:10]):
            text = header.get_text(strip=True)
            if text:
                print(f"  {i+1}. {text}")
                # Sjekk om det er dato i teksten
                if re.search(r'\d{1,2}\.\d{1,2}\.\d{4}', text):
                    print(f"     -> DATO FUNNET!")
        
        # Søk etter datoer generelt
        all_text = soup.get_text()
        dates = re.findall(r'\d{1,2}\.\d{1,2}\.202[45]', all_text)
        print(f"\nDatoer 2024/2025 funnet: {len(dates)}")
        for date in dates[:10]:
            print(f"  - {date}")
        
        # Søk etter "kl." som indikerer tidspunkt
        times = re.findall(r'kl\.?\s*\d{1,2}:\d{2}', all_text)
        print(f"\nTidspunkt funnet: {len(times)}")
        for time in times[:10]:
            print(f"  - {time}")
            
    except Exception as e:
        print(f"Feil: {e}")

if __name__ == '__main__':
    test_working_site()
