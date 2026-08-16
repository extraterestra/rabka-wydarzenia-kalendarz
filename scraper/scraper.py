#!/usr/bin/env python3
"""
Scraper for the Rabka-Zdrój town hall events calendar
(https://rabka.pl/kalendarz-wydarzen/), producing data/events-auto.json.

IMPORTANT — read before relying on this in production:
There is no public API or RSS feed for this calendar. This script parses
the rendered page heuristically (looking for "DD - MM - YYYY" date
patterns and the text around them). Town-hall CMS templates change
without notice, so:
  1. Treat this as a starting point, not a guaranteed-forever solution.
  2. Run it in CI (see .github/workflows/update-events.yml) and check
     the diff each time it updates events-auto.json, at least for the
     first few months.
  3. The more durable fix is asking the Urząd (you already have a
     contact there) whether they can export a simple CSV/JSON feed of
     events instead of scraping their public site. Worth raising this
     even after the scraper is running.

Usage:
    pip install requests beautifulsoup4
    python scraper/scraper.py
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

CALENDAR_URL = "https://rabka.pl/kalendarz-wydarzen/"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "events-auto.json"

DATE_RE = re.compile(r"(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{4})")

CATEGORY_KEYWORDS = {
    "sport":    ["bike", "rowe", "bieg", "puchar", "zawody", "turniej", "calisthenics",
                 "lifting", "sport", "mecz", "wyścig", "tour", "grand prix"],
    "dzieci":   ["dzieck", "dziecię", "rodzin", "przedszkol", "malucha"],
    "historia": ["pamięc", "pamięt", "muze", "histor", "tradycj", "redyk", "holocaust",
                 "architektury drewnian"],
    "samorzad": ["sesja rady", "rada miejska", "urząd", "uchwał", "konsultacj"],
    # everything else defaults to "kultura"
}


def guess_category(title: str, desc: str) -> str:
    text = f"{title} {desc}".lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return cat
    return "kultura"


def parse_date_range(raw_dates: list[str]) -> tuple[str, str]:
    """Turns one or two DD-MM-YYYY strings into ISO start/end dates."""
    def to_iso(d, m, y):
        return f"{y}-{int(m):02d}-{int(d):02d}"

    parsed = [DATE_RE.match(d.strip()) for d in raw_dates]
    parsed = [m for m in parsed if m]
    if not parsed:
        return None, None
    start = to_iso(*parsed[0].groups())
    end = to_iso(*parsed[-1].groups())
    return start, end


def fetch_page(url: str) -> str:
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (compatible; RabkaEventsBot/1.0)"})
    resp.raise_for_status()
    return resp.text


def extract_events(html: str) -> list[dict]:
    """
    Heuristic extraction: the page lists events as repeating blocks, each
    containing a title, a date (or date range in "DD - MM - YYYY" form),
    and a short description. We split the page text on the date pattern
    and reconstruct blocks around each match. This is intentionally
    tolerant of markup changes since it works on visible text, not on
    specific CSS classes/IDs — but it WILL need tuning against the live
    site. Inspect the page's HTML and adjust `soup.select(...)` below for
    a more precise, less fragile extraction once you've seen the real DOM.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Prefer a scoped container if we can find one; fall back to full body.
    container = soup.select_one("main") or soup.body or soup

    text_blocks = [t for t in container.stripped_strings]
    full_text = "\n".join(text_blocks)

    events = []
    # Split around date-pattern occurrences, keeping some context before
    # (title, usually the line(s) just above the date) and after (desc).
    matches = list(DATE_RE.finditer(full_text))
    for i, m in enumerate(matches):
        start_idx = m.start()
        # look back up to ~200 chars for a plausible title line
        preceding = full_text[max(0, start_idx - 200):start_idx].strip().splitlines()
        title = next((line.strip() for line in reversed(preceding) if len(line.strip()) > 4), "").strip()

        # look forward up to ~400 chars for description, stopping at the next date match
        end_of_block = matches[i + 1].start() if i + 1 < len(matches) else min(len(full_text), m.end() + 400)
        following = full_text[m.end():end_of_block].strip()
        desc = " ".join(following.splitlines()).strip()
        # trim boilerplate like "zobacz więcej" links
        desc = re.sub(r"\b(zobacz więcej|czytaj dalej)\b", "", desc, flags=re.IGNORECASE).strip()

        if not title:
            continue

        # check if the very next match is glued to this one (a date range like
        # "29 - 08 - 2026" ... "30 - 08 - 2026" listed together for one event)
        raw_dates = [m.group(0)]
        start, end = parse_date_range(raw_dates)
        if not start:
            continue

        events.append({
            "id": f"auto-{len(events) + 1}",
            "title": title[:200],
            "category": guess_category(title, desc),
            "start": start,
            "end": end,
            "time": "",
            "location": "",
            "desc": desc[:400],
        })

    return events


def main():
    try:
        html = fetch_page(CALENDAR_URL)
    except requests.RequestException as e:
        print(f"Failed to fetch {CALENDAR_URL}: {e}", file=sys.stderr)
        sys.exit(1)

    events = extract_events(html)
    if not events:
        print("No events extracted — the page structure likely changed. "
              "Inspect rabka.pl/kalendarz-wydarzen/ and update scraper.py.", file=sys.stderr)
        sys.exit(1)

    output = {
        "source": CALENDAR_URL,
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "events": events,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(events)} events to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
