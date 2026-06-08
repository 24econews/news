import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import { getCountry, getActiveCountries } from '@/lib/countries'
import { getDigest, getCountryDigests } from '@/lib/digests'
import DigestViewer from '@/components/DigestViewer'

export async function generateStaticParams() {
  const params: { country: string; date: string }[] = []
  for (const country of getActiveCountries()) {
    const digests = await getCountryDigests(country.slug)
    for (const digest of digests) {
      params.push({ country: country.slug, date: digest.date })
    }
  }
  return params
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ country: string; date: string }>
}): Promise<Metadata> {
  const { country, date } = await params
  const digest = await getDigest(country, date)
  if (!digest) return {}
  return {
    title: `${digest.title} | 24EcoNews`,
    description: digest.firstHeadline,
    openGraph: digest.image_url ? { images: [digest.image_url] } : undefined,
  }
}

export default async function DigestPage({
  params,
}: {
  params: Promise<{ country: string; date: string }>
}) {
  const { country: countrySlug, date } = await params

  const countryInfo = getCountry(countrySlug)
  if (!countryInfo || !countryInfo.active) notFound()

  const digest = await getDigest(countrySlug, date)
  if (!digest) notFound()

  return (
    <>
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
