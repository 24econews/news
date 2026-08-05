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
from oped_bluesky_poster import parse_oped  # noqa: E402 (sibling module in publishing/, reuses its PERSONA/LENS/TITLE parsing)

OPED_DIR = os.path.join(REPO_ROOT, "digests", "opinion")

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

Below are this week's daily digest narratives for 6 countries: Argentina, Brazil, Chile, Uruguay, Paraguay and Bolivia — with MULTIPLE dated digests provided per country (Monday through Friday, whichever days exist), each with its own URL. Also below, in OPED DATA, are any Opinion columns published since last week's briefing.

Write a Mercosur Weekly Briefing with this structure:

---
Before the main content, write a short 1-2 sentence email greeting that feels personal and editorial — as if written by the editor introducing this week's briefing to a subscriber. It should set the tone for what's inside without repeating the Big Picture content. Vary the opening style week to week (don't always start with "Good morning"). Examples of tone (write an original one, don't reuse these):

- "This week Mercosur delivered a masterclass in contradiction — bold reforms paired with mounting fiscal strain."
- "Six countries, one currency regime abandoned, and a growing sense that the region's reform momentum is outrunning its fiscal cushion. Here's what mattered this week."
- "From Bolivia's historic currency shift to Chile's fifth straight month of contraction, this week tested the region's resilience. Here's your briefing."

After the greeting sentences, on their own line, add a signature:

— John Dominguez, Editor

Example format:
"This week Mercosur delivered a masterclass in contradiction — bold reforms paired with mounting fiscal strain.

— John Dominguez, Editor"

Keep the greeting itself to 1-2 sentences maximum, followed by the signature line, followed by a blank line, then directly the "## The Big Picture" section below. Do NOT write a title or headline of your own — a headline is generated separately and prepended to your output afterward.

## The Big Picture
2-3 paragraphs identifying the dominant theme or themes that ran across the region this week. What connected these economies? What diverged? What should a global investor take away from this week in Mercosur? Write with authority and specificity — name the data points, the companies, the policy decisions that mattered most.

When you reference a specific country's development, hyperlink that reference to its corresponding digest URL from the DATA section below — e.g., "[Argentina's inflation surprise](URL)" — using the exact URL for the specific day that development was reported. Multiple hyperlinks within this section are expected and encouraged: it should read as richly linked, letting readers jump directly to the source digest for whatever specifically interests them. Only use URLs provided in the DATA section — never invent or alter one.

## Country by Country

For each of the 6 countries, write 3-4 short bullet points (fewer only if fewer days of digest data are available for that country — never invent content or pad with a repeated point). Each bullet must:
- Cover a distinct development or angle — do not restate the same story across a country's bullets
- Link to the specific day's digest most relevant to that bullet, using the exact URL from the DATA section for that day
- Actively vary which day you link across a country's bullets — a reader browsing that country's bullets should end up with links to several different days' digests, not the same (likely most recent) digest repeated every time

Each bullet must be ONE clear fact or development, stated in 15-25 words maximum. Do not combine multiple data points, causes, and consequences into a single bullet — if a story has three important facets, that's three separate bullets, not one bullet with three clauses joined by commas or em-dashes.

Bad example (too dense, avoid this): "Petrobras posted an all-time production record of 3.336 million barrels of oil equivalent per day in Q2, up 14% year-on-year, driven by the pre-salt layer and the early startup of the FPSO P-79 at Búzios — roughly three months ahead of schedule"

Good example (single fact, scannable): "Petrobras hit an all-time production record: 3.336 million barrels/day in Q2, up 14% year-on-year."

Each bullet should be readable in under 5 seconds. The goal is a reader can scan a country's 3-4 bullets in 15-20 seconds total and grasp the week's key developments — not read four mini-paragraphs.

Format:
### 🇧🇷 Brazil
- [Specific development, one sentence](url for the most relevant day)
- [Specific development, one sentence](url for a different day)
- [Specific development, one sentence](url for yet another day)

### 🇦🇷 Argentina
- [Specific development, one sentence](url)
- ...

(continue in this order: Brazil, Argentina, Chile, Uruguay, Paraguay, Bolivia)

## Corporate Watch of the Week
If notable corporate stories appeared this week across any country's Corporate Watch section, highlight the 2-3 most globally significant ones here in brief.
(Skip this section if no significant corporate stories this week)

## Opinion This Week
If pieces are listed in the OPED DATA section below, list each one here in this exact format:

