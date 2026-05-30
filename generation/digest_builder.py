"""Build the daily Markdown digest from summarized articles."""

from collections import defaultdict
from datetime import date
from typing import List

from ingestion.rss_fetcher import Article


def build_digest(articles: List[Article], digest_date: date, max_articles: int = 10) -> str:
    """Compile a Markdown digest grouped by news source.

    Articles are capped at max_articles total, then grouped by source for
    readability. Returns the full Markdown string.
    """
    # Cap total articles
    articles = articles[:max_articles]

    # Group by source
    by_source: dict[str, List[Article]] = defaultdict(list)
    for article in articles:
        by_source[article.source].append(article)

    lines: List[str] = []

    # Header
    lines.append(f"# Digest Económico Argentina — {digest_date.strftime('%d de %B de %Y')}")
    lines.append("")
    lines.append(f"*{len(articles)} artículos seleccionados de {len(by_source)} fuentes*")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Table of contents
    lines.append("## Fuentes")
    lines.append("")
    for source in sorted(by_source):
        count = len(by_source[source])
        anchor = source.lower().replace(" ", "-")
        lines.append(f"- [{source}](#{anchor}) ({count} artículo{'s' if count > 1 else ''})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Articles by source
    for source in sorted(by_source):
        anchor = source.lower().replace(" ", "-")
        lines.append(f"## {source}")
        lines.append("")
        for article in by_source[source]:
            lines.append(f"### [{article.title}]({article.url})")
            lines.append("")
            if article.full_summary:
                lines.append(article.full_summary)
            elif article.summary:
                lines.append(article.summary)
            lines.append("")
            pub = article.published_at.strftime("%d/%m/%Y %H:%M")
            lines.append(f"*Publicado: {pub}*")
            lines.append("")
        lines.append("---")
        lines.append("")

    # Footer
    lines.append(f"*Digest generado automáticamente el {digest_date.isoformat()}*")

    return "\n".join(lines)
