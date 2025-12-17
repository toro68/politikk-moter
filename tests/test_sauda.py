from pathlib import Path

from bs4 import BeautifulSoup

from politikk_moter.scraper import _requires_playwright_for_config


def test_sauda_innsyn_fixture_is_js_shell():
    html = Path("tests/fixtures/kommune_html/sauda_sample.html").read_text(errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    assert soup.title and "Politiske møter" in soup.title.get_text()
    assert soup.select_one(".innsyn-overview") is not None


def test_sauda_config_requires_playwright():
    config = {
        "name": "Sauda kommune",
        "url": "https://www.sauda.kommune.no/innsyn/politiske-moter/",
        "type": "acos",
    }
    assert _requires_playwright_for_config(config) is True

