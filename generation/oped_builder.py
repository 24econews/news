"""Generate the Mercosur/Brazil OpEd column, rotating through 5 recurring personas.

Publishes on a Mon/Wed/Fri schedule. The persona for a given date is computed
deterministically from the count of Mon/Wed/Fri publishing days elapsed since
a fixed epoch, mod 5 — no external state (files, DB rows) needed to track
whose "turn" it is.
"""

import argparse
import logging
import os
import sys
from datetime import date, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "publishing"))

# Reuse the existing digest-reading logic (path resolution + parsing) rather
# than re-implementing it.
from weekly_briefing import COUNTRY_DISPLAY_NAMES, COUNTRY_ORDER, digest_path, parse_country_digest  # noqa: E402
from x_poster import FLAGS  # noqa: E402

from generation.oped_personas import PERSONAS  # noqa: E402

# First Monday the OpEd section runs from. Fixed so the rotation is
# reproducible from the date alone — do not change once pieces have been
# published, or the rotation will jump.
OPED_START_DATE = date(2026, 1, 5)

PUBLISHING_WEEKDAYS = (0, 2, 4)  # Monday, Wednesday, Friday (date.weekday())

LOOKBACK_DAYS = 5

OUTPUT_DIR = os.path.join(REPO_ROOT, "digests", "opinion")

MODEL = "claude-sonnet-4-6"
HEADLINE_MODEL = "claude-haiku-4-5-20251001"

PROMPT_TEMPLATE = """You are {name}, {voice}, writing a 600-800 word opinion column for 24EcoNews's Opinion section.

Below is recent factual reporting on Brazil and Mercosur economic and political developments. Select the single most opinion-worthy story or tension from this material — something genuinely contestable, not settled consensus.

Write a sharp, well-argued opinion piece from your stated ideological perspective. Your argument MUST be grounded in the real facts, figures, and events provided below — do not fabricate data, quotes, or events. You may interpret, emphasize, and draw conclusions the underlying reporting doesn't state explicitly, but the underlying facts must be real and traceable to the source material.

Write with conviction and a clear point of view — this is opinion writing, not neutral reporting. Be willing to criticize your own 'side' when the facts warrant it; intellectual honesty matters more than ideological consistency.

Your rhetorical style: {style}

Structure: a sharp opening that states your thesis, 3-4 paragraphs of argument grounded in specific facts, a closing that doesn't hedge.

Do not include a byline or title — just the piece itself.

---
RECENT FACTUAL REPORTING (Brazil and broader Mercosur, last {lookback_days} days):

{grounding_material}"""


def is_publishing_day(day: date) -> bool:
    return day.weekday() in PUBLISHING_WEEKDAYS


def publishing_day_count(day: date) -> int:
    """Count of Mon/Wed/Fri publishing days in [OPED_START_DATE, day)."""
    delta_days = (day - OPED_START_DATE).days
    if delta_days < 0:
        raise ValueError(f"{day.isoformat()} is before OPED_START_DATE ({OPED_START_DATE.isoformat()})")
    full_weeks, remainder = divmod(delta_days, 7)
    count = full_weeks * 3
    for i in range(remainder):
        weekday = (OPED_START_DATE.weekday() + i) % 7
        if weekday in PUBLISHING_WEEKDAYS:
            count += 1
    return count


def persona_for_date(day: date):
    """Deterministically pick the persona whose turn it is on a given publishing day."""
    if not is_publishing_day(day):
        raise ValueError(f"{day.isoformat()} ({day.strftime('%A')}) is not a Mon/Wed/Fri publishing day")
    index = publishing_day_count(day) % len(PERSONAS)
    return PERSONAS[index]


def gather_grounding_material(as_of: date, lookback_days: int = LOOKBACK_DAYS) -> list[dict]:
    """Collect parsed digests from the last `lookback_days` calendar days, Brazil + broader Mercosur.

    Reuses digest_path/parse_country_digest from weekly_briefing.py. Looks at
    days strictly before `as_of` (the day's own digest may not exist yet when
    the OpEd runs).
    """
    entries = []
    for country in COUNTRY_ORDER:
        for offset in range(1, lookback_days + 1):
            day = as_of - timedelta(days=offset)
            path = digest_path(country, day)
            if os.path.exists(path):
                entries.append(parse_country_digest(path, country, day))
    entries.sort(key=lambda e: (e["date"], e["country"]), reverse=True)
    return entries


