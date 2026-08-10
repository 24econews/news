import type { MetadataRoute } from 'next'
import { getActiveCountries } from '@/lib/countries'
import { getCountryDigests } from '@/lib/digests'
import { getAllOpeds } from '@/lib/oped'
import { buildDigestUrl, buildOpinionUrl } from '@/lib/slugify'

export const revalidate = 300

const BASE = 'https://www.24econews.com'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const countries = getActiveCountries()

  const staticEntries: MetadataRoute.Sitemap = [
    { url: BASE, changeFrequency: 'daily', priority: 1 },
    { url: `${BASE}/opinion`, changeFrequency: 'weekly', priority: 0.7 },
    { url: `${BASE}/archive`, changeFrequency: 'daily', priority: 0.7 },
    { url: `${BASE}/search`, changeFrequency: 'monthly', priority: 0.5 },
    ...countries.map((c) => ({
      url: `${BASE}/${c.slug}`,
      changeFrequency: 'daily' as const,
      priority: 0.9,
    })),
  ]

  const digestEntries = (
    await Promise.all(
      countries.map(async (c) => {
        const digests = await getCountryDigests(c.slug)
        return digests.map((d) => ({
          url: `${BASE}${buildDigestUrl(c.slug, d.date, d.title)}`,
          lastModified: new Date(d.date),
          changeFrequency: 'daily' as const,
          priority: 0.8,
        }))
      })
    )
  ).flat()

  const opeds = await getAllOpeds()
  const opedEntries: MetadataRoute.Sitemap = opeds.map((o) => ({
    url: `${BASE}${buildOpinionUrl(o.slug, o.date, o.title)}`,
    lastModified: new Date(o.date),
    changeFrequency: 'monthly' as const,
    priority: 0.6,
  }))

  return [...staticEntries, ...digestEntries, ...opedEntries]
}
