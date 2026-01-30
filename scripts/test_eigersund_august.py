#!/usr/bin/env python3
"""
Lister alle møter fra Eigersund kommune i en gitt måned (default: august 2025).
Bruker Playwright hvis tilgjengelig, ellers faller den tilbake til HTML-parser.
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _bootstrap_package() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    src_dir = os.path.join(repo_root, 'src')
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)



async def run_playwright(cfg):
    try:
        from politikk_moter.playwright_scraper import scrape_with_playwright
    except Exception as e:
        logger.warning('⚠️  Playwright-scraper ikke tilgjengelig: %s', e)
        return None
    try:
        results = await scrape_with_playwright([cfg])
        return results
    except Exception as e:
        logger.error('❌ Playwright scraping feilet: %s', e)
        return None


def run_fallback_parse(cfg, parser_cls):
    parser = parser_cls()
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


def print_meetings(meetings, year, month):
    if not meetings:
        logger.warning('⚠️  Ingen møter funnet i valgt måned')
        return
    logger.info('✅ Fant %s møter i %s-%02d:', len(meetings), year, month)
    for m in meetings:
        logger.info(
            " - %s %s - %s (%s)",
            m.get('date'),
            m.get('time', 'hele dagen'),
            m.get('title'),
            m.get('kommune'),
        )
        if m.get('url'):
            logger.info("     URL: %s", m.get('url'))


def main():
    _bootstrap_package()
    from politikk_moter.scraper import KOMMUNE_URLS, MoteParser, PLAYWRIGHT_AVAILABLE

    # Finn Eigersund-konfig
    eigersund_cfg = None
    for c in KOMMUNE_URLS:
        if 'eigersund' in c.get('name', '').lower() or 'eigersund' in c.get('url', '').lower():
            eigersund_cfg = c
            break

    if not eigersund_cfg:
        logger.error('❌ Fant ikke Eigersund-konfigurasjon i KOMMUNE_URLS')
        sys.exit(2)

    # Parametre
    year = 2025
    month = 8
    if '--year' in sys.argv:
        try:
            year = int(sys.argv[sys.argv.index('--year') + 1])
        except Exception:
            pass
    if '--month' in sys.argv:
        try:
            month = int(sys.argv[sys.argv.index('--month') + 1])
        except Exception:
            pass

    logger.info("🔎 Henter møter for Eigersund (%s-%02d)", year, month)
    logger.info("%s", json.dumps(eigersund_cfg, indent=2, ensure_ascii=False))

    meetings = None
    if PLAYWRIGHT_AVAILABLE:
        logger.info('🎭 Prøver Playwright-ruten')
        try:
            meetings = asyncio.run(run_playwright(eigersund_cfg))
        except Exception as e:
            logger.warning('⚠️  Feil ved kjøring av Playwright: %s', e)
            meetings = None

    if not meetings:
        logger.info('🔁 Fallback: bruker HTML-parser')
        meetings = run_fallback_parse(eigersund_cfg, MoteParser)

    filtered = filter_month(meetings or [], year, month)
    print_meetings(filtered, year, month)


if __name__ == '__main__':
    main()
