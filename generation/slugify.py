"""Shared slug + URL-building logic for digest and opinion pieces.

Must stay byte-for-byte identical to website/lib/slugify.ts — Python-generated
links (weekly briefing, Bluesky posts, Related Coverage/Opinion blocks) must
resolve to the same URLs the website itself generates for the same title, or
the two diverge and links 404.

CUTOFF_DATE marks a permanent dual-pattern split, not a migration: anything
dated before it keeps its exact existing plain-date URL forever; anything on
or after it gets the new date+slug pattern.
"""

import re
import unicodedata
from datetime import date as _date

CUTOFF_DATE = _date(2026, 8, 6)

MAX_SLUG_LENGTH = 60


def slugify(title: str) -> str:
    s = title.lower()
    # NFKD decomposition splits accented Latin characters into base + combining
    # mark (á -> a + U+0301); dropping combining chars then strips the accent
    # while leaving the base letter — same effect as the TS version's NFKD +
    # U+0300-U+036F strip, via Python's own combining-class check.
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s).strip("-")

    if len(s) > MAX_SLUG_LENGTH:
        s = s[:MAX_SLUG_LENGTH]
        last_hyphen = s.rfind("-")
        if last_hyphen > 0:
            s = s[:last_hyphen]

    return s.strip("-")


def _as_date(d) -> _date:
    return _date.fromisoformat(d) if isinstance(d, str) else d


def build_digest_url(country: str, d, title: str) -> str:
    """Return the site-relative path for a country digest on date `d`.

    `d` may be a date object or an ISO 'YYYY-MM-DD' string.
    """
    day = _as_date(d)
    if day < CUTOFF_DATE:
        return f"/{country}/{day.isoformat()}"
    slug = slugify(title)
    return f"/{country}/{day.isoformat()}-{slug}" if slug else f"/{country}/{day.isoformat()}"


def build_opinion_url(persona_slug: str, d, title: str) -> str:
    """Return the site-relative path for an OpEd piece on date `d`.

    `d` may be a date object or an ISO 'YYYY-MM-DD' string.
    """
    day = _as_date(d)
    if day < CUTOFF_DATE:
        return f"/opinion/{persona_slug}/{day.isoformat()}"
    slug = slugify(title)
    return (
        f"/opinion/{persona_slug}/{day.isoformat()}-{slug}"
        if slug
        else f"/opinion/{persona_slug}/{day.isoformat()}"
    )
