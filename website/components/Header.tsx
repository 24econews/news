'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false)
  const pathname = usePathname()

  const navLinks = [
    { label: 'Home', href: '/' },
    { label: 'Countries', href: '/#countries' },
    { label: 'Search', href: '/search' },
  ]

  function isActive(href: string) {
    if (href === '/') return pathname === '/'
    return pathname.startsWith(href.replace('/#countries', ''))
  }

  return (
    <header className="bg-white border-b border-red-600 shadow-none">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">

        {/* Logo */}
        <Link
          href="/"
          className="text-xl font-bold tracking-tight shrink-0 text-red-600 hover:text-red-700 transition-colors"
        >
          24EcoNews
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-1 flex-1">
          {navLinks.map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
                isActive(href)
                  ? 'text-slate-900 border-red-600'
                  : 'text-slate-700 hover:text-slate-900 border-transparent'
              }`}
            >
              {label}
            </Link>
          ))}
        </nav>

        {/* Updated Daily badge */}
        <span className="hidden md:inline-flex items-center px-2.5 py-1 bg-red-600 text-white text-xs font-bold uppercase tracking-widest shrink-0">
          Updated Daily
        </span>

        {/* Mobile menu button */}
        <button
          className="md:hidden p-2 rounded-md text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
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

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden bg-white border-t border-slate-200">
          {navLinks.map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setMenuOpen(false)}
              className={`block px-6 py-3 text-sm font-medium transition-colors ${
                isActive(href)
                  ? 'text-slate-900 border-l-2 border-red-600 bg-slate-50'
                  : 'text-slate-700 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              {label}
            </Link>
          ))}
        </div>
      )}
    </header>
  )
}
