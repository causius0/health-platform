<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  patientId: {
    type: Number,
    required: true
  }
})

// Define guided health paths
const guidedPaths = ref([
  {
    id: 'nutrition_improvement',
    name: 'Miglioramento Nutrizione',
    description: 'Percorso guidato per migliorare l alimentazione',
    icon: '🥗',
    status: 'not_started', // not_started, in_progress, completed
    progress: 0,
    steps: [
      'Analizza abitudini alimentari attuali',
      'Identifica aree di miglioramento',
      'Scegli un obiettivo settimanale realistico',
      'Traccia i progressi giornalieri'
    ],
    measurableOutput: 'Riduzione zuccheri semplici del 50% in 4 settimane',
    completedAt: null
  },
  {
    id: 'physical_activity',
    name: 'Aumento Attività Fisica',
    description: 'Percorso per aumentare movimento quotidiano',
    icon: '🚶',
    status: 'not_started',
    progress: 0,
    steps: [
      'Valuta livello attività attuale',
      'Definisci obiettivo realistico',
      'Pianifica esercizi settimanali',
      'Monitora aderenza e progressi'
    ],
    measurableOutput: '30 minuti camminata 5 giorni/settimana per 4 settimane',
    completedAt: null
  },
  {
    id: 'stress_management',
    name: 'Gestione Stress',
    description: 'Tecniche per ridurre stress lavorativo',
    icon: '🧘',
    status: 'not_started',
    progress: 0,
    steps: [
      'Identifica fonti di stress',
      'Impara tecniche di rilassamento',
      'Implementa pause strategiche',
      'Valuta miglioramento benessere'
    ],
    measurableOutput: 'Riduzione punteggio stress del 30% in 3 settimane',
    completedAt: null
  },
  {
    id: 'sleep_quality',
    name: 'Miglioramento Sonno',
    description: 'Percorso per migliorare qualità del sonno',
    icon: '😴',
    status: 'not_started',
    progress: 0,
    steps: [
      'Analizza routine pre-sonno',
      'Identifica fattori disturbanti',
      'Implementa igiene del sonno',
      'Traccia qualità riposo'
    ],
    measurableOutput: 'Aumento ore sonno da 6 a 7.5 per notte in 3 settimane',
    completedAt: null
  }
])

const activePath = computed(() => {
  return guidedPaths.value.find(p => p.status === 'in_progress') || null
})

const completedPaths = computed(() => {
  return guidedPaths.value.filter(p => p.status === 'completed')
})

function startPath(pathId) {
  const path = guidedPaths.value.find(p => p.id === pathId)
  if (path) {
    path.status = 'in_progress'
    path.progress = 10
  }
}

function completePath(pathId) {
  const path = guidedPaths.value.find(p => p.id === pathId)
  if (path) {
    path.status = 'completed'
    path.progress = 100
    path.completedAt = new Date().toISOString()
  }
}

function resetPath(pathId) {
  const path = guidedPaths.value.find(p => p.id === pathId)
  if (path) {
    path.status = 'not_started'
    path.progress = 0
    path.completedAt = null
  }
}

function getStatusColor(status) {
  switch (status) {
    case 'completed': return 'teal'
    case 'in_progress': return 'amber'
    default: return 'gray'
  }
}

function getStatusText(status) {
  switch (status) {
    case 'completed': return 'Completato'
    case 'in_progress': return 'In corso'
    default: return 'Non iniziato'
  }
}
</script>

