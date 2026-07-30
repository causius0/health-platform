<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { login, getCurrentUser } from '../utils/api'

const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const handleSubmit = async () => {
  error.value = ''
  loading.value = true

  try {
    const response = await login(username.value, password.value)

    if (response.token) {
      authStore.setToken(response.token)
      try {
        const userData = await getCurrentUser()
        authStore.setUser(userData)
      } catch (userError) {
        console.error('Error fetching user data:', userError)
        if (response.user) {
          authStore.setUser(response.user)
        }
      }
    } else if (response.error) {
      error.value = response.error
    }
  } catch (err) {
    error.value = 'Errore di connessione. Riprova.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-50 px-4">
    <div class="max-w-md w-full">
      <div class="bg-white rounded-lg shadow-sm border border-slate-200 p-8">
        <div class="text-center mb-8">
          <div class="inline-flex items-center justify-center w-12 h-12 bg-blue-600 rounded-lg mb-4">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path>
            </svg>
          </div>

          <h1 class="text-2xl font-semibold text-slate-800 mb-1">Health Platform</h1>
          <p class="text-sm text-slate-500">Accedi al tuo account</p>
        </div>

        <form @submit.prevent="handleSubmit" class="space-y-4">
          <div>
            <label for="username" class="block text-sm font-medium text-slate-700 mb-1">
              Nome utente
            </label>
            <input
              id="username"
              v-model="username"
              type="text"
              required
              class="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
              placeholder="Inserisci il tuo nome utente"
            />
          </div>

          <div>
            <label for="password" class="block text-sm font-medium text-slate-700 mb-1">
              Password
            </label>
            <input
              id="password"
              v-model="password"
              type="password"
              required
              class="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
              placeholder="Inserisci la tua password"
            />
          </div>

          <div
            v-if="error"
            class="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-md text-sm"
          >
            {{ error }}
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
          >
            {{ loading ? 'Accesso in corso...' : 'Accedi' }}
          </button>
        </form>

        <div class="mt-6 pt-6 border-t border-slate-200 text-center">
          <p class="text-xs text-slate-500">Demo credentials available</p>
        </div>
      </div>
    </div>
  </div>
</template>
