#!/usr/bin/env python3
"""
Test-skript for å hente alle møter fra Eigersund kommune.
- Prøver Playwright-rutinen hvis tilgjengelig.
- Ellers bruker MoteParser.parse_onacos_site som fallback.
"""
import asyncio
import sys
import json
import os

# Sørg for at repo-root er i sys.path slik at vi kan importere scraper.py
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from scraper import KOMMUNE_URLS, MoteParser, PLAYWRIGHT_AVAILABLE

# Finn Eigersund-konfig
eigersund_cfg = None
for c in KOMMUNE_URLS:
    if 'eigersund' in c.get('name', '').lower() or 'eigersund' in c.get('url', '').lower():
        eigersund_cfg = c
        break

if not eigersund_cfg:
    print('❌ Fant ikke Eigersund-konfigurasjon i KOMMUNE_URLS')
    sys.exit(2)

print('🔎 Tester scraping for Eigersund:')
print(json.dumps(eigersund_cfg, indent=2, ensure_ascii=False))

async def run_playwright(cfg):
    try:
        from playwright_scraper import scrape_with_playwright
    except Exception as e:
        print('⚠️  Playwright-scraper ikke tilgjengelig:', e)
        return None
    try:
        results = await scrape_with_playwright([cfg])
        return results
    except Exception as e:
        print('❌ Playwright scraping feilet:', e)
        return None


def run_fallback_parse(cfg):
    parser = MoteParser()
    typ = cfg.get('type')
    url = cfg.get('url')
    name = cfg.get('name')
    if typ == 'onacos':
        return parser.parse_onacos_site(url, name)
    elif typ == 'acos':
        return parser.parse_acos_site(url, name)
    elif typ == 'elements':
        return parser.parse_elements_site(url, name)
    else:
        return parser.parse_custom_site(url, name)


def print_meetings(meetings):
    if not meetings:
        print('⚠️  Ingen møter funnet')
        return
    print(f'✅ Fant {len(meetings)} møter:')
    for m in meetings:
        print(f" - {m.get('date')} {m.get('time','hele dagen')} - {m.get('title')} ({m.get('kommune')})")
        if m.get('url'):
            print(f"     URL: {m.get('url')}")


if __name__ == '__main__':
    # Forsøk Playwright hvis tilgjengelig
    meetings = None
    if PLAYWRIGHT_AVAILABLE:
        print('🎭 Playwright tilgjengelig — prøver Playwright-ruten')
        try:
            meetings = asyncio.run(run_playwright(eigersund_cfg))
        except Exception as e:
            print('⚠️  Feil ved kjøring av Playwright:', e)
            meetings = None

    if not meetings:
        print('🔁 Fallback: bruker HTML-parser')
        meetings = run_fallback_parse(eigersund_cfg)

    print_meetings(meetings)
