'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import type { DigestContent } from '@/lib/digests'

interface Props {
  esDigest: DigestContent
  enDigest: DigestContent | null
  country: string
  countryName: string
  countryFlag: string
}

const SOURCE_COLORS: Record<string, string> = {
  Infobae: 'bg-red-100 text-red-700',
  Clarín: 'bg-blue-100 text-blue-700',
  'La Nación': 'bg-emerald-100 text-emerald-700',
  'El Cronista': 'bg-amber-100 text-amber-700',
  Ambito: 'bg-purple-100 text-purple-700',
  Reuters: 'bg-orange-100 text-orange-700',
  Bloomberg: 'bg-sky-100 text-sky-700',
}

function sourceBadgeClass(source: string): string {
  return SOURCE_COLORS[source] ?? 'bg-slate-100 text-slate-600'
}

function renderSummary(summary: string) {
  if (!summary) return null
  // Already HTML (contains tags)
  if (summary.includes('<')) {
    return (
      <div
        className="digest-summary text-slate-600 text-sm leading-relaxed"
        dangerouslySetInnerHTML={{ __html: summary }}
      />
    )
  }
  return <p className="text-slate-600 text-sm leading-relaxed">{summary}</p>
}

export default function DigestViewer({
  esDigest,
  enDigest,
  country,
  countryName,
  countryFlag,
}: Props) {
  const [lang, setLang] = useState<'es' | 'en'>('es')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem('preferred-lang')
    if (stored === 'en') setLang('en')
  }, [])

  const switchLang = (next: 'es' | 'en') => {
    setLang(next)
    localStorage.setItem('preferred-lang', next)
  }

  const copyUrl = useCallback(() => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [])

  const digest = lang === 'en' && enDigest ? enDigest : esDigest
  const showEnComingSoon = lang === 'en' && !enDigest

  return (
    <div>
      {/* Digest header bar */}
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

          <div className="flex items-center gap-2">
            {/* Language toggle */}
            <div className="flex items-center rounded-full border border-slate-200 overflow-hidden text-xs font-semibold">
              <button
                onClick={() => switchLang('es')}
                className={`px-3 py-1.5 transition-colors ${
                  lang === 'es' ? 'bg-slate-900 text-white' : 'text-slate-500 hover:bg-slate-50'
                }`}
              >
                ES
              </button>
              <button
                onClick={() => switchLang('en')}
                className={`px-3 py-1.5 transition-colors ${
                  lang === 'en' ? 'bg-slate-900 text-white' : 'text-slate-500 hover:bg-slate-50'
                }`}
              >
                EN
              </button>
            </div>

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
                  Copiado
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                  </svg>
                  Compartir
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Digest content */}
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
            <span className="flex items-center gap-1.5">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
              </svg>
              {digest.articleCount} artículos
            </span>
            {digest.sources.map((s) => (
              <span key={s} className={`px-2 py-0.5 rounded-full text-xs font-medium ${sourceBadgeClass(s)}`}>
                {s}
              </span>
            ))}
          </div>
        </div>

        {/* EN coming soon banner */}
        {showEnComingSoon && (
          <div className="mb-8 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-sm flex items-center gap-2">
            <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            English version coming soon. Showing original Spanish content.
          </div>
        )}

        {/* Articles */}
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
                <span
                  className={`shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${sourceBadgeClass(article.source)}`}
                >
                  {article.source}
                </span>
              </div>

              {renderSummary(article.summary)}

              {article.publishedAt && (
                <p className="mt-3 text-xs text-slate-400">
                  Publicado: {article.publishedAt}
                </p>
              )}
            </article>
          ))}
        </div>
      </div>
    </div>
  )
}