<template>
  <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border border-amber-100 p-6 mb-6">
    <h3 class="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
      <svg class="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
      </svg>
      Percorsi Guidati di Prevenzione
    </h3>

    <!-- Active Path -->
    <div v-if="activePath" class="mb-6 p-4 bg-amber-50 rounded-xl border border-amber-200">
      <div class="flex items-start gap-3 mb-3">
        <span class="text-2xl">{{ activePath.icon }}</span>
        <div class="flex-1">
          <h4 class="font-bold text-gray-800">{{ activePath.name }}</h4>
          <p class="text-sm text-gray-600">{{ activePath.description }}</p>
        </div>
        <span class="px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-700">
          In corso
        </span>
      </div>

      <!-- Progress bar -->
      <div class="mb-4">
        <div class="flex justify-between text-sm mb-1">
          <span class="text-gray-600">Progresso</span>
          <span class="font-bold text-amber-700">{{ activePath.progress }}%</span>
        </div>
        <div class="w-full bg-amber-200 rounded-full h-2">
          <div class="bg-amber-500 h-2 rounded-full transition-all" :style="{ width: activePath.progress + '%' }"></div>
        </div>
      </div>

      <!-- Steps -->
      <div class="space-y-2 mb-4">
        <div v-for="(step, index) in activePath.steps" :key="index" class="flex items-center gap-2 text-sm">
          <div class="w-4 h-4 rounded-full" :class="index < activePath.progress / 25 ? 'bg-teal-500' : 'bg-gray-300'"></div>
          <span :class="index < activePath.progress / 25 ? 'text-gray-800' : 'text-gray-500'">{{ step }}</span>
        </div>
      </div>

      <!-- Action buttons -->
      <div class="flex gap-2">
        <button
          @click="completePath(activePath.id)"
          class="flex-1 bg-teal-500 text-white px-4 py-2 rounded-lg hover:bg-teal-600 transition-colors text-sm font-medium"
        >
          Completa Percorso
        </button>
        <button
          @click="resetPath(activePath.id)"
          class="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors text-sm"
        >
          Reset
        </button>
      </div>
    </div>

    <!-- Available Paths -->
    <div class="space-y-3">
      <h4 class="text-sm font-semibold text-gray-700">Percorsi Disponibili</h4>
      <div
        v-for="path in guidedPaths.filter(p => p.status !== 'in_progress')"
        :key="path.id"
        class="border rounded-xl p-4 transition-all hover:shadow-md"
        :class="`border-${getStatusColor(path.status)}-200 bg-${getStatusColor(path.status)}-50`"
      >
        <div class="flex items-start gap-3">
          <span class="text-2xl">{{ path.icon }}</span>
          <div class="flex-1">
            <div class="flex items-center justify-between mb-1">
              <h5 class="font-bold text-gray-800">{{ path.name }}</h5>
              <span class="px-2 py-0.5 rounded-full text-xs font-bold" :class="`bg-${getStatusColor(path.status)}-100 text-${getStatusColor(path.status)}-700`">
                {{ getStatusText(path.status) }}
              </span>
            </div>
            <p class="text-sm text-gray-600 mb-2">{{ path.description }}</p>

            <!-- Measurable output for completed paths -->
            <div v-if="path.status === 'completed'" class="p-2 bg-teal-100 rounded-lg mb-2">
              <p class="text-xs font-bold text-teal-800">RISULTATO MISURABILE:</p>
              <p class="text-xs text-teal-700">{{ path.measurableOutput }}</p>
              <p class="text-xs text-teal-600 mt-1">Completato il: {{ new Date(path.completedAt).toLocaleDateString('it-IT') }}</p>
            </div>

            <!-- Measurable output preview for not started paths -->
            <div v-else class="p-2 bg-gray-100 rounded-lg mb-2">
              <p class="text-xs text-gray-600"><strong>Obiettivo:</strong> {{ path.measurableOutput }}</p>
            </div>

            <button
              v-if="path.status === 'not_started'"
              @click="startPath(path.id)"
              class="w-full bg-amber-500 text-white px-4 py-2 rounded-lg hover:bg-amber-600 transition-colors text-sm font-medium"
            >
              Inizia Percorso
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Summary -->
    <div v-if="completedPaths.length > 0" class="mt-6 p-4 bg-gradient-to-r from-teal-50 to-green-50 rounded-xl border border-teal-200">
      <p class="text-sm text-teal-800 font-medium flex items-center gap-2">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
        Hai completato {{ completedPaths.length }} {{ completedPaths.length === 1 ? 'percorso' : 'percorsi' }}!
        Continua così per migliorare la tua salute.
      </p>
    </div>
  </div>
</template>
