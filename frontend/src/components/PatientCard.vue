<script setup>
import { computed } from 'vue'
import { formatDateItalian } from '../utils/formatters'

const props = defineProps({
  patient: {
    type: Object,
    required: true
  },
  alert: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['select'])

function handleSelect() {
  emit('select', props.patient)
}

// Determine the most relevant metric based on patient condition
const primaryMetric = computed(() => {
  const condition = props.patient.condition?.toLowerCase() || ''
  const medications = props.patient.medications || ''

  // Check what medications they're taking to determine condition better
  const hasDiabetesMeds = medications.toLowerCase().includes('insulina') ||
                      medications.toLowerCase().includes('metformina') ||
                      medications.toLowerCase().includes('metformin')

  if (condition.includes('diabete') || hasDiabetesMeds) {
    return {
      label: 'Ultimo HbA1c',
      value: props.patient.last_hba1c,
      unit: '%',
      icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
      color: 'text-amber-500'
    }
  } else if (condition.includes('ipertensione')) {
    // For hypertension, show blood pressure or creatinine
    return {
      label: 'Funzione renale',
      value: props.patient.last_creatinine || 'N/A',
      unit: 'mg/dL',
      icon: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z',
      color: 'text-teal-500'
    }
  } else {
    // Default fallback
    return {
      label: 'Ultimo valore',
      value: 'N/A',
      unit: '',
      icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
      color: 'text-gray-500'
    }
  }
})

// Alert status styling
const alertStyling = computed(() => {
  if (!props.alert) return null

  switch (props.alert.severity) {
    case 'critical':
      return {
        border: 'border-red-300',
        bg: 'bg-red-50',
        text: 'text-red-700',
        icon: '🚨',
        badge: 'bg-red-100 text-red-700'
      }
    case 'warning':
      return {
        border: 'border-amber-300',
        bg: 'bg-amber-50',
        text: 'text-amber-700',
        icon: '⚠️',
        badge: 'bg-amber-100 text-amber-700'
      }
    case 'info':
      return {
        border: 'border-teal-300',
        bg: 'bg-teal-50',
        text: 'text-teal-700',
        icon: 'ℹ️',
        badge: 'bg-teal-100 text-teal-700'
      }
    default:
      return null
  }
})

// Format trigger time
const triggerTime = computed(() => {
  if (!props.alert) return null
  // This would come from the alert's timestamp
  return props.alert.timestamp || 'Recente'
})
</script>

<template>
  <div
    @click="handleSelect"
    class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-md p-6 cursor-pointer hover:shadow-xl transition-all border hover:border-amber-200 transform hover:-translate-y-1"
    :class="alertStyling?.border || 'border-amber-100'"
  >
    <!-- Alert Banner (if flagged) -->
    <div v-if="alert && alertStyling" class="mb-4 p-3 rounded-xl" :class="alertStyling.bg">
      <div class="flex items-start gap-2">
        <span class="text-xl">{{ alertStyling.icon }}</span>
        <div class="flex-1">
          <p class="font-bold text-sm" :class="alertStyling.text">
            {{ alert.title }}
          </p>
          <p class="text-xs text-gray-600 mt-1">
            <strong>Trigger:</strong> {{ alert.message }}
          </p>
          <p class="text-xs text-gray-500 mt-0.5">
            <strong>Dal:</strong> {{ triggerTime }}
          </p>
          <p class="text-xs text-gray-700 mt-1 font-medium">
            <strong>Azione raccomandata:</strong> {{ alert.action || alert.recommendation }}
          </p>
        </div>
      </div>
    </div>

    <div class="flex items-center mb-4">
      <div class="w-14 h-14 bg-gradient-to-br from-amber-100 to-orange-100 rounded-full flex items-center justify-center mr-4 shadow-md">
        <span class="text-amber-600 font-bold text-xl">
          {{ patient.first_name[0] }}{{ patient.last_name[0] }}
        </span>
      </div>
      <div>
        <h3 class="text-lg font-bold text-gray-800">
          {{ patient.first_name }} {{ patient.last_name }}
        </h3>
        <p class="text-sm text-amber-600 font-medium">{{ patient.condition }}</p>
      </div>
      <!-- Alert badge -->
      <div v-if="alert && alertStyling" class="ml-auto px-3 py-1 rounded-full text-xs font-bold" :class="alertStyling.badge">
        {{ alert.severity === 'critical' ? 'CRITICO' : alert.severity === 'warning' ? 'ATTENZIONE' : 'INFO' }}
      </div>
    </div>

    <div class="space-y-3">
      <div class="flex justify-between items-center text-sm">
        <span class="text-gray-500 flex items-center gap-2">
          <svg class="w-4 h-4" :class="primaryMetric.color" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="primaryMetric.icon"></path>
          </svg>
          {{ primaryMetric.label }}:
        </span>
        <span class="font-bold text-gray-800" :class="!primaryMetric.value && 'text-gray-400'">
          {{ primaryMetric.value }}{{ primaryMetric.unit }}
        </span>
      </div>
      <div class="flex justify-between items-center text-sm">
        <span class="text-gray-500 flex items-center gap-2">
          <svg class="w-4 h-4 text-teal-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
          </svg>
          Ultima visita:
        </span>
        <span class="font-medium text-gray-800">
          {{ patient.last_visit_date ? formatDateItalian(patient.last_visit_date) : 'N/A' }}
        </span>
      </div>
    </div>

    <div class="mt-4 pt-4 border-t border-amber-100">
      <p class="text-xs text-amber-600 font-medium flex items-center gap-1">
        Clicca per vedere dettagli completi
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
        </svg>
      </p>
    </div>
  </div>
</template>
