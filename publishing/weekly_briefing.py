"""Generate the Mercosur Weekly Briefing from the week's daily digests."""

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
sys.path.insert(0, SCRIPT_DIR)

from x_poster import COUNTRY_OUTPUT_DIRS, FLAGS, REPO_ROOT, SITE_BASE_URL  # noqa: E402

COUNTRY_ORDER = ["brazil", "argentina", "chile", "uruguay", "paraguay", "bolivia"]

COUNTRY_DISPLAY_NAMES = {
    "argentina": "Argentina",
    "brazil": "Brazil",
    "chile": "Chile",
    "uruguay": "Uruguay",
    "paraguay": "Paraguay",
    "bolivia": "Bolivia",
}

WEEKLY_OUTPUT_DIR = os.path.join(REPO_ROOT, "digests", "weekly")

MODEL = "claude-sonnet-4-6"

EDITOR_INSTRUCTIONS = """You are the editor of 24EcoNews, a weekly economic briefing covering the Mercosur region for a global audience of investors, analysts, and business professionals.

Below are this week's daily digest narratives for 6 countries: Argentina, Brazil, Chile, Uruguay, Paraguay and Bolivia.

Write a Mercosur Weekly Briefing with this structure:

---
Before the main title, write a short 1-2 sentence email greeting that feels personal and editorial — as if written by the editor introducing this week's briefing to a subscriber. It should set the tone for what's inside without repeating the Big Picture content. Vary the opening style week to week (don't always start with "Good morning"). Examples of tone (write an original one, don't reuse these):

- "This week Mercosur delivered a masterclass in contradiction — bold reforms paired with mounting fiscal strain."
- "Six countries, one currency regime abandoned, and a growing sense that the region's reform momentum is outrunning its fiscal cushion. Here's what mattered this week."
- "From Bolivia's historic currency shift to Chile's fifth straight month of contraction, this week tested the region's resilience. Here's your briefing."

After the greeting sentences, on their own line, add a signature:

— John Dominguez, Editor

Example format:
"This week Mercosur delivered a masterclass in contradiction — bold reforms paired with mounting fiscal strain.

— John Dominguez, Editor"

Keep the greeting itself to 1-2 sentences maximum, followed by the signature line, followed by a blank line, then the main title.

# Mercosur Weekly Briefing — Week of {monday_display} to {thursday_display}

## The Big Picture
2-3 paragraphs identifying the dominant theme or themes that ran across the region this week. What connected these economies? What diverged? What should a global investor take away from this week in Mercosur? Write with authority and specificity — name the data points, the companies, the policy decisions that mattered most.

## Country by Country

### 🇧🇷 Brazil
2-3 sentences on the week's most important Brazilian development.
Link: [BRAZIL_URL]

### 🇦🇷 Argentina
2-3 sentences on the week's most important Argentine development.
Link: [ARGENTINA_URL]

### 🇨🇱 Chile
2-3 sentences on the week's most important Chilean development.
Link: [CHILE_URL]

### 🇺🇾 Uruguay
2-3 sentences on the week's most important Uruguayan development.
Link: [URUGUAY_URL]

### 🇵🇾 Paraguay
2-3 sentences on the week's most important Paraguayan development.
Link: [PARAGUAY_URL]

### 🇧🇴 Bolivia
2-3 sentences on the week's most important Bolivian development.
Link: [BOLIVIA_URL]

## Corporate Watch of the Week
If notable corporate stories appeared this week across any country's Corporate Watch section, highlight the 2-3 most globally significant ones here in brief.
(Skip this section if no significant corporate stories this week)

## What to Watch Next Week
2-3 bullet points identifying the economic storylines, data releases, or political events across the region that global readers should track in the coming week.

---

Tone: Bloomberg Markets meets The Economist. Authoritative, specific, globally relevant. No filler sentences. Every sentence should earn its place.

Use the exact [COUNTRY_URL] links given in the DATA section below for each country's "Link:" line — do not invent or alter them. Replace [BRAZIL_URL], [ARGENTINA_URL], etc. with the real URLs provided.

Output only the briefing itself, starting directly with the email greeting. Do not include any preamble, meta-commentary, or introductory sentence like "Here is this week's briefing" before the greeting, and do not wrap the output in a leading "---" separator."""


