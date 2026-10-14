"""Generate special-edition OpEd series for 24EcoNews's Opinion section.

A special edition is a one-off (or periodic) event where all eight recurring
columnists (see oped_personas.py) write on the SAME fixed subject, each
through their own assigned angle, instead of the usual daily rotation where
one columnist picks their own story. Built for the Brazil 2026 election
series but written to be reusable for any future shared-topic edition —
editions are defined in generation/special_editions.json, not in this file.

Generation and review tooling only: no newsletter, no Bluesky, no deploy
step lives here. Output lands in digests/opinion/ in the exact same file
format oped_builder.py produces, so every downstream consumer (the website,
oped_bluesky_poster.py, opinion_linker.py, weekly_briefing.py) keeps working
unmodified.
"""

import argparse
import json
import logging
import os
import re
import sys
from collections import Counter
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
from generation.oped_builder import (  # noqa: E402
    OPED_OUTPUT_DIR,
    generate_headline,
    generate_oped,
    save_oped,
)
from publishing.weekly_briefing import (  # noqa: E402
    COUNTRY_DISPLAY_NAMES,
    COUNTRY_ORDER,
    FLAGS,
    digest_path,
    gather_week,
)
from publishing.bluesky_poster import split_sentences  # noqa: E402

EDITIONS_CONFIG_PATH = os.path.join(SCRIPT_DIR, "special_editions.json")
SPECIAL_MANIFEST_DIR = os.path.join(REPO_ROOT, "digests", "special")

WORD_COUNT_TARGET = (700, 900)
WORD_COUNT_HARD_CAP = 950
WORD_COUNT_RETRY_THRESHOLD = 1150  # retry only once a piece runs well past the prompt's own 950 hard cap, so pieces aren't regenerated for length alone
# Length never drives NEEDS HUMAN REVIEW — only grounding issues do (see run()).

THIN_MATERIAL_RULE = """If the source material below offers little or no direct support for your assigned angle this week, do NOT compensate by reaching for statistics, counts, or figures from your own background knowledge — use only numbers that actually appear in the source material below. In that situation, argue qualitatively instead: build your case on reasoning, and connect your angle to whatever the sources DO report even when the connection is adjacent rather than squarely on-topic.

Bad example (never do this): a fintech columnist with no Pix-related material in a given week's sources opened a piece with "Pix has 165 million active users" — a real-sounding but entirely unsourced statistic pulled from general knowledge rather than that week's reporting. That is exactly the failure this rule exists to prevent."""

SPECIAL_EDITION_PROMPT_TEMPLATE = """You are {name}, {lens}, writing an opinion column for 24EcoNews's Opinion section — one of eight columnists contributing to a special-edition series in which every columnist writes on the SAME subject, each from their own stated perspective.

Length: target 700-900 words. Hard maximum: 950 words — do not exceed this under any circumstance. If covering multiple scenarios, give each one short paragraph, not a full symmetric side-by-side analysis.

Your rhetorical style: {style}

SUBJECT (fixed for this special edition — write on this subject only; do not survey the material for a different story, and do not apply any country-rotation logic):
{topic}

Your assigned angle, which must lead this piece — open by engaging it directly, not after a generic scene-setter: {angle}

{scenario_block}Write a sharp, well-argued opinion piece from your stated ideological perspective, built around your assigned angle. Your argument MUST be grounded in the real facts, figures, and events provided below — do not fabricate data or events. You may interpret, emphasize, and draw conclusions the underlying reporting doesn't state explicitly, but the underlying facts must be real and traceable to the source material.

Do not state what any candidate or party plans, has promised, or will do unless the source material below explicitly says so. Any claim about a candidate's or party's future action, plan, or policy that the source does not state outright must be framed explicitly as a scenario — e.g. "If Flávio wins, his team would likely need to..." — never presented as settled fact.

{thin_material_rule}

At least two-thirds of the piece must be economic analysis — fiscal, monetary, trade, market, and investment consequences. The remainder may cover your political reading: what the result says about coalitions, Congress, and governability. Do not let the political commentary dominate the piece or crowd out the economics.

Absolutely not allowed, under any circumstance:
- Telling readers how to vote, or endorsing or opposing any candidate or party.
- Quotation marks around any statement attributed to a person, political party, ministry, company, or institution — even if the source material itself quotes them directly and even if the words would be accurate. Paraphrase the statement in your own words and attribute it to the reporting instead (e.g. "Valor Econômico reported that..." or "according to the digest coverage..."). Do not put anyone's words in quotation marks, period. A single word of your own scare-quoted for rhetorical effect (e.g. calling a plan "temporary") is fine — the ban is on quoting someone else's words, not on your own emphasis.
- Any number, percentage, date, or figure that does not appear in the source material below.
- Stating what any candidate or party plans, has promised, or will do unless the source material explicitly says so — frame it as a scenario instead (see above).

Write with conviction and a clear point of view — this is opinion writing, not neutral reporting. Be willing to criticize your own 'side' when the facts warrant it; intellectual honesty matters more than ideological consistency.

Structure: a sharp opening that states your thesis through your assigned angle, 3-4 paragraphs of argument grounded in specific facts, a closing that doesn't hedge.

Do not include a byline or title — just the piece itself."""


