#!/usr/bin/env python3
"""Regresjonstest for Hjelmeland sin innsyn-møteplan."""

from pathlib import Path

from bs4 import BeautifulSoup

from politikk_moter.scraper import _requires_playwright_for_config


def test_hjelmeland_moteplan_fixture_is_js_shell() -> None:
    html = Path("tests/fixtures/kommune_html/hjelmeland_sample.html").read_text(errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    assert soup.select_one(".innsyn-overview") is not None


def test_hjelmeland_config_requires_playwright() -> None:
    config = {
        "name": "Hjelmeland kommune",
        "url": "https://www.hjelmeland.kommune.no/politikk/moteplan-og-sakspapir/innsyn-moteplan/",
        "type": "acos",
    }
    assert _requires_playwright_for_config(config) is True


if __name__ == "__main__":
    raise SystemExit("Run via pytest")
