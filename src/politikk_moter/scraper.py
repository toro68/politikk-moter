#!/usr/bin/env python3
"""Scraper for politiske møter og Slack-notifikasjoner."""
# pylint: disable=broad-except

import asyncio
import html
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .kommuner import get_default_kommune_configs, get_kommune_configs
from .pipeline_config import PipelineConfig, get_pipeline_configs
from .models import Meeting, ensure_meeting
# Import Playwright scraper for JavaScript-heavy sites
from .reporting import format_slack_message

CALENDAR_EXPECTED_LABELS = {
    "turnus": {"name": "(Turnus-kalender)", "label": "turnus"},
    "arrangementer_sa": {"name": "(Arrangementer-SA-kalender)", "label": "ovrige"},
    "regional_kultur": {"name": "(Regional kulturkalender)", "label": "ovrige"},
}

# Import Playwright scraper for JavaScript-heavy sites
try:
    from .playwright_scraper import scrape_with_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright ikke tilgjengelig. Bruker kun requests/BeautifulSoup.")

# Import Google Calendar integration
try:
    from .calendar_integration import get_calendar_meetings, get_calendar_meetings_for_sources
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False
    get_calendar_meetings = None  # type: ignore[assignment]
    get_calendar_meetings_for_sources = None  # type: ignore[assignment]
    print("⚠️  Google Calendar-integrasjon ikke tilgjengelig.")

# Konfigurasjon av kilde-URLer (beholder globalt navn for bakoverkompatibilitet i tester)
KOMMUNE_URLS = get_default_kommune_configs()

# Import Eigersund parser
try:
    from .eigersund_parser import parse_eigersund_meetings
    EIGERSUND_AVAILABLE = True
except Exception:
    EIGERSUND_AVAILABLE = False

TURNUS_KOMMUNER = {
    "Stavanger kommune",
    "Sola kommune",
    "Randaberg kommune",
    "Klepp kommune",
    "Time kommune",
    "Hå kommune",
    "Sandnes kommune",
    "Gjesdal kommune",
    "Kvitsøy kommune",
}
TURNUS_CALENDAR_SOURCE = "calendar:turnus"

BATCH_LABELS = {
    "turnus": "Nord-Jæren og Jæren",
    "ovrige": "Ryfylke, Dalane",
    "alle": "Politiske møter",
}

WEBHOOK_FALLBACK_ENVIRONMENTS = [
    "SLACK_WEBHOOK_URL",
]

SLACK_WEBHOOK_FALLBACK_FLAG_ENV = "SLACK_WEBHOOK_FALLBACK"


