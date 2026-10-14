"""Generate the Mercosur Weekly Briefing from the week's daily digests."""

import argparse
import glob
import json
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

sys.path.insert(0, REPO_ROOT)
from generation.slugify import build_digest_url, build_opinion_url  # noqa: E402

OPED_DIR = os.path.join(REPO_ROOT, "digests", "opinion")
SPECIAL_MANIFEST_DIR = os.path.join(REPO_ROOT, "digests", "special")

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

EDITOR_INSTRUCTIONS_TEMPLATE = """You are the editor of 24EcoNews, a weekly economic briefing covering the Mercosur region for a global audience of investors, analysts, and business professionals.

Below are this week's daily digest narratives for 6 countries: Argentina, Brazil, Chile, Uruguay, Paraguay and Bolivia — with MULTIPLE dated digests provided per country (Monday through Friday, whichever days exist), each with its own URL. Also below, in OPED DATA, are any Opinion columns published since last week's briefing.

Write a Mercosur Weekly Briefing with this structure:

---
Before the main content, write a short 1-2 sentence email greeting that feels personal and editorial — as if written by the editor introducing this week's briefing to a subscriber. It should set the tone for what's inside without repeating the Big Picture content.
{recent_openings_block}
Do NOT begin the greeting with any of: "Rarely", "Seldom", "Few weeks", "This week", or the pattern "[Adverb] does a single week..." (e.g. "Rarely does a single week..."). These openings have been overused and will be rejected.

To vary the opening, pick ONE of the following devices — choose whichever fits this week's content best, and make sure it differs from whatever device the recent openings above relied on:
- A concrete number or data point from this week's coverage
- A single vivid image or scene
- A short question
- A very short declarative sentence, followed by a longer one
- A direct contrast between two countries
- A quoted phrase pulled from this week's coverage

If you use the number/data-point device: the number AND the specific claim it describes must appear TOGETHER, as stated, in the DATA section below for this week. Never construct your own count, tally, or aggregate across countries, institutions, or time (e.g., "X officials have lost their jobs this year/in recent memory/in living memory") unless the DATA explicitly states that exact count. A single fact pulled directly from one line of the DATA ("unemployment hit 9.5%", "copper closed at $6.51/lb") is correct; a number you computed or estimated yourself is not, no matter how plausible it sounds.

Bad example (fabricated historical aggregate — never do this): "Five finance ministers have lost their jobs to reform pressure in this region in living memory." Nothing in the DATA counts ministerial dismissals across countries or years — this number was invented, and sentences like it will be rejected.

If you use the quoted-phrase device, the quote must be copied verbatim from the DATA section — never fabricate or paraphrase a quote. If no sufficiently strong grounded number or quote exists this week, pick a different device from the list instead.

After the greeting sentences, on their own line, add a signature:

— John Dominguez, Editor

Example format:
"Chile's unemployment rate just hit a five-year high. So did its copper exports.

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

If an OPED DATA entry is marked "SPECIAL EDITION" (collapsed — several columnists wrote on one shared subject), do NOT use the per-piece format above and do NOT list its pieces individually. Write exactly one line for it instead, in this format, using its given count and URL:

**[N] columnists weigh in on this week's special edition** — [Read all N on the Opinion page](URL)

If OPED DATA below has no pieces, omit this "## Opinion This Week" section entirely — do not include the header with no content beneath it, and do not write a note saying no pieces were published.

## What to Watch Next Week
2-3 bullet points identifying the economic storylines, data releases, or political events across the region that global readers should track in the coming week.

---

Tone: Bloomberg Markets meets The Economist. Authoritative, specific, globally relevant. No filler sentences. Every sentence should earn its place.

Use only the exact URLs given in the DATA and OPED DATA sections below for any link — never invent or alter one.

Output only the briefing itself, starting directly with the email greeting. Do not include any preamble, meta-commentary, or introductory sentence like "Here is this week's briefing" before the greeting, and do not wrap the output in a leading "---" separator. Do not include a top-level title or headline line anywhere — start with the greeting and end with "What to Watch Next Week"."""

BANNED_OPENER_RE = re.compile(
    r"^(Rarely|Seldom|Few\s+weeks|This\s+week)\b|^\w+\s+does\s+a\s+single\s+week",
    re.IGNORECASE,
)

# Catches the specific fabricated-aggregate failure mode (e.g. "Five ministers have
# lost their jobs ... in living memory") that slipped past the prompt-level ban on
# invented historical/regional tallies.
UNGROUNDED_TIMEFRAME_RE = re.compile(r"living memory|recent memory", re.IGNORECASE)

GREETING_RECENT_LOOKBACK = 6


