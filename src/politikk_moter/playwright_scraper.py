#!/usr/bin/env python3
"""
Playwright-basert scraper for JavaScript-tunge kommunesider.
"""

# pylint: disable=broad-exception-caught

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List, Dict, Optional


class PlaywrightMoteParser:
    def __init__(self):
        self.browser = None
        self.context = None
        self.playwright = None
        self._current_base_url: str = ""
        self._oslo_tz = ZoneInfo("Europe/Oslo")

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def scrape_javascript_site(self, url: str, kommune_name: str) -> List[Dict]:
        try:
            print(f"🎭 Playwright: Scraper {kommune_name}...")
            page = await self.context.new_page()
            self._current_base_url = url
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(2500)
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            meetings = self._extract_meetings_from_soup(soup, kommune_name)
            await page.close()
            return meetings
        except Exception as e:
            print(f"Playwright feil for {kommune_name}: {e}")
            return []
        finally:
            self._current_base_url = ""

    def _normalize_time_str(self, hh: str, mm: str) -> Optional[str]:
        try:
            hh_i = int(hh); mm_i = int(mm)
            if 0 <= hh_i < 24 and 0 <= mm_i < 60:
                return f"{hh_i:02d}:{mm_i:02d}"
        except Exception:
            return None
        return None

    async def scrape_elements_cloud(self, url: str, kommune_name: Optional[str] = None) -> List[Dict]:
        try:
            kommune_label = kommune_name or url
            print(f"🎭 Playwright Elements Cloud: {kommune_label}")
            page = await self.context.new_page()
            self._current_base_url = url
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(4000)
            try:
                await page.wait_for_selector('table, .meeting, .møte, .calendar', timeout=8000)
            except Exception:
                pass
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            meetings = self._extract_elements_meetings(soup, kommune_label)
            self._attach_elements_urls(meetings, url)

            # For meetings without explicit time, try opening the meeting detail pages
            for meeting in meetings:
                try:
                    if meeting.get('time') in (None, 'TBD') and meeting.get('href'):
                        target = urljoin(url, meeting['href'])
                        detail_page = await self.context.new_page()
                        await detail_page.goto(target, wait_until='networkidle', timeout=20000)
                        await detail_page.wait_for_timeout(1000)
                        detail_html = await detail_page.content()
                        dsoup = BeautifulSoup(detail_html, 'html.parser')

                        # 1) <time datetime="..."> preferert
                        time_tag = dsoup.find('time')
                        found_time = None
                        if time_tag and time_tag.get('datetime'):
                            try:
                                dt = datetime.fromisoformat(time_tag.get('datetime').split('+')[0])
                                found_time = dt.strftime('%H:%M')
                            except Exception:
                                pass

                        # 2) meta tags eller data-attributter
                        if not found_time:
                            meta = dsoup.find('meta', {'property': 'event:start'}) or dsoup.find('meta', {'name': 'event:start'})
                            if meta and meta.get('content'):
                                try:
                                    dt = datetime.fromisoformat(meta.get('content').split('+')[0])
                                    found_time = dt.strftime('%H:%M')
                                except Exception:
                                    pass

                        # 3) Regex i detaljsiden: prefer colon-format, fallback 'kl X.YY'
                        if not found_time:
                            text_blob = dsoup.get_text(' ', strip=True)
                            tm = re.search(r'(\d{1,2}):(\d{2})', text_blob)
                            if not tm:
                                tm = re.search(r'(?:kl\.?\s*)(\d{1,2})[.](\d{2})', text_blob)
                            if tm:
                                hh, mm = tm.groups()
                                found_time = self._normalize_time_str(hh, mm)

                        if found_time:
                            meeting['time'] = found_time

                        await detail_page.close()
                except Exception:
                    # ikke fatal, beholder eksisterende meeting
                    continue
            await page.close()
            return meetings
        except Exception as e:
            print(f"Elements Cloud Playwright feil: {e}")
            return []
        finally:
            self._current_base_url = ""

    async def scrape_onacos_site(self, url: str, kommune_name: str) -> List[Dict]:
        try:
            print(f"🎭 Playwright Onacos: {kommune_name}")
            page = await self.context.new_page()
            self._current_base_url = url
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(4000)
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            meetings = self._extract_meetings_from_soup(soup, kommune_name)
            await page.close()
            return meetings
        except Exception as e:
            print(f"Onacos Playwright feil for {kommune_name}: {e}")
            return []
        finally:
            self._current_base_url = ""

    async def scrape_digdem_site(self, url: str, kommune_name: str) -> List[Dict]:
        page = None
        try:
            print(f"🎭 Playwright Digdem: {kommune_name}")
            page = await self.context.new_page()
            self._current_base_url = url
            await page.goto(url, wait_until='networkidle', timeout=45000)
            await page.wait_for_function("() => window.__APOLLO_CLIENT__ && window.__APOLLO_CLIENT__.cache", timeout=20000)
            await page.wait_for_timeout(1500)

            try:
                right_button = page.locator('button:has(svg.tabler-icon-chevron-right)')
                if await right_button.count() > 0:
                    await right_button.first.click()
                    await page.wait_for_timeout(2000)
            except Exception:
                pass

            apollo_cache = await page.evaluate("""
                () => {
                    if (!window.__APOLLO_CLIENT__) {
                        return null;
                    }
                    try {
                        return window.__APOLLO_CLIENT__.cache.extract();
                    } catch (error) {
                        return null;
                    }
                }
            """)

            meetings = self._extract_digdem_meetings(apollo_cache, kommune_name, url)
            await page.close()
            return meetings
        except Exception as exc:
            print(f"Digdem Playwright feil for {kommune_name}: {exc}")
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            return []
        finally:
            self._current_base_url = ""

    def _extract_digdem_meetings(self, cache: Optional[Dict], kommune_name: str, base_url: str) -> List[Dict]:
        if not cache or not isinstance(cache, dict):
            return []

        commission_names_by_ref: Dict[str, str] = {}
        commission_names_by_id: Dict[str, str] = {}
        for key, value in cache.items():
            if not isinstance(value, dict):
                continue
            if key.startswith('Commission:') and value.get('name'):
                commission_names_by_ref[key] = value['name']
                if value.get('id'):
                    commission_names_by_id[value['id']] = value['name']

        meetings: List[Dict] = []
        seen_ids: set[str] = set()
        now = datetime.now(self._oslo_tz)
        earliest = now - timedelta(days=2)
        latest = now + timedelta(days=400)

        for key, value in cache.items():
            if not isinstance(value, dict) or not key.startswith('Meeting:'):
                continue

            meeting_id = value.get('id')
            date_raw = value.get('date') or value.get('endDateTime')
            if not meeting_id or not date_raw or meeting_id in seen_ids:
                continue

            try:
                start_dt = datetime.fromisoformat(date_raw.replace('Z', '+00:00'))
                start_local = start_dt.astimezone(self._oslo_tz)
            except Exception:
                continue

            if start_local < earliest or start_local > latest:
                continue

            commission_ref = None
            commission_name = None
            commission = value.get('commission') or {}
            if isinstance(commission, dict):
                commission_ref = commission.get('__ref')
            if commission_ref:
                commission_name = commission_names_by_ref.get(commission_ref)
                if not commission_name and ':' in commission_ref:
                    commission_name = commission_names_by_id.get(commission_ref.split(':', 1)[1])

            base_title = value.get('meetingName') or commission_name or 'Politisk møte'
            status = (value.get('status') or '').strip()
            if status and status.lower() != 'regulært':
                title = f"[{status}] {base_title}"
            else:
                title = base_title

            meeting_url = f"{base_url.rstrip('/')}/{meeting_id}"
            meetings.append({
                'title': title[:100],
                'date': start_local.strftime('%Y-%m-%d'),
                'time': start_local.strftime('%H:%M'),
                'location': 'Ikke oppgitt',
                'kommune': kommune_name,
                'url': meeting_url,
                'raw_text': f"Status: {status or 'Ukjent'} | Internal: {value.get('internalStatus') or '-'}",
            })
            seen_ids.add(meeting_id)

        meetings.sort(key=lambda item: (item['date'], item.get('time') or ''))
        return meetings

    def _attach_elements_urls(self, meetings: List[Dict], base_url: str) -> None:
        """Sørg for at Elements Cloud-møter peker på detaljerte lenker."""
        for meeting in meetings:
            href = meeting.get('href')
            if href:
                meeting['url'] = urljoin(base_url, href)
            elif not meeting.get('url'):
                meeting['url'] = base_url

    def _extract_meetings_from_soup(self, soup: BeautifulSoup, kommune_name: str) -> List[Dict]:
        meetings = []

        # Først: nye innsyn-komponenter med bc-content-list
        bc_meetings = self._extract_bc_content_list_meetings(
            soup,
            kommune_name,
            base_url=self._current_base_url,
        )
        if bc_meetings:
            return bc_meetings

        # First: try to parse calendar-style tables where header cells are month names (Jan..Des)
        tables = soup.find_all('table')
        months_map = {
            'jan':1,'januar':1,'feb':2,'februar':2,'mar':3,'mars':3,'apr':4,'april':4,
            'mai':5,'jun':6,'juni':6,'jul':7,'juli':7,'aug':8,'august':8,'sep':9,'sept':9,'september':9,
            'okt':10,'oktober':10,'nov':11,'november':11,'des':12,'desember':12
        }

        for table in tables:
            first_row = table.find('tr')
            if not first_row:
                continue
            header_cells = first_row.find_all(['th', 'td'])
            header_texts = [hc.get_text(strip=True).lower() for hc in header_cells]
            if not any((h and h[:3] in months_map) for h in header_texts):
                continue

            # Map header column index -> month number
            month_indices = {}
            for idx, txt in enumerate(header_texts):
                key = txt.rstrip('.')[:3]
                if key in months_map:
                    month_indices[idx] = months_map[key]

            # DEBUG header
            # print(f"[DEBUG calendar headers] {header_texts}")

            # Iterate subsequent rows (skip header row)
            for row in table.find_all('tr')[1:]:
                cols = row.find_all(['td', 'th'])
                if not cols:
                    continue
                committee = cols[0].get_text(strip=True)
                if not committee:
                    continue

                for col_idx, month_num in month_indices.items():
                    if col_idx >= len(cols):
                        continue
                    cell = cols[col_idx]
                    # extract day numbers from anchors or plain text
                    days = []
                    a_tags = cell.find_all('a')
                    if a_tags:
                        for a in a_tags:
                            text = a.get_text(strip=True)
                            parts = re.findall(r'\d{1,2}', text)
                            days.extend(parts)
                    else:
                        txt = cell.get_text(' ', strip=True)
                        parts = re.findall(r'\d{1,2}', txt)
                        days.extend(parts)

                    for part in days:
                        try:
                            day = int(part)
                            dt = datetime(datetime.now().year, month_num, day)
                        except Exception:
                            continue
                        meetings.append({
                            'title': committee,
                            'date': dt.strftime('%Y-%m-%d'),
                            'time': None,
                            'location': 'Ikke oppgitt',
                            'kommune': kommune_name,
                            'raw_text': cell.get_text(strip=True)
                        })

        # If we found calendar meetings, dedupe, optionally filter for Eigersund, and return
        if meetings:
            unique = []
            seen = set()
            for m in meetings:
                key = (m['date'], m['title'], m.get('kommune') or kommune_name)
                if key not in seen:
                    seen.add(key)
                    unique.append(m)

            # If this is Eigersund, filter to today..today+10 days
            try:
                if 'eigersund' in (kommune_name or '').lower():
                    today = datetime.now().date()
                    end_date = today + timedelta(days=10)
                    filtered = []
                    for m in unique:
                        try:
                            md = datetime.strptime(m['date'], '%Y-%m-%d').date()
                            if today <= md <= end_date:
                                filtered.append(m)
                        except Exception:
                            continue
                    return filtered
            except Exception:
                pass

            return unique

        # Fallback: generic element scraping
        potential_elements = []
        potential_elements.extend(soup.find_all('tr'))
        potential_elements.extend(soup.find_all('div', class_=re.compile(r'.*møte.*|.*meeting.*|.*event.*', re.I)))
        potential_elements.extend(soup.find_all(['article', 'section']))
        potential_elements.extend(soup.find_all('li'))
        potential_elements.extend(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))

        for element in potential_elements:
            meeting = self._extract_meeting_from_element(element, kommune_name)
            if meeting:
                meetings.append(meeting)

        # dedupe
        unique = []
        seen = set()
        for m in meetings:
            key = (m['date'], m['title'], m.get('kommune') or kommune_name)
            if key not in seen:
                seen.add(key)
                unique.append(m)
        return unique

    def _parse_date_string(self, text: Optional[str]) -> Optional[datetime]:
        if not text:
            return None
        text = text.strip()
        if not text:
            return None

        # dd.mm.yyyy or dd.mm.yy
        m = re.search(r"(\d{1,2})[\./-](\d{1,2})[\./-](\d{2,4})", text)
        if m:
            day, month, year = m.groups()
            year_int = int(year)
            if year_int < 100:
                year_int += 2000
            try:
                return datetime(year_int, int(month), int(day))
            except Exception:
                return None

        # dd month yyyy (Norwegian)
        m2 = re.search(r"(\d{1,2})\.?\s+([A-Za-zæøåÆØÅ\.]{3,})\s+(\d{4})", text)
        if m2:
            day = int(m2.group(1))
            mon_str = m2.group(2).lower().rstrip('.')
            year = int(m2.group(3))
            months = {
                'jan': 1, 'januar': 1, 'feb': 2, 'februar': 2,
                'mar': 3, 'mars': 3, 'apr': 4, 'april': 4,
                'mai': 5, 'jun': 6, 'juni': 6, 'jul': 7, 'juli': 7,
                'aug': 8, 'august': 8, 'sep': 9, 'sept': 9, 'september': 9,
                'okt': 10, 'oktober': 10, 'nov': 11, 'november': 11,
                'des': 12, 'desember': 12,
            }
            month = months.get(mon_str[:3]) or months.get(mon_str)
            if month:
                try:
                    return datetime(year, month, day)
                except Exception:
                    return None
        return None

    def _extract_time_from_text(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        match = re.search(r"(\d{1,2}):(\d{2})", text)
        if match:
            return self._normalize_time_str(*match.groups())
        match = re.search(r"(?:kl\.?\s*)(\d{1,2})(?:[\.:](\d{2}))?", text, re.IGNORECASE)
        if match:
            hour = match.group(1)
            minute = match.group(2) or "00"
            return self._normalize_time_str(hour, minute)
        return None

    def _extract_bc_content_list_meetings(
        self,
        soup: BeautifulSoup,
        kommune_name: str,
        base_url: Optional[str] = None,
    ) -> List[Dict]:
        items = soup.select('.bc-content-list-item')
        if not items:
            return []

        resolved_base = (base_url or self._current_base_url or '').strip()

        meetings: List[Dict] = []
        for item in items:
            anchor_el = item.select_one('.bc-content-teaser-title a')
            title_container = item.select_one('.bc-content-teaser-title')
            title_source = anchor_el or title_container
            if not title_source:
                continue
            title_text = title_source.get_text(' ', strip=True)
            if not title_text:
                continue

            date_container = (
                item.select_one('div._meetingDate_mqsmx_38')
                or item.select_one('div.MoteListItem_meetingDate__780f64')
                or item.select_one('div[class*="meetingDate"]:not([class*="meetingDateDay"])')
            )
            candidate_date_text = date_container.get_text(' ', strip=True) if date_container else ''

            if candidate_date_text and '-' in candidate_date_text:
                candidate_date_text = candidate_date_text.split('-')[0].strip()

            # Reconstruct day/month/year when split into separate divs
            if date_container:
                day_el = (
                    date_container.select_one('._meetingDateDay_mqsmx_50')
                    or date_container.select_one('[class*="meetingDateDay"]')
                )
                month_text = None
                year_text = None
                day_text = day_el.get_text(strip=True).strip('. ') if day_el else None
                for div in date_container.find_all(['div', 'span']):
                    text = div.get_text(' ', strip=True)
                    classes = div.get('class') or []
                    if not text:
                        continue
                    if day_el is not None and div is day_el:
                        continue
                    if day_text and text.strip('. ') == day_text:
                        continue
                    if 'innsyn-header-hidden' in classes:
                        year_text = text
                    elif text != '-' and not month_text:
                        month_text = text
                if day_text:
                    parts = [part for part in (day_text, month_text, year_text) if part]
                    if parts:
                        candidate_date_text = ' '.join(parts)

            if not candidate_date_text:
                aria_label = anchor_el.get('aria-label') if anchor_el else None
                candidate_date_text = aria_label or item.get_text(' ', strip=True)

            meeting_date = self._parse_date_string(candidate_date_text)
            if not meeting_date:
                continue

            meta_map: Dict[str, str] = {}
            for meta in item.select('.bc-content-teaser-meta-property'):
                label = meta.select_one('.bc-content-teaser-meta-property-label')
                value = meta.select_one('.bc-content-teaser-meta-property-value')
                if label and value:
                    key = label.get_text(strip=True).lower()
                    meta_map[key] = value.get_text(' ', strip=True)

            meeting_time = None
            for time_key in ('tid', 'tidspunkt', 'klokkeslett'):
                if time_key in meta_map:
                    meeting_time = self._extract_time_from_text(meta_map[time_key])
                    if meeting_time:
                        break
            if not meeting_time and anchor_el and anchor_el.has_attr('aria-label'):
                meeting_time = self._extract_time_from_text(anchor_el['aria-label'])

            location = None
            for loc_key in ('stad', 'stad:', 'stad/sted', 'sted'):
                if loc_key in meta_map and meta_map[loc_key].strip():
                    location = meta_map[loc_key]
                    break
            if location:
                location = location.strip()

            meeting = {
                'title': title_text[:100],
                'date': meeting_date.strftime('%Y-%m-%d'),
                'time': meeting_time,
                'location': (location or 'Ikke oppgitt')[:50],
                'kommune': kommune_name,
                'raw_text': item.get_text(' ', strip=True)[:300],
            }

            if anchor_el and anchor_el.has_attr('href'):
                href = anchor_el['href']
                try:
                    meeting['url'] = urljoin(resolved_base, href)
                except Exception:
                    meeting['url'] = href
            elif resolved_base:
                meeting['url'] = resolved_base
            else:
                meeting['url'] = ''

            meetings.append(meeting)  # type: ignore[list-item]

        unique: List[Dict] = []
        seen = set()
        for meeting in meetings:
            key = (meeting['date'], meeting['title'])
            if key in seen:
                continue
            seen.add(key)
            unique.append(meeting)  # type: ignore[arg-type]

        return unique

    def _extract_elements_meetings(self, soup: BeautifulSoup, kommune_name: Optional[str] = None) -> List[Dict]:
        meetings: List[Dict] = []
        kommune_label = kommune_name or 'Rogaland fylkeskommune'

        bc_meetings = self._extract_bc_content_list_meetings(
            soup,
            kommune_label,
            base_url=self._current_base_url or None,
        )
        if bc_meetings:
            return bc_meetings

        def _parse_date_string(s: str) -> Optional[str]:
            if not s:
                return None
            s = s.strip()
            # mm/dd/yyyy
            m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', s)
            if m:
                mo, d, y = m.groups()
                try:
                    dt = datetime(int(y), int(mo), int(d))
                    return dt.strftime('%Y-%m-%d')
                except Exception:
                    pass
            # dd.mm.yyyy or dd-mm-yyyy
            m2 = re.search(r'(\d{1,2})[\.\-](\d{1,2})[\.\-](\d{4})', s)
            if m2:
                d, mo, y = m2.groups()
                try:
                    dt = datetime(int(y), int(mo), int(d))
                    return dt.strftime('%Y-%m-%d')
                except Exception:
                    pass
            # dd month yyyy
            m3 = re.search(r'(\d{1,2})\.?\s+([A-Za-zæøåÆØÅ\.]{3,})\s+(\d{4})', s)
            if m3:
                day = int(m3.group(1))
                mon_str = m3.group(2).lower().rstrip('.')
                year = int(m3.group(3))
                months = {'jan':1,'januar':1,'feb':2,'februar':2,'mar':3,'mars':3,'apr':4,'april':4,'mai':5,'jun':6,'juni':6,'jul':7,'juli':7,'aug':8,'august':8,'sep':9,'sept':9,'september':9,'okt':10,'oktober':10,'nov':11,'november':11,'des':12,'desember':12}
                mon = months.get(mon_str[:3]) or months.get(mon_str)
                if mon:
                    try:
                        dt = datetime(year, mon, day)
                        return dt.strftime('%Y-%m-%d')
                    except Exception:
                        pass
            # ISO 8601 (e.g. 2025-08-21T10:00:00 or 2025-08-21 10:00)
            try:
                iso = re.search(r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}', s)
                if iso:
                    iso_s = iso.group(0).replace(' ', 'T')
                    try:
                        dt = datetime.fromisoformat(iso_s)
                        return dt.strftime('%Y-%m-%d')
                    except Exception:
                        pass
            except Exception:
                pass

            # Epoch seconds or milliseconds
            digits = re.search(r'\b(\d{10,13})\b', s)
            if digits:
                try:
                    val = int(digits.group(1))
                    if len(digits.group(1)) >= 13:
                        ts = val / 1000.0
                    else:
                        ts = val
                    dt = datetime.fromtimestamp(ts)
                    return dt.strftime('%Y-%m-%d')
                except Exception:
                    pass
            return None

        # tables
        tables = soup.find_all('table')
        # First: detect calendar-style tables where header cells are month names (Jan..Des)
        months_map = {
            'jan':1,'januar':1,'feb':2,'februar':2,'mar':3,'mars':3,'apr':4,'april':4,
            'mai':5,'jun':6,'juni':6,'jul':7,'juli':7,'aug':8,'august':8,'sep':9,'sept':9,'september':9,
            'okt':10,'oktober':10,'nov':11,'november':11,'des':12,'desember':12
        }
        for table in tables:
            # Use first row as header (handles th or td)
            first_row = table.find('tr')
            if not first_row:
                continue
            header_cells = first_row.find_all(['th', 'td'])
            header_texts = [hc.get_text(strip=True).lower() for hc in header_cells]
            if not any((h and h[:3] in months_map) for h in header_texts):
                continue

            # Map header column index -> month number
            month_indices = {}
            for idx, txt in enumerate(header_texts):
                key = txt.rstrip('.')[:3]
                if key in months_map:
                    month_indices[idx] = months_map[key]

            # DEBUG: show detected headers
            print(f"[DEBUG Playwright calendar headers] {header_texts}")

            # Iterate subsequent rows (skip header row)
            for row in table.find_all('tr')[1:]:
                cols = row.find_all(['td', 'th'])
                if not cols:
                    continue
                committee = cols[0].get_text(strip=True)
                if not committee:
                    continue

                for col_idx, month_num in month_indices.items():
                    if col_idx >= len(cols):
                        continue
                    cell = cols[col_idx]
                    # DEBUG: print cell for the specific committee we're checking
                    if 'råd for personer' in committee.lower():
                        print(f"[DEBUG Playwright row] committee={committee} col_idx={col_idx} month={month_num} cell='{cell.get_text(strip=True)}'")
                    # extract day numbers from anchors or plain text
                    days = []
                    a_tags = cell.find_all('a')
                    if a_tags:
                        for a in a_tags:
                            text = a.get_text(strip=True)
                            parts = re.findall(r'\d{1,2}', text)
                            days.extend(parts)
                    else:
                        txt = cell.get_text(' ', strip=True)
                        parts = re.findall(r'\d{1,2}', txt)
                        days.extend(parts)

                    for part in days:
                        try:
                            day = int(part)
                            dt = datetime(datetime.now().year, month_num, day)
                        except Exception:
                            continue
                        meetings.append({
                            'title': committee,
                            'date': dt.strftime('%Y-%m-%d'),
                            'time': None,
                            'location': 'Ikke oppgitt',
                            'kommune': kommune_label,
                            'raw_text': cell.get_text(strip=True)
                        })

        # Non-calendar table fallback
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                row_text = ' '.join([c.get_text(strip=True) for c in cells])
                if len(row_text) > 15 and re.search(r'\d{1,2}[\./-]\d{1,2}[\./-]202[4-6]', row_text):
                    meeting = self._extract_meeting_from_element(row, kommune_label)
                    if meeting and len(meeting['title']) > 3:
                        meetings.append(meeting)

        # links
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if 'DmbMeeting' in href or re.search(r'utvalg|dmb|meeting', href, re.I) or re.search(r'utvalg|møte|meeting|utvalgsmøte', text, re.I):
                title_attr = link.get('title') or ''
                aria_attr = link.get('aria-label') or ''
                data_date = link.get('data-date') or ''
                data_start = link.get('data-start') or ''
                parent = link.parent
                parent_title = ''
                parent_aria = ''
                if parent:
                    parent_title = parent.get('title') or ''
                    parent_aria = parent.get('aria-label') or ''
                ancestor = link.find_parent()
                ancestor_attrs: List[str] = []
                for _ in range(3):
                    if not ancestor:
                        break
                    ancestor_attrs.append(ancestor.get('title') or '')
                    ancestor_attrs.append(ancestor.get('aria-label') or '')
                    ancestor = ancestor.parent

                candidate_blob = ' '.join([title_attr, aria_attr, data_date, data_start, parent_title, parent_aria] + ancestor_attrs + [text])
                date_iso = _parse_date_string(candidate_blob)
                # try data-date first if present
                if not date_iso and data_date:
                    date_iso = _parse_date_string(data_date)

                meeting_date_str = date_iso or 'TBD'
                meeting_time = None

                # If data-start looks like epoch or ISO, prefer it for date+time
                if data_start:
                    ds = data_start.strip()
                    # ISO
                    iso_match = re.search(r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}(:\d{2})?)', ds)
                    if iso_match:
                        try:
                            iso_s = iso_match.group(1).replace(' ', 'T')
                            dt_ds = datetime.fromisoformat(iso_s)
                            meeting_date_str = dt_ds.strftime('%Y-%m-%d')
                            meeting_time = dt_ds.strftime('%H:%M')
                        except Exception:
                            pass
                    else:
                        # epoch
                        dig = re.search(r'\b(\d{10,13})\b', ds)
                        if dig:
                            try:
                                val = int(dig.group(1))
                                ts = val / 1000.0 if len(dig.group(1)) >= 13 else val
                                dt_ds = datetime.fromtimestamp(ts)
                                meeting_date_str = dt_ds.strftime('%Y-%m-%d')
                                meeting_time = dt_ds.strftime('%H:%M')
                            except Exception:
                                pass

                # Fallback: parse time from candidate blob (prefer colon, validate hour)
                if not meeting_time:
                    tm = re.search(r'(\d{1,2}):(\d{2})', candidate_blob)
                    if not tm:
                        tm = re.search(r'(?:kl\.?\s*)(\d{1,2})[.](\d{2})', candidate_blob)
                    if tm:
                        hh, mm = tm.groups()
                        meeting_time = self._normalize_time_str(hh, mm)

                meeting = {
                    'title': text.strip()[:100] or 'Politisk møte',
                    'date': meeting_date_str,
                    'time': meeting_time or 'TBD',
                    'location': 'Ikke oppgitt',
                    'kommune': kommune_label,
                    'href': href
                }
                meetings.append(meeting)

        # other containers
        containers = []
        containers.extend(soup.find_all('div', class_=re.compile(r'.*møte.*|.*meeting.*|.*calendar.*|.*event.*', re.I)))
        containers.extend(soup.find_all('li', class_=re.compile(r'.*møte.*|.*meeting.*|.*item.*', re.I)))
        containers.extend(soup.find_all('article'))
        for c in containers:
            text = c.get_text(strip=True)
            if (len(text) > 20 and
                re.search(r'\d{1,2}[\./-]\d{1,2}[\./-]202[4-6]', text) and
                re.search(r'(møte|meeting|utvalg|styre|råd|nemnd|formannskap|kommunestyre)', text, re.I)):
                meeting = self._extract_meeting_from_element(c, kommune_label)
                if meeting and len(meeting['title']) > 3:
                    meetings.append(meeting)

        # dedupe and filter
        good = []
        seen = set()
        for m in meetings:
            title = m['title']
            if (len(title) < 200 and not re.match(r'^[0-9\s\+\-]+$', title)):
                key = (m['date'], title)
                if key not in seen:
                    seen.add(key)
                    good.append(m)

        return good

    def _extract_meeting_from_element(self, element, kommune_name: str) -> Optional[Dict]:
        try:
            text = element.get_text(strip=True)
            candidate_texts = [text]
            try:
                aria = element.get('aria-label')
                title_attr = element.get('title')
            except Exception:
                aria = None; title_attr = None
            if aria:
                candidate_texts.insert(0, aria)
            if title_attr:
                candidate_texts.insert(0, title_attr)
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

            combined = ' '.join([c for c in candidate_texts if c])
            if len(combined) < 8:
                return None

            meeting_date = None
            for cand in candidate_texts:
                if not cand:
                    continue
                m = re.search(r'(\d{1,2})[\.\-/](\d{1,2})[\.\-/](\d{2,4})', cand)
                if m:
                    d, mo, y = m.groups()
                    y = int(y)
                    if y < 100:
                        y += 2000
                    try:
                        meeting_date = datetime(y, int(mo), int(d))
                        break
                    except Exception:
                        meeting_date = None
                else:
                    m2 = re.search(r'(\d{1,2})\.?\s+([A-Za-zæøåÆØÅ\.]{3,})\s+(\d{4})', cand)
                    if m2:
                        day = int(m2.group(1))
                        mon_str = m2.group(2).lower().rstrip('.')
                        year = int(m2.group(3))
                        months = {'jan':1,'januar':1,'feb':2,'februar':2,'mar':3,'mars':3,'apr':4,'april':4,'mai':5,'jun':6,'juni':6,'jul':7,'juli':7,'aug':8,'august':8,'sep':9,'sept':9,'september':9,'okt':10,'oktober':10,'nov':11,'november':11,'des':12,'desember':12}
                        mon = months.get(mon_str[:3]) or months.get(mon_str)
                        if mon:
                            try:
                                meeting_date = datetime(year, mon, day)
                                break
                            except Exception:
                                meeting_date = None

            if not meeting_date:
                return None

            meeting_time = None
            for cand in candidate_texts:
                if not cand:
                    continue
                tm = re.search(r'(\d{1,2}):(\d{2})', cand)
                if not tm:
                    tm = re.search(r'(?:kl\.?\s*)(\d{1,2})[.](\d{2})', cand)
                if tm:
                    hh, mm = tm.groups()
                    meeting_time = self._normalize_time_str(hh, mm)
                    if meeting_time:
                        break

            title = ''
            if element.name in ['h1','h2','h3','h4','h5','h6']:
                title = element.get_text(strip=True)
            else:
                title_el = element.find(['h1','h2','h3','h4','h5','h6','strong','b'])
                if title_el:
                    title = title_el.get_text(strip=True)
                else:
                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if len(line) > 3 and not re.search(r'\d{1,2}\.\d{1,2}\.\d{4}', line):
                            title = line
                            break

            if title:
                title = re.sub(r'\d{1,2}\.\d{1,2}\.\d{4}.*','', title).strip()
                title = re.sub(r'kl\.?\s*\d{1,2}:\d{2}.*','', title).strip()
                title = re.sub(r'\s+',' ', title).strip()

            # blacklist common UI text
            lowt = (title or '').lower()
            for bp in [r'søk etter møte', r'resultatside med møter', r'søk etter møter', r'resultatside', r'møtekalender', r'vis flere']:
                if re.search(bp, lowt):
                    return None

            location = 'Ikke oppgitt'
            loc_words = re.findall(r'\b(?:kommunestyresalen|formannskapssalen|rådhuset|møterom|kommunehuset|fylkeshuset)\b', text, re.I)
            if loc_words:
                location = loc_words[0].title()

            return {
                'title': (title or 'Politisk møte')[:100],
                'date': meeting_date.strftime('%Y-%m-%d'),
                'time': meeting_time,
                'location': location[:50],
                'kommune': kommune_name,
                'raw_text': text[:300]
            }
        except Exception as e:
            print(f"Feil ved ekstraksjon: {e}")
            return None


