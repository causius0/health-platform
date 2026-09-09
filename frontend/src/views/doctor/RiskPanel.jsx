/** Full risk stratification: component breakdown with thresholds, literature
 * references, recomputation and audit history. */
import { useCallback, useState } from 'react'
import * as api from '../../lib/api'
import { formatDateTime, RISK_LEVEL_LABEL } from '../../lib/format'
import { Badge } from '../../components/ui'
import { useAsync } from '../../lib/useAsync'

const STATE_LABEL = { risk: 'Rischio', protective: 'Protettivo', borderline: 'Da monitorare', unknown: 'N/D' }
const BADGE_OF = { risk: 'badge-risk', protective: 'badge-ok', borderline: 'badge-warn', unknown: 'badge-neutral' }
const DOMAIN_LABEL = { clinico: 'Parametri clinici', stile_di_vita: 'Stile di vita', lavoro: 'Lavoro', storia_clinica: 'Storia clinica' }

export default function RiskPanel({ patientId, onRiskUpdated }) {
  const risk = useAsync(() => api.getRisk(patientId), [patientId])
  const [history, setHistory] = useState([])
  const [recomputing, setRecomputing] = useState(false)
  const [showHistory, setShowHistory] = useState(false)

  const loadHistory = useCallback(async () => {
    setHistory(await api.getRiskHistory(patientId))
  }, [patientId])

  async function recompute() {
    setRecomputing(true)
    try {
      const updated = await api.recomputeRisk(patientId)
      risk.setData(updated)
      setHistory(await api.getRiskHistory(patientId))
      onRiskUpdated?.(updated)
    } finally {
      setRecomputing(false)
    }
  }

  const data = risk.data
  if (!data) return null

  const groups = Object.entries(
    data.components.reduce((acc, c) => { (acc[c.domain] ||= []).push(c); return acc }, {}),
  )

  return (
    <div className="section">
      <div className="card">
        <div className="card-head">
          <div className="row" style={{ gap: 10 }}>
            <h3>Stratificazione del rischio</h3>
            <RiskBadgeSmall level={data.level} />
            {data.has_critical && <span className="badge badge-risk">Valore critico presente</span>}
          </div>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn btn-secondary btn-sm" onClick={() => { setShowHistory(!showHistory); if (!showHistory) loadHistory() }}>
              Storico
            </button>
            <button className="btn btn-primary btn-sm" disabled={recomputing} onClick={recompute}>
              {recomputing ? 'Ricalcolo…' : 'Ricalcola'}
            </button>
          </div>
        </div>
        <div className="card-body">
          <div className="row wrap" style={{ gap: 8, marginBottom: 14 }}>
            <span className="chip"><strong style={{ color: 'var(--risk)' }}>{data.risk_count}</strong>&nbsp;attivi</span>
            <span className="chip"><strong style={{ color: 'var(--ok)' }}>{data.protective_count}</strong>&nbsp;protettivi</span>
            <span className="chip"><strong>{data.borderline_count}</strong>&nbsp;vicini alla soglia</span>
            <span className="chip">Regola: <strong>≥ 4 fattori → alto</strong> · 2–3 → medio · 0–1 → basso</span>
            <span className="chip">{data.model_version}</span>
          </div>

          {groups.map(([domain, items]) => (
            <div key={domain} style={{ marginBottom: 12 }}>
              <h3 style={{ fontSize: 11, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 5 }}>
                {DOMAIN_LABEL[domain] || domain}
              </h3>
              <table className="table">
                <thead>
                  <tr><th>Fattore</th><th>Stato</th><th>Valore</th><th>Soglia di rischio</th><th>Criterio protettivo</th><th>Fonte</th></tr>
                </thead>
                <tbody>
                  {items.map((c) => (
                    <tr key={c.code}>
                      <td style={{ fontWeight: 650 }}>{c.label}</td>
                      <td><span className={`badge ${BADGE_OF[c.state]}`}><span className="dot" />{STATE_LABEL[c.state]}</span></td>
                      <td className="num">{c.value_text}</td>
                      <td className="muted" style={{ fontSize: 11.5 }}>{c.threshold_text || '—'}</td>
                      <td className="muted" style={{ fontSize: 11.5 }}>{c.protective_threshold_text || '—'}</td>
                      <td style={{ fontSize: 11, color: 'var(--faint)', maxWidth: 220 }}>{c.reference || c.protective_reference || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}

          <div className="panel-flat accent-brand">
            <strong style={{ fontSize: 12 }}>Azioni consigliate</strong>
            <ul style={{ margin: '5px 0 0', paddingLeft: 18, fontSize: 12 }}>
              {data.recommendations.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          </div>
        </div>
      </div>

      {showHistory && (
        <div className="card">
          <div className="card-head"><h3>Storico valutazioni (audit)</h3></div>
          <div className="card-body">
            <table className="table">
              <thead><tr><th>Data</th><th>Livello</th><th>Rischi</th><th>Protettivi</th><th>Modello</th></tr></thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.computed_at}>
                    <td>{formatDateTime(h.computed_at)}</td>
                    <td><Badge tone={h.level === 'alto' ? 'risk' : h.level === 'medio' ? 'warn' : 'ok'} dot>{RISK_LEVEL_LABEL[h.level]}</Badge></td>
                    <td className="num">{h.risk_count}</td>
                    <td className="num">{h.protective_count}</td>
                    <td className="muted" style={{ fontSize: 11.5 }}>{h.model_version}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function RiskBadgeSmall({ level }) {
  return <span className={`badge level-${level}`}><span className="dot" />{RISK_LEVEL_LABEL[level]}</span>
}
