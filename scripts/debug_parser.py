#!/usr/bin/env python3
"""
Debug-skript for å teste en enkelt kommune-side.
"""

import requests
from bs4 import BeautifulSoup
import re

def debug_single_site(url: str, name: str):
    """Debug en enkelt side for å se strukturen."""
    print(f"\n🔍 Debugger {name}")
    print(f"URL: {url}")
    
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        print(f"Status: {response.status_code}")
        print(f"Content-Length: {len(response.content)}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Finn alle elementer med tekst som inneholder dato
        date_pattern = re.compile(r'\d{1,2}\.\d{1,2}\.\d{4}')
        elements_with_dates = soup.find_all(text=date_pattern)
        
        print(f"\nElementer med datoer funnet: {len(elements_with_dates)}")
        
        for i, text in enumerate(elements_with_dates[:5]):  # Vis bare første 5
            print(f"  {i+1}. {text.strip()[:100]}")
            parent = text.parent
            if parent:
                print(f"     Parent: {parent.name} - {parent.get('class', 'no-class')}")
        
        # Finn alle h-tags
        headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        print(f"\nHeaders funnet: {len(headers)}")
        
        for i, header in enumerate(headers[:10]):  # Vis bare første 10
            text = header.get_text(strip=True)
            if text and len(text) > 3:
                print(f"  {i+1}. {header.name}: {text[:80]}")
        
        # Sjekk etter JavaScript-innhold
        scripts = soup.find_all('script')
        print(f"\nScript-tags funnet: {len(scripts)}")
        
        # Sjekk om siden har loading-indikatorer
        loading_elements = soup.find_all(text=re.compile(r'[Ll]oading|[Ll]aster', re.I))
        if loading_elements:
            print(f"Loading-indikatorer funnet: {len(loading_elements)}")
            for element in loading_elements[:3]:
                print(f"  - {element.strip()}")
        
    except Exception as e:
        print(f"Feil: {e}")

if __name__ == '__main__':
    # Test en enkelt side først
    debug_single_site(
        "https://www.sauda.kommune.no/innsyn/politiske-moter/",
        "Sauda kommune"
    )
    
    print("\n" + "="*60)
    
    # Test Elements Cloud
    debug_single_site(
        "https://prod01.elementscloud.no/publikum/971045698/Dmb",
        "Elements Cloud"
    )
