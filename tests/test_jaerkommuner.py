#!/usr/bin/env python3
"""
Enkle nettverkstester for Jæren-kommunene. Testene verifiserer at
møte-/saksportaler svarer og at responsen inneholder sannsynlige
møteindikatorer (datoer eller kjente møteord).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List, Sequence

import pytest
import requests
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class KommuneCase:
    """Testkonfigurasjon for en kommune."""

    kommune: str
    url: str
    expected_keywords: Sequence[str]


TEST_CASES: Sequence[KommuneCase] = (
    KommuneCase(
        kommune="Time kommune",
        url="https://www.time.kommune.no/politikk/mote-og-saksdokument/moter-og-saksdokument/",
        expected_keywords=("møte", "saksliste", "politikk", "kommunestyre", "formannskap"),
    ),
    KommuneCase(
        kommune="Klepp kommune",
        url="https://opengov.360online.com/Meetings/KLEPP",
        expected_keywords=("meeting", "møte", "agenda", "saksliste", "utvalg"),
    ),
    KommuneCase(
        kommune="Hå kommune",
        url="https://www.ha.no/politikk-og-samfunnsutvikling/mote-og-sakspapir/",
        expected_keywords=("møte", "saksliste", "politikk", "kommunestyre", "utvalg"),
    ),
    KommuneCase(
        kommune="Sola kommune",
        url="https://nyttinnsyn.sola.kommune.no/wfinnsyn.ashx?response=moteplan&",
        expected_keywords=("møte", "utvalg", "møteplan", "saksliste"),
    ),
)


def _find_dates(text: str) -> List[str]:
    """Returner datoer i norsk eller ISO-format fra en tekst."""
    patterns = (r"\d{1,2}\.\d{1,2}\.\d{2,4}", r"\d{4}-\d{2}-\d{2}")
    hits: List[str] = []
    for pattern in patterns:
        hits.extend(re.findall(pattern, text))
    return hits


@pytest.mark.parametrize("case", TEST_CASES, ids=lambda c: c.kommune)
def test_jaerkommune_meeting_pages_expose_data(case: KommuneCase) -> None:
    """Sjekk at vi får sensibel møteinformasjon fra kommunenettstedet."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        }
    )

    response = session.get(case.url, timeout=20)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    is_json = "json" in content_type

    if is_json:
        try:
            payload = response.json()
            text_blob = json.dumps(payload, ensure_ascii=False)
        except json.JSONDecodeError as exc:  # pragma: no cover
            pytest.fail(f"{case.kommune}: klarte ikke å parse JSON ({exc})")
        keyword_hits = [kw for kw in case.expected_keywords if kw.lower() in text_blob.lower()]
        date_hits = _find_dates(text_blob)
        preview = text_blob[:500]
    else:
        text_blob = response.text
        soup = BeautifulSoup(response.content, "html.parser")
        keyword_hits = [kw for kw in case.expected_keywords if kw.lower() in text_blob.lower()]
        date_hits = _find_dates(text_blob)

        if not keyword_hits and not date_hits:
            candidate_elements = soup.find_all(["article", "li", "tr", "td"], limit=40)
            for element in candidate_elements:
                snippet = element.get_text(" ", strip=True)
                if not snippet:
                    continue
                lowered = snippet.lower()
                if any(kw in lowered for kw in case.expected_keywords):
                    keyword_hits.append(snippet)
                date_hits.extend(_find_dates(snippet))
        preview = soup.get_text(" ", strip=True)[:500]

    print(f"\n--- {case.kommune} ({case.url}) ---")
    print(f"Content-Type: {content_type or 'ukjent'}")
    print(f"Keyword-hits: {keyword_hits[:5]}")
    print(f"Date-hits: {date_hits[:5]}")
    print(f"Preview: {preview[:500]}")
    print("--- slutt ---\n")

    assert keyword_hits or date_hits, (
        f"{case.kommune}: fant verken møtenøkkelord {case.expected_keywords} eller datoer i responsen."
    )
