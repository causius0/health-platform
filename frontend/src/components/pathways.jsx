/** Care-pathway UI shared by the worker portal and the clinician console. */
import { useState } from 'react'
import * as api from '../lib/api'
import { formatDate, formatDateTime, STEP_KIND_LABEL } from '../lib/format'
import Icon from './Icon'
import { Badge, Field, Modal, Progress } from './ui'

const KIND_ICON = {
  screening: 'flask',
  visita: 'stethoscope',
  misurazione: 'monitor',
  educazione: 'book',
  richiamo: 'phone',
}

const STATE_META = {
  completato: { label: 'Completato', cls: 'badge-ok' },
  programmato: { label: 'Programmato', cls: 'badge-info' },
  in_ritardo: { label: 'In ritardo', cls: 'badge-risk' },
  in_attesa: { label: 'Da fare', cls: 'badge-warn' },
}

export function PathwayCard({ pathway, role, onUpdate, onRecord }) {
  const [busyStep, setBusyStep] = useState(null)
  const [bookingStep, setBookingStep] = useState(null)
  const [error, setError] = useState('')

  async function run(stepId, fn) {
    setBusyStep(stepId)
    setError('')
    try {
      const updated = await fn()
      onUpdate?.(updated.pathway ?? updated)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusyStep(null)
    }
  }

  const pending = pathway.steps.filter((s) => s.status !== 'completato')
  const nextStep = pending.find((s) => s.status === 'in_ritardo') || pending[0]

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h3 style={{ textTransform: 'none', letterSpacing: 0, fontSize: 14 }}>{pathway.name}</h3>
          {pathway.description && (
            <p className="muted" style={{ fontSize: 12, marginTop: 2 }}>{pathway.description}</p>
          )}
        </div>
        <div className="row" style={{ minWidth: 170, justifyContent: 'flex-end', gap: 10 }}>
          <div style={{ flex: 1, maxWidth: 120 }}>
            <Progress value={pathway.progress} tone={pathway.progress === 100 ? 'ok' : undefined} />
          </div>
          <span className="num" style={{ fontWeight: 700, fontSize: 13 }}>{pathway.progress}%</span>
        </div>
      </div>
      <div className="card-body">
        {/* step rail */}
        <div className="step-rail">
          {pathway.steps.map((s, i) => {
            const nodeClass =
              s.status === 'completato' ? 'done'
                : s.status === 'in_ritardo' ? 'in-ritardo'
                  : s.status === 'programmato' ? 'programmato'
                    : i === pathway.steps.findIndex((x) => x.status === 'in_attesa') ? 'corrente' : ''
            return (
              <div key={s.id} className={`step-node ${nodeClass}`} title={`${s.title} · ${STEP_KIND_LABEL[s.kind]}`}>
                <div className="line" />
                <div className="marker">
                  <Icon name={s.status === 'completato' ? 'check' : KIND_ICON[s.kind] || 'clock'} size={13} strokeWidth={2.2} />
                </div>
                <div className="step-title">{s.title}</div>
                <div className="step-when">
                  {s.status === 'completato' ? formatDate(s.completed_on) : formatDate(s.due_on)}
                </div>
              </div>
            )
          })}
        </div>

        {/* pending actions */}
        {pending.length > 0 && (
          <div className="stack" style={{ marginTop: 8 }}>
            {pending.map((s) => (
              <StepAction
                key={s.id}
                step={s}
                role={role}
                busy={busyStep === s.id}
                isNext={s.id === nextStep?.id}
                onBook={() => setBookingStep(s)}
                onComplete={(outcome) => run(s.id, () => api.completePathwayStep(s.id, { outcome }))}
                onRecord={() => onRecord?.(s)}
                onFollowUp={() => run(s.id, () => api.scheduleStepFollowUp(s.id, {}))}
              />
            ))}
          </div>
        )}

        {pending.length === 0 && (
          <div className="alert-item" style={{ borderColor: 'var(--ok-soft)', background: 'var(--ok-soft)' }}>
            <span style={{ color: 'var(--ok)' }}><Icon name="check" size={16} /></span>
            <span style={{ fontSize: 12.5 }}>Tutte le tappe del percorso sono state completate.</span>
          </div>
        )}
        {error && <p className="error-text" style={{ marginTop: 8 }}>{error}</p>}
      </div>

      {bookingStep && (
        <BookingStepModal
          step={bookingStep}
          onClose={() => setBookingStep(null)}
          onBooked={(payload) => {
            setBookingStep(null)
            onUpdate?.(payload.pathway)
          }}
        />
      )}
    </div>
  )
}

