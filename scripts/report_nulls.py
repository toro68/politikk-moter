#!/usr/bin/env python3
"""Rapporter kommuner med 0 møter og manglende felter i 10-dagersvinduet."""

from __future__ import annotations

import sys
from collections import defaultdict
from contextlib import redirect_stdout
import io
from pathlib import Path


def _bootstrap_package() -> None:
    root = Path(__file__).resolve().parents[1]
    src_dir = root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def _field(item, key):
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def main() -> None:
    _bootstrap_package()
    from politikk_moter.kommuner import get_kommune_configs
    from politikk_moter.pipeline_config import get_pipeline_configs
    from politikk_moter.scraper import filter_meetings_by_date_range, scrape_all_meetings

    pipeline = get_pipeline_configs()[0]
    configs = get_kommune_configs(pipeline.kommune_groups)
    config_names = [c["name"] for c in configs]

    silent = io.StringIO()
    with redirect_stdout(silent):
        meetings = scrape_all_meetings(configs, pipeline.calendar_sources, days_ahead=10)
    filtered = filter_meetings_by_date_range(meetings, days_ahead=10)

    by_kommune = defaultdict(list)
    missing_time = []
    missing_location = []
    missing_title = []
    missing_url = []

    for m in filtered:
        kommune = _field(m, "kommune") or "(ukjent)"
        by_kommune[kommune].append(m)
        if not _field(m, "time"):
            missing_time.append(m)
        if not _field(m, "location"):
            missing_location.append(m)
        if not _field(m, "title"):
            missing_title.append(m)
        if not _field(m, "url"):
            missing_url.append(m)

    zero_kommuner = [name for name in config_names if len(by_kommune.get(name, [])) == 0]
    print("=== 0 møter (kommune) ===")
    for name in sorted(zero_kommuner):
        print(f"- {name}")

    print("\n=== Mangler felt (antall) ===")
    print(f"time: {len(missing_time)}")
    print(f"location: {len(missing_location)}")
    print(f"title: {len(missing_title)}")
    print(f"url: {len(missing_url)}")

    print("\n=== Eksempler (mangler time/location) ===")
    examples = missing_time[:5] + missing_location[:5]
    for m in examples:
        print(
            f"- {_field(m, 'date')} | {_field(m, 'kommune')} | {_field(m, 'title')} | "
            f"time={_field(m, 'time')} | loc={_field(m, 'location')}"
        )


if __name__ == "__main__":
    main()
