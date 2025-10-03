# pylint: disable=import-error

import pytest
from bs4 import BeautifulSoup

from politikk_moter.playwright_scraper import PlaywrightMoteParser


class _TestablePlaywrightParser(PlaywrightMoteParser):
    """Expose helper for testing the bc-content-list parser."""

    def extract_bc_meetings(
        self,
        soup: BeautifulSoup,
        kommune_name: str,
        base_url: str,
    ):
        return self._extract_bc_content_list_meetings(
            soup,
            kommune_name,
            base_url=base_url,
        )


TIME_SAMPLE_HTML = """
<div class="bc-content-list">
  <div class="bc-content-list-item">
    <div class="bc-content-teaser-text _contentTeaserText_mqsmx_60">
      <h4 class="bc-heading bc-heading--h4 bc-content-teaser-title _contentTeaserTitle_mqsmx_70">
        <span class="bc-content-teaser-title-text">
          <a href="#/details/m-123" aria-label="Administrasjonsutvalet, 15. oktober 2025, kl. 08:00">
            Administrasjonsutvalet
          </a>
        </span>
      </h4>
      <div class="_meetingDate_mqsmx_38">
        <div class="_meetingDateDay_mqsmx_50">15.</div>
        <div>oktober</div>
        <div class="innsyn-header-hidden">2025</div>
      </div>
      <dl class="bc-content-teaser-meta">
        <div class="bc-content-teaser-meta-property">
          <dt class="bc-content-teaser-meta-property-label">Tid</dt>
          <dd class="bc-content-teaser-meta-property-value">08:00</dd>
        </div>
        <div class="bc-content-teaser-meta-property">
          <dt class="bc-content-teaser-meta-property-label">Stad</dt>
          <dd class="bc-content-teaser-meta-property-value">Formannskapssalen</dd>
        </div>
      </dl>
    </div>
  </div>
  <div class="bc-content-list-item">
    <div class="bc-content-teaser-text _contentTeaserText_mqsmx_60">
      <h4 class="bc-heading bc-heading--h4 bc-content-teaser-title _contentTeaserTitle_mqsmx_70">
        <span class="bc-content-teaser-title-text">
          <a href="#/details/m-456" aria-label="Ungdomsrådet, 30.09.2025, kl. 15:45">
            Ungdomsrådet
          </a>
        </span>
      </h4>
      <div class="_meetingDate_mqsmx_38">
        <div>30.09.2025</div>
        <div>-</div>
        <div>25.07.2026</div>
      </div>
      <dl class="bc-content-teaser-meta">
        <div class="bc-content-teaser-meta-property">
          <dt class="bc-content-teaser-meta-property-label">Stad</dt>
          <dd class="bc-content-teaser-meta-property-value">Formannskapssalen</dd>
        </div>
      </dl>
    </div>
  </div>
</div>
"""


@pytest.mark.parametrize("expected_title, expected_date, expected_time", [
    ("Administrasjonsutvalet", "2025-10-15", "08:00"),
    ("Ungdomsrådet", "2025-09-30", "15:45"),
])
def test_time_bc_content_list_parser(expected_title, expected_date, expected_time):
    parser = _TestablePlaywrightParser()
    soup = BeautifulSoup(TIME_SAMPLE_HTML, "html.parser")
    meetings = parser.extract_bc_meetings(
        soup,
        "Time kommune",
        base_url="https://www.time.kommune.no/politikk/mote-og-saksdokument/moter-og-saksdokument/",
    )
    assert len(meetings) == 2

    titles = [m["title"] for m in meetings]
    assert expected_title in titles

    target = next(m for m in meetings if m["title"] == expected_title)
    assert target["date"] == expected_date
    assert target["time"] == expected_time
    assert target["kommune"] == "Time kommune"
    assert target["url"].startswith("https://www.time.kommune.no/")
    assert "Formannskapssalen" in target["location"]