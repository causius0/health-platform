<script setup>
import { ref, computed, onMounted } from 'vue'
import { getPatientExams } from '../utils/api'

const props = defineProps({
  patientId: {
    type: Number,
    required: true
  }
})

const loading = ref(true)
const exams = ref([])
const healthAreas = ref({
  physical_activity: { status: 'unknown', value: null, trend: 'stable' },
  nutrition: { status: 'unknown', value: null, trend: 'stable' },
  smoking: { status: 'unknown', value: null, trend: 'stable' },
  alcohol: { status: 'unknown', value: null, trend: 'stable' },
  sleep: { status: 'unknown', value: null, trend: 'stable' },
  stress: { status: 'unknown', value: null, trend: 'stable' }
})

const overallStatus = computed(() => {
  const areas = Object.values(healthAreas.value)
  const concerning = areas.filter(a => a.status === 'concerning').length
  const needs_attention = areas.filter(a => a.status === 'needs_attention').length
  const good = areas.filter(a => a.status === 'good').length

  if (concerning >= 3) return { level: 'high', message: 'Richiede attenzione prioritaria', color: 'red' }
  if (concerning >= 1 || needs_attention >= 3) return { level: 'medium', message: 'Alcune aree da migliorare', color: 'amber' }
  if (good >= 4) return { level: 'good', message: 'Buono stato di salute', color: 'teal' }
  return { level: 'stable', message: 'Stato generale stabile', color: 'green' }
})

onMounted(async () => {
  try {
    const examsData = await getPatientExams(props.patientId)
    exams.value = examsData

    // Analyze health areas based on lab results
    analyzeHealthAreas()
  } catch (error) {
    console.error('Error loading health summary:', error)
  } finally {
    loading.value = false
  }
})

function analyzeHealthAreas() {
  // Get most recent values for each health area
  const latestHbA1c = exams.value.find(e => e.test_name === 'HbA1c')
  const latestGlucose = exams.value.find(e => e.test_name === 'Glicemia a digiuno')
  const latestCholesterol = exams.value.find(e => e.test_name === 'Colesterolo totale')
  const latestHDL = exams.value.find(e => e.test_name === 'Colesterolo HDL')
  const latestLDL = exams.value.find(e => e.test_name === 'Colesterolo LDL')
  const latestTriglycerides = exams.value.find(e => e.test_name === 'Trigliceridi')
  const latestCreatinine = exams.value.find(e => e.test_name === 'Creatinina')
  const latestBloodPressureSys = exams.value.find(e => e.test_name === 'Pressione sistolica')
  const latestBloodPressureDia = exams.value.find(e => e.test_name === 'Pressione diastolica')

  // Nutrition assessment (based on lipids and glucose)
  if (latestHbA1c) {
    const hba1cValue = parseFloat(latestHbA1c.test_value)
    if (hba1cValue > 7.0) {
      healthAreas.value.nutrition = { status: 'concerning', value: 'HbA1c elevato', trend: 'worsening' }
    } else if (hba1cValue > 6.0) {
      healthAreas.value.nutrition = { status: 'needs_attention', value: 'HbA1c da monitorare', trend: 'stable' }
    } else {
      healthAreas.value.nutrition = { status: 'good', value: 'HbA1c nel target', trend: 'stable' }
    }
  }

  if (latestCholesterol) {
    const cholValue = parseFloat(latestCholesterol.test_value)
    if (cholValue > 240) {
      healthAreas.value.nutrition = { status: 'concerning', value: 'Colesterolo elevato', trend: 'worsening' }
    } else if (cholValue > 200) {
      healthAreas.value.nutrition = { status: 'needs_attention', value: 'Colesterolo da controllare', trend: 'stable' }
    }
  }

  // Physical activity (based on overall metabolic profile)
  const metabolicScore = [
    latestGlucose ? parseFloat(latestGlucose.test_value) : 100,
    latestTriglycerides ? parseFloat(latestTriglycerides.test_value) : 150,
    latestHDL ? parseFloat(latestHDL.test_value) : 50
  ]

  const avgMetabolic = metabolicScore.reduce((a, b) => a + b, 0) / metabolicScore.length
  if (avgMetabolic > 180) {
    healthAreas.value.physical_activity = { status: 'concerning', value: 'Profilo metabolico elevato', trend: 'worsening' }
  } else if (avgMetabolic > 140) {
    healthAreas.value.physical_activity = { status: 'needs_attention', value: 'Profilo metabolico da migliorare', trend: 'stable' }
  } else {
    healthAreas.value.physical_activity = { status: 'good', value: 'Profilo metabolico buono', trend: 'stable' }
  }

  // Kidney health (creatinine)
  if (latestCreatinine) {
    const creatValue = parseFloat(latestCreatinine.test_value)
    if (creatValue > 1.3) {
      healthAreas.value.stress = { status: 'needs_attention', value: 'Funzionalità renale da controllare', trend: 'stable' }
    }
  }

  // Blood pressure / cardiovascular
  if (latestBloodPressureSys && latestBloodPressureDia) {
    const sysValue = parseFloat(latestBloodPressureSys.test_value)
    const diaValue = parseFloat(latestBloodPressureDia.test_value)

    if (sysValue > 140 || diaValue > 90) {
      healthAreas.value.stress = { status: 'concerning', value: 'Pressione elevata', trend: 'worsening' }
    } else if (sysValue > 130 || diaValue > 85) {
      healthAreas.value.stress = { status: 'needs_attention', value: 'Pressione da monitorare', trend: 'stable' }
    } else {
      healthAreas.value.stress = { status: 'good', value: 'Pressione nel target', trend: 'stable' }
    }
  }

  // Set default values for areas without data
  if (healthAreas.value.smoking.status === 'unknown') {
    healthAreas.value.smoking = { status: 'good', value: 'Non fumatore', trend: 'stable' }
  }
  if (healthAreas.value.alcohol.status === 'unknown') {
    healthAreas.value.alcohol = { status: 'good', value: 'Consumo moderato', trend: 'stable' }
  }
  if (healthAreas.value.sleep.status === 'unknown') {
    healthAreas.value.sleep = { status: 'good', value: 'Buon riposo', trend: 'stable' }
  }
  if (healthAreas.value.stress.status === 'unknown') {
    healthAreas.value.stress = { status: 'good', value: 'Benessere lavorativo buono', trend: 'stable' }
  }
}

