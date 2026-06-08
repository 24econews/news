#!/usr/bin/env python3
"""Backfill Unsplash hero images into existing digest .md files."""

import glob
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(REPO_ROOT, ".env"))

from processing.image_fetcher import fetch_hero_image

DIGEST_DIRS = [
    os.path.join(REPO_ROOT, "digests"),
    os.path.join(REPO_ROOT, "digests", "brazil"),
    os.path.join(REPO_ROOT, "digests", "chile"),
    os.path.join(REPO_ROOT, "digests", "uruguay"),
    os.path.join(REPO_ROOT, "digests", "paraguay"),
    os.path.join(REPO_ROOT, "digests", "bolivia"),
]

_COUNTRY_RE = re.compile(r"digests/([^/]+)/digest_")


def detect_country(filepath: str) -> str:
    m = _COUNTRY_RE.search(filepath.replace(os.sep, "/"))
    return m.group(1) if m else "argentina"


def has_image(content: str) -> bool:
    return any(line.startswith("> IMAGE_URL:") for line in content.splitlines()[:8])


def extract_title(content: str) -> str | None:
    for line in content.splitlines()[:8]:
        if line.startswith("> TITLE:"):
            return line[len("> TITLE:"):].strip()
    return None


def prepend_image(filepath: str, img: dict) -> None:
    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()
    block = (
        f"> IMAGE_URL: {img['url']}\n"
        f"> IMAGE_THUMB: {img['thumb']}\n"
        f"> IMAGE_CREDIT: {img['photographer']}\n"
        f"> IMAGE_CREDIT_URL: {img['photographer_url']}\n"
    )
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(block + original)


def main() -> None:
    md_files = []
    for d in DIGEST_DIRS:
        md_files.extend(sorted(glob.glob(os.path.join(d, "digest_*.md"))))
    md_files = [f for f in md_files if not f.endswith(".en.md")]

    print(f"Found {len(md_files)} digest files to check.")

    skipped = updated = failed = 0

    for filepath in md_files:
        filename = os.path.basename(filepath)
        country = detect_country(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if has_image(content):
            print(f"  skip {country}/{filename} (already has image)")
            skipped += 1
            continue

        title = extract_title(content)
        if not title:
            print(f"  skip {country}/{filename} (no title found)")
            skipped += 1
            continue

        img = fetch_hero_image(title, country)
        if not img:
            print(f"  FAIL {country}/{filename} (no image returned)")
            failed += 1
            continue

        prepend_image(filepath, img)
        print(f"  ok   {country}/{filename}: {img['photographer']} — {img['url'][:60]}…")
        updated += 1

    print(f"\nDone. {updated} updated, {skipped} skipped, {failed} failed.")


if __name__ == "__main__":
    main()
