#!/usr/bin/env python3
"""Fuzzy de-duplication for events with near-identical titles on the same date."""
import re

STOP = {
    "w", "we", "na", "do", "od", "z", "za", "po", "dla", "i", "oraz", "the",
    "a", "an", "już", "juz", "się", "sie", "to", "jak", "czy", "że", "ze",
    "raz", "trzeci", "drugi", "pierwszy", "edn", "rabce", "rabka", "zdroju",
    "zdroj", "dni", "dnia", "dwa",
}


def normalize_title(title: str) -> str:
    t = (title or "").lower().replace("\xa0", " ")
    t = re.sub(r"\b20\d{2}\b", " ", t)
    t = re.sub(r"[^a-ząćęłńóśźż0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def title_tokens(title: str) -> set[str]:
    return {
        w for w in normalize_title(title).split()
        if len(w) > 2 and w not in STOP
    }


def dates_overlap(a: dict, b: dict) -> bool:
    a0, a1 = a.get("start") or "", a.get("end") or a.get("start") or ""
    b0, b1 = b.get("start") or "", b.get("end") or b.get("start") or ""
    if not a0 or not b0:
        return False
    return a0 <= b1 and b0 <= a1


def is_near_duplicate(a: dict, b: dict) -> bool:
    if not dates_overlap(a, b):
        return False
    ta, tb = title_tokens(a.get("title", "")), title_tokens(b.get("title", ""))
    na, nb = normalize_title(a.get("title", "")), normalize_title(b.get("title", ""))
    if na and nb and (na in nb or nb in na):
        return True

    def lead(title: str) -> str:
        words = [
            w for w in normalize_title(title).split()
            if len(w) > 2 and w not in STOP
        ]
        return " ".join(words[:3])

    la, lb = lead(a.get("title", "")), lead(b.get("title", ""))
    if la and lb and la == lb:
        return True
    if not ta or not tb:
        return na == nb
    inter = len(ta & tb)
    return inter / min(len(ta), len(tb)) >= 0.5


def prefer_event(a: dict, b: dict) -> dict:
    """Keep the more informative listing when two events collide."""
    source_rank = {
        "Fundacja": 0,
        "Rabcio": 1,
        "Urząd Miejski": 2,
        "CKSiP": 3,
    }
    # Prefer richer title, then preferred source, then longer description
    score = lambda e: (
        len(title_tokens(e.get("title", ""))),
        len((e.get("title") or "")),
        -source_rank.get(e.get("source", ""), 9),
        len((e.get("desc") or "")),
        1 if e.get("time") else 0,
        1 if e.get("url") else 0,
    )
    return a if score(a) >= score(b) else b


def dedupe_events(events: list[dict]) -> list[dict]:
    unique: list[dict] = []
    for e in events:
        matched_idx = None
        for i, kept in enumerate(unique):
            if is_near_duplicate(e, kept):
                matched_idx = i
                break
        if matched_idx is None:
            unique.append(e)
        else:
            unique[matched_idx] = prefer_event(unique[matched_idx], e)
    return unique