def load_editions() -> dict:
    with open(EDITIONS_CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_edition(editions: dict, edition_id: str) -> dict:
    if edition_id not in editions:
        raise ValueError(f"Unknown edition {edition_id!r} — expected one of {sorted(editions)}")
    return editions[edition_id]


def window_days(lookback_start: date, end: date) -> list[date]:
    if end < lookback_start:
        return []
    return [lookback_start + timedelta(days=i) for i in range((end - lookback_start).days + 1)]


def build_special_prompt(persona: Persona, angle: str, edition: dict, country_data: dict) -> str:
    scenario_instruction = edition.get("scenario_instruction") or ""
    scenario_block = f"{scenario_instruction}\n\n" if scenario_instruction else ""

    instructions = SPECIAL_EDITION_PROMPT_TEMPLATE.format(
        name=persona.name,
        lens=persona.lens_full,
        style=persona.style,
        topic=edition["topic"],
        angle=angle,
        scenario_block=scenario_block,
        thin_material_rule=THIN_MATERIAL_RULE,
    )

    material_blocks = ["\n\n---\nPRIMARY SOURCE MATERIAL — BRAZIL (full coverage for this window):\n"]
    for d in country_data.get("brazil") or []:
        block = f"\n### {FLAGS['brazil']} Brazil — {d['date']}\nTITLE: {d['title']}\n{d['narrative']}\n"
        if d["corporate_watch"]:
            block += f"\n{d['corporate_watch']}\n"
        material_blocks.append(block)

    material_blocks.append(
        "\n\n---\nSECONDARY SOURCE MATERIAL — regional spillover context "
        "(Argentina, Chile, Uruguay, Paraguay, Bolivia):\n"
    )
    any_secondary = False
    for country in COUNTRY_ORDER:
        if country == "brazil":
            continue
        for d in country_data.get(country) or []:
            any_secondary = True
            flag = FLAGS[country]
            name = COUNTRY_DISPLAY_NAMES[country]
            block = f"\n### {flag} {name} — {d['date']}\nTITLE: {d['title']}\n{d['narrative']}\n"
            if d["corporate_watch"]:
                block += f"\n{d['corporate_watch']}\n"
            material_blocks.append(block)
    if not any_secondary:
        material_blocks.append("\n(No secondary-country digests found in this window.)\n")

    return instructions + "\n".join(material_blocks)


# --- Grounding report -------------------------------------------------------
#
# Heuristic, substring-based verification: every figure or quote the piece
# uses must appear verbatim somewhere in the source corpus fed to the model.
# This cannot catch a fabrication that happens to reuse real-looking digits,
# but it's exactly the kind of check that would have caught the "Five finance
# ministers... in living memory" fabrication from the weekly briefing — a
# number with no matching claim anywhere in the source material. Flags are
# for human review, not an automatic accept/reject gate.

FIGURE_PATTERNS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),  # ISO dates
    re.compile(
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2}(?:,\s*\d{4})?\b"
    ),
    # \d{1,3}(?:,\d{3})* (not \d[\d,]*) so a comma is only consumed as a
    # thousands separator (followed by exactly 3 digits) — \d[\d,]* let a
    # bare trailing sentence comma ("R$62," mid-sentence) get swallowed into
    # the match, the same false-positive class as the trailing-period bug
    # fixed earlier for quotes.
    re.compile(r"(?:R\$|US\$|USD|BRL)\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:\s?(?:billion|million|trillion|bn|mn))?"),
    re.compile(r"\d+(?:\.\d+)?%"),
    re.compile(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s?(?:billion|million|trillion)\b"),
    re.compile(r"\b\d{1,3}(?:,\d{3})+\b"),  # comma-grouped numbers, e.g. 100,000
]

QUOTE_PATTERNS = [
    re.compile(r'"([^"]{4,})"'),
    re.compile(r"[“”]([^“”]{4,})[“”]"),
]


