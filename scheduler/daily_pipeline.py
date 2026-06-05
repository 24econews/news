"""Orchestrate the full daily pipeline and optionally schedule it."""

import argparse
import logging
import os
import subprocess
import sys
from datetime import date, datetime

import anthropic
import schedule
import time
import yaml
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.storage import init_db, get_known_urls, save_articles, save_summary
from generation.digest_builder import build_digest
from ingestion.rss_fetcher import fetch_all_feeds
from processing.relevance_filter import filter_articles
from processing.summarizer import summarize_articles
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

_BRAZIL_RELEVANCE_PROMPT = """Você é um analista econômico especializado no Brasil. Sua tarefa é determinar se um artigo jornalístico é relevante do ponto de vista econômico para o Brasil.

Um artigo é relevante se tratar de algum dos seguintes temas:
- Macroeconomia brasileira (inflação, PIB, dívida, reservas do Banco Central)
- Mercados financeiros (real, câmbio, Ibovespa, bonds, commodities)
- Política econômica do governo brasileiro (orçamento, impostos, subsídios)
- Comércio exterior e importações/exportações
- Empresas e indústrias com impacto econômico significativo
- Emprego e salários no Brasil
- Medidas do FMI ou acordos internacionais que afetem o Brasil

Responda APENAS com um objeto JSON com dois campos:
- "relevant": boolean (true se for relevante, false se não for)
- "reason": string curta em português explicando por quê

Exemplo: {"relevant": true, "reason": "Trata sobre a variação do real e seu impacto nas importações"}"""

_BRAZIL_SUMMARIZER_PROMPT = """Você é um analista econômico especializado no Brasil. Sua tarefa é redigir um resumo conciso e objetivo de uma notícia econômica.

O resumo deve:
- Ter entre 3 e 5 frases
- Mencionar cifras, percentuais ou dados concretos quando disponíveis
- Usar um tom neutro e jornalístico
- Estar escrito em português brasileiro
- Destacar o impacto econômico principal da notícia

Não inclua frases introdutórias como "Este artigo trata sobre..." — vá direto ao conteúdo."""

COUNTRY_SETTINGS: dict = {
    "argentina": {
        "config_file": "config.yaml",
        "relevance_prompt": None,   # use module default (Argentina/Spanish)
        "summarizer_prompt": None,  # use module default (Argentina/Spanish)
    },
    "brazil": {
        "config_file": "config_brazil.yaml",
        "relevance_prompt": _BRAZIL_RELEVANCE_PROMPT,
        "summarizer_prompt": _BRAZIL_SUMMARIZER_PROMPT,
    },
}

# ---------------------------------------------------------------------------

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_pipeline(country: str = "argentina") -> None:
    """Execute the full pipeline: fetch → filter → summarize → store → publish → translate → push."""
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
        logger.info("No relevant articles found — skipping summarization")
        save_articles(conn, new_articles)
        conn.close()
        return

    # --- Summarize ---
    max_articles = digest_cfg.get("max_articles", 10)
    to_summarize = relevant[:max_articles]
    summarize_kwargs = {}
    if settings["summarizer_prompt"]:
        summarize_kwargs["system_prompt"] = settings["summarizer_prompt"]
    summarize_articles(to_summarize, client, **summarize_kwargs)

    # --- Persist ---
    save_articles(conn, new_articles)
    digest_date_str = today.isoformat()
    for article in to_summarize:
        if article.full_summary:
            save_summary(conn, article.url, article.full_summary, digest_date_str)

    # --- Build & publish digest ---
    digest_md = build_digest(to_summarize, today, max_articles, country=country)
    path = publish_digest_file(digest_md, today, output_dir)

    # --- Translate to English ---
    en_path = path.replace(".md", ".en.md")
    try:
        logger.info("Translating digest to English…")
        en_md = translate_digest(digest_md, client)
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
        choices=list(COUNTRY_SETTINGS),
        help="Country to run the pipeline for (default: argentina)",
    )
    args = parser.parse_args()
    run_pipeline(country=args.country)
