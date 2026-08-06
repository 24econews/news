// Shared slug + URL-building logic for digest and opinion pieces.
//
// Must stay byte-for-byte identical to generation/slugify.py — Python-generated
// links (weekly briefing, Bluesky posts, Related Coverage/Opinion blocks) must
// resolve to the same URLs the website itself generates for the same title,
// or the two diverge and links 404.
//
// CUTOFF_DATE marks a permanent dual-pattern split, not a migration: anything
// dated before it keeps its exact existing plain-date URL forever; anything
// on or after it gets the new date+slug pattern.

export const CUTOFF_DATE = '2026-08-06'

const MAX_SLUG_LENGTH = 60

// U+0300-U+036F is the Combining Diacritical Marks block that NFKD
// decomposition produces for accented Latin characters (á -> a + U+0301).
const COMBINING_MARKS_RE = new RegExp('[̀-ͯ]', 'g')

export function slugify(title: string): string {
  let slug = title
    .toLowerCase()
    .normalize('NFKD')
    .replace(COMBINING_MARKS_RE, '')
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/[\s-]+/g, '-')
    .replace(/^-+|-+$/g, '')

  if (slug.length > MAX_SLUG_LENGTH) {
    slug = slug.slice(0, MAX_SLUG_LENGTH)
    const lastHyphen = slug.lastIndexOf('-')
    if (lastHyphen > 0) slug = slug.slice(0, lastHyphen)
  }

  return slug.replace(/^-+|-+$/g, '')
}

export function buildDigestUrl(country: string, date: string, title: string): string {
  if (date < CUTOFF_DATE) return `/${country}/${date}`
  const slug = slugify(title)
  return slug ? `/${country}/${date}-${slug}` : `/${country}/${date}`
}

export function buildOpinionUrl(personaSlug: string, date: string, title: string): string {
  if (date < CUTOFF_DATE) return `/opinion/${personaSlug}/${date}`
  const slug = slugify(title)
  return slug ? `/opinion/${personaSlug}/${date}-${slug}` : `/opinion/${personaSlug}/${date}`
}