def _dedup(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def extract_figures(text: str) -> list[str]:
    found = []
    for pattern in FIGURE_PATTERNS:
        found.extend(m.group(0) for m in pattern.finditer(text))
    return _dedup(found)


def extract_quotes(text: str) -> list[str]:
    # American typographic convention puts sentence-final punctuation inside
    # the closing quote mark even when it isn't part of the quoted material
    # (e.g. source: "history may repeat itself" — a reference...; generated:
    # "history may repeat itself."). Strip trailing .,;: before comparing, or
    # a correctly-quoted phrase gets flagged as unverified over punctuation
    # the source's sentence structure never had reason to include.
    found = []
    for pattern in QUOTE_PATTERNS:
        found.extend(m.group(1).strip().rstrip(".,;:") for m in pattern.finditer(text))
    return _dedup(found)


VOTE_PERCENT_RE = re.compile(r"\d+(?:\.\d+)?%")
# Deliberately narrower than a generic "election" word: "electoral noise" or
# "election campaign" sits near plenty of non-vote percentages (diesel
# prices, Selic, GDP) in a piece about an election. Require a marker that's
# specifically about a vote tally or poll, not just election-adjacent prose.
VOTE_CONTEXT_RE = re.compile(
    r"\b(votes?|voted|poll(?:ster)?s?|Datafolha|Quaest|AtlasIntel|runoff|first[\s-]round|valid\s+votes)\b",
    re.IGNORECASE,
)
VOTE_CONTEXT_WINDOW = 60  # chars of surrounding text checked for a vote/poll context word


def extract_vote_figures(text: str) -> list[str]:
    """Percentages whose immediate context (±60 chars) reads as an election
    or poll result, as opposed to an unrelated macro percentage (inflation,
    Selic, GDP growth) that happens to share the same %-number pattern."""
    found = []
    for m in VOTE_PERCENT_RE.finditer(text):
        start = max(0, m.start() - VOTE_CONTEXT_WINDOW)
        end = min(len(text), m.end() + VOTE_CONTEXT_WINDOW)
        if VOTE_CONTEXT_RE.search(text[start:end]):
            found.append(m.group(0))
    return _dedup(found)


def find_lines_with_figure(figure: str, line_index: list[tuple[str, int, str]]) -> list[tuple[str, int]]:
    # Word-boundary-safe: a plain substring check would match "7%" inside
    # "47%" or "17%" — reject matches immediately preceded by another digit.
    pattern = re.compile(r"(?<!\d)" + re.escape(figure))
    return [(path, lineno) for path, lineno, line_text in line_index if pattern.search(line_text)]


def build_source_corpus(country_data: dict) -> str:
    parts = []
    for digests in country_data.values():
        for d in digests:
            parts.append(d["narrative"])
            if d["corporate_watch"]:
                parts.append(d["corporate_watch"])
    return "\n".join(parts)


def _is_allowed_fact(item: str, allowed_facts: list[str]) -> bool:
    """True only on an EXACT match against one of the edition's pre-approved
    known premises (fixed dates like the election/runoff dates). Exact, not
    substring — allowed_facts is for dates only, never names, and a loose
    match would let an unrelated figure ride along with a date string that
    happens to contain it."""
    return item in allowed_facts


def grounding_report(piece_text: str, source_corpus: str, allowed_facts: list[str] | None = None) -> dict:
    allowed_facts = allowed_facts or []
    figures = extract_figures(piece_text)
    quotes = extract_quotes(piece_text)
    # Quote comparison is case-insensitive: a persona scare-quoting a generic
    # phrase for rhetorical effect ("Fiscal adjustment" is not a neutral
    # phrase) capitalizes it differently than the source's mid-sentence
    # "fiscal adjustment" even though the words are identical and it isn't
    # attributed to anyone — a formatting difference, not a fabrication.
    corpus_lower = source_corpus.lower()
    return {
        "figures_checked": len(figures),
        "quotes_checked": len(quotes),
        # allowed_facts exempts dates/figures only — never quotes. A quote is
        # either verbatim in the source or it isn't; a pre-approved "known
        # premise" is not a license to fabricate attributed speech.
        "unverified_figures": [
            f for f in figures if f not in source_corpus and not _is_allowed_fact(f, allowed_facts)
        ],
        "unverified_quotes": [q for q in quotes if q.lower() not in corpus_lower],
    }


def print_grounding_report(persona_name: str, piece_text: str, source_corpus: str, allowed_facts: list[str] | None = None) -> None:
    report = grounding_report(piece_text, source_corpus, allowed_facts)
    print(f"\n--- Grounding report: {persona_name} ---")
    print(f"Figures checked: {report['figures_checked']}  |  Quotes checked: {report['quotes_checked']}")
    if not report["unverified_figures"] and not report["unverified_quotes"]:
        print("All figures and quotes verified against source material.")
        return
    if report["unverified_figures"]:
        print("UNVERIFIED figures/dates (not found verbatim in source material — review):")
        for f in report["unverified_figures"]:
            print(f"  - {f!r}")
    if report["unverified_quotes"]:
        print("UNVERIFIED quotes (not found verbatim in source material — review):")
        for q in report["unverified_quotes"]:
            print(f"  - {q!r}")


def _attributes_to_someone(quote: str) -> bool:
    """The prompt rule allows a single word of the columnist's own language
    scare-quoted for emphasis — only a multi-word quoted span plausibly puts
    someone else's words in their mouth, which is what the rule actually
    bans. A one-word quote is assumed to be the columnist's own emphasis."""
    return len(quote.split()) > 1


def print_remaining_quotes(persona_name: str, piece_text: str, headline: str) -> None:
    """This edition bans quotation marks around attributed statements (see
    the prompt rule) but allows single-word scare quotes on the columnist's
    own language — so unlike grounding, which only flags an UNVERIFIED
    quote, this lists every quoted span that attributes words to someone,
    verbatim-accurate or not, as a compliance check on that rule."""
    quotes = [q for q in extract_quotes(headline + "\n" + piece_text) if _attributes_to_someone(q)]
    print(f"\n--- Remaining quotation marks (attributing words to someone): {persona_name} ---")
    if not quotes:
        print("None.")
        return
    for q in quotes:
        print(f"  - {q!r}")


def print_vote_figures(persona_name: str, piece_text: str, headline: str, line_index: list[tuple[str, int, str]]) -> None:
    """List every vote/poll percentage used in the piece against its source
    digest(s) and line(s), so each can be checked against the official
    result directly — separate from the general grounding report, which
    only confirms a figure appears somewhere in the corpus, not which one."""
    figures = extract_vote_figures(headline + "\n" + piece_text)
    print(f"\n--- Vote/poll figures: {persona_name} ---")
    if not figures:
        print("No vote/poll percentages found.")
        return
    for figure in figures:
        locations = find_lines_with_figure(figure, line_index)
        if not locations:
            print(f"  {figure}: NOT FOUND in source material")
        else:
            where = ", ".join(f"{path}:{lineno}" for path, lineno in locations)
            print(f"  {figure}: {where}")


# --- Retry on ungrounded figures/quotes or length overage -------------------


def build_retry_prompt(original_prompt: str, unverified_items: list[str], overage_words: int | None) -> str:
    corrections = []
    if unverified_items:
        quoted = "; ".join(f'"{item}"' for item in unverified_items)
        corrections.append(
            "Your previous draft used the following figures and/or quoted phrases that could not be "
            f"verified against the source material: {quoted}. Remove every one of them entirely — do "
            "not restate them in any form, even paraphrased or rounded — unless you can find genuine "
            "support for them in the source material below. If you have no grounded replacement, drop "
            "the claim rather than inventing a substitute number or quote."
        )
    if overage_words:
        corrections.append(
            f"Your previous draft was {overage_words} words, exceeding the {WORD_COUNT_HARD_CAP}-word "
            f"hard cap. Cut it to under {WORD_COUNT_HARD_CAP} words by tightening the prose and trimming "
            "scenario treatment to one short paragraph per outcome — do not just truncate the ending."
        )
    correction_block = "\n\n--- REQUIRED CORRECTIONS FOR THIS REWRITE ---\n" + "\n".join(corrections) + "\n"
    return original_prompt + correction_block


# --- Attribution trace --------------------------------------------------------
#
# Heuristic, deliberately broad-coverage check: every sentence (and the
# headline) that names an entity drawn from THIS week's source material is
# flagged for review, regardless of whether it uses a classic reporting verb
# ("said", "argued") — a headline like "Petrobras Stock Split Shows..." makes
# a factual claim about an institution without any such verb, and silently
# skipping it would miss exactly the kind of fabrication this check exists to
# catch. Entities are mined from the source corpus itself (not hardcoded) so
# this stays reusable for future special editions on other subjects.

_MONTHS = {
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
}
_WEEKDAYS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
_GENERIC_CAPITALIZED_STOPLIST = {
    "The", "This", "That", "These", "Those", "It", "Its", "What", "Which", "Who", "Both",
    "Under", "Over", "After", "Before", "During", "While", "Research", "Markets", "Market",
    "Economic", "Economy", "Election", "Runoff", "First", "Second", "Scenario", "Scenarios",
    "Brazil", "Brazilian", "Argentina", "Argentine", "Argentinian", "Chile", "Chilean",
    "Uruguay", "Uruguayan", "Paraguay", "Paraguayan", "Bolivia", "Bolivian", "Mercosur",
} | _MONTHS | _WEEKDAYS

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "at", "for", "with", "as",
    "is", "are", "was", "were", "be", "been", "that", "this", "these", "those", "it", "its",
    "his", "her", "their", "they", "he", "she", "we", "you", "i", "not", "no", "so", "if",
    "than", "then", "which", "who", "what", "when", "where", "how", "why", "from", "by",
    "will", "would", "could", "should", "can", "may", "might", "must", "do", "does", "did",
    "has", "have", "had", "under", "over", "into", "onto", "about", "after", "before",
    "during", "while", "both", "each", "either", "neither", "also", "still", "yet", "just",
    "more", "most", "less", "least", "such", "per", "vs", "versus",
}


