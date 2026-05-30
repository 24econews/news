"""Orchestrate the full daily pipeline and optionally schedule it."""

import logging
import os
import sys
from datetime import date, datetime

import anthropic
import schedule
import time
import yaml
from dotenv import load_dotenv

# Make project root importable when running this file directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.storage import init_db, get_known_urls, save_articles, save_summary
from generation.digest_builder import build_digest
from ingestion.rss_fetcher import fetch_all_feeds
from processing.relevance_filter import filter_articles
from processing.summarizer import summarize_articles
from publishing.publisher import publish_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_pipeline() -> None:
    """Execute the full pipeline: fetch → filter → summarize → store → publish."""
    logger.info("=== Pipeline started ===")
    today = date.today()

    # --- Setup ---
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")

    config = load_config()
    claude_cfg = config.get("claude", {})
    digest_cfg = config.get("digest", {})

    conn = init_db()
    client = anthropic.Anthropic(api_key=api_key)

    # --- Fetch ---
    articles = fetch_all_feeds(config)
    if not articles:
        logger.warning("No articles fetched — aborting pipeline")
        return

    # --- Deduplicate against DB ---
    known_urls = get_known_urls(conn)
    new_articles = [a for a in articles if a.url not in known_urls]
    logger.info(f"New articles (not yet in DB): {len(new_articles)}/{len(articles)}")

    if not new_articles:
        logger.info("No new articles to process today")
        return

    # --- Filter for relevance ---
    relevant = filter_articles(new_articles, client)
    if not relevant:
        logger.info("No relevant articles found — skipping summarization")
        save_articles(conn, new_articles)
        return

    # --- Summarize ---
    max_articles = digest_cfg.get("max_articles", 10)
    to_summarize = relevant[:max_articles]
    summarize_articles(to_summarize, client)

    # --- Persist ---
    save_articles(conn, new_articles)
    digest_date_str = today.isoformat()
    for article in to_summarize:
        if article.full_summary:
            save_summary(conn, article.url, article.full_summary, digest_date_str)

    # --- Build & publish digest ---
    digest_md = build_digest(to_summarize, today, max_articles)
    output_dir = digest_cfg.get("output_dir", "digests/")
    path = publish_digest(digest_md, today, output_dir)

    logger.info(f"=== Pipeline complete — digest at {path} ===")
    conn.close()


def main() -> None:
    """Run once immediately, then schedule daily at 07:00."""
    run_pipeline()

    schedule.every().day.at("07:00").do(run_pipeline)
    logger.info("Scheduler active — next run at 07:00 daily. Press Ctrl+C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    # Run once immediately when called directly, without the scheduler loop
    run_pipeline()
