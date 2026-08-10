import Link from 'next/link'
import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import { getCountry, getActiveCountries } from '@/lib/countries'
import { getCountryDigests, formatDate } from '@/lib/digests'
import { buildDigestUrl } from '@/lib/slugify'

const PAGE_SIZE = 10
const BASE = 'https://www.24econews.com'

export async function generateStaticParams() {
  return getActiveCountries().map((c) => ({ country: c.slug }))
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ country: string }>
}): Promise<Metadata> {
  const { country: countrySlug } = await params
  const countryInfo = getCountry(countrySlug)
  if (!countryInfo || !countryInfo.active) return {}

  const title = `${countryInfo.name} Economic Digest | 24EcoNews`
  const description = `Daily economic digest coverage of ${countryInfo.name}: inflation, currency, trade, and policy news, drawn from ${countryInfo.sources.join(', ')}.`

  return {
    title,
    description,
    alternates: { canonical: `${BASE}/${countrySlug}` },
  }
}

export default async function CountryPage({
  params,
  searchParams,
}: {
  params: Promise<{ country: string }>
  searchParams: Promise<{ page?: string }>
}) {
  const { country: countrySlug } = await params
  const { page = '1' } = await searchParams

  const countryInfo = getCountry(countrySlug)
  if (!countryInfo || !countryInfo.active) notFound()

  const allDigests = await getCountryDigests(countrySlug)
  const pageNum = Math.max(1, parseInt(page) || 1)
  const totalPages = Math.max(1, Math.ceil(allDigests.length / PAGE_SIZE))
  const digests = allDigests.slice((pageNum - 1) * PAGE_SIZE, pageNum * PAGE_SIZE)

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      {/* Back link */}
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900 transition-colors mb-6"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        All Countries
      </Link>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-1">
          {countryInfo.flag} {countryInfo.name}
        </h1>
        <p className="text-slate-500">Daily Economic Digest</p>
      </div>

      {allDigests.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <div className="text-5xl mb-4">📭</div>
          <p>No digests available yet.</p>
        </div>
      ) : (
        <>
          <ul className="space-y-3">
            {digests.map((digest) => (
              <li key={digest.date}>
                <Link
                  href={buildDigestUrl(countrySlug, digest.date, digest.title)}
                  className="flex items-center justify-between gap-4 bg-white rounded-xl border border-slate-200 p-5 hover:border-blue-300 hover:shadow-sm transition-all group"
                >
                  <div className="min-w-0">
                    <p className="text-sm text-slate-900 leading-snug">
                      <time dateTime={digest.date} className="font-medium text-slate-500 shrink-0">
                        {formatDate(digest.date)}:
                      </time>{' '}
                      <span className="font-semibold group-hover:text-blue-600 transition-colors">
                        {digest.title || 'Read Today\'s Analysis'}
                      </span>
                    </p>
                  </div>
                  <svg
                    className="w-4 h-4 shrink-0 text-slate-400 group-hover:text-blue-500 group-hover:translate-x-0.5 transition-all"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              </li>
            ))}
          </ul>

          {/* Pagination */}
          {totalPages > 1 && (
            <nav className="flex items-center justify-center gap-2 mt-8">
              {pageNum > 1 && (
                <Link
                  href={`/${countrySlug}?page=${pageNum - 1}`}
                  className="px-3 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-200 transition-colors"
                >
                  ← Previous
                </Link>
              )}
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <Link
                  key={p}
                  href={`/${countrySlug}?page=${p}`}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    p === pageNum
                      ? 'bg-slate-900 text-white'
                      : 'text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {p}
                </Link>
              ))}
              {pageNum < totalPages && (
                <Link
                  href={`/${countrySlug}?page=${pageNum + 1}`}
                  className="px-3 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-200 transition-colors"
                >
                  Next →
                </Link>
              )}
            </nav>
          )}
        </>
      )}
    </div>
  )
}
