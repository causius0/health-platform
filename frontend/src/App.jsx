import { useEffect } from 'react'
import { NavLink, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useAuth } from './auth'
import Icon from './components/Icon'
import { logout as apiLogout } from './lib/api'
import Login from './views/Login'
import PatientPortal from './views/patient/PatientPortal'
import DoctorWorkspace from './views/doctor/DoctorWorkspace'

function TopBar() {
  const auth = useAuth()
  const navigate = useNavigate()

  const initials = auth.fullName
    .split(/[\s.]+/).filter(Boolean).slice(0, 2)
    .map((s) => s[0].toUpperCase()).join('') || '?'

  async function doLogout() {
    try { await apiLogout() } catch { /* token already invalid */ }
    auth.signOut()
    navigate('/login')
  }

  return (
    <header className="topbar">
      <NavLink to={auth.role === 'doctor' ? '/studio' : '/portal'} className="brand" style={{ textDecoration: 'none' }}>
        <span className="brand-mark">
          <Icon name="pulse" size={15} strokeWidth={2.3} />
        </span>
        Health Platform
      </NavLink>
      <span className="brand-context">
        {auth.role === 'doctor' ? 'Console clinica · prevenzione e presa in carico' : 'Il mio percorso di prevenzione'}
      </span>
      <span className="topbar-spacer" />
      {auth.user && (
        <div className="user-chip">
          <div className="meta">
            <div className="name">{auth.fullName}</div>
            <div className="role">{auth.role === 'doctor' ? 'Medico / operatore sanitario' : 'Lavoratore'}</div>
          </div>
          <span className="avatar">{initials}</span>
          <button className="btn btn-secondary btn-sm" onClick={doLogout}>Esci</button>
        </div>
      )}
    </header>
  )
}

function RequireRole({ role, children }) {
  const auth = useAuth()
  if (!auth.user) return <Navigate to="/login" replace />
  if (auth.role !== role) return <Navigate to={auth.role === 'doctor' ? '/studio' : '/portal'} replace />
  return children
}

function FatalBoundary({ children }) {
  // Uncaught render errors become visible instead of a blank screen.
  useEffect(() => {
    const show = (message) => {
      let el = document.getElementById('fatal-error')
      if (!el) {
        el = document.createElement('div')
        el.id = 'fatal-error'
        el.style.cssText =
          'position:fixed;bottom:12px;left:12px;right:12px;z-index:9999;background:#b42318;color:#fff;' +
          'padding:12px 16px;border-radius:10px;font:12px/1.5 system-ui;white-space:pre-wrap;max-height:40vh;overflow:auto'
        document.body.appendChild(el)
      }
      el.textContent = message
    }
    const onRejection = (e) => show(e.reason?.stack || String(e.reason))
    const onError = (e) => show(e.error?.stack || e.message)
    window.addEventListener('unhandledrejection', onRejection)
    window.addEventListener('error', onError)
    return () => {
      window.removeEventListener('unhandledrejection', onRejection)
      window.removeEventListener('error', onError)
    }
  }, [])
  return children
}

export default function App() {
  const auth = useAuth()
  return (
    <FatalBoundary>
      <div className="app-shell">
        <TopBar />
        <Routes>
          <Route path="/login" element={
            auth.user
              ? <Navigate to={auth.role === 'doctor' ? '/studio' : '/portal'} replace />
              : <Login />
          } />
          <Route path="/portal/*" element={<RequireRole role="patient"><PatientPortal /></RequireRole>} />
          <Route path="/studio/*" element={<RequireRole role="doctor"><DoctorWorkspace /></RequireRole>} />
          <Route path="*" element={<Navigate to={auth.role === 'doctor' ? '/studio' : auth.user ? '/portal' : '/login'} replace />} />
        </Routes>
      </div>
    </FatalBoundary>
  )
}