def extract_known_entities(source_corpus: str) -> set[str]:
    multi_word = set(re.findall(r"\b[A-Z][a-zA-Z.&'-]*(?:\s+[A-Z][a-zA-Z.&'-]*){1,3}\b", source_corpus))
    single_counts = Counter(re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", source_corpus))
    recurring_single = {w for w, c in single_counts.items() if c >= 2}
    entities = (multi_word | recurring_single) - _GENERIC_CAPITALIZED_STOPLIST
    return {e for e in entities if len(e) > 2}


def find_entities_in_text(text: str, known_entities: set[str]) -> list[str]:
    found = [e for e in known_entities if e in text]
    found.sort(key=len, reverse=True)
    deduped = []
    for e in found:
        if not any(e != other and e in other for other in deduped):
            deduped.append(e)
    return deduped


def _significant_tokens(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z]{4,}|\d[\d.,]*%?", text)
    return {w.lower() for w in words if w.lower() not in _STOPWORDS}


def build_line_index(days: list[date]) -> list[tuple[str, int, str]]:
    """Return (repo-relative path, 1-indexed line number, line text) for
    every non-empty line in every country's raw .en.md digest in the window —
    the same (file, line) granularity used for manual spot-checks throughout
    this project, since each digest paragraph is one physical line."""
    entries = []
    for country in COUNTRY_ORDER:
        for day in days:
            path = digest_path(country, day)
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as f:
                lines = f.read().split("\n")
            rel = os.path.relpath(path, REPO_ROOT)
            for lineno, line in enumerate(lines, start=1):
                if line.strip():
                    entries.append((rel, lineno, line))
    return entries


MIN_SHARED_TOKENS = 3  # other significant words required beyond the entity's own name


ANALYSIS_MARKER_RE = re.compile(r"\b(if|would|could|might|may|likely)\b", re.IGNORECASE)


def classify_sentence(sentence: str) -> str:
    """ANALYSIS = scenario/judgment language (if/would/could/might/may/likely);
    ASSERTION = states what a named politician or institution said, proposed,
    did, or what a figure is — the category that actually needs a source."""
    return "ANALYSIS" if ANALYSIS_MARKER_RE.search(sentence) else "ASSERTION"


def find_source_line(sentence: str, entity: str, line_index: list[tuple[str, int, str]]) -> tuple[tuple[str, int, str] | None, bool]:
    """Return (best candidate, confirmed) where best candidate is the
    highest-overlap (path, line, text) among lines mentioning `entity` (or
    None if the entity appears nowhere), and confirmed is True only if that
    overlap meets MIN_SHARED_TOKENS. The candidate is returned even when not
    confirmed, so an UNSOURCED assertion can still show its nearest match
    for human judgment rather than nothing at all."""
    entity_tokens = _significant_tokens(entity)
    sig_tokens = _significant_tokens(sentence) - entity_tokens
    best = None
    best_score = -1
    for rel_path, lineno, line_text in line_index:
        if entity not in line_text:
            continue
        line_tokens = _significant_tokens(line_text) - entity_tokens
        score = len(sig_tokens & line_tokens)
        if score > best_score:
            best_score = score
            best = (rel_path, lineno, line_text)
    return best, (best is not None and best_score >= MIN_SHARED_TOKENS)


def attribution_trace(piece_text: str, headline: str, known_entities: set[str], line_index: list[tuple[str, int, str]]) -> list[dict]:
    units = [("TITLE", headline)] + [("BODY", s) for s in split_sentences(piece_text)]
    rows = []
    for label, sentence in units:
        entities = find_entities_in_text(sentence, known_entities)
        if not entities:
            continue
        entity = entities[0]
        candidate, confirmed = find_source_line(sentence, entity, line_index)
        rows.append({
            "label": label,
            "sentence": sentence,
            "entity": entity,
            "classification": classify_sentence(sentence),
            "confirmed": confirmed,
            "source": f"{candidate[0]}:{candidate[1]}" if confirmed else None,
            "nearest": f"{candidate[0]}:{candidate[1]}" if candidate else None,
            "nearest_snippet": candidate[2].strip()[:120] if candidate else "",
        })
    return rows


# Tested directly against every sentence, independent of attribution_trace's
# single-longest-entity-per-sentence selection — a sentence naming both "Lula"
# and "Flávio" should produce two rows, not get collapsed to whichever entity
# find_entities_in_text happened to pick.
_CANDIDATE_MENTION_RE = re.compile(r"\b(Lula|Flávio|Bolsonaro|PT|PL|[Cc]ampaign)\b")


def _candidate_mentions(sentence: str) -> list[str]:
    return _dedup(m.group(1) for m in _CANDIDATE_MENTION_RE.finditer(sentence))


def candidate_assertion_rows(piece_text: str, headline: str, line_index: list[tuple[str, int, str]]) -> list[dict]:
    """One row per distinct candidate mention (not per sentence) in every
    ASSERTION sentence that names Lula, Flávio, Bolsonaro, PT, PL, or a
    campaign — so a sentence mentioning more than one of those produces a
    row for each, each checked against its own nearest source line."""
    units = [("TITLE", headline)] + [("BODY", s) for s in split_sentences(piece_text)]
    rows = []
    for label, sentence in units:
        if classify_sentence(sentence) != "ASSERTION":
            continue
        for mention in _candidate_mentions(sentence):
            candidate, confirmed = find_source_line(sentence, mention, line_index)
            rows.append({
                "label": label,
                "sentence": sentence,
                "mention": mention,
                "confirmed": confirmed,
                "nearest": f"{candidate[0]}:{candidate[1]}" if candidate else None,
                "nearest_snippet": candidate[2].strip()[:120] if candidate else "",
            })
    return rows


def print_candidate_unsourced_assertions(
    persona_name: str, piece_text: str, headline: str, line_index: list[tuple[str, int, str]]
) -> None:
    """Narrower than the full attribution table: every ASSERTION sentence
    naming Lula, Flávio, Bolsonaro, PT, PL, or a campaign, tested sentence by
    sentence rather than via attribution_trace's one-entity-per-sentence
    pick. UNSOURCED rows print first since a fabricated claim about either
    runoff candidate is the highest-stakes failure this check exists to
    catch; CONFIRMED rows follow for completeness."""
    rows = candidate_assertion_rows(piece_text, headline, line_index)
    print(f"\n--- Lula/Flávio candidate assertions: {persona_name} ---")
    if not rows:
        print("None.")
        return
    ordered = [r for r in rows if not r["confirmed"]] + [r for r in rows if r["confirmed"]]
    for r in ordered:
        tag = f"[{r['label']}]"
        status = "CONFIRMED" if r["confirmed"] else "UNSOURCED"
        sentence = r["sentence"] if len(r["sentence"]) <= 160 else r["sentence"][:157] + "..."
        print(f"{tag} {status} ({r['mention']}): {sentence}")
        if r["nearest"]:
            print(f"        nearest: {r['nearest']}: {r['nearest_snippet']}")
        else:
            print(f"        nearest: (no line mentions {r['mention']!r} at all)")


def print_attribution_table(persona_name: str, rows: list[dict]) -> None:
    print(f"\n--- Attribution trace: {persona_name} ---")
    if not rows:
        print("No entity-attributed sentences found.")
        return

    analysis_count = sum(1 for r in rows if r["classification"] == "ANALYSIS")
    assertion_count = sum(1 for r in rows if r["classification"] == "ASSERTION")
    print(f"Classified: {analysis_count} ANALYSIS, {assertion_count} ASSERTION")

    unsourced_assertions = [r for r in rows if r["classification"] == "ASSERTION" and not r["confirmed"]]
    if not unsourced_assertions:
        print("No unsourced ASSERTION sentences about a named politician or institution.")
        return

    print(f"UNSOURCED assertions ({len(unsourced_assertions)}):")
    for r in unsourced_assertions:
        tag = f"[{r['label']}]"
        sentence = r["sentence"] if len(r["sentence"]) <= 160 else r["sentence"][:157] + "..."
        print(f"{tag} {sentence}")
        if r["nearest"]:
            print(f"        nearest: {r['nearest']}: {r['nearest_snippet']}")
        else:
            print(f"        nearest: (no line mentions {r['entity']!r} at all)")


# --- Manifest ----------------------------------------------------------------


def save_manifest(edition_id: str, edition: dict, new_pieces: list[dict]) -> str:
    os.makedirs(SPECIAL_MANIFEST_DIR, exist_ok=True)
    path = os.path.join(SPECIAL_MANIFEST_DIR, f"{edition_id}.json")

    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = {"edition": edition_id, "publish_date": edition["publish_date"], "pieces": []}

    by_persona = {p["persona"]: p for p in manifest.get("pieces", [])}
    for p in new_pieces:
        by_persona[p["persona"]] = p
    manifest["pieces"] = list(by_persona.values())

    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path


def run(edition_id: str, persona_slug: str | None, dry_run: bool, force: bool) -> None:
    editions = load_editions()
    edition = get_edition(editions, edition_id)

    publish_date = date.fromisoformat(edition["publish_date"])
    lookback_start = date.fromisoformat(edition["lookback_start"])
    today = date.today()

    days = window_days(lookback_start, today)
    logger.info(
        f"=== Special edition {edition_id!r} — window {lookback_start.isoformat()} to {today.isoformat()} "
        f"({len(days)} day(s)), publishing {publish_date.isoformat()} ==="
    )

    country_data = gather_week(days) if days else {c: [] for c in COUNTRY_ORDER}
    brazil_digests = country_data.get("brazil") or []

    if persona_slug is not None:
        if persona_slug not in PERSONAS_BY_SLUG:
            raise ValueError(f"Unknown persona slug {persona_slug!r} — expected one of {sorted(PERSONAS_BY_SLUG)}")
        personas_to_run = [PERSONAS_BY_SLUG[persona_slug]]
    else:
        personas_to_run = PERSONAS

    if dry_run:
        print(f"=== DRY RUN — Special edition {edition_id!r} ===\n")
        print(f"Publish date:    {edition['publish_date']}")
        print(f"Lookback start:  {edition['lookback_start']}  ->  today: {today.isoformat()}")
        print(f"Topic pending:   {edition.get('topic_pending', False)}")
        print(f"Topic:\n  {edition['topic']}\n")

        print("Source files found:")
        for country in COUNTRY_ORDER:
            digests = country_data.get(country) or []
            label = "PRIMARY" if country == "brazil" else "secondary"
            if not digests:
                print(f"  [{country}] ({label}) — none found in window")
            else:
                for d in digests:
                    print(f"  [{country}] ({label}) {d['date']}: {d['title']}")

        sample_personas = personas_to_run[:2]
        for persona in sample_personas:
            angle = edition["angles"].get(persona.slug, "(no angle configured for this persona in this edition)")
            prompt = build_special_prompt(persona, angle, edition, country_data)
            print(f"\n=== PROMPT — {persona.name} ({persona.slug}) ===\n")
            print(prompt)

        print("\nDry run — Sonnet API not called, no files written.")
        return

    if edition.get("topic_pending"):
        raise RuntimeError(
            f"Edition {edition_id!r} has topic_pending=true in {EDITIONS_CONFIG_PATH} — "
            "fill in the real topic (and set topic_pending to false) before generating for real."
        )

    if not brazil_digests:
        raise RuntimeError(
            f"No Brazil digest material found in the window {lookback_start.isoformat()} to {today.isoformat()} "
            "— aborting rather than generating ungrounded special-edition pieces."
        )

    source_corpus = build_source_corpus(country_data)
    allowed_facts = edition.get("allowed_facts") or []
    known_entities = extract_known_entities(source_corpus)
    line_index = build_line_index(days)
    generated_pieces = []

    for persona in personas_to_run:
        angle = edition["angles"].get(persona.slug)
        if not angle:
            raise ValueError(f"No angle configured for persona {persona.slug!r} in edition {edition_id!r}")

        existing_path = os.path.join(OPED_OUTPUT_DIR, f"{persona.slug}_{publish_date.isoformat()}.md")
        if os.path.exists(existing_path) and not force:
            logger.warning(f"{existing_path} already exists — skipping (pass --force to overwrite).")
            continue

        prompt = build_special_prompt(persona, angle, edition, country_data)

        logger.info(f"Generating special-edition piece for {persona.name} ({persona.slug})…")
        piece = generate_oped(prompt)
        word_count = len(piece.split())
        report = grounding_report(piece, source_corpus, allowed_facts)

        needs_retry_grounding = bool(report["unverified_figures"] or report["unverified_quotes"])
        needs_retry_length = word_count > WORD_COUNT_RETRY_THRESHOLD
        retried = False
        needs_human_review = False

        if needs_retry_grounding or needs_retry_length:
            retried = True
            offending = report["unverified_figures"] + report["unverified_quotes"] if needs_retry_grounding else []
            overage = word_count if needs_retry_length else None
            logger.warning(
                f"{persona.name}: retrying once — grounding_issues={needs_retry_grounding} "
                f"length_issue={needs_retry_length} ({word_count} words)"
            )
            retry_prompt = build_retry_prompt(prompt, offending, overage)
            piece = generate_oped(retry_prompt)
            word_count = len(piece.split())
            report = grounding_report(piece, source_corpus, allowed_facts)
            if report["unverified_figures"] or report["unverified_quotes"]:
                needs_human_review = True
                logger.warning(f"{persona.name}: still has unverified items after retry — flagging NEEDS HUMAN REVIEW")
            if word_count > WORD_COUNT_HARD_CAP:
                # Length alone never flags NEEDS HUMAN REVIEW — just a note for the log.
                logger.warning(f"{persona.name}: still {word_count} words after retry (cap {WORD_COUNT_HARD_CAP}).")

        logger.info(f"Generating headline for {persona.name}…")
        headline = generate_headline(piece)

        path = save_oped(persona, publish_date, headline, piece)
        logger.info(f"Saved {persona.name}'s piece to {path}")

        generated_pieces.append({
            "persona": persona.name,
            "slug": persona.slug,
            "title": headline,
            "path": path,
            "word_count": word_count,
            "piece": piece,
            "retried": retried,
            "needs_human_review": needs_human_review,
        })

    if generated_pieces:
        manifest_entries = [
            {
                "persona": p["persona"],
                "title": p["title"],
                "path": p["path"],
                "needs_human_review": p["needs_human_review"],
            }
            for p in generated_pieces
        ]
        manifest_path = save_manifest(edition_id, edition, manifest_entries)
        logger.info(f"Manifest updated: {manifest_path}")

    print_full_report(generated_pieces, source_corpus, allowed_facts, known_entities, line_index)


def print_full_report(
    pieces: list[dict],
    source_corpus: str,
    allowed_facts: list[str],
    known_entities: set[str],
    line_index: list[tuple[str, int, str]],
) -> None:
    print("\n=== SUMMARY ===")
    for p in pieces:
        in_range = WORD_COUNT_TARGET[0] <= p["word_count"] <= WORD_COUNT_TARGET[1]
        flags = []
        if not in_range:
            flags.append(f"outside {WORD_COUNT_TARGET[0]}-{WORD_COUNT_TARGET[1]} target")
        if p.get("retried"):
            flags.append("retried once")
        if p.get("needs_human_review"):
            flags.append("NEEDS HUMAN REVIEW")
        flag_str = f"  ({'; '.join(flags)})" if flags else ""
        print(f"- {p['persona']}: \"{p['title']}\" — {p['word_count']} words{flag_str} — {p['path']}")

    for p in pieces:
        print_grounding_report(p["persona"], p["piece"], source_corpus, allowed_facts)

    for p in pieces:
        rows = attribution_trace(p["piece"], p["title"], known_entities, line_index)
        print_attribution_table(p["persona"], rows)
        print_candidate_unsourced_assertions(p["persona"], p["piece"], p["title"], line_index)

    for p in pieces:
        print_vote_figures(p["persona"], p["piece"], p["title"], line_index)

    for p in pieces:
        print_remaining_quotes(p["persona"], p["piece"], p["title"])


def report_only(edition_id: str) -> None:
    """Re-run the grounding report and attribution trace against pieces
    already on disk, per the edition's manifest — no API calls, no opinion
    file writes. Rebuilds the same source corpus / entity set / line index
    the original generation used (same window), so results are directly
    comparable. Recomputes each piece's needs_human_review flag from the
    fresh grounding report (unverified figures/quotes only — length never
    drives this flag) and writes it back to the manifest; the manifest is
    the ONLY file this function writes."""
    from generation.oped_builder import _strip_oped_body

    editions = load_editions()
    edition = get_edition(editions, edition_id)

    manifest_path = os.path.join(SPECIAL_MANIFEST_DIR, f"{edition_id}.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"No manifest found at {manifest_path} — nothing to report on.")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    lookback_start = date.fromisoformat(edition["lookback_start"])
    today = date.today()
    days = window_days(lookback_start, today)

    country_data = gather_week(days) if days else {c: [] for c in COUNTRY_ORDER}
    source_corpus = build_source_corpus(country_data)
    allowed_facts = edition.get("allowed_facts") or []
    known_entities = extract_known_entities(source_corpus)
    line_index = build_line_index(days)

    pieces = []
    for entry in manifest.get("pieces", []):
        path = entry["path"]
        if not os.path.exists(path):
            logger.warning(f"{entry['persona']}: manifest path not found on disk: {path} — skipping")
            continue
        with open(path, encoding="utf-8") as f:
            content = f.read()
        body = _strip_oped_body(content)
        report = grounding_report(body, source_corpus, allowed_facts)
        needs_human_review = bool(report["unverified_figures"] or report["unverified_quotes"])
        entry["needs_human_review"] = needs_human_review  # written back to `manifest` below
        pieces.append({
            "persona": entry["persona"],
            "title": entry["title"],
            "path": path,
            "word_count": len(body.split()),
            "piece": body,
            "needs_human_review": needs_human_review,
        })

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")
    logger.info(f"Recomputed needs_human_review for {len(pieces)} piece(s) and saved: {manifest_path}")

    print(f"=== REPORT ONLY — Special edition {edition_id!r} (no API calls; manifest needs_human_review refreshed) ===")
    print_full_report(pieces, source_corpus, allowed_facts, known_entities, line_index)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a special-edition OpEd series (all columnists, one shared topic).")
    parser.add_argument("--edition", required=True, help="Edition id from generation/special_editions.json (e.g. brazil-2026-r1)")
    parser.add_argument("--persona", default=None, choices=sorted(PERSONAS_BY_SLUG), help="Generate only this columnist's piece instead of all 8")
    parser.add_argument("--dry-run", action="store_true", help="Show source files and sample prompts without calling the API or saving")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing piece for a persona/date instead of skipping it")
    parser.add_argument("--report-only", action="store_true", help="Re-run grounding report + attribution trace on manifest pieces already on disk; no API calls, no file writes")
    args = parser.parse_args()

    try:
        if args.report_only:
            report_only(args.edition)
        else:
            run(args.edition, args.persona, args.dry_run, args.force)
    except Exception as exc:
        logger.error(f"Special edition generation failed: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