**[Headline]** — By [Persona Name], [Lens]
[One sentence summary or hook capturing the piece's core argument, based on its excerpt in OPED DATA]
[Link to the piece, using its exact URL from OPED DATA]

If OPED DATA below has no pieces, omit this "## Opinion This Week" section entirely — do not include the header with no content beneath it, and do not write a note saying no pieces were published.

## What to Watch Next Week
2-3 bullet points identifying the economic storylines, data releases, or political events across the region that global readers should track in the coming week.

---

Tone: Bloomberg Markets meets The Economist. Authoritative, specific, globally relevant. No filler sentences. Every sentence should earn its place.

Use only the exact URLs given in the DATA and OPED DATA sections below for any link — never invent or alter one.

Output only the briefing itself, starting directly with the email greeting. Do not include any preamble, meta-commentary, or introductory sentence like "Here is this week's briefing" before the greeting, and do not wrap the output in a leading "---" separator. Do not include a top-level title or headline line anywhere — start with the greeting and end with "What to Watch Next Week"."""


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


def gather_week(week_days: list[date]) -> dict:
    """Return {country: [parsed_digest, ...]}, oldest first, for every day in week_days that has a digest."""
    results = {}
    for country in COUNTRY_ORDER:
        digests = []
        for day in week_days:
            path = digest_path(country, day)
            if os.path.exists(path):
                digests.append(parse_country_digest(path, country, day))
                logger.info(f"[{country}] Using digest from {day.isoformat()} ({path})")
        if not digests:
            logger.warning(f"[{country}] No digests found for week of {week_days[0].isoformat()}")
        results[country] = digests
    return results


def gather_recent_opeds(since_day: date, until_day: date) -> list[dict]:
    """Return OpEd pieces published in (since_day, until_day], most recent first.

    Reuses oped_bluesky_poster.py's parse_oped() for the PERSONA/LENS/TITLE
    metadata extraction and body-sentence splitting, rather than re-implementing
    that parsing a third time.
    """
    if not os.path.isdir(OPED_DIR):
        return []

    filename_re = re.compile(r"^([a-z-]+)_(\d{4}-\d{2}-\d{2})\.md$")
    results = []
    for fname in os.listdir(OPED_DIR):
        match = filename_re.match(fname)
        if not match:
            continue
        slug, date_str = match.group(1), match.group(2)
        oped_date = date.fromisoformat(date_str)
        if not (since_day < oped_date <= until_day):
            continue

        path = os.path.join(OPED_DIR, fname)
        try:
            persona_name, lens_short, title, sentences = parse_oped(path)
        except ValueError as exc:
            logger.warning(f"[weekly_briefing] Skipping unparseable OpEd file {fname}: {exc}")
            continue

        results.append({
            "slug": slug,
            "date": date_str,
            "persona_name": persona_name,
            "lens_short": lens_short,
            "title": title,
            "excerpt": " ".join(sentences[:2]),
            "url": f"{SITE_BASE_URL}/opinion/{slug}/{date_str}",
        })
        logger.info(f"[weekly_briefing] Including OpEd {slug}_{date_str} in roundup")

    results.sort(key=lambda o: o["date"], reverse=True)
    return results


def _day_display(d: date) -> str:
    return d.strftime("%A, %B %-d") if os.name != "nt" else d.strftime("%A, %B %d")


def build_prompt(country_data: dict, oped_pieces: list[dict]) -> str:
    data_blocks = ["\n\n---\nDATA FOR THIS WEEK:\n"]
    for country in COUNTRY_ORDER:
        digests = country_data.get(country) or []
        flag = FLAGS[country]
        name = COUNTRY_DISPLAY_NAMES[country]
        if not digests:
            data_blocks.append(f"\n### {flag} {name}\n(No digests available this week — omit or note briefly.)\n")
            continue

        block_parts = [f"\n### {flag} {name}\n"]
        for data in digests:
            day_display = _day_display(date.fromisoformat(data["date"]))
            block_parts.append(
                f"📅 {day_display} — URL: {data['url']}\n"
                f"TITLE: {data['title']}\n"
                f"NARRATIVE:\n{data['narrative']}\n"
            )
            if data["corporate_watch"]:
                block_parts.append(f"{data['corporate_watch']}\n")
        data_blocks.append("\n".join(block_parts))

    data_blocks.append("\n\n---\nOPED DATA (Opinion pieces published since last week's briefing):\n")
    if oped_pieces:
        for oped in oped_pieces:
            data_blocks.append(
                f"\n### {oped['persona_name']} — {oped['lens_short']} ({oped['date']})\n"
                f"TITLE: {oped['title']}\n"
                f"URL: {oped['url']}\n"
                f"EXCERPT: {oped['excerpt']}\n"
            )
    else:
        data_blocks.append("\n(No OpEd pieces were published since last week's briefing — omit the Opinion This Week section entirely.)\n")

    return EDITOR_INSTRUCTIONS + "\n".join(data_blocks)


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


def generate_headline(body: str) -> str:
    """Generate a catchy headline for the week (same follow-up-Haiku-call pattern
    as digest_builder.py's daily headline). This becomes both the document's
    title line and the email subject line sent via Buttondown."""
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
                "Write a short, catchy headline (max 10 words) capturing the dominant story or "
                "tension in this week's Mercosur economic briefing below. Style examples (write "
                "an original one — do not reuse these):\n"
                "- \"Bolivia's Currency Gamble, Argentina's Borrowed Time\"\n"
                "- \"The Region That's Winning and Losing at the Same Time\"\n\n"
                "Return ONLY the final headline, nothing else.\n\n" + body
            ),
        }],
    )
    return response.content[0].text.strip()


def save_briefing(content: str, friday: date) -> str:
    os.makedirs(WEEKLY_OUTPUT_DIR, exist_ok=True)
    path = os.path.join(WEEKLY_OUTPUT_DIR, f"briefing_{friday.isoformat()}.md")
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


def extract_section(content: str, heading: str) -> str:
    match = re.search(rf"##\s*{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)", content, re.DOTALL)
    return match.group(1) if match else ""


def count_markdown_links(section: str) -> int:
    return len(re.findall(r"\[[^\]]+\]\([^)]+\)", section))


def print_summary(content: str, country_data: dict, oped_pieces: list[dict], headline: str, send_date: date) -> None:
    word_count = len(content.split())
    countries_covered = [c for c in COUNTRY_ORDER if country_data.get(c)]
    cw_count = count_corporate_watch_items(content)

    big_picture = extract_section(content, "The Big Picture")
    country_section = extract_section(content, "Country by Country")
    opinion_section = extract_section(content, "Opinion This Week")

    print("\n=== SUMMARY ===")
    print(f"Headline (email subject): {headline}")
    print(f"Send date: {send_date.strftime('%A, %B %-d, %Y')}")
    print(f"Word count: {word_count}")
    print(f"Countries covered: {len(countries_covered)}/6 ({', '.join(countries_covered)})")
    print(f"Big Picture inline links: {count_markdown_links(big_picture)}")
    print(f"Country by Country links: {count_markdown_links(country_section)}")
    print(f"Corporate Watch items found: {cw_count}")
    print(f"OpEd pieces available for roundup: {len(oped_pieces)}")
    print(f"Opinion This Week section present: {'yes' if opinion_section.strip() else 'no'} "
          f"({count_markdown_links(opinion_section)} link(s))")


def run(week_arg: str | None, dry_run: bool) -> None:
    monday = monday_of_week(week_arg)
    friday = monday + timedelta(days=4)  # last digest day AND send date — generation now runs Friday, same day as send
    week_days = [monday + timedelta(days=i) for i in range(5)]
    last_friday = monday - timedelta(days=3)  # exclusive lower bound for the OpEd lookback window (previous week's Friday)

    logger.info(f"=== Weekly Briefing — week of {monday.isoformat()} to {friday.isoformat()} (sends {friday.isoformat()}) ===")

    if dry_run:
        print(f"=== DRY RUN — week of {monday.isoformat()} (Mon) to {friday.isoformat()} (Fri) ===\n")
        for country in COUNTRY_ORDER:
            found_days = [d for d in week_days if os.path.exists(digest_path(country, d))]
            if not found_days:
                candidates = ", ".join(digest_path(country, d) for d in week_days)
                print(f"[{country}] NOT FOUND — checked: {candidates}")
            else:
                print(f"[{country}] Would use {len(found_days)} day(s): {', '.join(d.isoformat() for d in found_days)}")

        opeds = gather_recent_opeds(last_friday, friday)
        print(f"\nOpEd pieces since last briefing ({last_friday.isoformat()} exclusive → {friday.isoformat()} inclusive): {len(opeds)}")
        for o in opeds:
            print(f"  - [{o['date']}] {o['persona_name']}: {o['title']}")

        print(f"\nDate range covered: {monday.isoformat()} (Mon) through {friday.isoformat()} (Fri)")
        print(f"Send date (document date line): {friday.strftime('%A, %B %-d, %Y')}")
        print("Dry run — Sonnet API not called, no file saved.")
        return

    country_data = gather_week(week_days)
    if all(not v for v in country_data.values()):
        raise RuntimeError(f"No digests found for any country in week of {monday.isoformat()} — aborting")

    oped_pieces = gather_recent_opeds(last_friday, friday)

    prompt = build_prompt(country_data, oped_pieces)

    logger.info("Generating weekly briefing via Claude Sonnet…")
    body = generate_briefing(prompt)

    logger.info("Generating catchy headline via Claude Haiku…")
    headline = generate_headline(body)

    send_date_display = friday.strftime("%A, %B %-d, %Y") if os.name != "nt" else friday.strftime("%A, %B %d, %Y")

    marker = "\n## The Big Picture"
    idx = body.find(marker)
    if idx == -1:
        raise ValueError("Could not find '## The Big Picture' in the generated briefing — cannot assemble the headline/date header")
    greeting = body[:idx].strip()
    rest = body[idx:].strip()

    briefing = f"{greeting}\n\n# {headline}\n\n*{send_date_display}*\n\n{rest}"

    path = save_briefing(briefing, friday)
    logger.info(f"Weekly briefing saved to {path}")

    print(briefing)
    print_summary(briefing, country_data, oped_pieces, headline, friday)


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
