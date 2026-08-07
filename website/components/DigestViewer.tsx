'use client'

import Link from 'next/link'
import type { DigestContent } from '@/lib/digests'
import ShareBar from './ShareBar'

interface Props {
  digest: DigestContent
  country: string
  countryName: string
  countryFlag: string
  canonicalUrl: string
}

interface CrossLink {
  event: string
  summary: string
  links: Array<{ text: string; url: string }>
}

interface RelatedOpinionLink {
  title: string
  url: string
  byline: string
}

function findFirstMarker(rawContent: string, markers: string[]): { idx: number; len: number } | null {
  for (const marker of markers) {
    const idx = rawContent.indexOf(marker)
    if (idx !== -1) return { idx, len: marker.length }
  }
  return null
}

function parseCoverageItems(section: string): CrossLink[] {
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

  return items
}

function parseOpinionSection(section: string): RelatedOpinionLink | null {
  // Written by processing/opinion_linker.py as "[title](url)\nBy Name — Lens".
  const linkMatch = section.match(/^\[([^\]]+)\]\(([^)]+)\)/m)
  if (!linkMatch) return null
  const bylineMatch = section.match(/^By .+$/m)
  return { title: linkMatch[1], url: linkMatch[2], byline: bylineMatch ? bylineMatch[0] : '' }
}

// Splits a digest's raw content into narrative prose plus its two distinct
// "Related" blocks — Related Coverage (cross-country news, from
// processing/cross_linker.py) and Related Opinion (a linked OpEd piece, from
// processing/opinion_linker.py). These must never be visually or
// structurally conflated: one is more news, the other is editorial opinion.
// opinion_linker.py always appends its block after cross_linker.py's, so in
// practice Coverage precedes Opinion when both exist — but this is written
// to handle either order or either section being absent.
function parseDigestSections(rawContent: string): {
  mainContent: string
  coverageItems: CrossLink[]
  opinion: RelatedOpinionLink | null
} {
  const coverageMarker = findFirstMarker(rawContent, ['\n---\n## Related Coverage', '\n## Related Coverage'])
  const opinionMarker = findFirstMarker(rawContent, ['\n---\n## Related Opinion', '\n## Related Opinion'])

  const cutoffs = [coverageMarker?.idx, opinionMarker?.idx].filter((n): n is number => n !== undefined)
  const mainEnd = cutoffs.length ? Math.min(...cutoffs) : rawContent.length
  const mainContent = rawContent.slice(0, mainEnd)

  let coverageItems: CrossLink[] = []
  if (coverageMarker) {
    const sectionEnd = opinionMarker && opinionMarker.idx > coverageMarker.idx ? opinionMarker.idx : rawContent.length
    const section = rawContent.slice(coverageMarker.idx + coverageMarker.len, sectionEnd).trim()
    coverageItems = parseCoverageItems(section)
  }

  let opinion: RelatedOpinionLink | null = null
  if (opinionMarker) {
    const sectionEnd = coverageMarker && coverageMarker.idx > opinionMarker.idx ? coverageMarker.idx : rawContent.length
    const section = rawContent.slice(opinionMarker.idx + opinionMarker.len, sectionEnd).trim()
    opinion = parseOpinionSection(section)
  }

  return { mainContent, coverageItems, opinion }
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

function RelatedOpinion({ opinion }: { opinion: RelatedOpinionLink | null }) {
  if (!opinion) return null

  return (
    <div className="mt-6 rounded-xl border-2 border-slate-900 overflow-hidden">
      <div className="bg-slate-900 px-5 py-3 flex items-center gap-2">
        <span className="inline-flex items-center px-2 py-0.5 border border-white text-white text-[10px] font-bold uppercase tracking-widest">
          Opinion
        </span>
        <h2 className="text-xs font-bold uppercase tracking-widest text-white">
          Related Opinion
        </h2>
      </div>
      <div className="bg-white px-5 py-4">
        <Link
          href={opinion.url}
          className="text-slate-900 font-semibold text-sm leading-snug hover:text-red-700 transition-colors"
        >
          {opinion.title}
        </Link>
        {opinion.byline && <p className="text-xs text-slate-500 mt-1.5">{opinion.byline}</p>}
      </div>
    </div>
  )
}

function NarrativeContent({ rawContent }: { rawContent: string }) {
  const { mainContent, coverageItems, opinion } = parseDigestSections(rawContent)

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
      <RelatedCoverage items={coverageItems} />
      <RelatedOpinion opinion={opinion} />
    </>
  )
}

export default function DigestViewer({
  digest,
  country,
  countryName,
  countryFlag,
  canonicalUrl,
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
        <ShareBar title={digest.title} canonicalUrl={canonicalUrl} label="Share this digest" />

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
