#!/usr/bin/env python3
"""Ad-hoc inspector for municipality meeting API endpoints."""

from __future__ import annotations

import json
import re
from typing import Iterable

import requests
from bs4 import BeautifulSoup


DEFAULT_ENDPOINTS = (
    "https://www.sauda.kommune.no/api/meetings",
    "https://www.sauda.kommune.no/api/moter",
    "https://www.strand.kommune.no/api/meetings",
    "https://www.hjelmeland.kommune.no/api/meetings",
)


def inspect_endpoint(url: str) -> None:
    """Fetch and print a small diagnostic summary for a single endpoint."""
    print(f"\n🔍 Testing {url}")

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json, text/html, */*",
        }
    )

    response = session.get(url, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
    print(f"Content-Length: {len(response.content)}")

    content_type = response.headers.get("content-type", "").lower()
    if "json" in content_type:
        try:
            data = response.json()
        except json.JSONDecodeError:
            print("Ikke gyldig JSON")
        else:
            print(f"JSON data type: {type(data)}")
            if isinstance(data, dict):
                print(f"JSON keys: {list(data.keys())}")
            elif isinstance(data, list):
                print(f"JSON array length: {len(data)}")
                if data:
                    first = data[0]
                    print(
                        f"First item keys: {list(first.keys()) if isinstance(first, dict) else 'Not a dict'}"
                    )
    else:
        soup = BeautifulSoup(response.content, "html.parser")
        text = soup.get_text()

        meeting_words = ["møte", "formannskap", "kommunestyre", "utvalg", "råd"]
        found_words = [word for word in meeting_words if word.lower() in text.lower()]
        if found_words:
            print(f"Møte-relaterte ord funnet: {found_words}")
            dates = re.findall(r"\\d{1,2}\\.\\d{1,2}\\.202[45]", text)
            if dates:
                print(f"Datoer funnet: {dates[:5]}")
        else:
            print("Ingen møte-relaterte ord funnet")

    print("Preview (500 tegn):")
    print(response.text[:500])


def main(endpoints: Iterable[str] = DEFAULT_ENDPOINTS) -> None:
    for endpoint in endpoints:
        try:
            inspect_endpoint(endpoint)
        except Exception as exc:
            print(f"Feil: {exc}")
        print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