def _strip_greeting_signature(text: str) -> str:
    """Return the greeting opening (everything before the '— John Dominguez'
    signature line), ignoring any leading HTML comment line."""
    lines = text.split("\n")
    i = 0
    while i < len(lines) and lines[i].strip().startswith("<!--"):
        i += 1
    sig_idx = next(
        (j for j in range(i, len(lines)) if lines[j].strip().startswith("— John Dominguez")),
        None,
    )
    if sig_idx is None:
        sig_idx = next((j for j in range(i, len(lines)) if lines[j].strip().startswith("#")), len(lines))
    return " ".join(ln.strip() for ln in lines[i:sig_idx] if ln.strip())


def _first_word(text: str) -> str:
    match = re.search(r"[A-Za-z']+", text)
    return match.group(0).lower() if match else ""


def collect_recent_greetings(before: date, n: int = GREETING_RECENT_LOOKBACK) -> list[str]:
    """Return up to n greeting openings from the most recent saved briefings
    dated before `before`, most recent first."""
    dated = []
    for path in glob.glob(os.path.join(WEEKLY_OUTPUT_DIR, "briefing_*.md")):
        match = re.search(r"briefing_(\d{4}-\d{2}-\d{2})\.md$", path)
        if not match:
            continue
        d = date.fromisoformat(match.group(1))
        if d < before:
            dated.append((d, path))
    dated.sort(key=lambda t: t[0], reverse=True)

    greetings = []
    for _, path in dated[:n]:
        with open(path, encoding="utf-8") as f:
            greeting = _strip_greeting_signature(f.read())
        if greeting:
            greetings.append(greeting)
    return greetings


def build_editor_instructions(recent_greetings: list[str]) -> str:
    if recent_greetings:
        quoted = "\n".join(f'- "{g}"' for g in recent_greetings)
        recent_openings_block = (
            "\nRecent openings (do NOT reuse their first word, sentence structure, or rhetorical device):\n"
            f"{quoted}\n"
        )
    else:
        recent_openings_block = ""
    return EDITOR_INSTRUCTIONS_TEMPLATE.format(recent_openings_block=recent_openings_block)


def regenerate_greeting(data_section: str, recent_greetings: list[str], conflict_reason: str) -> str:
    """Ask Sonnet for a replacement greeting when the generated one collides
    with a recent opening or a banned pattern. Grounded against the same raw
    DATA FOR THIS WEEK section used for the main generation (not the model's
    own Big Picture synthesis), so any number or quote it uses is verifiable
    against the source digests. Returns a 'greeting\\n\\n— John Dominguez,
    Editor' block to splice in place of the original."""
    import anthropic
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")

    quoted = "\n".join(f'- "{g}"' for g in recent_greetings) if recent_greetings else "(none)"

    prompt = (
        "You are the editor of 24EcoNews, a weekly Mercosur economic briefing. Write a "
        "replacement 1-2 sentence email greeting for this week's briefing, followed by the "
        "signature line '— John Dominguez, Editor' on its own line.\n\n"
        f"Your previous attempt {conflict_reason} — it must not be reused.\n\n"
        "Recent openings (do NOT reuse their first word, sentence structure, or rhetorical device):\n"
        f"{quoted}\n\n"
        "Do NOT begin with any of: \"Rarely\", \"Seldom\", \"Few weeks\", \"This week\", or the "
        "pattern \"[Adverb] does a single week...\".\n\n"
        "Pick ONE device that differs from the recent openings above: a concrete number or data "
        "point, a single vivid image or scene, a short question, a very short declarative sentence "
        "followed by a longer one, a direct contrast between two countries, or a quoted phrase from "
        "this week's coverage.\n\n"
        "If you use the number/data-point device: the number AND the specific claim it describes "
        "must appear TOGETHER, as stated, in the DATA below for this week. Never construct your own "
        "count, tally, or aggregate across countries, institutions, or time (e.g., \"X officials have "
        "lost their jobs this year/in recent memory/in living memory\") unless the DATA explicitly "
        "states that exact count. A single fact pulled directly from one line of the DATA is correct; "
        "a number you computed or estimated yourself is not, no matter how plausible it sounds.\n\n"
        "Bad example (fabricated historical aggregate — never do this): \"Five finance ministers have "
        "lost their jobs to reform pressure in this region in living memory.\" Nothing in the DATA "
        "counts ministerial dismissals across countries or years — this number was invented.\n\n"
        "If you use the quoted-phrase device, the quote must be copied verbatim from the DATA below — "
        "never fabricate or paraphrase a quote. If no sufficiently strong grounded number or quote "
        "exists this week, pick a different device from the list instead.\n\n"
        "This week's source data, for grounding:\n" + data_section + "\n\n"
        "Output ONLY the greeting followed by the signature line, nothing else."
    )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


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

    url = f"{SITE_BASE_URL}{build_digest_url(country, day, title)}"
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


