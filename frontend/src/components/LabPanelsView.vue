<script setup>
import { ref, computed, onMounted } from 'vue'
import { getPatientExams } from '../utils/api'
import { formatDateItalian } from '../utils/formatters'

const props = defineProps({
  patientId: {
    type: Number,
    required: true
  }
})

const exams = ref([])
const loading = ref(true)
const selectedPanel = ref('all')
const selectedEncounter = ref('latest')

// Organize exams into encounters and panels
const organizedData = computed(() => {
  if (!exams.value.length) return { encounters: [], panels: {} }

  // Group by date (encounter)
  const encounters = {}
  exams.value.forEach(exam => {
    if (!encounters[exam.date]) {
      encounters[exam.date] = {
        date: exam.date,
        tests: []
      }
    }
    encounters[exam.date].tests.push(exam)
  })

  // Sort encounters by date (newest first)
  const sortedEncounters = Object.values(encounters).sort((a, b) =>
    new Date(b.date) - new Date(a.date)
  )

  // Group tests by panel type for each encounter
  const panelTypes = {
    emogramma: {
      name: 'Emogramma',
      icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
      color: 'red',
      tests: ['Emoglobina', 'Ematocrito', 'Globuli bianchi', 'Piastrine', 'RBC', 'MCV', 'MCH', 'MCHC']
    },
    funzionalita_renale: {
      name: 'Funzionalità Renale',
      icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
      color: 'cyan',
      tests: ['Creatinina', 'BUN azoto', 'eGFR', 'Microalbuminuria', 'Urea', 'Acido urico']
    },
    funzionalita_epatica: {
      name: 'Funzionalità Epatica',
      icon: 'M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z',
      color: 'amber',
      tests: ['ALT', 'AST', 'Gamma-GT', 'Bilirubina totale', 'Bilirubina diretta', 'Albumina', 'Proteine totali']
    },
    panel_diabete: {
      name: 'Panel Diabete',
      icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
      color: 'purple',
      tests: ['HbA1c', 'Glicemia a digiuno', 'Glicemia postprandiale', 'Insulina', 'Peptide C']
    },
    profilo_lipidico: {
      name: 'Profilo Lipidico',
      icon: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z',
      color: 'pink',
      tests: ['Colesterolo totale', 'Colesterolo LDL', 'Colesterolo HDL', 'Trigliceridi']
    },
    elettroliti: {
      name: 'Elettroliti',
      icon: 'M13 10V3L4 14h7v7l9-11h-7z',
      color: 'yellow',
      tests: ['Sodio', 'Potassio', 'Cloro', 'Magnesio', 'Calcio', 'Fosforo']
    },
    marcatori_cardiovascolari: {
      name: 'Marcatori Cardiovascolari',
      icon: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z',
      color: 'red',
      tests: ['Omocisteina', 'Troponina', 'BNP', 'PCR', 'VES']
    },
    funzionalita_tiroidea: {
      name: 'Funzionalità Tiroidea',
      icon: 'M13 10V3L4 14h7v7l9-11h-7z',
      color: 'teal',
      tests: ['TSH', 'T3 libero', 'T4 libero']
    },
    vitamine: {
      name: 'Vitamine',
      icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
      color: 'green',
      tests: ['Vitamina D', 'Vitamina B12', 'Acido folico', 'Ferritina', 'Ferro sierico']
    }
  }

  // Organize tests by panel for each encounter
  const panelsByEncounter = {}

  sortedEncounters.forEach(encounter => {
    panelsByEncounter[encounter.date] = {}

    Object.entries(panelTypes).forEach(([panelKey, panelInfo]) => {
      const panelTests = encounter.tests.filter(test =>
        panelInfo.tests.some(testName =>
          test.test_name.toLowerCase().includes(testName.toLowerCase()) ||
          testName.toLowerCase().includes(test.test_name.toLowerCase())
        )
      )

      if (panelTests.length > 0) {
        panelsByEncounter[encounter.date][panelKey] = {
          ...panelInfo,
          tests: panelTests
        }
      }
    })
  })

  return {
    encounters: sortedEncounters,
    panels: panelTypes,
    panelsByEncounter
  }
})

// Filter encounters based on selection
const filteredEncounters = computed(() => {
  if (selectedEncounter.value === 'latest') {
    return organizedData.value.encounters.slice(0, 1)
  } else if (selectedEncounter.value === 'recent') {
    return organizedData.value.encounters.slice(0, 3)
  } else {
    return organizedData.value.encounters
  }
})

// Get panel colors
const getPanelColor = (color) => {
  const colors = {
    red: 'from-red-50 to-pink-50 border-red-200',
    cyan: 'from-cyan-50 to-blue-50 border-cyan-200',
    amber: 'from-amber-50 to-orange-50 border-amber-200',
    purple: 'from-purple-50 to-indigo-50 border-purple-200',
    pink: 'from-pink-50 to-rose-50 border-pink-200',
    yellow: 'from-yellow-50 to-amber-50 border-yellow-200',
    teal: 'from-teal-50 to-green-50 border-teal-200',
    green: 'from-green-50 to-emerald-50 border-green-200'
  }
  return colors[color] || 'from-gray-50 to-gray-100 border-gray-200'
}

