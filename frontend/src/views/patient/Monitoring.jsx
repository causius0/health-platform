/** Remote monitoring: care plan, home measurements, trends. */
import { useCallback, useState } from 'react'
import * as api from '../../lib/api'
import { formatDate } from '../../lib/format'
import { Badge, Empty, Field, Modal } from '../../components/ui'
import TrendChart from '../../components/TrendChart'
import { useAsync } from '../../lib/useAsync'

const EXTRA_METRICS = [
  { code: 'weight', label: 'Peso' },
  { code: 'bp_systolic', label: 'Pressione sistolica' },
  { code: 'bp_diastolic', label: 'Pressione diastolica' },
  { code: 'glucose_fasting', label: 'Glicemia a digiuno' },
  { code: 'waist', label: 'Circonferenza vita' },
]

function RecordModal({ patientId, initialCode, plan, onClose, onSaved }) {
  const [code, setCode] = useState(initialCode || '')
  const [value, setValue] = useState('')
  const [takenOn, setTakenOn] = useState(new Date().toISOString().slice(0, 10))
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const options = [
    ...plan.map((item) => ({ code: item.code, label: item.label })),
    ...EXTRA_METRICS.filter((m) => !plan.some((item) => item.code === m.code)),
  ]

  async function save() {
    if (!code || value === '') { setError('Compila metrica e valore.'); return }
    setBusy(true)
    try {
      const res = await api.addObservation(patientId, {
        code, value: Number(value), taken_on: takenOn, source: 'patient_home',
      })
      onSaved(res)
    } catch (e) {
      setError(e.message)
      setBusy(false)
    }
  }

  return (
    <Modal
      title="Registra una misurazione"
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
          <select className="select" value={code} onChange={(e) => setCode(e.target.value)}>
            <option value="" disabled>Scegli…</option>
            {options.map((m) => <option key={m.code} value={m.code}>{m.label}</option>)}
          </select>
        </Field>
        <Field label="Valore">
          <input type="number" step="0.1" className="input" value={value}
                 onChange={(e) => setValue(e.target.value)} placeholder="es. 128" />
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

export default function Monitoring({ patientId, onRiskUpdated }) {
  const plan = useAsync(() => api.getMonitoring(patientId), [patientId])
  const observations = useAsync(() => api.getObservations(patientId, 12), [patientId])
  const [showRecord, setShowRecord] = useState(false)
  const [initialCode, setInitialCode] = useState('')

  const refresh = useCallback(async (res) => {
    setShowRecord(false)
    await Promise.all([plan.reload(), observations.reload()])
    if (res?.risk) onRiskUpdated?.(res.risk)
  }, [plan, observations, onRiskUpdated])

  function openRecord(code = '') {
    setInitialCode(code)
    setShowRecord(true)
  }

  const homeReadings = (observations.data || []).filter((o) => o.source === 'patient_home').slice(0, 8)

  return (
    <div className="section">
      <div className="card">
        <div className="card-head">
          <h3>Piano di monitoraggio</h3>
          <span className="hint">Concordato con l’operatore sanitario</span>
        </div>
        <div className="card-body">
          {(plan.data || []).length === 0 && (
            <Empty icon="monitor">
              Nessun piano di monitoraggio attivo: l’operatore lo definisce insieme a te in
              base al tuo percorso.
            </Empty>
          )}
          <div className="stack" style={{ gap: 9 }}>
            {(plan.data || []).map((item) => (
              <div key={item.id} className="panel-flat">
                <div className="row-between wrap" style={{ gap: 8 }}>
                  <div>
                    <strong style={{ fontSize: 12.5 }}>{item.label}</strong>
                    <span className="muted" style={{ fontSize: 12 }}> · ogni {item.frequency_days} giorni</span>
                    {item.target_text && (
                      <div style={{ fontSize: 12, color: 'var(--ink-2)', marginTop: 2 }}>
                        Obiettivo: {item.target_text}
                      </div>
                    )}
                  </div>
                  <div className="row" style={{ gap: 10 }}>
                    <div style={{ textAlign: 'right' }}>
                      {item.last_value !== null && (
                        <div style={{ fontWeight: 750 }}>
                          {item.last_value} <span className="muted" style={{ fontSize: 10.5, fontWeight: 500 }}>{item.unit}</span>
                        </div>
                      )}
                      {item.last_taken_on && <div style={{ fontSize: 10.5, color: 'var(--faint)' }}>{formatDate(item.last_taken_on)}</div>}
                    </div>
                    <button className="btn btn-primary btn-sm" onClick={() => openRecord(item.code)}>Registra</button>
                  </div>
                </div>
                {item.overdue && (
                  <div style={{ marginTop: 6 }}>
                    <Badge tone="warn" dot>Misurazione in ritardo</Badge>
                  </div>
                )}
              </div>
            ))}
          </div>
          <button className="btn btn-secondary btn-sm" style={{ marginTop: 12 }} onClick={() => openRecord()}>
            Registra una misura libera
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-head"><h3>Andamento nel tempo</h3></div>
        <div className="card-body">
          <TrendChart observations={observations.data || []} />
        </div>
      </div>

      {homeReadings.length > 0 && (
        <div className="card">
          <div className="card-head"><h3>Ultime misurazioni a domicilio</h3></div>
          <div className="card-body">
            <table className="table">
              <thead><tr><th>Metrica</th><th>Valore</th><th>Data</th><th>Fonte</th></tr></thead>
              <tbody>
                {homeReadings.map((o) => (
                  <tr key={o.id}>
                    <td>{o.label}</td>
                    <td className="num"><strong>{o.value}</strong> <span className="muted">{o.unit}</span></td>
                    <td>{formatDate(o.taken_on)}</td>
                    <td><Badge>domicilio</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showRecord && (
        <RecordModal
          patientId={patientId}
          initialCode={initialCode}
          plan={plan.data || []}
          onClose={() => setShowRecord(false)}
          onSaved={refresh}
        />
      )}
    </div>
  )
}
