import { useMemo, useState } from 'react'
import ChatPanel from '../../components/ChatPanel'
import Icon from '../../components/Icon'
import { Badge, Loading, RiskBadge } from '../../components/ui'
import * as api from '../../lib/api'
import { formatDate, formatDateTime } from '../../lib/format'
import { Modal } from '../../components/ui'
import { useAsync } from '../../lib/useAsync'
import AnamnesisPanel from './AnamnesisPanel'
import CarePanel from './CarePanel'
import MonitoringPanel from './MonitoringPanel'
import OverviewPanel from './OverviewPanel'
import PathwaysPanel from './PathwaysPanel'
import RiskPanel from './RiskPanel'
import TriageConsole from './TriageConsole'
import TriageHistoryPanel from './TriageHistoryPanel'

const TABS = [
  { key: 'panoramica', label: 'Panoramica', icon: 'pulse' },
  { key: 'rischio', label: 'Rischio & anamnesi', icon: 'shield' },
  { key: 'percorsi', label: 'Percorsi', icon: 'route' },
  { key: 'monitoraggio', label: 'Monitoraggio', icon: 'monitor' },
  { key: 'presa', label: 'Presa in carico', icon: 'calendar' },
  { key: 'chiamate', label: 'Chiamate', icon: 'phone' },
]

const SEVERITY_ICON = { critical: 'alert', warning: 'alert', info: 'bell' }
const initials = (name) => name.split(' ').map((s) => s[0]).slice(0, 2).join('')

