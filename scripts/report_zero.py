#!/usr/bin/env python3
"""Rapporter kommuner med 0 møter (10 dager) og tidligste møte innen 60 dager."""

from __future__ import annotations

import io
import sys
from collections import defaultdict
from contextlib import redirect_stdout
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

    silent = io.StringIO()
    with redirect_stdout(silent):
        meetings = scrape_all_meetings(configs, pipeline.calendar_sources, days_ahead=60)

    by_kommune = defaultdict(list)
    for m in meetings:
        kommune = _field(m, "kommune") or "(ukjent)"
        by_kommune[kommune].append(m)

    zero_list = [
        "Klepp kommune",
        "Gjesdal kommune",
        "Kvitsøy kommune",
        "Randaberg kommune",
        "Sandnes kommune",
        "Time kommune",
        "Bymiljøpakken",
        "Ferde",
        "Sirdal kommune",
        "Strand kommune",
        "Suldal kommune",
        "Hå kommune",
    ]

    print("=== Tidligste møter (innen 60 dager) ===")
    for name in zero_list:
        meetings = by_kommune.get(name, [])
        parsed = []
        for m in meetings:
            date = _field(m, "date")
            time = _field(m, "time") or ""
            if date:
                parsed.append((date, time, m))
        parsed.sort(key=lambda item: (item[0], item[1]))
        if not parsed:
            print(f"- {name}: ingen møter funnet")
            continue
        date, time, m = parsed[0]
        print(f"- {name}: {date} {time} | {_field(m, 'title')}")

    print("\n=== Antall møter innen 10 dager ===")
    filtered_10 = filter_meetings_by_date_range(meetings, days_ahead=10)
    by_kommune_10 = defaultdict(list)
    for m in filtered_10:
        by_kommune_10[_field(m, "kommune") or "(ukjent)"].append(m)
    for name in zero_list:
        print(f"- {name}: {len(by_kommune_10.get(name, []))}")


if __name__ == "__main__":
    main()
