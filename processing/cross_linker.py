"""Identify cross-country economic connections and inject cross-references into digests."""

import json
import logging
import os
import re

import anthropic

logger = logging.getLogger(__name__)

COUNTRY_META = {
    "argentina": {"flag": "🇦🇷", "display": "Argentina", "path": "digests/digest_{date}.md"},
    "brazil":    {"flag": "🇧🇷", "display": "Brazil",    "path": "digests/brazil/digest_{date}.md"},
    "chile":     {"flag": "🇨🇱", "display": "Chile",     "path": "digests/chile/digest_{date}.md"},
    "uruguay":   {"flag": "🇺🇾", "display": "Uruguay",   "path": "digests/uruguay/digest_{date}.md"},
    "paraguay":  {"flag": "🇵🇾", "display": "Paraguay",  "path": "digests/paraguay/digest_{date}.md"},
    "bolivia":   {"flag": "🇧🇴", "display": "Bolivia",   "path": "digests/bolivia/digest_{date}.md"},
}

_SYSTEM_PROMPT = (
    "You are an editor at a global economic news agency covering Latin America. "
    "Your job is to identify connections between economic stories happening across "
    "different countries on the same day."
)


def _digest_path(base_dir: str, country: str, date: str) -> str:
    rel = COUNTRY_META[country]["path"].replace("{date}", date)
    return os.path.join(base_dir, rel)


def _extract_title(content: str) -> str:
    m = re.search(r"^> TITLE: (.+)$", content, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _strip_existing_cross_refs(content: str) -> str:
    """Remove any previously injected ## Related Coverage section."""
    for marker in ("\n---\n## Related Coverage", "\n## Related Coverage"):
        idx = content.find(marker)
        if idx != -1:
            return content[:idx]
    return content


def _build_cross_ref_block(country: str, connections: list, date: str) -> str:
    """Return the ## Related Coverage markdown block for a country, or '' if none."""
    relevant = [c for c in connections if country in c.get("countries", [])]
    if not relevant:
        return ""

    lines = ["\n---\n## Related Coverage\n"]
    for conn in relevant:
        event = conn["event"]
        summary = conn["summaries"].get(country, "")
        others = [c for c in conn["countries"] if c != country]

        lines.append(f"**{event}**")
        if summary:
            lines.append(summary)
        for other in others:
            meta = COUNTRY_META[other]
            title = conn.get("titles", {}).get(other, "")
            url = f"/{other}/{date}"
            if title:
                lines.append(f"→ See also: {meta['flag']} {meta['display']}: {title} — {url}")
            else:
                lines.append(f"→ See also: {meta['flag']} {meta['display']} — {url}")
        lines.append("")

    return "\n".join(lines)


def cross_link_digests(
    date: str,
    countries: list,
    digests_base_dir: str,
    client: anthropic.Anthropic,
) -> dict:
    """
    Find shared events across country digests and inject cross-references.
    Returns a summary dict: {connections, countries, events}.
    """
    # Step a: Read digests
    narratives: dict = {}
    titles: dict = {}

    for country in countries:
        if country not in COUNTRY_META:
            continue
        path = _digest_path(digests_base_dir, country, date)
        if not os.path.exists(path):
            logger.info(f"[cross_linker] No digest for {country} on {date} — skipping")
            continue
        with open(path, encoding="utf-8") as f:
            content = f.read()
        narratives[country] = _strip_existing_cross_refs(content)
        titles[country] = _extract_title(content)
        logger.info(f"[cross_linker] Loaded {country} digest ({len(content):,} chars)")

    if len(narratives) < 2:
        logger.info("[cross_linker] Fewer than 2 digests found — nothing to link")
        return {"connections": 0, "countries": []}

    # Step b: Find connections via Claude
    narratives_text = "\n\n".join(
        f"=== {c.upper()} ===\n{text}" for c, text in narratives.items()
    )
    user_prompt = (
        f"Here are today's economic narratives from {len(narratives)} countries. "
        "Identify up to 5 cross-country connections where the same event, trend, or development "
        "is mentioned in multiple countries, or where one country's story directly impacts another.\n\n"
        "For each connection found, return a JSON array:\n"
        "[\n"
        "  {\n"
        '    "event": "brief description of shared event (max 8 words)",\n'
        '    "countries": ["argentina", "brazil"],\n'
        '    "summaries": {\n'
        '      "argentina": "one sentence on how it affects Argentina",\n'
        '      "brazil": "one sentence on how it affects Brazil"\n'
        "    }\n"
        "  }\n"
        "]\n\n"
        "Only include genuine connections — not superficial mentions.\n"
        "Return ONLY the JSON array, nothing else.\n\n"
        f"{narratives_text}"
    )

    logger.info(f"[cross_linker] Sending {len(narratives)} narratives to Claude…")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = response.content[0].text.strip()

    # Step c: Parse JSON
    try:
        cleaned = re.sub(r"^```[a-z]*\n?", "", raw)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()
        connections: list = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error(f"[cross_linker] Failed to parse JSON: {exc}\nRaw: {raw[:500]}")
        return {"connections": 0, "countries": [], "error": str(exc)}

    # Attach digest titles so "See also" lines can include them
    for conn in connections:
        conn["titles"] = {c: titles.get(c, "") for c in conn.get("countries", [])}

    logger.info(f"[cross_linker] {len(connections)} connection(s) found")

    # Steps d+e: Inject cross-references into .md and .en.md
    affected: set = set()

    for country in narratives:
        block = _build_cross_ref_block(country, connections, date)
        if not block:
            continue

        md_path = _digest_path(digests_base_dir, country, date)
        en_path = md_path[:-3] + ".en.md"

        for path in (md_path, en_path):
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as f:
                content = f.read()
            content = _strip_existing_cross_refs(content)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content + block)
            logger.info(f"[cross_linker] Injected into {os.path.basename(path)}")

        affected.add(country)

    return {
        "connections": len(connections),
        "countries": sorted(affected),
        "events": [c["event"] for c in connections],
    }
