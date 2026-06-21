'use client'

import { useState, useEffect } from 'react'
import Script from 'next/script'
import { getStoredConsent, type ConsentState } from './CookieConsent'

export default function ConsentScripts() {
  const [consent, setConsent] = useState<ConsentState | null>(null)

  useEffect(() => {
    setConsent(getStoredConsent())
    function sync() { setConsent(getStoredConsent()) }
    window.addEventListener('consent-updated', sync)
    return () => window.removeEventListener('consent-updated', sync)
  }, [])

  if (!consent) return null

  return (
    <>
      {consent.advertising && (
        <Script
          async
          src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7161273140151755"
          crossOrigin="anonymous"
          strategy="afterInteractive"
        />
      )}
    </>
  )
}
