/** Appointments (visite e teleconsulti) + operator recalls (richiami). */
import { useState } from 'react'
import * as api from '../../lib/api'
import {
  APPT_KIND_LABEL, APPT_STATUS_LABEL, formatDate, formatDateTime, relativeDays,
} from '../../lib/format'
import { Badge, ConfirmDialog, Empty, Field, Modal } from '../../components/ui'
import { useAsync } from '../../lib/useAsync'

export default function Appointments({ patientId }) {
  const appts = useAsync(() => api.getAppointments(patientId), [patientId])
  const followUps = useAsync(() => api.getFollowUps(patientId), [patientId])
  const [showBook, setShowBook] = useState(false)
  const [form, setForm] = useState({
    kind: 'visita_ambulatoriale', reason: '', priority: 'routine', scheduled_at: '',
  })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [cancelFor, setCancelFor] = useState(null)

  const upcoming = (appts.data || [])
    .filter((a) => ['proposto', 'confermato'].includes(a.status))
    .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))
  const past = (appts.data || []).filter((a) => !['proposto', 'confermato'].includes(a.status)).slice(0, 6)
  const pendingFu = (followUps.data || []).filter((f) => f.status === 'pending')

  async function book() {
    if (!form.reason.trim() || !form.scheduled_at) { setError('Compila motivo e data/ora.'); return }
    setBusy(true)
    setError('')
    try {
      await api.createAppointment(patientId, {
        ...form,
        scheduled_at: new Date(form.scheduled_at).toISOString(),
      })
      setShowBook(false)
      setForm({ kind: 'visita_ambulatoriale', reason: '', priority: 'routine', scheduled_at: '' })
      await appts.reload()
    } catch (e) {
      setError(e.message)
    } finally { setBusy(false) }
  }

  async function cancel(a) {
    setCancelFor(null)
    await api.updateAppointment(a.id, { status: 'annullato' })
    await appts.reload()
  }

  return (
    <div className="section">
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 12 }} className="appt-grid">
        <div className="card">
          <div className="card-head">
            <h3>Visite e teleconsulti</h3>
            <button className="btn btn-primary btn-sm" onClick={() => setShowBook(true)}>
              Richiedi un appuntamento
            </button>
          </div>
          <div className="card-body stack" style={{ gap: 8 }}>
            {upcoming.length === 0 && (
              <Empty icon="calendar">
                Nessun appuntamento futuro. Puoi richiederne uno oppure troverai qui le visite
                prenotate dall’operatore (anche dopo una chiamata di triage).
              </Empty>
            )}
            {upcoming.map((a) => (
              <div key={a.id} className="panel-flat">
                <div className="row-between wrap" style={{ gap: 8 }}>
                  <div>
                    <strong style={{ fontSize: 12.5 }}>{APPT_KIND_LABEL[a.kind]}</strong>
                    {a.priority === 'urgente' && <Badge tone="warn">urgente</Badge>}
                    <div className="muted truncate" style={{ fontSize: 11.5, maxWidth: 320 }}>{a.reason}</div>
                    <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>{a.location}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 700, fontSize: 12.5 }}>{formatDateTime(a.scheduled_at)}</div>
                    <div className="row" style={{ justifyContent: 'flex-end', gap: 6, marginTop: 4 }}>
                      <Badge tone={a.status === 'confermato' ? 'ok' : 'warn'}>{APPT_STATUS_LABEL[a.status]}</Badge>
                      <button className="btn btn-danger btn-sm" onClick={() => setCancelFor(a)}>Annulla</button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {past.length > 0 && (
              <>
                <hr className="divider" />
                <h3 style={{ fontSize: 10.5, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em' }}>
                  Passati
                </h3>
                {past.map((a) => (
                  <div key={a.id} className="row-between" style={{ fontSize: 12 }}>
                    <span className="truncate">{APPT_KIND_LABEL[a.kind]} — {a.reason}</span>
                    <span className="muted">{formatDate(a.scheduled_at)} · {APPT_STATUS_LABEL[a.status]}</span>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-head"><h3>Richiami dell’operatore</h3></div>
          <div className="card-body stack" style={{ gap: 8 }}>
            {pendingFu.length === 0 && (
              <Empty icon="phone">Nessun richiamo in programma.</Empty>
            )}
            {pendingFu.map((f) => (
              <div key={f.id} className="panel-flat accent-info">
                <strong style={{ fontSize: 12.5 }}>{f.reason}</strong>
                <div className="row" style={{ gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
                  <Badge tone={f.overdue ? 'risk' : 'info'} dot>
                    {f.overdue ? 'In ritardo' : relativeDays(`${f.due_on}T12:00:00`)}
                  </Badge>
                  <span className="muted" style={{ fontSize: 11.5 }}>{formatDate(f.due_on)} · via {f.channel}</span>
                </div>
              </div>
            ))}
            {(followUps.data || []).filter((f) => f.status === 'done').slice(0, 4).map((f) => (
              <div key={f.id} className="row-between" style={{ fontSize: 12 }}>
                <span className="truncate">{f.reason}</span>
                <span className="muted">{formatDate(f.completed_at)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {showBook && (
        <Modal
          title="Richiedi un appuntamento"
          onClose={() => setShowBook(false)}
          footer={
            <>
              <button className="btn btn-secondary" onClick={() => setShowBook(false)}>Annulla</button>
              <button className="btn btn-primary" disabled={busy} onClick={book}>Invia richiesta</button>
            </>
          }
        >
          <div className="form-grid">
            <Field label="Tipo">
              <select className="select" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
                {Object.entries(APPT_KIND_LABEL).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
              </select>
            </Field>
            <Field label="Data e ora">
              <input type="datetime-local" className="input" value={form.scheduled_at}
                     onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })} />
            </Field>
            <div style={{ gridColumn: '1 / -1' }}>
              <Field label="Motivo">
                <input className="input" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })}
                       placeholder="es. controllo glicemico trimestrale" />
              </Field>
            </div>
          </div>
          <p className="reference-note" style={{ marginTop: 10 }}>
            La richiesta nasce con stato “da confermare”: l’operatore la confermerà dopo la verifica
            della disponibilità dell’ambulatorio.
          </p>
          {error && <p className="error-text" style={{ marginTop: 10 }}>{error}</p>}
        </Modal>
      )}

      <ConfirmDialog
        open={!!cancelFor} tone="danger" confirmLabel="Annulla appuntamento"
        title="Annullare questo appuntamento?"
        message={cancelFor ? `${APPT_KIND_LABEL[cancelFor.kind]} del ${formatDateTime(cancelFor.scheduled_at)} verrà annullato e l'operatore ne verrà informato.` : ''}
        onConfirm={() => cancel(cancelFor)}
        onCancel={() => setCancelFor(null)}
      />

      <style>{`@media (max-width: 980px) { .appt-grid { grid-template-columns: 1fr !important; } }`}</style>
    </div>
  )
}