def format_grounding_material(entries: list[dict]) -> str:
    if not entries:
        return "(No recent digest material available.)"
    blocks = []
    for e in entries:
        flag = FLAGS.get(e["country"], "")
        name = COUNTRY_DISPLAY_NAMES.get(e["country"], e["country"].capitalize())
        block = f"### {flag} {name} — {e['date']}\nTITLE: {e['title']}\n\n{e['narrative']}"
        if e["corporate_watch"]:
            block += f"\n\n{e['corporate_watch']}"
        blocks.append(block)
    return "\n\n---\n\n".join(blocks)


def build_prompt(persona, entries: list[dict]) -> str:
    return PROMPT_TEMPLATE.format(
        name=persona.name,
        voice=persona.voice,
        style=persona.style,
        lookback_days=LOOKBACK_DAYS,
        grounding_material=format_grounding_material(entries),
    )


def generate_body(prompt: str, client) -> str:
    with client.messages.stream(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for _ in stream.text_stream:
            pass
        final_message = stream.get_final_message()
    if final_message.stop_reason == "max_tokens":
        logger.warning("OpEd generation hit max_tokens — output may be truncated.")
    return final_message.content[0].text.strip()


def generate_headline(persona, body: str, client) -> str:
    response = client.messages.create(
        model=HEADLINE_MODEL,
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": (
                f"Write a headline (max 12 words) for the opinion column below, written by "
                f"{persona.name} ({persona.lens}). The headline should reflect the columnist's "
                "argument or thesis — not a neutral summary of the underlying news event. It "
                "should read like an opinion-section headline: pointed, not hedged.\n\n"
                "Return ONLY the final headline, nothing else.\n\n" + body
            ),
        }],
    )
    return response.content[0].text.strip()


def save_oped(persona, day: date, title: str, body: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"{persona.slug}_{day.isoformat()}.md")
    content = (
        f"> PERSONA: {persona.name}\n"
        f"> LENS: {persona.lens}\n"
        f"> TITLE: {title}\n"
        f"> DATE: {day.isoformat()}\n\n"
        f"{body}"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def run(target_date: date, dry_run: bool) -> None:
    if not is_publishing_day(target_date):
        logger.info(
            f"{target_date.isoformat()} ({target_date.strftime('%A')}) is not a Mon/Wed/Fri "
            "publishing day — nothing to do."
        )
        return

    persona = persona_for_date(target_date)
    entries = gather_grounding_material(target_date)
    prompt = build_prompt(persona, entries)

    if dry_run:
        print(f"=== DRY RUN — OpEd for {target_date.isoformat()} ({target_date.strftime('%A')}) ===\n")
        print(f"Publishing day count since {OPED_START_DATE.isoformat()}: {publishing_day_count(target_date)}")
        print(f"Persona selected: {persona.name} ({persona.slug})")
        print(f"Lens: {persona.lens}\n")
        print(f"Grounding material — {len(entries)} digest(s) found in last {LOOKBACK_DAYS} days:")
        for e in entries:
            print(f"  [{e['country']}] {e['date']} — {e['title']}")
        print("\n--- PROMPT ---\n")
        print(prompt)
        print("\nDry run — Sonnet API not called, no file saved.")
        return

    import anthropic
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
    client = anthropic.Anthropic(api_key=api_key)

    logger.info(f"Generating OpEd for {target_date.isoformat()} as {persona.name} ({persona.lens})…")
    body = generate_body(prompt, client)
    title = generate_headline(persona, body, client)

    path = save_oped(persona, target_date, title, body)
    logger.info(f"OpEd saved to {path}")

    word_count = len(body.split())
    print(f"\n=== SUMMARY ===")
    print(f"Persona: {persona.name} ({persona.lens})")
    print(f"Title: {title}")
    print(f"Word count: {word_count}")
    print(f"Saved to: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the rotating Mercosur/Brazil OpEd column.")
    parser.add_argument("--date", default=None, help="Publishing date (YYYY-MM-DD, must be Mon/Wed/Fri); defaults to today")
    parser.add_argument("--dry-run", action="store_true", help="Show persona selection and prompt without calling the API or saving")
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date) if args.date else date.today()

    try:
        run(target_date, args.dry_run)
    except Exception as exc:
        logger.error(f"OpEd generation failed: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
