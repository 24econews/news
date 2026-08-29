import type { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: '*', allow: '/' },
    sitemap: [
      'https://www.24econews.com/sitemap.xml',
      'https://www.24econews.com/news-sitemap.xml',
    ],
  }
}
