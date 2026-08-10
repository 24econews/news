import Link from 'next/link'
import type { Metadata } from 'next'
import { countries, getActiveCountries, type Country } from '@/lib/countries'
import { getCountryDigests, getDigest, formatDate, extractTeaser, type DigestContent } from '@/lib/digests'
import { getAllOpeds, extractOpedExcerpt } from '@/lib/oped'
import { buildDigestUrl, buildOpinionUrl } from '@/lib/slugify'
import HeroRotator from '@/components/HeroRotator'
import NewsletterSignup from '@/components/NewsletterSignup'

const BASE = 'https://www.24econews.com'

const SITE_TITLE = '24EcoNews — Global Economic Intelligence'
const SITE_DESCRIPTION =
  'Daily economic narratives from the world\'s most important emerging markets. Coverage of Argentina, Brazil, and the Mercosur region.'

export const metadata: Metadata = {
  title: SITE_TITLE,
  description: SITE_DESCRIPTION,
  alternates: { canonical: BASE },
  openGraph: {
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    url: BASE,
    siteName: '24EcoNews',
    locale: 'en_US',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
  },
}

export default async function HomePage() {
  const activeCountries = getActiveCountries()

  const [latestMetaEntries, allOpeds] = await Promise.all([
    Promise.all(
      activeCountries.map(async (c) => {
        const digests = await getCountryDigests(c.slug)
        return [c.slug, digests[0] ?? null] as const
      })
    ),
    getAllOpeds(),
  ])
  const latestMetaBySlug = Object.fromEntries(latestMetaEntries)
  const latestOpeds = allOpeds.slice(0, 3)

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
              One email every Friday. The region&apos;s biggest economic stories, distilled.
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
                  href={buildDigestUrl(c.slug, content.date, title)}
                  className="text-sm font-semibold text-red-600 hover:text-red-700 transition-colors"
                >
                  Read Analysis →
                </Link>
              </div>
            )
          })}
        </div>
      </section>

      {/* ── LATEST OPINION ── */}
      {latestOpeds.length > 0 && (
        <section className="border-t border-slate-100 bg-white">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
            <div className="flex items-center gap-3 mb-8">
              <span className="inline-flex items-center px-2.5 py-1 border-2 border-slate-900 text-slate-900 text-xs font-bold uppercase tracking-widest">
                Opinion
              </span>
              <h2 className="text-2xl font-bold text-slate-900 font-serif italic">Latest Opinion</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {latestOpeds.map((oped) => {
                const excerpt = extractOpedExcerpt(oped.paragraphs)
                return (
                  <Link
                    key={`${oped.slug}-${oped.date}`}
                    href={buildOpinionUrl(oped.slug, oped.date, oped.title)}
                    className="block border border-slate-200 bg-white p-6 hover:border-slate-400 hover:shadow-sm transition-all group"
                  >
                    <div className="flex flex-wrap items-center gap-2 mb-3">
                      <span className="inline-flex items-center px-2 py-0.5 border border-slate-900 text-slate-900 text-[10px] font-bold uppercase tracking-widest">
                        Opinion
                      </span>
                      <span className="text-xs font-semibold text-slate-700">{oped.personaName}</span>
                    </div>
                    <h3 className="text-lg font-bold text-slate-900 leading-snug mb-2 font-serif group-hover:text-red-700 transition-colors line-clamp-2">
                      {oped.title}
                    </h3>
                    {excerpt && (
                      <p className="text-slate-600 text-sm leading-relaxed mb-3 line-clamp-2">{excerpt}</p>
                    )}
                    <p className="text-xs text-slate-400">{formatDate(oped.date)}</p>
                  </Link>
                )
              })}
            </div>
            <div className="mt-6">
              <Link href="/opinion" className="text-sm font-semibold text-red-600 hover:text-red-700 transition-colors">
                More Opinion →
              </Link>
            </div>
          </div>
        </section>
      )}

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
