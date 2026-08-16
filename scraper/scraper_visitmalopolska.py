#!/usr/bin/env python3
"""
Scraper for VisitMalopolska (https://visitmalopolska.pl/wydarzenia), the
official regional tourism board's events portal, filtered down to events
mentioning Rabka-Zdrój / Rabka. Produces data/events-visitmalopolska.json.

READ THIS BEFORE RELYING ON IT:

1. VisitMalopolska runs on Liferay (a Java portal framework) with heavy
   client-side rendering and pagination via long query-string parameters
   (_101_INSTANCE_..._cur, ..._delta, etc.) — this is a fundamentally
   less scraper-friendly site than rabka.pl or centrum-kultury.rabka.pl.

2. The site has active bot-detection that blocked a basic fetch attempt
   during development of this script. I could NOT verify this scraper
   against the live site. It's written defensively (custom headers,
   generous timeout, clear failure messages) but you MUST test it
   locally before trusting it in production:

       pip install requests beautifulsoup4
       python scraper/scraper_visitmalopolska.py

   If it fails with a 403/999/anti-bot response, that confirms the
   block — see the "If this doesn't work" section below.

3. Because it's region-wide (all of Małopolska), this script filters
   results down to ones that mention "Rabka" in the title or location
   text. If VisitMalopolska's category/location filtering has a stable
   URL parameter for Rabka-Zdrój specifically (check by using their
   site's own filter UI and copying the resulting URL), swap
   SOURCE_URL below for that — it'll be far more precise than
   text-matching everything and filtering after the fact.

If this doesn't work — alternatives worth trying before giving up:
  a) Open browser dev tools (Network tab) while browsing
     visitmalopolska.pl/wydarzenia and filtering by Rabka-Zdrój. Liferay
     portlets sometimes call a JSON/XHR endpoint under the hood even
     though the page looks server-rendered — if you find one, hitting
     it directly is much more reliable than parsing HTML.
  b) Register at otwarte.dane.malopolska.pl for API access — if the
     region publishes tourism/events data there, it replaces this
     script entirely with a real API call.
  c) Fall back to the regional/county-level subdomain, e.g.
     nowytarg.visitmalopolska.pl (Rabka-Zdrój's powiat), which showed
     up in search results and may be less protected than the main
     domain — untested from here for the same bot-detection reason.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://visitmalopolska.pl/wydarzenia"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "events-visitmalopolska.json"

RABKA_KEYWORDS = ["rabka", "rabce", "rabki", "rabkę", "rabką"]

MONTHS = {
    "stycznia": 1, "lutego": 2, "marca": 3, "kwietnia": 4, "maja": 5, "czerwca": 6,
    "lipca": 7, "sierpnia": 8, "września": 9, "października": 10, "listopada": 11,
    "grudnia": 12,
}
MONTH_PATTERN = "|".join(MONTHS.keys())
# Handles "DD - MM - YYYY" (like rabka.pl) as well as "D miesiąca YYYY" (like CKSiP)
DATE_RE_NUMERIC = re.compile(r"(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{4})")
DATE_RE_PROSE = re.compile(
    rf"(\d{{1,2}})(?:\s*(?:[-–]|do)\s*(\d{{1,2}}))?\s+({MONTH_PATTERN})(?:\s+(\d{{4}}))?",
    re.IGNORECASE,
)

CATEGORY_KEYWORDS = {
    "sport":    ["bike", "rowe", "bieg", "puchar", "zawody", "turniej", "mtb", "sport"],
    "dzieci":   ["dzieck", "dziecię", "rodzin", "przedszkol"],
    "historia": ["pamięc", "muze", "histor", "tradycj", "zabytk"],
    "samorzad": ["sesja rady", "rada miejska", "urząd", "uchwał"],
}

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def guess_category(text: str) -> str:
    t = text.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return cat
    return "kultura"


def to_iso_prose(day, month_name, year, default_year):
    month = MONTHS[month_name.lower()]
    y = int(year) if year else default_year
    return f"{y}-{month:02d}-{int(day):02d}"


def fetch(url: str) -> str:
    resp = requests.get(url, timeout=25, headers=HEADERS)
    resp.raise_for_status()
    return resp.text


def extract_rabka_events(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("main") or soup.body or soup
    full_text = "\n".join(container.stripped_strings)

    default_year = datetime.now(timezone.utc).year
    events = []

    # Try both date styles, merged and sorted by position in text.
    matches = sorted(
        list(DATE_RE_NUMERIC.finditer(full_text)) + list(DATE_RE_PROSE.finditer(full_text)),
        key=lambda m: m.start(),
    )

    for i, m in enumerate(matches):
        start_idx = m.start()
        preceding = full_text[max(0, start_idx - 200):start_idx].strip().splitlines()
        title = next((line.strip() for line in reversed(preceding) if len(line.strip()) > 4), "")
        if not title:
            continue

        end_of_block = matches[i + 1].start() if i + 1 < len(matches) else min(len(full_text), m.end() + 400)
        following = full_text[m.end():end_of_block].strip()
        desc = " ".join(following.splitlines()).strip()

        block_text = f"{title} {desc}"
        if not any(kw in block_text.lower() for kw in RABKA_KEYWORDS):
            continue  # not a Rabka-related event, skip (region-wide portal)

        if m.re is DATE_RE_NUMERIC:
            d, mo, y = m.groups()
            start = f"{y}-{int(mo):02d}-{int(d):02d}"
            end = start
        else:
            d1, d2, month_name, year = m.groups()
            start = to_iso_prose(d1, month_name, year, default_year)
            end = to_iso_prose(d2, month_name, year, default_year) if d2 else start

        events.append({
            "id": f"vm-{len(events) + 1}",
            "title": title[:200],
            "category": guess_category(block_text),
            "start": start,
            "end": end,
            "time": "",
            "location": "Rabka-Zdrój (okolice)",
            "desc": desc[:400],
        })

    return events


def main():
    try:
        html = fetch(SOURCE_URL)
    except requests.RequestException as e:
        print(f"Failed to fetch {SOURCE_URL}: {e}", file=sys.stderr)
        print("This is very likely the bot-detection issue described in this "
              "script's docstring — see the 'If this doesn't work' section there.",
              file=sys.stderr)
        sys.exit(1)

    events = extract_rabka_events(html)

    output = {
        "source": SOURCE_URL,
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "events": events,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    if not events:
        print(f"Fetched the page OK but found 0 Rabka-related events. Wrote empty "
              f"events list to {OUTPUT_PATH}. This likely means the page structure "
              f"needs a closer look — inspect visitmalopolska.pl/wydarzenia manually "
              f"and adjust the parsing.", file=sys.stderr)
    else:
        print(f"Wrote {len(events)} Rabka-related events to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
