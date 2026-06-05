"""Summarize articles using Claude."""

import logging
from typing import List

import anthropic

from ingestion.rss_fetcher import Article

logger = logging.getLogger(__name__)

# Cached across all summarization calls in the same run.
SYSTEM_PROMPT = """Eres un analista económico especializado en Argentina. Tu tarea es redactar un resumen conciso y objetivo de una noticia económica.

El resumen debe:
- Tener entre 3 y 5 oraciones
- Mencionar cifras, porcentajes o datos concretos cuando estén disponibles
- Usar un tono neutral y periodístico
- Estar escrito en español argentino
- Destacar el impacto económico principal de la noticia

No incluyas frases introductorias como "Este artículo trata sobre..." — ve directo al contenido."""


def summarize_article(
    article: Article, client: anthropic.Anthropic, system_prompt: str = SYSTEM_PROMPT
) -> str:
    """Generate a 3–5 sentence economic summary of an article via Claude."""
    body = article.content or article.summary or ""
    if not body.strip():
        body = "(Solo se dispone del título)"

    prompt = f"Título: {article.title}\n\nContenido:\n{body[:3000]}"

    try:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=512,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )
        summary = response.content[0].text.strip()
        logger.debug(f"Summarized: '{article.title[:60]}'")
        return summary
    except Exception as exc:
        logger.warning(f"Summarization failed for '{article.title[:60]}': {exc}")
        return article.summary or ""


def summarize_articles(
    articles: List[Article], client: anthropic.Anthropic, system_prompt: str = SYSTEM_PROMPT
) -> List[Article]:
    """Summarize all articles in-place and return the list."""
    for i, article in enumerate(articles, 1):
        logger.info(f"Summarizing {i}/{len(articles)}: {article.title[:60]}")
        article.full_summary = summarize_article(article, client, system_prompt)
    return articles
