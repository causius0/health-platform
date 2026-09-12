// API endpoint for this deployment: window.__API_BASE__ is set at deploy time
// by public/config.js (GitHub Pages builds point it at the tunnel URL),
// VITE_API_BASE at build time; default is same-origin /api (dev, docker).
const API_BASE =
  (typeof window !== 'undefined' && window.__API_BASE__) ||
  import.meta.env.VITE_API_BASE ||
  '/api'

// App (SPA) base path, guaranteed to end with "/" — for hard redirects that
// bypass the router (which already knows the base via BrowserRouter basename).
const APP_BASE = `${import.meta.env.BASE_URL.replace(/\/+$/, '')}/`

export const appUrl = (path) => `${APP_BASE}${path.replace(/^\//, '')}`

/* Session auth: the primary path is the HttpOnly cookie set by the server, with
   the readable CSRF cookie echoed back on unsafe methods. When the environment
   drops cookies (some embedded browsers), the client falls back to a Bearer
   token kept in memory/sessionStorage for the duration of the session. */
let csrfToken = ''
let fallbackToken = ''

export function setCsrfToken(token) {
  csrfToken = token || ''
}

export function enableTokenFallback(token) {
  fallbackToken = token || ''
  try {
    sessionStorage.setItem('fallback_auth', JSON.stringify({ token: fallbackToken, csrf: csrfToken }))
  } catch { /* storage unavailable: in-memory only */ }
}

export function restoreTokenFallback() {
  if (fallbackToken) return
  try {
    const saved = JSON.parse(sessionStorage.getItem('fallback_auth') || 'null')
    if (saved?.token) {
      fallbackToken = saved.token
      csrfToken = saved.csrf || ''
    }
  } catch { /* ignore */ }
}

function csrfFromCookie() {
  const pair = document.cookie.split('; ').find((c) => c.startsWith('csrf_access_token='))
  return pair ? decodeURIComponent(pair.split('=')[1]) : ''
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function request(path, { method = 'GET', body } = {}) {
  restoreTokenFallback()
  if (!csrfToken) csrfToken = csrfFromCookie()
  const headers = { 'Content-Type': 'application/json' }
  if (fallbackToken) headers.Authorization = `Bearer ${fallbackToken}`
  if (method !== 'GET' && csrfToken) headers['X-CSRF-TOKEN'] = csrfToken

  let res
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      credentials: 'include',
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError('Server non raggiungibile', 0)
  }

  if (res.status === 401) {
    localStorage.removeItem('user')
    csrfToken = ''
    fallbackToken = ''
    try { sessionStorage.removeItem('fallback_auth') } catch { /* ignore */ }
    if (!window.location.pathname.startsWith(`${APP_BASE}login`)) {
      window.location.assign(appUrl('login'))
    }
    throw new ApiError('Sessione scaduta', 401)
  }
  if (!res.ok) {
    let message = `Errore ${res.status}`
    try {
      const payload = await res.json()
      if (payload?.error) message = payload.error
    } catch { /* non-JSON body */ }
    throw new ApiError(message, res.status)
  }
  const ct = res.headers.get('content-type') || ''
  return ct.includes('json') ? res.json() : res.text()
}

/* auth */
export const login = async (username, password) => {
  const data = await request('/login', { method: 'POST', body: { username, password } })
  setCsrfToken(data.csrf_token)
  // if the environment dropped the session cookie, switch to the Bearer fallback
  if (!csrfFromCookie() && data.token) enableTokenFallback(data.token)
  return data
}
export const logout = async () => {
  try { await request('/logout', { method: 'POST' }) } finally {
    setCsrfToken('')
    fallbackToken = ''
    try { sessionStorage.removeItem('fallback_auth') } catch { /* ignore */ }
  }
}
export const getMe = () => request('/me')

/* patients & clinical data */
export const getDoctorPatients = () => request('/doctor/patients')
export const getPatient = (id) => request(`/patients/${id}`)
export const getObservations = (id, months = 12) => request(`/patients/${id}/observations?months=${months}`)
export const addObservation = (id, body) => request(`/patients/${id}/observations`, { method: 'POST', body })
export const getEncounters = (id) => request(`/patients/${id}/encounters`)

/* printable lab request (server-rendered HTML, opened in a new tab) */
export const labRequestUrl = (id, tests) =>
  `${API_BASE}/patients/${id}/lab-request?tests=${tests.join(',')}`

/* risk */
export const getRisk = (id) => request(`/patients/${id}/risk`)
export const recomputeRisk = (id) => request(`/patients/${id}/risk/recompute`, { method: 'POST' })
export const getRiskHistory = (id) => request(`/patients/${id}/risk/history`)

/* anamnesis */
export const getAnamnesis = (id) => request(`/patients/${id}/anamnesis`)
export const putAnamnesisAnswer = (id, question_id, value) =>
  request(`/patients/${id}/anamnesis`, { method: 'PUT', body: { question_id, value } })
export const exportAnamnesisFhir = (id) => request(`/patients/${id}/anamnesis/export`)

