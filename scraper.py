#!/usr/bin/env python3
"""
Politiske møter scraper for Slack-notifikasj    {
        "name": "Rogaland fylkeskommune",
        "url": "https://prod01.elementscloud.no/publikum/971045698/Dmb",
        "type": "elements_cloud"
    }
Henter møtedata fra kommunale nettsider og sender daglig sammendrag til Slack.
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
import sys
import asyncio
from urllib.parse import urljoin

# Import Playwright scraper for JavaScript-heavy sites
try:
    from playwright_scraper import scrape_with_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright ikke tilgjengelig. Bruker kun requests/BeautifulSoup.")

# Import Google Calendar integration
try:
    from calendar_integration import add_meetings_to_google_calendar
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False
    print("⚠️  Google Calendar-integrasjon ikke tilgjengelig.")

# Konfigurasjon av kilde-URLer
KOMMUNE_URLS = [
    {
        "name": "Sauda kommune",
        "url": "https://www.sauda.kommune.no/innsyn/politiske-moter/",
        "type": "acos"
    },
    {
        "name": "Strand kommune",
        "url": "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/politiske-moter-og-sakspapirer/politisk-motekalender/",
        "type": "acos"
    },
    {
        "name": "Suldal kommune", 
        "url": "https://www.suldal.kommune.no/innsyn/politiske-moter/",
        "type": "acos"
    },
    {
        "name": "Hjelmeland kommune",
        "url": "https://www.hjelmeland.kommune.no/politikk/moteplan-og-sakspapir/innsyn-moteplan/",
        "type": "acos"
    },
    {
        "name": "Sirdal kommune",
        "url": "https://innsynpluss.onacos.no/sirdal/moteoversikt/",
        "type": "onacos"
    },
    {
        "name": "Rogaland fylkeskommune",
        "url": "https://prod01.elementscloud.no/publikum/971045698/Dmb",
        "type": "elements"
    },
    {
        "name": "Sokndal kommune",
        "url": "https://www.sokndal.kommune.no/innsyn/moteoversikt/",
        "type": "acos"
    },
    {
        "name": "Bjerkreim kommune",
        "url": "https://www.bjerkreim.kommune.no/innsyn/moteplan-og-sakslister/",
        "type": "acos"
    },
    {
        "name": "Bymiljøpakken",
        "url": "https://bymiljopakken.no/moter/",
        "type": "custom"
    },
    {
        "name": "Eigersund kommune",
        "url": "https://innsyn.onacos.no/eigersund/mote/wfinnsyn.ashx?response=moteplan&",
        "type": "onacos"
    },
    
]

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
                    header_texts = headers
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
            
            meetings = []
            
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
    
    def _extract_meeting_from_element(self, element, kommune_name: str) -> Optional[Dict]:
        """Ekstraherer møteinfo fra HTML-element."""
        try:
            text = element.get_text(strip=True)

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

def scrape_all_meetings() -> List[Dict]:
    """Scraper alle møter fra alle konfigurerte kommuner."""
    all_meetings = []
    
    # Separer sider basert på om de trenger Playwright
    js_heavy_sites = []
    standard_sites = []
    
    for kommune_config in KOMMUNE_URLS:
        # ACOS/Onacos/Elements og andre JS-baserte innsynsider trenger Playwright
        if kommune_config['type'] in ['elements', 'onacos', 'acos'] or 'innsynpluss' in kommune_config['url']:
            js_heavy_sites.append(kommune_config)
        else:
            standard_sites.append(kommune_config)
    
    # Scrape standard sider med requests/BeautifulSoup
    if standard_sites:
        parser = MoteParser()
        for kommune_config in standard_sites:
            print(f"📄 Scraper {kommune_config['name']} (standard)...")
            
            if kommune_config['type'] == 'acos':
                meetings = parser.parse_acos_site(kommune_config['url'], kommune_config['name'])
            elif kommune_config['type'] == 'custom':
                meetings = parser.parse_custom_site(kommune_config['url'], kommune_config['name'])
            else:
                print(f"Ukjent sidetype: {kommune_config['type']}")
                continue
            # Legg på kilde-URL for hvert møte slik at Slack-meldingen kan linke tilbake
            for m in meetings:
                if 'url' not in m or not m.get('url'):
                    m['url'] = kommune_config.get('url')
                all_meetings.append(m)
            print(f"Fant {len(meetings)} møter fra {kommune_config['name']}")
    
    # Scrape JavaScript-tunge sider med Playwright
    if js_heavy_sites and PLAYWRIGHT_AVAILABLE:
        print("\n🎭 Bruker Playwright for JavaScript-tunge sider...")
        try:
            playwright_meetings = asyncio.run(scrape_with_playwright(js_heavy_sites))
            # Sørg for at hvert møte fra Playwright også har en kilde-URL (basert på config)
            name_to_url = {c['name']: c.get('url') for c in js_heavy_sites}
            for m in playwright_meetings:
                if 'url' not in m or not m.get('url'):
                    # Forsøk å mappe kommune-navn til konfig URL
                    m['url'] = name_to_url.get(m.get('kommune')) or ''
                all_meetings.append(m)
            print(f"Playwright fant {len(playwright_meetings)} møter totalt")
        except Exception as e:
            print(f"Playwright-feil: {e}")
    elif js_heavy_sites:
        print("⚠️  Playwright ikke tilgjengelig for JavaScript-tunge sider")
    
    # Hvis ingen møter ble funnet, bruk mock-data for demo
    if len(all_meetings) == 0:
        print("\n⚠️  Ingen møter funnet via scraping. Bruker mock-data for demo...")
        try:
            from mock_data import get_mock_meetings
            all_meetings = get_mock_meetings()
            print(f"Lastet {len(all_meetings)} mock-møter")
        except ImportError:
            print("Mock-data ikke tilgjengelig")
    
    return all_meetings

def filter_meetings_by_date_range(meetings: List[Dict], days_ahead: int = 9) -> List[Dict]:
    """Filtrer møter for dagens dato + angitt antall dager frem."""
    today = datetime.now().date()
    end_date = today + timedelta(days=days_ahead)
    
    filtered_meetings = []
    for meeting in meetings:
        try:
            meeting_date = datetime.strptime(meeting['date'], '%Y-%m-%d').date()
            if today <= meeting_date <= end_date:
                filtered_meetings.append(meeting)
        except ValueError:
            continue
    
    # Sorter etter dato og tid
    filtered_meetings.sort(key=lambda x: (x['date'], x['time'] or '00:00'))
    return filtered_meetings

def format_slack_message(meetings: List[Dict]) -> str:
    """Formater møter til Slack-melding."""
    if not meetings:
        return "📅 *Politiske møter de neste 10 dagene*\n\nIngen møter funnet i perioden."
    
    message = "📅 *Politiske møter de neste 10 dagene*\n\n"
    
    current_date = None
    for meeting in meetings:
        meeting_date = datetime.strptime(meeting['date'], '%Y-%m-%d')
        
        # Ny dato-overskrift
        if current_date != meeting['date']:
            current_date = meeting['date']
            date_str = meeting_date.strftime('%A %d. %B %Y')
            
            # Norske dagnavn
            date_str = date_str.replace('Monday', 'Mandag')
            date_str = date_str.replace('Tuesday', 'Tirsdag')  
            date_str = date_str.replace('Wednesday', 'Onsdag')
            date_str = date_str.replace('Thursday', 'Torsdag')
            date_str = date_str.replace('Friday', 'Fredag')
            date_str = date_str.replace('Saturday', 'Lørdag')
            date_str = date_str.replace('Sunday', 'Søndag')
            
            message += f"\n*{date_str}*\n"
        
        # Møteinfo - gjør linjen klikkbar tilbake til kildesiden hvis URL finnes
        display_title = f"{meeting['title']} ({meeting['kommune']})"
        if meeting.get('url'):
            # Slack format for link: <url|tekst>
            display_title = f"<{meeting['url']}|{display_title}>"

        # Vis tid kun hvis vi har den
        if meeting.get('time'):
            message += f"• {display_title} - kl. {meeting['time']}\n"
        else:
            message += f"• {display_title}\n"

        if meeting.get('location') and meeting['location'] != "Ikke oppgitt":
            message += f"  {meeting['location']}\n"
    
    return message

def send_to_slack(message: str, force_send: bool = False) -> bool:
    """
    Send melding til Slack via webhook.
    
    Args:
        message: Slack-melding som skal sendes
        force_send: Hvis True, send melding selv i test-modus
    """
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if not webhook_url:
        print("SLACK_WEBHOOK_URL environment variable ikke satt")
        return False
    
    # Sjekk om vi er i test-modus (hindrer utilsiktet sending)
    is_test_mode = (
        '--debug' in sys.argv or 
        '--test' in sys.argv or
        os.getenv('TESTING', '').lower() in ['true', '1', 'yes']
    )
    
    if is_test_mode and not force_send:
        print("🚫 Test-modus: Sender IKKE til Slack (bruk --force for å overstyre)")
        print(f"Webhook URL: {webhook_url[:50]}...")
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
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ Melding sendt til Slack!")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Feil ved sending til Slack: {e}")
        return False

def main():
    """Hovedfunksjon."""
    print("🏛️  Starter scraping av politiske møter...")
    
    # Sjekk for force-send flag
    force_send = '--force' in sys.argv
    debug_mode = '--debug' in sys.argv or '--test' in sys.argv
    calendar_mode = '--calendar' in sys.argv or os.getenv('ENABLE_CALENDAR', '').lower() in ['true', '1', 'yes']
    
    # Scrape møter
    all_meetings = scrape_all_meetings()
    print(f"📊 Totalt funnet {len(all_meetings)} møter")
    
    # Filtrer for neste 10 dager
    filtered_meetings = filter_meetings_by_date_range(all_meetings, days_ahead=9)
    print(f"📅 Filtrert til {len(filtered_meetings)} møter for de neste 10 dagene")
    
    # Hvis ingen møter i perioden, bruk mock-data
    if len(filtered_meetings) == 0:
        print("\n⚠️  Ingen møter i neste 10-dagers periode. Bruker mock-data...")
        try:
            from mock_data import get_mock_meetings
            mock_meetings = get_mock_meetings()
            filtered_meetings = filter_meetings_by_date_range(mock_meetings, days_ahead=9)
            print(f"Lastet {len(filtered_meetings)} mock-møter for de neste 10 dagene")
        except ImportError:
            print("Mock-data ikke tilgjengelig")
    
    # Debug output
    if debug_mode:
        print("\n🔍 Debug - funnet møter:")
        for meeting in filtered_meetings:
            print(f"  📅 {meeting['date']} {meeting['time'] or 'ukjent tid'} - {meeting['title']} ({meeting['kommune']})")
        print()
    
    # Lag Slack-melding
    slack_message = format_slack_message(filtered_meetings)
    
    # Send til Slack (med sikkerhet mot utilsiktet sending)
    slack_success = False
    if debug_mode:
        print("🎭 DEBUG-MODUS: Viser Slack-melding uten å sende")
        print("=" * 50)
        print(slack_message)
        print("=" * 50)
        print("\nFor å sende til Slack:")
        print("  python scraper.py --force")
        print("  ELLER sett TESTING=false")
        slack_success = True  # Behandle som vellykket i debug-modus
    else:
        slack_success = send_to_slack(slack_message, force_send=force_send)
        if not slack_success:
            print("❌ Slack-sending feilet")
    
    # Google Calendar-integrasjon (kun hvis Slack var vellykket eller i debug-modus)
    if calendar_mode and CALENDAR_AVAILABLE and (slack_success or debug_mode):
        print("\n📅 Legger til møter i Google Calendar...")
        try:
            added_count = add_meetings_to_google_calendar(filtered_meetings, test_mode=debug_mode)
            if debug_mode:
                print(f"🧪 VILLE lagt til {added_count} møter i Google Calendar")
            else:
                print(f"✅ Lagt til {added_count} nye møter i Google Calendar")
        except Exception as e:
            print(f"❌ Google Calendar-feil: {e}")
    elif calendar_mode and not CALENDAR_AVAILABLE:
        print("⚠️  Google Calendar-integrasjon ikke tilgjengelig (mangler avhengigheter)")
    elif calendar_mode:
        print("⚠️  Google Calendar-integrasjon hoppet over (Slack-sending feilet)")
    
    # Exit med feilkode hvis noe feilet (kun i produksjon)
    if not debug_mode and not slack_success:
        sys.exit(1)

if __name__ == '__main__':
    main()
