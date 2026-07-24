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
      {consent.analytics && (
        <>
          <Script
            src="https://www.googletagmanager.com/gtag/js?id=G-JGHRWTD99E"
            strategy="afterInteractive"
          />
          <Script id="ga-init" strategy="afterInteractive">{`
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', 'G-JGHRWTD99E');
          `}</Script>
        </>
      )}
    </>
  )
}
