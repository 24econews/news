import Link from 'next/link'
import { countries, getActiveCountries } from '@/lib/countries'
import { getCountryDigests, formatDate } from '@/lib/digests'

export default async function HomePage() {
  const activeCountries = getActiveCountries()

  const latestBySlug = Object.fromEntries(
    await Promise.all(
      activeCountries.map(async (c) => {
        const digests = await getCountryDigests(c.slug)
        return [c.slug, digests[0] ?? null] as const
      })
    )
  )

  return (
    <div>
      {/* Hero */}
      <section className="bg-slate-900 text-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-500/20 text-blue-300 text-xs font-semibold tracking-wide mb-6">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
              Updated Daily
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-tight mb-4">
              Global Economic
              <br />
              <span className="text-blue-400">Intelligence</span>
            </h1>
            <p className="text-lg text-slate-300 leading-relaxed mb-8">
              Daily economic narratives from the world&apos;s most important emerging markets.
            </p>
            <div className="flex flex-wrap gap-3">
              {activeCountries.map((c) => (
                <Link
                  key={c.slug}
                  href={`/${c.slug}`}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white text-slate-900 text-sm font-semibold hover:bg-blue-50 transition-colors"
                >
                  <span>{c.flag}</span>
                  {c.name}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Coverage cards */}
      <section id="countries" className="max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-16">
        <h2 className="text-2xl font-bold text-slate-900 mb-8">Coverage</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {countries.map((country) => {
            const latest = country.active ? (latestBySlug[country.slug] ?? null) : null

            if (!country.active) {
              return (
                <div
                  key={country.slug}
                  className="bg-white rounded-2xl border border-slate-200 p-6 opacity-50 cursor-not-allowed"
                >
                  <div className="text-4xl mb-3">{country.flag}</div>
                  <h3 className="font-semibold text-slate-900 mb-1">{country.name}</h3>
                  <span className="inline-block mt-2 px-2.5 py-1 rounded-full bg-slate-100 text-slate-500 text-xs font-medium">
                    Coming Soon
                  </span>
                </div>
              )
            }

            return (
              <Link
                key={country.slug}
                href={`/${country.slug}`}
                className="bg-white rounded-2xl border border-slate-200 p-6 hover:border-blue-300 hover:shadow-md transition-all group"
              >
                <div className="text-4xl mb-3">{country.flag}</div>
                <h3 className="font-semibold text-slate-900 mb-1 group-hover:text-blue-600 transition-colors">
                  {country.name}
                </h3>
                {latest ? (
                  <>
                    <p className="text-xs text-slate-500 mb-4">
                      Latest: {formatDate(latest.date)}
                    </p>
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 group-hover:gap-2.5 transition-all">
                      Read Today&apos;s Digest
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </span>
                  </>
                ) : (
                  <p className="text-xs text-slate-400">No digests yet</p>
                )}
              </Link>
            )
          })}
        </div>
      </section>

      {/* About strip */}
      <section className="bg-slate-900 text-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
            {[
              { icon: '📰', label: 'Trusted Sources', desc: 'Curated from leading economic media outlets' },
              { icon: '🌎', label: 'Emerging Markets', desc: 'Deep coverage of Latin American economies' },
              { icon: '🔄', label: 'Updated Daily', desc: 'Fresh digests published every morning' },
            ].map(({ icon, label, desc }) => (
              <div key={label} className="flex flex-col items-center gap-2">
                <span className="text-3xl">{icon}</span>
                <h4 className="font-semibold text-white">{label}</h4>
                <p className="text-sm text-slate-400">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
