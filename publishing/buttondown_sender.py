"""Send the Mercosur Weekly Briefing as a newsletter via Buttondown."""

import argparse
import logging
import os
import re
import sys
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEEKLY_BRIEFING_DIR = os.path.join(REPO_ROOT, "digests", "weekly")

BUTTONDOWN_EMAILS_URL = "https://api.buttondown.com/v1/emails"


def thursday_of_week(week_arg: str | None) -> date:
    """--week takes the Monday (YYYY-MM-DD) of the target week; returns that week's Thursday."""
    if week_arg:
        monday = date.fromisoformat(week_arg)
        if monday.weekday() != 0:
            raise ValueError(f"--week must be a Monday (YYYY-MM-DD); {week_arg} is a {monday.strftime('%A')}")
    else:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
    return monday + timedelta(days=3)


def briefing_path(thursday: date) -> str:
    return os.path.join(WEEKLY_BRIEFING_DIR, f"briefing_{thursday.isoformat()}.md")


def parse_briefing(path: str) -> tuple[str, str, str]:
    """Return (subject, greeting_teaser, body) parsed from a weekly briefing file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Weekly briefing file not found: {path}")

    with open(path, encoding="utf-8") as f:
        content = f.read()

    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if not title_match:
        raise ValueError(f"No title line (# ...) found in {path}")

    subject = title_match.group(1).strip()
    greeting = content[: title_match.start()].strip()

    body = content[: title_match.start()] + content[title_match.end() :]
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    return subject, greeting, body


def send_newsletter(subject: str, body: str, api_key: str) -> dict:
    response = requests.post(
        BUTTONDOWN_EMAILS_URL,
        headers={
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "subject": subject,
            "body": body,
            "status": "about_to_send",
        },
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Buttondown API error {response.status_code}: {response.text}")
    return response.json()


def run(week_arg: str | None, dry_run: bool) -> None:
    thursday = thursday_of_week(week_arg)
    path = briefing_path(thursday)

    logger.info(f"Reading weekly briefing: {path}")
    subject, greeting, body = parse_briefing(path)

    if dry_run:
        print("=== DRY RUN ===")
        print(f"Subject: {subject}")
        print(f"Greeting/preview teaser: {greeting}")
        print(f"\nBody preview (first 200 chars):\n{body[:200]}")
        print("\nDRY RUN — no email sent")
        return

    load_dotenv()
    api_key = os.getenv("BUTTONDOWN_API_KEY")
    if not api_key:
        raise EnvironmentError("BUTTONDOWN_API_KEY is not set. Add it to your .env file or environment.")

    logger.info("Sending newsletter via Buttondown…")
    result = send_newsletter(subject, body, api_key)
    print("Newsletter sent successfully.")
    print(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send the Mercosur Weekly Briefing via Buttondown.")
    parser.add_argument("--week", default=None, help="Monday (YYYY-MM-DD) of the week to send; defaults to this week")
    parser.add_argument("--dry-run", action="store_true", help="Preview the email without calling the Buttondown API")
    args = parser.parse_args()

    try:
        run(args.week, args.dry_run)
    except Exception as exc:
        logger.error(f"Newsletter send failed: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
