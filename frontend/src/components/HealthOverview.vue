<script setup>
/**
 * Plain-language health overview — leads the worker dashboard.
 * Derives the 6 lifestyle areas from lab values + self-reported anamnesis,
 * always surfacing BOTH risk factors and protective factors.
 */
import { computed } from 'vue'
import { formatDateItalian } from '../utils/formatters'

const props = defineProps({
  exams: { type: Array, default: () => [] },
  anamnesis: { type: Object, default: () => ({}) },
  condition: { type: String, default: '' },
})

function latest(name) {
  const f = (props.exams || []).filter(e => e.test_name === name)
  if (!f.length) return null
  return f.sort((a, b) => (a.date || '').localeCompare(b.date || ''))[f.length - 1]
}
function num(name) {
  const e = latest(name); return e ? parseFloat(e.test_value) : null
}

const an = computed(() => props.anamnesis || {})

// ---- Derive each lifestyle area: { status, headline, detail } ----
// status: good | attention | concerning
const areas = computed(() => {
  const out = {}
  const isD = (props.condition || '').toLowerCase().includes('diabete')

  // Activity: metabolic profile (triglycerides, HDL, glucose) + self-report
  const tg = num('Trigliceridi'), hdl = num('Colesterolo HDL'), glu = num('Glicemia a digiuno')
  let actScore = 0
  if (tg != null && tg > 150) actScore++
  if (hdl != null && hdl < 40) actScore++
  if (glu != null && glu > 110) actScore++
  const selfAct = (an.value.physical_activity || '').toLowerCase()
  const sedentary = selfAct.includes('sedentar') || selfAct.includes('0') || selfAct.includes('mai')
  out.physical_activity = {
    self: an.value.physical_activity,
    status: actScore >= 2 || sedentary ? 'concerning' : actScore === 1 ? 'attention' : 'good',
    headline: actScore >= 2 || sedentary ? 'Profilo metabolico da risollevare' : actScore === 1 ? 'Movimento da consolidare' : 'Buon profilo metabolico',
    detail: sedentary ? 'Hai indicato uno stile di vita sedentario.' : (an.value.physical_activity || 'Attività regolare'),
  }

  // Nutrition: self-report leads, labs as supporting evidence
  const hba1c = num('HbA1c'), ldl = num('Colesterolo LDL'), tg2 = num('Trigliceridi')
  const selfNut = (an.value.nutrition || '').toLowerCase()
  const poorDiet = selfNut.includes('veloci') || selfNut.includes('zuccher') || selfNut.includes('merendine') || selfNut.includes('preconfezionat')
  const goodDiet = selfNut.includes('equilibrat') || selfNut.includes('attenta') || selfNut.includes('conta carb')
  let nutScore = 0
  if (poorDiet) nutScore += 2
  if (goodDiet) nutScore = 0
  if (tg2 != null && tg2 > 175) nutScore++
  if (ldl != null && ldl > 150) nutScore++
  out.nutrition = {
    self: an.value.nutrition,
    status: nutScore >= 2 ? 'concerning' : nutScore === 1 ? 'attention' : 'good',
    headline: nutScore >= 2 ? 'Alimentazione da riequilibrare' : nutScore === 1 ? 'Qualche attenzione alla dieta' : 'Alimentazione equilibrata',
    detail: an.value.nutrition || 'Dieta bilanciata',
  }

  // Smoking: from anamnesis
  const smoke = (an.value.smoking || '').toLowerCase()
  out.smoking = {
    self: an.value.smoking,
    status: smoke.includes('sigaret') || smoke.startsWith('fumatore ') ? 'concerning'
      : smoke.includes('ex') ? 'attention' : 'good',
    headline: smoke.includes('sigaret') || smoke.startsWith('fumatore') ? 'Fumo attivo — il primo obiettivo'
      : smoke.includes('ex') ? 'Ottimo aver smesso' : 'Non fumi — un grande vantaggio',
    detail: an.value.smoking || 'Non fumatore',
  }

  // Alcohol: from anamnesis
  const alc = (an.value.alcohol || '').toLowerCase()
  out.alcohol = {
    self: an.value.alcohol,
    status: alc.includes('quotidiana') || alc.includes('feriali') || alc.includes('birre') ? 'attention' : 'good',
    headline: alc.includes('quotidiana') ? 'Consumo frequente — riducilo' : 'Consumo moderato o assente',
    detail: an.value.alcohol || 'Consumo occasionale',
  }

  // Sleep: from anamnesis
  const sleep = (an.value.sleep || '').toLowerCase()
  const lowSleep = sleep.includes('5') || sleep.includes('6 ore') && sleep.includes('interrot')
  out.sleep = {
    self: an.value.sleep,
    status: sleep.includes('5') ? 'attention' : 'good',
    headline: sleep.includes('5') ? 'Poco sonno — mira a 7 ore' : lowSleep ? 'Qualità del sonno da migliorare' : 'Riposo adeguato',
    detail: an.value.sleep || '7+ ore',
  }

  // Stress / wellbeing: BP proxy + self-report
  const sys = num('Pressione sistolica')
  let stressScore = 0
  if (sys != null && sys > 140) stressScore += 2
  else if (sys != null && sys > 130) stressScore++
  const selfStress = (an.value.stress || '').toLowerCase()
  if (selfStress.includes('alto')) stressScore += 2
  else if (selfStress.includes('medio')) stressScore++
  out.stress = {
    self: an.value.stress,
    status: stressScore >= 2 ? 'concerning' : stressScore === 1 ? 'attention' : 'good',
    headline: stressScore >= 2 ? 'Pressione/stress da gestire' : stressScore === 1 ? 'Monitora lo stress' : 'Benessere stabile',
    detail: an.value.stress || 'Basso',
  }
  return out
})

