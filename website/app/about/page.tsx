import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'About | 24EcoNews',
}

export default function AboutPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-12">
      <h1 className="text-3xl font-bold text-slate-900 mb-6">About 24EcoNews</h1>

      <p className="text-slate-600 leading-relaxed mb-8">
        24EcoNews is an independent economic news platform covering the Mercosur region —
        Argentina, Brazil, Chile, Uruguay, Paraguay, and Bolivia.
      </p>

      <p className="text-slate-600 leading-relaxed mb-10">
        The site is run by a small editorial team of working journalists whose careers have taken
        them through Afghanistan, France, Italy, Brazil, Japan, and the United States — experience
        that shapes how we think about covering economies shaped by political risk, currency
        volatility, and institutional change. We built 24EcoNews to fill a gap: there was no single
        place to get a daily, coherent picture of what&apos;s actually happening across these
        economies, drawn directly from the region&apos;s own financial and business press.
      </p>

      <div className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 border-l-4 border-red-600 pl-3 mb-4">
          How it works
        </h2>
        <p className="text-slate-600 leading-relaxed mb-4">
          Every day, our system gathers reporting from leading financial and business outlets in
          each country — outlets like Infobae, La Nación, Valor Econômico, Diario Financiero, and
          others. AI is used to identify the most economically significant stories of the day and
          synthesize them into a single, readable narrative per country, in the style of a
          wire-service briefing. Stories that connect across borders — a trade dispute, a shared
          market reaction, a regional ripple effect — are automatically cross-linked between
          countries.
        </p>
        <p className="text-slate-600 leading-relaxed">
          This is, by design, a mix of AI and editorial judgment: AI handles the heavy lifting of
          monitoring dozens of sources and drafting each day&apos;s narrative, while our editorial
          team sets the sourcing, reviews the output, and steers the coverage.
        </p>
      </div>

      <div className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 border-l-4 border-red-600 pl-3 mb-4">
          What&apos;s next
        </h2>
        <p className="text-slate-600 leading-relaxed">
          We&apos;re actively building out 24EcoNews. Coming soon is an Op-Ed section featuring
          original analysis — both human-written and AI-assisted — going deeper on the stories and
          trends shaping the region.
        </p>
      </div>

      <div className="mb-10">
        <h2 className="text-xl font-bold text-slate-900 border-l-4 border-red-600 pl-3 mb-4">
          Get in touch
        </h2>
        <p className="text-slate-600 leading-relaxed">
          Questions, feedback, or tips? Reach us at{' '}
          <a
            href="mailto:contact-the-team@24econews.com"
            className="text-red-600 hover:text-red-700 transition-colors underline underline-offset-2"
          >
            contact-the-team@24econews.com
          </a>
          .
        </p>
      </div>
    </div>
  )
}
