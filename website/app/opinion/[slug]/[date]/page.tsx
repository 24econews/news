import Link from 'next/link'
import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import { getAllOpeds, getOpedBySlugAndDate, extractOpedExcerpt } from '@/lib/oped'
import { formatDate } from '@/lib/digests'

const BASE = 'https://24econews.com'

export async function generateStaticParams() {
  const opeds = await getAllOpeds()
  return opeds.map((o) => ({ slug: o.slug, date: o.date }))
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string; date: string }>
}): Promise<Metadata> {
  const { slug, date } = await params
  const oped = await getOpedBySlugAndDate(slug, date)
  if (!oped) return {}
  return {
    title: `${oped.title} | 24EcoNews Opinion`,
    description: extractOpedExcerpt(oped.paragraphs),
  }
}

export default async function OpedPage({
  params,
}: {
  params: Promise<{ slug: string; date: string }>
}) {
  const { slug, date } = await params

  // Returns null both when the file is missing and when its date is still
  // in the future (see isPublished() in lib/oped.ts) — either way, 404.
  const oped = await getOpedBySlugAndDate(slug, date)
  if (!oped) notFound()

  const publishedDate = `${oped.date}T00:00:00.000Z`
  const description = extractOpedExcerpt(oped.paragraphs)

  // OpinionNewsArticle, not NewsArticle — this content is editorial commentary
  // attributed to a named columnist, not 24EcoNews's neutral news reporting.
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'OpinionNewsArticle',
    headline: oped.title,
    datePublished: publishedDate,
    dateModified: publishedDate,
    author: { '@type': 'Person', name: oped.personaName },
    publisher: { '@type': 'Organization', name: '24EcoNews' },
    description,
    mainEntityOfPage: { '@type': 'WebPage', '@id': `${BASE}/opinion/${oped.slug}/${oped.date}` },
  }

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }}
      />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <Link
          href="/opinion"
          className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900 transition-colors mb-6"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Opinion
        </Link>

        <div className="mb-8 pb-8 border-b border-slate-100">
          <span className="inline-flex items-center px-2.5 py-1 border-2 border-slate-900 text-slate-900 text-xs font-bold uppercase tracking-widest mb-4">
            Opinion
          </span>
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 leading-tight tracking-tight mb-4 font-serif">
            {oped.title}
          </h1>
          <p className="text-sm text-slate-600 mb-1">
            By <span className="font-semibold text-slate-900">{oped.personaName}</span>
            <span className="text-slate-400"> · </span>
            <span>{oped.lensShort}</span>
          </p>
          <p className="text-xs text-slate-400">{formatDate(oped.date)}</p>
        </div>

        <div className="prose prose-slate max-w-none">
          {oped.paragraphs.map((p, i) => (
            <p key={i} className="text-slate-800 leading-relaxed mb-4 last:mb-0 font-serif">
              {p}
            </p>
          ))}
        </div>

        {oped.bioDisclosure && (
          <p className="mt-8 pt-6 border-t border-slate-100 text-xs italic text-slate-500 leading-relaxed">
            {oped.bioDisclosure}
          </p>
        )}
      </div>
    </>
  )
}
