"""Filter articles for economic relevance using Claude."""

import logging
from typing import List, Set

import anthropic

from ingestion.rss_fetcher import Article

logger = logging.getLogger(__name__)

BATCH_SIZE = 10

# Cached across all calls in the same pipeline run (5-minute TTL on Anthropic's side).
SYSTEM_PROMPT = """Eres un analista económico especializado en Argentina. Tu tarea es determinar qué artículos periodísticos son relevantes desde el punto de vista económico para Argentina.

Un artículo es relevante si trata sobre alguno de estos temas:
- Macroeconomía argentina (inflación, PBI, deuda, reservas del BCRA)
- Mercados financieros (dólar, bonos, acciones, commodities)
- Política económica del gobierno argentino (presupuesto, impuestos, subsidios)
- Comercio exterior e importaciones/exportaciones
- Empresas e industrias con impacto económico significativo
- Empleo y salarios en Argentina
- Medidas del FMI o acuerdos internacionales que afecten a Argentina

Se te dará una lista numerada de artículos (pueden estar en cualquier idioma). Responde ÚNICAMENTE con los números de los artículos relevantes, separados por comas.
Si ninguno es relevante, responde ÚNICAMENTE con la palabra "ninguno".
Responde siempre en este formato, independientemente del idioma de los artículos.

Ejemplo de respuesta: "1,3,5,7"
Otro ejemplo: "2,4"
Ejemplo cuando ninguno es relevante: "ninguno"
"""


def _filter_batch(
    batch: List[Article], batch_start: int, client: anthropic.Anthropic, system_prompt: str = SYSTEM_PROMPT
) -> Set[int]:
    """Send a batch of articles to Claude Haiku and return indices of relevant ones.

    Returns the set of absolute article indices (within the full list) that are relevant.
    On any error, conservatively includes all articles in the batch.
    """
    if not batch:
        return set()

    lines = []
    for i, article in enumerate(batch, start=1):
        snippet = article.summary or article.content or "(sin contenido)"
        snippet = snippet[:200].replace("\n", " ")
        lines.append(f"{i}. {article.title} — {snippet}")
    user_text = "\n".join(lines)

    all_indices = set(range(batch_start, batch_start + len(batch)))

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_text}],
        )
        raw = response.content[0].text.strip().lower()

        _NONE_RESPONSES = {"ninguno", "nenhum", "none", "0", ""}
        if raw in _NONE_RESPONSES:
            return set()

        relevant_indices: Set[int] = set()
        for token in raw.split(","):
            token = token.strip()
            if token.isdigit():
                # token is 1-based position within this batch
                pos = int(token) - 1
                if 0 <= pos < len(batch):
                    relevant_indices.add(batch_start + pos)
                else:
                    logger.warning(f"Batch response contained out-of-range index {token} (batch size {len(batch)})")

        logger.debug(f"Batch [{batch_start}:{batch_start+len(batch)}]: {len(relevant_indices)}/{len(batch)} relevant")
        return relevant_indices

    except Exception as exc:
        logger.warning(f"Batch relevance check failed (articles {batch_start}-{batch_start+len(batch)-1}): {exc} — including all in batch")
        return all_indices


def filter_articles(
    articles: List[Article], client: anthropic.Anthropic, system_prompt: str = SYSTEM_PROMPT
) -> List[Article]:
    """Return only the economically relevant articles from the list."""
    if not articles:
        return []

    relevant_indices: Set[int] = set()

    for batch_start in range(0, len(articles), BATCH_SIZE):
        batch = articles[batch_start : batch_start + BATCH_SIZE]
        relevant_indices |= _filter_batch(batch, batch_start, client, system_prompt)

    relevant = []
    for i, article in enumerate(articles):
        article.is_relevant = i in relevant_indices
        if article.is_relevant:
            relevant.append(article)

    logger.info(f"Relevance filter: {len(relevant)}/{len(articles)} articles kept")
    return relevant
