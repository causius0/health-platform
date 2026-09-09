/** Doctor view of the structured anamnesis with correction rights + FHIR export. */
import { Fragment, useState } from 'react'
import * as api from '../../lib/api'
import { useAsync } from '../../lib/useAsync'
import WellbeingTrend from '../../components/WellbeingTrend'
import QuestionEditor, { serializeAnswer } from '../../components/QuestionEditor'

const SECTION_LABELS = { stile_di_vita: 'Stile di vita', lavoro: 'Lavoro', storia_clinica: 'Storia clinica' }

export default function AnamnesisPanel({ patientId, onRiskUpdated }) {
  const anamnesis = useAsync(() => api.getAnamnesis(patientId), [patientId])
  const wellbeing = useAsync(() => api.getWellbeing(patientId), [patientId])
  const [editing, setEditing] = useState(null)
  const [editValue, setEditValue] = useState(null)
  const [saving, setSaving] = useState(false)

  if (anamnesis.loading || !anamnesis.data) return null
  const data = anamnesis.data

  const grouped = Object.entries(
    data.questions.reduce((acc, q) => { (acc[q.section] ||= []).push(q); return acc }, {}),
  ).map(([key, items]) => ({ key, label: SECTION_LABELS[key] || key, items }))

  const answerOf = (q) => data.answers?.[String(q.id)] || null

  function startEdit(q) {
    setEditing(q.id)
    const a = answerOf(q)
    setEditValue(q.answer_type === 'multi_choice'
      ? (a ? a.value.split(', ').map((s) => s.trim()) : [])
      : a?.value ?? null)
  }

  async function saveEdit(q) {
    const value = serializeAnswer(editValue)
    if (!value) { setEditing(null); return }
    setSaving(true)
    try {
      const res = await api.putAnamnesisAnswer(patientId, q.id, value)
      await anamnesis.reload()
      onRiskUpdated?.(res.risk)
      setEditing(null)
    } finally { setSaving(false) }
  }

  async function exportFhir() {
    const text = await api.exportAnamnesisFhir(patientId)
    const blob = new Blob([text], { type: 'application/fhir+json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `anamnesis_${patientId}_fhir.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="section">
      <div className="card">
        <div className="card-head">
          <h3>Anamnesi strutturata</h3>
          <div className="row" style={{ gap: 8 }}>
            <span className="hint">Compilata dal lavoratore · correggibile dall’operatore</span>
            <button className="btn btn-secondary btn-sm" onClick={exportFhir}>Esporta FHIR</button>
          </div>
        </div>
        <div className="card-body stack" style={{ gap: 14 }}>
          {grouped.map((group) => (
            <div key={group.key}>
              <h3 style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 5 }}>
                {group.label}
              </h3>
              <table className="table">
                <tbody>
                  {group.items.map((q) => {
                    const a = answerOf(q)
                    return (
                      <Fragment key={q.id}>
                        <tr>
                          <td style={{ width: '36%', fontWeight: 650 }}>{q.prompt}</td>
                          <td style={{ color: a ? 'var(--brand-strong)' : 'var(--faint)', fontWeight: a ? 650 : 400 }}>
                            {a ? a.value : 'Non compilato'}
                          </td>
                          <td style={{ width: 90, textAlign: 'right' }}>
                            <button className="btn btn-secondary btn-sm"
                                    onClick={() => (editing === q.id ? setEditing(null) : startEdit(q))}>
                              {editing === q.id ? 'Chiudi' : 'Correggi'}
                            </button>
                          </td>
                        </tr>
                        {editing === q.id && (
                          <tr>
                            <td colSpan={3}>
                              <QuestionEditor question={q} value={editValue} onChange={setEditValue} />
                              <div className="row" style={{ justifyContent: 'flex-end', marginTop: 8 }}>
                                <button className="btn btn-primary btn-sm" disabled={saving} onClick={() => saveEdit(q)}>Salva</button>
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="card-head"><h3>Andamento indicatori di benessere</h3></div>
        <div className="card-body">
          <WellbeingTrend assessments={wellbeing.data || []} />
        </div>
      </div>
    </div>
  )
}
