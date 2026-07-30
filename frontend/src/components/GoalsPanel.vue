<script setup>
/**
 * Prevention goals + weekly adherence tracker. Persisted to the backend so
 * the operator sees worker activity (the §C.2 interoperability hook).
 */
import { ref, computed, onMounted } from 'vue'
import { getPatientGoals, createGoal, goalCheckin, updateGoal } from '../utils/api'
import { formatDateItalian } from '../utils/formatters'

const props = defineProps({
  patientId: { type: Number, required: true },
  editable: { type: Boolean, default: false }, // true for worker, false for doctor
})

const goals = ref([])
const loading = ref(true)
const showNewGoal = ref(false)
const newGoal = ref({ area: 'physical_activity', title: '', frequency_per_week: 5 })

const AREA_LABELS = {
  physical_activity: 'Attività fisica', nutrition: 'Alimentazione', smoking: 'Fumo',
  alcohol: 'Alcol', sleep: 'Sonno', stress: 'Stress',
}
const AREA_COLOR = {
  physical_activity: 'bg-teal-100 text-teal-700',
  nutrition: 'bg-emerald-100 text-emerald-700',
  smoking: 'bg-rose-100 text-rose-700',
  alcohol: 'bg-amber-100 text-amber-700',
  sleep: 'bg-indigo-100 text-indigo-700',
  stress: 'bg-fuchsia-100 text-fuchsia-700',
}

const thisWeekStr = (() => {
  const t = new Date(); const mon = new Date(t)
  mon.setDate(t.getDate() - ((t.getDay() + 6) % 7))
  return mon.toISOString().slice(0, 10)
})()

async function load() {
  loading.value = true
  try { goals.value = await getPatientGoals(props.patientId) } catch (e) { console.error(e) }
  finally { loading.value = false }
}
onMounted(load)

// Current-week check-in days for each goal
function weekDays(g) {
  const c = (g.checkins || []).find(x => x.week_of === thisWeekStr)
  return c ? c.completed_days : 0
}
function weekPct(g) {
  return Math.min(100, Math.round((weekDays(g) / (g.frequency_per_week || 1)) * 100))
}
function weekCheckinId(g) {
  const c = (g.checkins || []).find(x => x.week_of === thisWeekStr)
  return c ? c.id : null
}

async function setDays(g, delta) {
  if (!props.editable) return
  const next = Math.max(0, Math.min(g.frequency_per_week, weekDays(g) + delta))
  try {
    await goalCheckin(g.id, { completed_days: next, week_of: thisWeekStr })
    await load()
  } catch (e) { console.error(e) }
}

async function addGoal() {
  if (!newGoal.value.title.trim()) return
  try {
    await createGoal({ patient_id: props.patientId, ...newGoal.value })
    newGoal.value = { area: 'physical_activity', title: '', frequency_per_week: 5 }
    showNewGoal.value = false
    await load()
  } catch (e) { console.error(e) }
}

async function markComplete(g) {
  try { await updateGoal(g.id, { status: 'completed' }); await load() } catch (e) { console.error(e) }
}

// Adherence history: aggregate across goals, last 6 weeks
const history = computed(() => {
  const weeks = new Map()
  for (const g of goals.value) {
    for (const c of (g.checkins || [])) {
      const e = weeks.get(c.week_of) || { week: c.week_of, done: 0, target: 0 }
      e.done += c.completed_days; e.target += g.frequency_per_week
      weeks.set(c.week_of, e)
    }
  }
  return [...weeks.values()]
    .sort((a, b) => a.week.localeCompare(b.week))
    .slice(-6)
    .map(e => ({ ...e, pct: Math.round((e.done / (e.target || 1)) * 100) }))
})

const overallAdherence = computed(() => {
  if (!history.value.length) return null
  return Math.round(history.value.reduce((s, e) => s + e.pct, 0) / history.value.length)
})

const activeGoals = computed(() => goals.value.filter(g => g.status === 'active'))
const completedGoals = computed(() => goals.value.filter(g => g.status === 'completed'))
</script>

