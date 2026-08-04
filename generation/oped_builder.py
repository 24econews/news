"""Generate the Mercosur OpEd piece for 24EcoNews's Opinion section.

Publishes Monday/Wednesday/Friday, cycling deterministically through five
recurring opinion columnists (see oped_personas.py). Each piece is grounded
in recent Brazil and Mercosur-wide daily digests but argued from the
assigned columnist's stated ideological perspective.
"""

import argparse
import logging
import os
import re
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

from generation.oped_personas import PERSONAS, PERSONAS_BY_SLUG, Persona  # noqa: E402
from publishing.weekly_briefing import (  # noqa: E402
    COUNTRY_DISPLAY_NAMES,
    COUNTRY_ORDER,
    FLAGS,
    digest_path,
    parse_country_digest,
)

OPED_OUTPUT_DIR = os.path.join(REPO_ROOT, "digests", "opinion")

MODEL = "claude-sonnet-4-6"

# Fixed reference point for the rotation — the first Monday the OpEd
# section is live. Persona assignment is computed from the count of
# Mon/Wed/Fri publishing days elapsed since this date, so no external
# state (files, DB) is needed to know whose turn it is.
START_DATE = date(2026, 8, 3)

OPED_WEEKDAYS = (0, 2, 4)  # Monday, Wednesday, Friday

OPINION_PROMPT_TEMPLATE = """You are {name}, {lens}, writing a 600-800 word opinion column for 24EcoNews's Opinion section.

Your rhetorical style: {style}

Below is recent factual reporting on Brazil and Mercosur economic and political developments.

Before selecting your subject, briefly survey the grounding material from ALL SIX countries — Brazil, Argentina, Chile, Uruguay, Paraguay, and Bolivia — not just the country with the most coverage that week. Brazil often generates the most dramatic headlines simply due to its size and market attention, but do not default to it for that reason alone. Actively consider whether Argentina, Chile, Uruguay, Paraguay, or Bolivia offers a more genuinely contestable, opinion-worthy angle this week — a story where reasonable people looking at the same facts would draw different conclusions.

Over time, this column should reflect the full breadth of the Mercosur region, not become a Brazil-only column. Weight your selection accordingly.
{country_nudge}
Select the single most opinion-worthy story or tension from this material — something genuinely contestable, not settled consensus.

Write a sharp, well-argued opinion piece from your stated ideological perspective. Your argument MUST be grounded in the real facts, figures, and events provided below — do not fabricate data, quotes, or events. You may interpret, emphasize, and draw conclusions the underlying reporting doesn't state explicitly, but the underlying facts must be real and traceable to the source material.

Write with conviction and a clear point of view — this is opinion writing, not neutral reporting. Be willing to criticize your own 'side' when the facts warrant it; intellectual honesty matters more than ideological consistency.

Structure: a sharp opening that states your thesis, 3-4 paragraphs of argument grounded in specific facts, a closing that doesn't hedge.

Do not include a byline or title — just the piece itself."""

# Word-boundary patterns for each country's name plus its common English
# adjectival form (e.g. "Brazilian"), used to mechanically infer which
# country a past piece was actually about — see infer_primary_country().
COUNTRY_MENTION_PATTERNS = {
    "brazil": r"Brazil(?:ian)?",
    "argentina": r"Argentin(?:a|e|ian)",
    "chile": r"Chile|Chilean",
    "uruguay": r"Uruguay(?:an)?",
    "paraguay": r"Paraguay(?:an)?",
    "bolivia": r"Bolivia(?:n)?",
}


def is_oped_day(day: date) -> bool:
    return day.weekday() in OPED_WEEKDAYS


def _count_oped_days_before(day: date) -> int:
    """Count Mon/Wed/Fri dates in [START_DATE, day)."""
    if day <= START_DATE:
        return 0
    count = 0
    cur = START_DATE
    while cur < day:
        if is_oped_day(cur):
            count += 1
        cur += timedelta(days=1)
    return count


def persona_for_date(day: date) -> Persona:
    if not is_oped_day(day):
        raise ValueError(f"{day.isoformat()} is not an OpEd day (Mon/Wed/Fri)")
    index = _count_oped_days_before(day) % len(PERSONAS)
    return PERSONAS[index]


def gather_recent_digests(reference_day: date, lookback_days: int = 5) -> list[dict]:
    """Return parsed digests for Brazil + Mercosur from the lookback window, most recent last."""
    days = [reference_day - timedelta(days=i) for i in range(lookback_days)]
    days.reverse()  # oldest first, so material reads chronologically

    results = []
    for country in COUNTRY_ORDER:
        for day in days:
            path = digest_path(country, day)
            if os.path.exists(path):
                results.append(parse_country_digest(path, country, day))
                logger.info(f"[{country}] Using digest from {day.isoformat()} ({path})")
    return results


