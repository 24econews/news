"""Build the daily Markdown digest from summarized articles."""

from collections import defaultdict
from datetime import date
from typing import List

from ingestion.rss_fetcher import Article

_STRINGS = {
    "argentina": {
        "header": "Digest Económico Argentina",
        "sources_heading": "Fuentes",
        "summary_line": lambda n_art, n_src: f"*{n_art} artículos seleccionados de {n_src} fuentes*",
        "article_count": lambda n: f"{n} artículo{'s' if n > 1 else ''}",
        "published": "Publicado",
        "footer": lambda d: f"*Digest generado automáticamente el {d}*",
    },
    "brazil": {
        "header": "Digest Econômico Brasil",
        "sources_heading": "Fontes",
        "summary_line": lambda n_art, n_src: f"*{n_art} artigos selecionados de {n_src} fonte{'s' if n_src > 1 else ''}*",
        "article_count": lambda n: f"{n} artigo{'s' if n > 1 else ''}",
        "published": "Publicado",
        "footer": lambda d: f"*Digest gerado automaticamente em {d}*",
    },
}


def build_digest(
    articles: List[Article],
    digest_date: date,
    max_articles: int = 10,
    country: str = "argentina",
) -> str:
    """Compile a Markdown digest grouped by news source."""
    strings = _STRINGS.get(country, _STRINGS["argentina"])
    articles = articles[:max_articles]

    by_source: dict[str, List[Article]] = defaultdict(list)
    for article in articles:
        by_source[article.source].append(article)

    lines: List[str] = []

    lines.append(f"# {strings['header']} — {digest_date.strftime('%d de %B de %Y')}")
    lines.append("")
    lines.append(strings["summary_line"](len(articles), len(by_source)))
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append(f"## {strings['sources_heading']}")
    lines.append("")
    for source in sorted(by_source):
        count = len(by_source[source])
        anchor = source.lower().replace(" ", "-")
        lines.append(f"- [{source}](#{anchor}) ({strings['article_count'](count)})")
    lines.append("")
    lines.append("---")
    lines.append("")

    for source in sorted(by_source):
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
            lines.append(f"*{strings['published']}: {pub}*")
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.append(strings["footer"](digest_date.isoformat()))

    return "\n".join(lines)
