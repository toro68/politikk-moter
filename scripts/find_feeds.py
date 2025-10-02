#!/usr/bin/env python3
"""
Søk etter alternative API-endepunkter og RSS-feeds.
"""

import requests
from bs4 import BeautifulSoup
import re

def find_alternative_endpoints():
    """Søk etter RSS/API-endepunkter fra kommune-hovedsider."""
    
    kommune_domains = [
        "https://www.sauda.kommune.no",
        "https://www.strand.kommune.no", 
        "https://www.suldal.kommune.no",
        "https://www.hjelmeland.kommune.no",
        "https://www.sokndal.kommune.no",
        "https://www.bjerkreim.kommune.no"
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    
    for domain in kommune_domains:
        print(f"\n🔍 Sjekker {domain}")
        
        # Test vanlige RSS/API-paths
        test_paths = [
            '/rss',
            '/api/meetings',
            '/api/moter',
            '/innsyn/rss',
            '/feed',
            '/politikk/rss',
            '/calendar.ics',
            '/moter.ics'
        ]
        
        for path in test_paths:
            try:
                url = domain + path
                response = session.get(url, timeout=5)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '').lower()
                    if 'xml' in content_type or 'rss' in content_type or 'ical' in content_type:
                        print(f"  ✅ Funnet: {url} ({content_type})")
                    elif len(response.content) > 100:  # Ikke bare en feilside
                        print(f"  🔍 Mulig: {url} ({len(response.content)} bytes)")
            except:
                pass
        
        # Sjekk hovedsiden for RSS-lenker
        try:
            response = session.get(domain, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Søk etter RSS-lenker
                rss_links = soup.find_all('link', {'type': re.compile(r'rss|xml', re.I)})
                rss_links += soup.find_all('a', href=re.compile(r'rss|feed|\.xml|\.ics', re.I))
                
                for link in rss_links:
                    href = link.get('href') or link.get('src', '')
                    if href:
                        if not href.startswith('http'):
                            href = domain + href
                        print(f"  📡 RSS/Feed funnet: {href}")
        except:
            pass

if __name__ == '__main__':
    find_alternative_endpoints()