async def scrape_with_playwright(kommune_urls: List[Dict]) -> List[Dict]:
    all_meetings: List[Dict] = []
    async with PlaywrightMoteParser() as parser:
        for cfg in kommune_urls:
            name = cfg.get('name')
            url = cfg.get('url')
            t = cfg.get('type')
            try:
                # Special-case: if this config is for Eigersund, prefer the dedicated parser
                # which parses the meeting plan table reliably via requests/BeautifulSoup.
                if name and 'eigersund' in name.lower():
                    try:
                        from .eigersund_parser import parse_eigersund_meetings
                        meetings = parse_eigersund_meetings(url, name, days_ahead=10)
                        all_meetings.extend(meetings)
                        print(f"\u2705 {name}: {len(meetings)} m\u00f8ter (via eigersund_parser)")
                        continue
                    except Exception:
                        # fallback to Playwright parsing if dedicated parser fails
                        pass

                if url and 'digdem' in url:
                    meetings = await parser.scrape_digdem_site(url, name or url)
                elif t == 'elements':
                    meetings = await parser.scrape_elements_cloud(url, name)
                elif t == 'onacos':
                    meetings = await parser.scrape_onacos_site(url, name)
                else:
                    meetings = await parser.scrape_javascript_site(url, name)

                # If this config is for Eigersund, filter meetings to today..today+10 days
                try:
                    if name and 'eigersund' in name.lower():
                        today = datetime.now().date()
                        end_date = today + timedelta(days=10)
                        filt = []
                        for m in meetings:
                            try:
                                md = date.fromisoformat(m['date'])
                                if today <= md <= end_date:
                                    filt.append(m)
                            except Exception:
                                continue
                        meetings = filt
                except Exception:
                    pass

                all_meetings.extend(meetings)
                print(f"✅ {name}: {len(meetings)} møter")
            except Exception as e:
                print(f"❌ {name}: {e}")
                continue
    return all_meetings


def main():
    test_urls = [
        {"name": "Elements Cloud Test", "url": "https://prod01.elementscloud.no/publikum/971045698/Dmb", "type": "elements"},
        {"name": "Sirdal Onacos Test", "url": "https://innsynpluss.onacos.no/sirdal/moteoversikt/", "type": "onacos"}
    ]
    print("🎭 Tester Playwright-scraper...")
    meetings = asyncio.run(scrape_with_playwright(test_urls))
    print(f"\n✅ Totalt funnet: {len(meetings)} møter")
    for m in meetings:
        print(f"  - {m['date']} {m['time']} | {m['title']} ({m['kommune']})")


if __name__ == '__main__':
    main()
