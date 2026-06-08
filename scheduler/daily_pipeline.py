"""Orchestrate the full daily pipeline and optionally schedule it."""

import argparse
import logging
import os
import subprocess
import sys
from datetime import date

import anthropic
import schedule
import time
import yaml
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.dirname(SCRIPT_DIR))

from db.storage import init_db, get_known_urls, save_articles
from generation.digest_builder import build_narrative_digest
from ingestion.rss_fetcher import fetch_all_feeds
from processing.image_fetcher import fetch_hero_image
from processing.relevance_filter import filter_articles
from processing.translator import translate_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Country-specific prompts and config routing
# ---------------------------------------------------------------------------

_PARAGUAY_RELEVANCE_PROMPT = """You are an economic relevance classifier. Your ONLY job is to output numbers.

An article is relevant if it covers any of these topics related to Paraguay:
- Paraguayan macroeconomics (inflation, GDP, guaraní currency, Central Bank of Paraguay, BCP)
- Financial markets (PYG/USD exchange rate, bonds, commodities)
- Paraguayan government economic policy (budget, taxes, subsidies, reforms)
- Foreign trade, imports or exports involving Paraguay
- Companies or industries with significant economic impact in Paraguay
- Employment and wages in Paraguay
- IMF measures or international agreements affecting Paraguay
- Key sectors: soy, beef, electricity (Itaipú/Yacyretá), re-export trade, maquila industry

You will receive a numbered list of articles. They may be in any language.

RESPOND ONLY WITH COMMA-SEPARATED NUMBERS. NOTHING ELSE.
- If articles 1, 3, and 7 are relevant: respond exactly with:  1,3,7
- If only article 2 is relevant: respond exactly with:  2
- If none are relevant: respond exactly with:  none

DO NOT write any words, explanations, translations, or punctuation other than digits and commas.
DO NOT respond in Spanish or any language — output only digits and commas.
"""

_BOLIVIA_RELEVANCE_PROMPT = """You are an economic relevance classifier. Your ONLY job is to output numbers.

An article is relevant if it covers any of these topics related to Bolivia:
- Bolivian macroeconomics (inflation, GDP, boliviano currency, Central Bank of Bolivia, BCB)
- Financial markets (BOB/USD exchange rate, bonds, commodities)
- Bolivian government economic policy (budget, subsidies, nationalization, reforms)
- Foreign trade, imports or exports involving Bolivia
- Companies or industries with significant economic impact in Bolivia
- Employment and wages in Bolivia
- IMF measures or international agreements affecting Bolivia
- Key sectors: gas/hydrocarbons, lithium, mining (tin, silver, zinc), coca, agriculture
- Fuel crisis or dollar shortage (chronic structural issues)

You will receive a numbered list of articles. They may be in any language.

RESPOND ONLY WITH COMMA-SEPARATED NUMBERS. NOTHING ELSE.
- If articles 1, 3, and 7 are relevant: respond exactly with:  1,3,7
- If only article 2 is relevant: respond exactly with:  2
- If none are relevant: respond exactly with:  none

DO NOT write any words, explanations, translations, or punctuation other than digits and commas.
DO NOT respond in Spanish or any language — output only digits and commas.
"""

_URUGUAY_RELEVANCE_PROMPT = """You are an economic relevance classifier. Your ONLY job is to output numbers.

An article is relevant if it covers any of these topics related to Uruguay:
- Uruguayan macroeconomics (inflation, GDP, UYU peso, Central Bank of Uruguay, BCU)
- Financial markets (UYU/USD exchange rate, Montevideo stock exchange, bonds, commodities)
- Uruguayan government economic policy (budget, taxes, subsidies, reforms)
- Foreign trade, imports or exports involving Uruguay
- Companies or industries with significant economic impact in Uruguay
- Employment and wages in Uruguay
- IMF measures or international agreements affecting Uruguay
- Key sectors: agriculture (soy, beef, dairy), technology, tourism, free trade zones

You will receive a numbered list of articles. They may be in any language.

RESPOND ONLY WITH COMMA-SEPARATED NUMBERS. NOTHING ELSE.
- If articles 1, 3, and 7 are relevant: respond exactly with:  1,3,7
- If only article 2 is relevant: respond exactly with:  2
- If none are relevant: respond exactly with:  none

DO NOT write any words, explanations, translations, or punctuation other than digits and commas.
DO NOT respond in Spanish or any language — output only digits and commas.
"""

