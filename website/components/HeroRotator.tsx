'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import type { Country } from '@/lib/countries'
import type { DigestContent } from '@/lib/digests'
import { formatDate } from '@/lib/digests'

export interface HeroItem {
  country: Country
  content: DigestContent
  title: string
}

export default function HeroRotator({ items }: { items: HeroItem[] }) {
  const [idx, setIdx] = useState(0)
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    if (items.length <= 1) return
    const random = Math.floor(Math.random() * items.length)
    if (random === idx) return
    setVisible(false)
    const t = setTimeout(() => {
      setIdx(random)
      setVisible(true)
    }, 120)
    return () => clearTimeout(t)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // run once on mount

  const item = items[idx]
  if (!item) return null

  const { image_url, image_credit, image_credit_url } = item.content

  if (image_url) {
    return (
      <section
        className="relative overflow-hidden"
        style={{
          backgroundImage: `url(${image_url})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          opacity: visible ? 1 : 0,
          transition: 'opacity 120ms ease-in-out',
        }}
      >
        {/* Dark gradient overlay: left dark → right transparent */}
        <div
          className="absolute inset-0"
          style={{ background: 'linear-gradient(to right, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.4) 55%, rgba(0,0,0,0.1) 100%)' }}
          aria-hidden="true"
        />

        <div className="relative max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
          <div className="max-w-xl">
            <span className="text-xs font-bold uppercase tracking-widest text-red-400 mb-4 block">
              {item.country.flag}&nbsp; {item.country.name}
            </span>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight leading-tight text-white mb-4">
              {item.title || "Read Today's Analysis"}
            </h1>
            <p className="text-slate-300 text-sm mb-8">
              {formatDate(item.content.date)}
            </p>
            <Link
              href={`/${item.country.slug}/${item.content.date}`}
              className="inline-block bg-red-600 hover:bg-red-700 text-white text-sm font-semibold px-6 py-3 transition-colors"
            >
              Read Today&apos;s Digest →
            </Link>
          </div>
        </div>

        {/* Photo credit bottom-right */}
        {image_credit && (
          <a
            href={image_credit_url ?? 'https://unsplash.com'}
            target="_blank"
            rel="noopener noreferrer"
            className="absolute bottom-2 right-3 text-[10px] text-white/60 hover:text-white/90 transition-colors"
          >
            Photo: {image_credit} on Unsplash
          </a>
        )}
      </section>
    )
  }

  // Fallback: flag emoji design
  return (
    <section className="bg-white border-b border-slate-200">
      <div
        className="max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-20"
        style={{
          opacity: visible ? 1 : 0,
          transition: 'opacity 120ms ease-in-out',
        }}
      >
        <div className="flex items-center gap-8 md:gap-16">
          {/* Left: text */}
          <div className="flex-1 min-w-0">
            <span className="text-xs font-bold uppercase tracking-widest text-red-600 mb-4 block">
              {item.country.flag}&nbsp; {item.country.name}
            </span>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight leading-tight text-slate-900 mb-4">
              {item.title || "Read Today's Analysis"}
            </h1>
            <p className="text-slate-500 text-sm mb-8">
              {formatDate(item.content.date)}
            </p>
            <Link
              href={`/${item.country.slug}/${item.content.date}`}
              className="inline-block bg-red-600 hover:bg-red-700 text-white text-sm font-semibold px-6 py-3 transition-colors"
            >
              Read Today&apos;s Digest →
            </Link>
          </div>
          {/* Right: large flag */}
          <div
            className="hidden sm:block shrink-0 leading-none select-none"
            style={{ fontSize: '10rem' }}
            aria-hidden="true"
          >
            {item.country.flag}
          </div>
        </div>
      </div>
    </section>
  )
}
