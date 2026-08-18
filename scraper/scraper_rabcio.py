#!/usr/bin/env python3
"""
Scraper for Teatr Lalek Rabcio repertoire
(https://teatr.rabcio.pl/), producing data/events-rabcio.json.

The theatre site's "Repertuar" page embeds a Bilety24 ticket widget
(partner 1568). Dated showings live on the public organizer page:

    https://www.bilety24.pl/organizator/teatr-lalek-rabcio-1568.html

This script parses that page for links under /teatr/1568-… and reads
title/date/time/city from each link's title attribute, e.g.:

    Spektakl: Luna - 2026-08-19 11:00 - Rabka Zdrój

Only performances in Rabka-Zdrój are kept (touring guest dates elsewhere
are ignored for this municipal calendar).

Usage:
    pip install requests beautifulsoup4
    python scraper/scraper_rabcio.py
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

THEATRE_URL = "https://teatr.rabcio.pl/"
REPERTUAR_URL = "https://teatr.rabcio.pl/repertuar-2025/"
BILETY24_URL = "https://www.bilety24.pl/organizator/teatr-lalek-rabcio-1568.html"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "events-rabcio.json"

LOCATION = "Teatr Lalek Rabcio, ul. Orkana 3c, Rabka-Zdrój"

# Title attribute pattern from Bilety24 full-info links.
TITLE_RE = re.compile(
    r"(?:Spektakl:\s*)?(.+?)\s*-\s*(\d{4}-\d{2}-\d{2})(?:\s+(\d{1,2}:\d{2}))?\s*-\s*(.+)$",
    re.IGNORECASE,
)

# Adult / "Scena Dużego Widza" cues; everything else defaults to children.
ADULT_KEYWORDS = [
    "makbet", "szkoła katów", "szkola katow", "ballady", "letni dzień",
    "letni dzien", "scena dużego", "scena duzego",
]


def guess_category(title: str) -> str:
    text = title.lower()
    if any(kw in text for kw in ADULT_KEYWORDS):
        return "kultura"
    return "dzieci"


def fetch_page(url: str) -> str:
    resp = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RabkaEventsBot/1.0)"},
    )
    resp.raise_for_status()
    return resp.text


def extract_events(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    events = []
    seen = set()

    for a in soup.select('a[href*="/teatr/1568-"]'):
        href = a.get("href") or ""
        title_attr = (a.get("title") or "").strip()
        m = TITLE_RE.match(title_attr)
        if not m:
            continue

        title, start, time, city = m.groups()
        title = title.strip()
        city = city.strip()

        # Keep only home performances in Rabka-Zdrój.
        if "rabka" not in city.lower():
            continue

        # Prefer data-title from the sibling "kup bilet" button when present.
        parent = a.find_parent("div")
        kup = parent.select_one("a.kupinfo[data-title]") if parent else None
        if kup and kup.get("data-title"):
            title = kup["data-title"].strip()

        key = (title.lower(), start, time or "")
        if key in seen:
            continue
        seen.add(key)

        event_id = re.search(r"id=(\d+)", href)
        uid = event_id.group(1) if event_id else str(len(events) + 1)

        ticket_url = urljoin(BILETY24_URL, href)
        events.append({
            "id": f"rabcio-{uid}",
            "title": title[:200],
            "category": guess_category(title),
            "start": start,
            "end": start,
            "time": time or "",
            "location": LOCATION,
            "url": ticket_url,
            "desc": "Spektakl Teatru Lalek Rabcio.",
        })

    events.sort(key=lambda e: (e["start"], e["time"] or ""))
    return events


def main():
    try:
        html = fetch_page(BILETY24_URL)
    except requests.RequestException as e:
        print(f"Failed to fetch {BILETY24_URL}: {e}", file=sys.stderr)
        sys.exit(1)

    events = extract_events(html)
    if not events:
        print(
            "No Rabcio performances in Rabka-Zdrój found on Bilety24 — "
            "the season may be empty or the page structure changed. "
            "Inspect https://www.bilety24.pl/organizator/teatr-lalek-rabcio-1568.html "
            "and update scraper_rabcio.py if needed.",
            file=sys.stderr,
        )

    output = {
        "source": REPERTUAR_URL,
        "ticket_source": BILETY24_URL,
        "theatre": THEATRE_URL,
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "events": events,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(events)} events to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
