<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement } from 'chart.js/auto'
import { getPatientExams } from '../utils/api'

ChartJS.register(Title, Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement)

const props = defineProps({
  patientId: {
    type: Number,
    required: true
  },
  role: {
    type: String,
    default: 'patient'
  }
})

const exams = ref([])
const loading = ref(true)

// Available metrics for chart
const availableMetrics = computed(() => {
  if (!exams.value.length) return []

  const uniqueTests = [...new Set(exams.value.map(exam => exam.test_name))]
  return uniqueTests.map(testName => {
    const samples = exams.value.filter(exam => exam.test_name === testName).slice(0, 5)
    const latestValue = samples[0]?.test_value || 'N/A'
    const unit = samples[0]?.unit || ''

    return {
      name: testName,
      label: formatMetricLabel(testName),
      latestValue: `${latestValue}${unit}`,
      unit: unit,
      color: getMetricColor(testName),
      selected: false
    }
  })
})

// Selected metrics for display
const selectedMetrics = ref([])

// Chart data
const chartData = computed(() => {
  if (!selectedMetrics.value.length || !exams.value.length) {
    return {
      labels: [],
      datasets: []
    }
  }

  // Get all unique dates from exams
  const allDates = [...new Set(exams.value
    .filter(exam => selectedMetrics.value.includes(exam.test_name))
    .map(exam => exam.date)
  )].sort().reverse().slice(-12) // Last 12 dates max

  const datasets = selectedMetrics.value.map((metricName, index) => {
    const metricExams = exams.value.filter(exam => exam.test_name === metricName)

    const data = allDates.map(date => {
      const exam = metricExams.find(e => e.date === date)
      return exam ? parseFloat(exam.test_value) : null
    })

    const color = getMetricColor(metricName)

    return {
      label: formatMetricLabel(metricName),
      data: data,
      borderColor: color,
      backgroundColor: color + '20',
      tension: 0.3,
      fill: false,
      pointRadius: 4,
      pointHoverRadius: 6,
      spanGaps: true
    }
  })

  return {
    labels: allDates.map(date => formatDateItalian(date)),
    datasets: datasets
  }
})

// Chart options
const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false // Using custom legend instead
    },
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.9)',
      titleColor: '#1f2937',
      bodyColor: '#4b5563',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      padding: 12,
      displayColors: true,
      callbacks: {
        label: function(context) {
          const label = context.dataset.label || ''
          const value = context.parsed.y
          const dataset = context.dataset
          const dataIndex = context.dataIndex
          const date = chartData.value.labels[dataIndex]

          // Find original data for unit
          const metricName = availableMetrics.value.find(m => m.name === dataset.label)?.name
          const unit = availableMetrics.value.find(m => m.name === metricName)?.unit || ''

          return `${date}: ${value} ${unit}`
        }
      }
    }
  },
  scales: {
    y: {
      beginAtZero: false,
      grid: {
        color: '#f3f4f6'
      },
      ticks: {
        color: '#6b7280',
        font: {
          size: 11
        }
      }
    },
    x: {
      grid: {
        display: false
      },
      ticks: {
        color: '#6b7280',
        font: {
          size: 11
        }
      }
    }
  },
  interaction: {
    mode: 'index',
    intersect: false,
  },
  elements: {
    point: {
      radius: 4,
      hoverRadius: 6
    }
  }
}))

// Toggle metric selection
function toggleMetric(metricName) {
  const index = selectedMetrics.value.indexOf(metricName)
  if (index > -1) {
    selectedMetrics.value.splice(index, 1)
  } else {
    if (selectedMetrics.value.length < 5) { // Max 5 metrics at once
      selectedMetrics.value.push(metricName)
    }
  }
}

// Auto-select most important metrics on load
function autoSelectMetrics() {
  const priorityMetrics = ['HbA1c', 'Glicemia a digiuno', 'Colesterolo LDL', 'Creatinina']

  priorityMetrics.forEach(metric => {
    if (availableMetrics.value.find(m => m.name === metric) && selectedMetrics.value.length < 3) {
      selectedMetrics.value.push(metric)
    }
  })
}

function formatMetricLabel(testName) {
  const labels = {
    'HbA1c': 'HbA1c',
    'Glicemia a digiuno': 'Glicemia',
    'Glicemia postprandiale': 'Glicemia post-prandiale',
    'Colesterolo LDL': 'Colesterolo LDL',
    'Colesterolo HDL': 'Colesterolo HDL',
    'Colesterolo totale': 'Colesterolo totale',
    'Trigliceridi': 'Trigliceridi',
    'Creatinina': 'Creatinina',
    'eGFR': 'Filtrazione glomerulare',
    'Pressione arteriosa': 'Pressione'
  }

  return labels[testName] || testName
}

