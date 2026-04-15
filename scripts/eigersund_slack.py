#!/usr/bin/env python3
"""
Hent Eigersund møteplan, konverter til "meeting"-objekter, og send Slack-melding.
Bruker samme format som `scraper.py`.
Kjør med --debug for å ikke sende (viser melding).
"""
import logging
import os
import sys
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _bootstrap_package() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    src_dir = os.path.join(repo_root, 'src')
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

URL = "https://innsyn.onacos.no/eigersund/mote/wfinnsyn.ashx?response=moteplan&"


def fetch_table(url=URL):
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    page_soup = BeautifulSoup(resp.content, 'html.parser')
    # Finn tabellen som inneholder 'Møteplan'
    target_table = None
    for candidate in page_soup.find_all('table'):
        caption = candidate.find('caption')
        if caption and 'Møteplan' in caption.get_text():
            target_table = candidate
            break
    if not target_table:
        target_table = page_soup.find('table')
    return target_table, page_soup


def parse_table_to_meetings(meeting_table, base_url=URL, year=None):
    current_month = None
    if year is None:
        now = datetime.now()
        year = now.year
        current_month = now.month
    parsed_meetings = []
    for tr in meeting_table.find_all('tr'):
        cols = tr.find_all(['td','th'])
        if not cols:
            continue
        committee = cols[0].get_text(strip=True)
        if not committee or committee.lower().startswith('utvalg') or 'vis forrige' in committee.lower():
            continue
        a = cols[0].find('a')
        link = urljoin(base_url, a.get('href')) if a and a.get('href') else base_url
        # months are next columns; some tables include exactly 12 months
        month_cells = cols[1:13]
        for idx, cell in enumerate(month_cells, start=1):
            month = idx  # 1..12
            # collect day numbers
            days = [a.get_text(strip=True) for a in cell.find_all('a')]
            if not days:
                txt = cell.get_text(separator=' ', strip=True)
                if txt:
                    # sometimes numbers separated by comma
                    parts = [p.strip() for p in txt.split(',') if p.strip()]
                    days = parts
            for d in days:
                # skip non-numeric
                try:
                    day = int(''.join([c for c in d if c.isdigit()]))
                except ValueError:
                    continue
                try:
                    target_year = year
                    if current_month is not None and month < current_month and current_month >= 11:
                        target_year += 1
                    dt = datetime(target_year, month, day)
                except ValueError:
                    continue
                parsed_meetings.append({
                    'title': committee,
                    'date': dt.strftime('%Y-%m-%d'),
                    'time': None,
                    'location': 'Ikke oppgitt',
                    'kommune': 'Eigersund kommune',
                    'url': link,
                    'raw_text': f'Eigersund: {committee} {day}.{month}.{target_year}'
                })
    return parsed_meetings


def send_to_slack(message: str, webhook_env: str = 'SLACK_WEBHOOK_URL', force_send: bool = False) -> bool:
    webhook_url = os.getenv(webhook_env)
    if send_to_slack.test_mode and not force_send:
        logger.info('DEBUG: Viser melding uten å sende')
        logger.info('%s', '=' * 40)
        logger.info('%s', message)
        logger.info('%s', '=' * 40)
        return True
    if not webhook_url:
        logger.error('Feil: %s ikke satt', webhook_env)
        return False
    payload = {'text': message}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info('✅ Sendt til Slack')
        return True
    except requests.RequestException as exc:
        logger.error('❌ Feil ved sending til Slack: %s', exc.__class__.__name__)
        return False


send_to_slack.test_mode = False


if __name__ == '__main__':
    _bootstrap_package()
    from politikk_moter.cli_utils import is_debug_mode, is_force_send, is_test_mode
    from politikk_moter.scraper import (
        filter_meetings_by_date_range,
        format_slack_message,
    )
    debug_mode = is_debug_mode()
    send_to_slack.test_mode = is_test_mode()
    try:
        table, soup = fetch_table()
        meetings = parse_table_to_meetings(table)
        # bruk filter fra scraper for neste 10 dager
        filtered = filter_meetings_by_date_range(meetings, days_ahead=9)
        slack_message = format_slack_message(filtered)
        sent = send_to_slack(slack_message, force_send=is_force_send())
        if not debug_mode and not sent:
            sys.exit(1)
    except requests.RequestException as exc:
        logger.error('Feil ved henting av tabell: %s', exc)
        sys.exit(2)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception('Feil i skriptet: %s', exc)
        sys.exit(2)
