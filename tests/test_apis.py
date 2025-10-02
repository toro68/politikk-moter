#!/usr/bin/env python3
"""
Test kommune API-endepunkter som ble funnet.
"""

import pytest
import requests
import json
from bs4 import BeautifulSoup


@pytest.mark.parametrize("url", [
    "https://www.sauda.kommune.no/api/meetings",
    "https://www.sauda.kommune.no/api/moter",
    "https://www.strand.kommune.no/api/meetings",
    "https://www.hjelmeland.kommune.no/api/meetings",
])
def test_api_endpoint(url: str):
    """Test et API-endepunkt for å se hva det returnerer."""
    print(f"\n🔍 Testing {url}")
    
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/html, */*'
        })
        
        response = session.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
        print(f"Content-Length: {len(response.content)}")
        
        content_type = response.headers.get('content-type', '').lower()
        
        if 'json' in content_type:
            try:
                data = response.json()
                print(f"JSON data type: {type(data)}")
                if isinstance(data, dict):
                    print(f"JSON keys: {list(data.keys())}")
                elif isinstance(data, list):
                    print(f"JSON array length: {len(data)}")
                    if len(data) > 0:
                        print(f"First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'Not a dict'}")
            except json.JSONDecodeError:
                print("Ikke gyldig JSON")
        else:
            # Sjekk om det er HTML med møtedata
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Søk etter møte-relaterte ord
            text = soup.get_text()
            meeting_words = ['møte', 'formannskap', 'kommunestyre', 'utvalg', 'råd']
            found_words = []
            for word in meeting_words:
                if word.lower() in text.lower():
                    found_words.append(word)
            
            if found_words:
                print(f"Møte-relaterte ord funnet: {found_words}")
                
                # Se etter datoer
                import re
                dates = re.findall(r'\d{1,2}\.\d{1,2}\.202[45]', text)
                if dates:
                    print(f"Datoer funnet: {dates[:5]}")  # Vis bare første 5
            else:
                print("Ingen møte-relaterte ord funnet")
        
        # Vis de første 500 tegnene av response
        print(f"Preview (500 tegn):")
        print(response.text[:500])
        
    except Exception as e:
        print(f"Feil: {e}")

def main():
    """Test alle funnet API-endepunkter."""
    endpoints = [
        "https://www.sauda.kommune.no/api/meetings",
        "https://www.sauda.kommune.no/api/moter",
        "https://www.strand.kommune.no/api/meetings",
        "https://www.hjelmeland.kommune.no/api/meetings",
    ]
    
    for endpoint in endpoints:
        test_api_endpoint(endpoint)
        print("\n" + "="*60)


if __name__ == '__main__':
    main()
