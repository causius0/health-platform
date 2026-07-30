<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import {
  getDoctorPatients, getPatientExams, getPatient, getPatientVisits,
  getDoctorActivity, getPatientGoals, createGoal,
  logout as apiLogout
} from '../utils/api'
import { formatDateItalian, translateCondition } from '../utils/formatters'
import TrendChart from './TrendChart.vue'
import ChatInterface from './ChatInterface.vue'

const authStore = useAuthStore()
const user = computed(() => authStore.user)

const patients = ref([])          // list from API
const examsByPatient = ref({})     // patientId -> exams[]
const selected = ref(null)         // selected patient (list obj)
const profile = ref(null)          // selected patient profile
const visits = ref([])
const loading = ref(true)
const activity = ref([])        // worker activity feed (interoperability)
const viewMode = ref('patients') // 'patients' | 'activity'
const selectedGoals = ref([])
const escalationStarted = ref({}) // patientId -> bool (≥4-factor monitoring path)

// ---- helpers --------------------------------------------------------------
function latestExam(exams, name) {
  const f = (exams || []).filter(e => e.test_name === name)
  if (!f.length) return null
  return f.sort((a, b) => (a.date || '').localeCompare(b.date || ''))[f.length - 1]
}
function valOf(exams, name) {
  const e = latestExam(exams, name)
  return e ? parseFloat(e.test_value) : null
}
function trendOf(exams, name) {
  const s = (exams || []).filter(e => e.test_name === name)
    .sort((a, b) => (a.date || '').localeCompare(b.date || ''))
  if (s.length < 2) return 0
  return parseFloat(s[s.length - 1].test_value) - parseFloat(s[0].test_value)
}

// clinical colours per metric
const MCOLOR = {
  'HbA1c': '#0d9488', 'Glicemia a digiuno': '#e11d48', 'Glicemia postprandiale': '#f97316',
  'Colesterolo LDL': '#7c3aed', 'Colesterolo HDL': '#059669', 'Colesterolo totale': '#2563eb',
  'Trigliceridi': '#db2777', 'Creatinina': '#0891b2', 'eGFR': '#65a30d',
  'Microalbuminuria': '#ca8a04', 'Pressione sistolica': '#dc2626', 'Pressione diastolica': '#9333ea',
  'Potassio': '#0284c7', 'Sodio': '#475569',
}

// status: normal / elevated / critical  (drives colour)
function metricStatus(name, v) {
  if (v == null) return 'normal'
  const r = {
    'HbA1c': [4, 7, 8], 'Glicemia a digiuno': [70, 100, 140], 'Glicemia postprandiale': [70, 140, 180],
    'Colesterolo LDL': [0, 100, 130], 'Colesterolo HDL': [40, 200, 200], 'Colesterolo totale': [0, 200, 240],
    'Trigliceridi': [0, 150, 200], 'Creatinina': [0.4, 1.3, 1.5], 'eGFR': [60, 200, 200],
    'Microalbuminuria': [0, 30, 300], 'Pressione sistolica': [90, 130, 140], 'Pressione diastolica': [60, 85, 90],
    'Potassio': [3.5, 5.1, 5.5], 'Sodio': [136, 145, 150],
  }[name]
  if (!r) return 'normal'
  // eGFR & HDL: low is bad -> invert the "high" logic
  if (name === 'eGFR') return v < r[0] ? 'critical' : v < 60 ? 'elevated' : 'normal'
  if (name === 'Colesterolo HDL') return v < 40 ? 'elevated' : 'normal'
  return v > r[2] ? 'critical' : v > r[1] ? 'elevated' : 'normal'
}
function statusDot(s) {
  return { normal: 'bg-emerald-500', elevated: 'bg-amber-500', critical: 'bg-rose-500' }[s] || 'bg-slate-300'
}

