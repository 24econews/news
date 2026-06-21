import type { Metadata } from 'next'
import { Geist } from 'next/font/google'
import './globals.css'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import CookieConsent from '@/components/CookieConsent'
import ConsentScripts from '@/components/ConsentScripts'

const geist = Geist({ subsets: ['latin'], variable: '--font-geist-sans' })

export const metadata: Metadata = {
  title: '24EcoNews — Global Economic Intelligence',
  description:
    'Daily economic narratives from the world\'s most important emerging markets. Coverage of Argentina, Brazil, and the Mercosur region.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={geist.variable}>
      <body className="min-h-screen flex flex-col bg-white font-sans antialiased">
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
        <CookieConsent />
        <ConsentScripts />
      </body>
    </html>
  )
}
