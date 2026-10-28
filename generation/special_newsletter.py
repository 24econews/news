"""Build the one-off newsletter for a special-edition OpEd series (see
special_editions.py) — all eight columnists' pieces on one shared subject,
collected into a single email instead of the usual one-piece-per-day cadence.

Only the teasers are model-generated; the subject line, intro, and call to
action are deterministic fixed/templated copy — see build_subject(),
build_intro(), and call_to_action() — so their exact wording and length
budget can't drift between runs. Reuses special_editions.py's
grounding_report() to flag any teaser that strays from its source piece,
plus two sharper checks specific to this script: a per-claim match against
the piece's own sentences (print_claim_support), and a spot-check of
specific claims against the raw source digests (print_claim_spot_checks).
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, REPO_ROOT)

from generation.oped_personas import PERSONAS  # noqa: E402
from generation.oped_builder import _strip_oped_body  # noqa: E402
from generation.slugify import build_opinion_url  # noqa: E402
from generation.special_editions import (  # noqa: E402
    SPECIAL_MANIFEST_DIR,
    grounding_report,
    load_editions,
    get_edition,
    window_days,
    build_line_index,
    find_lines_with_figure,
)
from publishing.oped_bluesky_poster import parse_oped  # noqa: E402
from publishing.x_poster import SITE_BASE_URL, split_sentences  # noqa: E402

MODEL = "claude-haiku-4-5-20251001"

SIGNATURE = "— John Dominguez, Editor"

# Count is driven by how many pieces actually clear needs_human_review — see
# gather_included_pieces() — so the wording stays correct if a piece is skipped.
_NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}

PERSONA_ORDER = {p.slug: i for i, p in enumerate(PERSONAS)}

SLUG_DATE_RE = re.compile(r"^([a-z-]+)_(\d{4}-\d{2}-\d{2})\.md$")

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# Upper bound on top of the "about 60 words" target in build_intro() — a
# little slack for the count word's length, not a license to drift further.
INTRO_MAX_WORDS = 65
INTRO_MAX_SENTENCES = 3

TEASER_MAX_WORDS = 35
TEASER_MIN_SENTENCES = 1
TEASER_MAX_SENTENCES = 2

# Rotated across pieces in persona order (see generate_teaser) so no two
# consecutive teasers open with the same verb. Length 5 against 8 pieces
# guarantees no adjacent repeat without needing to track the previous pick.
TEASER_VERBS = ["argues", "contends", "maintains", "holds", "makes the case"]


def strip_trailing_period(title: str) -> str:
    return title[:-1] if title.endswith(".") else title


def call_to_action(count: int) -> str:
    """Fixed, non-generated copy — only the piece count varies. Keep the
    wording exactly as specified; only _NUMBER_WORDS[count] changes."""
    word = _NUMBER_WORDS.get(count, str(count))
    return (
        "Whoever you are, a start-up founder in São Paulo, an economist "
        "working near 19th and H in Washington, a policy analyst in Brussels "
        "or Beijing, a sustainable fund manager in Rio, there is something "
        f"for you in these {word} columns. They disagree with one another on "
        "purpose, so read the ones that challenge you most. If they're "
        "useful, forward this edition to colleagues and friends who follow "
        "Brazil. And tell us what you think: write to the editor at "
        "contact-the-team@24econews.com. We may publish a selection of "
        "letters on the site, with the writer's permission."
    )


def build_subject(count: int, edition: dict) -> str:
    """Fixed, non-generated subject line, templated per-edition in
    generation/special_editions.json (key: newsletter_subject) with a
    {count_word} placeholder — only the piece count varies."""
    word = _NUMBER_WORDS.get(count, str(count))
    return edition["newsletter_subject"].format(count_word=word)


def build_intro(count: int, edition: dict) -> str:
    """Fixed, non-generated intro, templated per-edition in
    generation/special_editions.json (key: newsletter_intro) with a
    {count_word} placeholder — describes only what the edition contains,
    never what a candidate said, avoided, or promised. Enforced at most
    INTRO_MAX_SENTENCES sentences and INTRO_MAX_WORDS words below, since
    this text is static copy and should never silently drift past its
    own budget after an edit.

    The budget applies only to the first paragraph (the promotional
    summary this guard exists to keep from drifting). A second paragraph,
    separated by a blank line — e.g. an editor's note on late-breaking
    developments — is exact verbatim copy dictated by events, not prone
    to the same drift, so it's exempt from the word/sentence cap."""
    word = _NUMBER_WORDS.get(count, str(count))
    intro = edition["newsletter_intro"].format(count_word=word)
    first_paragraph = intro.split("\n\n", 1)[0]
    sentence_count = len(SENTENCE_SPLIT_RE.split(first_paragraph.strip()))
    word_count = len(first_paragraph.split())
    if sentence_count > INTRO_MAX_SENTENCES:
        raise AssertionError(f"Intro's first paragraph has {sentence_count} sentences, exceeds the {INTRO_MAX_SENTENCES}-sentence budget: {first_paragraph!r}")
    if word_count > INTRO_MAX_WORDS:
        raise AssertionError(f"Intro's first paragraph has {word_count} words, exceeds the {INTRO_MAX_WORDS}-word budget: {first_paragraph!r}")
    return intro


