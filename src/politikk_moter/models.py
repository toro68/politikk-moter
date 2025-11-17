"""Dataclasses and helpers for structured scraper data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Union


@dataclass(frozen=True, slots=True)
class Meeting:
    """Structured representation of a single political meeting."""

    title: str
    date: str
    time: Optional[str] = None
    location: str = "Ikke oppgitt"
    kommune: str = "Ukjent kommune"
    url: str = ""
    raw_text: str = ""
    source: Optional[str] = None

    def sort_key(self) -> tuple[str, str]:
        """Sorting helper used for chronological ordering."""
        return (self.date, self.time or "00:00")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the meeting back to a serialisable dict."""
        return {
            "title": self.title,
            "date": self.date,
            "time": self.time,
            "location": self.location,
            "kommune": self.kommune,
            "url": self.url,
            "raw_text": self.raw_text,
            "source": self.source,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Meeting":
        """Create a meeting from an unstructured mapping."""
        title = str(data.get("title") or "Politisk møte").strip()
        if not title:
            title = "Politisk møte"
        date = str(data.get("date") or "1970-01-01")
        time = data.get("time")
        location = str(data.get("location") or "Ikke oppgitt")
        kommune = str(data.get("kommune") or "Ukjent kommune")
        url = str(data.get("url") or "")
        raw_text = str(data.get("raw_text") or "")
        source = data.get("source")
        return cls(
            title=title,
            date=date,
            time=time,
            location=location,
            kommune=kommune,
            url=url,
            raw_text=raw_text,
            source=source,
        )


MeetingLike = Union[Meeting, Mapping[str, Any]]


def ensure_meeting(value: MeetingLike) -> Meeting:
    """Coerce dictionaries or Meeting instances into Meeting."""
    return value if isinstance(value, Meeting) else Meeting.from_mapping(value)
