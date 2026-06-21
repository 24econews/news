import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Privacy Policy | 24EcoNews',
}

function Section({ num, title, children }: { num: number; title: string; children: React.ReactNode }) {
  return (
    <div className="mb-10">
      <h2 className="text-xl font-bold text-slate-900 border-l-4 border-red-600 pl-3 mb-4">
        {num}. {title}
      </h2>
      <div className="text-slate-600 leading-relaxed space-y-3">{children}</div>
    </div>
  )
}

export default function PrivacyPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-12">
      <h1 className="text-3xl font-bold text-slate-900 mb-2">Privacy Policy</h1>
      <p className="text-sm text-slate-400 mb-10">Last updated: June 21, 2026</p>

      <Section num={1} title="Introduction">
        <p>
          Your privacy is important to us. This Privacy Policy explains how 24EcoNews
          (&ldquo;24EcoNews&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;, or &ldquo;our&rdquo;)
          collects, uses, discloses, and protects your personal data when you visit our website.
          It also describes your rights and how you can exercise them.
        </p>
        <p>
          This policy applies to personal data processed through our website. By using our site,
          you acknowledge the practices described here. We encourage you to read it carefully.
        </p>
      </Section>

      <Section num={2} title="Data Controller">
        <p>
          24EcoNews is operated by 24EcoNews. We are the data controller for the personal data
          described in this Privacy Policy under applicable data protection laws (including the
          GDPR where relevant).
        </p>
        <p>
          Contact Information:{' '}
          <a
            href="mailto:contact-the-team@24econews.com"
            className="text-red-600 hover:text-red-700 transition-colors underline underline-offset-2"
          >
            contact-the-team@24econews.com
          </a>
        </p>
      </Section>

      <Section num={3} title="Data We Collect">
        <ul className="list-disc list-outside ml-5 space-y-2">
          <li>
            <strong className="text-slate-700">Technical and Usage Data:</strong> IP address,
            browser type, device information, operating system, pages visited, time spent on
            pages, referral sources, and timestamps. Collected automatically through server logs
            and analytics tools.
          </li>
          <li>
            <strong className="text-slate-700">Analytics Data:</strong> Aggregated insights on
            user interactions via Google Analytics 4.
          </li>
          <li>
            <strong className="text-slate-700">Advertising Data:</strong> Data used for serving
            and personalizing ads, including cookies and identifiers from Google AdSense and its
            partners.
          </li>
          <li>
            <strong className="text-slate-700">Contact Data:</strong> Name, email address, and
            message content if you email us.
          </li>
          <li>
            <strong className="text-slate-700">Other:</strong> Any additional information you
            voluntarily provide.
          </li>
        </ul>
        <p>We do not knowingly collect sensitive personal data.</p>
      </Section>

      <Section num={4} title="How We Use Your Data and Legal Bases">
        <p>We process your data only when we have a valid legal basis:</p>
        <ul className="list-disc list-outside ml-5 space-y-2">
          <li>
            <strong className="text-slate-700">Consent:</strong> For non-essential cookies
            (analytics and advertising). You can withdraw consent at any time.
          </li>
          <li>
            <strong className="text-slate-700">Legitimate Interests:</strong> To operate and
            secure the website, improve user experience, respond to inquiries, maintain basic
            records, and prevent abuse.
          </li>
          <li>
            <strong className="text-slate-700">Legal Obligation:</strong> To comply with laws,
            respond to lawful requests from authorities, or fulfill retention requirements.
          </li>
        </ul>
        <p>Specific Uses:</p>
        <ul className="list-disc list-outside ml-5 space-y-2">
          <li>
            <strong className="text-slate-700">Google Analytics:</strong> Understand site usage,
            measure trends, and improve content.
          </li>
          <li>
            <strong className="text-slate-700">Google AdSense:</strong> Serve and personalize
            advertisements.
          </li>
          <li>
            <strong className="text-slate-700">Hosting &amp; Security (Vercel):</strong> Deliver
            the site, troubleshoot issues, and protect against abuse.
          </li>
          <li>
            <strong className="text-slate-700">Email Correspondence:</strong> Respond to your
            inquiries.
          </li>
        </ul>
      </Section>

      <Section num={5} title="Sharing Your Data">
        <p>We do not sell your personal data. We may share it with:</p>
        <ul className="list-disc list-outside ml-5 space-y-2">
          <li>
            <strong className="text-slate-700">Service Providers:</strong> Google (Analytics and
            AdSense), Vercel (hosting), and other processors who act on our behalf.
          </li>
          <li>
            <strong className="text-slate-700">Advertising Partners:</strong> Google and its
            network may share data for ad personalization.
          </li>
          <li>
            <strong className="text-slate-700">Legal Authorities:</strong> When required by law.
          </li>
          <li>
            <strong className="text-slate-700">Business Transfers:</strong> In the event of a
            merger or acquisition.
          </li>
        </ul>
      </Section>

      <Section num={6} title="Cookies and Tracking Technologies">
        <p>
          Our site uses cookies for functionality, analytics, advertising, and security.
        </p>
        <ul className="list-disc list-outside ml-5 space-y-2">
          <li>
            <strong className="text-slate-700">Essential Cookies:</strong> Strictly necessary for
            site operation (placed without consent).
          </li>
          <li>
            <strong className="text-slate-700">Non-Essential Cookies:</strong> Analytics and
            advertising cookies require your explicit consent via our cookie banner.
          </li>
        </ul>
        <p>
          You can manage preferences through the cookie banner or by clicking &ldquo;Cookie
          Settings&rdquo; in the footer. You may also opt out of personalized advertising via{' '}
          <a
            href="https://adssettings.google.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-red-600 hover:text-red-700 transition-colors underline underline-offset-2"
          >
            Google Ads Settings
          </a>{' '}
          or the{' '}
          <a
            href="https://optout.networkadvertising.org"
            target="_blank"
            rel="noopener noreferrer"
            className="text-red-600 hover:text-red-700 transition-colors underline underline-offset-2"
          >
            Network Advertising Initiative Opt-Out
          </a>
          .
        </p>
      </Section>

      <Section num={7} title="International Data Transfers">
        <p>
          Our service providers (Google and Vercel) process data in the United States and other
          countries. We rely on Standard Contractual Clauses, Data Privacy Framework
          participation, or equivalent safeguards.
        </p>
      </Section>

      <Section num={8} title="Data Retention">
        <ul className="list-disc list-outside ml-5 space-y-2">
          <li>Email inquiries: As long as needed to resolve your request.</li>
          <li>Analytics data: Typically up to 14 months.</li>
          <li>Server logs: For a limited period for security and debugging.</li>
        </ul>
      </Section>

      <Section num={9} title="Your Rights">
        <p>
          You may have rights to access, correct, delete, restrict, object to processing, request
          data portability, and withdraw consent.
        </p>
        <p>
          <strong className="text-slate-700">EU/EEA Residents:</strong> You may lodge a complaint
          with your local data protection authority.
        </p>
        <p>
          <strong className="text-slate-700">California Residents (CCPA/CPRA):</strong> You have
          rights to know, delete, correct, opt out of sale/sharing, and non-discrimination.
        </p>
        <p>
          To exercise any rights, email{' '}
          <a
            href="mailto:contact-the-team@24econews.com"
            className="text-red-600 hover:text-red-700 transition-colors underline underline-offset-2"
          >
            contact-the-team@24econews.com
          </a>
          . We respond within one month.
        </p>
      </Section>

      <Section num={10} title="Security">
        <p>
          We implement reasonable technical and organizational measures to protect your data. No
          system is completely secure.
        </p>
      </Section>

      <Section num={11} title="Automated Decision-Making and Profiling">
        <p>
          We do not engage in solely automated decision-making with legal effects. Advertising
          partners may use data for behavioral advertising.
        </p>
      </Section>

      <Section num={12} title="Children's Privacy">
        <p>
          Our site is not directed at children under 13. We do not knowingly collect data from
          children.
        </p>
      </Section>

      <Section num={13} title="Third-Party Links">
        <p>
          Our site may contain links to external websites. We are not responsible for their
          privacy practices.
        </p>
      </Section>

      <Section num={14} title="Changes to This Policy">
        <p>
          We may update this policy periodically. Changes are reflected in the &ldquo;Last
          updated&rdquo; date.
        </p>
      </Section>
    </div>
  )
}
