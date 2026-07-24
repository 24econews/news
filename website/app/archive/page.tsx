import Link from 'next/link'
import type { Metadata } from 'next'
import { getCountry } from '@/lib/countries'
import { getAllDigests, formatDate, type DigestMeta } from '@/lib/digests'

const PAGE_SIZE = 50

export const metadata: Metadata = {
  title: 'Archive | 24EcoNews',
  description: 'Every daily economic digest published by 24EcoNews, across all countries.',
}

export default async function ArchivePage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>
}) {
  const { page = '1' } = await searchParams

  const allDigests = await getAllDigests()
  const pageNum = Math.max(1, parseInt(page) || 1)
  const totalPages = Math.max(1, Math.ceil(allDigests.length / PAGE_SIZE))
  const pageDigests = allDigests.slice((pageNum - 1) * PAGE_SIZE, pageNum * PAGE_SIZE)

  const grouped: Array<[string, DigestMeta[]]> = []
  for (const digest of pageDigests) {
    const last = grouped[grouped.length - 1]
    if (last && last[0] === digest.date) {
      last[1].push(digest)
    } else {
      grouped.push([digest.date, [digest]])
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900 transition-colors mb-6"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Home
      </Link>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-1">Archive</h1>
        <p className="text-slate-500">Every digest published, across all countries</p>
      </div>

      {allDigests.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <div className="text-5xl mb-4">📭</div>
          <p>No digests available yet.</p>
        </div>
      ) : (
        <>
          <div className="space-y-8">
            {grouped.map(([date, entries]) => (
              <div key={date}>
                <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-3">
                  {formatDate(date)}
                </h2>
                <ul className="space-y-2">
                  {entries.map((entry) => {
                    const countryInfo = getCountry(entry.country)
                    return (
                      <li key={`${entry.country}-${date}`}>
                        <Link
                          href={`/${entry.country}/${date}`}
                          className="flex items-center gap-3 bg-white rounded-xl border border-slate-200 p-4 hover:border-blue-300 hover:shadow-sm transition-all group"
                        >
                          <span className="text-xl shrink-0">{countryInfo?.flag}</span>
                          <span className="text-sm text-slate-900 font-semibold group-hover:text-blue-600 transition-colors line-clamp-1">
                            {entry.title || `${countryInfo?.name ?? entry.country} Economic Digest`}
                          </span>
                        </Link>
                      </li>
                    )
                  })}
                </ul>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <nav className="flex items-center justify-center gap-2 mt-8">
              {pageNum > 1 && (
                <Link
                  href={`/archive?page=${pageNum - 1}`}
                  className="px-3 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-200 transition-colors"
                >
                  ← Previous
                </Link>
              )}
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <Link
                  key={p}
                  href={`/archive?page=${p}`}
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
                  href={`/archive?page=${pageNum + 1}`}
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
