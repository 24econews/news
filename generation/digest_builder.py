"""Build the daily Bloomberg-style narrative digest using Claude."""

from datetime import date
from typing import List

import anthropic

from ingestion.rss_fetcher import Article

_TITLES = {
    "argentina": "Argentina: El Pulso Económico",
    "brazil": "Brasil: O Pulso Econômico",
    "chile": "Chile: El Pulso Económico",
    "uruguay": "Uruguay: El Pulso Económico",
    "paraguay": "Paraguay: El Pulso Económico",
    "bolivia": "Bolivia: The Economic Pulse",
}

_BYLINES = {
    "argentina": "Análisis generado con IA",
    "brazil": "Análise gerada com IA",
    "chile": "Análisis generado con IA",
    "uruguay": "Análisis generado con IA",
    "paraguay": "Análisis generado con IA",
    "bolivia": "Análisis generado con IA",
}

_LANGUAGES = {
    "argentina": "Spanish",
    "brazil": "Portuguese",
    "chile": "Spanish",
    "uruguay": "Spanish",
    "paraguay": "Spanish",
    "bolivia": "Spanish",
}

_COUNTRY_NAMES = {
    "argentina": "Argentina",
    "brazil": "Brazil",
    "chile": "Chile",
    "uruguay": "Uruguay",
    "paraguay": "Paraguay",
    "bolivia": "Bolivia",
}

SYSTEM_PROMPT = (
    "You are a senior financial journalist writing for an audience of "
    "sophisticated investors and business executives. Your style is "
    "analytical, precise and authoritative — like Bloomberg or the "
    "Financial Times. You write in clear, confident prose. No bullet "
    "points. No headers within the article. No filler phrases."
)


def build_narrative_digest(
    articles: List[Article],
    digest_date: date,
    country: str = "argentina",
    client: anthropic.Anthropic = None,
) -> str:
    """Generate a Bloomberg-style narrative digest from filtered articles via Claude."""
    title = _TITLES.get(country, _TITLES["argentina"])
    byline = _BYLINES.get(country, _BYLINES["argentina"])
    language = _LANGUAGES.get(country, "Spanish")
    country_name = _COUNTRY_NAMES.get(country, country.capitalize())
    date_str = digest_date.isoformat()

    articles_text = _format_articles(articles)

    user_prompt = f"""Based on the following news articles from {country_name} today, produce an economic and business report in two parts.

---
PART 1 — MAIN NARRATIVE (600-800 words, required):

Before writing, identify what is most newsworthy TODAY specifically — what has changed, what is surprising, what connects to global trends, or what contradicts expectations. Lead with that angle. Do not default to a standard macro-overview structure every day.

Possible angles (choose the one that fits today's news best):
- A single dominant story that overshadows everything else
- A tension or contradiction between two economic forces
- A surprising data point or market move that needs explaining
- A corporate or sector story with regional/global implications
- A policy decision and its likely ripple effects
- A longer-term trend that today's news crystallizes

Your opening sentence should immediately signal which angle you have chosen. A reader should know within one sentence what makes today's digest different from yesterday's.

- Weave the most important stories together into flowing, connected prose
- Integrate market data (exchange rates, indices, risk indicators) naturally
- Group related themes: fiscal policy, markets, trade, industry, etc.
- When significant corporate stories exist (earnings results, M&A deals, IPOs, major restructurings), weave them naturally into the narrative. If the company trades internationally, note it explicitly — e.g., "Petrobras, whose ADRs trade on the NYSE, reported quarterly earnings that..."
- End with a forward-looking paragraph on what to watch next
- Write in {language}
- Do not list articles separately — this must read as one unified piece
- Attribute key facts to their sources naturally within the text
- Do NOT insert any headlines, sub-headlines, or title lines inside the narrative body. The narrative should be flowing prose only, with no # headings, no bold title lines, and no lines that summarize the article before the body begins. Start directly with the first sentence of the narrative.
- Do not follow the same paragraph structure every day. Sometimes open with markets, sometimes with a company, sometimes with a political-economic development, sometimes with a data point. The narrative should feel like it was written by a journalist who read today's news and chose the most compelling entry point — not by a system running the same template.

---
PART 2 — CORPORATE WATCH (optional section, include only if warranted):
After the narrative, if the articles contain significant corporate news — M&A deals, earnings that materially beat or missed expectations, IPOs, major restructurings, or notable executive appointments/departures at major companies — add a "## Corporate Watch" section.

Rules for this section:
- Maximum 3 items
- Each item: bold company name with exchange and ticker in parentheses, then an em dash, then 1-2 sentences maximum
- Tone: Bloomberg Markets brief — factual, precise, no editorializing
- Make global significance explicit in every item (international listings, cross-border deals, commodity exposure, etc.)
- Format: **Company Name (NYSE: XYZ)** — Sentence one. Sentence two if needed.
- Write the content in {language}, but keep "## Corporate Watch" as the section header in English
- If there are no significant corporate stories today, omit this entire section — do NOT force it

---
Articles:
{articles_text}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    narrative = response.content[0].text.strip()

    headline = _generate_headline(narrative, client)
    return f"> TITLE: {headline}\n\n# {title} — {date_str}\n\n*{byline} | {date_str}*\n\n{narrative}"


def _generate_headline(narrative: str, client: anthropic.Anthropic) -> str:
    """Generate a short Bloomberg/NYT-style English headline for the narrative."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": (
                "Write a headline (max 12 words) that captures the single most important or "
                "surprising economic development described below. The headline should reflect "
                "what is genuinely new or different today — not a generic summary of ongoing "
                "conditions. Vary the style: sometimes a declarative statement, sometimes a "
                "tension or paradox, sometimes a question, sometimes a single sharp observation. "
                "Avoid starting every headline with the country name followed by a verb.\n\n"
                "Review your headline. If it follows the pattern '[Country] + [verb] + [economic "
                "theme]', rewrite it to be more specific, more surprising, or more vivid. The "
                "best headlines name something concrete, not a category.\n\n"
                "Return ONLY the final headline, nothing else.\n\n"
                + narrative
            ),
        }],
    )
    return response.content[0].text.strip()


def _format_articles(articles: List[Article]) -> str:
    parts = []
    for article in articles:
        content = article.full_summary or article.content or article.summary or ""
        parts.append(
            f"SOURCE: {article.source}\n"
            f"HEADLINE: {article.title}\n"
            f"CONTENT: {content[:2000]}\n"
            "---"
        )
    return "\n".join(parts)
