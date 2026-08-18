#!/usr/bin/env python3
"""
Scraper for Centrum Kultury, Sportu i Promocji (CKSiP) w Rabce-Zdroju
(https://centrum-kultury.rabka.pl/), producing data/events-cksip.json.

CKSiP is the actual organizer behind most cultural events in Rabka-Zdrój
(amfiteatr, Kino Śnieżka, Teatr Rabcio partnerships, Muzeum im. Orkana
events, etc.) — its site is often more detailed than the town hall's
calendar, but has a different structure: mostly prose blog posts and a
narrative "Kalendarz Imprez" page, not a clean list of dated entries.

Like scraper.py, this is a HEURISTIC text-based parser, not a precise
DOM scraper (no public API/RSS exists here either). Dates on this site
are written in prose, e.g. "19–21 czerwca 2026" or "15 do 18 lipca", so
the pattern here is Polish month names rather than the "DD - MM - YYYY"
style used on rabka.pl. Expect to tune this if CKSiP changes its site.

Usage:
    pip install requests beautifulsoup4
    python scraper/scraper_cksip.py
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from categories import guess_category
from event_quality import is_plausible_event

CALENDAR_URL = "https://centrum-kultury.rabka.pl/kalendarz"
BLOG_URL = "https://centrum-kultury.rabka.pl/blog"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "events-cksip.json"

MONTHS = {
    "stycznia": 1, "lutego": 2, "marca": 3, "kwietnia": 4, "maja": 5, "czerwca": 6,
    "lipca": 7, "sierpnia": 8, "września": 9, "października": 10, "listopada": 11,
    "grudnia": 12,
}
MONTH_PATTERN = "|".join(MONTHS.keys())

# Matches: "19–21 czerwca 2026", "15 do 18 lipca 2026", "2 lutego 2026", "29 czerwca"
DATE_RE = re.compile(
    rf"(\d{{1,2}})(?:\s*(?:[-–]|do)\s*(\d{{1,2}}))?\s+({MONTH_PATTERN})(?:\s+(\d{{4}}))?",
    re.IGNORECASE,
)

DEFAULT_YEAR = datetime.now(timezone.utc).year


def to_iso(day: str, month_name: str, year: str | None) -> str:
    month = MONTHS[month_name.lower()]
    y = int(year) if year else DEFAULT_YEAR
    return f"{y}-{month:02d}-{int(day):02d}"


def fetch_page(url: str) -> str:
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (compatible; RabkaEventsBot/1.0)"})
    resp.raise_for_status()
    return resp.text


def extract_events(html: str, page_label: str, page_url: str) -> list[dict]:
    """
    Same block-around-a-date-match heuristic as scraper.py, adapted to
    the Polish-prose date format used on this site. See scraper.py's
    docstring for the general approach and its caveats — they apply
    here too.
    """
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("main") or soup.body or soup
    text_blocks = [t for t in container.stripped_strings]
    full_text = "\n".join(text_blocks)

    events = []
    matches = list(DATE_RE.finditer(full_text))
    for i, m in enumerate(matches):
        start_idx = m.start()
        preceding = full_text[max(0, start_idx - 200):start_idx].strip().splitlines()
        title = next((line.strip() for line in reversed(preceding) if len(line.strip()) > 4), "").strip()
        if not title:
            continue

        end_of_block = matches[i + 1].start() if i + 1 < len(matches) else min(len(full_text), m.end() + 400)
        following = full_text[m.end():end_of_block].strip()
        desc = " ".join(following.splitlines()).strip()
        desc = re.sub(r"\b(zobacz więcej|czytaj dalej)\b", "", desc, flags=re.IGNORECASE).strip()

        day1, day2, month_name, year = m.groups()
        start = to_iso(day1, month_name, year)
        end = to_iso(day2, month_name, year) if day2 else start

        if not is_plausible_event(title, desc):
            continue

        events.append({
            "id": f"cksip-{page_label}-{len(events) + 1}",
            "title": title[:200],
            "category": guess_category(title, desc),
            "start": start,
            "end": end,
            "time": "",
            "location": "",
            "url": page_url,
            "desc": desc[:400],
        })

    return events


def dedupe(events: list[dict]) -> list[dict]:
    """Drop exact (title, start) duplicates that show up across the two pages scraped."""
    seen = set()
    unique = []
    for e in events:
        key = (e["title"].lower(), e["start"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)
    return unique


def main():
    all_events = []
    for label, url in (("kalendarz", CALENDAR_URL), ("blog", BLOG_URL)):
        try:
            html = fetch_page(url)
        except requests.RequestException as e:
            print(f"Failed to fetch {url}: {e}", file=sys.stderr)
            continue
        all_events.extend(extract_events(html, label, url))

    all_events = dedupe(all_events)

    if not all_events:
        print("No events extracted from centrum-kultury.rabka.pl — the page "
              "structure likely changed. Inspect the site and update scraper_cksip.py.",
              file=sys.stderr)
        sys.exit(1)

    output = {
        "source": CALENDAR_URL,
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "events": all_events,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(all_events)} events to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