_CHILE_RELEVANCE_PROMPT = """You are an economic relevance classifier. Your ONLY job is to output numbers.

An article is relevant if it covers any of these topics related to Chile:
- Chilean macroeconomics (inflation, GDP, CLP peso, Central Bank of Chile)
- Financial markets (CLP exchange rate, IPSA index, copper prices, bonds)
- Chilean government economic policy (budget, taxes, subsidies, reforms)
- Foreign trade, imports or exports involving Chile
- Companies or industries with significant economic impact in Chile
- Employment and wages in Chile
- IMF measures or international agreements affecting Chile
- Mining, especially copper (Chile's main export)

You will receive a numbered list of articles. They may be in any language.

RESPOND ONLY WITH COMMA-SEPARATED NUMBERS. NOTHING ELSE.
- If articles 1, 3, and 7 are relevant: respond exactly with:  1,3,7
- If only article 2 is relevant: respond exactly with:  2
- If none are relevant: respond exactly with:  none

DO NOT write any words, explanations, translations, or punctuation other than digits and commas.
DO NOT respond in Spanish or any language — output only digits and commas.
"""

_BRAZIL_RELEVANCE_PROMPT = """You are an economic relevance classifier. Your ONLY job is to output numbers.

An article is relevant if it covers any of these topics related to Brazil:
- Brazilian macroeconomics (inflation, GDP, debt, central bank reserves)
- Financial markets (BRL/real exchange rate, Ibovespa, bonds, commodities)
- Brazilian government economic policy (budget, taxes, subsidies)
- Foreign trade, imports or exports
- Companies or industries with significant economic impact in Brazil
- Employment and wages in Brazil
- IMF measures or international agreements affecting Brazil

You will receive a numbered list of articles. They may be in any language.

RESPOND ONLY WITH COMMA-SEPARATED NUMBERS. NOTHING ELSE.
- If articles 1, 3, and 7 are relevant: respond exactly with:  1,3,7
- If only article 2 is relevant: respond exactly with:  2
- If none are relevant: respond exactly with:  none

DO NOT write any words, explanations, translations, or punctuation other than digits and commas.
DO NOT say "Os artigos relevantes são" or anything like that.
DO NOT respond in Portuguese or any language — output only digits and commas.
"""

COUNTRY_SETTINGS: dict = {
    "argentina": {
        "config_file": "config.yaml",
        "relevance_prompt": None,   # use module default (Argentina/Spanish)
        "source_language": "Spanish",
    },
    "brazil": {
        "config_file": "config_brazil.yaml",
        "relevance_prompt": _BRAZIL_RELEVANCE_PROMPT,
        "source_language": "Portuguese",
    },
    "chile": {
        "config_file": "config_chile.yaml",
        "relevance_prompt": _CHILE_RELEVANCE_PROMPT,
        "source_language": "Spanish",
    },
    "uruguay": {
        "config_file": "config_uruguay.yaml",
        "relevance_prompt": _URUGUAY_RELEVANCE_PROMPT,
        "source_language": "Spanish",
    },
    "paraguay": {
        "config_file": "config_paraguay.yaml",
        "relevance_prompt": _PARAGUAY_RELEVANCE_PROMPT,
        "source_language": "Spanish",
    },
    "bolivia": {
        "config_file": "config_bolivia.yaml",
        "relevance_prompt": _BOLIVIA_RELEVANCE_PROMPT,
        "source_language": "Spanish",
    },
}

# ---------------------------------------------------------------------------

