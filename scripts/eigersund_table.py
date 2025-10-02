#!/usr/bin/env python3
"""\nHent og vis møteplan-tabellen fra Eigersund (Onacos) med kolonner for måneder.
Output: CSV til stdout og enkel tabellvisning.
"""
import requests
from bs4 import BeautifulSoup
import csv
import sys
from urllib.parse import urljoin

URL = "https://innsyn.onacos.no/eigersund/mote/wfinnsyn.ashx?response=moteplan&"
MONTHS = ['Jan','Feb','Mar','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Des']


def fetch_table(url=URL):
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, 'html.parser')
    # Finn tabellen som sannsynligvis inneholder 'Møteplan' i en caption eller heading
    # Fall tilbake til første table
    table = None
    for t in soup.find_all('table'):
        caption = t.find('caption')
        if caption and 'Møteplan' in caption.get_text():
            table = t
            break
    if not table:
        # fallback: første table
        table = soup.find('table')
    return table, soup


def parse_table(table, base_url=URL):
    rows = []
    headers = []
    # Hent header-rad hvis tilstede
    thead = table.find('thead')
    if thead:
        header_cells = thead.find_all('th')
        headers = [th.get_text(strip=True) for th in header_cells]
    else:
        # prøv første tr
        first_tr = table.find('tr')
        if first_tr:
            headers = [th.get_text(strip=True) for th in first_tr.find_all(['th','td'])]
    # Nå parse rader
    for tr in table.find_all('tr'):
        cols = tr.find_all(['td','th'])
        if not cols:
            continue
        # første kolonne er utvalg/committee
        first = cols[0]
        committee = first.get_text(strip=True)
        # link i første kolonne
        a = first.find('a')
        link = urljoin(base_url, a.get('href')) if a and a.get('href') else ''
        month_cells = []
        # remaining cells correspond to months - sometimes there may be an extra leading column
        for c in cols[1:13]:
            # finn alle linker (dager) i cellen
            days = [a.get_text(strip=True) for a in c.find_all('a')]
            # også inkluderer ren tekst hvis ingen lenker
            if not days:
                txt = c.get_text(separator=' ', strip=True)
                days = [txt] if txt else []
            month_cells.append(', '.join(days))
        # hvis fewer cells, pad
        while len(month_cells) < 12:
            month_cells.append('')
        rows.append({'committee': committee, 'link': link, 'months': month_cells})
    return rows


def print_csv(rows):
    writer = csv.writer(sys.stdout)
    writer.writerow(['Committee','Link'] + MONTHS)
    for r in rows:
        writer.writerow([r['committee'], r['link']] + r['months'])


def print_table(rows):
    # Print a compact text table
    col_widths = [30] + [6]*12
    # header
    hdr = ['Committee'] + MONTHS
    fmt = ''.join([f"{{:<{w}}}" for w in col_widths])
    print(fmt.format(*hdr))
    print('-'*sum(col_widths))
    for r in rows:
        row = [r['committee'][:30]] + [ (m[:5] if m else '') for m in r['months'] ]
        print(fmt.format(*row))


if __name__ == '__main__':
    try:
        table, soup = fetch_table()
        rows = parse_table(table)
        print('\nCSV output:\n')
        print_csv(rows)
        print('\nCompact table view:\n')
        print_table(rows)
    except Exception as e:
        print('Feil ved henting/parsing:', e)
        sys.exit(1)
