import Link from 'next/link'
import { getActiveCountries } from '@/lib/countries'
import { searchDigests, formatDate } from '@/lib/digests'

function highlight(text: string, query: string): string {
  if (!query.trim()) return text
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return text.replace(
    new RegExp(`(${escaped})`, 'gi'),
    '<mark class="bg-yellow-200 text-yellow-900 rounded px-0.5">$1</mark>'
  )
}

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; country?: string }>
}) {
  const { q = '', country = '' } = await searchParams
  const activeCountries = getActiveCountries()
  const results = q.trim() ? await searchDigests(q.trim(), country || undefined) : []

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Search</h1>
        <p className="text-slate-500">Search across all available digests</p>
      </div>

      {/* Search form */}
      <form method="GET" action="/search" className="mb-8">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <svg
              className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              type="text"
              name="q"
              defaultValue={q}
              placeholder="Search keywords... (e.g. Milei, Lula, Petrobras)"
              autoFocus
              className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-300 bg-white text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
          </div>

          <select
            name="country"
            defaultValue={country}
            className="px-4 py-3 rounded-xl border border-slate-300 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm min-w-[160px]"
          >
            <option value="">All countries</option>
            {activeCountries.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.flag} {c.name}
              </option>
            ))}
          </select>

          <button
            type="submit"
            className="px-6 py-3 rounded-xl bg-slate-900 text-white text-sm font-semibold hover:bg-slate-700 transition-colors shrink-0"
          >
            Search
          </button>
        </div>
      </form>

      {/* Results */}
      {q.trim() ? (
        results.length > 0 ? (
          <>
            <p className="text-sm text-slate-500 mb-4">
              {results.length} digest{results.length !== 1 ? 's' : ''} found for{' '}
              <strong className="text-slate-900">&ldquo;{q}&rdquo;</strong>
              {country && activeCountries.find((c) => c.slug === country) && (
                <> in {activeCountries.find((c) => c.slug === country)!.flag}{' '}
                  {activeCountries.find((c) => c.slug === country)!.name}
                </>
              )}
            </p>

            <ul className="space-y-4">
              {results.map((result) => {
                const countryInfo = activeCountries.find((c) => c.slug === result.country)
                const snippetHtml = highlight(result.snippet, q)
                const headlineHtml = highlight(result.firstHeadline, q)

                return (
                  <li key={`${result.country}-${result.date}`}>
                    <Link
                      href={`/${result.country}/${result.date}`}
                      className="block bg-white rounded-xl border border-slate-200 p-5 hover:border-blue-300 hover:shadow-sm transition-all group"
                    >
                      <div className="flex items-center justify-between gap-4 flex-wrap mb-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          {countryInfo && (
                            <span className="text-lg">{countryInfo.flag}</span>
                          )}
                          <time
                            dateTime={result.date}
                            className="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors"
                          >
                            {formatDate(result.date)}
                          </time>
                        </div>
                        <span className="text-xs text-slate-400 font-medium">
                          {result.matchCount} match{result.matchCount !== 1 ? 'es' : ''}
                        </span>
                      </div>

                      {result.firstHeadline && (
                        <p
                          className="text-sm font-medium text-slate-700 mb-2 leading-snug"
                          dangerouslySetInnerHTML={{ __html: headlineHtml }}
                        />
                      )}

                      <p
                        className="text-xs text-slate-500 leading-relaxed line-clamp-2"
                        dangerouslySetInnerHTML={{ __html: `...${snippetHtml}...` }}
                      />
                    </Link>
                  </li>
                )
              })}
            </ul>
          </>
        ) : (
          <div className="text-center py-16">
            <div className="text-5xl mb-4">🔍</div>
            <p className="text-slate-600 font-medium mb-1">
              No results for &ldquo;{q}&rdquo;
            </p>
            <p className="text-sm text-slate-400">Try different keywords or broaden your search</p>
          </div>
        )
      ) : (
        <div className="text-center py-16 text-slate-400">
          <div className="text-5xl mb-4">📰</div>
          <p className="text-slate-500">Enter keywords to search across all digests</p>
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            {['Milei', 'Lula', 'BCRA', 'Ibovespa', 'Petrobras', 'default'].map((term) => (
              <Link
                key={term}
                href={`/search?q=${encodeURIComponent(term)}`}
                className="px-3 py-1.5 rounded-full bg-white border border-slate-200 text-sm text-slate-600 hover:border-blue-300 hover:text-blue-600 transition-colors"
              >
                {term}
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
