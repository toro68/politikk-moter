#!/usr/bin/env python3
"""
Detaljert debug av Elements Cloud-siden.
"""

import requests
from bs4 import BeautifulSoup

def inspect_elements_cloud():
    """Detaljert inspeksjon av Elements Cloud-siden."""
    url = "https://prod01.elementscloud.no/publikum/971045698/Dmb"
    
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        print(f"Status: {response.status_code}")
        print(f"Content-Length: {len(response.content)}")
        print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
        
        print("\n=== RAW HTML ===")
        print(response.text)
        print("=== END RAW HTML ===\n")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Finn alle script-tags og deres innhold
        scripts = soup.find_all('script')
        print(f"Script-tags: {len(scripts)}")
        
        for i, script in enumerate(scripts):
            print(f"\nScript {i+1}:")
            if script.string:
                print(f"  Innhold (første 200 tegn): {script.string[:200]}")
            if script.get('src'):
                print(f"  Src: {script.get('src')}")
        
        # Sjekk alle elementer
        all_elements = soup.find_all()
        print(f"\nTotalt elementer: {len(all_elements)}")
        
        for element in all_elements:
            if element.name and element.get_text(strip=True):
                text = element.get_text(strip=True)
                if len(text) > 5:
                    print(f"  {element.name}: {text[:100]}")
        
    except Exception as e:
        print(f"Feil: {e}")

if __name__ == '__main__':
    inspect_elements_cloud()
