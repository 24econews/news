'use client'

import { useState, useCallback } from 'react'
import Link from 'next/link'
import type { DigestContent } from '@/lib/digests'

interface Props {
  digest: DigestContent
  country: string
  countryName: string
  countryFlag: string
}

function NarrativeContent({ rawContent }: { rawContent: string }) {
  const paragraphs = rawContent
    .split('\n\n')
    .map((p) => p.trim())
    .filter((p) => p && !p.startsWith('#'))

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8">
      <div className="prose prose-slate max-w-none">
        {paragraphs.map((p, i) => (
          <p key={i} className="text-slate-700 leading-relaxed mb-4 last:mb-0">
            {p}
          </p>
        ))}
      </div>
    </div>
  )
}

export default function DigestViewer({
  digest,
  country,
  countryName,
  countryFlag,
}: Props) {
  const [copied, setCopied] = useState(false)

  const copyUrl = useCallback(() => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [])

  return (
    <div>
      {/* Sticky header bar */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4 flex-wrap">
          <Link
            href={`/${country}`}
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            {countryFlag} {countryName}
          </Link>

          {/* Share button */}
          <button
            onClick={copyUrl}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-slate-200 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:border-slate-300 transition-colors"
          >
            {copied ? (
              <>
                <svg className="w-3.5 h-3.5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Copied
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                </svg>
                Share
              </>
            )}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        {/* Title + meta */}
        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 leading-tight mb-3">
            {digest.title}
          </h1>
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-500">
            <span className="flex items-center gap-1.5">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              {digest.date}
            </span>
            {digest.sources.map((s) => (
              <span key={s} className="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
                {s}
              </span>
            ))}
          </div>
        </div>

        {/* Articles or narrative content */}
        {digest.articles.length > 0 ? (
          <div className="space-y-4">
            {digest.articles.map((article, i) => (
              <article
                key={i}
                className="bg-white rounded-xl border border-slate-200 p-5 hover:border-slate-300 hover:shadow-sm transition-all"
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-base font-semibold text-slate-900 hover:text-blue-600 transition-colors leading-snug"
                  >
                    {article.title}
                  </a>
                  <span className="shrink-0 px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
                    {article.source}
                  </span>
                </div>

                {article.summary && (
                  <p className="text-slate-600 text-sm leading-relaxed">{article.summary}</p>
                )}

                {article.publishedAt && (
                  <p className="mt-3 text-xs text-slate-400">
                    Published: {article.publishedAt}
                  </p>
                )}
              </article>
            ))}
          </div>
        ) : (
          <NarrativeContent rawContent={digest.rawContent} />
        )}
      </div>
    </div>
  )
}