def infer_primary_country(piece_body: str) -> str | None:
    """Infer which country a past piece was mainly about by counting name mentions.

    Returns None when no country has a clear plurality (zero mentions, or a
    tie for the top spot) — an ambiguous piece shouldn't count toward or
    break a streak either way.
    """
    counts = {
        country: len(re.findall(rf"\b(?:{pattern})\b", piece_body, re.IGNORECASE))
        for country, pattern in COUNTRY_MENTION_PATTERNS.items()
    }
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    top_country, top_count = ranked[0]
    runner_up_count = ranked[1][1]
    if top_count == 0 or top_count == runner_up_count:
        return None
    return top_country


def _strip_oped_body(content: str) -> str:
    """Strip the '> FIELD: ...' metadata block and trailing bio disclosure, mirroring save_oped's format."""
    lines = content.split("\n")
    i = 0
    while i < len(lines) and lines[i].startswith(">"):
        i += 1
    if i < len(lines) and lines[i].strip() == "":
        i += 1
    body = "\n".join(lines[i:])
    return body.split("\n---\n")[0].strip()


def get_recent_country_streak(before_day: date, lookback_files: int = 10) -> list[str]:
    """Return inferred primary countries for the most recent published pieces before before_day, newest first."""
    if not os.path.isdir(OPED_OUTPUT_DIR):
        return []

    filename_re = re.compile(r"^([a-z-]+)_(\d{4}-\d{2}-\d{2})\.md$")
    dated_files = []
    for fname in os.listdir(OPED_OUTPUT_DIR):
        match = filename_re.match(fname)
        if not match:
            continue
        file_date = date.fromisoformat(match.group(2))
        if file_date < before_day:
            dated_files.append((file_date, fname))
    dated_files.sort(key=lambda t: t[0], reverse=True)

    countries = []
    for _, fname in dated_files[:lookback_files]:
        with open(os.path.join(OPED_OUTPUT_DIR, fname), encoding="utf-8") as f:
            body = _strip_oped_body(f.read())
        country = infer_primary_country(body)
        if country:
            countries.append(country)
    return countries


def build_prompt(persona: Persona, digests: list[dict], force_non_brazil: bool = False) -> str:
    country_nudge = ""
    if force_non_brazil:
        country_nudge = (
            "\nIMPORTANT: The last two published OpEd pieces both focused primarily on Brazil. "
            "This piece MUST focus on a different country — Argentina, Chile, Uruguay, Paraguay, "
            "or Bolivia. Do not select Brazil as your subject this time, even if its news is more "
            "dramatic.\n"
        )

    instructions = OPINION_PROMPT_TEMPLATE.format(
        name=persona.name,
        lens=persona.lens_full,
        style=persona.style,
        country_nudge=country_nudge,
    )

    material_blocks = ["\n\n---\nRECENT REPORTING (Brazil and Mercosur):\n"]
    for d in digests:
        flag = FLAGS[d["country"]]
        name = COUNTRY_DISPLAY_NAMES[d["country"]]
        block = f"\n### {flag} {name} — {d['date']}\nTITLE: {d['title']}\n{d['narrative']}\n"
        if d["corporate_watch"]:
            block += f"\n{d['corporate_watch']}\n"
        material_blocks.append(block)

    return instructions + "\n".join(material_blocks)


def generate_oped(prompt: str) -> str:
    import anthropic
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")

    client = anthropic.Anthropic(api_key=api_key)
    with client.messages.stream(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for _ in stream.text_stream:
            pass
        final_message = stream.get_final_message()
    if final_message.stop_reason == "max_tokens":
        logger.warning("OpEd generation hit max_tokens — output may be truncated. Consider raising max_tokens.")
    return final_message.content[0].text.strip()


def generate_headline(piece: str) -> str:
    import anthropic
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        messages=[{
            "role": "user",
            "content": (
                "Write a headline (max 12 words) that captures the central thesis of "
                "the opinion column below. It should read like an op-ed headline — "
                "pointed and specific to the argument, not a generic topic summary.\n\n"
                "Return ONLY the final headline, nothing else.\n\n" + piece
            ),
        }],
    )
    return response.content[0].text.strip()


def save_oped(persona: Persona, day: date, headline: str, piece: str) -> str:
    os.makedirs(OPED_OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OPED_OUTPUT_DIR, f"{persona.slug}_{day.isoformat()}.md")
    metadata = (
        f"> PERSONA: {persona.name}\n"
        f"> LENS: {persona.lens_short}\n"
        f"> TITLE: {headline}\n"
        f"> DATE: {day.isoformat()}\n"
    )
    # Deterministic, code-appended disclosure — not left to Sonnet to include or phrase.
    bio_block = f"\n---\n\n*{persona.bio}*\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(metadata + "\n" + piece + "\n" + bio_block)
    return path


