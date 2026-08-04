"""Post a published OpEd piece's teaser to Bluesky.

Reuses bluesky_poster.py's session/facet/posting plumbing — only the
digest-specific parsing and post composition differ, since OpEd pieces
live in digests/opinion/{slug}_{date}.md rather than a per-country digest.
"""

import argparse
import glob
import logging
import os
import re
import sys
from datetime import date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, REPO_ROOT)

from publishing.bluesky_poster import (  # noqa: E402
    POST_MAX_CHARS,
    SITE_BASE_URL,
    fit_teaser,
    post_to_bluesky,
    split_sentences,
)

OPED_DIR = os.path.join(REPO_ROOT, "digests", "opinion")


def find_oped_file(date_str: str) -> tuple[str, str]:
    """Return (slug, path) for the single OpEd published on date_str.

    Raises if zero or more than one file matches — either is a pipeline
    error (nothing scheduled that day, or an ambiguous duplicate) that
    should stop the post rather than guess.
    """
    matches = sorted(glob.glob(os.path.join(OPED_DIR, f"*_{date_str}.md")))
    if not matches:
        raise FileNotFoundError(f"No OpEd file found for {date_str} in {OPED_DIR}")
    if len(matches) > 1:
        raise ValueError(f"Multiple OpEd files found for {date_str}: {matches!r} — ambiguous")

    path = matches[0]
    filename = os.path.basename(path)
    slug = filename[: -(len(date_str) + len(".md") + 1)]  # strip "_{date}.md"
    return slug, path


def parse_oped(path: str) -> tuple[str, str, str, list[str]]:
    """Extract PERSONA, LENS, TITLE metadata and the body's sentences from an OpEd file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"OpEd file not found: {path}")

    with open(path, encoding="utf-8") as f:
        content = f.read()

    persona_match = re.search(r"^>\s*PERSONA:\s*(.+)$", content, re.MULTILINE)
    lens_match = re.search(r"^>\s*LENS:\s*(.+)$", content, re.MULTILINE)
    # Same lazy-[\s\S]+?-with-lookahead technique used elsewhere for this file
    # format: TITLE and DATE sit back-to-back with no blank line between, so
    # the lookahead must stop at the next "> FIELD:" line, not just a blank line.
    title_match = re.search(r"^>\s*TITLE:\s*([\s\S]+?)(?=\n>\s*[A-Z_]+:|\n\s*\n)", content, re.MULTILINE)

    if not persona_match or not title_match:
        raise ValueError(f"Missing PERSONA or TITLE metadata in {path}")

    persona_name = persona_match.group(1).strip()
    lens_short = lens_match.group(1).strip() if lens_match else ""
    title = re.sub(r"\s+", " ", title_match.group(1)).strip()

    # Strip the leading "> FIELD: ..." metadata block and the trailing bio
    # disclosure block (same format save_oped() in oped_builder.py writes).
    lines = content.split("\n")
    i = 0
    while i < len(lines) and lines[i].startswith(">"):
        i += 1
    if i < len(lines) and lines[i].strip() == "":
        i += 1
    body = "\n".join(lines[i:]).split("\n---\n")[0]

    body_lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    body_text = " ".join(body_lines)

    sentences = split_sentences(body_text)
    if not sentences:
        raise ValueError(f"No body text found in {path}")

    return persona_name, lens_short, title, sentences


def post_url(slug: str, date_str: str) -> str:
    return f"{SITE_BASE_URL}/opinion/{slug}/{date_str}"


def compose_post(persona_name: str, title: str, sentences: list[str], url: str) -> str:
    """Compose the post text. The header (opinion marker + byline + headline) is
    never truncated — if space is tight, the teaser is shortened (down to
    omitted entirely) instead, same policy as the news digest poster."""
    header = f"🗣️ OPINION — {persona_name}: {title}"
    footer = f"💬 {url}"

    header_and_footer = f"{header}\n\n{footer}"
    if len(header_and_footer) > POST_MAX_CHARS:
        raise ValueError(
            f"Header + URL alone are {len(header_and_footer)} chars, exceeding {POST_MAX_CHARS} "
            f"— cannot compose a post without truncating the header"
        )

    fixed_len = len(header) + 2 + 2 + len(footer)
    available = POST_MAX_CHARS - fixed_len
    teaser = fit_teaser(sentences, available)

    if not teaser:
        return header_and_footer
    return f"{header}\n\n{teaser}\n\n{footer}"


def run(date_str: str, dry_run: bool) -> None:
    slug, path = find_oped_file(date_str)
    persona_name, lens_short, title, sentences = parse_oped(path)
    url = post_url(slug, date_str)
    post_text = compose_post(persona_name, title, sentences, url)

    if len(post_text) > POST_MAX_CHARS:
        raise ValueError(f"Composed post is {len(post_text)} chars, exceeds {POST_MAX_CHARS}")

    if dry_run:
        header = f"🗣️ OPINION — {persona_name}: {title}"
        footer = f"💬 {url}"
        available = POST_MAX_CHARS - (len(header) + 2 + 2 + len(footer))
        teaser = fit_teaser(sentences, available)
        spacing = 4 if teaser else 2

        print(f"=== DRY RUN — OpEd {slug} {date_str} ({len(post_text)} chars) ===")
        print(post_text)
        print("--- breakdown ---")
        print(f"columnist: {persona_name} ({lens_short})")
        print(f"header:  {len(header)} chars (opinion marker + byline + headline)")
        print(f"teaser:  {len(teaser)} chars")
        print(f"footer:  {len(footer)} chars (emoji + space + url)")
        print(f"spacing: {spacing} chars ({spacing // 2} blank-line separator{'s' if spacing == 4 else ''})")
        print(f"total:   {len(post_text)} / {POST_MAX_CHARS} chars")
        print("=== END ===")
        return

    posted_url = post_to_bluesky(post_text, url)
    logger.info(f"[opinion/{slug}] Posted successfully: {posted_url}")
    print(f"Posted: {posted_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post a published OpEd piece's teaser to Bluesky.")
    parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD, defaults to today")
    parser.add_argument("--dry-run", action="store_true", help="Compose and print the post without posting")
    args = parser.parse_args()

    try:
        run(args.date, args.dry_run)
    except Exception as exc:
        logger.error(f"Failed to post OpEd for {args.date}: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