const orderedKeys = ['physical_activity', 'nutrition', 'smoking', 'alcohol', 'sleep', 'stress']
const LABELS = {
  physical_activity: 'Attività fisica',
  nutrition: 'Alimentazione',
  smoking: 'Fumo',
  alcohol: 'Alcol',
  sleep: 'Sonno',
  stress: 'Stress & benessere lavorativo',
}
const ICON_PATHS = {
  physical_activity: 'M13 10V3L4 14h7v7l9-11h-7z',
  nutrition: 'M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z',
  smoking: 'M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636',
  alcohol: 'M20 7l-8 4-8-4m16 0v10a2 2 0 01-2 2H6a2 2 0 01-2-2V7m16 0L12 3 4 7',
  sleep: 'M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z',
  stress: 'M9.663 17h4.673M12 3v1m6.364-.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
}

const STYLE = {
  good: { ring: 'ring-emerald-200', bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500', icon: 'M5 13l4 4L19 7' },
  attention: { ring: 'ring-amber-200', bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500', icon: 'M12 9v2m0 4h.01M5 19h14a2 2 0 001.84-2.75L13.74 4a2 2 0 00-3.48 0L3.16 16.25A2 2 0 005 19z' },
  concerning: { ring: 'ring-rose-200', bg: 'bg-rose-50', text: 'text-rose-700', dot: 'bg-rose-500', icon: 'M12 9v2m0 4h.01M5 19h14a2 2 0 001.84-2.75L13.74 4a2 2 0 00-3.48 0L3.16 16.25A2 2 0 005 19z' },
}

const protective = computed(() => (an.value.protective || []))

const overall = computed(() => {
  const arr = orderedKeys.map(k => areas.value[k].status)
  const concerning = arr.filter(s => s === 'concerning').length
  const attention = arr.filter(s => s === 'attention').length
  if (concerning >= 2) return { text: 'Diverse aree meritano attenzione', tone: 'concerning' }
  if (concerning >= 1 || attention >= 3) return { text: 'Qualche ambito da migliorare', tone: 'attention' }
  return { text: 'Stato generale positivo', tone: 'good' }
})

const lastExamDate = computed(() => {
  const arr = (props.exams || []).map(e => (e.date || '').split(' ')[0]).filter(Boolean).sort()
  return arr.length ? formatDateItalian(arr[arr.length - 1]) : null
})
</script>

<template>
  <div>
    <!-- Overall banner -->
    <div class="mb-5 flex items-center justify-between rounded-xl border px-5 py-4"
      :class="[STYLE[overall.tone].ring, STYLE[overall.tone].bg]">
      <div class="flex items-center gap-3">
        <span class="h-2.5 w-2.5 rounded-full" :class="STYLE[overall.tone].dot"></span>
        <div>
          <p class="text-sm font-semibold" :class="STYLE[overall.tone].text">Il tuo stato di salute</p>
          <p class="text-sm text-slate-600">{{ overall.text }}</p>
        </div>
      </div>
      <span v-if="lastExamDate" class="text-xs text-slate-400">Ultimo esame: {{ lastExamDate }}</span>
    </div>

    <!-- 6 area cards -->
    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <div v-for="key in orderedKeys" :key="key"
        class="rounded-xl border bg-white p-4 ring-1 transition hover:shadow-sm"
        :class="STYLE[areas[key].status].ring">
        <div class="mb-2 flex items-center gap-2.5">
          <span class="flex h-8 w-8 items-center justify-center rounded-lg" :class="STYLE[areas[key].status].bg">
            <svg class="h-4 w-4" :class="STYLE[areas[key].status].text" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="ICON_PATHS[key]" />
            </svg>
          </span>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-semibold text-slate-800">{{ LABELS[key] }}</p>
            <p class="truncate text-xs text-slate-500">{{ areas[key].headline }}</p>
          </div>
          <span class="h-2 w-2 shrink-0 rounded-full" :class="STYLE[areas[key].status].dot"></span>
        </div>
        <p class="text-xs leading-relaxed text-slate-600">{{ areas[key].detail }}</p>
      </div>
    </div>

    <!-- Protective factors -->
    <div v-if="protective.length" class="mt-4 rounded-xl border border-emerald-200 bg-emerald-50/60 p-4">
      <p class="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-emerald-700">
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        I tuoi fattori di protezione
      </p>
      <div class="flex flex-wrap gap-2">
        <span v-for="p in protective" :key="p"
          class="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200">{{ p }}</span>
      </div>
    </div>
  </div>
</template>
