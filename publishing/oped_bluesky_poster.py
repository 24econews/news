"""Post the day's published OpEd piece(s) teaser to Bluesky.

Reuses bluesky_poster.py's session/facet/posting plumbing — only the
digest-specific parsing and post composition differ, since OpEd pieces
live in digests/opinion/{slug}_{date}.md rather than a per-country digest.

Usually there's exactly one OpEd per date, but more than one is legitimate
(e.g. a date-gated launch piece whose reveal date coincides with that day's
regular rotation pick) — all matches are posted, staggered STAGGER_SECONDS
apart, same pattern as post_all_countries_bluesky.py uses for digests.
"""

import argparse
import glob
import json
import logging
import os
import re
import sys
import time
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
from generation.slugify import build_opinion_url  # noqa: E402
from generation.oped_personas import PERSONAS_BY_SLUG  # noqa: E402

OPED_DIR = os.path.join(REPO_ROOT, "digests", "opinion")
SPECIAL_MANIFEST_DIR = os.path.join(REPO_ROOT, "digests", "special")
STAGGER_SECONDS = 1800


def find_oped_files(date_str: str) -> list[tuple[str, str]]:
    """Return [(slug, path), ...] for every OpEd published on date_str, sorted by slug.

    More than one match is legitimate — e.g. a date-gated launch piece whose
    reveal date happens to land on the same day as that day's regular
    rotation-selected piece — so all matches are posted (see run()), not
    treated as an ambiguity error. Only zero matches is a pipeline error
    (nothing scheduled that day).
    """
    matches = sorted(glob.glob(os.path.join(OPED_DIR, f"*_{date_str}.md")))
    if not matches:
        raise FileNotFoundError(f"No OpEd file found for {date_str} in {OPED_DIR}")

    results = []
    for path in matches:
        filename = os.path.basename(path)
        slug = filename[: -(len(date_str) + len(".md") + 1)]  # strip "_{date}.md"
        results.append((slug, path))
    return results


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
    # rsplit on the LAST "\n---\n" — Sonnet sometimes uses "---" as a stylistic
    # mid-piece divider, and the bio-block separator save_oped() appends is
    # always the final one, so splitting on the first occurrence would
    # truncate the body (and its teaser) at that internal divider instead.
    body = "\n".join(lines[i:]).rsplit("\n---\n", 1)[0]

    body_lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    body_text = " ".join(body_lines)

    sentences = split_sentences(body_text)
    if not sentences:
        raise ValueError(f"No body text found in {path}")

    return persona_name, lens_short, title, sentences


def load_special_basenames() -> set[str]:
    """Return the basenames of every opinion file listed in any
    digests/special/*.json manifest — pieces that belong to a special
    edition (see special_editions.py) the editor pushes out deliberately as
    a batch, not the daily rotation pick this poster normally handles.
    Posting all 8 automatically, staggered 30 minutes apart like a normal
    day's single piece, is exactly the mishandling this skip exists to stop.
    """
    basenames = set()
    if not os.path.isdir(SPECIAL_MANIFEST_DIR):
        return basenames
    for manifest_path in glob.glob(os.path.join(SPECIAL_MANIFEST_DIR, "*.json")):
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        for piece in manifest.get("pieces", []):
            basenames.add(os.path.basename(piece["path"]))
    return basenames


def post_url(slug: str, date_str: str, title: str) -> str:
    return f"{SITE_BASE_URL}{build_opinion_url(slug, date_str, title)}"


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


def post_one(slug: str, path: str, date_str: str, dry_run: bool) -> None:
    persona_name, lens_short, title, sentences = parse_oped(path)
    url = post_url(slug, date_str, title)
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


def run(date_str: str, dry_run: bool, include_special: bool, persona_slug: str | None) -> None:
    if persona_slug and not include_special:
        raise ValueError("--persona only applies together with --include-special.")

    opeds = find_oped_files(date_str)
    special_basenames = load_special_basenames()

    if include_special:
        if not persona_slug:
            raise ValueError("--include-special requires --persona <slug> to pick exactly one piece from the special edition.")
        opeds = [(slug, path) for slug, path in opeds if slug == persona_slug]
        if not opeds:
            raise FileNotFoundError(f"No OpEd file found for {date_str} matching --persona {persona_slug!r}")
    else:
        eligible = [(slug, path) for slug, path in opeds if os.path.basename(path) not in special_basenames]
        skipped = len(opeds) - len(eligible)
        if skipped:
            logger.info(
                f"Skipping {skipped} special-edition piece(s) for {date_str} — they're part of a "
                "digests/special/*.json manifest; rerun with --include-special --persona <slug> to post one deliberately."
            )
        opeds = eligible
        if not opeds:
            raise FileNotFoundError(
                f"No eligible OpEd file found for {date_str} in {OPED_DIR} — all matches are part of a "
                "special edition (use --include-special --persona <slug> to post one)."
            )

    if len(opeds) > 1:
        slugs = ", ".join(slug for slug, _ in opeds)
        logger.info(
            f"Found {len(opeds)} OpEd pieces for {date_str} ({slugs}) — "
            f"posting all, staggered {STAGGER_SECONDS}s apart"
        )

    failed = []
    for i, (slug, path) in enumerate(opeds):
        try:
            post_one(slug, path, date_str, dry_run)
        except Exception as exc:
            logger.error(f"[opinion/{slug}] Failed to post: {exc}")
            print(f"ERROR: [opinion/{slug}] {exc}", file=sys.stderr)
            failed.append(slug)

        is_last = i == len(opeds) - 1
        if not is_last and not dry_run:
            logger.info(f"Waiting {STAGGER_SECONDS}s before next OpEd post…")
            time.sleep(STAGGER_SECONDS)

    if failed:
        raise RuntimeError(f"Failed to post {len(failed)}/{len(opeds)} OpEd piece(s): {', '.join(failed)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post a published OpEd piece's teaser to Bluesky.")
    parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD, defaults to today")
    parser.add_argument("--dry-run", action="store_true", help="Compose and print the post without posting")
    parser.add_argument(
        "--include-special", action="store_true",
        help="Allow posting a piece that's part of a digests/special/*.json manifest — requires --persona to pick exactly one",
    )
    parser.add_argument(
        "--persona", default=None, choices=sorted(PERSONAS_BY_SLUG),
        help="Required with --include-special: which persona's piece to post",
    )
    args = parser.parse_args()

    try:
        run(args.date, args.dry_run, args.include_special, args.persona)
    except Exception as exc:
        logger.error(f"Failed to post OpEd for {args.date}: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
