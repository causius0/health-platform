<script setup>
import { onMounted, computed } from 'vue'
import { useAuthStore } from './stores/auth'
import LoginForm from './components/LoginForm.vue'
import PatientDashboard from './components/PatientDashboard.vue'
import DoctorDashboard from './components/DoctorDashboard.vue'

const authStore = useAuthStore()

onMounted(() => {
  // Auth state is now loaded from localStorage by the auth store
  // If we have a token but no user data, try to fetch it
  if (authStore.token && !authStore.user) {
    import('./utils/api').then(({ getCurrentUser }) => {
      getCurrentUser()
        .then(userData => {
          authStore.setUser(userData)
        })
        .catch(() => {
          // Token might be expired, clear it
          authStore.setToken(null)
        })
    })
  }
})

const currentView = computed(() => {
  if (!authStore.isAuthenticated) {
    return 'login'
  }
  if (authStore.userRole === 'patient') {
    return 'patient'
  }
  if (authStore.userRole === 'doctor') {
    return 'doctor'
  }
  return 'login'
})
</script>

<template>
  <div id="app" class="min-h-screen bg-slate-50">
    <LoginForm v-if="currentView === 'login'" />
    <PatientDashboard v-else-if="currentView === 'patient'" />
    <DoctorDashboard v-else-if="currentView === 'doctor'" />
  </div>
</template>
