<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { getPatient, getPatientExams, getAnamnesis, logout as apiLogout } from '../utils/api'
import { translateCondition } from '../utils/formatters'
import ChatInterface from './ChatInterface.vue'
import HealthOverview from './HealthOverview.vue'
import GoalsPanel from './GoalsPanel.vue'
import TrendChart from './TrendChart.vue'

const authStore = useAuthStore()
const user = computed(() => authStore.user)

const patient = ref(null)
const exams = ref([])
const anamnesis = ref({})
const loading = ref(true)
const showDetail = ref(false) // charts/exams pushed down as optional deep-dive

async function reloadAnamnesis() {
  try {
    const r = await getAnamnesis(authStore.user?.patient_id)
    anamnesis.value = r.anamnesis || {}
  } catch (e) {}
}
onMounted(async () => {
  try {
    const patientId = authStore.user?.patient_id
    if (patientId) {
      const [p, ex, an] = await Promise.all([
        getPatient(patientId),
        getPatientExams(patientId),
        getAnamnesis(patientId).catch(() => ({ anamnesis: {} })),
      ])
      patient.value = p
      exams.value = ex
      anamnesis.value = an.anamnesis || {}
    }
  } catch (e) { console.error(e) }
  finally { loading.value = false }
  window.addEventListener('anamnesis-updated', reloadAnamnesis)
})
onUnmounted(() => window.removeEventListener('anamnesis-updated', reloadAnamnesis))

async function handleLogout() {
  try { await apiLogout() } catch (e) {}
  authStore.logout(); window.location.href = '/'
}
</script>

<template>
  <div class="flex h-screen flex-col bg-slate-100">
    <!-- Header -->
    <header class="flex shrink-0 items-center justify-between border-b border-slate-200 bg-white px-5 py-3">
      <div class="flex items-center gap-3">
        <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-500">
          <svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
        </div>
        <div>
          <h1 class="text-[15px] font-semibold text-slate-800">Prevenzione &amp; Salute</h1>
          <p class="text-xs text-slate-500">{{ user?.first_name }} {{ user?.last_name }} · il tuo compagno di salute</p>
        </div>
      </div>
      <button @click="handleLogout" class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100">
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
        Esci
      </button>
    </header>

    <!-- Privacy strip -->
    <div class="flex shrink-0 items-center justify-center gap-1.5 border-b border-amber-100 bg-amber-50 py-1.5 text-[11px] text-amber-700">
      <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
      I tuoi dati sono sicuri e protetti
    </div>

    <main class="flex min-h-0 flex-1">
      <!-- LEFT: summary + goals + deep-dive -->
      <section class="min-w-0 flex-1 overflow-y-auto bg-slate-50">
        <div v-if="loading" class="flex h-full items-center justify-center text-slate-400">Caricamento…</div>
        <div v-else-if="!patient" class="flex h-full items-center justify-center text-slate-400">Profilo non disponibile</div>
        <div v-else class="space-y-4 p-6">
          <!-- Condition pill -->
          <div class="flex items-center gap-2">
            <span class="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600 ring-1 ring-slate-200">
              Patologia: <span class="capitalize">{{ translateCondition(patient.condition) }}</span>
            </span>
          </div>

          <!-- 1. Plain-language summary (LEADS) -->
          <div class="rounded-xl border border-slate-200 bg-white p-5">
            <HealthOverview :exams="exams" :anamnesis="anamnesis" :condition="patient.condition" />
          </div>

          <!-- 2. Goals + adherence -->
          <div class="rounded-xl border border-slate-200 bg-white p-5">
            <GoalsPanel :patient-id="patient.id" :editable="true" />
          </div>

          <!-- 3. Optional deep-dive: charts + exams -->
          <div class="rounded-xl border border-slate-200 bg-white">
            <button @click="showDetail = !showDetail"
              class="flex w-full items-center justify-between px-5 py-4 text-left">
              <div>
                <h3 class="text-sm font-semibold text-slate-800">Esami e andamento nel tempo</h3>
                <p class="text-xs text-slate-500">Approfondimento — valori di laboratorio e grafici</p>
              </div>
              <svg class="h-5 w-5 text-slate-400 transition-transform" :class="{ 'rotate-180': showDetail }" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
            </button>
            <div v-if="showDetail" class="border-t border-slate-100 p-5">
              <TrendChart :exams="exams" :condition="patient.condition" :height="280" />
            </div>
          </div>
        </div>
      </section>

      <!-- RIGHT: prevention chat (always on) -->
      <aside class="flex w-[380px] shrink-0 flex-col border-l border-slate-200 bg-white">
        <div class="border-b border-slate-200 px-4 py-3">
          <div class="flex items-center gap-2">
            <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500">
              <svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg>
            </div>
            <div>
              <h2 class="text-sm font-semibold text-slate-800">Coach di prevenzione</h2>
              <p class="text-[11px] text-slate-500">Consigli personalizzati evidence-based</p>
            </div>
          </div>
        </div>
        <div class="min-h-0 flex-1">
          <ChatInterface v-if="patient" :patient-id="patient.id" role="patient" />
        </div>
      </aside>
    </main>
  </div>
</template>
