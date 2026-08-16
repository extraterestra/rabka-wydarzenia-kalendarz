#!/usr/bin/env python3
"""
Combines data/events-auto.json + data/events-cksip.json + data/events-manual.json
into a single events.ics file at the repo root, so residents can subscribe once
(via webcal:// or a plain https URL) and get every event in their own calendar
app (Google Calendar, Apple Calendar, Outlook...) automatically, refreshed
whenever those apps re-poll the feed.

No external dependencies — hand-rolled minimal ICS writer, since the format
is simple enough not to need a library for this use case.

Usage:
    python scraper/generate_ics.py
"""
import json
import uuid
from datetime import datetime, date, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILES = [
    ROOT / "data" / "events-auto.json",
    ROOT / "data" / "events-cksip.json",
    ROOT / "data" / "events-visitmalopolska.json",
    ROOT / "data" / "events-manual.json",
]
OUTPUT_PATH = ROOT / "events.ics"

CATEGORY_LABELS = {
    "kultura": "Kultura",
    "sport": "Sport",
    "dzieci": "Dzieci i rodzina",
    "historia": "Historia i tradycja",
    "samorzad": "Samorząd",
}


def load_events() -> list[dict]:
    events = []
    for path in DATA_FILES:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        events.extend(data.get("events", []))
    return events


def fold_line(line: str, limit: int = 73) -> str:
    """ICS lines should be folded at 75 octets; keep it simple with a char-based limit."""
    if len(line) <= limit:
        return line
    parts = [line[:limit]]
    rest = line[limit:]
    while rest:
        parts.append(" " + rest[:limit - 1])
        rest = rest[limit - 1:]
    return "\r\n".join(parts)


def escape_text(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics_date(iso_date: str, exclusive_end: bool = False) -> str:
    """All-day events use DATE (not DATETIME) values; DTEND is exclusive per the spec."""
    y, m, d = (int(x) for x in iso_date.split("-"))
    dt = date(y, m, d)
    if exclusive_end:
        # add one day so a single-day event still renders as one day, and
        # multi-day ranges include their last day
        from datetime import timedelta
        dt = dt + timedelta(days=1)
    return dt.strftime("%Y%m%d")


def build_vevent(e: dict) -> list[str]:
    uid = f"{e.get('id', uuid.uuid4())}@rabka-wydarzenia-kalendarz"
    cat_label = CATEGORY_LABELS.get(e.get("category"), e.get("category", ""))
    summary = escape_text(e.get("title", "Wydarzenie"))
    location = escape_text(e.get("location", ""))
    desc_parts = []
    if e.get("time"):
        desc_parts.append(f"Godzina: {e['time']}")
    if e.get("desc"):
        desc_parts.append(e["desc"])
    if e.get("source"):
        desc_parts.append(f"Źródło: {e['source']}")
    description = escape_text(" | ".join(desc_parts))

    start = e.get("start")
    end = e.get("end") or start
    if not start:
        return []

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;VALUE=DATE:{ics_date(start)}",
        f"DTEND;VALUE=DATE:{ics_date(end, exclusive_end=True)}",
        fold_line(f"SUMMARY:{summary}"),
    ]
    if location:
        lines.append(fold_line(f"LOCATION:{location}"))
    if description:
        lines.append(fold_line(f"DESCRIPTION:{description}"))
    if cat_label:
        lines.append(fold_line(f"CATEGORIES:{escape_text(cat_label)}"))
    lines.append("END:VEVENT")
    return lines


def main():
    events = load_events()
    # de-dupe identical (title, start) pairs across the three source files
    seen = set()
    unique = []
    for e in events:
        key = (e.get("title", "").strip().lower(), e.get("start"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Fundacja Rozwoju Regionu Rabka//Kalendarz Wydarzen//PL",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Kalendarz Wydarzeń — Rabka-Zdrój",
        "X-WR-TIMEZONE:Europe/Warsaw",
    ]
    for e in unique:
        lines.extend(build_vevent(e))
    lines.append("END:VCALENDAR")

    OUTPUT_PATH.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    print(f"Wrote {len(unique)} events to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
