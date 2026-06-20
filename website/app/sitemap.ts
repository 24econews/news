import type { MetadataRoute } from 'next'
import { getActiveCountries } from '@/lib/countries'
import { getCountryDigests } from '@/lib/digests'

export const revalidate = 300

const BASE = 'https://24econews.com'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const countries = getActiveCountries()

  const staticEntries: MetadataRoute.Sitemap = [
    { url: BASE, changeFrequency: 'daily', priority: 1 },
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
          url: `${BASE}/${c.slug}/${d.date}`,
          lastModified: new Date(d.date),
          changeFrequency: 'daily' as const,
          priority: 0.8,
        }))
      })
    )
  ).flat()

  return [...staticEntries, ...digestEntries]
}
