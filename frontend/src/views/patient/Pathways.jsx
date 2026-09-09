import { useState } from 'react'
import { PathwayCard } from '../../components/pathways'
import { Badge, Empty, Field, Modal, Progress } from '../../components/ui'
import * as api from '../../lib/api'
import { GOAL_AREA_LABEL } from '../../lib/format'

const monday = () => {
  const d = new Date()
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7))
  return d.toISOString().slice(0, 10)
}

const METRIC_OPTIONS = [
  { code: 'glucose_fasting', label: 'Glicemia a digiuno' },
  { code: 'bp_systolic', label: 'Pressione sistolica' },
  { code: 'bp_diastolic', label: 'Pressione diastolica' },
  { code: 'weight', label: 'Peso' },
  { code: 'waist', label: 'Circonferenza vita' },
  { code: 'hba1c', label: 'HbA1c' },
]

function RecordMeasurementModal({ patientId, initialCode, step, onClose, onSaved }) {
  const [code, setCode] = useState(initialCode || '')
  const [value, setValue] = useState('')
  const [takenOn, setTakenOn] = useState(new Date().toISOString().slice(0, 10))
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function save() {
    if (!code || value === '') { setError('Compila metrica e valore.'); return }
    setBusy(true)
    try {
      const res = await api.addObservation(patientId, {
        code, value: Number(value), taken_on: takenOn, source: 'patient_home',
      })
      // the measurement IS the step: close it in the pathway as well
      if (step) await api.completePathwayStep(step.id, { outcome: 'Misurazione registrata dal lavoratore' })
      onSaved(res)
    } catch (e) {
      setError(e.message)
      setBusy(false)
    }
  }

  return (
    <Modal
      title={step ? `Registra — ${step.title}` : 'Registra una misurazione'}
      onClose={onClose}
      footer={
        <>
          <button className="btn btn-secondary" onClick={onClose}>Annulla</button>
          <button className="btn btn-primary" disabled={busy} onClick={save}>Salva misura</button>
        </>
      }
    >
      <div className="form-grid">
        <Field label="Metrica">
          <select className="select" value={code} onChange={(e) => setCode(e.target.value)} disabled={!!step}>
            <option value="" disabled>Scegli…</option>
            {METRIC_OPTIONS.map((m) => <option key={m.code} value={m.code}>{m.label}</option>)}
          </select>
        </Field>
        <Field label="Valore">
          <input type="number" step="0.1" className="input" value={value} onChange={(e) => setValue(e.target.value)} placeholder="es. 128" />
        </Field>
        <Field label="Data">
          <input type="date" className="input" value={takenOn} max={new Date().toISOString().slice(0, 10)}
                 onChange={(e) => setTakenOn(e.target.value)} />
        </Field>
      </div>
      {error && <p className="error-text" style={{ marginTop: 10 }}>{error}</p>}
      <p className="reference-note" style={{ marginTop: 10 }}>
        La stratificazione del rischio viene ricalcolata automaticamente dopo ogni misurazione.
      </p>
    </Modal>
  )
}

