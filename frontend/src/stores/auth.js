import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  // Load persisted state from localStorage
  const persistedToken = localStorage.getItem('token')
  const persistedUser = localStorage.getItem('user')
  const persistedRole = localStorage.getItem('userRole')

  const token = ref(persistedToken || null)
  const user = ref(persistedUser ? JSON.parse(persistedUser) : null)
  const userRole = ref(persistedRole || null)
  const isAuthenticated = ref(!!persistedToken)

  const setToken = (newToken) => {
    token.value = newToken
    if (newToken) {
      localStorage.setItem('token', newToken)
      isAuthenticated.value = true
    } else {
      localStorage.removeItem('token')
      isAuthenticated.value = false
      user.value = null
      userRole.value = null
      localStorage.removeItem('user')
      localStorage.removeItem('userRole')
    }
  }

  const setUser = (userData) => {
    user.value = userData
    userRole.value = userData?.role
    if (userData) {
      localStorage.setItem('user', JSON.stringify(userData))
      localStorage.setItem('userRole', userData?.role || '')
    }
  }

  const logout = () => {
    token.value = null
    user.value = null
    userRole.value = null
    isAuthenticated.value = false
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('userRole')
  }

  return {
    token,
    user,
    userRole,
    isAuthenticated,
    setToken,
    setUser,
    logout
  }
})