def run(date_arg: str | None, dry_run: bool, lookback_days: int, force: bool, persona_slug: str | None = None) -> None:
    day = date.fromisoformat(date_arg) if date_arg else date.today()

    if not is_oped_day(day):
        raise ValueError(
            f"{day.isoformat()} ({day.strftime('%A')}) is not an OpEd day — "
            "OpEd pieces publish Monday, Wednesday, and Friday only."
        )

    if persona_slug is not None:
        if persona_slug not in PERSONAS_BY_SLUG:
            raise ValueError(
                f"Unknown persona slug {persona_slug!r} — expected one of {sorted(PERSONAS_BY_SLUG)}"
            )
        persona = PERSONAS_BY_SLUG[persona_slug]
        logger.info(f"--persona override: forcing columnist {persona.name} (rotation would assign {persona_for_date(day).name})")
    else:
        persona = persona_for_date(day)

    logger.info(f"=== OpEd for {day.isoformat()} ({day.strftime('%A')}) — columnist: {persona.name} ===")

    existing_path = os.path.join(OPED_OUTPUT_DIR, f"{persona.slug}_{day.isoformat()}.md")
    if not dry_run and os.path.exists(existing_path) and not force:
        raise FileExistsError(
            f"{existing_path} already exists — pass --force to regenerate and overwrite it."
        )

    digests = gather_recent_digests(day, lookback_days)
    if not digests:
        raise RuntimeError(
            f"No digest material found in the {lookback_days} days ending {day.isoformat()} — aborting"
        )

    recent_countries = get_recent_country_streak(day)
    force_non_brazil = len(recent_countries) >= 2 and recent_countries[0] == "brazil" and recent_countries[1] == "brazil"
    if force_non_brazil:
        logger.info(f"Last 2 published pieces were both Brazil-focused ({recent_countries[:2]}) — forcing a non-Brazil subject this run")

    prompt = build_prompt(persona, digests, force_non_brazil)

    if dry_run:
        print(f"=== DRY RUN — OpEd for {day.isoformat()} ({day.strftime('%A')}) ===\n")
        print(f"Columnist:  {persona.name}")
        print(f"Lens:       {persona.lens_short}")
        print(f"Slug:       {persona.slug}")
        if persona_slug is not None:
            print(f"Rotation index: {_count_oped_days_before(day) % len(PERSONAS)} (of {len(PERSONAS)}) — OVERRIDDEN via --persona, would normally be {persona_for_date(day).name}")
        else:
            print(f"Rotation index: {_count_oped_days_before(day) % len(PERSONAS)} (of {len(PERSONAS)})")
        print(f"\nGrounding material: {len(digests)} digest(s) from {lookback_days}-day lookback")
        for d in digests:
            print(f"  - [{d['country']}] {d['date']}: {d['title']}")
        print(f"\nRecent country streak (newest first, up to 10): {recent_countries}")
        print(f"Force non-Brazil this run: {force_non_brazil}")
        print(f"\nWould save to: {os.path.join(OPED_OUTPUT_DIR, f'{persona.slug}_{day.isoformat()}.md')}")
        print("\n--- FULL PROMPT ---\n")
        print(prompt)
        print("\nDry run — Sonnet API not called, no file saved.")
        return

    logger.info("Generating OpEd piece via Claude Sonnet…")
    piece = generate_oped(prompt)

    logger.info("Generating headline via Claude Haiku…")
    headline = generate_headline(piece)

    path = save_oped(persona, day, headline, piece)
    logger.info(f"OpEd piece saved to {path}")

    word_count = len(piece.split())
    inferred_country = infer_primary_country(piece)
    print(piece)
    print("\n=== SUMMARY ===")
    print(f"Columnist: {persona.name} ({persona.lens_short})")
    print(f"Headline: {headline}")
    print(f"Word count: {word_count}")
    print(f"Inferred subject country: {inferred_country or 'unclear'}")
    if not (600 <= word_count <= 800):
        logger.warning(f"Word count {word_count} is outside the target 600-800 range.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the Mercosur OpEd piece for 24EcoNews's Opinion section.")
    parser.add_argument("--date", default=None, help="Publication date (YYYY-MM-DD), must be Mon/Wed/Fri; defaults to today")
    parser.add_argument("--lookback-days", type=int, default=5, help="How many days of digests to use as grounding material (default 5)")
    parser.add_argument("--dry-run", action="store_true", help="Show persona selection and prompt without calling the API or saving")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing OpEd file for this persona/date instead of erroring")
    parser.add_argument("--persona", default=None, choices=sorted(PERSONAS_BY_SLUG), help="TESTING ONLY: override the rotation and force a specific persona by slug")
    args = parser.parse_args()

    try:
        run(args.date, args.dry_run, args.lookback_days, args.force, args.persona)
    except Exception as exc:
        logger.error(f"OpEd generation failed: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