def load_special_edition_basenames() -> dict[str, str]:
    """Return {opinion-file basename: edition id} for every piece listed in
    any digests/special/*.json manifest, so the weekly roundup can collapse
    a special edition's pieces into one line instead of listing all 8
    individually (see gather_recent_opeds)."""
    mapping = {}
    if not os.path.isdir(SPECIAL_MANIFEST_DIR):
        return mapping
    for manifest_path in sorted(glob.glob(os.path.join(SPECIAL_MANIFEST_DIR, "*.json"))):
        edition_id = os.path.splitext(os.path.basename(manifest_path))[0]
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        for piece in manifest.get("pieces", []):
            mapping[os.path.basename(piece["path"])] = edition_id
    return mapping


def gather_recent_opeds(since_day: date, until_day: date) -> list[dict]:
    """Return OpEd pieces published in (since_day, until_day], most recent first.

    Reuses oped_bluesky_poster.py's parse_oped() for the PERSONA/LENS/TITLE
    metadata extraction and body-sentence splitting, rather than re-implementing
    that parsing a third time.

    Pieces belonging to a special edition (digests/special/*.json) are not
    added individually — they'd otherwise fill the roundup with 8 near-identical
    entries on the same subject. Instead each edition encountered this week
    collapses into a single "special" entry pointing at the /opinion page;
    see build_data_section() for how that entry is rendered for the model.
    """
    if not os.path.isdir(OPED_DIR):
        return []

    special_basenames = load_special_edition_basenames()
    filename_re = re.compile(r"^([a-z-]+)_(\d{4}-\d{2}-\d{2})\.md$")
    results = []
    special_counts: dict[str, dict] = {}  # edition_id -> {"count": int, "date": str}

    for fname in os.listdir(OPED_DIR):
        match = filename_re.match(fname)
        if not match:
            continue
        slug, date_str = match.group(1), match.group(2)
        oped_date = date.fromisoformat(date_str)
        if not (since_day < oped_date <= until_day):
            continue

        edition_id = special_basenames.get(fname)
        if edition_id:
            entry = special_counts.setdefault(edition_id, {"count": 0, "date": date_str})
            entry["count"] += 1
            entry["date"] = max(entry["date"], date_str)
            logger.info(f"[weekly_briefing] {fname} is part of special edition {edition_id!r} — collapsing into one roundup line")
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
            "url": f"{SITE_BASE_URL}{build_opinion_url(slug, date_str, title)}",
        })
        logger.info(f"[weekly_briefing] Including OpEd {slug}_{date_str} in roundup")

    for edition_id, entry in special_counts.items():
        results.append({
            "special": True,
            "edition": edition_id,
            "count": entry["count"],
            "date": entry["date"],
            "url": f"{SITE_BASE_URL}/opinion",
        })

    results.sort(key=lambda o: o["date"], reverse=True)
    return results


def _day_display(d: date) -> str:
    return d.strftime("%A, %B %-d") if os.name != "nt" else d.strftime("%A, %B %d")


def build_data_section(country_data: dict, oped_pieces: list[dict]) -> str:
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
            if oped.get("special"):
                data_blocks.append(
                    f"\n### SPECIAL EDITION — {oped['count']} pieces ({oped['date']}) — COLLAPSE INTO ONE LINE, do not list individually\n"
                    f"URL: {oped['url']}\n"
                )
                continue
            data_blocks.append(
                f"\n### {oped['persona_name']} — {oped['lens_short']} ({oped['date']})\n"
                f"TITLE: {oped['title']}\n"
                f"URL: {oped['url']}\n"
                f"EXCERPT: {oped['excerpt']}\n"
            )
    else:
        data_blocks.append("\n(No OpEd pieces were published since last week's briefing — omit the Opinion This Week section entirely.)\n")

    return "\n".join(data_blocks)


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

    recent_greetings = collect_recent_greetings(friday)
    recent_first_words = {_first_word(g) for g in recent_greetings}

    data_section = build_data_section(country_data, oped_pieces)
    prompt = build_editor_instructions(recent_greetings) + data_section

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

    def _opening_conflict(opening: str) -> str | None:
        word = _first_word(opening)
        if BANNED_OPENER_RE.match(opening.strip()):
            return f"opened with a banned pattern (\"{opening.strip()[:40]}...\")"
        if UNGROUNDED_TIMEFRAME_RE.search(opening):
            return "used an ungrounded cross-time framing (\"living memory\"/\"recent memory\")"
        if word and word in recent_first_words:
            return f"opened with the word \"{word}\", matching a recent briefing's opening word"
        return None

    conflict = _opening_conflict(_strip_greeting_signature(greeting))
    if conflict:
        logger.warning(f"Greeting {conflict} — regenerating once.")
        greeting = regenerate_greeting(data_section, recent_greetings, conflict)
        new_conflict = _opening_conflict(_strip_greeting_signature(greeting))
        if new_conflict:
            logger.warning(f"Regenerated greeting still {new_conflict} — proceeding anyway.")

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
