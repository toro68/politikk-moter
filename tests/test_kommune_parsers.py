"""Fixture-driven parser tests for every kommune configuration."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

import pytest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))

from politikk_moter import eigersund_parser  # noqa: E402  # pylint: disable=wrong-import-position,import-error
from politikk_moter.kommuner import KOMMUNE_CONFIGS  # noqa: E402  # pylint: disable=wrong-import-position,import-error
from politikk_moter.playwright_scraper import PlaywrightMoteParser  # noqa: E402  # pylint: disable=wrong-import-position,import-error
from politikk_moter.scraper import MoteParser  # noqa: E402  # pylint: disable=wrong-import-position,import-error

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "kommune_html"


@dataclass
class DummyResponse:
    html: str

    @property
    def text(self) -> str:
        return self.html

    @property
    def content(self) -> bytes:
        return self.html.encode("utf-8")

    def raise_for_status(self) -> None:  # pragma: no cover - HTTP errors mocked away
        return None


def load_fixture(name: str) -> str:
    target = FIXTURE_DIR / name
    return target.read_text(encoding="utf-8")


ACOS_KOMMUNER = [cfg.name for cfg in KOMMUNE_CONFIGS if cfg.type == "acos"]
CUSTOM_KOMMUNER = [cfg.name for cfg in KOMMUNE_CONFIGS if cfg.type == "custom" and "klepp" not in cfg.name.lower()]
KLEPP_KOMMUNE = next(cfg.name for cfg in KOMMUNE_CONFIGS if "klepp" in cfg.name.lower())
ONACOS_KOMMUNER = [
    cfg.name for cfg in KOMMUNE_CONFIGS if cfg.type == "onacos" and "eigersund" not in cfg.name.lower()
]
EIGERSUND_NAME = next(cfg.name for cfg in KOMMUNE_CONFIGS if "eigersund" in cfg.name.lower())
ELEMENTS_NAME = next(cfg.name for cfg in KOMMUNE_CONFIGS if cfg.type == "elements")


@pytest.mark.parametrize("kommune_name", ACOS_KOMMUNER)
def test_acos_parser_handles_all_kommuner(monkeypatch: pytest.MonkeyPatch, kommune_name: str) -> None:
    parser = MoteParser()
    html = load_fixture("acos_sample.html")

    def fake_get(*_args, **_kwargs) -> DummyResponse:
        return DummyResponse(html)

    monkeypatch.setattr(parser.session, "get", fake_get)

    meetings = parser.parse_acos_site("https://example.com", kommune_name)
    assert meetings, f"Expected at least one meeting for {kommune_name}"
    assert all(m["kommune"] == kommune_name for m in meetings)


@pytest.mark.parametrize("kommune_name", CUSTOM_KOMMUNER)
def test_custom_parser_handles_all_kommuner(monkeypatch: pytest.MonkeyPatch, kommune_name: str) -> None:
    parser = MoteParser()
    html = load_fixture("custom_sample.html")

    def fake_get(*_args, **_kwargs) -> DummyResponse:
        return DummyResponse(html)

    monkeypatch.setattr(parser.session, "get", fake_get)

    meetings = parser.parse_custom_site("https://example.com", kommune_name)
    assert meetings, f"Custom parser should find meetings for {kommune_name}"
    assert {m["title"] for m in meetings} == {"Utvalg for kultur"}


def test_klepp_parser_uses_special_markup(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = MoteParser()
    html = load_fixture("klepp_sample.html")

    def fake_get(*_args, **_kwargs) -> DummyResponse:
        return DummyResponse(html)

    monkeypatch.setattr(parser.session, "get", fake_get)

    meetings = parser.parse_custom_site("https://opengov.360online.com/Meetings/KLEPP", KLEPP_KOMMUNE)
    assert meetings, "Klepp parser should extract meetings from 360online markup"
    assert meetings[0]["title"].startswith("Klepp kommunestyre")
    assert meetings[0]["date"].startswith("2025-")


def test_opengov_parser_handles_sandnes(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = MoteParser()
    html = load_fixture("sandnes_sample.html")

    def fake_get(*_args, **_kwargs) -> DummyResponse:
        return DummyResponse(html)

    monkeypatch.setattr(parser.session, "get", fake_get)

    meetings = parser.parse_custom_site(
        "https://opengov.360online.com/Meetings/SANDNESKOMMUNE",
        "Sandnes kommune",
    )

    assert len(meetings) == 2
    assert meetings[0]["title"].startswith("Formannskapet")
    assert meetings[0]["time"] == "12:00"
    assert all(m["kommune"] == "Sandnes kommune" for m in meetings)


def test_opengov_parser_handles_randaberg(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = MoteParser()
    html = load_fixture("randaberg_sample.html")

    def fake_get(*_args, **_kwargs) -> DummyResponse:
        return DummyResponse(html)

    monkeypatch.setattr(parser.session, "get", fake_get)

    meetings = parser.parse_custom_site(
        "https://opengov.360online.com/Meetings/randaberg",
        "Randaberg kommune",
    )

    assert len(meetings) == 2
    assert meetings[0]["title"].startswith("Hovedutvalg for nærmiljø")
    assert meetings[0]["time"] == "18:00"
    assert all(m["kommune"] == "Randaberg kommune" for m in meetings)


@pytest.mark.parametrize("kommune_name", ONACOS_KOMMUNER)
def test_onacos_parser_handles_all_kommuner(monkeypatch: pytest.MonkeyPatch, kommune_name: str) -> None:
    parser = MoteParser()
    html = load_fixture("onacos_sample.html")

    def fake_get(*_args, **_kwargs) -> DummyResponse:
        return DummyResponse(html)

    monkeypatch.setattr(parser.session, "get", fake_get)

    meetings = parser.parse_onacos_site("https://innsynpluss.onacos.no", kommune_name)
    assert meetings, f"Onacos parser should return meetings for {kommune_name}"
    assert all(m["kommune"] == kommune_name for m in meetings)


def test_eigersund_parser_reads_table_and_details(monkeypatch: pytest.MonkeyPatch) -> None:
    table_html = load_fixture("eigersund_table.html")
    detail_html = load_fixture("eigersund_detail.html")

    def fake_get(*_args, **_kwargs) -> DummyResponse:
        return DummyResponse(table_html)

    class FakeSession:
        def __init__(self, html_text: str):
            self.html_text = html_text
            self.requested_urls: List[str] = []

        def get(self, url: str, *_args, **_kwargs) -> DummyResponse:
            self.requested_urls.append(url)
            return DummyResponse(self.html_text)

    fake_session = FakeSession(detail_html)

    monkeypatch.setattr(eigersund_parser.requests, "get", fake_get)
    monkeypatch.setattr(eigersund_parser.requests, "Session", lambda: fake_session)
    monkeypatch.setattr(eigersund_parser, "_DETAILS_CACHE", {})

    target_year = datetime.now().year + 1
    meetings = eigersund_parser.parse_eigersund_meetings(
        "https://innsyn.onacos.no/eigersund/mote/",
        EIGERSUND_NAME,
        year=target_year,
        days_ahead=4000,
    )
    assert meetings, "Eigersund parser should return meetings from the fixture"
    assert fake_session.requested_urls, "Detail pages should be fetched"
    assert meetings[0]["time"] == "10:00"
    assert meetings[0]["kommune"] == EIGERSUND_NAME
    assert meetings[0]["date"].startswith(str(target_year))


def test_elements_parser_extracts_bc_cards() -> None:
    parser = PlaywrightMoteParser()
    html = load_fixture("elements_sample.html")
    soup = BeautifulSoup(html, "html.parser")

    meetings = parser._extract_elements_meetings(soup, ELEMENTS_NAME)  # noqa: SLF001  # pylint: disable=protected-access
    assert meetings, "Elements parser should find meetings from bc-content cards"
    assert meetings[0]["title"] == "Fylkesting"
    assert meetings[0]["kommune"] == ELEMENTS_NAME
    assert meetings[0]["date"].startswith("2025-")
