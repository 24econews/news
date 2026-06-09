"""Run the daily digest pipeline for every active country."""

import argparse
import logging
import os
import subprocess
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

COUNTRIES = ["argentina", "brazil", "chile", "uruguay", "paraguay", "bolivia"]

PIPELINE = os.path.join(SCRIPT_DIR, "daily_pipeline.py")


def run_country(country: str) -> bool:
    """Return True on success, False on failure."""
    start_t = __import__("datetime").datetime.now()
    logger.info(f"[{country}] Starting pipeline…")
    try:
        subprocess.run(
            [sys.executable, PIPELINE, "--country", country],
            check=True,
        )
        elapsed = int((__import__("datetime").datetime.now() - start_t).total_seconds())
        logger.info(f"[{country}] Completed in {elapsed}s")
        return True
    except subprocess.CalledProcessError as exc:
        elapsed = int((__import__("datetime").datetime.now() - start_t).total_seconds())
        logger.error(f"[{country}] Pipeline failed after {elapsed}s: {exc}")
        return False


def run_cross_linking() -> None:
    """Find cross-country story connections and inject them into today's digests."""
    import anthropic
    from dotenv import load_dotenv

    sys.path.insert(0, REPO_ROOT)
    from processing.cross_linker import cross_link_digests

    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set")

    client = anthropic.Anthropic(api_key=api_key)
    today = date.today().isoformat()

    logger.info("=== Cross-linking started ===")
    result = cross_link_digests(
        date=today,
        countries=COUNTRIES,
        digests_base_dir=REPO_ROOT,
        client=client,
    )
    n_conn = result.get("connections", 0)
    n_countries = len(result.get("countries", []))
    logger.info(f"Cross-linking complete: {n_conn} connection(s) found across {n_countries} country/ies")
    if result.get("events"):
        for event in result["events"]:
            logger.info(f"  • {event}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all country pipelines, then cross-link.")
    parser.add_argument(
        "--cross-link-only",
        action="store_true",
        help="Skip country pipelines — only run the cross-linking step",
    )
    args = parser.parse_args()

    if args.cross_link_only:
        try:
            run_cross_linking()
        except Exception as exc:
            logger.error(f"Cross-linking failed: {exc}")
            sys.exit(1)
    else:
        logger.info("=== run_all_countries started ===")
        for country in COUNTRIES:
            run_country(country)
        logger.info("=== All country pipelines finished ===")

        try:
            run_cross_linking()
        except Exception as exc:
            logger.error(f"Cross-linking failed (non-fatal): {exc}")

        logger.info("=== run_all_countries finished ===")
