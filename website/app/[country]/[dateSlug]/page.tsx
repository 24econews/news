import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import { getCountry, getActiveCountries } from '@/lib/countries'
import { getDigest, getCountryDigests, extractTeaser } from '@/lib/digests'
import { buildDigestUrl } from '@/lib/slugify'
import DigestViewer from '@/components/DigestViewer'

const BASE = 'https://24econews.com'

// The dateSlug URL segment is "YYYY-MM-DD" (old plain-date pattern) or
// "YYYY-MM-DD-title-slug" (new pattern, see lib/slugify.ts). Only the leading
// date is ever used to look up content — the suffix is cosmetic/SEO only, so
// a stale or mistyped slug still resolves the right digest instead of 404ing.
function extractDate(dateSlug: string): string | null {
  const match = dateSlug.match(/^(\d{4}-\d{2}-\d{2})(?:-|$)/)
  return match ? match[1] : null
}

export async function generateStaticParams() {
  const params: { country: string; dateSlug: string }[] = []
  for (const country of getActiveCountries()) {
    const digests = await getCountryDigests(country.slug)
    for (const digest of digests) {
      const url = buildDigestUrl(country.slug, digest.date, digest.title)
      params.push({ country: country.slug, dateSlug: url.split('/').pop()! })
    }
  }
  return params
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ country: string; dateSlug: string }>
}): Promise<Metadata> {
  const { country, dateSlug } = await params
  const date = extractDate(dateSlug)
  if (!date) return {}
  const digest = await getDigest(country, date)
  if (!digest) return {}

  const countryInfo = getCountry(country)
  const title = digest.title || `${countryInfo?.name ?? country} Economic Digest`
  const description = extractTeaser(digest.rawContent) || digest.firstHeadline
  const url = `${BASE}${buildDigestUrl(country, date, digest.title)}`
  const publishedTime = `${date}T00:00:00.000Z`

  return {
    title: `${title} | 24EcoNews`,
    description,
    alternates: { canonical: url },
    openGraph: {
      title,
      description,
      url,
      siteName: '24EcoNews',
      images: digest.image_url ? [digest.image_url] : undefined,
      locale: 'en_US',
      type: 'article',
      publishedTime,
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
      images: digest.image_url ? [digest.image_url] : undefined,
    },
  }
}

export default async function DigestPage({
  params,
}: {
  params: Promise<{ country: string; dateSlug: string }>
}) {
  const { country: countrySlug, dateSlug } = await params

  const countryInfo = getCountry(countrySlug)
  if (!countryInfo || !countryInfo.active) notFound()

  const date = extractDate(dateSlug)
  if (!date) notFound()

  const digest = await getDigest(countrySlug, date)
  if (!digest) notFound()

  const publishedDate = `${date}T00:00:00.000Z`
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'NewsArticle',
    headline: digest.title || `${countryInfo.name} Economic Digest`,
    datePublished: publishedDate,
    dateModified: publishedDate,
    author: { '@type': 'Organization', name: '24EcoNews' },
    publisher: { '@type': 'Organization', name: '24EcoNews' },
    ...(digest.image_url ? { image: digest.image_url } : {}),
    description: extractTeaser(digest.rawContent) || digest.firstHeadline,
    mainEntityOfPage: { '@type': 'WebPage', '@id': `${BASE}${buildDigestUrl(countrySlug, date, digest.title)}` },
  }

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }}
      />

      {/* Hero image banner */}
      {digest.image_url && (
        <div
          className="relative w-full overflow-hidden"
          style={{ height: '300px' }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={digest.image_url}
            alt=""
            className="w-full h-full object-cover"
            aria-hidden="true"
          />
          {/* Gradient overlay */}
          <div
            className="absolute inset-0"
            style={{ background: 'linear-gradient(to right, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.2) 60%, rgba(0,0,0,0) 100%)' }}
            aria-hidden="true"
          />
          {/* Photo credit */}
          {digest.image_credit && (
            <a
              href={digest.image_credit_url ?? 'https://unsplash.com'}
              target="_blank"
              rel="noopener noreferrer"
              className="absolute bottom-2 right-3 text-[10px] text-white/60 hover:text-white/90 transition-colors"
            >
              Photo: {digest.image_credit} on Unsplash
            </a>
          )}
        </div>
      )}

      <DigestViewer
        digest={digest}
        country={countrySlug}
        countryName={countryInfo.name}
        countryFlag={countryInfo.flag}
      />
    </>
  )
}
