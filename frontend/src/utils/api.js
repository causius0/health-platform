/**
 * API client for making requests to the backend with authentication.
 */
const API_BASE = '/api'

/**
 * Make authenticated API request.
 * @param {string} endpoint - API endpoint path
 * @param {Object} options - Request options
 * @returns {Promise} Response promise
 */
async function apiRequest(endpoint, options = {}) {
  const { useAuthStore } = await import('../stores/auth')

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  }

  // Add JWT token if available
  const authStore = useAuthStore()
  if (authStore.token) {
    headers['Authorization'] = `Bearer ${authStore.token}`
  }

  const config = {
    ...options,
    headers
  }

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, config)

    if (!response.ok) {
      // Handle 401 Unauthorized (token expired)
      if (response.status === 401) {
        authStore.logout()
        window.location.href = '/'
        throw new Error('Sessione scaduta')
      }
      throw new Error(`Request failed: ${response.status}`)
    }

    return response.json()
  } catch (error) {
    console.error('API request error:', error)
    throw error
  }
}

/**
 * Login with username and password.
 * @param {string} username
 * @param {string} password
 * @returns {Promise} Response with token
 */
export async function login(username, password) {
  return apiRequest('/login', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  })
}

/**
 * Logout and clear session.
 * @returns {Promise} Response
 */
export async function logout() {
  return apiRequest('/logout', {
    method: 'POST'
  })
}

/**
 * Get current user info.
 * @returns {Promise} User data
 */
export async function getCurrentUser() {
  return apiRequest('/me')
}

/**
 * Get patient profile.
 * @param {number} patientId
 * @returns {Promise} Patient data
 */
export async function getPatient(patientId) {
  return apiRequest(`/patient/${patientId}`)
}

/**
 * Get patient exams/lab results.
 * @param {number} patientId
 * @returns {Promise} Lab results array
 */
export async function getPatientExams(patientId) {
  return apiRequest(`/patient/${patientId}/exams`)
}

/**
 * Get patient visits.
 * @param {number} patientId
 * @returns {Promise} Visits array
 */
export async function getPatientVisits(patientId) {
  return apiRequest(`/patient/${patientId}/visits`)
}

/**
 * Get all patients (for doctor).
 * @returns {Promise} Patients array
 */
export async function getDoctorPatients() {
  return apiRequest('/doctor/patients')
}

/**
 * Get patient full history.
 * @param {number} patientId
 * @returns {Promise} Patient history with exams and visits
 */
export async function getPatientHistory(patientId) {
  return apiRequest(`/patient/${patientId}/history`)
}

/**
 * Start new chat session.
 * @param {Object} data - Session data
 * @returns {Promise} Session info
 */
export async function startChatSession(data) {
  return apiRequest('/chat/start', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

/**
 * Send chat message.
 * @param {Object} data - Message data
 * @returns {Promise} Response with AI reply
 */
export async function sendChatMessage(data) {
  return apiRequest('/chat/message', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

/**
 * Delete chat session.
 * @param {Object} data - Session data
 * @returns {Promise} Response
 */
export async function deleteChatSession(data) {
  return apiRequest('/chat/session', {
    method: 'DELETE',
    body: JSON.stringify(data)
  })
}

/**
 * Get patient health alerts.
 * @param {number} patientId
 * @returns {Promise} Alerts array
 */
export async function getPatientAlerts(patientId) {
  return apiRequest(`/patient/${patientId}/alerts`)
}

/**
 * Get all doctor alerts for all patients.
 * @returns {Promise} Alerts array
 */
export async function getDoctorAlerts() {
  return apiRequest('/doctor/alerts')
}

/**
 * Get doctor alerts for specific patient.
 * @param {number} patientId
 * @returns {Promise} Alerts array
 */
export async function getDoctorPatientAlerts(patientId) {
  return apiRequest(`/doctor/patient/${patientId}/alerts`)
}

/**
 * Get prevention goals for a patient.
 */
export async function getPatientGoals(patientId) {
  return apiRequest(`/patient/${patientId}/goals`)
}

/**
 * Create a new prevention goal.
 */
export async function createGoal(data) {
  return apiRequest('/goals', { method: 'POST', body: JSON.stringify(data) })
}

/**
 * Update a goal (status / frequency).
 */
export async function updateGoal(goalId, data) {
  return apiRequest(`/goals/${goalId}`, { method: 'PATCH', body: JSON.stringify(data) })
}

/**
 * Record a weekly check-in against a goal.
 */
export async function goalCheckin(goalId, data) {
  return apiRequest(`/goals/${goalId}/checkin`, { method: 'POST', body: JSON.stringify(data) })
}

/**
 * Get or update a patient's lifestyle anamnesis.
 */
export async function getAnamnesis(patientId) {
  return apiRequest(`/patient/${patientId}/anamnesis`)
}

export async function updateAnamnesis(patientId, anamnesis) {
  return apiRequest(`/patient/${patientId}/anamnesis`, {
    method: 'PUT', body: JSON.stringify({ anamnesis: JSON.stringify(anamnesis) })
  })
}

/**
 * Cross-patient worker activity feed (operator view).
 */
export async function getDoctorActivity() {
  return apiRequest('/doctor/activity')
}
