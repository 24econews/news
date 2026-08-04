import { API_BASE, RAW_BASE, FETCH_OPTS, fetchText } from './digests'

const OPED_DIR = 'digests/opinion'

export interface OpedMeta {
  slug: string
  date: string
  personaName: string
  lensShort: string
  title: string
}

export interface OpedContent extends OpedMeta {
  paragraphs: string[]
  bioDisclosure: string | null
  rawContent: string
}

// File names are `{persona-slug}_{YYYY-MM-DD}.md` — the slug/date pair is the
// canonical identity, independent of whatever the PERSONA/DATE metadata says.
const FILENAME_RE = /^([a-z-]+)_(\d{4}-\d{2}-\d{2})\.md$/

// DATE (and the filename date) are calendar dates assigned by the generation
// pipeline running on GitHub Actions runners, which default to UTC — so
// "today" for gating purposes is the server's UTC calendar date, not local
// time. YYYY-MM-DD strings compare correctly with plain `<=`, same as the
// `.localeCompare()` sorting already used on these dates elsewhere.
function todayUTC(): string {
  return new Date().toISOString().slice(0, 10)
}

export function isPublished(date: string): boolean {
  return date <= todayUTC()
}

export async function getAllOpeds(): Promise<OpedContent[]> {
  let files: Array<{ name: string; type: string }>

  try {
    const res = await fetch(`${API_BASE}/${OPED_DIR}`, FETCH_OPTS)
    if (!res.ok) return []
    files = await res.json()
  } catch {
    return []
  }

  const opedFiles = files.filter((f) => f.type === 'file' && FILENAME_RE.test(f.name))

  const opeds = await Promise.all(
    opedFiles.map(async (f) => {
      const match = f.name.match(FILENAME_RE)!
      const [, slug, date] = match
      const content = await fetchText(`${RAW_BASE}/${OPED_DIR}/${f.name}`)
      if (!content) return null
      return parseOped(content, slug, date)
    })
  )

  return opeds
    .filter((o): o is OpedContent => o !== null && isPublished(o.date))
    .sort((a, b) => b.date.localeCompare(a.date) || a.slug.localeCompare(b.slug))
}

export async function getOpedBySlugAndDate(
  slug: string,
  date: string
): Promise<OpedContent | null> {
  // Gate on the URL's date before fetching — a future-dated slug/date pair
  // must 404 even if the file already exists in the repo (it does, for the
  // test pieces), so direct links can't leak content ahead of schedule.
  if (!isPublished(date)) return null
  const content = await fetchText(`${RAW_BASE}/${OPED_DIR}/${slug}_${date}.md`)
  if (!content) return null
  return parseOped(content, slug, date)
}

export function parseOpedMetadata(content: string, slug: string, date: string): OpedMeta {
  // Same lazy-[\s\S]+?-with-lookahead technique as parseDigestMetadata's TITLE
  // handling in digests.ts, adapted for this file's fixed 4-field metadata
  // block: the lookahead stops at the next "> FIELD:" line (not just a blank
  // line), since TITLE and DATE sit back-to-back with no blank line between.
  const personaMatch = content.match(/^>\s*PERSONA:\s*(.+)$/m)
  const lensMatch = content.match(/^>\s*LENS:\s*(.+)$/m)
  const titleMatch = content.match(/^>\s*TITLE:\s*([\s\S]+?)(?=\n>\s*[A-Z_]+:|\n\s*\n)/m)
  const dateMatch = content.match(/^>\s*DATE:\s*(\d{4}-\d{2}-\d{2})/m)

  return {
    slug,
    date: dateMatch?.[1] ?? date,
    personaName: personaMatch?.[1].trim() ?? '',
    lensShort: lensMatch?.[1].trim() ?? '',
    title: titleMatch ? titleMatch[1].replace(/\s+/g, ' ').trim() : '',
  }
}

function parseOped(content: string, slug: string, date: string): OpedContent {
  const meta = parseOpedMetadata(content, slug, date)

  // Strip the leading "> FIELD: ..." metadata block to get at the body.
  const body = content.replace(/^(?:>.*\n)+\s*/m, '').trim()

  // Same paragraph-block filtering approach as NarrativeContent in
  // DigestViewer.tsx: split on blank lines, drop structural markers, and
  // treat a lone "*...*"-wrapped closing block as the bio disclosure rather
  // than body prose.
  const blocks = body.split(/\n\n+/).map((b) => b.trim()).filter(Boolean)
  const paragraphs: string[] = []
  let bioDisclosure: string | null = null

  blocks.forEach((block, i) => {
    if (block === '---') return
    const bioMatch = block.match(/^\*([^]+)\*$/)
    if (bioMatch && i === blocks.length - 1) {
      bioDisclosure = bioMatch[1].trim()
      return
    }
    paragraphs.push(block)
  })

  return { ...meta, paragraphs, bioDisclosure, rawContent: content }
}

export function extractOpedExcerpt(paragraphs: string[]): string {
  const first = paragraphs[0] ?? ''
  // A "." flanked by digits (e.g. "12.5") is a decimal point, not a sentence
  // boundary — same guard extractTeaser applies in digests.ts.
  const sentences = first.match(/(?:[^.!?]|(?<=\d)\.(?=\d))+[.!?]+/g) ?? []
  if (sentences.length >= 2) return sentences.slice(0, 2).join(' ')
  return first.slice(0, 220)
}
