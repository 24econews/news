import Link from 'next/link'
import CookieSettingsButton from './CookieSettingsButton'

export default function Footer() {
  return (
    <footer className="bg-white border-t border-slate-200 mt-auto">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-red-600 font-bold text-base hover:text-red-700 transition-colors">
              24EcoNews
            </Link>
            <span className="text-slate-300">·</span>
            <span className="text-slate-500">Global Economic Intelligence</span>
          </div>
          <div className="flex items-center gap-6 text-xs text-slate-500">
            <Link href="/" className="hover:text-slate-900 transition-colors">Home</Link>
            <Link href="/search" className="hover:text-slate-900 transition-colors">Search</Link>
            <Link href="/about" className="hover:text-slate-900 transition-colors">About</Link>
            <Link href="/contact" className="hover:text-slate-900 transition-colors">Contact</Link>
            <Link href="/privacy" className="hover:text-slate-900 transition-colors">Privacy Policy</Link>
            <CookieSettingsButton />
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-slate-100 text-xs text-center text-slate-400">
          24EcoNews — Global Economic Intelligence | Updated Daily
        </div>
      </div>
    </footer>
  )
}