function getMetricColor(testName) {
  const colors = {
    'HbA1c': '#f59e0b',          // Amber
    'Glicemia a digiuno': '#ef4444',  // Red
    'Glicemia postprandiale': '#f97316', // Orange
    'Colesterolo LDL': '#8b5cf6',    // Purple
    'Colesterolo HDL': '#10b981',    // Emerald
    'Colesterolo totale': '#6366f1',  // Blue
    'Trigliceridi': '#ec4899',       // Pink
    'Creatinina': '#06b6d4',         // Cyan
    'eGFR': '#84cc16',               // Lime
    'Pressione arteriosa': '#14b8a6' // Teal
  }

  return colors[testName] || '#6b7280'
}

function formatDateItalian(dateStr) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('it-IT', { day: '2-digit', month: 'short' })
}

// Load exam data
async function loadChartData() {
  try {
    loading.value = true
    exams.value = await getPatientExams(props.patientId)

    // Auto-select important metrics
    autoSelectMetrics()
  } catch (error) {
    console.error('Error loading chart data:', error)
  } finally {
    loading.value = false
  }
}

// Watch for patient changes
watch(() => props.patientId, () => {
  if (props.patientId) {
    selectedMetrics.value = []
    loadChartData()
  }
}, { immediate: true })
</script>

<template>
  <div class="health-chart">
    <!-- Chart Container -->
    <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-amber-100 overflow-hidden">
      <!-- Header -->
      <div class="bg-gradient-to-r from-amber-50 to-orange-50 px-6 py-4 border-b border-amber-100">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-amber-100 to-orange-100 rounded-full flex items-center justify-center">
              <svg class="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3-3M3 6l3 3 3-3M12 21V3a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
              </svg>
            </div>
            <div>
              <h3 class="text-lg font-bold text-gray-800">Andamento Valori</h3>
              <p class="text-xs text-gray-600">Clicca sulle metriche per visualizzarle</p>
            </div>
          </div>
          <div class="text-xs text-gray-500">
            {{ selectedMetrics.length }} metriche selezionate
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="p-8 text-center">
        <div class="animate-pulse flex space-x-4 justify-center mb-4">
          <div class="w-8 h-8 bg-amber-200 rounded"></div>
          <div class="w-8 h-8 bg-amber-200 rounded"></div>
          <div class="w-8 h-8 bg-amber-200 rounded"></div>
        </div>
        <p class="text-gray-500">Caricamento dati grafico...</p>
      </div>

      <!-- No Data State -->
      <div v-else-if="!exams.length" class="p-8 text-center">
        <div class="w-16 h-16 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3-3M3 6l3 3 3-3M12 21V3a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
          </svg>
        </div>
        <p class="text-gray-600 font-medium">Nessun dato disponibile</p>
        <p class="text-gray-500 text-sm">I grafici appariranno qui quando avrai esami</p>
      </div>

      <!-- Chart Content -->
      <div v-else>
        <!-- Metric Toggles -->
        <div class="px-6 py-4 border-b border-gray-100">
          <p class="text-xs font-medium text-gray-600 mb-3">Seleziona metriche da visualizzare (max 5):</p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="metric in availableMetrics"
              :key="metric.name"
              @click="toggleMetric(metric.name)"
              :class="[
                'px-3 py-2 rounded-lg text-xs font-medium transition-all border',
                selectedMetrics.includes(metric.name)
                  ? 'border-current shadow-sm'
                  : 'border-transparent opacity-60 hover:opacity-100'
              ]"
              :style="selectedMetrics.includes(metric.name) ? {
                backgroundColor: metric.color + '15',
                color: metric.color,
                borderColor: metric.color
              } : {}"
            >
              <div class="flex items-center gap-1">
                <div
                  class="w-2 h-2 rounded-full"
                  :style="{ backgroundColor: metric.color }"
                ></div>
                <span>{{ metric.label }}</span>
              </div>
            </button>
          </div>
        </div>

        <!-- Chart Area -->
        <div v-if="selectedMetrics.length > 0" class="p-6">
          <div class="h-80">
            <Line
              :data="chartData"
              :options="chartOptions"
            />
          </div>
        </div>

        <!-- Empty Chart State -->
        <div v-else class="p-12 text-center">
          <div class="w-20 h-20 bg-gradient-to-br from-amber-50 to-orange-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg class="w-10 h-10 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3-3M3 6l3 3 3-3M12 21V3a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
            </svg>
          </div>
          <p class="text-gray-600 font-medium mb-2">Seleziona una metrica per vedere il grafico</p>
          <p class="text-gray-500 text-sm">Clicca sui pulsanti colorati sopra per iniziare</p>
        </div>
      </div>
    </div>
  </div>
</template>
