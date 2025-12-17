#!/usr/bin/env python3
"""
Regresjonstest for Strand sin politiske møtekalender.
"""

from bs4 import BeautifulSoup
from pathlib import Path

from politikk_moter.scraper import _requires_playwright_for_config


def test_strand_motekalender_fixture_is_js_shell():
    html = Path("tests/fixtures/kommune_html/strand_sample.html").read_text(errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    assert soup.title and "Politisk møtekalender" in soup.title.get_text()
    assert soup.select_one(".innsyn-overview") is not None


def test_strand_config_requires_playwright():
    config = {
        "name": "Strand kommune",
        "url": "https://www.strand.kommune.no/tjenester/politikk-innsyn-og-medvirkning/politiske-moter-og-sakspapirer/politisk-motekalender/",
        "type": "acos",
    }
    assert _requires_playwright_for_config(config) is True

if __name__ == '__main__':
    raise SystemExit("Run via pytest")
