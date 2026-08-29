import { getActiveCountries } from '@/lib/countries'
import { getCountryDigests } from '@/lib/digests'
import { getAllOpeds } from '@/lib/oped'
import { buildDigestUrl, buildOpinionUrl } from '@/lib/slugify'

// Google News sitemaps must only list content published in the last 48
// hours — unlike the main sitemap.ts, which lists everything forever.
export const revalidate = 300

const BASE = 'https://www.24econews.com'
const NEWS_WINDOW_MS = 48 * 60 * 60 * 1000

interface NewsEntry {
  url: string
  title: string
  date: string // YYYY-MM-DD
}

// Digests/opeds only carry a calendar date, not a publish timestamp (see
// todayUTC() in lib/oped.ts), so a piece is treated as published at
// midnight UTC on its date — the same UTC-calendar-date convention used
// for the isPublished() gate it shares a file with.
function isWithinNewsWindow(dateStr: string): boolean {
  const publishedAt = new Date(`${dateStr}T00:00:00Z`).getTime()
  return Date.now() - publishedAt < NEWS_WINDOW_MS
}

function escapeXml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

function buildUrlEntry({ url, title, date }: NewsEntry): string {
  return `  <url>
    <loc>${escapeXml(url)}</loc>
    <news:news>
      <news:publication>
        <news:name>24EcoNews</news:name>
        <news:language>en</news:language>
      </news:publication>
      <news:publication_date>${date}T00:00:00Z</news:publication_date>
      <news:title>${escapeXml(title)}</news:title>
    </news:news>
  </url>`
}

export async function GET() {
  const countries = getActiveCountries()

  const digestEntries = (
    await Promise.all(
      countries.map(async (c) => {
        const digests = await getCountryDigests(c.slug)
        return digests
          .filter((d) => d.title && isWithinNewsWindow(d.date))
          .map((d): NewsEntry => ({
            url: `${BASE}${buildDigestUrl(c.slug, d.date, d.title)}`,
            title: d.title,
            date: d.date,
          }))
      })
    )
  ).flat()

  const opeds = await getAllOpeds()
  const opedEntries: NewsEntry[] = opeds
    .filter((o) => o.title && isWithinNewsWindow(o.date))
    .map((o) => ({
      url: `${BASE}${buildOpinionUrl(o.slug, o.date, o.title)}`,
      title: o.title,
      date: o.date,
    }))

  const entries = [...digestEntries, ...opedEntries]

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
${entries.map(buildUrlEntry).join('\n')}
</urlset>
`

  return new Response(xml, {
    headers: {
      'Content-Type': 'application/xml',
    },
  })
}
