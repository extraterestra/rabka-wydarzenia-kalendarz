#!/usr/bin/env python3
"""
Shared event-category heuristics for Rabka scrapers.

Priority matters: check samorząd / specific domains before broad tokens
like "sport" (which otherwise matches "Centrum Kultury, Sportu i Promocji").
"""
import re

# Checked in this order. First match wins.
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    (
        "samorzad",
        [
            r"\bsesj[aei]",
            r"rady\s+miejsk",
            r"rada\s+miejsk",
            r"\burz[aą]d\b",
            r"\buchwał",
            r"\bkonsultacj",
            r"\bburmistrz",
            r"konkurs\s+na\s+stanowisko",
            r"dyrektor(?:a)?\s+centrum\s+kultury",
        ],
    ),
    (
        "historia",
        [
            r"\bpamięc",
            r"\bpamięt",
            r"\bholocaust",
            r"\bmuze",
            r"\bhistori(?!czn)",
            r"\btradycj",
            r"\bredyk\b",
            r"architektur[ay]\s+drewnian",
            r"spacer\s+pamięci",
        ],
    ),
    (
        "sport",
        [
            r"\bbike\b",
            r"\brower",
            r"\bbieg",
            r"\bpuchar",
            r"\bzawody\b",
            r"\bturniej",
            r"\bcalisthen",
            r"kalisten",
            r"\blifting\b",
            r"street\s+workout",
            r"\bmecz\b",
            r"\bwyścig",
            r"\btour\b",
            r"grand\s+prix",
            r"\bmtb\b",
            r"\bkolarsk",
            r"\bmistrzostw",
            r"\bszachy\b",
            r"\bszachow",
            r"\bmma\b",
            r"highlander",
            r"sportow",
        ],
    ),
    (
        "dzieci",
        [
            r"\bdzieck",
            r"\bdzieci",
            r"\brodzin",
            r"\bprzedszkol",
            r"\bmaluch",
            r"tydzie[nń]\s+bardzo\s+małego",
            r"festiwal\s+literatur",
            r"\bspektakl",
            r"\blalk",
            r"\bpinokio",
            r"teatr\s+lalek",
            r"pch[lł]a\s+szachrajka",
        ],
    ),
    (
        "rozrywka",
        [
            r"\bkabaret",
            r"\bkoncert",
            r"stand[\s-]?up",
            r"\brozrywk",
            r"\bdisco\b",
            r"\bbaciary\b",
            r"\bimprez",
            r"\bdyskotek",
            r"\bshow\b",
            r"\bjubileuszow\w*\s+program",
            r"\bzabaw[ay]\b",
        ],
    ),
]

# Institutional wording that falsely triggers "sport" / similar tokens.
NOISE_RE = re.compile(
    r"centrum\s+kultury,?\s+sportu\s+i\s+promocji|"
    r"\bcksip\b|"
    r"wydział\s+kultury,?\s+sportu",
    re.IGNORECASE,
)


def guess_category(title: str, desc: str = "") -> str:
    """Return category key. Prefer signals from the title over the description."""
    title_l = NOISE_RE.sub(" ", (title or "").lower())
    desc_l = NOISE_RE.sub(" ", (desc or "").lower())

    for text in (title_l, f"{title_l} {desc_l}"):
        for cat, patterns in CATEGORY_RULES:
            if any(re.search(p, text, re.IGNORECASE) for p in patterns):
                return cat
    return "kultura"
