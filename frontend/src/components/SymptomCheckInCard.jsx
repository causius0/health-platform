/** Daily symptom check-in (COVIDApp-style traffic light): worker self-report
 * with immediate verde/arancione/rosso feedback and operator alerting. */
import { useMemo, useState } from 'react'
import * as api from '../lib/api'
import Icon from './Icon'
import { Badge } from './ui'
import { useAsync } from '../lib/useAsync'

const TIER_STYLE = {
  rosso: { cls: 'badge-risk', label: 'Rosso — allerta' },
  arancione: { cls: 'badge-warn', label: 'Arancione — attenzione' },
  verde: { cls: 'badge-ok', label: 'Verde — tutto ok' },
}

export default function SymptomCheckInCard({ patientId, onSubmitted }) {
  const questions = useAsync(() => api.getSymptomQuestions(), [])
  const history = useAsync(() => api.getSymptomCheckins(patientId), [patientId])
  const [answers, setAnswers] = useState({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const today = new Date().toISOString().slice(0, 10)
  const todayEntry = useMemo(
    () => (history.data || []).find((r) => r.taken_on === today),
    [history.data, today],
  )

  // editing mode: explicit user intent or first compilation of the day
  const [editing, setEditing] = useState(false)
  const showForm = editing || !todayEntry

  async function submit() {
    setError('')
    if (Object.keys(answers).length < questions.data?.length) {
      setError('Rispondi a tutte le domande.')
      return
    }
    setBusy(true)
    try {
      const payload = await api.submitSymptomCheckin(patientId, answers)
      setResult(payload)
      setAnswers({})
      await history.reload()
      onSubmitted?.(payload)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card" style={{ borderTop: '3px solid var(--brand)' }}>
      <div className="card-head">
        <div className="row" style={{ gap: 10 }}>
          <h3>Check-in sintomi di oggi</h3>
          {todayEntry && <Badge tone={todayEntry.tier === 'verde' ? 'ok' : todayEntry.tier === 'rosso' ? 'risk' : 'warn'} dot>
            {TIER_STYLE[todayEntry.tier]?.label}
          </Badge>}
        </div>
        <span className="hint">30 secondi · i sintomi importanti avvisano l'operatore</span>
      </div>
      <div className="card-body">
        {!showForm && todayEntry ? (
          <div className="stack" style={{ gap: 8 }}>
            <p style={{ fontSize: 13 }}>
              Check-in di oggi registrato: <Badge tone={todayEntry.tier === 'verde' ? 'ok' : todayEntry.tier === 'rosso' ? 'risk' : 'warn'}>
                {TIER_STYLE[todayEntry.tier]?.label}
              </Badge>
            </p>
            <p className="muted" style={{ fontSize: 12.5 }}>{todayEntry.advice}</p>
            <button className="btn btn-secondary btn-sm" style={{ alignSelf: 'flex-start' }}
                    onClick={() => { setAnswers({}); setEditing(true) }}>
              Aggiorna il check-in
            </button>
          </div>
        ) : result && !showForm ? (
          <div className="stack" style={{ gap: 8 }}>
            <div className="row" style={{ gap: 10 }}>
              <span className={`badge ${TIER_STYLE[result.tier]?.cls}`} style={{ fontSize: 14, padding: '4px 14px' }}>
                <span className="dot" />{TIER_STYLE[result.tier]?.label}
              </span>
            </div>
            <p style={{ fontSize: 13 }}>{result.advice}</p>
            {result.detail && <p className="muted" style={{ fontSize: 12.5 }}>{result.detail}</p>}
            {result.operator_alerted && (
              <div className="alert-item info">
                <span style={{ color: 'var(--info)' }}><Icon name="bell" size={15} /></span>
                <span style={{ fontSize: 12.5 }}>
                  L'operatore sanitario è stato avvisato{result.followup_scheduled ? ' e ti richiama entro domani' : ''}.
                </span>
              </div>
            )}
          </div>
        ) : (
          <div className="stack" style={{ gap: 12 }}>
            {questions.data?.map((q) => (
              <div key={q.id} className="field">
                <label>{q.text}</label>
                <div className="row wrap" style={{ gap: 6 }}>
                  {q.options.map((o) => (
                    <button key={o.value} type="button" className="chip"
                            style={answers[q.id] === o.value
                              ? { borderColor: 'var(--brand)', color: 'var(--brand-strong)', fontWeight: 650 }
                              : undefined}
                            onClick={() => setAnswers({ ...answers, [q.id]: o.value })}>
                      {o.label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {error && <p className="error-text">{error}</p>}
            <button className="btn btn-primary btn-sm" style={{ alignSelf: 'flex-start' }} disabled={busy} onClick={submit}>
              {busy ? 'Invio…' : 'Invia check-in'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
