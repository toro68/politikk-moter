#!/usr/bin/env python3
"""
Eigersund-specific parser: hent møteplan-tabellen og konverter til møte-objekter.
Returnerer liste av møter i samme format som resten av scrapers.
"""
from datetime import datetime, timedelta
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import re

# Simple in-memory cache for fetched meeting detail pages during one run
_DETAILS_CACHE = {}

def parse_eigersund_meetings(url: str, kommune_name: str='Eigersund kommune', year: int=None, days_ahead: int = 10):
    if year is None:
        year = datetime.now().year
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.content, 'html.parser')
    # find table with caption or fallback to first table
    table = None
    for t in soup.find_all('table'):
        caption = t.find('caption')
        if caption and 'Møteplan' in caption.get_text():
            table = t
            break
    if not table:
        table = soup.find('table')
    if not table:
        return []
    meetings = []
    session = requests.Session()

    # Attempt to detect header row with month names to map column indices -> month numbers
    month_map = {}  # col_index -> month_number (1-12)
    month_names = {
        'jan':1, 'januar':1,
        'feb':2, 'februar':2,
        'mar':3, 'mars':3,
        'apr':4, 'april':4,
        'may':5, 'mai':5,
        'jun':6, 'juni':6,
        'jul':7, 'juli':7,
        'aug':8, 'august':8,
        'sep':9, 'sept':9, 'september':9,
        'oct':10, 'okt':10, 'oktober':10,
        'nov':11, 'november':11,
        'dec':12, 'des':12, 'desember':12
    }

    # Look for a header row (th) that contains month names
    header_found = False
    for tr in table.find_all('tr'):
        ths = tr.find_all('th')
        if not ths:
            continue
        for idx, th in enumerate(ths):
            txt = th.get_text(strip=True).lower()
            # check if any known month appears
            for k, mnum in month_names.items():
                if k in txt:
                    # Map actual table column index to month number
                    # Note: we will use absolute column index when reading rows
                    month_map[idx] = mnum
                    header_found = True
        if header_found:
            # stop at first header row that looks like months
            break

    # If header not found, fallback to assuming cols[1:13] map to months 1..12
    use_fallback_indexing = not month_map

    # Prepare rows
    for tr in table.find_all('tr'):
        cols = tr.find_all(['td','th'])
        if not cols:
            continue
        # Determine committee/title cell - usually first column
        committee_cell = cols[0]
        committee = committee_cell.get_text(strip=True)
        if not committee:
            continue
        low = committee.lower()
        if low.startswith('utvalg') or 'vis forrige' in low or 'vis neste' in low:
            continue
        a = committee_cell.find('a')
        link = urljoin(url, a.get('href')) if a and a.get('href') else url

        # For each identified month column, extract days
        if use_fallback_indexing:
            # fallback: assume next 12 columns correspond to Jan..Dec
            for offset in range(1, min(13, len(cols))):
                month = offset
                cell = cols[offset] if offset < len(cols) else None
                if not cell:
                    continue
                days = _extract_days_from_cell(cell)
                _append_meetings_from_days(days, month, year, committee, link, kommune_name, meetings, session)
        else:
            # use detected month_map which maps header th indices to month numbers
            # Need to translate header index to data column index: if header used <th> across table,
            # assume data rows align in number of columns; we'll match by position.
            for header_idx, month in month_map.items():
                # find the corresponding data cell index in this row
                if header_idx < len(cols):
                    cell = cols[header_idx]
                else:
                    # some tables have separate header columns; try offset by 1 (committee col)
                    alt_idx = header_idx
                    if alt_idx < len(cols):
                        cell = cols[alt_idx]
                    else:
                        continue
                days = _extract_days_from_cell(cell)
                _append_meetings_from_days(days, month, year, committee, link, kommune_name, meetings, session)

    # Filter to only return meetings from today up to days_ahead (inclusive)
    try:
        today = datetime.now().date()
        end_date = today + timedelta(days=days_ahead)
        filtered = []
        for m in meetings:
            try:
                mdate = datetime.strptime(m['date'], '%Y-%m-%d').date()
                if today <= mdate <= end_date:
                    filtered.append(m)
            except Exception:
                continue
        return filtered
    except Exception:
        return meetings


def _extract_days_from_cell(cell):
    """Return list of day strings extracted from a table cell.
    Handles anchors, comma/newline separated numbers, and bare digits like '29' or '29.'
    """
    days = [aa.get_text(strip=True) for aa in cell.find_all('a')]
    if days:
        return days
    txt = cell.get_text(separator='\n', strip=True)
    if txt:
        parts = [p.strip() for p in re.split('[,;\n/\\]+', txt) if p.strip()]
        if parts:
            return parts
    # final fallback: find bare numbers in the cell text
    txt2 = cell.get_text(' ', strip=True)
    found_nums = re.findall(r'\b([0-3]?\d)\b', txt2)
    return found_nums


def _append_meetings_from_days(days, month, year, committee, link, kommune_name, meetings, session):
    for d in days:
        digits = ''.join([c for c in d if c.isdigit()])
        if not digits:
            continue
        try:
            day = int(digits)
            dt = datetime(year, month, day)
        except Exception:
            continue
        time_str = None
        location = 'Ikke oppgitt'
        try:
            if link and link not in _DETAILS_CACHE:
                r = session.get(link, timeout=10)
                r.raise_for_status()
                _DETAILS_CACHE[link] = r.text
            detail_html = _DETAILS_CACHE.get(link)
            if detail_html:
                txt = BeautifulSoup(detail_html, 'html.parser').get_text(separator='\n', strip=True)
                m = re.search(r'kl\.?\s*([0-2]?\d[:\.][0-5]\d)', txt, re.IGNORECASE)
                if not m:
                    m = re.search(r'\b([0-2]?\d[:\.][0-5]\d)\b', txt)
                if m:
                    time_str = m.group(1).replace('.', ':')
                loc_match = re.search(r"(Sted[:\s\-]*|Sted\:|Sted\s|Sted -|Sted:)\s*([^\n,]+)", txt, re.IGNORECASE)
                if loc_match:
                    location = loc_match.group(2).strip()
                else:
                    for place in ['R\u00e5dhuset', 'R\u00e5dhus', 'Kinosalen', 'Kinosal', 'Kyrkja', 'Kommunestyresalen', 'R\u00e5dhussalen', 'Storsalen']:
                        if re.search(r"\b" + re.escape(place) + r"\b", txt, re.IGNORECASE):
                            location = place
                            break
        except Exception:
            time_str = None
        meetings.append({
            'title': committee,
            'date': dt.strftime('%Y-%m-%d'),
            'time': time_str,
            'location': location,
            'kommune': kommune_name,
            'url': link,
            'raw_text': f'Eigersund: {committee} {day}.{month}.{year}'
        })
