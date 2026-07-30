<script setup>
import { ref, computed } from 'vue'
import { formatDateItalian } from '../utils/formatters'

const props = defineProps({
  patientId: {
    type: Number,
    required: true
  }
})

// Sample adherence data (in production, this would come from the backend)
const adherenceHistory = ref([
  {
    week: '2026-07-21',
    action: 'Camminata giornaliera 30 minuti',
    targetDays: 5,
    completedDays: 4,
    adherenceRate: 80,
    status: 'good'
  },
  {
    week: '2026-07-14',
    action: 'Riduzione zuccheri semplici',
    targetDays: 7,
    completedDays: 6,
    adherenceRate: 86,
    status: 'excellent'
  },
  {
    week: '2026-07-07',
    action: 'Esercizi di respirazione',
    targetDays: 5,
    completedDays: 3,
    adherenceRate: 60,
    status: 'needs_improvement'
  },
  {
    week: '2026-06-30',
    action: 'Monitoring glicemia',
    targetDays: 7,
    completedDays: 7,
    adherenceRate: 100,
    status: 'excellent'
  }
])

const currentWeekAction = ref('Camminata giornaliera 30 minuti')
const currentWeekTarget = ref(5)
const currentWeekCompleted = ref(2)

const overallAdherence = computed(() => {
  if (adherenceHistory.value.length === 0) return 0
  const total = adherenceHistory.value.reduce((sum, week) => sum + week.adherenceRate, 0)
  return Math.round(total / adherenceHistory.value.length)
})

const adherenceTrend = computed(() => {
  if (adherenceHistory.value.length < 2) return 'stable'

  const recent = adherenceHistory.value.slice(0, 4)
  const firstHalf = recent.slice(0, Math.ceil(recent.length / 2))
  const secondHalf = recent.slice(Math.ceil(recent.length / 2))

  const firstAvg = firstHalf.reduce((sum, w) => sum + w.adherenceRate, 0) / firstHalf.length
  const secondAvg = secondHalf.reduce((sum, w) => sum + w.adherenceRate, 0) / secondHalf.length

  if (secondAvg > firstAvg + 10) return 'improving'
  if (secondAvg < firstAvg - 10) return 'declining'
  return 'stable'
})

function getStatusBadge(status) {
  switch (status) {
    case 'excellent':
      return 'bg-teal-100 text-teal-700'
    case 'good':
      return 'bg-green-100 text-green-700'
    case 'needs_improvement':
      return 'bg-amber-100 text-amber-700'
    default:
      return 'bg-gray-100 text-gray-700'
  }
}

function getStatusText(status) {
  switch (status) {
    case 'excellent': return 'Eccellente'
    case 'good': return 'Buono'
    case 'needs_improvement': return 'Da migliorare'
    default: return 'N/A'
  }
}

function getTrendIcon(trend) {
  switch (trend) {
    case 'improving': return '📈 Miglioramento'
    case 'declining': return '📉 In calo'
    default: return '➡️ Stabile'
  }
}

function getTrendColor(trend) {
  switch (trend) {
    case 'improving': return 'text-teal-600'
    case 'declining': return 'text-amber-600'
    default: return 'text-gray-600'
  }
}
</script>

<template>
  <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-amber-100 p-6 mb-6">
    <h3 class="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
      <svg class="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
      </svg>
      Storico Aderenza e Progressi
    </h3>

    <!-- Overall Summary -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div class="bg-gradient-to-br from-teal-50 to-green-50 rounded-xl p-4 border border-teal-100">
        <p class="text-xs text-teal-600 font-medium mb-1">Aderenza Complessiva</p>
        <p class="text-2xl font-bold text-teal-700">{{ overallAdherence }}%</p>
        <p class="text-xs text-teal-600 mt-1">{{ adherenceHistory.length }} settimane monitorate</p>
      </div>

      <div class="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl p-4 border border-amber-100">
        <p class="text-xs text-amber-600 font-medium mb-1">Tendenza</p>
        <p class="text-lg font-bold text-amber-700 flex items-center gap-1">
          <span>{{ getTrendIcon(adherenceTrend).split(' ')[0] }}</span>
          {{ getTrendIcon(adherenceTrend).split(' ')[1] }}
        </p>
        <p class="text-xs text-amber-600 mt-1">Ultime 4 settimane</p>
      </div>

      <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-4 border border-purple-100">
        <p class="text-xs text-purple-600 font-medium mb-1">Settimana Corrente</p>
        <p class="text-lg font-bold text-purple-700">{{ currentWeekCompleted }}/{{ currentWeekTarget }} giorni</p>
        <p class="text-xs text-purple-600 mt-1">{{ currentWeekAction }}</p>
      </div>
    </div>

    <!-- Current Week Progress -->
    <div class="mb-6 p-4 bg-amber-50 rounded-xl border border-amber-200">
      <h4 class="font-bold text-gray-800 mb-3">Progresso Settimana Corrente</h4>
      <div class="mb-3">
        <div class="flex justify-between text-sm mb-1">
          <span class="text-gray-600">{{ currentWeekAction }}</span>
          <span class="font-bold text-amber-700">{{ Math.round((currentWeekCompleted / currentWeekTarget) * 100) }}%</span>
        </div>
        <div class="w-full bg-amber-200 rounded-full h-2">
          <div class="bg-amber-500 h-2 rounded-full transition-all" :style="{ width: (currentWeekCompleted / currentWeekTarget) * 100 + '%' }"></div>
        </div>
      </div>
      <p class="text-xs text-gray-600">
        {{ currentWeekCompleted }} giorni completati su {{ currentWeekTarget }} obiettivi
      </p>
    </div>

    <!-- History -->
    <div>
      <h4 class="font-bold text-gray-800 mb-3">Storico Settimanale</h4>
      <div class="space-y-2">
        <div
          v-for="(week, index) in adherenceHistory"
          :key="index"
          class="flex items-center justify-between p-3 bg-white rounded-lg border border-amber-100 hover:border-amber-200 transition-colors"
        >
          <div class="flex-1">
            <p class="text-sm font-medium text-gray-800">{{ week.action }}</p>
            <p class="text-xs text-gray-500">Settimana del {{ formatDateItalian(week.week) }}</p>
          </div>
          <div class="flex items-center gap-4">
            <div class="text-center">
              <p class="text-xs text-gray-500">Giorni</p>
              <p class="text-sm font-bold text-gray-700">{{ week.completedDays }}/{{ week.targetDays }}</p>
            </div>
            <div class="text-center">
              <p class="text-xs text-gray-500">Aderenza</p>
              <p class="text-sm font-bold" :class="week.adherenceRate >= 80 ? 'text-teal-600' : week.adherenceRate >= 60 ? 'text-amber-600' : 'text-red-600'">
                {{ week.adherenceRate }}%
              </p>
            </div>
            <span class="px-3 py-1 rounded-full text-xs font-bold" :class="getStatusBadge(week.status)">
              {{ getStatusText(week.status) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Motivational Message -->
    <div class="mt-6 p-4 bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl border border-amber-100">
      <p class="text-sm text-gray-700 flex items-center gap-2">
        <svg class="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
        </svg>
        <strong>Continue così!</strong> Ogni azione conta. La costanza è la chiave per raggiungere i tuoi obiettivi di salute.
      </p>
    </div>
  </div>
</template>
