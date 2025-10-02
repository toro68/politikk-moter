#!/usr/bin/env python3
"""
Lister alle møter fra Eigersund kommune i en gitt måned (default: august 2025).
Bruker Playwright hvis tilgjengelig, ellers faller den tilbake til HTML-parser.
"""
import sys
import os
import json
from datetime import datetime

# Sørg for repo-root i path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from scraper import KOMMUNE_URLS, MoteParser, PLAYWRIGHT_AVAILABLE
import asyncio

# Finn Eigersund-konfig
eigersund_cfg = None
for c in KOMMUNE_URLS:
    if 'eigersund' in c.get('name', '').lower() or 'eigersund' in c.get('url', '').lower():
        eigersund_cfg = c
        break

if not eigersund_cfg:
    print('❌ Fant ikke Eigersund-konfigurasjon i KOMMUNE_URLS')
    sys.exit(2)

# Parametre
YEAR = 2025
MONTH = 8
if '--year' in sys.argv:
    try:
        YEAR = int(sys.argv[sys.argv.index('--year')+1])
    except Exception:
        pass
if '--month' in sys.argv:
    try:
        MONTH = int(sys.argv[sys.argv.index('--month')+1])
    except Exception:
        pass

print(f"🔎 Henter møter for Eigersund ({YEAR}-{MONTH:02d})")
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


def filter_month(meetings, year, month):
    out = []
    for m in meetings:
        try:
            dt = datetime.strptime(m['date'], '%Y-%m-%d')
            if dt.year == year and dt.month == month:
                out.append(m)
        except Exception:
            continue
    # sort
    out.sort(key=lambda x: (x['date'], x.get('time') or ''))
    return out


def print_meetings(meetings):
    if not meetings:
        print('⚠️  Ingen møter funnet i valgt måned')
        return
    print(f'✅ Fant {len(meetings)} møter i {YEAR}-{MONTH:02d}:')
    for m in meetings:
        print(f" - {m.get('date')} {m.get('time','hele dagen')} - {m.get('title')} ({m.get('kommune')})")
        if m.get('url'):
            print(f"     URL: {m.get('url')}")


if __name__ == '__main__':
    meetings = None
    if PLAYWRIGHT_AVAILABLE:
        print('🎭 Prøver Playwright-ruten')
        try:
            meetings = asyncio.run(run_playwright(eigersund_cfg))
        except Exception as e:
            print('⚠️  Feil ved kjøring av Playwright:', e)
            meetings = None

    if not meetings:
        print('🔁 Fallback: bruker HTML-parser')
        meetings = run_fallback_parse(eigersund_cfg)

    filtered = filter_month(meetings or [], YEAR, MONTH)
    print_meetings(filtered)
