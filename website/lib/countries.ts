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
    name: 'Brazil',
    flag: '🇧🇷',
    language: 'pt',
    active: true,
    sources: ['Folha de S.Paulo', 'Valor Econômico', 'InfoMoney'],
  },
  { slug: 'uruguay', name: 'Uruguay', flag: '🇺🇾', language: 'es', active: false, sources: [] },
  { slug: 'paraguay', name: 'Paraguay', flag: '🇵🇾', language: 'es', active: false, sources: [] },
  {
    slug: 'chile',
    name: 'Chile',
    flag: '🇨🇱',
    language: 'es',
    active: true,
    sources: ['Diario Financiero', 'La Tercera', 'La Nación'],
  },
  { slug: 'bolivia', name: 'Bolivia', flag: '🇧🇴', language: 'es', active: false, sources: [] },
]

export function getCountry(slug: string): Country | undefined {
  return countries.find((c) => c.slug === slug)
}

export function getActiveCountries(): Country[] {
  return countries.filter((c) => c.active)
}
