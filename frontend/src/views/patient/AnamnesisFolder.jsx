/** Cartella anamnestica: structured history shared by worker and clinician —
 * risk factors vs confirmed strengths, questionnaire, wellbeing instruments. */
import { useMemo, useState } from 'react'
import * as api from '../../lib/api'
import { formatDate } from '../../lib/format'
import { Badge, ConfirmDialog, Empty, Modal } from '../../components/ui'
import WellbeingTrend from '../../components/WellbeingTrend'
import { useAsync } from '../../lib/useAsync'

const SECTION_LABELS = { stile_di_vita: 'Stile di vita', lavoro: 'Lavoro', storia_clinica: 'Storia clinica' }

export default function AnamnesisFolder({ patientId, onRiskUpdated }) {
  const anamnesis = useAsync(() => api.getAnamnesis(patientId), [patientId])
  const wellbeing = useAsync(() => api.getWellbeing(patientId), [patientId])
  const instruments = useAsync(() => api.getInstruments(), [])

  const [editing, setEditing] = useState(null)
  const [editValue, setEditValue] = useState(null)
  const [saving, setSaving] = useState(false)
  const [instrument, setInstrument] = useState(null)
  const [instrumentAnswers, setInstrumentAnswers] = useState({})
  const [instrumentError, setInstrumentError] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const medications = useAsync(() => api.getMedications(patientId), [patientId])

  const data = anamnesis.data
  const grouped = useMemo(() => groupQuestions(data), [data])

  function groupQuestions(data) {
    if (!data) return []
    const groups = {}
    for (const q of data.questions) (groups[q.section] ||= []).push(q)
    return Object.entries(groups).map(([key, items]) => ({ key, label: SECTION_LABELS[key] || key, items }))
  }

  const answerOf = (q) => data?.answers?.[String(q.id)] || null
  const byState = (state) => (data?.risk?.components || []).filter((c) => c.state === state)

  async function saveEdit(q) {
    let value = editValue
    if (Array.isArray(value)) value = value.join(', ')
    if (!value || (Array.isArray(editValue) && editValue.length === 0)) { setEditing(null); return }
    setSaving(true)
    try {
      const res = await api.putAnamnesisAnswer(patientId, q.id, value)
      await anamnesis.reload()
      onRiskUpdated?.(res.risk)
      setEditing(null)
    } finally { setSaving(false) }
  }

  function startEdit(q) {
    setEditing(q.id)
    const a = answerOf(q)
    setEditValue(q.answer_type === 'multi_choice' ? (a ? a.value.split(', ').map((s) => s.trim()) : []) : a?.value ?? null)
  }

  async function saveInstrument() {
    setInstrumentError('')
    try {
      await api.submitWellbeing(patientId, { instrument: instrument.instrument, answers: instrumentAnswers })
      await wellbeing.reload()
      setInstrument(null)
    } catch (e) {
      setInstrumentError(e.message)
    }
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

  if (anamnesis.loading) return null
  if (!data) return null

  const risks = byState('risk')
  const protectives = byState('protective')
  const borderlines = byState('borderline')
  const unknowns = byState('unknown')
  const latestOf = (inst) => (wellbeing.data || []).find((w) => w.instrument === inst.instrument)

  return (
    <div className="section">
      <div className="card">
        <div className="card-body row-between wrap" style={{ gap: 12 }}>
          <div style={{ maxWidth: 640 }}>
            <h2>Cartella anamnestica</h2>
            <p className="muted" style={{ fontSize: 12.5, marginTop: 4 }}>
              Raccolta strutturata e condivisa: tu e il medico visualizzate gli stessi dati —
              i fattori di rischio con le relative soglie documentate e i punti di forza
              confermati (un fattore “negativo”, sotto soglia o controllato, viene conteggiato
              come protettivo).
            </p>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={exportFhir}>Esporta FHIR</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }} className="folder-grid">
        <div className="card" style={{ borderTop: '3px solid var(--risk)' }}>
          <div className="card-head"><h3 style={{ color: 'var(--risk)' }}>Fattori di rischio attivi ({risks.length})</h3></div>
          <div className="card-body stack" style={{ gap: 9 }}>
            {risks.length === 0 && <p className="muted" style={{ fontSize: 12.5 }}>Nessun fattore di rischio attivo.</p>}
            {risks.map((c) => (
              <div key={c.code} className="panel-flat accent-risk">
                <div className="row-between">
                  <strong style={{ fontSize: 12.5 }}>{c.label}</strong>
                  <span className={`badge ${c.severity === 'alta' ? 'badge-risk' : 'badge-warn'}`}>
                    {c.severity === 'alta' ? 'Critico' : 'Da correggere'}
                  </span>
                </div>
                <div className="row-between" style={{ marginTop: 3 }}>
                  <span style={{ fontSize: 12.5 }}>{c.value_text}</span>
                  {c.threshold_text && <span className="muted" style={{ fontSize: 11 }}>soglia {c.threshold_text}</span>}
                </div>
                {c.reference && <p className="reference-note" style={{ marginTop: 3 }}>Fonte: {c.reference}</p>}
              </div>
            ))}
          </div>
        </div>

        <div className="card" style={{ borderTop: '3px solid var(--ok)' }}>
          <div className="card-head"><h3 style={{ color: 'var(--ok)' }}>Punti di forza confermati ({protectives.length})</h3></div>
          <div className="card-body stack" style={{ gap: 9 }}>
            {protectives.length === 0 && (
              <p className="muted" style={{ fontSize: 12.5 }}>Completa l’anamnesi per scoprire i tuoi punti di forza.</p>
            )}
            {protectives.map((c) => (
              <div key={c.code} className="panel-flat accent-ok">
                <div className="row-between">
                  <strong style={{ fontSize: 12.5 }}>{c.label}</strong>
                  <Badge tone="ok" dot>Protettivo</Badge>
                </div>
                <div className="row-between" style={{ marginTop: 3 }}>
                  <span style={{ fontSize: 12.5 }}>{c.value_text}</span>
                  {c.protective_threshold_text && (
                    <span className="muted" style={{ fontSize: 11 }}>criterio {c.protective_threshold_text}</span>
                  )}
                </div>
                {c.protective_reference && <p className="reference-note" style={{ marginTop: 3 }}>Fonte: {c.protective_reference}</p>}
              </div>
            ))}
          </div>
        </div>
      </div>

      {(borderlines.length > 0 || unknowns.length > 0) && (
        <div className="row wrap" style={{ gap: 12 }}>
          {borderlines.length > 0 && (
            <div className="card grow">
              <div className="card-head"><h3>Vicino alla soglia — da monitorare</h3></div>
              <div className="card-body row wrap" style={{ gap: 7 }}>
                {borderlines.map((c) => (
                  <span key={c.code} className="chip">
                    {c.label} · {c.value_text}{c.threshold_text ? ` (soglia ${c.threshold_text})` : ''}
                  </span>
                ))}
              </div>
            </div>
          )}
          {unknowns.length > 0 && (
            <div className="card grow">
              <div className="card-head"><h3>Dati mancanti</h3></div>
              <div className="card-body row wrap" style={{ gap: 7 }}>
                {unknowns.map((c) => <span key={c.code} className="chip">{c.label}</span>)}
              </div>
            </div>
          )}
        </div>
      )}

      {/* questionnaire */}
      <div className="card">
        <div className="card-head">
          <h3>Questionario anamnestico</h3>
          <span className="hint">Risposte condivise con l’operatore sanitario</span>
        </div>
        <div className="card-body stack" style={{ gap: 15 }}>
          {grouped.map((group) => (
            <div key={group.key}>
              <h3 style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 7 }}>
                {group.label}
              </h3>
              <div className="stack" style={{ gap: 7 }}>
                {group.items.map((q) => {
                  const a = answerOf(q)
                  return (
                    <div key={q.id} className="panel-flat">
                      <div className="row-between wrap" style={{ gap: 8 }}>
                        <div className="grow">
                          <div style={{ fontWeight: 650, fontSize: 12.5 }}>{q.prompt}</div>
                          {a ? (
                            <div style={{ fontSize: 12.5, color: 'var(--brand-strong)', marginTop: 2, fontWeight: 600 }}>{a.value}</div>
                          ) : (
                            <div style={{ fontSize: 12, color: 'var(--faint)', marginTop: 2 }}>Non compilato</div>
                          )}
                          {q.help_text && <div className="help" style={{ marginTop: 2 }}>{q.help_text}</div>}
                        </div>
                        <button className="btn btn-secondary btn-sm" onClick={() => startEdit(q)}>
                          {a ? 'Modifica' : 'Rispondi'}
                        </button>
                      </div>

                      {editing === q.id && (
                        <div style={{ marginTop: 10 }}>
                          {q.answer_type === 'single_choice' && (
                            <div className="option-list">
                              {q.options.map((o) => (
                                <label key={o.value} className={`option-item${editValue === o.value ? ' selected' : ''}`}>
                                  <input type="radio" name={`q_${q.id}`} value={o.value}
                                         checked={editValue === o.value} onChange={() => setEditValue(o.value)} />
                                  {o.label}
                                  {o.risk && <span className="badge badge-risk flag">fattore di rischio</span>}
                                  {o.protective && <span className="badge badge-ok flag">protettivo</span>}
                                </label>
                              ))}
                            </div>
                          )}
                          {q.answer_type === 'multi_choice' && (
                            <div className="option-list">
                              {q.options.map((o) => (
                                <label key={o.value} className={`option-item${editValue?.includes(o.value) ? ' selected' : ''}`}>
                                  <input type="checkbox" value={o.value}
                                         checked={editValue?.includes(o.value)}
                                         onChange={(e) => setEditValue((cur) => (
                                           e.target.checked ? [...(cur || []), o.value] : (cur || []).filter((v) => v !== o.value)
                                         ))} />
                                  {o.label}
                                  {o.risk && <span className="badge badge-risk flag">fattore di rischio</span>}
                                  {o.protective && <span className="badge badge-ok flag">protettivo</span>}
                                </label>
                              ))}
                            </div>
                          )}
                          {q.answer_type === 'text' && (
                            <input className="input" value={editValue ?? ''} onChange={(e) => setEditValue(e.target.value)} placeholder="Scrivi qui…" />
                          )}
                          <div className="row" style={{ justifyContent: 'flex-end', marginTop: 8, gap: 8 }}>
                            <button className="btn btn-secondary btn-sm" onClick={() => setEditing(null)}>Annulla</button>
                            <button className="btn btn-primary btn-sm" disabled={saving} onClick={() => saveEdit(q)}>Salva risposta</button>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* wellbeing instruments */}
      <div className="card">
        <div className="card-head">
          <h3>Indicatori di benessere</h3>
          <span className="hint">Questionari validati dalla letteratura</span>
        </div>
        <div className="card-body stack" style={{ gap: 9 }}>
          {(instruments.data || []).map((inst) => {
            const latest = latestOf(inst)
            return (
              <div key={inst.instrument} className="panel-flat">
                <div className="row-between wrap" style={{ gap: 8 }}>
                  <div className="grow" style={{ minWidth: 220 }}>
                    <strong style={{ fontSize: 12.5 }}>{inst.label}</strong>
                    <p className="muted" style={{ fontSize: 12, marginTop: 2 }}>{inst.description}</p>
                    <p className="reference-note" style={{ marginTop: 2 }}>{inst.reference}</p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    {latest && (
                      <>
                        <div style={{ fontWeight: 750 }}>
                          {latest.score ?? '—'} <span className="muted" style={{ fontSize: 10.5, fontWeight: 500 }}>{latest.category}</span>
                        </div>
                        <div style={{ fontSize: 10.5, color: 'var(--faint)' }}>{formatDate(latest.taken_on)}</div>
                      </>
                    )}
                    <button className="btn btn-primary btn-sm" style={{ marginTop: 6 }}
                            onClick={() => { setInstrument(inst); setInstrumentAnswers({}); setInstrumentError('') }}>
                      {latest ? 'Ripeti' : 'Compila'}
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
          {(instruments.data || []).length === 0 && <Empty icon="book">Nessun questionario disponibile.</Empty>}
        </div>
      </div>

      {/* therapy (read-only for the worker; managed by the clinician) */}
      <div className="card">
        <div className="card-head"><h3>Terapia in corso</h3></div>
        <div className="card-body">
          {(medications.data || []).filter((m) => m.active).length > 0 ? (
            <div className="row wrap" style={{ gap: 7 }}>
              {medications.data.filter((m) => m.active).map((m) => (
                <span key={m.id} className="chip">
                  <strong>{m.name}</strong>{m.dosage ? ` · ${m.dosage}` : ''}{m.schedule ? ` · ${m.schedule}` : ''}
                </span>
              ))}
            </div>
          ) : (
            <p className="muted" style={{ fontSize: 12.5 }}>Nessuna terapia in corso registrata.</p>
          )}
        </div>
      </div>

      {/* wellbeing trend */}
      <div className="card">
        <div className="card-head"><h3>Andamento benessere e lavoro</h3></div>
        <div className="card-body">
          <WellbeingTrend assessments={wellbeing.data || []} />
        </div>
      </div>

      {/* GDPR: data portability and erasure */}
      <div className="card">
        <div className="card-head"><h3>I tuoi dati</h3></div>
        <div className="card-body row-between wrap" style={{ gap: 10 }}>
          <p className="muted" style={{ fontSize: 12.5, maxWidth: 520 }}>
            Puoi scaricare una copia completa dei dati che la piattaforma ti riguarda, o
            richiederne la cancellazione: le informazioni personali vengono rimosse e
            l'accesso disattivato (i dati clinici aggregati restano in forma anonima).
          </p>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn btn-secondary btn-sm" onClick={async () => {
              const text = await api.exportAllData(patientId)
              const blob = new Blob([text], { type: 'application/json' })
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = `dati_paziente${patientId}.json`
              a.click()
              URL.revokeObjectURL(url)
            }}>
              Esporta tutti i dati
            </button>
            <button className="btn btn-danger btn-sm" onClick={() => setConfirmDelete(true)}>
              Cancella account
            </button>
          </div>
        </div>
      </div>

      {instrument && (
        <Modal
          wide
          title={instrument.label}
          onClose={() => setInstrument(null)}
          footer={
            <>
              <button className="btn btn-secondary" onClick={() => setInstrument(null)}>Annulla</button>
              <button className="btn btn-primary" onClick={saveInstrument}>Salva questionario</button>
            </>
          }
        >
          <p className="muted" style={{ fontSize: 12.5, marginBottom: 14 }}>{instrument.description}</p>
          <div className="stack" style={{ gap: 13 }}>
            {instrument.questions.map((q) => (
              <InstrumentQuestion key={q.id} q={q} answers={instrumentAnswers} setAnswers={setInstrumentAnswers} />
            ))}
          </div>
          {instrumentError && <p className="error-text" style={{ marginTop: 10 }}>{instrumentError}</p>}
        </Modal>
      )}
      <ConfirmDialog
        open={confirmDelete} tone="danger" confirmLabel="Cancella definitivamente"
        title="Cancellare l'account?"
        message="Questa azione rimuove i tuoi dati personali e disattiva l'accesso. Non è reversibile."
        onConfirm={async () => {
          await api.deleteMyAccount()
          localStorage.removeItem('user')
          window.location.assign('/login')
        }}
        onCancel={() => setConfirmDelete(false)}
      />
    </div>
  )
}

function InstrumentQuestion({ q, answers, setAnswers }) {
  if (q.options) {
    return (
      <div className="field">
        <label>{q.text}</label>
        <div className="row wrap" style={{ gap: 6 }}>
          {q.options.map((o) => (
            <label key={o.value} className="chip" style={{ cursor: 'pointer', ...(answers[q.id] === o.value ? { borderColor: 'var(--brand)', color: 'var(--brand-strong)', fontWeight: 650 } : {}) }}>
              <input type="radio" name={`w_${q.id}`} value={o.value} style={{ marginRight: 4 }}
                     checked={answers[q.id] === o.value} onChange={() => setAnswers({ ...answers, [q.id]: o.value })} />
              {o.label}
            </label>
          ))}
        </div>
      </div>
    )
  }
  if (q.answer_type === 'scale0_10') {
    return (
      <div className="field">
        <label>{q.text}</label>
        <div className="row wrap" style={{ gap: 4 }}>
          {Array.from({ length: 11 }, (_, n) => (
            <button key={n} type="button" className="chip" style={{ cursor: 'pointer', minWidth: 32, justifyContent: 'center', ...(Number(answers[q.id]) === n ? { borderColor: 'var(--brand)', color: 'var(--brand-strong)', fontWeight: 750 } : {}) }}
                    onClick={() => setAnswers({ ...answers, [q.id]: n })}>
              {n}
            </button>
          ))}
        </div>
      </div>
    )
  }
  const max = Number(q.answer_type.split('_').pop()) || 12
  return (
    <div className="field" style={{ maxWidth: 170 }}>
      <label>{q.text}</label>
      <input type="number" className="input" min={0} max={max} value={answers[q.id] ?? ''}
             onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value === '' ? '' : Number(e.target.value) })} />
    </div>
  )
}
