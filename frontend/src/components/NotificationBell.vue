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

const emit = defineEmits(['alertClicked'])

const alerts = ref([])
const showDropdown = ref(false)
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

const alertCount = computed(() => sortedAlerts.value.length)

// Show max 3 alerts in dropdown, indicate if more
const displayAlerts = computed(() => {
  return sortedAlerts.value.slice(0, 3)
})

const hasMoreAlerts = computed(() => {
  return sortedAlerts.value.length > 3
})

onMounted(async () => {
  try {
    if (props.role === 'patient' && props.patientId) {
      alerts.value = await getPatientAlerts(props.patientId)
    } else if (props.role === 'doctor') {
      alerts.value = await getDoctorAlerts()
    }
  } catch (error) {
    console.error('Error loading alerts:', error)
  }
})

function toggleDropdown() {
  showDropdown.value = !showDropdown.value
}

function closeDropdown() {
  showDropdown.value = false
}

function handleAlertClick(alert) {
  emit('alertClicked', alert)
  closeDropdown()
}

function dismissAlert(title, event) {
  event.stopPropagation()
  dismissedAlerts.value.add(title)
}

function getSeverityColor(severity) {
  switch (severity) {
    case 'critical': return 'bg-red-500'
    case 'warning': return 'bg-amber-500'
    case 'info': return 'bg-teal-500'
    default: return 'bg-gray-500'
  }
}

function getSeverityBorder(severity) {
  switch (severity) {
    case 'critical': return 'border-red-200 bg-red-50'
    case 'warning': return 'border-amber-200 bg-amber-50'
    case 'info': return 'border-teal-200 bg-teal-50'
    default: return 'border-gray-200 bg-gray-50'
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
  <div class="notification-bell relative">
    <!-- Bell Button -->
    <button
      @click="toggleDropdown"
      class="relative p-2 rounded-full hover:bg-amber-50 transition-colors"
      title="Avvisi sanitari"
    >
      <!-- Bell Icon -->
      <svg class="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
        ></path>
      </svg>

      <!-- Alert Badge -->
      <div
        v-if="alertCount > 0"
        :class="[
          'absolute -top-1 -right-1 w-5 h-5 rounded-full text-white text-xs font-bold flex items-center justify-center',
          getSeverityColor(hasCriticalAlerts ? 'critical' : sortedAlerts[0]?.severity || 'info')
        ]"
      >
        {{ alertCount > 9 ? '9+' : alertCount }}
      </div>

      <!-- Critical Pulse Animation -->
      <div
        v-if="hasCriticalAlerts"
        class="absolute inset-0 rounded-full border-2 border-red-500 animate-ping opacity-75"
      ></div>
    </button>

    <!-- Dropdown Panel -->
    <div
      v-if="showDropdown"
      class="absolute right-0 mt-2 w-96 bg-white rounded-2xl shadow-2xl border border-amber-100 z-50 max-h-96 overflow-hidden flex flex-col"
    >
      <!-- Header -->
      <div class="px-4 py-3 bg-gradient-to-r from-amber-50 to-orange-50 border-b border-amber-100">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <svg class="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path>
            </svg>
            <span class="font-bold text-gray-800">Avvisi Sanitari</span>
          </div>
          <span class="text-xs text-gray-500">{{ alertCount }} {{ alertCount === 1 ? 'avviso' : 'avvisi' }}</span>
        </div>
      </div>

      <!-- Alert List -->
      <div class="flex-1 overflow-y-auto p-3 space-y-2">
        <!-- No Alerts -->
        <div v-if="sortedAlerts.length === 0" class="text-center py-6">
          <div class="w-12 h-12 bg-gradient-to-br from-teal-100 to-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg class="w-6 h-6 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
          </div>
          <p class="text-gray-600 font-medium text-sm">Tutto bene! 🎉</p>
          <p class="text-gray-500 text-xs">Nessun avviso al momento</p>
        </div>

        <!-- Alert Items -->
        <div
          v-for="alert in displayAlerts"
          :key="alert.title"
          @click="handleAlertClick(alert)"
          :class="['rounded-lg border p-3 cursor-pointer transition-all hover:shadow-md', getSeverityBorder(alert.severity)]"
        >
          <div class="flex items-start gap-2">
            <!-- Icon -->
            <div class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-white border border-current opacity-30">
              <svg class="w-4 h-4 text-current" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="getIconForType(alert.icon)"></path>
              </svg>
            </div>

            <!-- Content -->
            <div class="flex-1 min-w-0">
              <div class="flex items-start justify-between gap-1">
                <h4 class="font-bold text-gray-800 text-xs">
                  {{ alert.title }}
                </h4>
                <button
                  @click="dismissAlert(alert.title, $event)"
                  class="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
                  title="Ignora"
                >
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                  </svg>
                </button>
              </div>

              <p class="text-xs text-gray-700 mt-1 line-clamp-2">
                {{ alert.message }}
              </p>
            </div>
          </div>
        </div>

        <!-- More Alerts Indicator -->
        <div
          v-if="hasMoreAlerts"
          class="text-center py-2 px-3 bg-amber-50 rounded-lg border border-amber-100 cursor-pointer hover:bg-amber-100 transition-colors"
          @click="handleAlertClick({ title: 'show_all_alerts' })"
        >
          <p class="text-xs font-medium text-amber-700">
            Vedi tutti gli {{ alertCount }} avvisi →
          </p>
        </div>
      </div>

      <!-- Footer -->
      <div class="px-4 py-2 bg-gradient-to-r from-amber-50 to-orange-50 border-t border-amber-100">
        <p class="text-xs text-gray-500 text-center">
          💡 Basato sui dati clinici più recenti
        </p>
      </div>
    </div>

    <!-- Overlay to close dropdown when clicking outside -->
    <div
      v-if="showDropdown"
      @click="closeDropdown"
      class="fixed inset-0 z-40"
    ></div>
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
