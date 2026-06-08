import { getActiveCountries } from './countries'

const REPO = '24econews/argentina'
const API_BASE = `https://api.github.com/repos/${REPO}/contents`
const RAW_BASE = `https://raw.githubusercontent.com/${REPO}/main`
const FETCH_OPTS = { next: { revalidate: 3600 } } as const

function digestDir(country: string): string {
  return country === 'argentina' ? 'digests' : `digests/${country}`
}

async function fetchText(url: string): Promise<string | null> {
  try {
    const res = await fetch(url, FETCH_OPTS)
    return res.ok ? res.text() : null
  } catch {
    return null
  }
}

export interface Article {
  title: string
  url: string
  summary: string
  source: string
  publishedAt: string
}

export interface DigestMeta {
  date: string
  country: string
  title: string
  articleCount: number
  sources: string[]
  firstHeadline: string
}

export interface DigestContent extends DigestMeta {
  articles: Article[]
  rawContent: string
}

export async function getCountryDigests(country: string): Promise<DigestMeta[]> {
  const apiUrl = `${API_BASE}/${digestDir(country)}`
  let files: Array<{ name: string; type: string }>

  try {
    const res = await fetch(apiUrl, FETCH_OPTS)
    if (!res.ok) return []
    files = await res.json()
  } catch {
    return []
  }

  const digestFiles = files
    .filter((f) => f.type === 'file' && /^digest_\d{4}-\d{2}-\d{2}\.md$/.test(f.name))
    .sort((a, b) => b.name.localeCompare(a.name))

  return Promise.all(
    digestFiles.map(async (f) => {
      const date = f.name.replace('digest_', '').replace('.md', '')
      const content = await fetchText(`${RAW_BASE}/${digestDir(country)}/${f.name}`)
      if (!content) return { date, country, title: 'Latest Economic Analysis', articleCount: 0, sources: [], firstHeadline: '' }
      return parseDigestMetadata(content, date, country)
    })
  )
}

// Try English version first; fall back to original-language file.
export async function getDigest(
  country: string,
  date: string
): Promise<DigestContent | null> {
  const dir = digestDir(country)
  const enContent = await fetchText(`${RAW_BASE}/${dir}/digest_${date}.en.md`)
  const content = enContent ?? await fetchText(`${RAW_BASE}/${dir}/digest_${date}.md`)
  if (!content) return null

  const meta = parseDigestMetadata(content, date, country)
  const articles = parseArticles(content)
  return { ...meta, articles, rawContent: content }
}

export async function searchDigests(
  query: string,
  country?: string
): Promise<Array<DigestMeta & { matchCount: number; snippet: string }>> {
  const targets = country ? [country] : getActiveCountries().map((c) => c.slug)
  const results: Array<DigestMeta & { matchCount: number; snippet: string }> = []
  const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const pattern = new RegExp(escapedQuery, 'gi')

  for (const c of targets) {
    const digests = await getCountryDigests(c)
    for (const digest of digests) {
      const content = await fetchText(`${RAW_BASE}/${digestDir(c)}/digest_${digest.date}.md`)
      if (!content) continue

      const matches = content.match(pattern) ?? []
      if (matches.length === 0) continue

      const idx = content.search(pattern)
      const start = Math.max(0, idx - 80)
      const end = Math.min(content.length, idx + 160)
      const snippet = content.slice(start, end).replace(/[#*\n]+/g, ' ').trim()

      results.push({ ...digest, matchCount: matches.length, snippet })
    }
  }

  return results.sort((a, b) => b.matchCount - a.matchCount)
}

export function parseDigestMetadata(
  content: string,
  date: string,
  country: string
): DigestMeta {
  const titleLineMatch = content.match(/^> TITLE: (.+)$/m)
  const title = titleLineMatch ? titleLineMatch[1].trim() : 'Latest Economic Analysis'

  const countMatch = content.match(/\*(\d+)\s+(?:artículos|artigos|articles)/)
  const articleCount = countMatch ? parseInt(countMatch[1]) : 0

  const sources: string[] = []
  const sourcesSection = content.match(/## (?:Fuentes|Fontes|Sources)([\s\S]*?)(?=\n---|\n## [^F])/)
  if (sourcesSection) {
    for (const m of sourcesSection[1].matchAll(/\[([^\]]+)\]\(#/g)) {
      sources.push(m[1])
    }
  }

  const headlineMatch = content.match(/### \[([^\]]+)\]/)
  const firstHeadline = headlineMatch ? headlineMatch[1] : ''

  return { date, country, title, articleCount, sources, firstHeadline }
}

function parseArticles(content: string): Article[] {
  const articles: Article[] = []

  const sections = content.split('\n## ')

  for (const section of sections) {
    if (!section.trim() || /^(?:Fuentes|Fontes|Sources)/.test(section)) continue

    const firstNewline = section.indexOf('\n')
    if (firstNewline === -1) continue
    const source = section.slice(0, firstNewline).trim()
    const sectionBody = section.slice(firstNewline + 1)

    const articleParts = sectionBody.split('\n### ')

    for (let i = 1; i < articleParts.length; i++) {
      const part = articleParts[i]
      const nl = part.indexOf('\n')
      if (nl === -1) continue

      const titleLine = part.slice(0, nl)
      const titleMatch = titleLine.match(/^\[([^\]]+)\]\(([^)]+)\)/)
      if (!titleMatch) continue

      const title = titleMatch[1]
      const url = titleMatch[2]
      const body = part.slice(nl + 1).trim()

      const pubMatch = body.match(/\*(?:Publicado|Published|Publicação): ([^*]+)\*/)
      const publishedAt = pubMatch ? pubMatch[1].trim() : ''

      const summary = body
        .replace(/\*(?:Publicado|Published|Publicação):[^*]+\*/g, '')
        .replace(/^---+\s*$/gm, '')
        .trim()

      articles.push({ title, url, summary, source, publishedAt })
    }
  }

  return articles
}

export function formatDate(dateStr: string): string {
  const [year, month, day] = dateStr.split('-').map(Number)
  const d = new Date(year, month - 1, day)
  return d.toLocaleDateString('en-US', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}
