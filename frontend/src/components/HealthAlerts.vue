<script setup>
import { ref, computed, onMounted } from 'vue'
import { getPatientAlerts, getDoctorAlerts } from '../utils/api'

const props = defineProps({
  patientId: {
    type: Number,
    default: null
  },
  role: {
    type: String,
    default: 'patient' // or 'doctor'
  }
})

const alerts = ref([])
const loading = ref(true)
const dismissedAlerts = ref(new Set())

const severityOrder = { critical: 0, warning: 1, info: 2 }

const sortedAlerts = computed(() => {
  return alerts.value
    .filter(alert => !dismissedAlerts.value.has(alert.title))
    .sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity])
})

const hasCriticalAlerts = computed(() => {
  return sortedAlerts.value.some(alert => alert.severity === 'critical')
})

const hasWarningAlerts = computed(() => {
  return sortedAlerts.value.some(alert => alert.severity === 'warning')
})

const alertCount = computed(() => sortedAlerts.value.length)

onMounted(async () => {
  try {
    if (props.role === 'patient' && props.patientId) {
      alerts.value = await getPatientAlerts(props.patientId)
    } else if (props.role === 'doctor') {
      alerts.value = await getDoctorAlerts()
    }
  } catch (error) {
    console.error('Error loading alerts:', error)
  } finally {
    loading.value = false
  }
})

function dismissAlert(title) {
  dismissedAlerts.value.add(title)
}

function getSeverityClasses(severity) {
  switch (severity) {
    case 'critical':
      return {
        container: 'border-red-200 bg-gradient-to-r from-red-50 to-pink-50',
        header: 'bg-red-100 text-red-800',
        icon: 'text-red-600',
        button: 'bg-red-500 hover:bg-red-600'
      }
    case 'warning':
      return {
        container: 'border-amber-200 bg-gradient-to-r from-amber-50 to-orange-50',
        header: 'bg-amber-100 text-amber-800',
        icon: 'text-amber-600',
        button: 'bg-amber-500 hover:bg-amber-600'
      }
    case 'info':
      return {
        container: 'border-teal-200 bg-gradient-to-r from-teal-50 to-green-50',
        header: 'bg-teal-100 text-teal-800',
        icon: 'text-teal-600',
        button: 'bg-teal-500 hover:bg-teal-600'
      }
    default:
      return {
        container: 'border-gray-200 bg-gray-50',
        header: 'bg-gray-100 text-gray-800',
        icon: 'text-gray-600',
        button: 'bg-gray-500 hover:bg-gray-600'
      }
  }
}

function getIconForType(iconType) {
  const icons = {
    warning: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
    alert: 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
    critical: 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
    kidney: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
    heart: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z',
    trend_up: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6',
    trend_down: 'M13 17h8m0 0V9m0 8l-8-8-4 4-6-6',
    medication: 'M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z',
    activity: 'M13 10V3L4 14h7v7l9-11h-7z',
    diet: 'M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z',
    calendar: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
    glucose: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z'
  }

  return icons[iconType] || icons.alert
}
</script>

<template>
  <div class="health-alerts">
    <!-- Alert Summary Badge -->
    <div v-if="!loading && alertCount > 0" class="mb-6">
      <div class="flex items-center gap-3 bg-white rounded-2xl shadow-md border border-amber-100 p-4">
        <div class="flex items-center gap-2">
          <div v-if="hasCriticalAlerts" class="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
          <div v-else-if="hasWarningAlerts" class="w-3 h-3 bg-amber-500 rounded-full"></div>
          <div v-else class="w-3 h-3 bg-teal-500 rounded-full"></div>

          <span class="font-semibold text-gray-800">
            {{ alertCount }} {{ alertCount === 1 ? 'avviso' : 'avvisi' }} sanitari
          </span>
        </div>

        <div class="flex-1"></div>

        <span class="text-sm text-gray-500">
          {{ hasCriticalAlerts ? 'Alcuni richiedono attenzione immediata' : 'Controlla regolarmente' }}
        </span>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-500 mx-auto"></div>
      <p class="text-gray-600 mt-2">Caricamento avvisi...</p>
    </div>

    <!-- No Alerts State -->
    <div v-else-if="sortedAlerts.length === 0" class="text-center py-8">
      <div class="w-16 h-16 bg-gradient-to-br from-teal-100 to-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg class="w-8 h-8 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
      </div>
      <p class="text-gray-600 font-medium">Tutto bene! 🎉</p>
      <p class="text-gray-500 text-sm">Nessun avviso al momento</p>
    </div>

    <!-- Alerts List -->
    <div v-else class="space-y-4">
      <div
        v-for="alert in sortedAlerts"
        :key="alert.title"
        :class="['rounded-xl border p-4 transition-all hover:shadow-md', getSeverityClasses(alert.severity).container]"
      >
        <div class="flex items-start gap-3">
          <!-- Icon -->
          <div class="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center" :class="getSeverityClasses(alert.severity).header">
            <svg class="w-5 h-5" :class="getSeverityClasses(alert.severity).icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="getIconForType(alert.icon)"></path>
            </svg>
          </div>

          <!-- Content -->
          <div class="flex-1 min-w-0">
            <div class="flex items-start justify-between gap-2">
              <h4 class="font-bold text-gray-800 text-sm">
                {{ alert.title }}
              </h4>
              <button
                @click="dismissAlert(alert.title)"
                class="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
                title="Ignora questo avviso"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </button>
            </div>

            <p class="text-sm text-gray-700 mt-1">
              {{ alert.message }}
            </p>

            <div class="mt-3 bg-white/60 rounded-lg p-3 border border-current opacity-20">
              <p class="text-xs font-medium text-gray-800 flex items-start gap-2">
                <svg class="w-4 h-4 flex-shrink-0 text-current" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <span>{{ alert.recommendation || alert.action }}</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Info about alerts -->
    <div class="mt-6 text-center text-xs text-gray-500">
      <p>💡 Gli avvisi si basano sui tuoi dati clinici più recenti</p>
    </div>
  </div>
</template>
