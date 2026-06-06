'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

export default function Header() {
  const [lang, setLang] = useState<'ES' | 'EN'>('ES')
  const [menuOpen, setMenuOpen] = useState(false)
  const pathname = usePathname()

  useEffect(() => {
    const stored = localStorage.getItem('preferred-lang')
    if (stored === 'en') setLang('EN')
  }, [])

  const toggleLang = () => {
    const next = lang === 'ES' ? 'EN' : 'ES'
    setLang(next)
    localStorage.setItem('preferred-lang', next.toLowerCase())
  }

  const navLinks = [
    { label: 'Home', href: '/' },
    { label: 'Countries', href: '/#countries' },
    { label: 'Search', href: '/search' },
  ]

  return (
    <header className="bg-slate-900 text-white shadow-lg">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Logo */}
        <Link
          href="/"
          className="text-xl font-bold tracking-tight shrink-0 hover:text-blue-400 transition-colors"
        >
          <span className="text-blue-400">Econo</span>Digest
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-1">
          {navLinks.map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                pathname === href || (href !== '/' && pathname.startsWith(href.replace('/#countries', '')))
                  ? 'text-white bg-slate-800'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            >
              {label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          {/* Language toggle */}
          <button
            onClick={toggleLang}
            aria-label="Toggle language"
            className="flex items-center gap-1 px-3 py-1.5 rounded-full border border-slate-600 text-xs font-semibold tracking-wide hover:border-slate-400 transition-colors"
          >
            <span className={lang === 'ES' ? 'text-white' : 'text-slate-500'}>ES</span>
            <span className="text-slate-600 mx-0.5">|</span>
            <span className={lang === 'EN' ? 'text-white' : 'text-slate-500'}>EN</span>
          </button>

          {/* Mobile menu button */}
          <button
            className="md:hidden p-2 rounded-md text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle menu"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {menuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden bg-slate-800 border-t border-slate-700">
          {navLinks.map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setMenuOpen(false)}
              className="block px-6 py-3 text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
            >
              {label}
            </Link>
          ))}
        </div>
      )}
    </header>
  )
}
