/** Care management: goals, follow-ups, appointments (create / confirm / complete). */
import { useState } from 'react'
import * as api from '../../lib/api'
import {
  APPT_KIND_LABEL, APPT_STATUS_LABEL, formatDate, formatDateTime, GOAL_AREA_LABEL,
} from '../../lib/format'
import { Badge, ConfirmDialog, Field } from '../../components/ui'
import { useAsync } from '../../lib/useAsync'

export default function CarePanel({ patientId, onChange }) {
  const meds = useAsync(() => api.getMedications(patientId), [patientId])
  const [newMed, setNewMed] = useState({ name: '', dosage: '', schedule: '' })
  const goals = useAsync(() => api.getGoals(patientId), [patientId])
  const followUps = useAsync(() => api.getFollowUps(patientId), [patientId])
  const appts = useAsync(() => api.getAppointments(patientId), [patientId])

  const [showFu, setShowFu] = useState(false)
  const [fu, setFu] = useState({ reason: '', due_on: '', channel: 'chiamata' })
  const [showAppt, setShowAppt] = useState(false)
  const [outcomeFor, setOutcomeFor] = useState(null)
  const [outcomeText, setOutcomeText] = useState('')
  const fuForId = outcomeFor?.id ?? null
  const [completeFor, setCompleteFor] = useState(null)
  const [appt, setAppt] = useState({ kind: 'visita_ambulatoriale', reason: '', priority: 'routine', scheduled_at: '', location: '' })

  async function addFollowUp() {
    if (!fu.reason || !fu.due_on) return
    await api.createFollowUp(patientId, fu)
    setShowFu(false)
    setFu({ reason: '', due_on: '', channel: 'chiamata' })
    await followUps.reload()
    onChange?.()
  }

  async function completeFu() {
    const outcome = outcomeText
    setOutcomeFor(null)
    setOutcomeText('')
    await api.updateFollowUp(fuForId, { status: 'done', outcome })
    await followUps.reload()
    onChange?.()
  }

  async function addAppointment() {
    if (!appt.reason || !appt.scheduled_at) return
    await api.createAppointment(patientId, { ...appt, scheduled_at: new Date(appt.scheduled_at).toISOString() })
    setShowAppt(false)
    setAppt({ kind: 'visita_ambulatoriale', reason: '', priority: 'routine', scheduled_at: '', location: '' })
    await appts.reload()
    onChange?.()
  }

  async function setApptStatus(a, status) {
    await api.updateAppointment(a.id, { status })
    await appts.reload()
    onChange?.()
  }

  const openAppts = (appts.data || [])
    .filter((a) => ['proposto', 'confermato'].includes(a.status))
    .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))

  // agenda: upcoming appointments grouped by day
  const agenda = openAppts.reduce((acc, a) => {
    const day = a.scheduled_at.slice(0, 10)
    ;(acc[day] ||= []).push(a)
    return acc
  }, {})

  return (
    <div className="section">
      {/* follow-ups */}
      <div className="card">
        <div className="card-head">
          <h3>Follow-up</h3>
          <button className="btn btn-primary btn-sm" onClick={() => setShowFu(!showFu)}>
            {showFu ? 'Chiudi' : 'Programma'}
          </button>
        </div>
        <div className="card-body">
          {showFu && (
            <div className="panel-flat" style={{ marginBottom: 12 }}>
              <div className="form-grid">
                <div style={{ gridColumn: '1 / -1' }}>
                  <Field label="Motivo">
                    <input className="input" value={fu.reason} onChange={(e) => setFu({ ...fu, reason: e.target.value })}
                           placeholder="es. verifica aderenza terapia" />
                  </Field>
                </div>
                <Field label="Entro il">
                  <input type="date" className="input" value={fu.due_on} onChange={(e) => setFu({ ...fu, due_on: e.target.value })} />
                </Field>
                <Field label="Canale">
                  <select className="select" value={fu.channel} onChange={(e) => setFu({ ...fu, channel: e.target.value })}>
                    <option value="chiamata">Chiamata</option>
                    <option value="chat">Chat</option>
                    <option value="visita">Visita</option>
                  </select>
                </Field>
              </div>
              <div className="row" style={{ justifyContent: 'flex-end', marginTop: 10 }}>
                <button className="btn btn-primary btn-sm" onClick={addFollowUp}>Programma follow-up</button>
              </div>
            </div>
          )}

          {(followUps.data || []).length > 0 ? (
            <table className="table">
              <thead><tr><th>Scadenza</th><th>Motivo</th><th>Canale</th><th>Stato</th><th /></tr></thead>
              <tbody>
                {(followUps.data || []).slice(0, 8).map((f) => (
                  <tr key={f.id}>
                    <td style={{ whiteSpace: 'nowrap' }}>{formatDate(f.due_on)}</td>
                    <td className="truncate" style={{ fontSize: 12, maxWidth: 260 }}>{f.reason}</td>
                    <td>{f.channel}</td>
                    <td>
                      <Badge tone={f.status === 'done' ? 'ok' : f.status === 'cancelled' ? 'neutral' : f.overdue ? 'risk' : 'warn'}>
                        {f.status === 'pending' ? (f.overdue ? 'in ritardo' : 'in programma') : f.status === 'done' ? 'completato' : 'annullato'}
                      </Badge>
                    </td>
                    <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                      {f.status === 'pending' && (
                        <>
                          <button className="btn btn-primary btn-sm" onClick={() => setOutcomeFor(f)}>Chiudi</button>{' '}
                          <button className="btn btn-secondary btn-sm"
                                  onClick={async () => { await api.updateFollowUp(f.id, { status: 'cancelled' }); await followUps.reload() }}>
                            Annulla
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p className="muted" style={{ fontSize: 12.5 }}>Nessun follow-up programmato.</p>}
        </div>
      </div>

      {/* appointments */}
      <div className="card">
        <div className="card-head">
          <h3>Visite e teleconsulti</h3>
          <button className="btn btn-primary btn-sm" onClick={() => setShowAppt(!showAppt)}>
            {showAppt ? 'Chiudi' : 'Prenota'}
          </button>
        </div>
        <div className="card-body">
          {showAppt && (
            <div className="panel-flat" style={{ marginBottom: 12 }}>
              <div className="form-grid">
                <Field label="Tipo">
                  <select className="select" value={appt.kind} onChange={(e) => setAppt({ ...appt, kind: e.target.value })}>
                    {Object.entries(APPT_KIND_LABEL).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
                  </select>
                </Field>
                <Field label="Priorità">
                  <select className="select" value={appt.priority} onChange={(e) => setAppt({ ...appt, priority: e.target.value })}>
                    <option value="routine">Routine</option>
                    <option value="urgente">Urgente</option>
                  </select>
                </Field>
                <div style={{ gridColumn: '1 / -1' }}>
                  <Field label="Motivo">
                    <input className="input" value={appt.reason} onChange={(e) => setAppt({ ...appt, reason: e.target.value })}
                           placeholder="es. controllo trimestrale" />
                  </Field>
                </div>
                <Field label="Data e ora">
                  <input type="datetime-local" className="input" value={appt.scheduled_at}
                         onChange={(e) => setAppt({ ...appt, scheduled_at: e.target.value })} />
                </Field>
                <Field label="Luogo">
                  <input className="input" value={appt.location || ''} placeholder="Ambulatorio Health Platform"
                         onChange={(e) => setAppt({ ...appt, location: e.target.value })} />
                </Field>
              </div>
              <div className="row" style={{ justifyContent: 'flex-end', marginTop: 10 }}>
                <button className="btn btn-primary btn-sm" onClick={addAppointment}>Prenota</button>
              </div>
            </div>
          )}

          {openAppts.length > 0 && (
          <div className="stack" style={{ gap: 10 }}>
            {Object.entries(agenda).map(([day, items]) => (
              <div key={day}>
                <h4 style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 4 }}>
                  {new Date(day + 'T12:00:00').toLocaleDateString('it-IT', { weekday: 'long', day: '2-digit', month: 'long' })}
                </h4>
                <div className="stack" style={{ gap: 6 }}>
                  {items.map((a) => (
                    <div key={a.id} className="panel-flat">
                      <div className="row-between wrap" style={{ gap: 8 }}>
                        <div>
                          <strong style={{ fontSize: 12.5 }}>{formatDateTime(a.scheduled_at)}</strong>{' '}
                          <span className="muted" style={{ fontSize: 12 }}>{APPT_KIND_LABEL[a.kind]}</span>
                          <div className="truncate muted" style={{ fontSize: 11.5, maxWidth: 320 }}>
                            {a.reason} {a.priority === 'urgente' && <Badge tone="warn">urgente</Badge>}
                          </div>
                        </div>
                        <div className="row" style={{ gap: 6 }}>
                          <Badge tone={a.status === 'confermato' ? 'ok' : 'warn'}>{APPT_STATUS_LABEL[a.status]}</Badge>
                          <Badge>{a.created_via}</Badge>
                          {a.status === 'proposto' && (
                            <button className="btn btn-primary btn-sm" onClick={() => setApptStatus(a, 'confermato')}>Conferma</button>
                          )}
                          <button className="btn btn-secondary btn-sm" onClick={() => setApptStatus(a, 'completato')}>Completata</button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {(appts.data || []).filter((a) => !['proposto', 'confermato'].includes(a.status)).length > 0 && (
          <>
            <hr className="divider" />
            <h4 style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 4 }}>
              Storico
            </h4>
            <table className="table">
              <tbody>
                {(appts.data || []).filter((a) => !['proposto', 'confermato'].includes(a.status)).slice(0, 8).map((a) => (
                  <tr key={a.id}>
                    <td style={{ whiteSpace: 'nowrap' }}>{formatDateTime(a.scheduled_at)}</td>
                    <td>{APPT_KIND_LABEL[a.kind]}</td>
                    <td className="truncate" style={{ fontSize: 12, maxWidth: 220 }}>{a.reason}</td>
                    <td>
                      <Badge tone={a.status === 'completato' ? 'ok' : 'neutral'}>{APPT_STATUS_LABEL[a.status]}</Badge>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      {a.status === 'completato' && a.outcome && <span className="muted" style={{ fontSize: 11 }}>{a.outcome}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {openAppts.length === 0 && (appts.data || []).length === 0 && <p className="muted" style={{ fontSize: 12.5 }}>Nessuna visita programmata.</p>}
        </div>
      </div>

      {/* therapy */}
      <div className="card">
        <div className="card-head">
          <h3>Terapia in corso</h3>
          <span className="hint">Gestita dall'operatore, visibile al lavoratore</span>
        </div>
        <div className="card-body">
          <div className="form-row" style={{ marginBottom: 10, flexWrap: 'wrap' }}>
            <input className="input" style={{ maxWidth: 220 }} placeholder="Farmaco (es. Metformina)"
                   value={newMed.name} onChange={(e) => setNewMed({ ...newMed, name: e.target.value })} />
            <input className="input" style={{ maxWidth: 130 }} placeholder="Dosaggio"
                   value={newMed.dosage} onChange={(e) => setNewMed({ ...newMed, dosage: e.target.value })} />
            <input className="input" style={{ maxWidth: 130 }} placeholder="Posologia"
                   value={newMed.schedule} onChange={(e) => setNewMed({ ...newMed, schedule: e.target.value })} />
            <button className="btn btn-primary btn-sm" disabled={!newMed.name.trim()}
                    onClick={async () => {
                      await api.addMedication(patientId, newMed)
                      setNewMed({ name: '', dosage: '', schedule: '' })
                      await meds.reload()
                    }}>
              Aggiungi
            </button>
          </div>
          <table className="table">
            <thead><tr><th>Farmaco</th><th>Dosaggio</th><th>Posologia</th><th>Stato</th><th /></tr></thead>
            <tbody>
              {(meds.data || []).map((m) => (
                <tr key={m.id}>
                  <td style={{ fontWeight: 650 }}>{m.name}</td>
                  <td>{m.dosage || '—'}</td>
                  <td>{m.schedule || '—'}</td>
                  <td><Badge tone={m.active ? 'ok' : 'neutral'}>{m.active ? 'in corso' : 'sospeso'}</Badge></td>
                  <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                    <button className="btn btn-secondary btn-sm"
                            onClick={async () => { await api.updateMedication(m.id, { active: !m.active }); await meds.reload() }}>
                      {m.active ? 'Sospendi' : 'Riattiva'}
                    </button>{' '}
                    <button className="btn btn-danger btn-sm"
                            onClick={async () => { await api.deleteMedication(m.id); await meds.reload() }}>
                      Elimina
                    </button>
                  </td>
                </tr>
              ))}
              {(meds.data || []).length === 0 && <tr><td colSpan={5} className="muted">Nessun farmaco registrato.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      {/* goals */}
      <div className="card">
        <div className="card-head"><h3>Obiettivi del lavoratore</h3></div>
        <div className="card-body stack" style={{ gap: 8 }}>
          {(goals.data || []).length === 0 && <p className="muted" style={{ fontSize: 12.5 }}>Nessun obiettivo attivo.</p>}
          {(goals.data || []).map((g) => (
            <div key={g.id} className="row-between panel-flat">
              <div>
                <strong style={{ fontSize: 12.5 }}>{g.title}</strong>
                <div className="row" style={{ gap: 8, marginTop: 2 }}>
                  <Badge>{GOAL_AREA_LABEL[g.area]}</Badge>
                  <span className="muted" style={{ fontSize: 11.5 }}>{g.frequency_per_week}x/settimana</span>
                  {g.created_by === 'doctor' && <Badge tone="info">operatore</Badge>}
                </div>
              </div>
              <button className="btn btn-secondary btn-sm"
                      onClick={async () => {
                        await api.updateGoal(g.id, { status: g.status === 'active' ? 'completed' : 'active' })
                        await goals.reload()
                      }}>
                {g.status === 'active' ? 'Archivia' : 'Riattiva'}
              </button>
            </div>
          ))}
        </div>
      </div>
      <ConfirmDialog
        open={!!completeFor} input confirmLabel="Completa e documenta"
        title="Completare la visita"
        message="La nota clinica viene registrata come incontro nel diario del lavoratore e, per le tappe di percorso, chiude la tappa associata."
        busy={false}
        onConfirm={async (note) => {
          await api.updateAppointment(completeFor.id, { status: 'completato', clinical_note: note })
          setCompleteFor(null)
          await appts.reload()
          onChange?.()
        }}
        onCancel={() => setCompleteFor(null)}
      />

      <ConfirmDialog
        open={!!outcomeFor} input confirmLabel="Registra esito"
        title="Chiudere il follow-up"
        message="Registra l'esito del contatto: resterà nello storico del lavoratore."
        busy={false}
        onConfirm={completeFu}
        onCancel={() => { setOutcomeFor(null); setOutcomeText('') }}
      />
    </div>
  )
}