def load_config(path: str) -> dict:
    if not os.path.isabs(path):
        path = os.path.join(SCRIPT_DIR, '..', path)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_pipeline(country: str = "argentina") -> None:
    """Execute the full pipeline: fetch → filter → store → publish → translate → push."""
    if country not in COUNTRY_SETTINGS:
        raise ValueError(f"Unknown country '{country}'. Supported: {list(COUNTRY_SETTINGS)}")

    settings = COUNTRY_SETTINGS[country]
    logger.info(f"=== Pipeline started [{country}] ===")
    today = date.today()

    # --- Setup ---
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")

    config = load_config(settings["config_file"])
    digest_cfg = config.get("digest", {})

    output_dir = digest_cfg.get("output_dir", f"digests/{country}/")
    db_path = digest_cfg.get("db_path", f"economy_{country}.db")

    repo_root = os.path.join(SCRIPT_DIR, '..')
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(repo_root, output_dir)
    if not os.path.isabs(db_path):
        db_path = os.path.join(repo_root, db_path)

    conn = init_db(db_path)
    client = anthropic.Anthropic(api_key=api_key)

    # --- Fetch ---
    articles = fetch_all_feeds(config)
    if not articles:
        logger.warning("No articles fetched — aborting pipeline")
        conn.close()
        return

    # --- Deduplicate against DB ---
    known_urls = get_known_urls(conn)
    new_articles = [a for a in articles if a.url not in known_urls]
    logger.info(f"New articles (not yet in DB): {len(new_articles)}/{len(articles)}")

    if not new_articles:
        logger.info("No new articles to process today")
        conn.close()
        return

    # --- Filter for relevance ---
    filter_kwargs = {}
    if settings["relevance_prompt"]:
        filter_kwargs["system_prompt"] = settings["relevance_prompt"]
    relevant = filter_articles(new_articles, client, **filter_kwargs)
    if not relevant:
        logger.info("No relevant articles found — skipping digest generation")
        save_articles(conn, new_articles)
        conn.close()
        return

    # --- Persist ---
    save_articles(conn, new_articles)

    # --- Build narrative digest ---
    logger.info(f"Generating narrative digest from {len(relevant)} relevant articles…")
    digest_md = build_narrative_digest(relevant, today, country=country, client=client)

    # --- Fetch hero image ---
    title_match = next(
        (line[len("> TITLE:"):].strip() for line in digest_md.splitlines()[:5] if line.startswith("> TITLE:")),
        None,
    )
    if title_match:
        img = fetch_hero_image(title_match, country)
        if img:
            image_block = (
                f"> IMAGE_URL: {img['url']}\n"
                f"> IMAGE_THUMB: {img['thumb']}\n"
                f"> IMAGE_CREDIT: {img['photographer']}\n"
                f"> IMAGE_CREDIT_URL: {img['photographer_url']}\n"
            )
            # Insert image block before the > TITLE: line
            digest_md = image_block + digest_md
            logger.info(f"Hero image attached: {img['url']}")
        else:
            logger.info("No hero image found — continuing without one")

    path = publish_digest_file(digest_md, today, output_dir)

    # --- Translate to English ---
    en_path = path.replace(".md", ".en.md")
    try:
        logger.info("Translating digest to English…")
        en_md = translate_digest(digest_md, client, source_language=settings["source_language"])
        with open(en_path, "w", encoding="utf-8") as f:
            f.write(en_md)
        logger.info(f"English digest saved to {en_path}")
    except Exception as exc:
        logger.error(f"Translation failed — skipping English digest: {exc}")
        en_path = None

    logger.info(f"=== Pipeline complete [{country}] — digest at {path} ===")
    conn.close()

    # --- Push to GitHub (local runs only; GitHub Actions handles this via workflow) ---
    if os.getenv("GITHUB_ACTIONS"):
        logger.info("Running in GitHub Actions — git push skipped (handled by workflow)")
    else:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        commit_msg = f"Daily digest {country} {today.isoformat()}"
        try:
            subprocess.run(["git", "add", "digests/"], cwd=repo_root, check=True)
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo_root, check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True)
            logger.info("Digest pushed to GitHub")
        except subprocess.CalledProcessError as e:
            logger.error(f"Git push failed: {e}")


def publish_digest_file(content: str, digest_date: date, output_dir: str) -> str:
    """Write digest markdown to output_dir/digest_YYYY-MM-DD.md and return the path."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"digest_{digest_date.isoformat()}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Digest published to {path}")
    return path


def main(country: str = "argentina") -> None:
    """Run once immediately, then schedule daily at 07:00."""
    run_pipeline(country)

    schedule.every().day.at("07:00").do(run_pipeline, country=country)
    logger.info(f"Scheduler active [{country}] — next run at 07:00 daily. Press Ctrl+C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the economy digest pipeline.")
    parser.add_argument(
        "--country",
        default="argentina",
        choices=sorted(COUNTRY_SETTINGS),
        help="Country to run the pipeline for (default: argentina)",
    )
    args = parser.parse_args()
    run_pipeline(country=args.country)