export default function DoctorWorkspace() {
  const dashboard = useAsync(() => api.getDoctorDashboard(), [])
  const [selectedId, setSelectedId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailRisk, setDetailRisk] = useState(null)
  const [tab, setTab] = useState('panoramica')
  const [showTriage, setShowTriage] = useState(false)
  const [report, setReport] = useState(null)

  async function selectPatient(id, section = 'panoramica') {
    setSelectedId(id)
    setTab(section)
    const [profile, risk] = await Promise.all([api.getPatient(id), api.getRisk(id)])
    setDetail(profile)
    setDetailRisk(risk)
  }

  async function reloadAll() {
    await dashboard.reload()
    if (selectedId) {
      setDetail(await api.getPatient(selectedId))
      setDetailRisk(await api.getRisk(selectedId))
    }
  }

  const data = dashboard.data
  const overdueCount = useMemo(
    () => (data?.pending_followups || []).filter((f) => f.overdue).length,
    [data],
  )

  if (dashboard.loading) return <main className="main"><Loading /></main>
  if (dashboard.error) return <main className="main"><p className="error-text">{dashboard.error.message}</p></main>

  return (
    <div className="workspace">
      {/* LEFT RAIL */}
      <aside className="rail">
        <div>
          <div className="row-between" style={{ marginBottom: 8 }}>
            <h3 style={{ fontSize: 11.5, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--ink-2)' }}>
              Avvisi clinici
            </h3>
            <button className="btn btn-ghost btn-sm" onClick={() => dashboard.reload()} aria-label="Aggiorna">
              <Icon name="refresh" size={13} />
            </button>
          </div>
          <div className="stack" style={{ gap: 6 }}>
            {(data.alerts || []).slice(0, 7).map((a, i) => (
              <div key={i} className={`alert-item ${a.severity}`} style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 2, cursor: 'pointer' }}
                   onClick={() => selectPatient(a.patient_id)}>
                <strong style={{ fontSize: 12 }}>
                  <Icon name={SEVERITY_ICON[a.severity] || 'bell'} size={12} style={{ verticalAlign: '-1px', marginRight: 4 }} />
                  {a.title}
                </strong>
                <span className="muted" style={{ fontSize: 11.5 }}>{a.patient_name} — {a.message}</span>
              </div>
            ))}
            {(data.alerts || []).length === 0 && <div className="empty" style={{ padding: 10 }}>Nessun avviso attivo.</div>}
          </div>
        </div>

        <div>
          <div className="row-between" style={{ marginBottom: 8 }}>
            <h3 style={{ fontSize: 11.5, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--ink-2)' }}>
              Follow-up in programma
            </h3>
            {overdueCount > 0 && <span className="badge badge-risk">{overdueCount} in ritardo</span>}
          </div>
          <div className="stack" style={{ gap: 6 }}>
            {(data.pending_followups || []).slice(0, 6).map((f) => (
              <div
                key={f.id}
                className="panel-flat"
                style={{ cursor: 'pointer', padding: '8px 10px' }}
                onClick={() => selectPatient(f.patient_id)}
              >
                <div className="truncate" style={{ fontSize: 12, fontWeight: 650 }}>{f.patient_name}</div>
                <div className="truncate muted" style={{ fontSize: 11 }}>{f.reason}</div>
                <div className="row" style={{ gap: 6, marginTop: 3 }}>
                  <Badge tone={f.overdue ? 'risk' : 'info'}>{formatDate(f.due_on)}</Badge>
                  <span style={{ fontSize: 10.5, color: 'var(--faint)' }}>via {f.channel}</span>
                </div>
              </div>
            ))}
            {(data.pending_followups || []).length === 0 && <div className="empty" style={{ padding: 10 }}>Nessun follow-up.</div>}
          </div>
        </div>

        <div>
          <h3 style={{ fontSize: 11.5, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--ink-2)', marginBottom: 8 }}>
            Prossime visite
          </h3>
          <div className="stack" style={{ gap: 6 }}>
            {(data.upcoming_appointments || []).slice(0, 5).map((a) => (
              <div key={a.id} className="panel-flat" style={{ cursor: 'pointer', padding: '8px 10px' }} onClick={() => selectPatient(a.patient_id)}>
                <div className="row-between">
                  <strong style={{ fontSize: 12 }} className="truncate">{a.patient_name}</strong>
                  <Badge tone={a.priority === 'urgente' ? 'warn' : 'neutral'}>{a.priority}</Badge>
                </div>
                <div className="truncate muted" style={{ fontSize: 11 }}>
                  {a.kind === 'teleconsulto' ? 'Teleconsulto' : 'Visita'} · {formatDateTime(a.scheduled_at)}
                </div>
              </div>
            ))}
            {(data.upcoming_appointments || []).length === 0 && <div className="empty" style={{ padding: 10 }}>Nessuna visita.</div>}
          </div>
        </div>
      </aside>

      {/* MAIN */}
      <main className="main">
        <div className="page-head">
          <div>
            <h1>Lavoratori in carico</h1>
            <p className="sub">{data.patients.length} lavoratori · stratificazione aggiornata in tempo reale</p>
          </div>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn btn-secondary" onClick={async () => setReport(await api.getDoctorReport())}>
              <Icon name="file" size={14} />
              Report aziende
            </button>
            <button className="btn btn-primary" onClick={() => setShowTriage(true)}>
              <Icon name="phone" size={14} />
              Nuova chiamata
            </button>
          </div>
        </div>

        {!selectedId ? (
          <div className="card">
            <table className="table">
              <thead>
                <tr><th>Lavoratore</th><th>Patologia</th><th>Rischio</th><th>Fattori</th><th>Ultimo incontro</th><th /></tr>
              </thead>
              <tbody>
                {data.patients.map((p) => (
                  <tr key={p.id} className="clickable" onClick={() => selectPatient(p.id)}>
                    <td>
                      <div className="row" style={{ gap: 10 }}>
                        <span className="avatar" style={{ borderRadius: 9 }}>{initials(p.full_name)}</span>
                        <div>
                          <strong>{p.full_name}</strong>
                          <div className="muted" style={{ fontSize: 11 }}>{p.job_title} · {p.age} anni</div>
                        </div>
                      </div>
                    </td>
                    <td style={{ fontSize: 12 }}>{p.primary_diagnosis}</td>
                    <td><RiskBadge level={p.risk_level} /></td>
                    <td className="num">
                      <span style={{ color: 'var(--risk)', fontWeight: 750 }}>{p.risk_count}</span>
                      <span className="muted"> / </span>
                      <span style={{ color: 'var(--ok)', fontWeight: 750 }}>{p.protective_count}</span>
                    </td>
                    <td className="muted" style={{ fontSize: 11.5 }}>{p.last_encounter ? formatDate(p.last_encounter) : '—'}</td>
                    <td style={{ textAlign: 'right' }}><Badge>Apri →</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          detail && (
            <>
              {/* patient context banner */}
              <div className="patient-banner">
                <span className="avatar">{initials(detail.full_name)}</span>
                <div className="who">
                  <div className="name">{detail.full_name}</div>
                  <div className="sub">
                    {detail.primary_diagnosis} · {detail.job_title} ({detail.employer}) · {detail.age} anni
                  </div>
                </div>
                <div className="facts">
                  <span className="fact"><Icon name="shield" size={12} /> Rischio {detail.risk_level}</span>
                  <span className="fact">{detail.risk_count} attivi · {detail.protective_count} protettivi</span>
                  {detail.comorbidities?.length > 0 && <span className="fact">Comorbidità: {detail.comorbidities.join(', ')}</span>}
                  <span className="fact">Terapia: {detail.medications?.length ?? 0} farmaci</span>
                  <button className="btn btn-secondary btn-sm" style={{ background: 'transparent', color: '#fff', borderColor: 'rgba(255,255,255,.3)' }}
                          onClick={() => setSelectedId(null)}>
                    ← Elenco
                  </button>
                </div>
              </div>

              <div className="tabs" style={{ marginBottom: 14 }}>
                {TABS.map((t) => (
                  <button key={t.key} className={`tab${tab === t.key ? ' active' : ''}`} onClick={() => setTab(t.key)}>
                    <Icon name={t.icon} size={14} />
                    {t.label}
                  </button>
                ))}
              </div>

              {tab === 'panoramica' && (
                <OverviewPanel patientId={selectedId} risk={detailRisk} onRiskUpdated={setDetailRisk} onOpenTab={setTab} />
              )}
              {tab === 'rischio' && (
                <div className="section">
                  <RiskPanel patientId={selectedId} onRiskUpdated={setDetailRisk} />
                  <AnamnesisPanel patientId={selectedId} onRiskUpdated={reloadAll} />
                </div>
              )}
              {tab === 'percorsi' && (
                <PathwaysPanel patientId={selectedId} onChange={reloadAll} />
              )}
              {tab === 'monitoraggio' && <MonitoringPanel patientId={selectedId} />}
              {tab === 'presa' && <CarePanel patientId={selectedId} onChange={reloadAll} />}
              {tab === 'chiamate' && <TriageHistoryPanel patientId={selectedId} />}
            </>
          )
        )}
      </main>

      {/* RIGHT RAIL */}
      <aside className="rail-right">
        <ChatPanel
          role="doctor"
          patientId={selectedId}
          patientName={detail?.full_name || ''}
          patientRisk={detailRisk}
        />
      </aside>

      {report && (
        <Modal wide title="Report per azienda" onClose={() => setReport(null)}>
          <p className="muted" style={{ fontSize: 12.5, marginBottom: 12 }}>
            Adesione ai percorsi, rischio e assenza per malattia aggregati per datore di lavoro.
            Generato il {formatDateTime(report.generated_at)}.
          </p>
          <table className="table">
            <thead>
              <tr><th>Datore di lavoro</th><th>Lavoratori</th><th>Avanzamento percorsi</th><th>Tappe in ritardo</th><th>Fattori di rischio (media)</th><th>Giorni assenza 12 mesi (media)</th></tr>
            </thead>
            <tbody>
              {report.rows.map((r) => (
                <tr key={r.employer}>
                  <td style={{ fontWeight: 650 }}>{r.employer}</td>
                  <td className="num">{r.workers}</td>
                  <td className="num">{r.avg_pathway_progress !== null ? `${r.avg_pathway_progress}%` : '—'}</td>
                  <td className="num" style={r.overdue_steps > 0 ? { color: 'var(--risk)', fontWeight: 700 } : undefined}>{r.overdue_steps}</td>
                  <td className="num">{r.avg_risk_factors ?? '—'}</td>
                  <td className="num">{r.avg_absence_days_12m ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Modal>
      )}

      {showTriage && (
        <TriageConsole
          onClose={() => setShowTriage(false)}
          onCompleted={() => {
            dashboard.reload()
            if (selectedId) selectPatient(selectedId, 'chiamate')
          }}
        />
      )}
    </div>
  )
}