function StepAction({ step, role, busy, isNext, onBook, onComplete, onRecord, onFollowUp }) {
  const state = STATE_META[step.status]
  const selfBooking = role === 'patient'
  return (
    <div className={`panel-flat${isNext ? ' accent-brand' : ''}`}>
      <div className="row-between wrap" style={{ gap: 8 }}>
        <div className="grow" style={{ minWidth: 200 }}>
          <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
            {isNext && <Badge tone="info">Prossima azione</Badge>}
            <strong style={{ fontSize: 13 }}>{step.title}</strong>
            <span className={`badge ${state.cls}`}>{state.label}</span>
          </div>
          {step.description && <p className="muted" style={{ fontSize: 12, marginTop: 2 }}>{step.description}</p>}
          <p style={{ fontSize: 11, color: 'var(--faint)', marginTop: 2 }}>
            {step.status === 'programmato' && step.appointment
              ? `Appuntamento ${formatDateTime(step.appointment.scheduled_at)} · ${step.appointment.status === 'proposto' ? 'in attesa di conferma' : 'confermato'}`
              : `Entro il ${formatDate(step.due_on)}`}
          </p>
        </div>

        <div className="row" style={{ gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {step.status === 'in_attesa' && step.kind === 'misurazione' && (
            <button className="btn btn-secondary btn-sm" disabled={busy} onClick={onRecord}>Registra</button>
          )}
          {(step.kind === 'visita' || step.kind === 'screening') &&
            ['in_attesa', 'in_ritardo'].includes(step.status) && (
            <button className="btn btn-primary btn-sm" disabled={busy} onClick={onBook}>
              {step.kind === 'screening' ? 'Prenota esame' : 'Prenota visita'}
            </button>
          )}
          {step.kind === 'richiamo' && role === 'doctor' && step.status === 'in_attesa' && (
            <button className="btn btn-primary btn-sm" disabled={busy} onClick={onFollowUp}>Programma richiamo</button>
          )}
          {step.kind === 'richiamo' && selfBooking && step.status === 'in_attesa' && (
            <span className="chip"><Icon name="phone" size={12} /> L’operatore ti richiamerà</span>
          )}
          {step.status !== 'completato' && step.kind !== 'richiamo' && step.status !== 'programmato' && (
            <button className="btn btn-secondary btn-sm" disabled={busy}
                    onClick={() => onComplete(step.kind === 'educazione' ? 'Completato' : undefined)}>
              Segna effettuato
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function BookingStepModal({ step, onClose, onBooked }) {
  const [date, setDate] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function book() {
    setBusy(true)
    setError('')
    try {
      const body = date ? { scheduled_at: new Date(`${date}T09:00`).toISOString() } : {}
      const payload = await api.bookPathwayStep(step.id, body)
      onBooked(payload)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      title={`Prenota — ${step.title}`}
      onClose={onClose}
      footer={
        <>
          <button className="btn btn-secondary" onClick={onClose}>Annulla</button>
          <button className="btn btn-primary" disabled={busy} onClick={book}>
            {busy ? 'Prenotazione…' : 'Prenota appuntamento'}
          </button>
        </>
      }
    >
      <p className="muted" style={{ fontSize: 12.5, marginBottom: 12 }}>
        {step.description || 'L’appuntamento verrà inserito nel percorso e nel tuo elenco visite.'}
      </p>
      <Field label="Giornata preferita (opzionale)" help="Senza indicazione, l’ambulatorio proporrà il primo slot utile entro una settimana.">
        <input type="date" className="input" value={date} min={new Date().toISOString().slice(0, 10)}
               onChange={(e) => setDate(e.target.value)} />
      </Field>
      {error && <p className="error-text" style={{ marginTop: 10 }}>{error}</p>}
    </Modal>
  )
}

/** The most urgent pending action across all pathways, for hero surfaces. */
export function nextActionsOf(pathways, limit = 3) {
  const stateRank = { in_ritardo: 0, in_attesa: 1, programmato: 2 }
  return pathways
    .flatMap((p) => p.steps.map((s) => ({ ...s, pathwayName: p.name })))
    .filter((s) => s.status !== 'completato')
    .sort((a, b) => (stateRank[a.status] - stateRank[b.status]) || (new Date(a.due_on) - new Date(b.due_on)))
    .slice(0, limit)
}
