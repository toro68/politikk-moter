#!/usr/bin/env python3
"""
Se på raw HTML fra Strand kommune for å forstå strukturen.
"""

import requests
from bs4 import BeautifulSoup
import re

def inspect_strand_html():
    """Inspiser raw HTML fra Strand kommune."""
    url = "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/politiske-moter-og-sakspapirer/politisk-motekalender/"
    
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        response = session.get(url, timeout=15)
        response.raise_for_status()
        
        # Les de første 2000 tegnene av HTML for å se strukturen
        html_preview = response.text[:2000]
        print("=== HTML PREVIEW (første 2000 tegn) ===")
        print(html_preview)
        print("=== END PREVIEW ===\n")
        
        # Søk etter forms som kan indikere AJAX-loading
        soup = BeautifulSoup(response.content, 'html.parser')
        
        forms = soup.find_all('form')
        print(f"Forms funnet: {len(forms)}")
        for form in forms:
            print(f"  Action: {form.get('action', 'N/A')}")
            print(f"  Method: {form.get('method', 'N/A')}")
        
        # Søk etter script-tags som kan indikere AJAX
        scripts = soup.find_all('script')
        ajax_scripts = []
        for script in scripts:
            if script.string and ('ajax' in script.string.lower() or 'fetch' in script.string.lower() or 'xhr' in script.string.lower()):
                ajax_scripts.append(script)
        
        print(f"\nPotensielle AJAX-scripts: {len(ajax_scripts)}")
        
        # Sjekk etter møte-relaterte CSS-klasser eller IDs
        meeting_elements = soup.find_all(attrs={'class': re.compile(r'.*m[øo]te.*|.*meeting.*', re.I)})
        meeting_elements += soup.find_all(attrs={'id': re.compile(r'.*m[øo]te.*|.*meeting.*', re.I)})
        
        print(f"Møte-relaterte elementer: {len(meeting_elements)}")
        for element in meeting_elements[:5]:
            print(f"  {element.name}: class={element.get('class')}, id={element.get('id')}")
            
    except Exception as e:
        print(f"Feil: {e}")

if __name__ == '__main__':
    inspect_strand_html()
