"""Filter articles for economic relevance using Claude."""

import json
import logging
from typing import List

import anthropic

from ingestion.rss_fetcher import Article

logger = logging.getLogger(__name__)

# Cached across all calls in the same pipeline run (5-minute TTL on Anthropic's side).
# With 30-50 articles per run, caching saves ~90% of system-prompt tokens.
SYSTEM_PROMPT = """Eres un analista económico especializado en Argentina. Tu tarea es determinar si un artículo periodístico es relevante desde el punto de vista económico para Argentina.

Un artículo es relevante si trata sobre alguno de estos temas:
- Macroeconomía argentina (inflación, PBI, deuda, reservas del BCRA)
- Mercados financieros (dólar, bonos, acciones, commodities)
- Política económica del gobierno argentino (presupuesto, impuestos, subsidios)
- Comercio exterior e importaciones/exportaciones
- Empresas e industrias con impacto económico significativo
- Empleo y salarios en Argentina
- Medidas del FMI o acuerdos internacionales que afecten a Argentina

Responde ÚNICAMENTE con un objeto JSON con dos campos:
- "relevant": boolean (true si es relevante, false si no lo es)
- "reason": string corta en español explicando por qué

Ejemplo: {"relevant": true, "reason": "Trata sobre la variación del dólar oficial y su impacto en las importaciones"}"""


def is_economically_relevant(
    article: Article, client: anthropic.Anthropic, system_prompt: str = SYSTEM_PROMPT
) -> bool:
    """Ask Claude whether a single article is economically relevant."""
    text = f"Título: {article.title}\n\nResumen: {article.summary or article.content or '(sin contenido)'}"

    try:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=150,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": text}],
        )
        result = json.loads(response.content[0].text)
        relevant = bool(result.get("relevant", False))
        logger.debug(f"[{article.source}] '{article.title[:60]}' → relevant={relevant} ({result.get('reason', '')})")
        return relevant
    except (json.JSONDecodeError, IndexError, Exception) as exc:
        logger.warning(f"Relevance check failed for '{article.title[:60]}': {exc}")
        return True


def filter_articles(
    articles: List[Article], client: anthropic.Anthropic, system_prompt: str = SYSTEM_PROMPT
) -> List[Article]:
    """Return only the economically relevant articles from the list."""
    relevant = []
    for article in articles:
        article.is_relevant = is_economically_relevant(article, client, system_prompt)
        if article.is_relevant:
            relevant.append(article)

    logger.info(f"Relevance filter: {len(relevant)}/{len(articles)} articles kept")
    return relevant
