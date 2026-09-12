/** Doctor monitoring view: plan management, observations, clinical encounters. */
import { useState } from 'react'
import * as api from '../../lib/api'
import { formatDate } from '../../lib/format'
import { Badge, Field, Modal } from '../../components/ui'
import TrendChart from '../../components/TrendChart'
import DeltaLine from '../../components/DeltaLine'
import { useAsync } from '../../lib/useAsync'

const METRIC_OPTIONS = [
  { code: 'bp_systolic', label: 'Pressione sistolica' },
  { code: 'bp_diastolic', label: 'Pressione diastolica' },
  { code: 'glucose_fasting', label: 'Glicemia a digiuno' },
  { code: 'hba1c', label: 'HbA1c' },
  { code: 'weight', label: 'Peso' },
  { code: 'waist', label: 'Circonferenza vita' },
]

export default function MonitoringPanel({ patientId }) {
  const plan = useAsync(() => api.getMonitoring(patientId), [patientId])
  const observations = useAsync(() => api.getObservations(patientId, 12), [patientId])
  const encounters = useAsync(() => api.getEncounters(patientId), [patientId])
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ code: 'bp_systolic', frequency_days: 7, target_text: '' })
  const [showLab, setShowLab] = useState(false)
  const [lab, setLab] = useState({ code: 'hba1c', value: '', taken_on: new Date().toISOString().slice(0, 10) })
  const [showEncounter, setShowEncounter] = useState(false)
  const [enc, setEnc] = useState({ kind: 'controllo', encounter_date: new Date().toISOString().slice(0, 10), notes: '', diagnosis: '' })
  const [showLabReq, setShowLabReq] = useState(false)
  const [labReqTests, setLabReqTests] = useState([])

  const LAB_REQUEST_TESTS = [
    { code: 'hba1c', label: 'Emoglobina glicata (HbA1c)' },
    { code: 'glucose_fasting', label: 'Glicemia a digiuno' },
    { code: 'ldl', label: 'Colesterolo LDL' },
    { code: 'hdl', label: 'Colesterolo HDL' },
    { code: 'total_cholesterol', label: 'Colesterolo totale' },
    { code: 'triglycerides', label: 'Trigliceridi' },
    { code: 'creatinine', label: 'Creatininemia' },
    { code: 'egfr', label: 'Filtrato glomerulare (eGFR)' },
    { code: 'microalbuminuria', label: 'Microalbuminuria (urine)' },
  ]

  function toggleTest(code) {
    setLabReqTests((cur) => cur.includes(code) ? cur.filter((c) => c !== code) : [...cur, code])
  }

  function printLabRequest() {
    const qs = labReqTests.join(',')
    window.open(`/api/patients/${patientId}/lab-request?tests=${qs}`, '_blank')
  }

  async function addItem() {
    await api.addMonitoring(patientId, form)
    setShowAdd(false)
    setForm({ code: 'bp_systolic', frequency_days: 7, target_text: '' })
    await plan.reload()
  }

  return (
    <div className="section">
      <div className="card">
        <div className="card-head">
          <h3>Piano di monitoraggio remoto</h3>
          <div className="row" style={{ gap: 6 }}>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowLabReq(true)}>
              Richiesta laboratorio
            </button>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowLab(!showLab)}>
              {showLab ? 'Chiudi esame' : 'Registra esame'}
            </button>
            <button className="btn btn-primary btn-sm" onClick={() => setShowAdd(!showAdd)}>
              {showAdd ? 'Chiudi' : 'Aggiungi metrica'}
            </button>
          </div>
        </div>
        <div className="card-body">
          {showAdd && (
            <div className="panel-flat" style={{ marginBottom: 12 }}>
              <div className="form-grid">
                <Field label="Metrica">
                  <select className="select" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })}>
                    {METRIC_OPTIONS.map((m) => <option key={m.code} value={m.code}>{m.label}</option>)}
                  </select>
                </Field>
                <Field label="Frequenza (giorni)">
                  <input type="number" min={1} max={90} className="input" value={form.frequency_days}
                         onChange={(e) => setForm({ ...form, frequency_days: Number(e.target.value) })} />
                </Field>
                <div style={{ gridColumn: '1 / -1' }}>
                  <Field label="Obiettivo (visibile al lavoratore)">
                    <input className="input" value={form.target_text || ''} placeholder="es. media settimanale < 130 mmHg"
                           onChange={(e) => setForm({ ...form, target_text: e.target.value })} />
                  </Field>
                </div>
              </div>
              <div className="row" style={{ justifyContent: 'flex-end', marginTop: 10 }}>
                <button className="btn btn-primary btn-sm" onClick={addItem}>Aggiungi al piano</button>
              </div>
            </div>
          )}

          {(plan.data || []).length > 0 ? (
            <table className="table">
              <thead><tr><th>Metrica</th><th>Frequenza</th><th>Obiettivo</th><th>Ultimo valore</th><th>Stato</th></tr></thead>
              <tbody>
                {(plan.data || []).map((item) => (
                  <tr key={item.id}>
                    <td style={{ fontWeight: 650 }}>{item.label}</td>
                    <td>ogni {item.frequency_days} giorni</td>
                    <td className="muted" style={{ fontSize: 11.5 }}>{item.target_text || '—'}</td>
                    <td className="num">
                      {item.last_value !== null ? (
                        <>
                          <strong>{item.last_value}</strong> <span className="muted">{item.unit}</span>
                          <div style={{ fontSize: 10.5, color: 'var(--faint)' }}>{formatDate(item.last_taken_on)}</div>
                          <DeltaLine observations={observations.data} code={item.code} />
                        </>
                      ) : '—'}
                    </td>
                    <td>
                      {item.overdue
                        ? <Badge tone="risk" dot>in ritardo</Badge>
                        : item.due_on ? <span className="muted" style={{ fontSize: 11.5 }}>entro {formatDate(item.due_on)}</span> : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="muted" style={{ fontSize: 12.5 }}>Nessuna metrica monitorata.</p>
          )}
        </div>
      </div>

      {showLab && (
        <div className="card">
          <div className="card-head"><h3>Registra esame di laboratorio</h3></div>
          <div className="card-body">
            <div className="form-grid">
              <Field label="Analisi">
                <select className="select" value={lab.code} onChange={(e) => setLab({ ...lab, code: e.target.value })}>
                  <option value="hba1c">HbA1c</option>
                  <option value="glucose_fasting">Glicemia a digiuno</option>
                  <option value="ldl">Colesterolo LDL</option>
                  <option value="hdl">Colesterolo HDL</option>
                  <option value="triglycerides">Trigliceridi</option>
                  <option value="total_cholesterol">Colesterolo totale</option>
                  <option value="creatinine">Creatinina</option>
                  <option value="egfr">eGFR</option>
                  <option value="microalbuminuria">Microalbuminuria</option>
                </select>
              </Field>
              <Field label="Valore">
                <input type="number" step="0.1" className="input" value={lab.value}
                       onChange={(e) => setLab({ ...lab, value: e.target.value })} />
              </Field>
              <Field label="Data del prelievo">
                <input type="date" className="input" value={lab.taken_on} max={new Date().toISOString().slice(0, 10)}
                       onChange={(e) => setLab({ ...lab, taken_on: e.target.value })} />
              </Field>
            </div>
            <div className="row" style={{ justifyContent: 'flex-end', marginTop: 10 }}>
              <button className="btn btn-primary btn-sm" disabled={!lab.value}
                      onClick={async () => {
                        await api.addObservation(patientId, {
                          code: lab.code, value: Number(lab.value),
                          taken_on: lab.taken_on, source: 'lab',
                          notes: 'Referto inserito dall\'operatore',
                        })
                        setShowLab(false)
                        setLab({ ...lab, value: '' })
                        await observations.reload()
                      }}>
                Salva referto
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-head">
          <h3>Andamento misurazioni</h3>
          <button className="btn btn-secondary btn-sm" onClick={() => setShowEncounter(!showEncounter)}>
            {showEncounter ? 'Chiudi' : 'Registra incontro'}
          </button>
        </div>
        <div className="card-body"><TrendChart observations={observations.data || []} /></div>
      </div>

      {showLabReq && (
        <Modal title="Richiesta di laboratorio" onClose={() => setShowLabReq(false)}
               footer={
                 <>
                   <button className="btn btn-secondary" onClick={() => setShowLabReq(false)}>Annulla</button>
                   <button className="btn btn-primary" disabled={!labReqTests.length} onClick={printLabRequest}>
                     Stampa richiesta ({labReqTests.length})
                   </button>
                 </>
               }>
          <p className="muted" style={{ fontSize: 12.5, marginBottom: 10 }}>
            Seleziona le analisi: il documento stampabile include i dati del lavoratore,
            le analisi richieste e lo spazio per le firme.
          </p>
          <div className="option-list">
            {LAB_REQUEST_TESTS.map((t) => (
              <label key={t.code} className={`option-item${labReqTests.includes(t.code) ? ' selected' : ''}`}>
                <input type="checkbox" checked={labReqTests.includes(t.code)}
                       onChange={() => toggleTest(t.code)} />
                {t.label}
              </label>
            ))}
          </div>
        </Modal>
      )}

      {showEncounter && (
        <div className="card">
          <div className="card-head"><h3>Documenta un incontro clinico</h3></div>
          <div className="card-body">
            <div className="form-grid">
              <Field label="Tipo">
                <select className="select" value={enc.kind} onChange={(e) => setEnc({ ...enc, kind: e.target.value })}>
                  <option value="controllo">Controllo</option>
                  <option value="followup">Follow-up</option>
                  <option value="urgenza">Urgenza</option>
                </select>
              </Field>
              <Field label="Data">
                <input type="date" className="input" value={enc.encounter_date} max={new Date().toISOString().slice(0, 10)}
                       onChange={(e) => setEnc({ ...enc, encounter_date: e.target.value })} />
              </Field>
              <div style={{ gridColumn: '1 / -1' }}>
                <Field label="Diagnosi / motivo">
                  <input className="input" value={enc.diagnosis} onChange={(e) => setEnc({ ...enc, diagnosis: e.target.value })}
                         placeholder="es. Diabete mellito — controllo trimestrale" />
                </Field>
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <Field label="Note cliniche">
                  <textarea className="textarea" value={enc.notes} onChange={(e) => setEnc({ ...enc, notes: e.target.value })}
                            placeholder="Esito, terapia, indicazioni…" />
                </Field>
              </div>
            </div>
            <div className="row" style={{ justifyContent: 'flex-end', marginTop: 10 }}>
              <button className="btn btn-primary btn-sm" disabled={!enc.diagnosis.trim()}
                      onClick={async () => {
                        await api.createEncounter(patientId, enc)
                        setShowEncounter(false)
                        setEnc({ kind: 'controllo', encounter_date: new Date().toISOString().slice(0, 10), notes: '', diagnosis: '' })
                        await encounters.reload()
                      }}>
                Salva incontro
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-head"><h3>Incontri clinici</h3></div>
        <div className="card-body">
          {(encounters.data || []).length > 0 ? (
            <table className="table">
              <thead><tr><th>Data</th><th>Tipo</th><th>Struttura</th><th>Diagnosi</th><th>Note</th></tr></thead>
              <tbody>
                {(encounters.data || []).map((e) => (
                  <tr key={e.id}>
                    <td style={{ whiteSpace: 'nowrap' }}>{formatDate(e.encounter_date)}</td>
                    <td>
                      <Badge tone={e.kind === 'urgenza' ? 'risk' : e.kind === 'followup' ? 'info' : 'neutral'}>{e.kind}</Badge>
                    </td>
                    <td className="muted" style={{ fontSize: 11.5 }}>{e.facility || '—'}</td>
                    <td style={{ fontSize: 12 }}>{e.diagnosis || '—'}</td>
                    <td className="muted truncate" style={{ fontSize: 11.5, maxWidth: 240 }}>{e.notes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p className="muted" style={{ fontSize: 12.5 }}>Nessun incontro registrato.</p>}
        </div>
      </div>
    </div>
  )
}
