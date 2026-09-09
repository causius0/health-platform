import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { getMe } from './lib/api'

const AuthContext = createContext(null)

function readUser() {
  try { return JSON.parse(localStorage.getItem('user')) } catch { return null }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => readUser())

  // The session lives in the HttpOnly cookie; the stored profile is only a
  // paint cache — always revalidate against the server on load.
  useEffect(() => {
    if (!localStorage.getItem('user')) return
    getMe()
      .then(setUser)
      .catch(() => setUser(null))
  }, [])

  const signIn = useCallback((newUser) => {
    localStorage.setItem('user', JSON.stringify(newUser))
    setUser(newUser)
  }, [])

  const signOut = useCallback(() => {
    localStorage.removeItem('user')
    setUser(null)
  }, [])

  const value = useMemo(() => ({
    user,
    role: user?.role ?? null,
    patientId: user?.patient_id ?? null,
    fullName: user?.full_name || user?.username || '',
    signIn,
    signOut,
  }), [user, signIn, signOut])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
