#!/usr/bin/env python3
"""Tests that known meeting snippets produce structured output."""

import re
from dataclasses import dataclass
from typing import List

from politikk_moter.scraper import MoteParser


@dataclass
class MockElement:
    """Minimal HTML-lignende element som gir parseren nødvendig tekst."""

    text: str

    def get_text(self, strip: bool = True) -> str:  # noqa: D401
        return self.text.strip() if strip else self.text

    def find(self, *_args, **_kwargs):  # pragma: no cover - ikke brukt i testen
        return None

    def find_all(self, *_args, **_kwargs):  # pragma: no cover - ikke brukt i testen
        return []

    @property
    def name(self) -> str:  # noqa: D401
        return "div"


def _extract_from_lines(parser: MoteParser, kommune: str, lines: List[str]) -> List[dict]:
    meetings: List[dict] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if not re.search(r"\d{1,2}\.\d{1,2}\.202[45]", line):
            continue

        meeting = parser._extract_meeting_from_element(  # noqa: SLF001  # pylint: disable=protected-access
            MockElement(line),
            kommune,
        )
        if meeting:
            meetings.append(meeting)
    return meetings


def test_parser_extracts_expected_meetings():
    parser = MoteParser()

    sauda_sample = """
Ungdomsrådet, 20.08.2025, kl. 09:00
Tid: 09:00
Sted: Formannskapssalen
3 saker 21. august 2025

Eldrerådet, 21.08.2025, kl. 10:00
Tid: 10:00
Sted: Formannskapssalen
12 saker 26. august 2025

Utvalg for areal, næring og kultur, 26.08.2025, kl. 12:00
Tid: 12:00
Sted: Kommunestyresalen
2 saker 27. august 2025

Administrasjonsutvalget, 27.08.2025, kl. 10:00
Tid: 10:00
Sted: Kommunestyresalen
3 saker 27. august 2025

Formannskapet, 27.08.2025, kl. 11:00
Tid: 11:00
Sted: Kommunestyresalen
"""

    strand_sample = """
Klagenemnd for eiendomsskatt, 26.08.2025, kl. 09:00
Tid: 09:00
Sted: Møterom - Heiahornet
7 saker 26. august 2025

Forvaltningsutvalget, 27.08.2025, kl. 16:00
Tid: 16:00
Sted: Kommunestyresalen
164 saker 27. august 2025

Kommunestyret - temamøte, 27.08.2025, kl. 18:00
Tid: 18:00
Sted: Kommunestyresalen
"""

    meetings_sauda = _extract_from_lines(parser, "Sauda kommune", sauda_sample.splitlines())
    meetings_strand = _extract_from_lines(parser, "Strand kommune", strand_sample.splitlines())

    assert len(meetings_sauda) == 5
    assert len(meetings_strand) == 3

    for meeting in meetings_sauda + meetings_strand:
        assert meeting["kommune"] in {"Sauda kommune", "Strand kommune"}
        assert meeting["title"]
        assert meeting["date"].startswith("2025-08")

    titles = {meeting["title"].strip().rstrip(',') for meeting in meetings_sauda}
    assert "Formannskapet" in titles
    assert "Administrasjonsutvalget" in titles
