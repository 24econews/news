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

# Static, non-AI-generated block appended to every send.
#
# NOTE: {{ subscribe_form }} does NOT work here — per Buttondown's docs
# (docs.buttondown.com/template-variables-subscribe-form), that tag only renders
# on the web/archive version of an email; it is silently dropped from the actual
# email delivered to inboxes. {{ subscribe_url }} is the tag that does render in
# delivered emails, so it's used here as a markdown link — the same pattern
# Buttondown's own docs use for this exact "forwarded email" scenario
# (docs.buttondown.com/template-variables-subscribe-url).
SUBSCRIBE_BLOCK = (
    "---\n"
    "\n"
    "*Was this briefing forwarded to you? [Subscribe here]({{ subscribe_url }}) "
    "to get the Mercosur Weekly Briefing in your inbox every Friday.*"
)


def append_subscribe_block(body: str) -> str:
    return f"{body.rstrip()}\n\n{SUBSCRIBE_BLOCK}"


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


def create_email(subject: str, body: str, api_key: str, status: str) -> dict:
    """Create an email via the Buttondown API with the given status.

    status="draft" creates the email in the dashboard WITHOUT sending it to any
    subscriber — this is the only status this function should ever be called
    with unless a live send has been explicitly confirmed by the caller.
    status="about_to_send" queues a real send to every subscriber.
    """
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
    }
    if status == "about_to_send":
        # Required to actually queue a live send — Buttondown returns a
        # sending_requires_confirmation 400 without it, as a safeguard against
        # accidental sends. See https://buttondown.com/blog/safer-email-api-defaults
        headers["X-Buttondown-Live-Dangerously"] = "true"

    response = requests.post(
        BUTTONDOWN_EMAILS_URL,
        headers=headers,
        json={
            "subject": subject,
            "body": body,
            "status": status,
        },
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Buttondown API error {response.status_code}: {response.text}")
    return response.json()


def run(week_arg: str | None, dry_run: bool, test_send: bool, confirm_live_send: bool) -> None:
    if test_send and confirm_live_send:
        raise ValueError("--test-send and --confirm-live-send are mutually exclusive — pick one.")

    thursday = thursday_of_week(week_arg)
    path = briefing_path(thursday)

    logger.info(f"Reading weekly briefing: {path}")
    subject, greeting, body = parse_briefing(path)
    body = append_subscribe_block(body)

    if dry_run:
        print("=== DRY RUN ===")
        print(f"Subject: {subject}")
        print(f"Greeting/preview teaser: {greeting}")
        print(f"\nBody preview (first 200 chars):\n{body[:200]}")
        print(f"\nBody end (last 500 chars):\n{body[-500:]}")
        print("\nDRY RUN — no email sent, no API call made")
        return

    load_dotenv()
    api_key = os.getenv("BUTTONDOWN_API_KEY")
    if not api_key:
        raise EnvironmentError("BUTTONDOWN_API_KEY is not set. Add it to your .env file or environment.")

    if confirm_live_send:
        logger.warning("LIVE SEND confirmed via --confirm-live-send — queuing email to all subscribers…")
        result = create_email(subject, body, api_key, status="about_to_send")
        print("Newsletter QUEUED FOR LIVE SEND to all subscribers.")
        print(result)
        return

    # Safe path — always draft, regardless of --test-send. The only difference
    # is the message, since --test-send is an intentional test and a bare
    # invocation without --confirm-live-send is (implicitly) a caller who
    # stopped short of confirming a live send.
    result = create_email(subject, body, api_key, status="draft")
    if test_send:
        print("Draft created — check your Buttondown dashboard to review before manually "
              "sending, if desired. NO EMAIL WAS SENT to subscribers.")
    else:
        print("WARNING: --confirm-live-send was not passed, so no live send was performed.")
        print("A draft was created instead as a safe default. NO EMAIL WAS SENT to subscribers.")
        print("To actually send to subscribers, re-run with --confirm-live-send.")
    print(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send the Mercosur Weekly Briefing via Buttondown.")
    parser.add_argument("--week", default=None, help="Monday (YYYY-MM-DD) of the week to send; defaults to this week")
    parser.add_argument("--dry-run", action="store_true", help="Preview the email without calling the Buttondown API")
    parser.add_argument(
        "--test-send", action="store_true",
        help="Create the email as a Buttondown draft (status=draft) via the real API call, "
             "without sending it to any subscriber. Safe to use at any time.",
    )
    parser.add_argument(
        "--confirm-live-send", action="store_true",
        help="Required to actually queue a real send (status=about_to_send) to every subscriber. "
             "Without this flag, the script always falls back to creating a draft.",
    )
    args = parser.parse_args()

    try:
        run(args.week, args.dry_run, args.test_send, args.confirm_live_send)
    except Exception as exc:
        logger.error(f"Newsletter send failed: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