// ---- flags / alerts -------------------------------------------------------
function computeFlags(exams) {
  const f = []
  const v = name => valOf(exams, name)
  // helper: last date this metric was abnormal (for "since when")
  const sinceName = (name) => {
    const arr = (exams||[]).filter(e => e.test_name===name)
      .sort((a,b)=>(a.date||'').localeCompare(b.date||''))
    // find earliest consecutive abnormal reading from the end
    let lastNormal = null
    for (const e of arr) {
      if (metricStatus(name, parseFloat(e.test_value))==='normal') lastNormal = (e.date||'').split(' ')[0]
    }
    // since = first abnormal after last normal
    const after = arr.filter(e => lastNormal ? (e.date||'').split(' ')[0] > lastNormal : metricStatus(name, parseFloat(e.test_value))!=='normal')
    return after.length ? (after[0].date||'').split(' ')[0] : null
  }
  const push = (sev, text, advice, factor=true, metric=null) => f.push({ sev, text, advice, factor, since: metric ? sinceName(metric) : null })

  const hba1c = v('HbA1c')
  if (hba1c != null) {
    if (hba1c > 8) push('critical', `HbA1c ${hba1c}% · critico`, 'Ricontattare il paziente, rivalutare terapia', true, 'HbA1c')
    else if (hba1c > 7) push('warning', `HbA1c ${hba1c}% · sopra target`, 'Rinforzare dieta e attività, stretto monitoraggio', true, 'HbA1c')
  }
  const sys = v('Pressione sistolica'), dia = v('Pressione diastolica')
  if (sys != null) {
    const both = `${sys}/${dia || '—'}`
    if (sys > 140) push('warning', `Pressione ${both} mmHg · stadio 2`, 'Rivedere terapia antiipertensiva', true, 'Pressione sistolica')
    else if (sys > 130) push('warning', `Pressione ${both} mmHg · elevata`, 'Monitoraggio domiciliare, ridurre sodio', true, 'Pressione sistolica')
  }
  const ldl = v('Colesterolo LDL')
  if (ldl != null && ldl > 130) push('warning', `LDL ${ldl} mg/dL`, 'Ottimizzare statina, dieta', true, 'Colesterolo LDL')
  const micro = v('Microalbuminuria')
  if (micro != null && micro > 30) push('warning', `Microalbuminuria ${micro} mg/g · nefropatia`, 'Protezione renale (ACE-inibitore)', true, 'Microalbuminuria')
  const crea = v('Creatinina')
  if (crea != null && crea > 1.3) push('warning', `Creatinina ${crea} mg/dL`, 'Valutazione nefrologica', true, 'Creatinina')
  const egfr = v('eGFR')
  if (egfr != null && egfr < 60) push('critical', `eGFR ${egfr} mL/min · ridotta`, 'Valutazione nefrologica urgente', true, 'eGFR')
  const fast = v('Glicemia a digiuno')
  if (fast != null && fast > 140) push('warning', `Glicemia a digiuno ${fast} mg/dL`, 'Verificare aderenza terapia', true, 'Glicemia a digiuno')
  const tg = v('Trigliceridi')
  if (tg != null && tg > 200) push('warning', `Trigliceridi ${tg} mg/dL`, 'Dieta, controllo glicemico', true, 'Trigliceridi')
  // trend flags (info, not counted as risk factors)
  if (hba1c != null && trendOf(exams, 'HbA1c') > 0.4) push('warning', 'HbA1c in peggioramento', 'Intensificare controllo glicemico', false)
  else if (hba1c != null && trendOf(exams, 'HbA1c') < -0.3) push('info', 'HbA1c in miglioramento', 'Continuare lo schema attuale', false)
  if (sys != null && trendOf(exams, 'Pressione sistolica') > 6) push('warning', 'Pressione in peggioramento', 'Rivedere terapia', false)
  else if (sys != null && trendOf(exams, 'Pressione sistolica') < -8) push('info', 'Pressione in miglioramento', 'Mantenere terapia', false)
  return f
}

// Risk level by the agreed rule: count distinct risk-factor metrics.
//   >=4 risk factors -> Alto ("piu' di 3") -> specific monitoring + occupational physician
//   2-3              -> Medio
//   0-1              -> Basso
function riskOf(exams) {
  const factorCount = computeFlags(exams).filter(x => x.factor).length
  if (factorCount >= 4) return 'Alto'
  if (factorCount >= 2) return 'Medio'
  return 'Basso'
}
function riskFactorCount(exams) {
  return computeFlags(exams).filter(x => x.factor).length
}
const RISK_STYLE = {
  Alto: 'bg-rose-50 text-rose-700 ring-rose-200',
  Medio: 'bg-amber-50 text-amber-700 ring-amber-200',
  Basso: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
}

