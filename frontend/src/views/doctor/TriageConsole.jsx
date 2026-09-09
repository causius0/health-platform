/** Triage console: guided diagnostic algorithm for the operator on a call.
 * Traffic-light outcome (rosso/arancione/verde) with automatic booking of
 * urgent visits, teleconsults or safety-net follow-up calls. */
import { useEffect, useState } from 'react'
import * as api from '../../lib/api'
import { formatDate } from '../../lib/format'
import Icon from '../../components/Icon'
import { Modal, TierBadge } from '../../components/ui'

const YES_NO = [{ value: 'no', label: 'No' }, { value: 'sì', label: 'Sì' }]

export default function TriageConsole({ onClose, onCompleted }) {
  const [patients, setPatients] = useState([])
  const [protocols, setProtocols] = useState([])
  const [step, setStep] = useState('setup') // setup | questions | result
  const [patientId, setPatientId] = useState(null)
  const [protocol, setProtocol] = useState(null)
  const [answers, setAnswers] = useState({})
  const [index, setIndex] = useState(0)
  const [result, setResult] = useState(null)
  const [drafts, setDrafts] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.getDoctorPatients(), api.getTriageProtocols(), api.getTriageDrafts()])
      .then(([p, pr, d]) => { setPatients(p); setProtocols(pr); setDrafts(d); setLoading(false) })
      .catch((e) => { setError(e.message); setLoading(false) })
  }, [])

  async function chooseProtocol(p, presetAnswers = null) {
    setError('')
    try {
      setProtocol(await api.getTriageProtocol(p.code))
      setAnswers(presetAnswers || {})
      const answered = presetAnswers ? Object.keys(presetAnswers).length : 0
      setIndex(Math.min(answered, p.questions ? p.questions.length - 1 : 0))
      setStep('questions')
    } catch (e) { setError(e.message) }
  }

  async function resumeDraft(d) {
    const protocol = await api.getTriageProtocol(d.protocol_code)
    if (d.patient_id) setPatientId(d.patient_id)
    setProtocol(protocol)
    setAnswers(d.answers)
    setIndex(Math.min(Object.keys(d.answers).length, protocol.questions.length - 1))
    setStep('questions')
  }

  async function suspend() {
    try {
      await api.saveTriageDraft({ patient_id: patientId, protocol_code: protocol.code, answers })
      onClose()
    } catch (e) { setError(e.message) }
  }

  async function discardDraft(id) {
    await api.discardTriageDraft(id)
    setDrafts((cur) => cur.filter((d) => d.id !== id))
  }

  const question = protocol?.questions?.[index] || null
  const selectedPatient = patients.find((p) => p.id === patientId)

  async function answer(value) {
    const next = { ...answers, [question.id]: value }
    setAnswers(next)
    // red flags conclude immediately
    if (protocol.red[question.id] && value === 'sì') return finish(next)
    if (index < protocol.questions.length - 1) setIndex(index + 1)
    else return finish(next)
  }

  async function finish(finalAnswers) {
    setError('')
    try {
      const r = await api.submitTriage({
        patient_id: patientId,
        protocol_code: protocol.code,
        answers: finalAnswers,
      })
      setResult(r)
      setStep('result')
      onCompleted?.()
    } catch (e) {
      setError(e.message)
    }
  }

  function resetAll() {
    setStep('setup'); setProtocol(null); setAnswers({}); setResult(null); setIndex(0)
  }

  const optionsOf = (q) => q.options || YES_NO

  return (
    <Modal
      wide
      title="Triage della chiamata"
      onClose={onClose}
      footer={step === 'result' && (
        <>
          <button className="btn btn-secondary" onClick={resetAll}>Nuova chiamata</button>
          <button className="btn btn-primary" onClick={onClose}>Chiudi</button>
        </>
      )}
    >
      {loading && <p className="muted">Caricamento…</p>}

      {step === 'setup' && !loading && (
        <>
          <p className="muted" style={{ fontSize: 12.5, marginBottom: 14 }}>
            Seleziona il lavoratore e il motivo della chiamata: l’algoritmo guida la raccolta
            delle informazioni e suggerisce il percorso (verde / arancione / rosso), prenotando
            automaticamente visita o teleconsulto quando necessario.
          </p>
          <div className="form-grid">
            <div className="field">
              <label>Lavoratore</label>
              <select className="select" value={patientId ?? ''} onChange={(e) => setPatientId(e.target.value ? Number(e.target.value) : null)}>
                <option value="">Chiamata anonima / non in carico</option>
                {patients.map((p) => <option key={p.id} value={p.id}>{p.full_name}</option>)}
              </select>
            </div>
            {selectedPatient && (
              <div className="field">
                <label>&nbsp;</label>
                <div className="row">
                  <span className={`badge level-${selectedPatient.risk_level}`}>Rischio {selectedPatient.risk_level}</span>
                  <span className="muted" style={{ fontSize: 11.5 }}>{selectedPatient.primary_diagnosis}</span>
                </div>
              </div>
            )}
          </div>

          {drafts.length > 0 && (
            <>
              <h3 style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em', margin: '16px 0 8px' }}>
                Chiamate sospese
              </h3>
              <div className="stack" style={{ gap: 6, marginBottom: 14 }}>
                {drafts.map((d) => (
                  <div key={d.id} className="panel-flat row-between" style={{ gap: 8 }}>
                    <span style={{ fontSize: 12.5 }}>
                      <strong>{d.complaint_label}</strong>
                      <span className="muted"> · {Object.keys(d.answers).length} risposte raccolte</span>
                    </span>
                    <span className="row" style={{ gap: 6 }}>
                      <button className="btn btn-primary btn-sm" onClick={() => resumeDraft(d)}>Riprendi</button>
                      <button className="btn btn-danger btn-sm" onClick={() => discardDraft(d.id)}>Scarta</button>
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}

          <h3 style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em', margin: '16px 0 8px' }}>
            Motivo della chiamata
          </h3>
          <div className="stack" style={{ gap: 6 }}>
            {protocols.map((p) => (
              <button key={p.code} className="option-item" style={{ textAlign: 'left' }} onClick={() => chooseProtocol(p)}>
                <div>
                  <strong style={{ fontSize: 12.5 }}>{p.label}</strong>
                  <div className="muted" style={{ fontSize: 11.5 }}>{p.description}</div>
                </div>
                <span style={{ marginLeft: 'auto', color: 'var(--faint)', fontSize: 11.5 }}>{p.n_questions} domande →</span>
              </button>
            ))}
          </div>
          {error && <p className="error-text" style={{ marginTop: 10 }}>{error}</p>}
        </>
      )}

      {step === 'questions' && question && (
        <>
          <div className="progress" style={{ marginBottom: 14 }}>
            <div className="bar" style={{ width: `${((index + 1) / protocol.questions.length) * 100}%` }} />
          </div>
          <p style={{ fontSize: 11.5, color: 'var(--muted)' }}>
            Domanda {index + 1} di {protocol.questions.length}
          </p>
          <h2 style={{ fontSize: 16.5, margin: '8px 0 16px', maxWidth: 560 }}>{question.text}</h2>
          <div className="row" style={{ gap: 10 }}>
            {optionsOf(question).map((o) => (
              <button key={o.value}
                      className={`btn ${o.value === 'sì' ? 'btn-danger' : 'btn-primary'}`}
                      style={{ minWidth: 110 }}
                      onClick={() => answer(o.value)}>
                {o.label}
              </button>
            ))}
            <span className="grow" />
            <button className="btn btn-secondary" onClick={() => (index > 0 ? setIndex(index - 1) : setStep('setup'))}>
              ← Indietro
            </button>
            <button className="btn btn-secondary" onClick={suspend}>Sospendi</button>
          </div>

          {Object.keys(answers).length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h3 style={{ fontSize: 10.5, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 6 }}>
                Risposte raccolte
              </h3>
              <div className="row wrap" style={{ gap: 6 }}>
                {Object.entries(answers).map(([qid, v]) => (
                  <span key={qid} className="chip">
                    {protocol.questions.find((q) => q.id === qid)?.text.slice(0, 44)}… <strong>{v}</strong>
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {step === 'result' && result && (
        <>
          <div className="row" style={{ gap: 10, marginBottom: 14 }}>
            <TierBadge tier={result.tier} />
            <strong style={{ fontSize: 14.5 }}>{result.disposition_label}</strong>
          </div>

          <div className="panel-flat" style={{ marginBottom: 12 }}>
            <strong style={{ fontSize: 12.5 }}>Cosa comunicare al lavoratore</strong>
            <p style={{ fontSize: 12.5, marginTop: 4 }}>{result.disposition_detail}</p>
            {result.safety_net && (
              <p style={{ fontSize: 12, color: 'var(--warn)', marginTop: 6 }}>
                <Icon name="alert" size={12} style={{ verticalAlign: '-2px', marginRight: 4 }} />
                Istruzioni di sicurezza: {result.safety_net}
              </p>
            )}
          </div>

          {result.red_flags?.length > 0 && (
            <div className="alert-item critical" style={{ marginBottom: 12 }}>
              <span style={{ color: 'var(--risk)' }}><Icon name="alert" size={16} /></span>
              <div>
                <strong>Segni d’allarme rilevati</strong>
                <ul style={{ margin: '4px 0 0', paddingLeft: 18, fontSize: 12 }}>
                  {result.red_flags.map((f) => <li key={f}>{f}</li>)}
                </ul>
              </div>
            </div>
          )}

          <div className="stack" style={{ gap: 8 }}>
            {result.appointment && (
              <div className="panel-flat accent-brand">
                <strong style={{ fontSize: 12.5 }}>Appuntamento prenotato automaticamente</strong>
                <div style={{ fontSize: 12, color: 'var(--ink-2)', marginTop: 2 }}>
                  {result.appointment.kind === 'teleconsulto' ? 'Teleconsulto' : 'Visita ambulatoriale'} ·
                  priorità {result.appointment.priority} · {result.appointment.location}
                </div>
                <div style={{ fontSize: 11.5, color: 'var(--muted)' }}>{formatDate(result.appointment.scheduled_at)}</div>
              </div>
            )}
            {result.follow_up && (
              <div className="panel-flat accent-info">
                <strong style={{ fontSize: 12.5 }}>Follow-up di sicurezza programmato</strong>
                <div style={{ fontSize: 12, color: 'var(--ink-2)', marginTop: 2 }}>
                  Richiamo entro il {formatDate(result.follow_up.due_on)} — {result.follow_up.reason}
                </div>
              </div>
            )}
            <div className="row wrap" style={{ gap: 6 }}>
              {result.risk_level_at_triage && <span className="badge badge-neutral">Stratificazione alla chiamata: {result.risk_level_at_triage}</span>}
              {result.trail.map((t, i) => <span key={i} className="muted" style={{ fontSize: 11.5 }}>{t}</span>)}
            </div>
          </div>
          {error && <p className="error-text" style={{ marginTop: 10 }}>{error}</p>}
        </>
      )}
    </Modal>
  )
}
