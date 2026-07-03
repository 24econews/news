"""Post a country's daily digest teaser to X (Twitter)."""

import argparse
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

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TWEET_MAX_CHARS = 280
SITE_BASE_URL = "https://24econews.com"

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

    title_match = re.search(r"^>\s*TITLE:\s*(.+)$", content, re.MULTILINE)
    if not title_match:
        raise ValueError(f"No TITLE metadata found in {path}")
    title = title_match.group(1).strip()

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
    """Take the first 2-3 sentences, truncating cleanly at a sentence boundary if needed."""
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


def compose_tweet(country: str, date_str: str, title: str, sentences: list[str]) -> str:
    flag = FLAGS[country]
    url = f"{SITE_BASE_URL}/{country}/{date_str}"
    header = f"{flag} {title}"
    footer = f"📰 {url}"

    fixed_len = len(header) + 2 + 2 + len(footer)
    available = TWEET_MAX_CHARS - fixed_len
    if available < 0:
        raise ValueError(
            f"Title + URL alone exceed {TWEET_MAX_CHARS} characters for {country} {date_str}"
        )

    teaser = fit_teaser(sentences, available)
    return f"{header}\n\n{teaser}\n\n{footer}"


def post_tweet(tweet_text: str) -> str:
    import tweepy

    api_key = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

    missing = [
        name
        for name, val in [
            ("X_API_KEY", api_key),
            ("X_API_SECRET", api_secret),
            ("X_ACCESS_TOKEN", access_token),
            ("X_ACCESS_TOKEN_SECRET", access_token_secret),
        ]
        if not val
    ]
    if missing:
        raise EnvironmentError(f"Missing required environment variable(s): {', '.join(missing)}")

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )

    response = client.create_tweet(text=tweet_text)
    tweet_id = response.data["id"]
    return f"https://x.com/i/web/status/{tweet_id}"


def run(country: str, date_str: str, dry_run: bool) -> None:
    path = digest_path(country, date_str)
    title, sentences = parse_digest(path)
    tweet_text = compose_tweet(country, date_str, title, sentences)

    if len(tweet_text) > TWEET_MAX_CHARS:
        raise ValueError(
            f"Composed tweet for {country} is {len(tweet_text)} chars, exceeds {TWEET_MAX_CHARS}"
        )

    if dry_run:
        print(f"=== DRY RUN — {country} {date_str} ({len(tweet_text)} chars) ===")
        print(tweet_text)
        print("=== END ===")
        return

    tweet_url = post_tweet(tweet_text)
    logger.info(f"[{country}] Posted successfully: {tweet_url}")
    print(f"Posted: {tweet_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post a country's daily digest to X.")
    parser.add_argument("--country", required=True, choices=sorted(COUNTRY_OUTPUT_DIRS))
    parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD, defaults to today")
    parser.add_argument("--dry-run", action="store_true", help="Compose and print the tweet without posting")
    args = parser.parse_args()

    try:
        run(args.country, args.date, args.dry_run)
    except Exception as exc:
        logger.error(f"[{args.country}] Failed to post: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
