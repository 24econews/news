import Link from 'next/link'
import type { Metadata } from 'next'
import { getAllOpeds, extractOpedExcerpt } from '@/lib/oped'
import { formatDate } from '@/lib/digests'
import { buildOpinionUrl } from '@/lib/slugify'

const PAGE_SIZE = 20

const BASE = 'https://www.24econews.com'
const PAGE_TITLE = 'Opinion | 24EcoNews'
const PAGE_DESCRIPTION =
  '24EcoNews Opinion features eight recurring columnists offering distinct editorial perspectives on Mercosur affairs.'

export const metadata: Metadata = {
  title: PAGE_TITLE,
  description: PAGE_DESCRIPTION,
  alternates: { canonical: `${BASE}/opinion` },
  openGraph: {
    title: PAGE_TITLE,
    description: PAGE_DESCRIPTION,
    url: `${BASE}/opinion`,
    siteName: '24EcoNews',
    locale: 'en_US',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: PAGE_TITLE,
    description: PAGE_DESCRIPTION,
  },
}

export default async function OpinionPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>
}) {
  const { page = '1' } = await searchParams

  const allOpeds = await getAllOpeds()
  const pageNum = Math.max(1, parseInt(page) || 1)
  const totalPages = Math.max(1, Math.ceil(allOpeds.length / PAGE_SIZE))
  const pageOpeds = allOpeds.slice((pageNum - 1) * PAGE_SIZE, pageNum * PAGE_SIZE)

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
        <span className="inline-flex items-center px-2.5 py-1 border-2 border-slate-900 text-slate-900 text-xs font-bold uppercase tracking-widest mb-3">
          Opinion
        </span>
        <h1 className="text-3xl font-bold text-slate-900 mb-2 font-serif italic">
          24EcoNews Opinion
        </h1>
        <p className="text-slate-500 max-w-2xl leading-relaxed">
          24EcoNews Opinion features eight recurring columnists offering distinct editorial
          perspectives on Mercosur affairs. These pieces represent the views of their authors,
          not 24EcoNews&apos;s news reporting.
        </p>
      </div>

      {allOpeds.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <div className="text-5xl mb-4">🖋️</div>
          <p>No Opinion pieces published yet.</p>
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {pageOpeds.map((oped) => {
              const excerpt = extractOpedExcerpt(oped.paragraphs)
              return (
                <Link
                  key={`${oped.slug}-${oped.date}`}
                  href={buildOpinionUrl(oped.slug, oped.date, oped.title)}
                  className="block bg-white rounded-xl border border-slate-200 p-5 sm:p-6 hover:border-slate-400 hover:shadow-sm transition-all group"
                >
                  <div className="flex flex-wrap items-center gap-2 mb-3">
                    <span className="inline-flex items-center px-2 py-0.5 border border-slate-900 text-slate-900 text-[10px] font-bold uppercase tracking-widest">
                      Opinion
                    </span>
                    <span className="text-xs font-semibold text-slate-700">{oped.personaName}</span>
                    <span className="text-slate-300">·</span>
                    <span className="text-xs text-slate-500">{oped.lensShort}</span>
                  </div>
                  <h2 className="text-xl font-bold text-slate-900 leading-snug mb-2 font-serif group-hover:text-red-700 transition-colors">
                    {oped.title}
                  </h2>
                  {excerpt && (
                    <p className="text-slate-600 text-sm leading-relaxed mb-3 line-clamp-2">
                      {excerpt}
                    </p>
                  )}
                  <p className="text-xs text-slate-400">{formatDate(oped.date)}</p>
                </Link>
              )
            })}
          </div>

          {totalPages > 1 && (
            <nav className="flex items-center justify-center gap-2 mt-8">
              {pageNum > 1 && (
                <Link
                  href={`/opinion?page=${pageNum - 1}`}
                  className="px-3 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-200 transition-colors"
                >
                  ← Previous
                </Link>
              )}
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <Link
                  key={p}
                  href={`/opinion?page=${p}`}
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
                  href={`/opinion?page=${pageNum + 1}`}
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
