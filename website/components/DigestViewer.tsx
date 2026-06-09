'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import type { DigestContent } from '@/lib/digests'

interface Props {
  digest: DigestContent
  country: string
  countryName: string
  countryFlag: string
}

interface CrossLink {
  event: string
  summary: string
  links: Array<{ text: string; url: string }>
}

function parseRelatedCoverage(rawContent: string): {
  mainContent: string
  items: CrossLink[]
} {
  const markers = ['\n---\n## Related Coverage', '\n## Related Coverage']
  let sepIdx = -1
  let markerLen = 0

  for (const marker of markers) {
    const idx = rawContent.indexOf(marker)
    if (idx !== -1) {
      sepIdx = idx
      markerLen = marker.length
      break
    }
  }

  if (sepIdx === -1) return { mainContent: rawContent, items: [] }

  const mainContent = rawContent.slice(0, sepIdx)
  const section = rawContent.slice(sepIdx + markerLen).trim()
  const items: CrossLink[] = []

  for (const block of section.split(/\n\n+/)) {
    const lines = block.split('\n').filter(Boolean)
    if (!lines.length) continue
    const eventMatch = lines[0].match(/^\*\*(.+)\*\*$/)
    if (!eventMatch) continue

    const summaryLines: string[] = []
    const links: Array<{ text: string; url: string }> = []

    for (let i = 1; i < lines.length; i++) {
      if (lines[i].startsWith('→ See also:')) {
        const rest = lines[i].slice('→ See also:'.length).trim()
        const dashIdx = rest.lastIndexOf(' — ')
        if (dashIdx !== -1) {
          links.push({ text: rest.slice(0, dashIdx), url: rest.slice(dashIdx + 3) })
        } else {
          links.push({ text: rest, url: '' })
        }
      } else {
        summaryLines.push(lines[i])
      }
    }

    items.push({ event: eventMatch[1], summary: summaryLines.join(' '), links })
  }

  return { mainContent, items }
}

function RelatedCoverage({ items }: { items: CrossLink[] }) {
  if (!items.length) return null

  return (
    <div
      className="mt-8 rounded-xl border border-slate-200 overflow-hidden"
      style={{ borderLeftWidth: '4px', borderLeftColor: '#dc2626' }}
    >
      <div className="bg-slate-50 px-5 py-3 border-b border-slate-200">
        <h2 className="text-xs font-bold uppercase tracking-widest text-slate-500">
          Related Coverage
        </h2>
      </div>
      <div className="divide-y divide-slate-100">
        {items.map((item, i) => (
          <div key={i} className="bg-slate-50 px-5 py-4">
            <p className="font-semibold text-slate-900 text-sm mb-1">{item.event}</p>
            {item.summary && (
              <p className="text-sm text-slate-600 mb-2 leading-relaxed">{item.summary}</p>
            )}
            <div className="space-y-1">
              {item.links.map((link, j) => (
                <div key={j} className="text-sm flex items-start gap-1">
                  <span className="text-slate-400 shrink-0">→</span>
                  {link.url ? (
                    <Link
                      href={link.url}
                      className="text-red-600 hover:text-red-700 font-medium leading-snug"
                    >
                      {link.text}
                    </Link>
                  ) : (
                    <span className="text-slate-600 leading-snug">{link.text}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function NarrativeContent({ rawContent }: { rawContent: string }) {
  const { mainContent, items } = parseRelatedCoverage(rawContent)

  const paragraphs = mainContent
    .split('\n\n')
    .map((p) => p.trim())
    .filter((p) => p && !p.startsWith('#') && !p.startsWith('>') && !/^\*[^*]+\*$/.test(p))

  return (
    <>
      <div className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8">
        <div className="prose prose-slate max-w-none">
          {paragraphs.map((p, i) => (
            <p key={i} className="text-slate-700 leading-relaxed mb-4 last:mb-0">
              {p}
            </p>
          ))}
        </div>
      </div>
      <RelatedCoverage items={items} />
    </>
  )
}

function ShareBar({ title }: { title: string }) {
  const [url, setUrl] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    setUrl(window.location.href)
  }, [])

  const enc = encodeURIComponent
  const tweetText = enc(`${title} via @24econews`)
  const waText = enc(`${title}\n${url}`)

  const copyLink = useCallback(() => {
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [url])

  const btnClass =
    'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 text-slate-700 text-xs font-medium hover:bg-slate-200 transition-colors'

  return (
    <div className="mb-8 pb-8 border-b border-slate-100">
      <p className="text-xs font-medium text-slate-400 mb-2 uppercase tracking-wide">
        Share this digest
      </p>
      <div className="flex flex-wrap gap-2">
        {/* Twitter / X */}
        <a
          href={`https://twitter.com/intent/tweet?text=${tweetText}&url=${enc(url)}`}
          target="_blank"
          rel="noopener noreferrer"
          className={btnClass}
        >
          {/* X logo */}
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.742l7.727-8.823L1.254 2.25H8.08l4.253 5.622 5.911-5.622Zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77Z" />
          </svg>
          X / Twitter
        </a>

        {/* LinkedIn */}
        <a
          href={`https://www.linkedin.com/sharing/share-offsite/?url=${enc(url)}`}
          target="_blank"
          rel="noopener noreferrer"
          className={btnClass}
        >
          {/* LinkedIn "in" logo */}
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
          </svg>
          LinkedIn
        </a>

        {/* WhatsApp */}
        <a
          href={`https://wa.me/?text=${waText}`}
          target="_blank"
          rel="noopener noreferrer"
          className={btnClass}
        >
          {/* WhatsApp logo */}
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413Z" />
          </svg>
          WhatsApp
        </a>

        {/* Copy Link */}
        <button onClick={copyLink} className={btnClass}>
          {copied ? (
            <>
              <svg className="w-3.5 h-3.5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Copied!
            </>
          ) : (
            <>
              {/* Link2 icon */}
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7h3a5 5 0 0 1 5 5 5 5 0 0 1-5 5h-3m-6 0H6a5 5 0 0 1-5-5 5 5 0 0 1 5-5h3" />
                <line x1="8" y1="12" x2="16" y2="12" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
              </svg>
              Copy Link
            </>
          )}
        </button>
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
  return (
    <div>
      {/* Sticky header bar */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-3">
          <Link
            href={`/${country}`}
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            {countryFlag} {countryName}
          </Link>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        {/* Title + meta */}
        <div className="mb-8 pb-8 border-b border-slate-100">
          <span className="text-xs font-bold uppercase tracking-widest text-red-600 mb-3 block">
            {countryFlag}&nbsp; {countryName}
          </span>
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 leading-tight tracking-tight mb-4">
            {digest.title || 'Economic Analysis'}
          </h1>
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-500">
            <span>{digest.date}</span>
            {digest.sources.map((s) => (
              <span key={s} className="px-2 py-0.5 text-xs font-medium bg-slate-100 text-slate-600">
                {s}
              </span>
            ))}
          </div>
        </div>

          {/* Share bar */}
        <ShareBar title={digest.title} />

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