// flat alert feed across patients (sorted by severity)
const alertFeed = computed(() => {
  const order = { critical: 0, warning: 1, info: 2 }
  const feed = []
  for (const p of patients.value) {
    const ex = examsByPatient.value[p.id] || []
    const flags = computeFlags(ex)
    for (const fl of flags) feed.push({ ...fl, patient: p, sevOrder: order[fl.sev] ?? 9 })
  }
  return feed.sort((a, b) => a.sevOrder - b.sevOrder)
})
const alertCounts = computed(() => {
  const c = { critical: 0, warning: 0, info: 0 }
  for (const a of alertFeed.value) c[a.sev] = (c[a.sev] || 0) + 1
  return c
})

// ---- patient detail summary tiles ----------------------------------------
function keyTiles(exams, condition) {
  const isD = (condition || '').toLowerCase().includes('diabete')
  const names = isD
    ? ['HbA1c', 'Glicemia a digiuno', 'Colesterolo LDL', 'eGFR']
    : ['Pressione sistolica', 'Pressione diastolica', 'Colesterolo LDL', 'Creatinina']
  return names.map(n => {
    const e = latestExam(exams, n)
    return {
      name: n,
      label: n.replace('Pressione ', 'P. ').replace('Colesterolo ', 'Colest. ').replace('Glicemia a digiuno', 'Glicemia'),
      value: e ? e.test_value : '—',
      unit: e ? e.unit : '',
      status: e ? metricStatus(n, parseFloat(e.test_value)) : 'normal',
      color: MCOLOR[n] || '#475569',
    }
  })
}

const age = (birth) => {
  if (!birth) return null
  const y = parseInt(birth.split('-')[0]); const now = new Date().getFullYear()
  return isNaN(y) ? null : now - y
}

// ---- actions --------------------------------------------------------------
async function selectPatient(p) {
  selected.value = p
  try {
    const [pr, vs, gls] = await Promise.all([
      getPatient(p.id), getPatientVisits(p.id), getPatientGoals(p.id).catch(()=>[]),
    ])
    profile.value = pr; visits.value = vs; selectedGoals.value = gls
  } catch (e) { console.error(e) }
}
function backToList() {
  selected.value = null; profile.value = null; visits.value = []; selectedGoals.value = []
  refreshActivity()
}
async function handleLogout() {
  try { await apiLogout() } catch (e) {}
  authStore.logout(); window.location.href = '/'
}

const chatKey = computed(() => selected.value ? `p${selected.value.id}` : 'general')
const selectedExams = computed(() => (selected.value && examsByPatient.value[selected.value.id]) || [])

onMounted(async () => {
  try {
    const list = await getDoctorPatients()
    patients.value = list
    const results = await Promise.all(list.map(p => getPatientExams(p.id).catch(() => [])))
    const map = {}
    list.forEach((p, i) => { map[p.id] = results[i] })
    examsByPatient.value = map
    activity.value = await getDoctorActivity().catch(() => [])
  } catch (e) { console.error('Error loading doctor data:', e) }
  finally { loading.value = false }
})
async function refreshActivity() {
  activity.value = await getDoctorActivity().catch(() => [])
}
// Activate the >3-risk-factor monitoring path: flags the worker and records a
// structured note in the activity feed so the handoff is visible/traceable.
async function startMonitoringPath() {
  if (!selected.value || escalationStarted.value[selected.value.id]) return
  escalationStarted.value[selected.value.id] = true
  try {
    await createGoal({
      patient_id: selected.value.id, area: 'stress',
      title: 'Percorso monitoraggio specifico — visita medico del lavoro',
      frequency_per_week: 1,
    })
    await refreshActivity()
  } catch (e) { console.error(e) }
}
const AREA_LABELS = {
  physical_activity: 'Attività fisica', nutrition: 'Alimentazione', smoking: 'Fumo',
  alcohol: 'Alcol', sleep: 'Sonno', stress: 'Stress',
}
</script>

