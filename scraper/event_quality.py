#!/usr/bin/env python3
"""Reject scraper artifacts that are not real event titles."""
import re
import unicodedata

MONTHS = (
    "stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|"
    "sierpnia|września|października|listopada|grudnia"
)

# Titles that are only date lists, e.g. "16 i 30 lipca oraz 13 i"
DATE_FRAGMENT_RE = re.compile(
    rf"^(?:\d{{1,2}}\s*(?:i|oraz|,|-|–|do|/)\s*)+\d{{0,2}}"
    rf"(?:\s+(?:{MONTHS}))?(?:\s+(?:i|oraz|,|-|–|do)\s*\d{{0,2}})*\s*$",
    re.IGNORECASE,
)

# Sentence leftovers / truncated prose used as a "title"
BAD_END_RE = re.compile(
    r"(?i)\b(już|od|oraz|natomiast|się|który|która|które|którym)\s*$"
)
# Lone dangling connector at the very end (avoid matching "i" inside words)
DANGLING_END_RE = re.compile(r"(?i)(?:\s|^)(?:a|i|w|na|do|,)\s*$")

BAD_START_RE = re.compile(
    r"(?i)^(ju[zż]\s+od|gotowano|urmistrz|tradycyjnie|publiczność|"
    r"amfiteatr stanie|odbędzie się|tego samego|dzi[sś]\b|nie był|"
    r"jednym z|miłośnicy|prawdziwie|najmłodsi|sportowe zakończenie|"
    r"pod koniec|na scenie|iwona gal)\b"
)


LETTER_RE = re.compile(r"[A-Za-zÀ-žĄĆĘŁŃÓŚŹŻąćęłńóśźż]")

# Mid-word scrape leftovers like "urmistrz" / "ka-Zdrój" (must stay case-sensitive)
MIDWORD_RE = re.compile(r"^[a-ząćęłńóśźż]{1,4}-?[A-ZĄĆĘŁŃÓŚŹŻ]")


def _starts_with_uppercase(title: str) -> bool:
    for ch in title:
        if ch.isspace() or ch in "„\"'«":
            continue
        # Digits / Roman-looking starts are OK (e.g. "XXXIII Sesja...")
        if ch.isdigit() or ch in "IVXLCDM":
            return True
        cat = unicodedata.category(ch)
        return cat.startswith("L") and ch == ch.upper()
    return False


def is_plausible_event(title: str, desc: str = "") -> bool:
    """
    Return False for CKSiP/auto prose fragments that must not be shown
    as calendar events (date crumbs, mid-sentence scraps, tiny stubs).
    """
    t = re.sub(r"\s+", " ", (title or "").replace("\xa0", " ")).strip(" .")
    if len(t) < 4:
        return False
    if not _starts_with_uppercase(t):
        return False
    if DATE_FRAGMENT_RE.match(t):
        return False

    letters = LETTER_RE.findall(t)
    digits = re.findall(r"\d", t)
    if len(letters) < 4:
        return False
    if len(digits) > len(letters):
        return False

    if BAD_END_RE.search(t) or DANGLING_END_RE.search(t):
        return False
    if t.endswith(",") or t.endswith("–") or t.endswith("-"):
        return False

    if BAD_START_RE.match(t):
        return False

    if MIDWORD_RE.match(t):
        return False

    # Reject titles that are mostly a date enumeration with almost no name words
    month_hits = len(re.findall(MONTHS, t, flags=re.IGNORECASE))
    if month_hits and len(digits) >= 2 and len(letters) < 18:
        return False

    # Long narrative sentences without a compact event-name shape
    words = t.split()
    if len(words) >= 12 and not re.search(r"[!?:]", t):
        # likely scraped prose, not a titled event
        if re.search(r"(?i)\b(odbędzie|odbyło|zapowiada|przyniesie|porwie|wystąpi|znajdą)\b", t):
            return False

    return True
