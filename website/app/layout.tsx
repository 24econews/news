import type { Metadata } from 'next'
import { Geist } from 'next/font/google'
import './globals.css'
import Header from '@/components/Header'
import Footer from '@/components/Footer'

const geist = Geist({ subsets: ['latin'], variable: '--font-geist-sans' })

export const metadata: Metadata = {
  title: 'EconoDigest — Global Economic Intelligence',
  description:
    'Daily economic digests from leading media sources around the world. Coverage of Argentina, Brazil, Mexico, and more.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={geist.variable}>
      <body className="min-h-screen flex flex-col bg-slate-50 font-sans antialiased">
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  )
}
