"""Post a country's daily digest teaser to Bluesky."""

import argparse
import logging
import os
import re
import sys
from datetime import date, datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from generation.slugify import build_digest_url  # noqa: E402

POST_MAX_CHARS = 300
SITE_BASE_URL = "https://24econews.com"
BLUESKY_API_BASE = "https://bsky.social/xrpc"

COUNTRY_OUTPUT_DIRS = {
    "argentina": "digests/",
    "brazil": "digests/brazil/",
    "chile": "digests/chile/",
    "uruguay": "digests/uruguay/",
    "paraguay": "digests/paraguay/",
    "bolivia": "digests/bolivia/",
}

FLAGS = {
    "argentina": "🇦🇷",
    "brazil": "🇧🇷",
    "chile": "🇨🇱",
    "uruguay": "🇺🇾",
    "paraguay": "🇵🇾",
    "bolivia": "🇧🇴",
}


def digest_path(country: str, date_str: str) -> str:
    if country not in COUNTRY_OUTPUT_DIRS:
        raise ValueError(f"Unknown country: {country!r}. Expected one of {sorted(COUNTRY_OUTPUT_DIRS)}")
    output_dir = COUNTRY_OUTPUT_DIRS[country]
    filename = f"digest_{date_str}.en.md"
    return os.path.join(REPO_ROOT, output_dir, filename)


def split_sentences(text: str) -> list[str]:
    """Split body text into sentences, guarding against common abbreviations."""
    placeholder = "<<DOT>>"
    protected = text.replace("U.S.", "U" + placeholder + "S" + placeholder)
    protected = protected.replace("U.K.", "U" + placeholder + "K" + placeholder)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", protected)
    return [p.replace(placeholder, ".").strip() for p in parts if p.strip()]


