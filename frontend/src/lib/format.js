export function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export function formatDay(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' })
}

export function formatDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return `${formatDay(iso)} ${d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}`
}

export function relativeDays(iso) {
  if (!iso) return ''
  const diff = Math.round((new Date(iso) - Date.now()) / 86400000)
  if (diff === 0) return 'oggi'
  if (diff === 1) return 'domani'
  if (diff === -1) return 'ieri'
  if (diff > 1) return `tra ${diff} giorni`
  return `${Math.abs(diff)} giorni fa`
}

export const RISK_LEVEL_LABEL = { alto: 'Rischio alto', medio: 'Rischio medio', basso: 'Rischio basso' }
export const TIER_LABEL = { rosso: 'Rosso', arancione: 'Arancione', verde: 'Verde' }
export const APPT_KIND_LABEL = {
  visita_ambulatoriale: 'Visita ambulatoriale',
  teleconsulto: 'Teleconsulto',
  visita_specialistica: 'Visita specialistica',
  esame: 'Esame',
}
export const APPT_STATUS_LABEL = {
  proposto: 'Da confermare', confermato: 'Confermato', completato: 'Completato', annullato: 'Annullato',
}
export const GOAL_AREA_LABEL = {
  physical_activity: 'Attività fisica', nutrition: 'Alimentazione', smoking: 'Fumo',
  alcohol: 'Alcol', sleep: 'Sonno', stress: 'Stress', monitoring: 'Monitoraggio',
}
export const STEP_KIND_LABEL = {
  screening: 'Screening', visita: 'Visita', misurazione: 'Misurazione',
  educazione: 'Educazione', richiamo: 'Richiamo',
}

/** Parse the assistant's three-tier answer format. */
export function parseTiered(content) {
  const tiers = { general: '', advice: '', clinical: '' }
  if (!content) return tiers
  const g = content.match(/INFORMAZIONE GENERALE:\s*([\s\S]*?)(?=CONSIGLIO PREVENTIVO|INDICAZIONE CLINICA|$)/i)
  const p = content.match(/CONSIGLIO PREVENTIVO PERSONALIZZATO:\s*([\s\S]*?)(?=INDICAZIONE CLINICA|$)/i)
  const c = content.match(/INDICAZIONE CLINICA:\s*([\s\S]*)$/i)
  if (g || p || c) {
    tiers.general = (g?.[1] || '').trim()
    tiers.advice = (p?.[1] || '').trim()
    tiers.clinical = (c?.[1] || '').trim()
  } else {
    tiers.general = content
  }
  return tiers
}