function getStatusColor(status) {
  switch (status) {
    case 'concerning': return 'red'
    case 'needs_attention': return 'amber'
    case 'good': return 'teal'
    default: return 'gray'
  }
}

function getStatusIcon(status) {
  switch (status) {
    case 'concerning': return '⚠️'
    case 'needs_attention': return '🔍'
    case 'good': return '✅'
    default: return 'ℹ️'
  }
}

function getTrendIcon(trend) {
  switch (trend) {
    case 'improving': return '📈'
    case 'worsening': return '📉'
    default: return '➡️'
  }
}
</script>

<template>
  <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-amber-100 p-6 mb-6">
    <!-- Header with overall status -->
    <div class="flex items-center gap-4 mb-6">
      <div class="w-16 h-16 rounded-full flex items-center justify-center"
           :class="{
             'bg-red-100': overallStatus.color === 'red',
             'bg-amber-100': overallStatus.color === 'amber',
             'bg-teal-100': overallStatus.color === 'teal',
             'bg-green-100': overallStatus.color === 'green'
           }">
        <span class="text-3xl">{{ overallStatus.level === 'high' ? '🚨' : overallStatus.level === 'medium' ? '⚠️' : overallStatus.level === 'good' ? '💚' : '✅' }}</span>
      </div>
      <div>
        <h2 class="text-2xl font-bold text-gray-800">Il tuo stato di salute</h2>
        <p class="text-lg font-medium" :class="{
          'text-red-600': overallStatus.color === 'red',
          'text-amber-600': overallStatus.color === 'amber',
          'text-teal-600': overallStatus.color === 'teal',
          'text-green-600': overallStatus.color === 'green'
        }">
          {{ overallStatus.message }}
        </p>
      </div>
    </div>

    <!-- Health Areas Grid -->
    <div v-if="!loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <!-- Physical Activity -->
      <div class="rounded-xl p-4 border-2 transition-all hover:shadow-md"
           :class="`border-${getStatusColor(healthAreas.physical_activity.status)}-200 bg-${getStatusColor(healthAreas.physical_activity.status)}-50`">
        <div class="flex items-start gap-3">
          <span class="text-2xl">{{ getStatusIcon(healthAreas.physical_activity.status) }}</span>
          <div class="flex-1">
            <h3 class="font-bold text-gray-800 flex items-center gap-2">
              Attività Fisica
              <span class="text-sm">{{ getTrendIcon(healthAreas.physical_activity.trend) }}</span>
            </h3>
            <p class="text-sm text-gray-600 mt-1">{{ healthAreas.physical_activity.value }}</p>
          </div>
        </div>
      </div>

      <!-- Nutrition -->
      <div class="rounded-xl p-4 border-2 transition-all hover:shadow-md"
           :class="`border-${getStatusColor(healthAreas.nutrition.status)}-200 bg-${getStatusColor(healthAreas.nutrition.status)}-50`">
        <div class="flex items-start gap-3">
          <span class="text-2xl">{{ getStatusIcon(healthAreas.nutrition.status) }}</span>
          <div class="flex-1">
            <h3 class="font-bold text-gray-800 flex items-center gap-2">
              Alimentazione
              <span class="text-sm">{{ getTrendIcon(healthAreas.nutrition.trend) }}</span>
            </h3>
            <p class="text-sm text-gray-600 mt-1">{{ healthAreas.nutrition.value }}</p>
          </div>
        </div>
      </div>

      <!-- Smoking -->
      <div class="rounded-xl p-4 border-2 transition-all hover:shadow-md"
           :class="`border-${getStatusColor(healthAreas.smoking.status)}-200 bg-${getStatusColor(healthAreas.smoking.status)}-50`">
        <div class="flex items-start gap-3">
          <span class="text-2xl">{{ getStatusIcon(healthAreas.smoking.status) }}</span>
          <div class="flex-1">
            <h3 class="font-bold text-gray-800 flex items-center gap-2">
              Fumo
              <span class="text-sm">{{ getTrendIcon(healthAreas.smoking.trend) }}</span>
            </h3>
            <p class="text-sm text-gray-600 mt-1">{{ healthAreas.smoking.value }}</p>
          </div>
        </div>
      </div>

      <!-- Alcohol -->
      <div class="rounded-xl p-4 border-2 transition-all hover:shadow-md"
           :class="`border-${getStatusColor(healthAreas.alcohol.status)}-200 bg-${getStatusColor(healthAreas.alcohol.status)}-50`">
        <div class="flex items-start gap-3">
          <span class="text-2xl">{{ getStatusIcon(healthAreas.alcohol.status) }}</span>
          <div class="flex-1">
            <h3 class="font-bold text-gray-800 flex items-center gap-2">
              Alcol
              <span class="text-sm">{{ getTrendIcon(healthAreas.alcohol.trend) }}</span>
            </h3>
            <p class="text-sm text-gray-600 mt-1">{{ healthAreas.alcohol.value }}</p>
          </div>
        </div>
      </div>

      <!-- Sleep -->
      <div class="rounded-xl p-4 border-2 transition-all hover:shadow-md"
           :class="`border-${getStatusColor(healthAreas.sleep.status)}-200 bg-${getStatusColor(healthAreas.sleep.status)}-50`">
        <div class="flex items-start gap-3">
          <span class="text-2xl">{{ getStatusIcon(healthAreas.sleep.status) }}</span>
          <div class="flex-1">
            <h3 class="font-bold text-gray-800 flex items-center gap-2">
              Sonno
              <span class="text-sm">{{ getTrendIcon(healthAreas.sleep.trend) }}</span>
            </h3>
            <p class="text-sm text-gray-600 mt-1">{{ healthAreas.sleep.value }}</p>
          </div>
        </div>
      </div>

      <!-- Stress -->
      <div class="rounded-xl p-4 border-2 transition-all hover:shadow-md"
           :class="`border-${getStatusColor(healthAreas.stress.status)}-200 bg-${getStatusColor(healthAreas.stress.status)}-50`">
        <div class="flex items-start gap-3">
          <span class="text-2xl">{{ getStatusIcon(healthAreas.stress.status) }}</span>
          <div class="flex-1">
            <h3 class="font-bold text-gray-800 flex items-center gap-2">
              Stress & Benessere Lavorativo
              <span class="text-sm">{{ getTrendIcon(healthAreas.stress.trend) }}</span>
            </h3>
            <p class="text-sm text-gray-600 mt-1">{{ healthAreas.stress.value }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading state -->
    <div v-else class="text-center py-8">
      <div class="animate-pulse flex space-x-4 justify-center">
        <div class="w-8 h-8 bg-amber-200 rounded"></div>
        <div class="w-8 h-8 bg-amber-200 rounded"></div>
        <div class="w-8 h-8 bg-amber-200 rounded"></div>
      </div>
      <p class="text-gray-500 mt-2">Analisi dello stato di salute...</p>
    </div>

    <!-- Action prompt -->
    <div class="mt-6 p-4 bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl border border-amber-100">
      <p class="text-sm text-gray-700 flex items-center gap-2">
        <svg class="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
        <strong>Suggerimento:</strong> Usa la chat in basso per ricevere consigli personalizzati su come migliorare ogni area.
      </p>
    </div>
  </div>
</template>
