'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'

export type ConsentState = { analytics: boolean; advertising: boolean }

const STORAGE_KEY = 'cookie-consent'

export function getStoredConsent(): ConsentState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as ConsentState) : null
  } catch {
    return null
  }
}

export function saveConsent(consent: ConsentState) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(consent))
  window.dispatchEvent(new Event('consent-updated'))
}

export default function CookieConsent() {
  const [visible, setVisible] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [analytics, setAnalytics] = useState(false)
  const [advertising, setAdvertising] = useState(false)

  useEffect(() => {
    const existing = getStoredConsent()
    if (!existing) {
      setVisible(true)
    }

    function handleShowSettings() {
      const current = getStoredConsent()
      setAnalytics(current?.analytics ?? false)
      setAdvertising(current?.advertising ?? false)
      setExpanded(true)
      setVisible(true)
    }

    window.addEventListener('show-cookie-settings', handleShowSettings)
    return () => window.removeEventListener('show-cookie-settings', handleShowSettings)
  }, [])

  function acceptAll() {
    saveConsent({ analytics: true, advertising: true })
    setVisible(false)
    setExpanded(false)
  }

  function rejectAll() {
    saveConsent({ analytics: false, advertising: false })
    setVisible(false)
    setExpanded(false)
  }

  function saveCustom() {
    saveConsent({ analytics, advertising })
    setVisible(false)
    setExpanded(false)
  }

  function openSettings() {
    const current = getStoredConsent()
    setAnalytics(current?.analytics ?? false)
    setAdvertising(current?.advertising ?? false)
    setExpanded(true)
  }

  if (!visible) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-slate-200 shadow-[0_-4px_16px_rgba(0,0,0,0.08)]">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4">
        {!expanded ? (
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <p className="text-sm text-slate-600 flex-1">
              We use cookies for analytics and to show relevant ads.{' '}
              <Link href="/privacy" className="text-red-600 hover:text-red-700 underline underline-offset-2 transition-colors">
                See our Privacy Policy
              </Link>{' '}
              for details.
            </p>
            <div className="flex items-center gap-2 shrink-0 flex-wrap">
              <button
                onClick={openSettings}
                className="px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-300 hover:border-slate-400 hover:text-slate-900 transition-colors rounded-sm"
              >
                Cookie Settings
              </button>
              <button
                onClick={rejectAll}
                className="px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-300 hover:border-slate-400 hover:text-slate-900 transition-colors rounded-sm"
              >
                Reject Non-Essential
              </button>
              <button
                onClick={acceptAll}
                className="px-3 py-1.5 text-xs font-medium bg-red-600 text-white hover:bg-red-700 transition-colors rounded-sm"
              >
                Accept All
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-slate-600">
              Manage your cookie preferences. Essential cookies are always active.
            </p>
            <div className="space-y-3">
              <label className="flex items-center justify-between gap-4 cursor-not-allowed">
                <div>
                  <span className="text-sm font-medium text-slate-700">Essential</span>
                  <p className="text-xs text-slate-500 mt-0.5">Required for the site to function. Always on.</p>
                </div>
                <div className="w-10 h-5 bg-slate-300 rounded-full relative shrink-0">
                  <div className="absolute right-0.5 top-0.5 w-4 h-4 bg-white rounded-full shadow" />
                </div>
              </label>

              <label className="flex items-center justify-between gap-4 cursor-pointer">
                <div>
                  <span className="text-sm font-medium text-slate-700">Analytics</span>
                  <p className="text-xs text-slate-500 mt-0.5">Helps us understand how visitors use the site (Google Analytics).</p>
                </div>
                <button
                  role="switch"
                  aria-checked={analytics}
                  onClick={() => setAnalytics(v => !v)}
                  className={`w-10 h-5 rounded-full relative transition-colors shrink-0 ${analytics ? 'bg-red-600' : 'bg-slate-300'}`}
                >
                  <span
                    className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${analytics ? 'translate-x-5' : 'translate-x-0.5'}`}
                  />
                </button>
              </label>

              <label className="flex items-center justify-between gap-4 cursor-pointer">
                <div>
                  <span className="text-sm font-medium text-slate-700">Advertising</span>
                  <p className="text-xs text-slate-500 mt-0.5">Used to show relevant ads (Google AdSense).</p>
                </div>
                <button
                  role="switch"
                  aria-checked={advertising}
                  onClick={() => setAdvertising(v => !v)}
                  className={`w-10 h-5 rounded-full relative transition-colors shrink-0 ${advertising ? 'bg-red-600' : 'bg-slate-300'}`}
                >
                  <span
                    className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${advertising ? 'translate-x-5' : 'translate-x-0.5'}`}
                  />
                </button>
              </label>
            </div>

            <div className="flex items-center gap-2 justify-end flex-wrap">
              <button
                onClick={rejectAll}
                className="px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-300 hover:border-slate-400 hover:text-slate-900 transition-colors rounded-sm"
              >
                Reject All
              </button>
              <button
                onClick={acceptAll}
                className="px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-300 hover:border-slate-400 hover:text-slate-900 transition-colors rounded-sm"
              >
                Accept All
              </button>
              <button
                onClick={saveCustom}
                className="px-3 py-1.5 text-xs font-medium bg-red-600 text-white hover:bg-red-700 transition-colors rounded-sm"
              >
                Save Preferences
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