def verify_call_to_action(newsletter: str, count: int) -> None:
    """Fail loudly if the assembled newsletter doesn't contain the fixed
    call-to-action text verbatim — this is the one piece of copy that must
    never be paraphrased, truncated, or otherwise altered by anything
    upstream of assembly."""
    cta = call_to_action(count)
    if cta not in newsletter:
        raise RuntimeError(
            "Call-to-action text is missing or altered in the assembled newsletter. "
            f"Expected verbatim:\n{cta!r}"
        )


def load_manifest(edition_id: str) -> dict:
    path = os.path.join(SPECIAL_MANIFEST_DIR, f"{edition_id}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No manifest found at {path} — run special_editions.py for this edition first.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_slug_date(path: str) -> tuple[str, str]:
    match = SLUG_DATE_RE.match(os.path.basename(path))
    if not match:
        raise ValueError(f"Can't parse persona slug/date from manifest path: {path}")
    return match.group(1), match.group(2)


def surname(persona_name: str) -> str:
    return persona_name.split()[-1]


def gather_included_pieces(manifest: dict) -> list[dict]:
    """Pieces not flagged needs_human_review, in house persona order, each
    with its body text, title, and URL resolved from the file itself —
    NOT from the manifest's own "title" field. special_editions.py only
    calls save_manifest() once its whole generation loop finishes, so a
    manifest written by a run that crashed partway (an API timeout, say)
    keeps stale titles for every piece that loop never reached the end
    for, even though those pieces' files were already saved with their
    real (possibly regenerated) title. Trusting the file avoids building
    a URL slug that doesn't match the title actually on the page.
    """
    included = []
    for entry in manifest.get("pieces", []):
        if entry.get("needs_human_review"):
            logger.info(f"Skipping {entry['persona']} — flagged needs_human_review")
            continue
        path = entry["path"]
        if not os.path.exists(path):
            logger.warning(f"{entry['persona']}: manifest path not found on disk: {path} — skipping")
            continue
        slug, date_str = parse_slug_date(path)
        persona_name, _lens_short, title, _sentences = parse_oped(path)
        with open(path, encoding="utf-8") as f:
            body = _strip_oped_body(f.read())
        if title != entry.get("title"):
            logger.warning(
                f"{persona_name}: manifest title is stale — manifest says {entry.get('title')!r}, "
                f"file says {title!r}. Using the file's title."
            )
        url = f"{SITE_BASE_URL}{build_opinion_url(slug, date_str, title)}"
        included.append({
            "persona": persona_name,
            "slug": slug,
            "date": date_str,
            "title": title,
            "url": url,
            "body": body,
        })
    included.sort(key=lambda p: PERSONA_ORDER.get(p["slug"], len(PERSONA_ORDER)))
    return included


def refresh_manifest_titles(manifest: dict, manifest_path: str, pieces: list[dict]) -> int:
    """Write each included piece's file-derived title back into the
    manifest, correcting exactly the staleness gather_included_pieces()
    warns about. Returns how many entries actually changed."""
    by_persona = {p["persona"]: p["title"] for p in pieces}
    changed = 0
    for entry in manifest.get("pieces", []):
        fresh_title = by_persona.get(entry["persona"])
        if fresh_title is not None and entry.get("title") != fresh_title:
            entry["title"] = fresh_title
            changed += 1
    if changed:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            f.write("\n")
    return changed


def _call_haiku(prompt: str, max_tokens: int) -> str:
    import anthropic
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


TEASER_PROMPT_TEMPLATE = """Below is an opinion column published by 24EcoNews, written by {persona}.

Write a teaser for a newsletter, following this exact format — all requirements are strict:

- Exactly one or two sentences, {max_words} words total at most.
- Must begin with exactly "{surname} {verb} that" — this verb has already been chosen for you; do not substitute a different one.
- State the piece's central claim, restated closely in your own words. Do not introduce any claim, framing, or figure beyond what the piece itself states.
- Do not use any digits anywhere in the teaser — no figures, percentages, amounts, or dates of any kind, even if the piece itself states them. Describe the claim qualitatively instead.
- Do not make any claim about what a candidate has said, avoided, or planned unless the piece attributes it as settled fact rather than a hypothetical scenario.
- Do not use quotation marks anywhere.
- End on the open question the piece raises — draw the reader in without revealing the piece's conclusion. The teaser's final sentence must be that question, ending in "?".
{extra_instruction}
TITLE: {title}

PIECE:
{body}

Return ONLY the teaser text, nothing else — no preamble, no label."""

# Persona-specific wording overrides, layered onto the shared prompt above.
TEASER_PERSONA_NOTES = {
    "Diego Restrepo": '- Refer to "the fate of Pix and fintech regulation" — do not say "Pix\'s survival".',
}


def validate_teaser(teaser: str, surname_: str, verb: str, body: str) -> list[str]:
    violations = []
    word_count = len(teaser.split())
    if word_count > TEASER_MAX_WORDS:
        violations.append(f"{word_count} words (max {TEASER_MAX_WORDS})")
    sentences = split_sentences(teaser)
    sentence_count = len(sentences)
    if not (TEASER_MIN_SENTENCES <= sentence_count <= TEASER_MAX_SENTENCES):
        violations.append(f"{sentence_count} sentences (must be {TEASER_MIN_SENTENCES}-{TEASER_MAX_SENTENCES})")
    lowered = teaser.strip().lower()
    if not lowered.startswith(f"{surname_.lower()} {verb.lower()} that"):
        violations.append(f"must start with '{surname_} {verb} that'")
    if re.search(r'["“”]', teaser):
        violations.append("contains quotation marks")
    if not teaser.strip().endswith("?"):
        violations.append("must end with a question mark")
    if len(sentences) >= 2 and any(s.strip().endswith("?") for s in sentences[:-1]):
        violations.append("only the final sentence may be a question — earlier sentence(s) must state the claim declaratively")
    if "cuts" in lowered and "cuts" not in body.lower():
        violations.append('uses "cuts", a word not present in the piece')
    return violations


TEASER_MAX_ATTEMPTS = 5

DIGIT_RE = re.compile(r"\d")


def build_teaser_prompt(persona: str, title: str, body: str, verb: str) -> str:
    extra_instruction = TEASER_PERSONA_NOTES.get(persona, "")
    return TEASER_PROMPT_TEMPLATE.format(
        persona=persona, surname=surname(persona), verb=verb, title=title, body=body,
        max_words=TEASER_MAX_WORDS, extra_instruction=extra_instruction,
    )


def enforce_teaser_no_digits(teaser: str, persona: str, title: str, body: str, verb: str) -> str:
    """Digits are never allowed in a teaser, whether it was just generated or
    loaded from the saved teasers file: a single dedicated regeneration, then
    a hard stop rather than the "use as-is, flag for review" fallback other
    format violations get — a figure slipping into a teaser is exactly the
    fabrication-adjacent risk this edition's digit ban exists to close off
    entirely."""
    if not DIGIT_RE.search(teaser):
        return teaser
    logger.warning(f"{persona}: teaser contains a digit — regenerating once")
    prompt = build_teaser_prompt(persona, title, body, verb)
    digit_correction = (
        f"\n\nYour previous attempt contained a digit, which is not allowed under any circumstance: "
        f"{teaser!r}\n\nRewrite the teaser with absolutely no digits anywhere — describe every figure, "
        "percentage, amount, or date qualitatively instead. Follow every other requirement exactly as before."
    )
    teaser = _call_haiku(prompt + digit_correction, max_tokens=120)
    if DIGIT_RE.search(teaser):
        raise RuntimeError(
            f"{persona}: teaser still contains a digit after regenerating once — aborting. "
            f"Offending teaser: {teaser!r}"
        )
    return teaser


def generate_teaser(persona: str, title: str, body: str, verb: str) -> str:
    surname_ = surname(persona)
    prompt = build_teaser_prompt(persona, title, body, verb)
    teaser = _call_haiku(prompt, max_tokens=120)
    violations = validate_teaser(teaser, surname_, verb, body)
    attempt = 1
    while violations and attempt < TEASER_MAX_ATTEMPTS:
        attempt += 1
        logger.warning(f"{persona}: teaser violates format ({'; '.join(violations)}) — retrying (attempt {attempt}/{TEASER_MAX_ATTEMPTS})")
        correction = (
            f"\n\nYour previous attempt violated: {'; '.join(violations)}. "
            f"Previous attempt: {teaser!r}\n\nTry again, following every requirement exactly. "
            f"If it was over the word limit, cut a clause rather than trimming individual words — "
            f"stay comfortably under {TEASER_MAX_WORDS} words, not right at the edge."
        )
        teaser = _call_haiku(prompt + correction, max_tokens=120)
        violations = validate_teaser(teaser, surname_, verb, body)
    if violations:
        logger.warning(f"{persona}: teaser still violates format after {attempt} attempts ({'; '.join(violations)}) — using as-is, flag for review")

    return enforce_teaser_no_digits(teaser, persona, title, body, verb)


# --- Teaser persistence -------------------------------------------------
#
# Teasers are saved to disk (keyed by persona slug) so a run — dry or real —
# reads the same fixed wording every time instead of re-generating (and
# risking different phrasing) on every invocation. --regenerate-teasers is
# the only path that calls the model and overwrites the file.


def teasers_path(edition_id: str) -> str:
    return os.path.join(SPECIAL_MANIFEST_DIR, f"teasers_{edition_id}.json")


def save_teasers(edition_id: str, teasers: dict) -> str:
    path = teasers_path(edition_id)
    os.makedirs(SPECIAL_MANIFEST_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(teasers, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path


def get_teasers(edition_id: str, pieces: list[dict], regenerate: bool) -> dict:
    """Return {slug: teaser} for every piece. Generates fresh (and saves)
    when `regenerate` is set or no teasers file exists yet; otherwise loads
    the saved file and re-applies the digit check to its contents — a
    teaser edited by hand after saving could reintroduce a digit, and that
    check must hold regardless of where the teaser text came from."""
    path = teasers_path(edition_id)
    if regenerate or not os.path.exists(path):
        teasers = {}
        for i, p in enumerate(pieces):
            verb = TEASER_VERBS[i % len(TEASER_VERBS)]
            logger.info(f"Generating teaser for {p['persona']} (verb: {verb})…")
            teaser = generate_teaser(p["persona"], p["title"], p["body"], verb)
            _check_grounding(f"{p['persona']} teaser", teaser, p["body"])
            teasers[p["slug"]] = teaser
        save_teasers(edition_id, teasers)
        logger.info(f"Teasers saved to {path}")
        return teasers

    with open(path, encoding="utf-8") as f:
        teasers = json.load(f)
    logger.info(f"Loaded teasers from {path}")

    changed = False
    for i, p in enumerate(pieces):
        slug = p["slug"]
        if slug not in teasers:
            raise RuntimeError(
                f"No teaser found for persona {p['persona']} ({slug}) in {path} — "
                "run with --regenerate-teasers to rebuild the file."
            )
        verb = TEASER_VERBS[i % len(TEASER_VERBS)]
        fixed = enforce_teaser_no_digits(teasers[slug], p["persona"], p["title"], p["body"], verb)
        if fixed != teasers[slug]:
            teasers[slug] = fixed
            changed = True
    if changed:
        save_teasers(edition_id, teasers)
        logger.info(f"Digit violation(s) fixed in loaded teasers — rewrote {path}")
    return teasers


def _significant_words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z]{4,}|\d[\d.,]*%?", text)}


MIN_CLAIM_SUPPORT = 3  # minimum shared significant words to count a piece sentence as supporting a claim


def extract_claims(teaser: str) -> list[str]:
    """Declarative (non-question) sentences in the teaser — the factual
    claims to verify. The closing question is deliberately excluded: it's
    not a claim, and matching it against piece sentences isn't meaningful."""
    return [s.strip() for s in split_sentences(teaser) if s.strip() and not s.strip().endswith("?")]


def find_supporting_sentence(claim: str, piece_sentences: list[str]) -> tuple[str | None, int]:
    claim_words = _significant_words(claim)
    best, best_score = None, -1
    for sent in piece_sentences:
        score = len(claim_words & _significant_words(sent))
        if score > best_score:
            best, best_score = sent, score
    return best, best_score


def print_claim_support(pieces: list[dict]) -> None:
    print("=== CLAIM SUPPORT CHECK (teaser claim vs. piece sentence) ===\n")
    for p in pieces:
        print(f"[{p['persona']}] \"{strip_trailing_period(p['title'])}\"")
        print(f"Teaser: {p['teaser']}")
        claims = extract_claims(p["teaser"])
        piece_sentences = split_sentences(p["body"])
        if not claims:
            print("  (no declarative claim sentence found in teaser)")
            print()
            continue
        for claim in claims:
            sent, score = find_supporting_sentence(claim, piece_sentences)
            print(f"  CLAIM: {claim}")
            if sent is not None and score >= MIN_CLAIM_SUPPORT:
                print(f"  SUPPORTING SENTENCE: {sent}")
            else:
                nearest = f" (nearest, unconfirmed: {sent})" if sent else ""
                print(f"  ⚠ NO SINGLE SUPPORTING SENTENCE FOUND{nearest}")
        print()


# --- Item 3: spot-check specific claims against the raw source digests ------
# (persona, kind, value) — kind "figure" uses the same digit-boundary-safe
# matcher special_editions.py uses for vote/poll figures; "phrase" is a
# plain substring search. Values are the exact strings worth re-verifying
# against the digests directly, independent of whether the piece itself
# states them correctly.
CLAIM_SPOT_CHECKS = [
    ("Eduardo Ferraz", "phrase", "largest party in both the Chamber and the Senate"),
    ("Camila Duarte", "figure", "60.8%"),
    ("Camila Duarte", "figure", "9.5%"),
    ("Camila Duarte", "phrase", "April 2020 and August 2026"),
    ("Camila Duarte", "phrase", "22 of 27 states"),
    ("Mariana Coelho", "phrase", "tenfold"),
    ("Mariana Coelho", "phrase", "Chinese restrictions"),
    ("Ricardo Almeida", "figure", "7.7%"),
    ("Ricardo Almeida", "figure", "82.9%"),
    ("Sofia Andrade", "figure", "8.19%"),
]


def find_lines_containing(phrase: str, line_index: list[tuple[str, int, str]]) -> list[tuple[str, int]]:
    return [(path, lineno) for path, lineno, line_text in line_index if phrase in line_text]


def build_digest_line_index(edition_id: str) -> list[tuple[str, int, str]]:
    editions = load_editions()
    edition = get_edition(editions, edition_id)
    lookback_start = date.fromisoformat(edition["lookback_start"])
    days = window_days(lookback_start, date.today())
    return build_line_index(days)


def print_claim_spot_checks(line_index: list[tuple[str, int, str]]) -> None:
    print("=== CLAIM SPOT-CHECK AGAINST SOURCE DIGESTS ===\n")
    for persona, kind, value in CLAIM_SPOT_CHECKS:
        locations = find_lines_with_figure(value, line_index) if kind == "figure" else find_lines_containing(value, line_index)
        label = f"[{persona}] {value!r}"
        if locations:
            where = ", ".join(f"{path}:{lineno}" for path, lineno in locations)
            print(f"{label}: {where}")
        else:
            print(f"{label}: NOT FOUND")
    print()


def find_sentence_containing_all(body: str, keywords: list[str]) -> str | None:
    for sent in split_sentences(body):
        low = sent.lower()
        if all(kw.lower() in low for kw in keywords):
            return sent
    return None


def print_almeida_candidates_check(pieces: list[dict]) -> None:
    """Item 3: verify the specific sentence in Almeida's piece claiming both
    candidates avoided naming the R$250bn adjustment. If it's not actually
    there, that clause has no business being in his teaser."""
    print("=== ALMEIDA — 'both candidates avoided naming it' check ===\n")
    piece = next((p for p in pieces if p["persona"] == "Ricardo Almeida"), None)
    if piece is None:
        print("Ricardo Almeida not included in this edition.\n")
        return
    sentence = find_sentence_containing_all(piece["body"], ["avoided", "candidates"])
    if sentence:
        print(f"FOUND in piece: {sentence}")
        has_cuts_word = "cuts" in sentence.lower()
        print(f"Sentence itself says \"cuts\": {has_cuts_word} — teaser must say \"R$250 billion in adjustment\", not \"cuts\", accordingly.")
    else:
        print("NOT FOUND — no sentence in Almeida's piece claims both candidates avoided naming it.")
        if "avoided naming" in piece["teaser"].lower() or "avoided spelling out" in piece["teaser"].lower():
            logger.warning("Ricardo Almeida: teaser contains the 'avoided naming it' clause despite no supporting sentence — should be dropped.")
    print()


def print_coelho_meat_export_check(pieces: list[dict], line_index: list[tuple[str, int, str]]) -> None:
    """Item 4: verify Coelho's meat-export-to-China/Europe sentence, and
    check each half (the China restriction, the Europe certification
    suspension) against the raw digests separately — a sentence can combine
    a sourced half with an unsourced one, so they're checked independently."""
    print("=== COELHO — meat exports (China/Europe) check ===\n")
    piece = next((p for p in pieces if p["persona"] == "Mariana Coelho"), None)
    if piece is None:
        print("Mariana Coelho not included in this edition.\n")
        return
    sentence = find_sentence_containing_all(piece["body"], ["meat exports"])
    if not sentence:
        print("NOT FOUND — no sentence in Coelho's piece makes the meat exports claim.\n")
        return
    print(f"Piece sentence: {sentence}\n")

    halves = [("China half ('Chinese restrictions')", "Chinese restrictions"),
              ("Europe half ('European certifications')", "European certifications")]
    for label, phrase in halves:
        locations = find_lines_containing(phrase, line_index)
        if locations:
            where = ", ".join(f"{path}:{lineno}" for path, lineno in locations)
            print(f"{label}: {where}")
        else:
            print(f"{label}: NOT FOUND — unsupported")
    print()


def _check_grounding(label: str, generated_text: str, source_corpus: str) -> None:
    report = grounding_report(generated_text, source_corpus)
    if report["unverified_figures"] or report["unverified_quotes"]:
        logger.warning(
            f"{label}: contains unverified figures/quotes not found in its source material — "
            f"review: figures={report['unverified_figures']} quotes={report['unverified_quotes']}"
        )


def assemble_newsletter(pieces: list[dict], subject: str, intro: str) -> str:
    lines = [f"# {subject}", "", intro.strip(), "", call_to_action(len(pieces)), "", SIGNATURE, "", "---"]
    for p in pieces:
        lines += [
            "",
            f"**[{strip_trailing_period(p['title'])}]({p['url']})** — By {p['persona']}",
            "",
            p["teaser"],
            "",
            f"[Read the piece →]({p['url']})",
        ]
    return "\n".join(lines).strip() + "\n"


def run(edition_id: str, dry_run: bool, regenerate_teasers: bool = False) -> None:
    editions = load_editions()
    edition = get_edition(editions, edition_id)

    manifest_path = os.path.join(SPECIAL_MANIFEST_DIR, f"{edition_id}.json")
    manifest = load_manifest(edition_id)
    total = len(manifest.get("pieces", []))
    pieces = gather_included_pieces(manifest)
    if not pieces:
        raise RuntimeError(
            f"No eligible pieces for edition {edition_id!r} — all {total} are flagged "
            "needs_human_review, or the manifest is empty."
        )
    logger.info(f"Including {len(pieces)}/{total} piece(s) for edition {edition_id!r}")

    changed = refresh_manifest_titles(manifest, manifest_path, pieces)
    if changed:
        logger.info(f"Refreshed {changed} stale manifest title(s) in {manifest_path}")

    teasers = get_teasers(edition_id, pieces, regenerate_teasers)
    for p in pieces:
        p["teaser"] = teasers[p["slug"]]

    count = len(pieces)
    subject = build_subject(count, edition)
    intro = build_intro(count, edition)

    newsletter = assemble_newsletter(pieces, subject, intro)
    verify_call_to_action(newsletter, count)

    label = "DRY RUN" if dry_run else "REAL RUN"
    print(f"=== {label} — special-edition newsletter for {edition_id!r} ===\n")
    print(f"Included pieces: {len(pieces)}/{total}")
    for p in pieces:
        assert p["url"].startswith(SITE_BASE_URL), f"URL does not start with {SITE_BASE_URL}: {p['url']}"
        print(f"  - {p['persona']}: {p['url']}")
    print(f"\nSubject: {subject}\n")

    print("--- FULL NEWSLETTER TEXT ---\n")
    print(newsletter)

    print_claim_support(pieces)

    line_index = build_digest_line_index(edition_id)
    print_claim_spot_checks(line_index)
    print_almeida_candidates_check(pieces)
    print_coelho_meat_export_check(pieces, line_index)

    if dry_run:
        print("DRY RUN — no newsletter file written (manifest title refresh above, if any, was still applied).")
        return

    os.makedirs(SPECIAL_MANIFEST_DIR, exist_ok=True)
    out_path = os.path.join(SPECIAL_MANIFEST_DIR, f"newsletter_{edition_id}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(newsletter)
    logger.info(f"Newsletter written to {out_path}")

    with open(out_path, encoding="utf-8") as f:
        saved_content = f.read()
    print(f"=== SAVED FILE — {out_path} (read back from disk) ===\n")
    print(saved_content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the newsletter for a special-edition OpEd series.")
    parser.add_argument("--edition", required=True, help="Edition id from generation/special_editions.json (e.g. brazil-2026-r1)")
    parser.add_argument("--dry-run", action="store_true", help="Generate and print the newsletter without writing digests/special/newsletter_<id>.md")
    parser.add_argument("--regenerate-teasers", action="store_true", help="Rebuild teasers via the model and overwrite digests/special/teasers_<id>.json, instead of reading the saved file")
    args = parser.parse_args()

    try:
        run(args.edition, args.dry_run, args.regenerate_teasers)
    except Exception as exc:
        logger.error(f"Special-edition newsletter build failed: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