// Check if value is abnormal
const isAbnormal = (test) => {
  if (!test.reference_range) return false

  const value = parseFloat(test.test_value)
  const range = test.reference_range

  // Handle different range formats
  if (range.includes('<')) {
    const max = parseFloat(range.replace('<', ''))
    return value >= max
  } else if (range.includes('>')) {
    const min = parseFloat(range.replace('>', ''))
    return value <= min
  } else if (range.includes('-')) {
    const [min, max] = range.split('-').map(v => parseFloat(v.trim()))
    return value < min || value > max
  }

  return false
}

onMounted(async () => {
  loading.value = true
  try {
    exams.value = await getPatientExams(props.patientId)
  } catch (error) {
    console.error('Error loading exam data:', error)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="lab-panels-view">
    <!-- Loading State -->
    <div v-if="loading" class="text-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-500 mx-auto"></div>
      <p class="text-gray-600 mt-2">Caricamento pannelli laboratorio...</p>
    </div>

    <!-- Content -->
    <div v-else-if="organizedData.encounters.length > 0">
      <!-- Filters -->
      <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-amber-100 p-4 mb-6">
        <div class="flex flex-wrap items-center gap-4">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium text-gray-700">Periodo:</span>
            <select v-model="selectedEncounter" class="px-3 py-2 rounded-lg border border-amber-200 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500">
              <option value="latest">Ultimo controllo</option>
              <option value="recent">Ultimi 3 controlli</option>
              <option value="all">Tutti i controlli</option>
            </select>
          </div>

          <div class="flex items-center gap-2">
            <span class="text-sm font-medium text-gray-700">Pannelli:</span>
            <select v-model="selectedPanel" class="px-3 py-2 rounded-lg border border-amber-200 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500">
              <option value="all">Tutti i pannelli</option>
              <option v-for="(panel, key) in organizedData.panels" :key="key" :value="key">
                {{ panel.name }}
              </option>
            </select>
          </div>

          <div class="flex-1"></div>

          <div class="text-sm text-gray-500">
            {{ organizedData.encounters.length }} controlli disponibili
          </div>
        </div>
      </div>

      <!-- Encounters -->
      <div v-for="encounter in filteredEncounters" :key="encounter.date" class="mb-6">
        <!-- Encounter Header -->
        <div class="bg-gradient-to-r from-amber-50 to-orange-50 rounded-t-2xl border-b border-amber-100 px-6 py-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-gradient-to-br from-amber-100 to-orange-100 rounded-full flex items-center justify-center">
                <svg class="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                </svg>
              </div>
              <div>
                <h3 class="text-lg font-bold text-gray-800">
                  Controllo del {{ formatDateItalian(encounter.date) }}
                </h3>
                <p class="text-sm text-gray-600">{{ encounter.tests.length }} esami completi</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Panels Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4 bg-white/80 backdrop-blur-sm rounded-b-2xl border border-amber-100">
          <div
            v-for="(panel, panelKey) in organizedData.panelsByEncounter[encounter.date]"
            :key="panelKey"
            v-show="selectedPanel === 'all' || selectedPanel === panelKey"
            :class="['rounded-xl border p-4 transition-all hover:shadow-md', `bg-gradient-to-br ${getPanelColor(panel.color)}`]"
          >
            <!-- Panel Header -->
            <div class="flex items-center gap-2 mb-3">
              <div class="w-8 h-8 rounded-full bg-white/80 flex items-center justify-center">
                <svg class="w-4 h-4 text-current" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="panel.icon"></path>
                </svg>
              </div>
              <h4 class="font-bold text-gray-800 text-sm">{{ panel.name }}</h4>
            </div>

            <!-- Panel Tests -->
            <div class="space-y-2">
              <div
                v-for="test in panel.tests"
                :key="test.id"
                :class="[
                  'flex justify-between items-center text-sm rounded-lg px-2 py-1',
                  isAbnormal(test) ? 'bg-red-100/50' : 'bg-white/50'
                ]"
              >
                <div class="flex-1 min-w-0">
                  <div class="font-medium text-gray-700 truncate">{{ test.test_name }}</div>
                  <div class="text-xs text-gray-500">Range: {{ test.reference_range }}</div>
                </div>
                <div class="flex-shrink-0 ml-2">
                  <div :class="[
                    'font-bold text-right',
                    isAbnormal(test) ? 'text-red-600' : 'text-gray-800'
                  ]">
                    {{ test.test_value }} {{ test.unit }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Panel Footer -->
            <div class="mt-3 pt-2 border-t border-current opacity-20">
              <p class="text-xs text-gray-600">{{ panel.tests.length }} parametri</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- No Data State -->
    <div v-else class="text-center py-8">
      <div class="w-16 h-16 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
        </svg>
      </div>
      <p class="text-gray-600 font-medium">Nessun dato laboratorio disponibile</p>
      <p class="text-gray-500 text-sm">I pannelli appariranno qui quando avrai esami</p>
    </div>
  </div>
</template>

<style scoped>
.lab-panels-view {
  /* Add any specific styles if needed */
}
</style>