/* goals */
export const getGoals = (id) => request(`/patients/${id}/goals`)
export const updateGoal = (goalId, body) => request(`/goals/${goalId}`, { method: 'PATCH', body })
export const goalCheckin = (goalId, body) => request(`/goals/${goalId}/checkin`, { method: 'POST', body })

/* monitoring plan */
export const getMonitoring = (id) => request(`/patients/${id}/monitoring`)
export const addMonitoring = (id, body) => request(`/patients/${id}/monitoring`, { method: 'POST', body })

/* follow-ups */
export const getFollowUps = (id) => request(`/patients/${id}/follow-ups`)
export const createFollowUp = (id, body) => request(`/patients/${id}/follow-ups`, { method: 'POST', body })
export const updateFollowUp = (fuId, body) => request(`/follow-ups/${fuId}`, { method: 'PATCH', body })

/* appointments */
export const getAppointments = (id) => request(`/patients/${id}/appointments`)
export const createAppointment = (id, body) => request(`/patients/${id}/appointments`, { method: 'POST', body })
export const updateAppointment = (apptId, body) => request(`/appointments/${apptId}`, { method: 'PATCH', body })

/* wellbeing */
export const getInstruments = () => request('/wellbeing/instruments')
export const getWellbeing = (id) => request(`/patients/${id}/wellbeing`)
export const submitWellbeing = (id, body) => request(`/patients/${id}/wellbeing`, { method: 'POST', body })
export const getEngagement = (id) => request(`/patients/${id}/engagement`)

/* triage */
export const getTriageProtocols = () => request('/triage/protocols')
export const getTriageProtocol = (code) => request(`/triage/protocols/${code}`)
export const submitTriage = (body) => request('/triage/assessments', { method: 'POST', body })
export const getTriageHistory = (id) => request(`/patients/${id}/triage`)

/* chat */
export const getChatThreads = () => request('/chat/threads')
export const startChatThread = (body = {}) => request('/chat/threads', { method: 'POST', body })
export const getChatThread = (id) => request(`/chat/threads/${id}`)
export const sendChatMessage = (id, content) =>
  request(`/chat/threads/${id}/messages`, { method: 'POST', body: { content } })
export const escalateThread = (id, subject) =>
  request(`/chat/threads/${id}/escalate`, { method: 'POST', body: { subject } })
export const claimThread = (id) => request(`/chat/threads/${id}/claim`, { method: 'POST' })
export const closeThread = (id) => request(`/chat/threads/${id}/close`, { method: 'POST' })
export const deleteThread = (id) => request(`/chat/threads/${id}`, { method: 'DELETE' })

/* pathways */
export const getPathwayTemplates = () => request('/pathways/templates')
export const getPatientPathways = (id) => request(`/patients/${id}/pathways`)
export const enrollInPathway = (id, template_code) =>
  request(`/patients/${id}/pathways`, { method: 'POST', body: { template_code } })
export const discontinuePathway = (id) => request(`/care-pathways/${id}`, { method: 'DELETE' })
export const completePathwayStep = (stepId, body = {}) =>
  request(`/pathway-steps/${stepId}/complete`, { method: 'POST', body })
export const bookPathwayStep = (stepId, body = {}) =>
  request(`/pathway-steps/${stepId}/book`, { method: 'POST', body })
export const scheduleStepFollowUp = (stepId, body = {}) =>
  request(`/pathway-steps/${stepId}/follow-up`, { method: 'POST', body })

/* doctor workspace */
export const getDoctorDashboard = () => request('/doctor/dashboard')
export const getDoctorReport = () => request('/doctor/report')

/* therapy (patient_medications) */
export const getMedications = (id) => request(`/patients/${id}/medications`)
export const addMedication = (id, body) => request(`/patients/${id}/medications`, { method: 'POST', body })
export const updateMedication = (medId, body) => request(`/medications/${medId}`, { method: 'PATCH', body })
export const deleteMedication = (medId) => request(`/medications/${medId}`, { method: 'DELETE' })

/* notifications */
export const getMyNotifications = () => request('/notifications')

/* GDPR */
export const exportAllData = (id) => request(`/patients/${id}/data-export`)
export const deleteMyAccount = () => request('/me', { method: 'DELETE' })

/* encounters */
export const createEncounter = (id, body) => request(`/patients/${id}/encounters`, { method: 'POST', body })

/* symptom check-ins */
export const getSymptomQuestions = () => request('/symptoms/questions')
export const getSymptomCheckins = (id) => request(`/patients/${id}/symptom-checkins`)
export const submitSymptomCheckin = (id, answers) =>
  request(`/patients/${id}/symptom-checkins`, { method: 'POST', body: { answers } })

/* pathway suggestions */
export const getPathwaySuggestions = (id) => request(`/patients/${id}/pathways/suggestions`)

/* education library */
export const getEducationArticles = () => request('/education')
export const getEducationArticle = (id) => request(`/education/${id}`)

/* triage drafts */
export const saveTriageDraft = (body) => request('/triage/drafts', { method: 'POST', body })
export const getTriageDrafts = () => request('/triage/drafts')
export const discardTriageDraft = (id) => request(`/triage/drafts/${id}`, { method: 'DELETE' })
