#!/usr/bin/env python3
"""
Liste unike "Utvalg" (committee names) fra Eigersund møteplan-tabellen.
Viser også hvor mange ganger hvert utvalg har dager oppført og hvilke måneder (kort) de har møter i.
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from collections import defaultdict, Counter
import sys

URL = "https://innsyn.onacos.no/eigersund/mote/wfinnsyn.ashx?response=moteplan&"
MONTHS = ['Jan','Feb','Mar','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Des']


def fetch_table(url=URL):
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, 'html.parser')
    table = None
    for t in soup.find_all('table'):
        caption = t.find('caption')
        if caption and 'Møteplan' in caption.get_text():
            table = t
            break
    if not table:
        table = soup.find('table')
    return table


def parse_utvalg(table):
    utvalg_info = defaultdict(lambda: {'count':0, 'months':set(), 'link':''})
    for tr in table.find_all('tr'):
        cols = tr.find_all(['td','th'])
        if not cols:
            continue
        raw_name = cols[0].get_text(separator=' ', strip=True)
        if not raw_name:
            continue
        name = raw_name.strip()
        # Filter out header/navigation rows
        low = name.lower()
        if low.startswith('utvalg') or 'vis forrige' in low or 'vis neste' in low:
            continue
        # collect link if present
        a = cols[0].find('a')
        link = urljoin(URL, a.get('href')) if a and a.get('href') else ''
        # months cells
        month_cells = cols[1:13]
        month_count = 0
        for idx, cell in enumerate(month_cells, start=1):
            # look for day links or numbers
            days = [a.get_text(strip=True) for a in cell.find_all('a')]
            if not days:
                txt = cell.get_text(separator=' ', strip=True)
                if txt:
                    parts = [p.strip() for p in txt.split(',') if p.strip()]
                    days = parts
            if days:
                month_code = MONTHS[idx-1]
                utvalg_info[name]['months'].add(month_code)
                month_count += len(days)
                utvalg_info[name]['count'] += len(days)
        if link and not utvalg_info[name]['link']:
            utvalg_info[name]['link'] = link
    return utvalg_info


def print_utvalg(utvalg_info):
    items = sorted(utvalg_info.items(), key=lambda x: (-x[1]['count'], x[0]))
    print(f"Funnet {len(items)} unike utvalg:\n")
    for name, info in items:
        months = ','.join(sorted(info['months'], key=lambda m: MONTHS.index(m))) if info['months'] else '-'
        link = info['link'] or '-'
        print(f"- {name}\n    Antall dager oppført: {info['count']}; Måneder: {months}; Link: {link}")


if __name__ == '__main__':
    try:
        table = fetch_table()
        utvalg = parse_utvalg(table)
        print_utvalg(utvalg)
    except Exception as e:
        print('Feil:', e)
        sys.exit(1)
