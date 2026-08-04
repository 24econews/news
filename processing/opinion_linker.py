"""Link recent OpEd pieces into daily digests as a distinctly-labeled 'Related Opinion' block.

Separate from processing/cross_linker.py's 'Related Coverage' (cross-country
news connections) — this links a digest to a recent *opinion* piece about the
same country, so the two must never be visually or structurally conflated.
"""

import logging
import os
import re
import sys
from datetime import date, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, REPO_ROOT)

from generation.oped_builder import (  # noqa: E402
    OPED_OUTPUT_DIR,
    _strip_oped_body,
    infer_primary_country,
)
from processing.cross_linker import COUNTRY_META  # noqa: E402

logger = logging.getLogger(__name__)

# How far back to look for a relevant OpEd. Pieces publish ~4x/week, so 10
# days guarantees several candidates without linking to something stale.
OPINION_LOOKBACK_DAYS = 10

_FILENAME_RE = re.compile(r"^([a-z-]+)_(\d{4}-\d{2}-\d{2})\.md$")


def _oped_metadata(path: str) -> dict | None:
    """Return {persona_name, lens_short, title, country}, or None if unparseable
    or its country focus is ambiguous (see infer_primary_country)."""
    with open(path, encoding="utf-8") as f:
        content = f.read()

    persona_match = re.search(r"^>\s*PERSONA:\s*(.+)$", content, re.MULTILINE)
    lens_match = re.search(r"^>\s*LENS:\s*(.+)$", content, re.MULTILINE)
    title_match = re.search(r"^>\s*TITLE:\s*([\s\S]+?)(?=\n>\s*[A-Z_]+:|\n\s*\n)", content, re.MULTILINE)
    if not persona_match or not title_match:
        return None

    country = infer_primary_country(_strip_oped_body(content))
    if not country:
        return None

    return {
        "persona_name": persona_match.group(1).strip(),
        "lens_short": lens_match.group(1).strip() if lens_match else "",
        "title": re.sub(r"\s+", " ", title_match.group(1)).strip(),
        "country": country,
    }


def find_related_oped(country: str, digest_date: date) -> dict | None:
    """Return the most recent published OpEd about `country` in the lookback
    window before digest_date (strictly before — never same-day or future),
    or None if none is genuinely about that country."""
    if not os.path.isdir(OPED_OUTPUT_DIR):
        return None

    earliest = digest_date - timedelta(days=OPINION_LOOKBACK_DAYS)
    candidates = []
    for fname in os.listdir(OPED_OUTPUT_DIR):
        match = _FILENAME_RE.match(fname)
        if not match:
            continue
        slug, date_str = match.group(1), match.group(2)
        oped_date = date.fromisoformat(date_str)
        if earliest <= oped_date < digest_date:
            candidates.append((oped_date, slug, date_str, fname))

    candidates.sort(key=lambda t: t[0], reverse=True)

    for oped_date, slug, date_str, fname in candidates:
        meta = _oped_metadata(os.path.join(OPED_OUTPUT_DIR, fname))
        if meta and meta["country"] == country:
            return {**meta, "slug": slug, "date": date_str}
    return None


def _digest_paths(base_dir: str, country: str, date_str: str) -> tuple[str, str]:
    rel = COUNTRY_META[country]["path"].replace("{date}", date_str)
    md_path = os.path.join(base_dir, rel)
    return md_path, md_path[:-3] + ".en.md"


def _strip_existing_related_opinion(content: str) -> str:
    """Remove any previously injected '## Related Opinion' block (idempotent re-runs)."""
    for marker in ("\n---\n## Related Opinion", "\n## Related Opinion"):
        idx = content.find(marker)
        if idx != -1:
            return content[:idx]
    return content


def _build_related_opinion_block(oped: dict) -> str:
    url = f"/opinion/{oped['slug']}/{oped['date']}"
    byline = f"By {oped['persona_name']} — {oped['lens_short']}" if oped["lens_short"] else f"By {oped['persona_name']}"
    return f"\n---\n## Related Opinion\n\n[{oped['title']}]({url})\n{byline}\n"


def link_opinions(digest_date: date, countries: list, digests_base_dir: str) -> dict:
    """For each country's digest on digest_date, inject a Related Opinion link
    if a relevant recent OpEd exists. Must run AFTER cross_linker's Related
    Coverage injection for the same date — this always appends last, so the
    two blocks never interleave and the website can split on whichever marker
    it needs. Returns {linked: [country, ...]}."""
    linked = []

    for country in countries:
        if country not in COUNTRY_META:
            continue

        oped = find_related_oped(country, digest_date)
        if not oped:
            continue

        block = _build_related_opinion_block(oped)
        md_path, en_path = _digest_paths(digests_base_dir, country, digest_date.isoformat())

        injected = False
        for path in (md_path, en_path):
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as f:
                content = f.read()
            content = _strip_existing_related_opinion(content)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content + block)
            injected = True
            logger.info(f"[opinion_linker] Linked {oped['slug']}_{oped['date']} into {os.path.basename(path)}")

        if injected:
            linked.append(country)

    return {"linked": linked}
