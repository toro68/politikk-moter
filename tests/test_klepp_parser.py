# pylint: disable=import-error

from bs4 import BeautifulSoup

from politikk_moter.scraper import MoteParser


KLEPP_SAMPLE_HTML = """
<div class="meetingList">
  <a href="/Meetings/KLEPP/Meetings/Details/111111">
    <div class="meetingName"><span>Formannskapet (13.10.2025)</span></div>
    <div class="meetingDate"><span>13.10.2025</span><span>16:00</span></div>
  </a>
  <a href="/Meetings/KLEPP/Meetings/Details/222222">
    <div class="meetingName"><span>Hovudutval for helse og velferd (01.10.2025)</span></div>
    <div class="meetingDate"><span>01.10.2025</span><span>16:00</span></div>
  </a>
  <a href="/Meetings/KLEPP/Meetings/Details/333333">
    <div class="meetingName"><span>Klima- og miljøutvalet (21.10.2025)</span></div>
    <div class="meetingDate"><span>Sist oppdatert: 20.09.2025</span><span>kl. 18:30</span></div>
  </a>
  <a href="/Meetings/KLEPP/Boards/Details/999999">
    <div class="meetingName"><span>Kommunestyret 2023 - 2027</span></div>
  </a>
</div>
"""


class _TestableParser(MoteParser):
    def parse_klepp(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        return self._parse_klepp_meetings(
            soup,
            "https://opengov.360online.com/Meetings/KLEPP",
            "Klepp kommune",
        )


def test_klepp_custom_parser_extracts_meetings():
    parser = _TestableParser()
    meetings = parser.parse_klepp(KLEPP_SAMPLE_HTML)

    assert len(meetings) == 3

    titles = {m["title"] for m in meetings}
    assert titles == {"Formannskapet", "Hovudutval for helse og velferd", "Klima- og miljøutvalet"}

    formannskapet = next(m for m in meetings if m["title"] == "Formannskapet")
    assert formannskapet["date"] == "2025-10-13"
    assert formannskapet["time"] == "16:00"
    assert formannskapet["kommune"] == "Klepp kommune"
    assert formannskapet["url"].endswith("/Meetings/Details/111111")

    klima = next(m for m in meetings if m["title"] == "Klima- og miljøutvalet")
    assert klima["date"] == "2025-10-21"
    assert klima["time"] == "18:30"
    assert klima["url"].endswith("/Meetings/Details/333333")