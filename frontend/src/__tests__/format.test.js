import { describe, expect, it } from 'vitest'
import { parseTiered } from '../lib/format'

describe('parseTiered', () => {
  it('splits the three assistant tiers', () => {
    const content = [
      'INFORMAZIONE GENERALE: L’HbA1c riflette la glicemia media.',
      'CONSIGLIO PREVENTIVO PERSONALIZZATO: Sostituisci una bevanda zuccherata al giorno.',
      'INDICAZIONE CLINICA: Non necessaria in questo caso.',
    ].join('\n')
    const t = parseTiered(content)
    expect(t.general).toContain('HbA1c')
    expect(t.advice).toContain('bevanda zuccherata')
    expect(t.clinical).toContain('Non necessaria')
  })

  it('falls back to plain text when no tiers are present', () => {
    expect(parseTiered('Ciao! Come posso aiutarti?').general).toContain('Ciao')
  })

  it('returns empty tiers for empty content', () => {
    expect(parseTiered('').general).toBe('')
  })
})
