export interface Country {
  slug: string
  name: string
  flag: string
  language: string
  active: boolean
  sources: string[]
}

export const countries: Country[] = [
  {
    slug: 'argentina',
    name: 'Argentina',
    flag: '🇦🇷',
    language: 'es',
    active: true,
    sources: ['Infobae', 'Clarín', 'La Nación'],
  },
  {
    slug: 'brazil',
    name: 'Brasil',
    flag: '🇧🇷',
    language: 'pt',
    active: true,
    sources: ['Folha de S.Paulo', 'Valor Econômico', 'InfoMoney', 'Exame'],
  },
  { slug: 'mexico', name: 'México', flag: '🇲🇽', language: 'es', active: false, sources: [] },
  { slug: 'chile', name: 'Chile', flag: '🇨🇱', language: 'es', active: false, sources: [] },
  { slug: 'usa', name: 'United States', flag: '🇺🇸', language: 'en', active: false, sources: [] },
  { slug: 'france', name: 'France', flag: '🇫🇷', language: 'fr', active: false, sources: [] },
  { slug: 'germany', name: 'Germany', flag: '🇩🇪', language: 'de', active: false, sources: [] },
]

export function getCountry(slug: string): Country | undefined {
  return countries.find((c) => c.slug === slug)
}

export function getActiveCountries(): Country[] {
  return countries.filter((c) => c.active)
}
