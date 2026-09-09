import { Link } from 'react-router-dom'
import { formatDateTime, GOAL_AREA_LABEL } from '../../lib/format'
import Icon from '../../components/Icon'
import { Badge, Progress, RiskBadge, StatTile } from '../../components/ui'
import SymptomCheckInCard from '../../components/SymptomCheckInCard'

function NextActionIcon(kind) {
  return { misurazione: 'monitor', visita: 'stethoscope', screening: 'flask', educazione: 'book', richiamo: 'phone' }[kind] || 'clock'
}

import { patientId } from '../../lib/api' // eslint-disable-line no-unused-vars
export default function Overview({ pid, risk, engagement, pendingActions, pathways, goals, notifications, onSymptomSubmitted }) {
  return (
    <div className="section">
      <SymptomCheckInCard patientId={pid} onSubmitted={onSymptomSubmitted} />

      {/* notification strip */}
      {(notifications?.items || []).length > 0 && (
        <div className="card" style={{ borderTop: '3px solid var(--warn)' }}>
          <div className="card-head"><h3>Promemoria</h3></div>
          <div className="card-body stack" style={{ gap: 7 }}>
            {notifications.items.slice(0, 4).map((n, i) => (
              <div key={i} className="row-between">
                <div className="row" style={{ gap: 8 }}>
                  <span className={`badge badge-${n.severity === 'critical' ? 'risk' : n.severity === 'warning' ? 'warn' : 'info'}`}>
                    <span className="dot" />{n.title}
                  </span>
                  <span className="muted small truncate">{n.detail}</span>
                </div>
                <Link to={n.link} className="btn btn-ghost btn-sm">Apri</Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* risk + engagement */}
      <div className="card">
        <div className="card-body">
          <div className="row-between wrap" style={{ gap: 16 }}>
            <div style={{ maxWidth: 560 }}>
              <div className="row" style={{ gap: 10 }}>
                <h2>La tua stratificazione del rischio</h2>
                <RiskBadge level={risk?.level} size={13} />
              </div>
              <p className="muted" style={{ marginTop: 6 }}>
                Calcolata su {risk?.risk_count ?? 0} fattori di rischio attivi e{' '}
                {risk?.protective_count ?? 0} fattori protettivi confermati, con soglie cliniche
                documentate e condivise con il medico.
                {risk?.has_critical && (
                  <span style={{ color: 'var(--risk)', fontWeight: 650 }}> Sono presenti valori critici.</span>
                )}
              </p>
            </div>
            <div className="row" style={{ gap: 8 }}>
              <StatTile label="Fattori attivi" value={risk?.risk_count ?? '—'} state="risk" />
              <StatTile label="Punti di forza" value={risk?.protective_count ?? '—'} state="protective" />
              <StatTile label="Da monitorare" value={risk?.borderline_count ?? '—'} />
            </div>
          </div>
          <hr className="divider" />
          <div className="row wrap" style={{ gap: 6 }}>
            {(risk?.recommendations || []).map((r, i) => (
              <span key={i} className="chip"><Icon name="target" size={12} /> {r}</span>
            ))}
          </div>
        </div>
      </div>

      {/* NEXT ACTIONS — the pathway hero */}
      <div className="card" style={{ borderTop: '3px solid var(--brand)' }}>
        <div className="card-head">
          <h3>Prossime azioni del tuo percorso</h3>
          <Link to="/portal/percorsi" className="btn btn-ghost btn-sm">
            Tutti i percorsi <Icon name="arrowRight" size={13} />
          </Link>
        </div>
        <div className="card-body stack" style={{ gap: 8 }}>
          {pendingActions.length === 0 && (
            <p className="muted" style={{ fontSize: 12.5 }}>
              Nessuna azione in sospeso: i tuoi percorsi sono al passo.
            </p>
          )}
          {pendingActions.map((a) => (
            <div key={a.id} className={`panel-flat${a.status === 'in_ritardo' ? ' accent-risk' : ' accent-brand'}`}>
              <div className="row-between wrap" style={{ gap: 8 }}>
                <div>
                  <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
                    {a.status === 'in_ritardo' && <span className="badge badge-risk"><span className="dot" />In ritardo</span>}
                    <strong style={{ fontSize: 13 }}>{a.title}</strong>
                    <span className="badge badge-neutral">{a.pathwayName}</span>
                  </div>
                  <p style={{ fontSize: 11, color: 'var(--faint)', marginTop: 2 }}>Entro il {new Date(a.due_on).toLocaleDateString('it-IT')}</p>
                </div>
                <span className="row" style={{ gap: 6, color: 'var(--muted)', fontSize: 12 }}>
                  {a.status === 'programmato'
                    ? (a.appointment ? `Appuntamento ${formatDateTime(a.appointment.scheduled_at)}` : 'Richiamo programmato')
                    : (
                      <Link to="/portal/percorsi" className="btn btn-primary btn-sm">
                        <Icon name={NextActionIcon(a.kind)} size={13} />
                        {a.kind === 'misurazione' ? 'Registra misura'
                          : a.kind === 'screening' ? 'Prenota esame'
                            : a.kind === 'visita' ? 'Prenota visita'
                              : 'Apri il percorso'}
                      </Link>
                    )}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="row" style={{ alignItems: 'stretch', gap: 12, flexWrap: 'wrap' }}>
        {/* engagement */}
        <div className="card grow" style={{ minWidth: 260 }}>
          <div className="card-head"><h3>Il tuo impegno nel percorso</h3></div>
          <div className="card-body">
            {engagement ? (
              <div className="row" style={{ gap: 14 }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 27, fontWeight: 800, color: 'var(--brand-strong)' }}>{engagement.score}</div>
                  <div style={{ fontSize: 10.5, color: 'var(--muted)' }}>su 100</div>
                </div>
                <div className="grow stack" style={{ gap: 7 }}>
                  {[
                    ['Obiettivi settimanali', engagement.components.goal_adherence],
                    ['Questionari benessere', engagement.components.questionnaire_coverage],
                    ['Misurazioni a domicilio', engagement.components.monitoring_compliance],
                  ].map(([label, v]) => (
                    <div key={label}>
                      <div className="row-between" style={{ fontSize: 11.5 }}>
                        <span>{label}</span>
                        <strong>{v ?? '—'}%</strong>
                      </div>
                      <Progress value={v || 0} />
                    </div>
                  ))}
                </div>
              </div>
            ) : <p className="muted" style={{ fontSize: 12.5 }}>Dati non disponibili.</p>}
          </div>
        </div>

        {/* active pathways mini */}
        <div className="card grow" style={{ minWidth: 260 }}>
          <div className="card-head"><h3>Percorsi attivi</h3></div>
          <div className="card-body stack" style={{ gap: 9 }}>
            {pathways.length === 0 && <p className="muted" style={{ fontSize: 12.5 }}>Nessun percorso attivo.</p>}
            {pathways.map((p) => (
              <div key={p.id}>
                <div className="row-between" style={{ fontSize: 12, marginBottom: 3 }}>
                  <span className="truncate">{p.name}</span>
                  <strong className="num">{p.progress}%</strong>
                </div>
                <Progress value={p.progress} tone={p.progress === 100 ? 'ok' : undefined} />
              </div>
            ))}
            <Link to="/portal/percorsi" className="btn btn-secondary btn-sm" style={{ alignSelf: 'flex-start' }}>
              <Icon name="route" size={13} /> Apri i percorsi
            </Link>
          </div>
        </div>

        {/* goals mini */}
        <div className="card grow" style={{ minWidth: 260 }}>
          <div className="card-head"><h3>Obiettivi attivi</h3></div>
          <div className="card-body stack" style={{ gap: 8 }}>
            {goals.filter((g) => g.status === 'active').slice(0, 3).map((g) => (
              <div key={g.id} className="row-between" style={{ fontSize: 12.5 }}>
                <span className="truncate">{g.title}</span>
                <Badge>{GOAL_AREA_LABEL[g.area]}</Badge>
              </div>
            ))}
            {goals.filter((g) => g.status === 'active').length === 0 && (
              <p className="muted" style={{ fontSize: 12.5 }}>Nessun obiettivo attivo.</p>
            )}
            <Link to="/portal/percorsi" className="btn btn-secondary btn-sm" style={{ alignSelf: 'flex-start' }}>
              Gestisci obiettivi
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