<template>
  <div class="flex h-screen flex-col bg-slate-100">
    <!-- Header -->
    <header class="flex shrink-0 items-center justify-between border-b border-slate-200 bg-white px-5 py-3">
      <div class="flex items-center gap-3">
        <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-600">
          <svg class="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
        </div>
        <div>
          <h1 class="text-[15px] font-semibold text-slate-800">Cruscotto Clinico</h1>
          <p class="text-xs text-slate-500">Dott. {{ user?.first_name }} {{ user?.last_name }} · {{ user?.specialization }}</p>
        </div>
      </div>
      <button @click="handleLogout" class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100">
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
        </svg>
        Esci
      </button>
    </header>

    <main class="flex min-h-0 flex-1">
      <!-- ============ LEFT: ALERTS ============ -->
      <aside class="flex w-72 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div class="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 class="text-sm font-semibold text-slate-800">Avvisi clinici</h2>
          <span v-if="alertCounts.critical" class="rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-semibold text-rose-700">{{ alertCounts.critical }} critici</span>
        </div>
        <div class="min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
          <div v-if="loading" class="py-8 text-center text-sm text-slate-400">Caricamento…</div>
          <div v-else-if="!alertFeed.length" class="py-8 text-center text-sm text-slate-400">
            <svg class="mx-auto mb-2 h-8 w-8 text-emerald-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            Nessun avviso. Tutti i pazienti nei limiti.
          </div>
          <button
            v-for="(a, i) in alertFeed" :key="i"
            @click="selectPatient(a.patient)"
            class="block w-full rounded-lg border border-slate-200 bg-white p-3 text-left transition hover:border-slate-300 hover:shadow-sm"
          >
            <div class="mb-1 flex items-center gap-2">
              <span class="h-2 w-2 shrink-0 rounded-full" :class="{ 'bg-rose-500': a.sev==='critical', 'bg-amber-500': a.sev==='warning', 'bg-sky-500': a.sev==='info' }"></span>
              <span class="truncate text-sm font-medium text-slate-800">{{ a.patient.first_name }} {{ a.patient.last_name }}</span>
              <span class="ml-auto shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
                :class="{ 'bg-rose-50 text-rose-600': a.sev==='critical', 'bg-amber-50 text-amber-600': a.sev==='warning', 'bg-sky-50 text-sky-600': a.sev==='info' }">
                {{ a.sev==='critical'?'critico':a.sev==='warning'?'attenzione':'info' }}
              </span>
            </div>
            <p class="text-sm text-slate-700">{{ a.text }}</p>
            <p class="mt-0.5 text-xs text-slate-400">{{ a.advice }}</p>
            <p v-if="a.since" class="mt-1 text-[11px] text-slate-400">Da {{ formatDateItalian(a.since) }}</p>
          </button>
        </div>
      </aside>

      <!-- ============ CENTER: PATIENTS / DETAIL ============ -->
      <section class="flex min-w-0 flex-1 flex-col bg-slate-50">
        <div v-if="loading" class="flex h-full items-center justify-center text-slate-400">Caricamento pazienti…</div>

        <!-- Patient list -->
        <div v-else-if="!selected" class="min-h-0 flex-1 overflow-y-auto p-6">
          <div class="mb-4 flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 class="text-lg font-semibold text-slate-800">I miei pazienti</h2>
              <p class="text-sm text-slate-500">{{ patients.length }} lavoratori in carico · clicca per aprire la cartella</p>
            </div>
            <div class="flex rounded-lg border border-slate-200 bg-white p-0.5 text-xs">
              <button @click="viewMode='patients'" :class="viewMode==='patients' ? 'bg-teal-600 text-white' : 'text-slate-600'" class="rounded-md px-3 py-1.5 font-medium transition">Pazienti</button>
              <button @click="viewMode='activity'" :class="viewMode==='activity' ? 'bg-teal-600 text-white' : 'text-slate-600'" class="rounded-md px-3 py-1.5 font-medium transition">Attività lavoratori</button>
            </div>
          </div>

          <!-- WORKER ACTIVITY FEED (interoperability) -->
          <div v-if="viewMode==='activity'" class="rounded-xl border border-slate-200 bg-white">
            <div class="flex items-center justify-between border-b border-slate-200 px-4 py-3">
              <div>
                <h3 class="text-sm font-semibold text-slate-800">Attività di prevenzione dei lavoratori</h3>
                <p class="text-xs text-slate-500">Obiettivi e check-in registrati tra le visite (aggiorati in tempo reale)</p>
              </div>
              <button @click="refreshActivity" class="flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50">
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                Aggiorna
              </button>
            </div>
            <div class="divide-y divide-slate-100">
              <button v-for="(it, i) in activity" :key="i" @click="selectPatient(patients.find(p=>p.id===it.patient_id))"
                class="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-slate-50">
                <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white"
                  :class="it.type==='goal' ? 'bg-teal-500' : (it.pct>=80 ? 'bg-emerald-500' : 'bg-amber-500')">
                  <svg v-if="it.type==='goal'" class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                  <span v-else class="text-[10px] font-bold">{{ it.pct }}%</span>
                </span>
                <div class="min-w-0 flex-1">
                  <p class="truncate text-sm text-slate-800"><span class="font-medium">{{ it.patient_name }}</span> · {{ it.detail }}</p>
                  <p class="text-[11px] text-slate-400">{{ AREA_LABELS[it.area] || it.area }} · {{ it.type==='goal' ? 'nuovo obiettivo' : 'check-in settimanale' }}</p>
                </div>
                <span v-if="it.ts" class="shrink-0 text-[11px] text-slate-400">{{ formatDateItalian((it.ts||'').slice(0,10)) }}</span>
              </button>
              <div v-if="!activity.length" class="px-4 py-10 text-center text-sm text-slate-400">Nessuna attività registrata dai lavoratori.</div>
            </div>
          </div>

          <!-- PATIENT GRID -->
          <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <button
              v-for="p in patients" :key="p.id"
              @click="selectPatient(p)"
              class="group rounded-xl border border-slate-200 bg-white p-4 text-left transition hover:-translate-y-0.5 hover:border-teal-300 hover:shadow-md"
            >
              <div class="flex items-center gap-3">
                <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-sm font-semibold text-white"
                  :style="{ background: (MCOLOR['HbA1c']) }"
                  v-if="p.condition.toLowerCase().includes('diabete')">
                  {{ p.first_name[0] }}{{ p.last_name[0] }}
                </div>
                <div v-else class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-sm font-semibold text-white"
                  :style="{ background: MCOLOR['Pressione sistolica'] }">
                  {{ p.first_name[0] }}{{ p.last_name[0] }}
                </div>
                <div class="min-w-0 flex-1">
                  <p class="truncate text-sm font-semibold text-slate-800">{{ p.first_name }} {{ p.last_name }}</p>
                  <p class="truncate text-xs capitalize text-slate-500">{{ translateCondition(p.condition) }}</p>
                </div>
                <span class="rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1"
                  :class="RISK_STYLE[riskOf(examsByPatient[p.id]||[])]">
                  {{ riskOf(examsByPatient[p.id]||[]) }}
                </span>
              </div>
              <!-- key metric line -->
              <div class="mt-3 flex items-center gap-4 border-t border-slate-100 pt-3 text-xs">
                <template v-if="p.condition.toLowerCase().includes('diabete')">
                  <div>
                    <span class="text-slate-400">HbA1c </span>
                    <span class="font-semibold tabular-nums" :style="{ color: metricStatus('HbA1c', valOf(examsByPatient[p.id],'HbA1c'))!=='normal' ? '#dc2626' : '#0f172a' }">{{ valOf(examsByPatient[p.id],'HbA1c') ?? '—' }}%</span>
                  </div>
                  <div>
                    <span class="text-slate-400">LDL </span>
                    <span class="font-semibold tabular-nums">{{ valOf(examsByPatient[p.id],'Colesterolo LDL') ?? '—' }}</span>
                  </div>
                </template>
                <template v-else>
                  <div>
                    <span class="text-slate-400">PA </span>
                    <span class="font-semibold tabular-nums">{{ valOf(examsByPatient[p.id],'Pressione sistolica') ?? '—' }}/{{ valOf(examsByPatient[p.id],'Pressione diastolica') ?? '—' }}</span>
                  </div>
                  <div>
                    <span class="text-slate-400">LDL </span>
                    <span class="font-semibold tabular-nums">{{ valOf(examsByPatient[p.id],'Colesterolo LDL') ?? '—' }}</span>
                  </div>
                </template>
              </div>
            </button>
          </div>
        </div>

        <!-- Patient detail -->
        <div v-else class="min-h-0 flex-1 overflow-y-auto">
          <!-- detail header -->
          <div class="sticky top-0 z-10 border-b border-slate-200 bg-white px-6 py-4">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <button @click="backToList" class="flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100">
                  <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
                </button>
                <div>
                  <h2 class="text-lg font-semibold text-slate-800">{{ selected.first_name }} {{ selected.last_name }}</h2>
                  <p class="text-xs capitalize text-slate-500">
                    {{ translateCondition(selected.condition) }}<template v-if="profile&&age(profile.birth_date)"> · {{ age(profile.birth_date) }} anni</template>
                  </p>
                </div>
              </div>
              <span class="rounded-full px-2.5 py-1 text-xs font-semibold ring-1"
                :class="RISK_STYLE[riskOf(selectedExams)]">{{ riskOf(selectedExams) }} rischio</span>
            </div>
          </div>

          <div class="space-y-5 p-6">
            <!-- key metric tiles -->
            <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <div v-for="t in keyTiles(selectedExams, selected.condition)" :key="t.name"
                class="rounded-xl border border-slate-200 bg-white p-3.5">
                <div class="flex items-center gap-1.5">
                  <span class="h-2 w-2 rounded-full" :class="statusDot(t.status)"></span>
                  <span class="text-xs text-slate-500">{{ t.label }}</span>
                </div>
                <div class="mt-1.5 flex items-baseline gap-1">
                  <span class="text-xl font-semibold tabular-nums text-slate-800">{{ t.value }}</span>
                  <span class="text-xs text-slate-400">{{ t.unit }}</span>
                </div>
              </div>
            </div>

            <!-- Risk-factor count + escalation (≥4 = Alto) -->
            <div class="flex items-center gap-3 rounded-xl px-4 py-3"
              :class="riskFactorCount(selectedExams) >= 4 ? 'bg-rose-50 ring-1 ring-rose-200' : 'bg-slate-50 ring-1 ring-slate-200'">
              <span class="text-2xl font-bold tabular-nums" :class="riskFactorCount(selectedExams) >= 4 ? 'text-rose-600' : 'text-slate-700'">{{ riskFactorCount(selectedExams) }}</span>
              <div class="flex-1">
                <p class="text-sm font-medium" :class="riskFactorCount(selectedExams) >= 4 ? 'text-rose-700' : 'text-slate-700'">
                  fattori di rischio
                </p>
                <p class="text-xs text-slate-500">
                  <template v-if="riskFactorCount(selectedExams) >= 4">Più di 3 → percorso di monitoraggio specifico · consigliata visita medico del lavoro</template>
                  <template v-else>Soglia &gt;3 fattori attiva percorso dedicato (medico del lavoro)</template>
                </p>
              </div>
              <button v-if="riskFactorCount(selectedExams) >= 4" @click="startMonitoringPath"
                class="rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-rose-700 disabled:opacity-60"
                :disabled="escalationStarted[selected.id]">
                {{ escalationStarted[selected.id] ? 'Percorso attivato' : 'Avvia percorso' }}
              </button>
            </div>

            <!-- Worker's prevention goals (what they're actually doing) -->
            <div class="rounded-xl border border-slate-200 bg-white p-5">
              <div class="mb-2 flex items-center justify-between">
                <div>
                  <h3 class="text-sm font-semibold text-slate-800">Obiettivi di prevenzione del lavoratore</h3>
                  <p class="text-xs text-slate-500">Attività registrata autonomamente tra le visite</p>
                </div>
              </div>
              <div v-if="selectedGoals.length" class="space-y-2">
                <div v-for="g in selectedGoals.filter(x=>x.status==='active')" :key="g.id" class="flex items-center gap-3 rounded-lg bg-slate-50 px-3 py-2">
                  <span class="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase text-teal-700 bg-teal-100">{{ AREA_LABELS[g.area] || g.area }}</span>
                  <span class="flex-1 text-sm text-slate-800">{{ g.title }}</span>
                  <span class="text-xs text-slate-500">{{ (g.checkins&&g.checkins.length?(g.checkins[0].completed_days):0) }}/{{ g.frequency_per_week }} sett.</span>
                </div>
                <p v-if="!selectedGoals.filter(x=>x.status==='active').length" class="text-xs text-slate-400">Nessun obiettivo attivo.</p>
              </div>
              <p v-else class="text-sm text-slate-400">Il lavoratore non ha ancora impostato obiettivi.</p>
            </div>

            <!-- trend chart -->
            <div class="rounded-xl border border-slate-200 bg-white p-5">
              <div class="mb-1 flex items-center justify-between">
                <div>
                  <h3 class="text-sm font-semibold text-slate-800">Andamento valori</h3>
                  <p class="text-xs text-slate-500">10 controlli · clicca un parametro per aggiungerlo al grafico</p>
                </div>
              </div>
              <TrendChart :exams="selectedExams" :condition="selected.condition" :height="300" />
            </div>

            <!-- two columns: labs table + visits -->
            <div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
              <!-- labs table -->
              <div class="overflow-hidden rounded-xl border border-slate-200 bg-white">
                <div class="border-b border-slate-200 px-4 py-3"><h3 class="text-sm font-semibold text-slate-800">Ultimi esami</h3></div>
                <div class="max-h-[420px] overflow-y-auto">
                  <table class="w-full text-sm">
                    <thead class="sticky top-0 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
                      <tr>
                        <th class="px-4 py-2 font-medium">Esame</th>
                        <th class="px-4 py-2 font-medium">Valore</th>
                        <th class="px-4 py-2 font-medium">Data</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                      <tr v-for="e in [...selectedExams].sort((a,b)=>(b.date||'').localeCompare(a.date||'')).slice(0,40)" :key="e.id" class="hover:bg-slate-50">
                        <td class="px-4 py-2">
                          <div class="flex items-center gap-2">
                            <span class="h-1.5 w-1.5 rounded-full" :style="{ background: MCOLOR[e.test_name]||'#cbd5e1' }"></span>
                            <span class="text-slate-700">{{ e.test_name }}</span>
                          </div>
                        </td>
                        <td class="px-4 py-2 tabular-nums">
                          <span class="font-medium text-slate-800">{{ e.test_value }}</span>
                          <span class="text-xs text-slate-400"> {{ e.unit }}</span>
                        </td>
                        <td class="px-4 py-2 text-slate-500">{{ formatDateItalian(e.date) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- visits -->
              <div class="overflow-hidden rounded-xl border border-slate-200 bg-white">
                <div class="border-b border-slate-200 px-4 py-3"><h3 class="text-sm font-semibold text-slate-800">Visite</h3></div>
                <div class="max-h-[420px] space-y-3 overflow-y-auto p-4">
                  <div v-for="vs in visits" :key="vs.id" class="rounded-lg border border-slate-100 p-3">
                    <div class="mb-1 flex items-center gap-2">
                      <span class="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase"
                        :class="{ 'bg-rose-50 text-rose-600': vs.visit_type==='urgenza', 'bg-sky-50 text-sky-600': vs.visit_type==='followup', 'bg-slate-100 text-slate-600': vs.visit_type==='controllo' }">
                        {{ vs.visit_type }}
                      </span>
                      <span class="text-xs text-slate-400">{{ formatDateItalian(vs.visit_date) }}</span>
                    </div>
                    <p class="text-sm text-slate-700">{{ vs.doctor_notes }}</p>
                    <p v-if="vs.diagnosis" class="mt-1 text-xs italic text-slate-400">{{ vs.diagnosis }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ============ RIGHT: CHAT (always on) ============ -->
      <aside class="flex w-[380px] shrink-0 flex-col border-l border-slate-200 bg-white">
        <div class="border-b border-slate-200 px-4 py-3">
          <div class="flex items-center gap-2">
            <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-teal-600">
              <svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <div>
              <h2 class="text-sm font-semibold text-slate-800">Assistente clinico</h2>
              <p class="text-[11px] text-slate-500">{{ selected ? `Contesto: ${selected.first_name} ${selected.last_name}` : 'Panoramica tutti i pazienti' }}</p>
            </div>
          </div>
        </div>
        <div class="min-h-0 flex-1">
          <ChatInterface :key="chatKey" :patient-id="selected ? selected.id : null" role="doctor" />
        </div>
      </aside>
    </main>
  </div>
</template>