def monday_of_week(week_arg: str | None) -> date:
    """Return the Monday for --week (YYYY-MM-DD of that Monday), or this week's Monday."""
    if week_arg:
        d = date.fromisoformat(week_arg)
        if d.weekday() != 0:
            raise ValueError(f"--week must be a Monday (YYYY-MM-DD); {week_arg} is a {d.strftime('%A')}")
        return d
    today = date.today()
    return today - timedelta(days=today.weekday())


def digest_path(country: str, day: date) -> str:
    output_dir = COUNTRY_OUTPUT_DIRS[country]
    filename = f"digest_{day.isoformat()}.en.md"
    return os.path.join(REPO_ROOT, output_dir, filename)


def find_most_recent_digest(country: str, week_days: list[date]) -> tuple[str, date] | None:
    """Return (path, day) for the most recent existing digest in week_days, or None."""
    for day in reversed(week_days):
        path = digest_path(country, day)
        if os.path.exists(path):
            return path, day
    return None


def parse_country_digest(path: str, country: str, day: date) -> dict:
    with open(path, encoding="utf-8") as f:
        content = f.read()

    title_match = re.search(r"^>\s*TITLE:\s*(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else ""

    lines = content.split("\n")
    i = 0
    while i < len(lines) and lines[i].startswith(">"):
        i += 1
    if i < len(lines) and lines[i].strip() == "":
        i += 1
    body = "\n".join(lines[i:])

    body = re.split(r"\n---\s*\n##\s*Related Coverage", body)[0]

    body_lines = [
        ln
        for ln in body.split("\n")
        if not (ln.strip().startswith("#") and not ln.strip().startswith("##"))
        and not (ln.strip().startswith("*") and ln.strip().endswith("*") and len(ln.strip()) > 1)
    ]
    body = "\n".join(body_lines).strip()

    cw_match = re.search(r"(##\s*Corporate Watch.*)", body, re.DOTALL)
    if cw_match:
        corporate_watch = cw_match.group(1).strip()
        narrative = body[: cw_match.start()].strip()
    else:
        corporate_watch = None
        narrative = body.strip()

    url = f"{SITE_BASE_URL}/{country}/{day.isoformat()}"
    return {
        "country": country,
        "title": title,
        "narrative": narrative,
        "corporate_watch": corporate_watch,
        "url": url,
        "date": day.isoformat(),
    }


def gather_week(monday: date) -> tuple[list[date], dict]:
    """Return (week_days [Mon..Thu], {country: parsed_digest_or_None})."""
    week_days = [monday + timedelta(days=i) for i in range(4)]
    results = {}
    for country in COUNTRY_ORDER:
        found = find_most_recent_digest(country, week_days)
        if found is None:
            logger.warning(f"[{country}] No digest found for week of {monday.isoformat()}")
            results[country] = None
            continue
        path, day = found
        results[country] = parse_country_digest(path, country, day)
        logger.info(f"[{country}] Using digest from {day.isoformat()} ({path})")
    return week_days, results


def build_prompt(monday: date, thursday: date, country_data: dict) -> str:
    monday_display = monday.strftime("%B %-d, %Y") if os.name != "nt" else monday.strftime("%B %d, %Y")
    thursday_display = thursday.strftime("%B %-d, %Y") if os.name != "nt" else thursday.strftime("%B %d, %Y")

    instructions = EDITOR_INSTRUCTIONS.format(
        monday_display=monday_display,
        thursday_display=thursday_display,
    )

    data_blocks = ["\n\n---\nDATA FOR THIS WEEK:\n"]
    for country in COUNTRY_ORDER:
        data = country_data.get(country)
        flag = FLAGS[country]
        name = COUNTRY_DISPLAY_NAMES[country]
        if data is None:
            data_blocks.append(f"\n### {flag} {name}\n(No digest available this week — omit or note briefly.)\n")
            continue
        block = (
            f"\n### {flag} {name}\n"
            f"TITLE: {data['title']}\n"
            f"URL: {data['url']}\n"
            f"NARRATIVE:\n{data['narrative']}\n"
        )
        if data["corporate_watch"]:
            block += f"\n{data['corporate_watch']}\n"
        data_blocks.append(block)

    return instructions + "\n".join(data_blocks)


def generate_briefing(prompt: str) -> str:
    import anthropic
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")

    client = anthropic.Anthropic(api_key=api_key)
    # Use streaming: this completion runs long enough that non-streaming requests
    # get dropped by intermediaries before the response arrives ("Server disconnected
    # without sending a response"). Streaming keeps the connection alive.
    with client.messages.stream(
        model=MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for _ in stream.text_stream:
            pass
        final_message = stream.get_final_message()
    if final_message.stop_reason == "max_tokens":
        logger.warning("Briefing generation hit max_tokens — output may be truncated. Consider raising max_tokens.")
    return final_message.content[0].text.strip()


def save_briefing(content: str, thursday: date) -> str:
    os.makedirs(WEEKLY_OUTPUT_DIR, exist_ok=True)
    path = os.path.join(WEEKLY_OUTPUT_DIR, f"briefing_{thursday.isoformat()}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def count_corporate_watch_items(content: str) -> int:
    """Count items in the generated briefing's own 'Corporate Watch of the Week' section."""
    match = re.search(r"##\s*Corporate Watch of the Week\s*\n(.*?)(?=\n##\s|\Z)", content, re.DOTALL)
    if not match:
        return 0
    section = match.group(1).strip()
    if not section or section.lower().startswith("(skip") or section.lower().startswith("skip"):
        return 0
    items = re.findall(r"^\*\*.+?\*\*", section, re.MULTILINE)
    if items:
        return len(items)
    return len([p for p in section.split("\n\n") if p.strip()])


def print_summary(content: str, country_data: dict) -> None:
    word_count = len(content.split())
    countries_covered = [c for c in COUNTRY_ORDER if country_data.get(c) is not None]
    cw_count = count_corporate_watch_items(content)

    print("\n=== SUMMARY ===")
    print(f"Word count: {word_count}")
    print(f"Countries covered: {len(countries_covered)}/6 ({', '.join(countries_covered)})")
    print(f"Corporate Watch items found: {cw_count}")


def run(week_arg: str | None, dry_run: bool) -> None:
    monday = monday_of_week(week_arg)
    thursday = monday + timedelta(days=3)
    week_days = [monday + timedelta(days=i) for i in range(4)]

    logger.info(f"=== Weekly Briefing — week of {monday.isoformat()} to {thursday.isoformat()} ===")

    if dry_run:
        print(f"=== DRY RUN — week of {monday.isoformat()} (Mon) to {thursday.isoformat()} (Thu) ===\n")
        for country in COUNTRY_ORDER:
            found = find_most_recent_digest(country, week_days)
            if found is None:
                candidates = ", ".join(digest_path(country, d) for d in week_days)
                print(f"[{country}] NOT FOUND — checked: {candidates}")
            else:
                path, day = found
                print(f"[{country}] Would use: {path} (dated {day.isoformat()})")
        print(f"\nDate range covered: {monday.isoformat()} (Mon) through {thursday.isoformat()} (Thu)")
        print("Dry run — Sonnet API not called, no file saved.")
        return

    _, country_data = gather_week(monday)
    if all(v is None for v in country_data.values()):
        raise RuntimeError(f"No digests found for any country in week of {monday.isoformat()} — aborting")

    prompt = build_prompt(monday, thursday, country_data)

    logger.info("Generating weekly briefing via Claude Sonnet…")
    briefing = generate_briefing(prompt)

    path = save_briefing(briefing, thursday)
    logger.info(f"Weekly briefing saved to {path}")

    print(briefing)
    print_summary(briefing, country_data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the Mercosur Weekly Briefing.")
    parser.add_argument("--week", default=None, help="Monday (YYYY-MM-DD) of the week to generate; defaults to this week")
    parser.add_argument("--dry-run", action="store_true", help="Show inputs without calling the API or saving")
    args = parser.parse_args()

    try:
        run(args.week, args.dry_run)
    except Exception as exc:
        logger.error(f"Weekly briefing failed: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
