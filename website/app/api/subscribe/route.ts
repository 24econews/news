const BUTTONDOWN_SUBSCRIBERS_URL = 'https://api.buttondown.com/v1/subscribers'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export async function POST(request: Request) {
  let email: unknown
  try {
    const body = await request.json()
    email = body?.email
  } catch {
    return Response.json({ error: 'Invalid request body.' }, { status: 400 })
  }

  if (typeof email !== 'string' || !EMAIL_RE.test(email.trim())) {
    return Response.json({ error: 'Please enter a valid email address.' }, { status: 400 })
  }

  const apiKey = process.env.BUTTONDOWN_API_KEY
  if (!apiKey) {
    console.error('[subscribe] BUTTONDOWN_API_KEY is not set')
    return Response.json({ error: 'Subscriptions are temporarily unavailable.' }, { status: 500 })
  }

  const response = await fetch(BUTTONDOWN_SUBSCRIBERS_URL, {
    method: 'POST',
    headers: {
      Authorization: `Token ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email: email.trim() }),
  })

  if (response.ok) {
    return Response.json({ success: true })
  }

  const text = await response.text()

  // Buttondown returns 400 with a message referencing the existing
  // subscriber when the email is already on the list — treat that as
  // a success from the user's perspective rather than an error.
  if (response.status === 400 && /already/i.test(text)) {
    return Response.json({ success: true, alreadySubscribed: true })
  }

  console.error(`[subscribe] Buttondown error ${response.status}: ${text}`)
  return Response.json({ error: 'Something went wrong. Please try again later.' }, { status: 502 })
}
