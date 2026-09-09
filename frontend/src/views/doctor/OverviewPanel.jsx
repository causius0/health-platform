/** Doctor overview for one patient: stratification summary, pathway next
 * actions and recommended actions in one screen. */
import { Link } from 'react-router-dom' // eslint-disable-line no-unused-vars
import { getPatientPathways } from '../../lib/api'
import { formatDate } from '../../lib/format'
import { useAsync } from '../../lib/useAsync'
import Icon from '../../components/Icon'
import { Empty, Progress, RiskBadge } from '../../components/ui'

const KIND_ICON = { screening: 'flask', visita: 'stethoscope', misurazione: 'monitor', educazione: 'book', richiamo: 'phone' }
const STATE_RANK = { in_ritardo: 0, in_attesa: 1, programmato: 2 }

export default function OverviewPanel({ patientId, risk, onOpenTab }) {
  const pathways = useAsync(() => getPatientPathways(patientId), [patientId])

  const nextActions = (pathways.data || [])
    .flatMap((p) => p.steps.map((s) => ({ ...s, pathwayName: p.name, pathwayId: p.id })))
    .filter((s) => s.status !== 'completato')
    .sort((a, b) => (STATE_RANK[a.status] - STATE_RANK[b.status]) || (new Date(a.due_on) - new Date(b.due_on)))

  return (
    <div className="section">
      <div className="card">
        <div className="card-body">
          <div className="row-between wrap" style={{ gap: 14 }}>
            <div style={{ maxWidth: 560 }}>
              <div className="row" style={{ gap: 10 }}>
                <h2>Stratificazione del rischio</h2>
                <RiskBadge level={risk?.level} size={13} />
                {risk?.has_critical && <span className="badge badge-risk">Valore critico presente</span>}
              </div>
              <p className="muted" style={{ marginTop: 6 }}>
                {risk?.risk_count ?? 0} fattori di rischio attivi, {risk?.protective_count ?? 0} fattori
                protettivi confermati e {risk?.borderline_count ?? 0} valori vicino alla soglia.
                Regola concordata: <strong>≥ 4 fattori attivi → alto</strong>, con attivazione del
                percorso specifico e del medico del lavoro.
              </p>
            </div>
            <button className="btn btn-secondary btn-sm" onClick={() => onOpenTab('rischio')}>
              Dettaglio soglie e fonti <Icon name="arrowRight" size={13} />
            </button>
          </div>
          <hr className="divider" />
          <div className="stack" style={{ gap: 6 }}>
            {(risk?.recommendations || []).map((r, i) => (
              <div key={i} className="row" style={{ gap: 9, alignItems: 'flex-start' }}>
                <span style={{ color: 'var(--brand)', fontWeight: 750 }}>{i + 1}.</span>
                <span style={{ fontSize: 12.5 }}>{r}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card" style={{ borderTop: '3px solid var(--brand)' }}>
        <div className="card-head">
          <h3>Prossime azioni nei percorsi</h3>
          <button className="btn btn-ghost btn-sm" onClick={() => onOpenTab('percorsi')}>
            Gestisci percorsi <Icon name="arrowRight" size={13} />
          </button>
        </div>
        <div className="card-body stack" style={{ gap: 8 }}>
          {(pathways.data || []).length === 0 && (
            <Empty icon="route">
              Nessun percorso attivo: iscrivi il lavoratore a un percorso di prevenzione,
              screening o follow-up dal tab Percorsi.
            </Empty>
          )}
          {nextActions.slice(0, 4).map((s) => (
            <div key={s.id} className={`panel-flat${s.status === 'in_ritardo' ? ' accent-risk' : ' accent-brand'}`}>
              <div className="row-between wrap" style={{ gap: 8 }}>
                <div>
                  <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
                    {s.status === 'in_ritardo' && <span className="badge badge-risk"><span className="dot" />In ritardo</span>}
                    <strong style={{ fontSize: 12.5 }}>{s.title}</strong>
                    <span className="badge badge-neutral">{s.pathwayName}</span>
                  </div>
                  <p style={{ fontSize: 11, color: 'var(--faint)', marginTop: 2 }}>
                    {s.status === 'programmato'
                      ? (s.appointment ? `Appuntamento ${formatDate(s.appointment.scheduled_at)}` : 'Richiamo programmato')
                      : `Entro il ${formatDate(s.due_on)}`}
                  </p>
                </div>
                <Icon name={KIND_ICON[s.kind] || 'clock'} size={15} style={{ color: 'var(--faint)' }} />
              </div>
            </div>
          ))}
          {(pathways.data || []).length > 0 && nextActions.length === 0 && (
            <div className="alert-item" style={{ background: 'var(--ok-soft)', borderColor: 'var(--ok-soft)' }}>
              <span style={{ color: 'var(--ok)' }}><Icon name="check" size={16} /></span>
              <span style={{ fontSize: 12.5 }}>Tutte le tappe dei percorsi attivi sono completate.</span>
            </div>
          )}
        </div>
      </div>

      {(pathways.data || []).map((p) => (
        <div key={p.id} className="card">
          <div className="card-body">
            <div className="row-between" style={{ fontSize: 12.5, marginBottom: 6 }}>
              <strong>{p.name}</strong>
              <span className="num muted">{p.progress}% · {p.steps.filter((s) => s.status === 'completato').length}/{p.steps.length} tappe</span>
            </div>
            <Progress value={p.progress} tone={p.progress === 100 ? 'ok' : undefined} />
          </div>
        </div>
      ))}
    </div>
  )
}
