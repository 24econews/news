'use client'

export default function CookieSettingsButton() {
  return (
    <button
      onClick={() => window.dispatchEvent(new Event('show-cookie-settings'))}
      className="hover:text-slate-900 transition-colors"
    >
      Cookie Settings
    </button>
  )
}
