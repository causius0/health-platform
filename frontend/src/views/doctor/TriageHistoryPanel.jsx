/** Triage history for one worker, with the collected answers. */
import { useState } from 'react'
import * as api from '../../lib/api'
import { formatDateTime } from '../../lib/format'
import { TierBadge } from '../../components/ui'
import { useAsync } from '../../lib/useAsync'

export default function TriageHistoryPanel({ patientId }) {
  const records = useAsync(() => api.getTriageHistory(patientId), [patientId])
  const [expanded, setExpanded] = useState(null)

  return (
    <div className="section">
      <div className="card">
        <div className="card-head"><h3>Chiamate e valutazioni di triage</h3></div>
        <div className="card-body stack" style={{ gap: 9 }}>
          {(records.data || []).length === 0 && (
            <p className="muted" style={{ fontSize: 12.5 }}>Nessuna chiamata registrata per questo lavoratore.</p>
          )}
          {(records.data || []).map((r) => (
            <div key={r.id} className="panel-flat">
              <div className="row-between wrap" style={{ gap: 8 }}>
                <div>
                  <div className="row" style={{ gap: 8 }}>
                    <TierBadge tier={r.tier} />
                    <strong style={{ fontSize: 12.5 }}>{r.complaint_label}</strong>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--ink-2)', marginTop: 4 }}>{r.disposition_label}</div>
                  <div style={{ fontSize: 11, color: 'var(--faint)', marginTop: 2 }}>
                    {formatDateTime(r.created_at)}
                    {r.risk_level_at_triage && <> · rischio {r.risk_level_at_triage}</>}
                  </div>
                </div>
                <button className="btn btn-secondary btn-sm"
                        onClick={() => setExpanded(expanded === r.id ? null : r.id)}>
                  {expanded === r.id ? 'Nascondi dettagli' : 'Dettagli'}
                </button>
              </div>

              {expanded === r.id && (
                <div style={{ marginTop: 10, borderTop: '1px dashed var(--border)', paddingTop: 10 }}>
                  <table className="table" style={{ fontSize: 12 }}>
                    <tbody>
                      {r.answers.map((a) => (
                        <tr key={a.id}>
                          <td style={{ width: '70%' }}>{a.question}</td>
                          <td style={{ fontWeight: 650 }}>{a.option_label}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {r.red_flags?.length > 0 && (
                    <div className="alert-item critical" style={{ marginTop: 8 }}>
                      <div>
                        <strong>Segni d’allarme:</strong> {r.red_flags.join('; ')}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
