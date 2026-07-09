import Link from 'next/link'
import { countries, getActiveCountries, type Country } from '@/lib/countries'
import { getCountryDigests, getDigest, formatDate, type DigestContent } from '@/lib/digests'
import HeroRotator from '@/components/HeroRotator'
import NewsletterSignup from '@/components/NewsletterSignup'

function extractTeaser(rawContent: string): string {
  const lines = rawContent.replace(/^>\s*TITLE:.*$/m, '').split('\n')
  let collected = ''

  for (const line of lines) {
    const t = line.trim()
    if (!t || t.startsWith('#') || t.startsWith('>') || t.startsWith('*') ||
        t.startsWith('-') || t.startsWith('_') || t.startsWith('|')) {
      if (collected) break
      continue
    }
    collected += (collected ? ' ' : '') + t
    const sents = collected.match(/[^.!?]+[.!?]+/g) ?? []
    if (sents.length >= 2) return sents.slice(0, 2).join(' ')
  }

  return collected.slice(0, 220)
}

export default async function HomePage() {
  const activeCountries = getActiveCountries()

  const latestMetaBySlug = Object.fromEntries(
    await Promise.all(
      activeCountries.map(async (c) => {
        const digests = await getCountryDigests(c.slug)
        return [c.slug, digests[0] ?? null] as const
      })
    )
  )

  const latestContentBySlug = Object.fromEntries(
    await Promise.all(
      activeCountries.map(async (c) => {
        const meta = latestMetaBySlug[c.slug]
        if (!meta) return [c.slug, null] as const
        const content = await getDigest(c.slug, meta.date)
        return [c.slug, content] as const
      })
    )
  )

  const allWithContent: Array<{ country: Country; content: DigestContent; title: string }> = activeCountries
    .flatMap((c) => {
      const content = latestContentBySlug[c.slug]
      if (!content) return []
      // Prefer title from getCountryDigests() (.md source) — confirmed working
      const title = latestMetaBySlug[c.slug]?.title || content.title || ''
      console.log(`[homepage] ${c.slug} title="${title}"`)
      return [{ country: c, content, title }]
    })
    .sort((a, b) => b.content.date.localeCompare(a.content.date))

  return (
    <div className="bg-white">

      {/* ── HERO / LEAD STORY — randomly rotates between countries on each load ── */}
      {allWithContent.length > 0 && <HeroRotator items={allWithContent} />}

      {/* ── NEWSLETTER SIGNUP ── */}
      <section className="bg-slate-50 border-y border-slate-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div>
            <h2 className="text-xl font-bold text-slate-900 mb-1">
              Get the Weekly Mercosur Briefing in your inbox
            </h2>
            <p className="text-slate-500 text-sm">
              One email every Thursday. The region&apos;s biggest economic stories, distilled.
            </p>
          </div>
          <NewsletterSignup />
        </div>
      </section>

      {/* ── TODAY'S BRIEFINGS ── */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
        <h2 className="text-2xl font-bold text-slate-900 mb-8 pl-4 border-l-4 border-red-600">
          Today&apos;s Briefings
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {allWithContent.map(({ country: c, content, title }) => {
            const teaser = extractTeaser(content.rawContent)
            return (
              <div
                key={c.slug}
                className="border border-slate-200 bg-white p-6 hover:shadow-md transition-shadow"
              >
                <span className="text-xs font-bold uppercase tracking-widest text-red-600 mb-3 block">
                  {c.flag}&nbsp; {c.name}
                </span>
                <h3 className="text-xl font-bold text-slate-900 leading-snug mb-2 line-clamp-2">
                  {title || 'Read Today\'s Analysis'}
                </h3>
                <p className="text-xs text-slate-500 mb-4">{formatDate(content.date)}</p>
                {teaser && (
                  <p className="text-slate-600 text-sm leading-relaxed mb-4 line-clamp-3">
                    {teaser}
                  </p>
                )}
                <Link
                  href={`/${c.slug}/${content.date}`}
                  className="text-sm font-semibold text-red-600 hover:text-red-700 transition-colors"
                >
                  Read Analysis →
                </Link>
              </div>
            )
          })}
        </div>
      </section>

      {/* ── COVERAGE MAP ── */}
      <section id="countries" className="border-t border-slate-100 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
          <h2 className="text-2xl font-bold text-slate-900 mb-8">Our Coverage</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {countries.map((country) => {
              const meta = country.active ? (latestMetaBySlug[country.slug] ?? null) : null

              if (!country.active) {
                return (
                  <div
                    key={country.slug}
                    className="bg-white border border-slate-200 p-5 opacity-50 cursor-not-allowed"
                  >
                    <div className="text-3xl mb-2">{country.flag}</div>
                    <p className="font-semibold text-slate-700 text-sm">{country.name}</p>
                    <span className="inline-block mt-2 px-2 py-0.5 bg-slate-100 text-slate-500 text-xs font-medium uppercase tracking-wide">
                      Coming Soon
                    </span>
                  </div>
                )
              }

              return (
                <Link
                  key={country.slug}
                  href={`/${country.slug}`}
                  className="bg-white border border-slate-200 p-5 hover:border-red-300 hover:shadow-sm transition-all group"
                >
                  <div className="text-3xl mb-2">{country.flag}</div>
                  <p className="font-semibold text-slate-900 text-sm group-hover:text-red-600 transition-colors">
                    {country.name}
                  </p>
                  {meta && (
                    <p className="text-xs text-slate-500 mt-1">Latest: {formatDate(meta.date)}</p>
                  )}
                  {meta?.title ? (
                    <p className="text-xs text-slate-600 mt-1 line-clamp-2 leading-snug">
                      {meta.title}
                    </p>
                  ) : null}
                </Link>
              )
            })}
          </div>
        </div>
      </section>

      {/* ── ABOUT STRIP ── */}
      <section className="bg-slate-50 border-t border-slate-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
          <p className="text-slate-600 text-sm leading-relaxed max-w-2xl">
            24EcoNews delivers daily AI-powered economic intelligence on emerging markets.
            Independent. Data-driven. Updated every morning.
          </p>
        </div>
      </section>

    </div>
  )
}
