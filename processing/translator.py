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


def _split_metadata(content: str) -> tuple[str, str]:
    """Split leading '> KEY: value' metadata lines from the rest of the digest.

    Returns (metadata_block, body). metadata_block includes its trailing blank-line
    separator (or is empty if there is no metadata), so callers can safely do
    f"{metadata_block}{translated_body}".
    """
    lines = content.split("\n")
    i = 0
    while i < len(lines) and lines[i].startswith(">"):
        i += 1
    metadata_lines = lines[:i]
    if i < len(lines) and lines[i].strip() == "":
        i += 1
    metadata = "\n".join(metadata_lines)
    if metadata:
        metadata += "\n\n"
    body = "\n".join(lines[i:])
    return metadata, body


def translate_digest(content: str, client: anthropic.Anthropic, source_language: str = "Spanish") -> str:
    """Return the English translation of a narrative digest, or raise on failure.

    The leading '> KEY: value' metadata block (IMAGE_URL, TITLE, etc.) is preserved
    verbatim rather than sent through translation, since the model doesn't reliably
    reproduce it (dropping lines or stripping the '>' prefix).
    """
    metadata, body = _split_metadata(content)

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
                "content": f"{instruction}\n\n{body}",
            }
        ],
    )
    translated_body = response.content[0].text.strip()
    return f"{metadata}{translated_body}"
