import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Contact | 24EcoNews',
}

export default function ContactPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-12">
      <h1 className="text-3xl font-bold text-slate-900 border-l-4 border-red-600 pl-3 mb-8">
        Contact
      </h1>
      <p className="text-slate-600 leading-relaxed mb-4">
        Have a question, a tip, or feedback on our coverage? We&apos;d love to hear from you.
      </p>
      <p className="text-slate-600 leading-relaxed mb-4">
        Reach us at{' '}
        <a
          href="mailto:contact-the-team@24econews.com"
          className="text-red-600 hover:text-red-700 transition-colors underline underline-offset-2"
        >
          contact-the-team@24econews.com
        </a>
        .
      </p>
      <p className="text-slate-600 leading-relaxed">
        We try to respond within a few business days.
      </p>
    </div>
  )
}