def parse_digest(path: str) -> tuple[str, list[str]]:
    """Extract the TITLE metadata and the narrative body's sentences from a digest file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Digest file not found: {path}")

    with open(path, encoding="utf-8") as f:
        content = f.read()

    # DOTALL + a "blank line" lookahead (rather than plain `$`) so a TITLE value
    # that got word-wrapped onto a following line (no leading "> ") is still
    # captured in full instead of silently cut at the first newline.
    title_match = re.search(r"^>\s*TITLE:\s*(.+?)(?=\n\s*\n|\Z)", content, re.MULTILINE | re.DOTALL)
    if not title_match:
        raise ValueError(f"No TITLE metadata found in {path}")
    title = re.sub(r"\s+", " ", title_match.group(1)).strip()

    heading_match = re.search(r"^#\s+.+$", content, re.MULTILINE)
    if not heading_match:
        raise ValueError(f"No heading line found in {path}")

    body = content[heading_match.end():]
    body = body.split("\n---")[0]

    lines = [
        ln.strip()
        for ln in body.splitlines()
        if ln.strip() and not ln.strip().startswith("*") and not ln.strip().startswith("#")
    ]
    body_text = " ".join(lines)

    sentences = split_sentences(body_text)
    if not sentences:
        raise ValueError(f"No narrative body found in {path}")

    return title, sentences


def fit_teaser(sentences: list[str], available_chars: int) -> str:
    """Take the first 2-3 sentences, truncating cleanly at a sentence boundary if needed.

    Returns "" if there isn't room for even a truncated excerpt — callers should
    omit the teaser paragraph entirely in that case rather than force something in.
    """
    if available_chars <= 0:
        return ""

    candidate_sentences = sentences[:3]
    full = " ".join(candidate_sentences)
    if len(full) <= available_chars:
        return full

    for n in range(len(candidate_sentences) - 1, 0, -1):
        candidate = " ".join(candidate_sentences[:n])
        if len(candidate) + 1 <= available_chars:
            return candidate + "…"

    single = candidate_sentences[0]
    if available_chars <= 1:
        return "…"
    truncated = single[: available_chars - 1].rsplit(" ", 1)[0]
    return truncated + "…"


def post_url(country: str, date_str: str, title: str) -> str:
    return f"{SITE_BASE_URL}{build_digest_url(country, date_str, title)}"


def compose_post(country: str, date_str: str, title: str, sentences: list[str]) -> str:
    """Compose the post text. The title is never truncated — if space is tight,
    the teaser is shortened (down to omitted entirely) instead."""
    flag = FLAGS[country]
    url = post_url(country, date_str, title)
    header = f"{flag} {title}"
    footer = f"📰 {url}"

    header_and_footer = f"{header}\n\n{footer}"
    if len(header_and_footer) > POST_MAX_CHARS:
        raise ValueError(
            f"Title + URL alone are {len(header_and_footer)} chars, exceeding {POST_MAX_CHARS} "
            f"for {country} {date_str} — cannot compose a post without truncating the title"
        )

    fixed_len = len(header) + 2 + 2 + len(footer)
    available = POST_MAX_CHARS - fixed_len
    teaser = fit_teaser(sentences, available)

    if not teaser:
        return header_and_footer
    return f"{header}\n\n{teaser}\n\n{footer}"


def build_facets(post_text: str, url: str) -> list[dict]:
    """Build an AT Protocol facets array marking `url`'s UTF-8 byte range as a link.

    Bluesky does not auto-linkify plain URL text — the byte offsets must be
    computed from the UTF-8 encoding, not character offsets, since emoji and
    other multi-byte characters earlier in the text would otherwise throw
    off the link's position.
    """
    idx = post_text.index(url)
    prefix_bytes = len(post_text[:idx].encode("utf-8"))
    url_bytes = len(url.encode("utf-8"))
    return [
        {
            "index": {"byteStart": prefix_bytes, "byteEnd": prefix_bytes + url_bytes},
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}],
        }
    ]


def create_session(handle: str, app_password: str) -> str:
    import requests

    response = requests.post(
        f"{BLUESKY_API_BASE}/com.atproto.server.createSession",
        json={"identifier": handle, "password": app_password},
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(
            f"Bluesky authentication failed ({response.status_code}): {response.text}"
        )
    data = response.json()
    access_jwt = data.get("accessJwt")
    if not access_jwt:
        raise RuntimeError("Bluesky authentication response did not include an accessJwt")
    return access_jwt


def post_to_bluesky(post_text: str, url: str) -> str:
    import requests

    handle = os.getenv("BLUESKY_HANDLE")
    app_password = os.getenv("BLUESKY_APP_PASSWORD")

    missing = [
        name
        for name, val in [
            ("BLUESKY_HANDLE", handle),
            ("BLUESKY_APP_PASSWORD", app_password),
        ]
        if not val
    ]
    if missing:
        raise EnvironmentError(f"Missing required environment variable(s): {', '.join(missing)}")

    access_jwt = create_session(handle, app_password)
    facets = build_facets(post_text, url)

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    response = requests.post(
        f"{BLUESKY_API_BASE}/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {access_jwt}"},
        json={
            "repo": handle,
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": post_text,
                "createdAt": created_at,
                "facets": facets,
            },
        },
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(
            f"Bluesky post failed ({response.status_code}): {response.text}"
        )

    data = response.json()
    uri = data.get("uri", "")
    # uri looks like at://did:plc:xxxx/app.bsky.feed.post/yyyy
    post_id = uri.rsplit("/", 1)[-1] if uri else ""
    handle_for_url = handle.lstrip("@")
    return f"https://bsky.app/profile/{handle_for_url}/post/{post_id}" if post_id else uri


def run(country: str, date_str: str, dry_run: bool) -> None:
    path = digest_path(country, date_str)
    title, sentences = parse_digest(path)
    post_text = compose_post(country, date_str, title, sentences)
    url = post_url(country, date_str, title)

    if len(post_text) > POST_MAX_CHARS:
        raise ValueError(
            f"Composed post for {country} is {len(post_text)} chars, exceeds {POST_MAX_CHARS}"
        )

    if dry_run:
        flag = FLAGS[country]
        header = f"{flag} {title}"
        footer = f"📰 {url}"
        available = POST_MAX_CHARS - (len(header) + 2 + 2 + len(footer))
        teaser = fit_teaser(sentences, available)
        spacing = 4 if teaser else 2  # one or two "\n\n" separators

        print(f"=== DRY RUN — {country} {date_str} ({len(post_text)} chars) ===")
        print(post_text)
        print("--- breakdown ---")
        print(f"title:   {len(title)} chars")
        print(f"header:  {len(header)} chars (flag + space + title)")
        print(f"teaser:  {len(teaser)} chars")
        print(f"footer:  {len(footer)} chars (emoji + space + url)")
        print(f"spacing: {spacing} chars ({spacing // 2} blank-line separator{'s' if spacing == 4 else ''})")
        print(f"total:   {len(post_text)} / {POST_MAX_CHARS} chars")
        print("=== END ===")
        return

    posted_url = post_to_bluesky(post_text, url)
    logger.info(f"[{country}] Posted successfully: {posted_url}")
    print(f"Posted: {posted_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post a country's daily digest to Bluesky.")
    parser.add_argument("--country", required=True, choices=sorted(COUNTRY_OUTPUT_DIRS))
    parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD, defaults to today")
    parser.add_argument("--dry-run", action="store_true", help="Compose and print the post without posting")
    args = parser.parse_args()

    try:
        run(args.country, args.date, args.dry_run)
    except Exception as exc:
        logger.error(f"[{args.country}] Failed to post: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