def _is_truthy_env(env_name: str) -> bool:
    """Return True when env var exists with a truthy value."""
    value = os.getenv(env_name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _expected_kommuner_by_batch(pipeline: PipelineConfig) -> Dict[str, List[str]]:
    """Return expected kommune names per Slack batch for summaries."""
    kommune_configs = get_kommune_configs(pipeline.kommune_groups)
    pipeline_names = {config["name"] for config in kommune_configs}

    turnus_expected = sorted(name for name in pipeline_names if name in TURNUS_KOMMUNER)
    other_expected = sorted(name for name in pipeline_names if name not in TURNUS_KOMMUNER)

    mapping: Dict[str, List[str]] = {}
    if turnus_expected:
        mapping["turnus"] = turnus_expected
    if other_expected:
        mapping["ovrige"] = other_expected

    if pipeline_names:
        mapping["alle"] = sorted(pipeline_names)

    def _add_expected(label: str, name: str) -> None:
        bucket = mapping.setdefault(label, [])
        if name not in bucket:
            bucket.append(name)

    for source_id in pipeline.calendar_sources:
        meta = CALENDAR_EXPECTED_LABELS.get(source_id)
        if not meta:
            continue
        display_name = meta["name"]
        target_label = meta.get("label") or "ovrige"
        _add_expected(target_label, display_name)
        _add_expected("alle", display_name)

    for label in mapping:
        mapping[label] = sorted(mapping[label])

    return mapping


def _format_heading_suffix(label: str, meetings: Sequence[Meeting]) -> str:
    """Return a human readable suffix for the Slack heading."""
    base_label = BATCH_LABELS.get(label, label.replace("_", " ").title())
    count = len(meetings)
    if count == 0:
        return f"{base_label} – ingen møter"
    noun = "møte" if count == 1 else "møter"
    return f"{base_label} ({count} {noun})"


def _resolve_slack_webhook(env_name: str) -> Tuple[Optional[str], str, bool]:
    """Return webhook URL, the env used, and whether fallback was applied."""
    candidates = [env_name]
    candidates.extend(
        fallback for fallback in WEBHOOK_FALLBACK_ENVIRONMENTS if fallback not in candidates
    )

    allow_fallback = _is_truthy_env(SLACK_WEBHOOK_FALLBACK_FLAG_ENV)

    for candidate in candidates:
        if candidate != env_name and not allow_fallback:
            continue
        value = os.getenv(candidate, "").strip()
        if value:
            return value, candidate, candidate != env_name

    return None, env_name, False

class MoteParser:
    """Parser for møtedata fra kommunale nettsider."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def parse_date_from_text(self, text: str) -> Optional[datetime]:
        """Prøver flere dato-formater i tekst (dd.mm.yyyy, dd.mm.yy, dd month yyyy)."""
        if not text:
            return None

        # 1) dd.mm.yyyy eller dd/mm/yyyy eller dd-mm-yyyy eller dd.mm.yy
        m = re.search(r"(\d{1,2})[\.\-/](\d{1,2})[\.\-/](\d{2,4})", text)
        if m:
            day, month, year = m.groups()
            y = int(year)
            if y < 100:  # to-sifret år
                y += 2000
            try:
                return datetime(y, int(month), int(day))
            except ValueError:
                pass

        # 2) Dag månednavn år (eks. 20. august 2025 eller 20 august 2025)
        months = {
            'jan':1,'januar':1,'feb':2,'februar':2,'mar':3,'mars':3,'apr':4,'april':4,
            'mai':5,'jun':6,'juni':6,'jul':7,'juli':7,'aug':8,'august':8,'sep':9,'sept':9,'september':9,
            'okt':10,'oktober':10,'nov':11,'november':11,'des':12,'desember':12
        }
    # finn pattern: (dag måned år)
        m2 = re.search(r"(\d{1,2})\.?\s+([A-Za-zæøåÆØÅ\.]{3,})\s+(\d{4})", text)
        if m2:
            day = int(m2.group(1))
            mon_str = m2.group(2).lower().rstrip('.')
            year = int(m2.group(3))
            mon = months.get(mon_str[:3]) or months.get(mon_str)
            if mon:
                try:
                    return datetime(year, mon, day)
                except ValueError:
                    pass

        return None

    def parse_time_from_text(self, text: str) -> Optional[str]:
        """Prøver flere tid-formater (kl. hh:mm, hh:mm, hh.mm). Returnerer 'HH:MM' eller None."""
        if not text:
            return None
        # Foretrekk tider med kolon eller 'kl' prefiks; unngå å tolke dd.mm som tid
        m = re.search(r'(?:kl\.?\s*)?(\d{1,2}):(\d{2})', text)
        if m:
            h, mi = m.groups()
            try:
                hh = int(h)
                mm = int(mi)
                if 0 <= hh < 24 and 0 <= mm < 60:
                    return f"{hh:02d}:{mm:02d}"
            except ValueError:
                pass
        m = re.search(r'(?:kl\.?\s*)(\d{1,2})(?:[\.:](\d{2}))?', text, re.IGNORECASE)
        if m:
            h, mi = m.groups()
            minute = mi or '00'
            try:
                hh = int(h)
                mm = int(minute)
                if 0 <= hh < 24 and 0 <= mm < 60:
                    return f"{hh:02d}:{mm:02d}"
            except ValueError:
                pass
        m = re.search(r'(?:klokka)\s*(\d{1,2})', text, re.IGNORECASE)
        if m:
            h = m.group(1)
            try:
                hh = int(h)
                if 0 <= hh < 24:
                    return f"{hh:02d}:00"
            except ValueError:
                pass
        return None
    
    def parse_acos_site(self, url: str, kommune_name: str) -> List[Dict]:
        """Parser for ACOS-baserte innsyn-sider."""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            meetings = []
            
            # Forbedret søk etter møte-elementer
            # 1. Søk etter h4-tags som ofte inneholder møtetitler
            h4_elements = soup.find_all('h4')
            
            # 2. Søk etter div-er med møte-relaterte klasser
            meeting_divs = soup.find_all('div', class_=re.compile(r'.*møte.*|.*meeting.*|.*resultat.*', re.I))
            
            # 3. Søk etter article-tags
            articles = soup.find_all('article')
            
            # 4. Søk etter elementer som inneholder datoformater
            date_sections = []
            
            # Finn alle paragrafer eller div-er som inneholder datoer
            for element in soup.find_all(['p', 'div', 'li', 'td']):
                text = element.get_text(strip=True)
                if re.search(r'\d{1,2}\.\d{1,2}\.202[4-6]', text):
                    date_sections.append(element)
            
            all_elements = h4_elements + meeting_divs + articles + date_sections
            
            for element in all_elements:
                meeting = self._extract_meeting_from_element(element, kommune_name)
                if meeting:
                    meetings.append(meeting)
            
            # Fjern duplikater basert på dato + tittel
            unique_meetings = []
            seen = set()
            for meeting in meetings:
                key = (meeting['date'], meeting['title'].lower())
                if key not in seen:
                    seen.add(key)
                    unique_meetings.append(meeting)
            
            return unique_meetings
            
        except Exception as e:
            print(f"Feil ved parsing av {kommune_name}: {e}")
            return []
    
    def parse_onacos_site(self, url: str, kommune_name: str) -> List[Dict]:
        """Parser for Onacos-baserte sider."""
        try:
            # Special-case: delegate to the dedicated Eigersund parser if this is Eigersund.
            # This ensures fallback HTML parsing for Eigersund applies the strict
            # "today..today+10 days" filter (the dedicated parser already does this).
            try:
                if EIGERSUND_AVAILABLE and (('eigersund' in (kommune_name or '').lower()) or ('eigersund' in (url or '').lower())):
                    return parse_eigersund_meetings(url, kommune_name, days_ahead=10)
            except Exception:
                # non-fatal: fall through to generic parsing
                pass
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            meetings = []
            # Onacos pages often use a calendar table: months as header cells across
            # and committee rows with day-links in the month columns. Detect that
            # pattern first and extract structured meetings.
            months_map = {
                'jan':1,'januar':1,'feb':2,'februar':2,'mar':3,'mars':3,'apr':4,'april':4,
                'mai':5,'jun':6,'juni':6,'jul':7,'juli':7,'aug':8,'august':8,'sep':9,'sept':9,'september':9,
                'okt':10,'oktober':10,'nov':11,'november':11,'des':12,'desember':12
            }

            calendar_table = None
            for table in soup.find_all('table'):
                headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
                if any(h[:3] in months_map for h in headers if h):
                    calendar_table = table
                    break

            today = datetime.now()
            current_year = today.year

            if calendar_table:
                # Map header index -> month number
                header_cells = calendar_table.find_all('th')
                month_indices = {}
                for idx, th in enumerate(header_cells):
                    txt = th.get_text(strip=True).lower()
                    key = txt.rstrip('.')[:3]
                    if key in months_map:
                        month_indices[idx] = months_map[key]

                # Iterate rows: first cell is committee name, following cells correspond to months
                for row in calendar_table.find_all('tr'):
                    cols = row.find_all(['td', 'th'])
                    if not cols:
                        continue
                    # The left-most column is usually the committee name
                    committee = cols[0].get_text(strip=True)
                    if not committee:
                        continue

                    for col_idx, cell in enumerate(cols[1:], start=1):
                        month_num = month_indices.get(col_idx)
                        if not month_num:
                            continue
                        # Find all day links in this cell
                        for a in cell.find_all('a'):
                            day_text = a.get_text(strip=True)
                            if not re.match(r'^\d{1,2}$', day_text):
                                # Sometimes links contain multiple days separated by comma
                                parts = re.findall(r'\d{1,2}', day_text)
                            else:
                                parts = [day_text]
                            for part in parts:
                                day = int(part)
                                # Construct date; assume current year. If month earlier than current month and we're late in year, could be next year - keep simple for now.
                                try:
                                    dt = datetime(current_year, month_num, day)
                                except ValueError:
                                    # invalid date (e.g., 30 Feb) - skip
                                    continue
                                meeting = {
                                    'title': committee,
                                    'date': dt.strftime('%Y-%m-%d'),
                                    'time': None,
                                    'location': 'Ikke oppgitt',
                                    'kommune': kommune_name,
                                    'raw_text': a.get_text(strip=True)[:300],
                                    'url': urljoin(url, a.get('href') or '')
                                }
                                meetings.append(meeting)
                return meetings

            # Fallback: previous generic scraping
            meeting_elements = soup.find_all(['tr', 'div'], class_=re.compile(r'.*møte.*|.*row.*', re.I))
            for element in meeting_elements:
                meeting = self._extract_meeting_from_element(element, kommune_name)
                if meeting:
                    meetings.append(meeting)
            
            return meetings
            
        except Exception as e:
            print(f"Feil ved parsing av {kommune_name}: {e}")
            return []
    
    def parse_elements_site(self, url: str, kommune_name: str) -> List[Dict]:
        """Parser for Elements Cloud-baserte sider."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            meetings = []
            
            # Elements Cloud har ofte JavaScript-generert innhold
            # Vi leter etter møte-tabeller eller strukturert data
            meeting_rows = soup.find_all(['tr', 'div'], class_=re.compile(r'.*møte.*|.*meeting.*|.*row.*', re.I))
            
            # Alternativ: søk etter alle lenker med møte-relaterte ord
            meeting_links = soup.find_all('a', href=re.compile(r'.*møte.*|.*meeting.*', re.I))
            
            all_elements = meeting_rows + meeting_links
            
            for element in all_elements:
                meeting = self._extract_meeting_from_element(element, kommune_name)
                if meeting:
                    meetings.append(meeting)
            
            return meetings
            
        except Exception as e:
            print(f"Feil ved parsing av {kommune_name}: {e}")
            return []
    
    def parse_custom_site(self, url: str, kommune_name: str) -> List[Dict]:
        """Parser for custom sider som Bymiljøpakken."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            html_text = getattr(response, 'text', None)
            if html_text is None and response.content:
                html_text = response.content.decode('utf-8', errors='ignore')

            if 'klepp' in kommune_name.lower():
                return self._parse_klepp_meetings(soup, url, kommune_name)

            if html_text and 'opengov.360online.com' in url.lower():
                opengov_meetings = self._parse_opengov_360_meetings(html_text, url, kommune_name)
                if opengov_meetings:
                    return opengov_meetings

            if 'bymiljopakken.no' in url.lower():
                return self._parse_bymiljopakken(soup, url, kommune_name)

            meetings = []
            
            # Special-case: Hå kommune bruker en enkel side-layout som kan
            # listes ut med klare dato-/tidsblokker. Implementer en lettvekts-
            # ekstraktor som fanger opp de to første møtene på `ha.no`.
            if 'ha.no' in url.lower() or 'hå.no' in url.lower():
                # Se etter elementer som inneholder dato + møtetittel
                for block in soup.select('article, .event, .meeting, .post'):
                    text = block.get_text(' ', strip=True)
                    if not text:
                        continue
                    # Prøv å parse dato og tid
                    parsed_date = self.parse_date_from_text(text)
                    parsed_time = self.parse_time_from_text(text)
                    if not parsed_date:
                        continue
                    title = None
                    # Finn teksten som ser ut som tittel (linjer uten dato/tid)
                    for line in text.split('\n'):
                        line = line.strip()
                        if not line:
                            continue
                        if re.search(r'\d{1,2}[\.\-/]\d{1,2}[\.\-/]\d{2,4}', line):
                            continue
                        if re.search(r'kl\.?', line, re.I):
                            continue
                        title = line
                        break
                    if not title:
                        title = 'Politisk møte'
                    meetings.append({
                        'title': title,
                        'date': parsed_date.strftime('%Y-%m-%d'),
                        'time': parsed_time,
                        'location': 'Hå rådhus' if 'rådhus' in text.lower() else 'Ikke oppgitt',
                        'kommune': kommune_name,
                        'url': url,
                        'raw_text': text[:300],
                    })
                # Deduplicate and return if we found items
                if meetings:
                    unique = []
                    seen = set()
                    for m in meetings:
                        key = (m['date'], m['title'])
                        if key not in seen:
                            seen.add(key)
                            unique.append(m)
                    return unique

            # For Bymiljøpakken og lignende - søk bredt
            # Alle elementer som kan inneholde møteinfo
            all_elements = []
            all_elements.extend(soup.find_all(['div', 'article', 'section', 'li', 'tr']))
            all_elements.extend(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
            all_elements.extend(soup.find_all(['p', 'span']))
            
            for element in all_elements:
                meeting = self._extract_meeting_from_element(element, kommune_name)
                if meeting:
                    meetings.append(meeting)
            
            # Dedupliser basert på dato og tittel
            unique_meetings = []
            seen = set()
            for meeting in meetings:
                key = (meeting['date'], meeting['title'])
                if key not in seen:
                    seen.add(key)
                    unique_meetings.append(meeting)
            
            return unique_meetings
            
        except Exception as e:
            print(f"Feil ved parsing av {kommune_name}: {e}")
            return []

    def _parse_klepp_meetings(self, soup: BeautifulSoup, base_url: str, kommune_name: str) -> List[Dict]:
        """Klepp kommune bruker 360online med tydelig møte-liste."""
        meetings: List[Dict] = []

        for link in soup.select('a[href*="/Meetings/Details/"]'):
            meeting_name = link.select_one('.meetingName')
            date_spans = link.select('.meetingDate span')

            if not meeting_name or not date_spans:
                continue

            raw_title = meeting_name.get_text(' ', strip=True)
            title = re.sub(r"\s*\([^)]*\)\s*$", "", raw_title).strip()
            if not title:
                continue

            meeting_date = None
            meeting_time = None
            for candidate in date_spans:
                text = candidate.get_text(' ', strip=True)
                if not text:
                    continue
                if meeting_date is None:
                    parsed_date = self.parse_date_from_text(text)
                    if parsed_date:
                        meeting_date = parsed_date
                        continue
                if meeting_time is None:
                    parsed_time = self.parse_time_from_text(text)
                    if parsed_time:
                        meeting_time = parsed_time

            if not meeting_date:
                continue

            meeting_url = urljoin(base_url, link.get('href', ''))

            meetings.append({
                'title': title,
                'date': meeting_date.strftime('%Y-%m-%d'),
                'time': meeting_time,
                'location': 'Ikke oppgitt',
                'kommune': kommune_name,
                'url': meeting_url,
                'raw_text': link.get_text(' ', strip=True)[:300],
            })

        unique: List[Dict] = []
        seen = set()
        for meeting in meetings:
            key = (meeting['date'], meeting['title'])
            if key in seen:
                continue
            seen.add(key)
            unique.append(meeting)

        return unique

    def _parse_opengov_360_meetings(self, html_text: str, base_url: str, kommune_name: str) -> List[Dict]:
        """Bruk BeautifulSoup (med regex-fallback) for opengov.360online.com."""

        meetings: List[Dict] = []
        soup = BeautifulSoup(html_text or "", "html.parser")

        def _append_meeting(title: str, date_str: str, time_str: Optional[str], href: str, raw: str) -> None:
            parsed_date = self.parse_date_from_text(date_str) or self.parse_date_from_text(title)
            if not parsed_date:
                return
            normalized_time = self.parse_time_from_text(time_str or "")
            if not normalized_time:
                normalized_time = self.parse_time_from_text(title)

            clean_title = title.strip()
            clean_title = re.sub(r'\(.*?\)$', '', clean_title).strip()
            clean_title = re.sub(r'\s+\d{1,2}[\.\-]\d{1,2}[\.\-]\d{2,4}.*', '', clean_title).strip(' -:')
            clean_title = re.sub(r'\s*kl\.?\s*\d{1,2}[:\. ]\d{2}', '', clean_title, flags=re.IGNORECASE).strip()
            if not clean_title:
                clean_title = title or "Politisk møte"

            meetings.append(
                {
                    "title": clean_title[:100],
                    "date": parsed_date.strftime("%Y-%m-%d"),
                    "time": normalized_time,
                    "location": "Ikke oppgitt",
                    "kommune": kommune_name,
                    "url": urljoin(base_url, href),
                    "raw_text": raw[:300],
                }
            )

        board_links = soup.select("li[class*='board']")
        if board_links:
            for li in board_links:
                anchor = li.find("a")
                href = anchor.get("href") if anchor else None
                if not href:
                    continue
                name_el = li.select_one(".meetingName") or li.select_one("[class*='meetingName']")
                date_el = li.select_one(".meetingDate") or li.select_one("[class*='meetingDate']")
                if not date_el:
                    continue
                raw_title = name_el.get_text(" ", strip=True) if name_el else anchor.get_text(" ", strip=True)
                date_span = date_el.find_all("span") if date_el else []
                explicit_date = date_span[0].get_text(strip=True) if date_span else date_el.get_text(" ", strip=True)
                explicit_time = date_span[1].get_text(strip=True) if len(date_span) > 1 else None
                if not explicit_date:
                    continue
                _append_meeting(raw_title or "Politisk møte", explicit_date or "", explicit_time, href, li.get_text(" ", strip=True))

        if not meetings:
            pattern = re.compile(
                r'<li[^>]*class="[^"]*boardLink[^"]*"[^>]*>\s*'
                r'<a[^>]*href="(?P<href>[^"]+)"[^>]*>.*?'
                r'<div[^>]*class="meetingName"[^>]*>\s*<span>(?P<name>.*?)</span>.*?'
                r'<div[^>]*class="meetingDate"[^>]*>\s*<span>(?P<date>\d{1,2}[\.\-]\d{1,2}[\.\-]\d{4})</span>'
                r'(?:\s*<span>(?P<time>[0-9:\.]+)</span>)?',
                re.IGNORECASE | re.DOTALL,
            )

            for match in pattern.finditer(html_text or ""):
                href = html.unescape(match.group("href") or "").strip()
                raw_title = html.unescape(match.group("name") or "").strip()
                explicit_time = (match.group("time") or "").replace(".", ":")
                _append_meeting(raw_title, match.group("date") or "", explicit_time, href, raw_title)

        unique: List[Dict] = []
        seen = set()
        for meeting in meetings:
            key = (meeting["date"], meeting["title"])
            if key in seen:
                continue
            seen.add(key)
            unique.append(meeting)

        return unique

    def _parse_bymiljopakken(self, soup: BeautifulSoup, base_url: str, kommune_name: str) -> List[Dict]:
        meetings: List[Dict] = []
        today = datetime.now().date()

        def append_meeting(title: str, text_blob: str, href: Optional[str], location: Optional[str] = None) -> None:
            parsed_date = self.parse_date_from_text(text_blob) or self.parse_date_from_text(title)
            if not parsed_date:
                return
            meeting_date = parsed_date.date()
            if meeting_date < today:
                return
            time_value = self.parse_time_from_text(text_blob)
            meeting = {
                'title': (title or 'Politisk møte')[:100],
                'date': meeting_date.strftime('%Y-%m-%d'),
                'time': time_value,
                'location': (location or 'Ikke oppgitt')[:50],
                'kommune': kommune_name,
                'url': href or base_url,
                'raw_text': text_blob[:300],
            }
            meetings.append(meeting)

        next_block = soup.select_one('.content__info-meeting')
        if next_block:
            title_el = next_block.find('h3')
            title = title_el.get_text(' ', strip=True) if title_el else 'Neste møte'
            text_blob = next_block.get_text(' ', strip=True)
            location_match = re.search(r'(?:Sted|Stad):\s*([^\n]+)', text_blob, re.IGNORECASE)
            location = location_match.group(1).strip() if location_match else None
            append_meeting(title, text_blob, base_url, location)

        for link in soup.select('.planned-meetings a.planned-meetings__link'):
            text_blob = link.get_text(' ', strip=True)
            title = link.get('title') or text_blob
            href = urljoin(base_url, link.get('href') or '')
            append_meeting(title, text_blob, href)

        unique: List[Dict] = []
        seen = set()
        for meeting in meetings:
            key = (meeting['date'], meeting['title'])
            if key in seen:
                continue
            seen.add(key)
            unique.append(meeting)

        return unique
    
    def _extract_meeting_from_element(self, element, kommune_name: str) -> Optional[Dict]:
        """Ekstraherer møteinfo fra HTML-element."""
        try:
            text = element.get_text(strip=True)
            if text:
                # Hopp over elementer som kun inneholder dato/tid (f.eks. separate kolonner i Sandnes-visningen)
                alnum_text = re.sub(r"\s+", "", text)
                if not re.search(r"[A-Za-zÆØÅæøå]", text):
                    # Støtte for format som 02.10.2025 16:00 eller 02.10.202516:00
                    if re.search(r"\d{1,2}[\.\-/]\d{1,2}[\.\-/]\d{2,4}", text) and re.search(r"\d{1,2}[:\.]\d{2}", text):
                        return None
                    if re.fullmatch(r"\d{6,}", alnum_text):
                        return None

            # Bygg liste av kandidat-tekster: synlig tekst + aria-label/title fra element og barn
            candidate_texts = [text]
            try:
                aria = element.get('aria-label')
                title_attr = element.get('title')
            except Exception:
                aria = None
                title_attr = None
            if aria:
                candidate_texts.insert(0, aria)
            if title_attr:
                candidate_texts.insert(0, title_attr)
            # child attributes
            for child in element.find_all(True):
                try:
                    a = child.get('aria-label')
                    t = child.get('title')
                except Exception:
                    a = None; t = None
                if a:
                    candidate_texts.append(a)
                if t:
                    candidate_texts.append(t)

            # Ignorer for korte synlige tekster hvis vi har andre kandidater
            if len(text) < 5 and all(len(c.strip()) < 5 for c in candidate_texts):
                return None

            # Parse dato og tid ved å prøve kandidat-tekstene
            meeting_date = None
            meeting_time = None
            for cand in candidate_texts:
                if not cand:
                    continue
                md = self.parse_date_from_text(cand)
                if md:
                    meeting_date = md
                    meeting_time = self.parse_time_from_text(cand) or meeting_time
                    break

            if not meeting_date:
                return None
            
            # Finn møtetittel - mer aggressiv søking
            title = ""
            
            # 1. Prøv å finne tittel i element selv
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                title = element.get_text(strip=True)
            else:
                # 2. Søk etter tittel i child-elementer
                title_element = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b'])
                if title_element:
                    title = title_element.get_text(strip=True)
                else:
                    # 3. Bruk første del av teksten som tittel
                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if len(line) > 3 and not re.search(r'\d{1,2}\.\d{1,2}\.\d{4}', line):
                            title = line
                            break
            
            # Rens opp tittel
            if title:
                title = re.sub(r'\d{1,2}\.\d{1,2}\.\d{4}.*', '', title).strip()
                title = re.sub(r'kl\.?\s*\d{1,2}:\d{2}.*', '', title).strip()
                title = re.sub(r'\s+', ' ', title)  # Normaliser whitespace
                
                # Fjern vanlige suffixer/prefixes
                title = re.sub(r'^(Møte i |Møte |Meeting )', '', title, flags=re.I)
                
                # Fjern kalender-relaterte ord og navigasjon
                title = re.sub(r'(mandagtirsdagonsdagtorsdagfredaglørdagsøndag|MøtekalenderFor|I dagForrigeNeste)', '', title, flags=re.I)
                title = re.sub(r'\d{8,}', '', title)  # Fjern lange tall-sekvenser
                title = re.sub(r'\+\d+\s*møter', '', title, flags=re.I)  # Fjern "+2 møter" osv
                title = re.sub(r'(utvalg){2,}', 'utvalg', title, flags=re.I)  # Fjern dupliserte "utvalg"
                
                # Trim og rens opp igjen
                title = re.sub(r'\s+', ' ', title).strip()
                
                # Hvis tittelen er for kort eller rar, bruk en generisk tittel
                if len(title) < 3 or re.match(r'^[0-9\s\+\-]+$', title):
                    title = "Politisk møte"
            
            if not title or len(title) < 3:
                # Siste forsøk: bruk tekst før første dato i teksten
                m_first = re.search(r"(\d{1,2}[\.\-/]\d{1,2}[\.\-/]\d{2,4})", text)
                if m_first:
                    before_date = text.split(m_first.group(0))[0].strip()
                    if before_date and len(before_date) > 3:
                        title = before_date
                    else:
                        title = "Politisk møte"
                else:
                    title = "Politisk møte"
            
            # Finn møtested - forbedret søking
            location = "Ikke oppgitt"

            # Filtrer bort generiske/utility-tekster som ikke er ekte møter
            blacklist_patterns = [
                r'søk etter møte', r'resultatside med møter', r'søk etter møter', r'resultatside', r'møtekalender', r'vis flere'
            ]
            lowertitle = title.lower() if title else ''
            for bp in blacklist_patterns:
                if re.search(bp, lowertitle):
                    return None
            
            # Søk etter sted-indikatorer på norsk og nynorsk
            location_patterns = [
                r'(?:Sted|Stad|Møtested|Møtestad):\s*([^,\n\r]+)',
                r'(?:Lokale|Sal|Rom):\s*([^,\n\r]+)',
                r'(?:Adresse):\s*([^,\n\r]+)'
            ]
            
            for pattern in location_patterns:
                location_match = re.search(pattern, text, re.IGNORECASE)
                if location_match:
                    location = location_match.group(1).strip()
                    break
            
            # Hvis ingen eksplisitt sted, søk etter vanlige møtested-ord
            if location == "Ikke oppgitt":
                location_words = re.findall(r'\b(?:kommunestyresalen|formannskapssalen|rådhuset|møterom|kommunehuset)\b', text, re.IGNORECASE)
                if location_words:
                    location = location_words[0].title()
            
            return {
                'title': title[:100],  # Begrens tittel-lengde
                'date': meeting_date.strftime('%Y-%m-%d'),
                'time': meeting_time,
                'location': location[:50],  # Begrens sted-lengde
                'kommune': kommune_name,
                'raw_text': text[:300]  # For debugging, begrens lengde
            }
            
        except Exception as e:
            print(f"Feil ved ekstraksjon av møtedata: {e}")
            return None

def scrape_all_meetings(
    kommune_configs: Optional[Sequence[Dict]] = None,
    calendar_sources: Optional[Sequence[str]] = None,
    *,
    days_ahead: int = 10,
) -> List[Dict]:
    """Scraper møter for angitte kommuner og kalendere."""
    all_meetings: List[Dict] = []

    kommuner = list(kommune_configs) if kommune_configs is not None else get_default_kommune_configs()
    aktive_kalendere: Sequence[str] = tuple(calendar_sources or ("arrangementer_sa",))
    debug_mode = "--debug" in sys.argv or "--test" in sys.argv

    # Hent møter fra Google Calendar først
    if CALENDAR_AVAILABLE and aktive_kalendere:
        print("📅 Henter møter fra Google Calendar...")
        try:
            if 'get_calendar_meetings_for_sources' in globals() and callable(get_calendar_meetings_for_sources):  # type: ignore[name-defined]
                calendar_meetings = get_calendar_meetings_for_sources(
                    aktive_kalendere,
                    days_ahead=days_ahead,
                    test_mode=debug_mode,
                )
            else:
                calendar_meetings = get_calendar_meetings(days_ahead=days_ahead, test_mode=debug_mode)  # type: ignore[misc]
            all_meetings.extend(calendar_meetings)
            print(f"Fant {len(calendar_meetings)} møter fra Google Calendar")
            # Diagnostic: list any meetings that originate from the turnus calendar
            turnus_found = [m for m in calendar_meetings if (m.get('source') or '').startswith('calendar:turnus') or (m.get('kommune') or '').strip().lower() == 'turnus']
            if turnus_found:
                print(f"🔍 Oppdaget {len(turnus_found)} turnus-møter fra kalender:")
                for m in turnus_found:
                    print(f"  - {m.get('date')} {m.get('time') or 'hele dagen'}: {m.get('title')} ({m.get('kommune')}) [source={m.get('source')}]")
            else:
                print("🔍 Ingen turnus-møter funnet i kalenderhentingen")
            # Additional diagnostic: search for likely keywords that might indicate Turnus entries
            keywords = ['turnus', 'turnusfri', 'hans christian']
            matches = []
            for m in calendar_meetings:
                txt = " ".join(filter(None, [str(m.get('title','')).lower(), str(m.get('raw_text','')).lower(), str(m.get('kommune','')).lower()]))
                if any(k in txt for k in keywords):
                    matches.append(m)
            if matches:
                print(f"🔎 Fant {len(matches)} kalenderhendelser som matcher søkeord {keywords}:")
                for m in matches:
                    print(f"  * {m.get('date')} {m.get('time') or 'hele dagen'}: {m.get('title')} ({m.get('kommune')}) [source={m.get('source')}] raw='{(m.get('raw_text') or '')[:80]}'")
        except Exception as e:
            print(f"⚠️  Google Calendar-feil: {e}")

    # Separer sider basert på om de trenger Playwright
    js_heavy_sites: List[Dict] = []
    standard_sites: List[Dict] = []
    retry_playwright_sites: List[Dict] = []
    parser: Optional[MoteParser] = None

    def _ensure_parser() -> MoteParser:
        nonlocal parser
        if parser is None:
            parser = MoteParser()
        return parser

    def _scrape_with_requests(config: Dict) -> List[Dict]:
        parser_instance = _ensure_parser()

        if EIGERSUND_AVAILABLE and (
            "eigersund" in config.get("url", "").lower()
            or "eigersund" in config.get("name", "").lower()
        ):
            try:
                print(f"🔎 Spesialparser for {config['name']}")
                return parse_eigersund_meetings(config["url"], config["name"])
            except Exception as exc:  # pragma: no cover - logging already helpful
                print(f"⚠️  Eigersund parser-feil: {exc}")
                return []

        site_type = config.get("type")
        try:
            if site_type == "acos":
                return parser_instance.parse_acos_site(config["url"], config["name"])
            if site_type == "custom":
                return parser_instance.parse_custom_site(config["url"], config["name"])
            if site_type == "onacos":
                return parser_instance.parse_onacos_site(config["url"], config["name"])
            if site_type == "elements":
                return parser_instance.parse_elements_site(config["url"], config["name"])
            print(f"Ukjent sidetype: {site_type}")
        except Exception as exc:  # pragma: no cover - network dependent
            print(f"⚠️  Feil ved parsing av {config['name']}: {exc}")
        return []

    def _should_retry_with_playwright(config: Dict) -> bool:
        url_value = (config.get('url') or '').lower()
        return 'opengov.360online.com' in url_value or '360online.com/meetings' in url_value

    for kommune_config in kommuner:
        url_value = (kommune_config.get('url') or '').lower()
        # ACOS/Onacos/Elements, Digdem og andre JS-baserte innsynsider trenger Playwright
        requires_playwright = (
            kommune_config['type'] in ['elements', 'onacos']
            or 'innsynpluss' in url_value
            or 'digdem' in url_value
        )
        if requires_playwright:
            js_heavy_sites.append(kommune_config)
        else:
            standard_sites.append(kommune_config)
    
    # Scrape standard sider med requests/BeautifulSoup
    if standard_sites:
        for kommune_config in standard_sites:
            print(f"📄 Scraper {kommune_config['name']} (standard)...")
            meetings = _scrape_with_requests(kommune_config)
            # Legg på kilde-URL for hvert møte slik at Slack-meldingen kan linke tilbake
            for m in meetings:
                if 'url' not in m or not m.get('url'):
                    m['url'] = kommune_config.get('url')
                all_meetings.append(m)
            print(f"Fant {len(meetings)} møter fra {kommune_config['name']}")
            if not meetings and _should_retry_with_playwright(kommune_config):
                retry_playwright_sites.append(kommune_config)

    playwright_targets: List[Dict] = list(js_heavy_sites)
    seen_names = {cfg['name'] for cfg in js_heavy_sites}
    for cfg in retry_playwright_sites:
        if cfg['name'] not in seen_names:
            playwright_targets.append(cfg)
            seen_names.add(cfg['name'])

    # Scrape JavaScript-tunge sider med Playwright
    if playwright_targets and PLAYWRIGHT_AVAILABLE:
        print("\n🎭 Bruker Playwright for JavaScript-tunge sider...")
        try:
            playwright_meetings = asyncio.run(scrape_with_playwright(playwright_targets))
            # Sørg for at hvert møte fra Playwright også har en kilde-URL (basert på config)
            name_to_url = {c['name']: c.get('url') for c in playwright_targets}
            for m in playwright_meetings:
                if 'url' not in m or not m.get('url'):
                    # Forsøk å mappe kommune-navn til konfig URL
                    m['url'] = name_to_url.get(m.get('kommune')) or ''
                all_meetings.append(m)
            print(f"Playwright fant {len(playwright_meetings)} møter totalt")
        except Exception as e:
            print(f"Playwright-feil: {e}")
    elif playwright_targets:
        print("⚠️  Playwright ikke tilgjengelig for JavaScript-tunge sider – faller tilbake til requests-basert parsing.")
        for kommune_config in playwright_targets:
            print(f"📄 Scraper {kommune_config['name']} (fallback)...")
            meetings = _scrape_with_requests(kommune_config)
            for m in meetings:
                if 'url' not in m or not m.get('url'):
                    m['url'] = kommune_config.get('url')
                all_meetings.append(m)
            print(f"Fant {len(meetings)} møter fra {kommune_config['name']} via fallback")
    
    # Hvis ingen møter ble funnet, bruk mock-data for demo
    if len(all_meetings) == 0:
        print("\n⚠️  Ingen møter funnet via scraping. Bruker mock-data for demo...")
        try:
            from .mock_data import get_mock_meetings
            all_meetings = get_mock_meetings()
            print(f"Lastet {len(all_meetings)} mock-møter")
        except ImportError:
            print("Mock-data ikke tilgjengelig")
    
    return all_meetings

def filter_meetings_by_date_range(
    meetings: Sequence[Union[Meeting, Mapping[str, object]]],
    days_ahead: int = 10,
) -> List[Meeting]:
    """Filtrer møter for dagens dato + angitt antall dager frem."""
    today = datetime.now().date()
    end_date = today + timedelta(days=days_ahead)
    
    filtered_meetings: List[Meeting] = []
    normalized = [ensure_meeting(m) for m in meetings]

    for meeting in normalized:
        try:
            meeting_date = datetime.strptime(meeting.date, '%Y-%m-%d').date()
            if today <= meeting_date <= end_date:
                filtered_meetings.append(meeting)
        except ValueError:
            continue
    
    # Sorter etter dato og tid
    filtered_meetings.sort(key=lambda meeting: meeting.sort_key())
    return filtered_meetings


def split_meetings_for_turnus(
    meetings: Sequence[Meeting],
) -> Tuple[List[Meeting], List[Meeting]]:
    """Del møter i turnus-kommuner/kalender vs øvrige kommuner."""

    turnus_meetings: List[Meeting] = []
    other_meetings: List[Meeting] = []

    for meeting in meetings:
        if (meeting.kommune in TURNUS_KOMMUNER) or (meeting.source == TURNUS_CALENDAR_SOURCE):
            turnus_meetings.append(meeting)
        else:
            other_meetings.append(meeting)

    return turnus_meetings, other_meetings


def build_slack_batches(meetings: Sequence[Meeting]) -> List[Tuple[str, List[Meeting]]]:
    """Lag separate Slack-batcher for turnus-kommuner og øvrige kommuner."""

    turnus_meetings, other_meetings = split_meetings_for_turnus(meetings)

    batches: List[Tuple[str, List[Meeting]]] = []

    if turnus_meetings:
        batches.append(("turnus", turnus_meetings))
    if other_meetings:
        batches.append(("ovrige", other_meetings))

    if not batches:
        batches.append(("alle", []))

    return batches

def _fallback_meetings(days_ahead: int) -> List[Meeting]:
    try:
        from .mock_data import get_mock_meetings

        mock_meetings = get_mock_meetings()
        return filter_meetings_by_date_range(mock_meetings, days_ahead=days_ahead)
    except ImportError:
        print("Mock-data ikke tilgjengelig")
        return []


def collect_meetings_for_pipeline(
    pipeline: PipelineConfig,
    *,
    days_ahead: int,
) -> List[Meeting]:
    kommune_configs = get_kommune_configs(pipeline.kommune_groups)
    if not kommune_configs and not pipeline.calendar_sources:
        print(f"⚠️  Pipeline {pipeline.key} har ingen kilder definert – hopper over")
        return []

    meetings = scrape_all_meetings(
        kommune_configs,
        pipeline.calendar_sources,
        days_ahead=days_ahead,
    )
    filtered_meetings = filter_meetings_by_date_range(meetings, days_ahead=days_ahead)

    if filtered_meetings:
        return filtered_meetings

    print(f"⚠️  Pipeline {pipeline.key} fant ingen møter i perioden. Bruker mock-data...")
    return _fallback_meetings(days_ahead)


def run_pipeline(
    pipeline: PipelineConfig,
    *,
    days_ahead: int = 10,
    force_send: bool = False,
    debug_mode: bool = False,
) -> bool:
    print(f"\n🚀 Kjører pipeline '{pipeline.key}': {pipeline.description}")

    meetings = collect_meetings_for_pipeline(
        pipeline,
        days_ahead=days_ahead,
    )

    normalized_meetings = [ensure_meeting(meeting) for meeting in meetings]
    batches = build_slack_batches(normalized_meetings)
    expected_by_label = _expected_kommuner_by_batch(pipeline)

    if debug_mode:
        print("🎭 DEBUG-MODUS: Viser Slack-meldinger uten å sende")
        print("=" * 50)
        for idx, (label, batch) in enumerate(batches, start=1):
            suffix = _format_heading_suffix(label, batch)
            expected = expected_by_label.get(label) or expected_by_label.get("alle")
            print(f"Melding {idx}/{len(batches)} ({suffix})")
            print(
                format_slack_message(
                    batch,
                    heading_suffix=suffix,
                    expected_kommuner=expected,
                )
            )
            print("-" * 50)
        print("=" * 50)
        return True

    overall_success = True
    webhook_cache: Dict[str, Tuple[Optional[str], str, bool]] = {}
    notified_fallback_envs: set[str] = set()
    for idx, (label, batch) in enumerate(batches, start=1):
        suffix = _format_heading_suffix(label, batch)
        expected = expected_by_label.get(label) or expected_by_label.get("alle")
        slack_message = format_slack_message(
            batch,
            heading_suffix=suffix,
            expected_kommuner=expected,
        )
        target_env = pipeline.batch_webhook_envs.get(label, pipeline.slack_webhook_env)

        if target_env not in webhook_cache:
            webhook_cache[target_env] = _resolve_slack_webhook(target_env)

        resolved_webhook, resolved_env, used_fallback = webhook_cache[target_env]

        if not resolved_webhook:
            print(
                f"ℹ️  Miljøvariabelen {target_env} er ikke satt. "
                f"Hopper over sending for batch '{label}' i pipeline {pipeline.key}."
            )
            overall_success = overall_success and not force_send
            continue

        if used_fallback and target_env not in notified_fallback_envs:
            print(
                f"ℹ️  Bruker {resolved_env} som fallback for {target_env} i pipeline {pipeline.key}."
            )
            notified_fallback_envs.add(target_env)

        print(f"✉️  Sender Slack-melding {idx}/{len(batches)} ({suffix})...")
        batch_success = send_to_slack(
            slack_message,
            force_send=force_send,
            webhook_env=resolved_env,
            webhook_url=resolved_webhook,
        )
        if not batch_success:
            print(
                f"❌ Slack-sending feilet for melding {idx} i pipeline {pipeline.key}"
            )
        overall_success = overall_success and batch_success

    return overall_success

def send_to_slack(
    message: str,
    force_send: bool = False,
    *,
    webhook_env: str = "SLACK_WEBHOOK_URL",
    webhook_url: Optional[str] = None,
) -> bool:
    """
    Send melding til Slack via webhook.
    
    Args:
        message: Slack-melding som skal sendes
        force_send: Hvis True, send melding selv i test-modus
    """
    resolved_webhook = webhook_url or os.getenv(webhook_env)
    if not resolved_webhook:
        print(f"{webhook_env} environment variable ikke satt")
        return False
    
    # Sjekk om vi er i test-modus (hindrer utilsiktet sending)
    is_test_mode = (
        '--debug' in sys.argv or 
        '--test' in sys.argv or
        os.getenv('TESTING', '').lower() in ['true', '1', 'yes']
    )
    
    if is_test_mode and not force_send:
        print("🚫 Test-modus: Sender IKKE til Slack (bruk --force for å overstyre)")
        if resolved_webhook:
            print(f"Webhook URL: {resolved_webhook[:50]}...")
        print("Melding som VILLE blitt sendt:")
        print("=" * 40)
        print(message)
        print("=" * 40)
        return True  # Returner True for test-formål
    
    payload = {
        'text': message,
        'username': 'Politikk-bot',
        'icon_emoji': ':classical_building:'
    }
    
    try:
        response = requests.post(resolved_webhook, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ Melding sendt til Slack!")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Feil ved sending til Slack: {e}")
        return False

def main():
    """Hovedfunksjon."""
    print("🏛️  Starter scraping av politiske møter...")
    
    force_send = '--force' in sys.argv
    debug_mode = '--debug' in sys.argv or '--test' in sys.argv
    days_ahead = 10

    pipelines = get_pipeline_configs()
    if not pipelines:
        print("⚠️  Ingen pipeline-konfigurasjoner funnet. Ingenting å gjøre.")
        return

    overall_success = True
    for pipeline in pipelines:
        success = run_pipeline(
            pipeline,
            days_ahead=days_ahead,
            force_send=force_send,
            debug_mode=debug_mode,
        )
        overall_success = overall_success and success

    if not debug_mode and not overall_success:
        sys.exit(1)

if __name__ == '__main__':
    main()
