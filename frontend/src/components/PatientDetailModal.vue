<script setup>
import { ref, watch } from 'vue'
import { getPatientHistory } from '../utils/api'
import { formatDateItalian } from '../utils/formatters'
import ChatInterface from './ChatInterface.vue'
import HealthChart from './HealthChart.vue'
import LabPanelsView from './LabPanelsView.vue'

const props = defineProps({
  patient: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close'])

const exams = ref([])
const visits = ref([])
const loading = ref(false)
const showChat = ref(false)

watch(() => props.patient, (newPatient) => {
  if (newPatient) {
    loadPatientHistory(newPatient.id)
  }
}, { immediate: true })

async function loadPatientHistory(patientId) {
  loading.value = true
  try {
    const history = await getPatientHistory(patientId)
    exams.value = history.exams || []
    visits.value = history.visits || []
  } catch (error) {
    console.error('Error loading patient history:', error)
  } finally {
    loading.value = false
  }
}

function closeChat() {
  showChat.value = false
}

function handleClose() {
  emit('close')
}
</script>

<template>
  <div class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
    <div class="bg-white/95 backdrop-blur-sm rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col border border-amber-100">
      <!-- Warm Header -->
      <div class="px-6 py-4 border-b border-amber-100 bg-gradient-to-r from-amber-50 to-orange-50 flex justify-between items-center">
        <div class="flex items-center gap-3">
          <div class="w-12 h-12 bg-gradient-to-br from-teal-100 to-green-100 rounded-full flex items-center justify-center">
            <span class="text-teal-600 font-bold text-lg">
              {{ patient.first_name[0] }}{{ patient.last_name[0] }}
            </span>
          </div>
          <div>
            <h2 class="text-2xl font-bold text-gray-800">
              {{ patient.first_name }} {{ patient.last_name }}
            </h2>
            <p class="text-amber-600 font-medium">{{ patient.condition }}</p>
          </div>
        </div>
        <button
          @click="handleClose"
          class="text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full w-8 h-8 flex items-center justify-center transition-all"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <div v-if="!loading">
          <!-- Medications Card -->
          <div class="bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl p-4 mb-6 border border-amber-100">
            <div class="flex items-center gap-2 mb-2">
              <svg class="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"></path>
              </svg>
              <h3 class="text-lg font-bold text-gray-800">Farmaci</h3>
            </div>
            <p class="text-gray-700">{{ patient.medications }}</p>
          </div>

          <!-- Health Chart -->
          <div class="mb-6">
            <HealthChart
              :patient-id="patient.id"
              role="doctor"
            />
          </div>

          <!-- Complete Lab Panels -->
          <div class="mb-6">
            <LabPanelsView
              :patient-id="patient.id"
            />
          </div>

          <!-- Exams -->
          <div class="bg-white rounded-xl border border-amber-100 overflow-hidden mb-6">
            <div class="bg-gradient-to-r from-amber-50 to-orange-50 px-4 py-3 border-b border-amber-100">
              <h3 class="text-lg font-bold text-gray-800">Esami recenti (ultimi 6 mesi)</h3>
            </div>
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-amber-50">
                <thead class="bg-amber-50">
                  <tr>
                    <th class="px-4 py-2 text-left text-xs font-medium text-amber-700 uppercase">Data</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-amber-700 uppercase">Esame</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-amber-700 uppercase">Risultato</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-amber-700 uppercase">Range</th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-amber-50">
                  <tr v-for="exam in exams.slice(0, 10)" :key="exam.id" class="hover:bg-amber-50/50 transition-colors">
                    <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                      {{ formatDateItalian(exam.date) }}
                    </td>
                    <td class="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
                      {{ exam.test_name }}
                    </td>
                    <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                      {{ exam.test_value }} {{ exam.unit }}
                    </td>
                    <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                      {{ exam.reference_range }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Visits -->
          <div class="bg-white rounded-xl border border-amber-100 overflow-hidden mb-6">
            <div class="bg-gradient-to-r from-teal-50 to-green-50 px-4 py-3 border-b border-teal-100">
              <h3 class="text-lg font-bold text-gray-800">Visite recenti</h3>
            </div>
            <div class="p-4 space-y-3">
              <div
                v-for="visit in visits.slice(0, 6)"
                :key="visit.id"
                class="border border-amber-100 rounded-xl p-3 hover:border-amber-200 hover:shadow-md transition-all bg-gradient-to-r from-amber-50/30 to-transparent"
              >
                <div class="flex justify-between items-start mb-2">
                  <div>
                    <p class="text-sm text-gray-500">{{ formatDateItalian(visit.visit_date) }}</p>
                    <p class="text-xs font-bold text-amber-600 uppercase mt-1">{{ visit.visit_type }}</p>
                  </div>
                </div>
                <div v-if="visit.doctor_notes" class="text-sm text-gray-700 bg-white/60 rounded-lg p-2">
                  <strong>Note:</strong> {{ visit.doctor_notes }}
                </div>
              </div>
            </div>
          </div>

          <!-- Chat Section -->
          <div class="mt-6">
            <button
              @click="showChat = !showChat"
              class="w-full bg-gradient-to-r from-teal-500 to-green-500 text-white px-4 py-3 rounded-xl hover:from-teal-600 hover:to-green-600 transition-all shadow-md hover:shadow-lg font-medium"
            >
              {{ showChat ? 'Nascondi Chat AI' : 'Chat con AI per analizzare i dati' }}
            </button>

            <div v-if="showChat" class="mt-4">
              <ChatInterface
                :patient-id="patient.id"
                role="doctor"
                @close="closeChat"
              />
            </div>
          </div>
        </div>

        <!-- Loading State with warm design -->
        <div v-else class="flex items-center justify-center py-12">
          <div class="text-center">
            <div class="animate-spin rounded-full h-12 w-12 border-b-4 border-amber-500 mx-auto mb-4"></div>
            <p class="text-gray-600 font-medium">Caricamento storia clinica...</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
