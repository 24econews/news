// No 'use client' needed — this renders a plain <a> to a static intent URL
// built entirely from props already known at render time, so it works as a
// server component too (used directly from the Opinion page).

interface Props {
  text: string
  url: string
  label?: string
}

const BTN_CLASS =
  'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 text-slate-700 text-xs font-medium hover:bg-slate-200 transition-colors'

export default function BlueskyShareButton({ text, url, label = 'Share on Bluesky' }: Props) {
  const intentUrl = `https://bsky.app/intent/compose?text=${encodeURIComponent(`${text}\n\n${url}`)}`

  return (
    <a href={intentUrl} target="_blank" rel="noopener noreferrer" className={BTN_CLASS}>
      {/* Bluesky butterfly logo */}
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M5.202 2.857C7.954 4.922 10.913 9.11 12 11.358c1.087-2.247 4.046-6.436 6.798-8.501C20.783 1.366 24 .213 24 3.883c0 .732-.42 6.156-.667 7.037-.856 3.061-3.978 3.842-6.755 3.37 4.854.826 6.089 3.562 3.422 6.299-5.065 5.196-7.28-1.304-7.847-2.97-.104-.305-.152-.448-.153-.327 0-.121-.05.022-.153.327-.568 1.666-2.782 8.166-7.847 2.97-2.667-2.737-1.432-5.473 3.422-6.3-2.777.473-5.899-.308-6.755-3.369C.42 10.04 0 4.615 0 3.883c0-3.67 3.217-2.517 5.202-1.026" />
      </svg>
      {label}
    </a>
  )
}
