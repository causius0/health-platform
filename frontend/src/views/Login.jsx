import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { getMe, login } from '../lib/api'
import Icon from '../components/Icon'

export default function Login() {
  const auth = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // A valid HttpOnly session cookie restores the session automatically.
  useEffect(() => {
    getMe()
      .then((user) => {
        auth.signIn(user)
        navigate(user.role === 'doctor' ? '/studio' : '/portal', { replace: true })
      })
      .catch(() => { /* no valid session: stay on the login form */ })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (!username.trim() || !password) {
      setError('Inserisci username e password.')
      return
    }
    setLoading(true)
    try {
      const { user } = await login(username.trim(), password)
      auth.signIn(user)
      navigate(user.role === 'doctor' ? '/studio' : '/portal', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-layout">
      <div className="login-hero">
        <div style={{ maxWidth: 480 }}>
          <span className="brand" style={{ color: '#fff' }}>
            <span className="brand-mark" style={{ background: '#fff', color: 'var(--brand)' }}>
              <Icon name="pulse" size={15} strokeWidth={2.3} />
            </span>
            Health Platform
          </span>
          <h1 style={{ fontSize: 26, maxWidth: 430, marginTop: 22, lineHeight: 1.25 }}>
            Prevenzione, monitoraggio e presa in carico per chi lavora.
          </h1>
          <p style={{ color: 'rgba(255,255,255,.72)', maxWidth: 430, marginTop: 12 }}>
            Anamnesi strutturata, percorsi di prevenzione e screening, stratificazione del
            rischio con soglie documentate, algoritmi di triage per le chiamate e
            assistente digitale con supporto umano.
          </p>
        </div>
      </div>

      <div className="login-panel">
        <form className="login-box" onSubmit={submit}>
          <h2>Accedi alla piattaforma</h2>
          <p className="muted" style={{ fontSize: 12.5, margin: '4px 0 18px' }}>
            Area riservata a lavoratori e operatori sanitari.
          </p>

          <div className="field">
            <label htmlFor="username">Username</label>
            <input id="username" className="input" value={username} autoComplete="username"
                   onChange={(e) => setUsername(e.target.value)} placeholder="es. patient1" />
          </div>
          <div className="field" style={{ marginTop: 12 }}>
            <label htmlFor="password">Password</label>
            <input id="password" type="password" className="input" value={password}
                   autoComplete="current-password" onChange={(e) => setPassword(e.target.value)}
                   placeholder="••••••••" />
          </div>

          {error && <p className="error-text" style={{ marginTop: 10 }}>{error}</p>}

          <button className="btn btn-primary btn-block" style={{ marginTop: 16 }} disabled={loading} type="submit">
            {loading ? <span className="spinner" style={{ borderTopColor: '#fff' }} /> : 'Accedi'}
          </button>

          <div className="demo-creds">
            <h4>Account dimostrativi</h4>
            <p>Lavoratori: <span className="kbd">patient1</span> … <span className="kbd">patient5</span></p>
            <p>Operatore: <span className="kbd">doctor</span></p>
            <p>Password: <span className="kbd">HealthPlatform.Demo2026!</span></p>
          </div>
        </form>
      </div>

      <style>{`
        .login-layout { display: grid; grid-template-columns: 1.1fr 1fr; min-height: calc(100vh - 53px); }
        .login-hero {
          background: radial-gradient(900px 520px at 8% 0%, rgba(12, 110, 100, .88), rgba(9, 56, 51, .98)), #0a3833;
          color: #fff; display: flex; align-items: center; padding: 48px;
        }
        .login-panel { display: flex; align-items: center; justify-content: center; padding: 32px; }
        .login-box { width: 100%; max-width: 350px; }
        .demo-creds { margin-top: 22px; border-top: 1px dashed var(--border); padding-top: 14px; color: var(--muted); font-size: 12px; }
        .demo-creds h4 { font-size: 10.5px; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }
        @media (max-width: 900px) { .login-layout { grid-template-columns: 1fr; } .login-hero { display: none; } }
      `}</style>
    </main>
  )
}