<template>
  <div>
    <div class="mb-4 flex items-center justify-between">
      <div>
        <h3 class="text-sm font-semibold text-slate-800">I tuoi obiettivi &amp; aderenza</h3>
        <p class="text-xs text-slate-500">Una azione concreta a settimana — traccia i progressi</p>
      </div>
      <div v-if="overallAdherence != null" class="text-right">
        <p class="text-2xl font-bold tabular-nums text-teal-600">{{ overallAdherence }}%</p>
        <p class="text-[11px] text-slate-400">aderenza media</p>
      </div>
    </div>

    <div v-if="loading" class="py-6 text-center text-sm text-slate-400">Caricamento…</div>

    <template v-else>
      <!-- Active goals -->
      <div class="space-y-3">
        <div v-for="g in activeGoals" :key="g.id" class="rounded-xl border border-slate-200 bg-white p-4">
          <div class="mb-3 flex items-start gap-3">
            <div class="min-w-0 flex-1">
              <div class="mb-1 flex flex-wrap items-center gap-2">
                <span class="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase" :class="AREA_COLOR[g.area]">{{ AREA_LABELS[g.area] }}</span>
                <span class="text-sm font-semibold text-slate-800">{{ g.title }}</span>
              </div>
              <p class="text-xs text-slate-500">Obiettivo: {{ g.frequency_per_week }} volte a settimana</p>
            </div>
          </div>
          <!-- current week progress -->
          <div class="rounded-lg bg-slate-50 p-3">
            <div class="mb-2 flex items-center justify-between">
              <span class="text-xs font-medium text-slate-600">Questa settimana</span>
              <div v-if="editable" class="flex items-center gap-1.5">
                <button @click="setDays(g, -1)" class="flex h-6 w-6 items-center justify-center rounded-md border border-slate-200 text-slate-500 hover:bg-white">−</button>
                <span class="w-12 text-center text-sm font-semibold tabular-nums text-slate-800">{{ weekDays(g) }}/{{ g.frequency_per_week }}</span>
                <button @click="setDays(g, 1)" class="flex h-6 w-6 items-center justify-center rounded-md border border-slate-200 text-slate-500 hover:bg-white">+</button>
              </div>
              <span v-else class="text-sm font-semibold tabular-nums text-slate-700">{{ weekDays(g) }}/{{ g.frequency_per_week }} giorni</span>
            </div>
            <div class="h-2 w-full overflow-hidden rounded-full bg-slate-200">
              <div class="h-full rounded-full transition-all"
                :class="weekPct(g) >= 80 ? 'bg-emerald-500' : weekPct(g) >= 50 ? 'bg-amber-500' : 'bg-rose-400'"
                :style="{ width: weekPct(g) + '%' }"></div>
            </div>
          </div>
          <div class="mt-2 flex justify-end">
            <button v-if="editable" @click="markComplete(g)" class="text-xs text-teal-600 hover:underline">Segna obiettivo completato →</button>
          </div>
        </div>
      </div>

      <!-- New goal form (worker only) -->
      <div v-if="editable && !showNewGoal" class="mt-3">
        <button @click="showNewGoal = true" class="w-full rounded-xl border border-dashed border-slate-300 py-2.5 text-sm text-slate-500 hover:border-teal-300 hover:text-teal-600">
          + Imposta un nuovo obiettivo
        </button>
      </div>
      <div v-if="editable && showNewGoal" class="mt-3 rounded-xl border border-slate-200 bg-white p-4">
        <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <select v-model="newGoal.area" class="rounded-lg border border-slate-200 px-2 py-1.5 text-sm">
            <option v-for="(lbl, k) in AREA_LABELS" :key="k" :value="k">{{ lbl }}</option>
          </select>
          <input v-model.number="newGoal.frequency_per_week" type="number" min="1" max="7"
            class="rounded-lg border border-slate-200 px-2 py-1.5 text-sm" placeholder="Volte/settimana" />
        </div>
        <input v-model="newGoal.title" type="text" placeholder="es. Camminata 30 minuti"
          class="mt-2 w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm" @keyup.enter="addGoal" />
        <div class="mt-2 flex justify-end gap-2">
          <button @click="showNewGoal = false" class="rounded-lg px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100">Annulla</button>
          <button @click="addGoal" class="rounded-lg bg-teal-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-teal-700">Aggiungi</button>
        </div>
      </div>

      <!-- Adherence history -->
      <div v-if="history.length" class="mt-5">
        <h4 class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Storico aderenza (settimane)</h4>
        <div class="space-y-1.5">
          <div v-for="h in [...history].reverse()" :key="h.week" class="flex items-center gap-3">
            <span class="w-20 shrink-0 text-xs text-slate-500">{{ formatDateItalian(h.week) }}</span>
            <div class="h-4 flex-1 overflow-hidden rounded bg-slate-100">
              <div class="h-full rounded transition-all"
                :class="h.pct >= 80 ? 'bg-emerald-500' : h.pct >= 50 ? 'bg-amber-500' : 'bg-rose-400'"
                :style="{ width: h.pct + '%' }"></div>
            </div>
            <span class="w-10 shrink-0 text-right text-xs font-semibold tabular-nums text-slate-700">{{ h.pct }}%</span>
          </div>
        </div>
      </div>

      <!-- Completed -->
      <div v-if="completedGoals.length" class="mt-5 rounded-lg bg-emerald-50/60 p-3 ring-1 ring-emerald-200">
        <p class="text-xs font-medium text-emerald-700">{{ completedGoals.length }} obiettivo/i completato/i</p>
        <ul class="mt-1 space-y-0.5">
          <li v-for="g in completedGoals" :key="g.id" class="text-xs text-emerald-700">✓ {{ g.title }}</li>
        </ul>
      </div>
    </template>
  </div>
</template>
