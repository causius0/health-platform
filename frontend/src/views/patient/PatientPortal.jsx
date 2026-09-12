import { useMemo, useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from '../../auth'
import ChatPanel from '../../components/ChatPanel'
import Icon from '../../components/Icon'
import { Loading, RiskBadge } from '../../components/ui'
import { getEngagement, getGoals, getMyNotifications, getPatient, getPatientPathways, getRisk } from '../../lib/api'
import { useAsync } from '../../lib/useAsync'
import AnamnesisFolder from './AnamnesisFolder'
import Education from './Education'
import Appointments from './Appointments'
import Monitoring from './Monitoring'
import Overview from './Overview'
import Pathways from './Pathways'

const NAV = [
  { to: 'panoramica', label: 'Panoramica', icon: 'home' },
  { to: 'percorsi', label: 'Percorsi', icon: 'route' },
  { to: 'anamnesi', label: 'Cartella anamnestica', icon: 'folder' },
  { to: 'monitoraggio', label: 'Monitoraggio', icon: 'monitor' },
  { to: 'appuntamenti', label: 'Appuntamenti', icon: 'calendar' },
  { to: 'educazione', label: 'Educazione', icon: 'book' },
]

const HOME_ICON = { home: 'pulse' }

export default function PatientPortal() {
  const auth = useAuth()
  const pid = auth.patientId
  const [riskOverride, setRiskOverride] = useState(null)

  const profile = useAsync(() => getPatient(pid), [pid])
  const risk = useAsync(() => getRisk(pid), [pid])
  const pathways = useAsync(() => getPatientPathways(pid), [pid])
  const engagement = useAsync(() => getEngagement(pid), [pid])
  const goals = useAsync(() => getGoals(pid), [pid])
  const notifications = useAsync(() => getMyNotifications(), [pid])

  const riskData = riskOverride || risk.data
  const pendingActions = useMemo(() => {
    const list = pathways.data || []
    const rank = { in_ritardo: 0, in_attesa: 1, programmato: 2 }
    return list
      .flatMap((p) => p.steps.map((s) => ({ ...s, pathwayName: p.name })))
      .filter((s) => s.status !== 'completato')
      .sort((a, b) => (rank[a.status] - rank[b.status]) || (new Date(a.due_on) - new Date(b.due_on)))
  }, [pathways.data])

  if (profile.loading || risk.loading) return <main className="main"><Loading /></main>
  if (profile.error) return <main className="main"><p className="error-text">{profile.error.message}</p></main>
  const p = profile.data

  const initials = p.full_name.split(' ').map((s) => s[0]).slice(0, 2).join('')
  const age = p.birth_date
    ? Math.floor((Date.now() - new Date(p.birth_date).getTime()) / 31557600000)
    : null

  return (
    <div className="workspace">
      <nav className="sidenav">
        <div className="nav-label">Il mio percorso</div>
        {NAV.map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? 'active' : '')}>
            <Icon name={HOME_ICON[item.icon] || item.icon} size={16} />
            <span className="lbl">{item.label}</span>
            {item.to === 'percorsi' && pendingActions.some((a) => a.status === 'in_ritardo') && (
              <span className="nav-badge">!</span>
            )}
            {item.to === 'panoramica' && (notifications.data?.unread_count ?? 0) > 0 && (
              <span className="nav-badge" style={{ background: 'var(--warn)' }}>
                {notifications.data.unread_count}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <main className="main">
        <div className="page-head">
          <div className="row" style={{ gap: 13 }}>
            <span className="avatar" style={{ width: 44, height: 44, borderRadius: 12, fontSize: 15 }}>{initials}</span>
            <div>
              <h1 style={{ fontSize: 20 }}>{p.full_name}</h1>
              <p className="sub">
                {p.primary_diagnosis}
                {p.job_title && <> · {p.job_title}, {p.employer}</>}
                {age && <> · {age} anni</>}
              </p>
            </div>
          </div>
          <div className="row" style={{ gap: 8 }}>
            <RiskBadge level={riskData?.level} size={12.5} />
          </div>
        </div>

        <Routes>
          <Route index element={<Navigate to="panoramica" replace />} />
          <Route path="panoramica" element={
            <Overview
              pid={pid}
              profile={p} risk={riskData} engagement={engagement.data}
              pendingActions={pendingActions} pathways={pathways.data || []}
              goals={goals.data || []} notifications={notifications.data}
            />
          } />
          <Route path="percorsi" element={
            <Pathways patientId={pid} pathways={pathways.data || []}
                      onPathwayUpdate={pathways.reload} goals={goals}
                      onRiskUpdated={setRiskOverride} />
          } />
          <Route path="anamnesi" element={
            <AnamnesisFolder patientId={pid} onRiskUpdated={setRiskOverride} />
          } />
          <Route path="monitoraggio" element={
            <Monitoring patientId={pid} onRiskUpdated={setRiskOverride} />
          } />
          <Route path="appuntamenti" element={<Appointments patientId={pid} />} />
          <Route path="educazione" element={<Education />} />
          <Route path="*" element={<Navigate to="panoramica" replace />} />
        </Routes>
      </main>

      <aside className="rail-right">
        <ChatPanel role="patient" />
      </aside>
    </div>
  )
}
