import Link from 'next/link'

export default function Footer() {
  return (
    <footer className="bg-slate-900 text-slate-400 mt-auto">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-white font-bold text-base hover:text-blue-400 transition-colors">
              24EcoNews
            </Link>
            <span className="text-slate-600">·</span>
            <span>Global Economic Intelligence</span>
          </div>
          <div className="flex items-center gap-6 text-xs">
            <Link href="/" className="hover:text-white transition-colors">Home</Link>
            <Link href="/search" className="hover:text-white transition-colors">Search</Link>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-slate-800 text-xs text-center text-slate-500">
          24EcoNews — Global Economic Intelligence | Updated Daily
        </div>
      </div>
    </footer>
  )
}