function GoalsCard({ goalsData }) {
  const [busyGoal, setBusyGoal] = useState(null)

  async function checkin(goal, days) {
    setBusyGoal(goal.id)
    try {
      await api.goalCheckin(goal.id, { week_of: monday(), completed_days: days })
      await goalsData.reload()
    } finally { setBusyGoal(null) }
  }

  async function toggleStatus(goal) {
    setBusyGoal(goal.id)
    try {
      await api.updateGoal(goal.id, { status: goal.status === 'active' ? 'completed' : 'active' })
      await goalsData.reload()
    } finally { setBusyGoal(null) }
  }

  const goals = (goalsData.data || []).filter((g) => g.status !== 'abandoned')
  const week = monday()
  const current = (g) => g.checkins.find((c) => c.week_of === week)

  return (
    <div className="card">
      <div className="card-head">
        <h3>Obiettivi settimanali</h3>
        <span className="hint">Il check-in settimanale alimenta il tuo indice di impegno</span>
      </div>
      <div className="card-body stack" style={{ gap: 10 }}>
        {goals.length === 0 && (
          <Empty icon="target">
            Nessun obiettivo attivo: vengono proposti dall’operatore o dal percorso di prevenzione.
          </Empty>
        )}
        {goals.map((g) => {
          const done = current(g)?.completed_days ?? 0
          return (
            <div key={g.id} className="panel-flat">
              <div className="row-between wrap" style={{ gap: 8 }}>
                <div>
                  <strong style={{ fontSize: 13 }}>{g.title}</strong>
                  <div className="row" style={{ gap: 8, marginTop: 3, flexWrap: 'wrap' }}>
                    <Badge>{GOAL_AREA_LABEL[g.area]}</Badge>
                    <span className="muted" style={{ fontSize: 12 }}>{g.frequency_per_week}x a settimana</span>
                    {g.status === 'completed' && <Badge tone="ok">Completato</Badge>}
                    {g.created_by === 'doctor' && <Badge tone="info">Proposto dall’operatore</Badge>}
                  </div>
                </div>
                <button className="btn btn-secondary btn-sm" disabled={busyGoal === g.id} onClick={() => toggleStatus(g)}>
                  {g.status === 'active' ? 'Segna completato' : 'Riattiva'}
                </button>
              </div>
              <div className="row" style={{ marginTop: 9, gap: 12, flexWrap: 'wrap' }}>
                <div className="grow" style={{ minWidth: 180 }}>
                  <div className="row-between" style={{ fontSize: 11.5 }}>
                    <span>Questa settimana</span>
                    <strong>{done} / {g.frequency_per_week}</strong>
                  </div>
                  <Progress value={(done / g.frequency_per_week) * 100} />
                  <div className="row" style={{ gap: 4, marginTop: 7 }}>
                    {[...g.checkins].reverse().slice(0, 6).map((c) => (
                      <div key={c.week_of} style={{ flex: 1, textAlign: 'center' }}>
                        <div style={{ height: 6, borderRadius: 4, background: 'var(--surface-2)', border: '1px solid var(--border)', overflow: 'hidden' }}>
                          <div style={{ height: '100%', background: 'var(--brand)', width: `${Math.min(100, (c.completed_days / g.frequency_per_week) * 100)}%` }} />
                        </div>
                        <div style={{ fontSize: 9, color: 'var(--faint)', marginTop: 2 }}>{c.week_of.slice(5)}</div>
                      </div>
                    ))}
                  </div>
                </div>
                {g.status === 'active' && (
                  <div className="row" style={{ gap: 4, alignItems: 'flex-start' }}>
                    {Array.from({ length: g.frequency_per_week }, (_, i) => i + 1).map((n) => (
                      <button key={n}
                              className={`btn btn-sm ${done >= n ? 'btn-primary' : 'btn-secondary'}`}
                              style={{ minWidth: 30, padding: '3.5px 8px' }}
                              disabled={busyGoal === g.id}
                              title={`Segna ${n} giorni`}
                              onClick={() => checkin(g, n)}>
                        {n}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function Pathways({ patientId, pathways, onPathwayUpdate, goals, onRiskUpdated }) {
  const [recordFor, setRecordFor] = useState(null) // step requesting a measurement

  async function afterMeasurementSaved(res) {
    setRecordFor(null)
    if (res?.risk) onRiskUpdated?.(res.risk)
    onPathwayUpdate?.()
  }

  return (
    <div className="section">
      <p className="muted" style={{ fontSize: 12.5, margin: 0 }}>
        I tuoi percorsi di <strong>prevenzione, screening e follow-up</strong>: ogni tappa
        indica cosa fare, entro quando e con quale azione — registra una misura, prenota una
        visita o un esame, oppure segna la tappa come effettuata. L’operatore sanitario
        visualizza gli stessi avanzamenti.
      </p>

      {pathways.length === 0 && (
        <Empty icon="route">
          Nessun percorso attivo: l’operatore sanitario ti iscriverà al percorso più adatto
          al tuo profilo di rischio.
        </Empty>
      )}

      {pathways.map((p) => (
        <PathwayCard
          key={p.id}
          pathway={p}
          role="patient"
          onUpdate={onPathwayUpdate}
          onRecord={(step) => setRecordFor(step)}
        />
      ))}

      <GoalsCard goalsData={goals} />

      {recordFor && (
        <RecordMeasurementModal
          patientId={patientId}
          initialCode={recordFor.metric_code || ''}
          step={recordFor}
          onClose={() => setRecordFor(null)}
          onSaved={afterMeasurementSaved}
        />
      )}
    </div>
  )
}
