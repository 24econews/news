"""Translate a Bloomberg-style narrative digest to English via Claude."""

import logging

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a professional financial translator specializing in Latin American economic news. "
    "Translate the provided narrative from its source language to English for an English-speaking "
    "financial audience. Keep all Markdown formatting, dates, and numbers exactly as they are. "
    "Keep proper nouns (company names, people names, places) in their original form. "
    "Keep stock exchange ticker references exactly as written (e.g., NYSE: PBR, B3: VALE3, NASDAQ: MELI). "
    "Keep the '## Corporate Watch' section header in English as-is — do not translate it."
)


def translate_digest(content: str, client: anthropic.Anthropic, source_language: str = "Spanish") -> str:
    """Return the English translation of a narrative digest, or raise on failure."""
    instruction = (
        f"Translate this Bloomberg-style economic narrative from {source_language} to English. "
        "Preserve the analytical tone, the flow of the prose, and all proper nouns. "
        "Preserve all Markdown formatting exactly, including any '## Corporate Watch' section and "
        "its bold company name entries with exchange:ticker notation (e.g., NYSE: PBR). "
        "This should read like it was written in English originally — not like a translation."
    )

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=8192,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"{instruction}\n\n{content}",
            }
        ],
    )
    return response.content[0].text.strip()
