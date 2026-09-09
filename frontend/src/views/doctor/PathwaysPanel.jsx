/** Doctor-side pathways: enroll the worker in a standard iter, act on steps
 * (book visit/exam, schedule recall, mark done), discontinue. */
import { useState } from 'react'
import { PathwayCard } from '../../components/pathways'
import Icon from '../../components/Icon'
import { ConfirmDialog, Empty, Modal } from '../../components/ui'
import * as api from '../../lib/api'
import { useAsync } from '../../lib/useAsync'

export default function PathwaysPanel({ patientId, onChange }) {
  const pathways = useAsync(() => api.getPatientPathways(patientId), [patientId])
  const suggestions = useAsync(() => api.getPathwaySuggestions(patientId), [patientId])
  const templates = useAsync(() => api.getPathwayTemplates(), [])
  const [showEnroll, setShowEnroll] = useState(false)
  const [selected, setSelected] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [discontinueId, setDiscontinueId] = useState(null)

  function onUpdate() {
    pathways.reload()
    onChange?.()
  }

  async function enroll() {
    if (!selected) return
    setBusy(true)
    setError('')
    try {
      await api.enrollInPathway(patientId, selected)
      setShowEnroll(false)
      setSelected('')
      onUpdate()
    } catch (e) {
      setError(e.message)
    } finally { setBusy(false) }
  }

  async function discontinue(id) {
    setDiscontinueId(null)
    await api.discontinuePathway(id)
    onUpdate()
  }

  return (
    <div className="section">
      <div className="row-between">
        <p className="muted" style={{ fontSize: 12.5, margin: 0 }}>
          Percorsi standard di <strong>prevenzione, screening e follow-up</strong>: ogni tappa
          prenota visite ed esami o programma richiami, e si chiude automaticamente al
          completamento dell’appuntamento associato.
        </p>
        <button className="btn btn-primary btn-sm" onClick={() => setShowEnroll(true)}>
          <Icon name="plus" size={13} /> Iscrivi a un percorso
        </button>
      </div>

      {(suggestions.data || []).length > 0 && (
        <div className="panel-flat accent-info">
          <strong style={{ fontSize: 12.5 }}>
            <Icon name="target" size={13} style={{ verticalAlign: '-2px', marginRight: 4 }} />
            Consigliati in base a diagnosi, rischio e chiamate recenti
          </strong>
          <div className="stack" style={{ gap: 6, marginTop: 8 }}>
            {suggestions.data.map((sg) => (
              <div key={sg.code} className="row-between wrap" style={{ gap: 8 }}>
                <div className="grow">
                  <strong style={{ fontSize: 12.5 }}>{sg.name}</strong>
                  <div className="muted" style={{ fontSize: 11.5 }}>{sg.reason}</div>
                </div>
                <button className="btn btn-secondary btn-sm"
                        onClick={async () => {
                          await api.enrollInPathway(patientId, sg.code)
                          onUpdate()
                        }}>
                  Iscrivi
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {(pathways.data || []).length === 0 && (
        <Empty icon="route">
          Nessun percorso attivo. Scegli “Iscrivi a un percorso” per attivare l’iter
          consigliato in base al profilo di rischio.
        </Empty>
      )}

      {(pathways.data || []).map((p) => (
        <div key={p.id} className="section" style={{ gap: 6 }}>
          <PathwayCard pathway={p} role="doctor" onUpdate={onUpdate} />
          <button className="btn btn-danger btn-sm" style={{ alignSelf: 'flex-start' }}
                  onClick={() => setDiscontinueId(p.id)}>
            Interrompi questo percorso
          </button>
        </div>
      ))}

      <ConfirmDialog
        open={!!discontinueId} tone="danger" confirmLabel="Interrompi percorso"
        title="Interrompere questo percorso?"
        message="Il percorso verrà contrassegnato come interrotto; le tappe già completate restano nello storico."
        onConfirm={() => discontinue(discontinueId)}
        onCancel={() => setDiscontinueId(null)}
      />

      {showEnroll && (
        <Modal
          title="Iscrivi a un percorso"
          onClose={() => setShowEnroll(false)}
          footer={
            <>
              <button className="btn btn-secondary" onClick={() => setShowEnroll(false)}>Annulla</button>
              <button className="btn btn-primary" disabled={!selected || busy} onClick={enroll}>
                Iscrivi lavoratore
              </button>
            </>
          }
        >
          <div className="option-list">
            {(templates.data || []).map((t) => (
              <label key={t.code} className={`option-item${selected === t.code ? ' selected' : ''}`}>
                <input type="radio" name="tpl" value={t.code} checked={selected === t.code}
                       onChange={() => setSelected(t.code)} />
                <div>
                  <strong style={{ fontSize: 12.5 }}>{t.name}</strong>
                  <div className="muted" style={{ fontSize: 11.5 }}>{t.description}</div>
                  <div style={{ fontSize: 10.5, color: 'var(--faint)', marginTop: 2 }}>
                    {t.target_text} · {t.steps.length} tappe
                  </div>
                </div>
              </label>
            ))}
          </div>
          {error && <p className="error-text" style={{ marginTop: 10 }}>{error}</p>}
        </Modal>
      )}
    </div>
  )
}
