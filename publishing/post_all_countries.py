"""Post all countries' daily digests to X, staggered 30 minutes apart."""

import argparse
import logging
import os
import subprocess
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
X_POSTER = os.path.join(SCRIPT_DIR, "x_poster.py")

POST_ORDER = ["brazil", "argentina", "chile", "uruguay", "paraguay", "bolivia"]
STAGGER_SECONDS = 1800


def post_country(country: str, date_str: str, dry_run: bool) -> bool:
    """Return True on success, False on failure."""
    cmd = [sys.executable, X_POSTER, "--country", country, "--date", date_str]
    if dry_run:
        cmd.append("--dry-run")

    logger.info(f"[{country}] Posting digest for {date_str}…")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout, end="")
        logger.info(f"[{country}] Success")
        return True
    except subprocess.CalledProcessError as exc:
        if exc.stdout:
            print(exc.stdout, end="")
        if exc.stderr:
            print(exc.stderr, end="", file=sys.stderr)
        logger.error(f"[{country}] Failed: {exc}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post all countries' digests to X, staggered 30 minutes apart.")
    parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD, defaults to today")
    parser.add_argument("--dry-run", action="store_true", help="Compose and print tweets without posting or waiting")
    args = parser.parse_args()

    logger.info(f"=== post_all_countries started for {args.date} ===")

    results = {}
    for i, country in enumerate(POST_ORDER):
        results[country] = post_country(country, args.date, args.dry_run)

        is_last = i == len(POST_ORDER) - 1
        if not is_last and not args.dry_run:
            logger.info(f"Waiting {STAGGER_SECONDS}s before next post…")
            time.sleep(STAGGER_SECONDS)

    succeeded = [c for c, ok in results.items() if ok]
    failed = [c for c, ok in results.items() if not ok]

    logger.info(f"=== post_all_countries finished: {len(succeeded)} succeeded, {len(failed)} failed ===")
    if succeeded:
        logger.info(f"Succeeded: {', '.join(succeeded)}")
    if failed:
        logger.error(f"Failed: {', '.join(failed)}")
