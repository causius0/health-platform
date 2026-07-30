<script setup>
import { ref, onMounted, computed, nextTick, watch } from 'vue'
import {
  sendChatMessage, startChatSession, getAnamnesis, updateAnamnesis, createGoal,
} from '../utils/api'

const props = defineProps({
  patientId: { type: Number, default: null },
  role: { type: String, default: 'patient' },
})

const messages = ref([])
const newMessage = ref('')
const loading = ref(false)
const sessionId = ref(null)
const scrollRef = ref(null)
const showSuggestions = ref(false) // drawer collapsed by default so chat isn't crushed

// ---- anamnesis onboarding (worker) ----
const anamnesis = ref(null)        // null = unknown / loading; {} = empty -> start flow; object = done
const anaStep = ref(0)
const anaAnswers = ref({})
const ANA_QUESTIONS = [
  { key: 'physical_activity', q: 'Quanto ti muovi in una settimana?', opts: [
    { v: 'Sedentario (quasi mai)', protect: false },
    { v: '1-2 volte a settimana', protect: false },
    { v: '3-4 volte a settimana', protect: true, label: 'attività fisica regolare' },
    { v: '5 o più volte a settimana', protect: true, label: 'attività fisica regolare' },
  ]},
  { key: 'nutrition', q: 'Come descrivi la tua alimentazione?', opts: [
    { v: 'Equilibrata, varia', protect: true, label: 'alimentazione attenta' },
    { v: 'Troppi carboidrati e zuccheri', protect: false },
    { v: 'Troppi cibi preconfezionati / sale', protect: false },
    { v: 'Spesso pasti veloci fuori casa', protect: false },
  ]},
  { key: 'smoking', q: 'Il fumo?', opts: [
    { v: 'Mai fumato', protect: true, label: 'non fumi' },
    { v: 'Ex fumatore', protect: true, label: 'ex fumatore' },
    { v: 'Pochissime sigarette', protect: false },
    { v: 'Fumo abituale', protect: false },
  ]},
  { key: 'alcohol', q: 'Il consumo di alcol?', opts: [
    { v: 'Mai o raro', protect: true, label: 'consumo di alcol moderato' },
    { v: 'Occasionale (weekend)', protect: true, label: 'consumo di alcol moderato' },
    { v: 'Quotidiano moderato', protect: false },
    { v: 'Frequente', protect: false },
  ]},
  { key: 'sleep', q: 'Quanto dormi di solito?', opts: [
    { v: '5 ore o meno', protect: false },
    { v: 'Circa 6 ore', protect: false },
    { v: '7 ore o più', protect: true, label: 'buon riposo' },
  ]},
  { key: 'stress', q: 'Come percepisci lo stress / carico lavorativo?', opts: [
    { v: 'Basso', protect: true, label: 'buon benessere lavorativo' },
    { v: 'Medio', protect: false },
    { v: 'Alto', protect: false },
  ]},
]

const startAnamnesis = computed(() => props.role === 'patient' && anamnesis.value && Object.keys(anamnesis.value).length === 0)

function pickAna(opt, qkey) {
  anaAnswers.value[qkey] = opt.v
  if (opt.protect && opt.label) {
    const arr = anaAnswers.value._protective || (anaAnswers.value._protective = [])
    if (!arr.includes(opt.label)) arr.push(opt.label)
  }
  if (anaStep.value < ANA_QUESTIONS.length - 1) {
    anaStep.value++
  } else {
    finishAnamnesis()
  }
}
function anaProgress() {
  return Math.round((anaStep.value / ANA_QUESTIONS.length) * 100)
}
async function finishAnamnesis() {
  const data = {
    physical_activity: anaAnswers.value.physical_activity,
    nutrition: anaAnswers.value.nutrition,
    smoking: anaAnswers.value.smoking,
    alcohol: anaAnswers.value.alcohol,
    sleep: anaAnswers.value.sleep,
    stress: anaAnswers.value.stress,
    protective: anaAnswers.value._protective || [],
  }
  try {
    await updateAnamnesis(props.patientId, data)
    anamnesis.value = data
    anaStep.value = -1
    window.dispatchEvent(new CustomEvent('anamnesis-updated'))
    await bootSession()
  } catch (e) { console.error(e) }
}

// ---- tier parsing ----
function parseTiered(content) {
  const t = { general: '', preventive: '', clinical: '' }
  const g = content.match(/INFORMAZIONE GENERALE:\s*(.*?)(?=CONSIGLIO|INDICAZIONE|$)/s)
  const p = content.match(/CONSIGLIO PREVENTIVO PERSONALIZZATO:\s*(.*?)(?=INDICAZIONE|$)/s)
  const c = content.match(/INDICAZIONE CLINICA:\s*(.*?)$/s)
  if (g) t.general = g[1].trim()
  if (p) t.preventive = p[1].trim()
  if (c) t.clinical = c[1].trim()
  if (!t.general && !t.preventive && !t.clinical) t.general = content
  return t
}
function showClinical(content) {
  const c = parseTiered(content).clinical
  if (!c) return false
  return !/non necessaria/i.test(c)
}

// ---- boot ----
async function bootSession() {
  try {
    const r = await startChatSession(props.patientId ? { patient_id: props.patientId } : {})
    sessionId.value = r.session_id
    if (props.role === 'patient') {
      const greet = anamnesis.value && (anamnesis.value.protective || []).length
        ? `Grazie! Ho memorizzato il tuo profilo.\n\nINFORMAZIONE GENERALE: Ho notato i tuoi punti di forza — ${ (anamnesis.value.protective||[]).join(', ') }.\nCONSIGLIO PREVENTIVO PERSONALIZZATO: Dimmi su quale area vuoi lavorare questa settimana.\nINDICAZIONE CLINICA: Non necessaria in questo caso.`
        : 'Ciao! Sono il tuo coach di prevenzione. Come posso aiutarti oggi?'
      messages.value.push({ role: 'assistant', content: greet })
    } else {
      messages.value.push({ role: 'assistant', content: 'Buongiorno dottore. Sono qui per aiutarla ad analizzare i dati dei pazienti.' })
    }
  } catch (e) { console.error(e) }
}

const selectedContext = computed(() => props.patientId != null)
const quickPrompts = computed(() =>
  selectedContext.value
    ? ['Quali valori sono fuori target?', 'Confronta l\'andamento di HbA1c', 'Cosa suggerisci per la terapia?']
    : ['Quali pazienti hanno valori critici?', 'Chi ha HbA1c più alto?', 'Riepilogo generale']
)

function scrollToBottom() {
  nextTick(() => { const el = scrollRef.value; if (el) el.scrollTop = el.scrollHeight })
}
watch(messages, scrollToBottom, { deep: true })

function ask(q) { newMessage.value = q; sendMessage() }

async function sendMessage() {
  if (!newMessage.value.trim() || loading.value || !sessionId.value) return
  const userMsg = newMessage.value
  messages.value.push({ role: 'user', content: userMsg })
  newMessage.value = ''
  loading.value = true
  try {
    const r = await sendChatMessage({ message: userMsg, session_id: sessionId.value })
    messages.value.push({ role: 'assistant', content: r.response })
  } catch (e) {
    messages.value.push({ role: 'assistant', content: 'Scusa, si è verificato un errore. Riprova.' })
  } finally { loading.value = false }
}

// ---- Suggerimenti: programs + EBM (worker) ----
const programs = ref([
  { id: 1, name: 'Sfida 10.000 passi', desc: 'Programma di mobilità aziendale', icon: 'walk', joined: false },
  { id: 2, name: 'Corso di mindfulness', desc: 'Gestione dello stress sul lavoro', icon: 'mind', joined: false },
  { id: 3, name: 'Cucina consapevole', desc: 'Workshop di alimentazione equilibrata', icon: 'food', joined: false },
])
const ebmSources = [
  { title: 'Linee guida per una sana alimentazione', src: 'CREA / INRAN', year: '2023' },
  { title: 'Indicazioni su attività fisica', src: 'OMS / WHO', year: '2020' },
  { title: 'Prevenzione del diabete tipo 2', src: 'AMD / SID', year: '2022' },
]
function toggleProgram(p) { p.joined = !p.joined }

// ---- AZIONI (worker) ----
async function joinProgramFromAction() {
  // concrete measurable output: join the step challenge as a goal
  try {
    await createGoal({ patient_id: props.patientId, area: 'physical_activity', title: 'Sfida 10.000 passi', frequency_per_week: 5 })
    messages.value.push({ role: 'user', content: 'Voglio iscrivermi a un programma aziendale' })
    messages.value.push({ role: 'assistant', content: 'INFORMAZIONE GENERALE: Iscrizione registrata.\nCONSIGLIO PREVENTIVO PERSONALIZZATO: Obiettivo "Sfida 10.000 passi" aggiunto al tuo cruscotto (5 giorni/sett). Lo trovi nel pannello obiettivi.\nINDICAZIONE CLINICA: Non necessaria in questo caso.' })
    scrollToBottom()
  } catch (e) { console.error(e) }
}

onMounted(async () => {
  if (props.role === 'patient') {
    try {
      const r = await getAnamnesis(props.patientId)
      anamnesis.value = r.anamnesis || {}
      // existing seed anamnesis -> go straight to chat
      if (anamnesis.value && Object.keys(anamnesis.value).length) { await bootSession() }
    } catch (e) { anamnesis.value = {}; }
  } else {
    await bootSession()
  }
})
</script>

<template>
  <!-- ===================== WORKER (patient) ===================== -->
  <div v-if="role === 'patient'" class="flex h-full flex-col bg-slate-50">
    <!-- Anamnesis onboarding flow -->
    <div v-if="startAnamnesis && anaStep >= 0" class="flex h-full flex-col p-4">
      <div class="mb-3 flex items-center gap-2">
        <span class="text-sm font-semibold text-slate-800">Conosciamoci</span>
        <span class="text-xs text-slate-400">{{ anaStep + 1 }}/{{ ANA_QUESTIONS.length }}</span>
      </div>
      <div class="mb-4 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
        <div class="h-full rounded-full bg-amber-500 transition-all" :style="{ width: anaProgress() + '%' }"></div>
      </div>
      <div class="flex flex-1 flex-col justify-center">
        <p class="mb-4 text-base font-medium text-slate-800">{{ ANA_QUESTIONS[anaStep].q }}</p>
        <div class="space-y-2">
          <button v-for="opt in ANA_QUESTIONS[anaStep].opts" :key="opt.v"
            @click="pickAna(opt, ANA_QUESTIONS[anaStep].key)"
            class="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-sm text-slate-700 transition hover:border-amber-300 hover:bg-amber-50">
            {{ opt.v }}
          </button>
        </div>
      </div>
      <p class="mt-3 flex items-center justify-center gap-1 text-[10px] text-slate-400">
        <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
        Dati trattati con riservatezza
      </p>
    </div>

    <!-- Chat + suggestions -->
    <template v-else>
      <!-- chat thread (guaranteed readable min height) -->
      <div ref="scrollRef" class="min-h-[240px] flex-1 space-y-3 overflow-y-auto p-4">
        <div v-for="(msg, i) in messages" :key="i" :class="['flex', msg.role==='user'?'justify-end':'justify-start']">
          <!-- user bubble -->
          <div v-if="msg.role==='user'" class="max-w-[80%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-amber-500 px-3 py-2 text-sm text-white">{{ msg.content }}</div>
          <!-- assistant: 3-tier -->
          <div v-else class="w-full max-w-[92%] overflow-hidden rounded-2xl rounded-bl-sm border border-slate-200 bg-white">
            <div v-if="parseTiered(msg.content).general" class="border-b border-slate-100 px-3 py-2">
              <p class="mb-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-600">Informazione generale</p>
              <p class="whitespace-pre-wrap text-sm text-slate-700">{{ parseTiered(msg.content).general }}</p>
            </div>
            <div v-if="parseTiered(msg.content).preventive" class="border-b border-slate-100 px-3 py-2">
              <p class="mb-0.5 text-[10px] font-semibold uppercase tracking-wide text-teal-600">Consiglio preventivo personalizzato</p>
              <p class="whitespace-pre-wrap text-sm text-slate-700">{{ parseTiered(msg.content).preventive }}</p>
            </div>
            <div v-if="showClinical(msg.content)" class="bg-rose-50 px-3 py-2">
              <p class="mb-0.5 text-[10px] font-semibold uppercase tracking-wide text-rose-600">Indicazione clinica</p>
              <p class="whitespace-pre-wrap text-sm text-slate-700">{{ parseTiered(msg.content).clinical }}</p>
            </div>
            <div v-if="!parseTiered(msg.content).general && !parseTiered(msg.content).preventive" class="px-3 py-2 text-sm text-slate-700">{{ msg.content }}</div>
          </div>
        </div>
        <div v-if="loading" class="flex justify-start">
          <div class="rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3">
            <div class="flex space-x-1.5">
              <span class="h-2 w-2 animate-bounce rounded-full bg-amber-400"></span>
              <span class="h-2 w-2 animate-bounce rounded-full bg-amber-400" style="animation-delay:.15s"></span>
              <span class="h-2 w-2 animate-bounce rounded-full bg-amber-400" style="animation-delay:.3s"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- quick prompts -->
      <div v-if="!messages.some(m=>m.role==='user')" class="flex flex-wrap gap-1.5 px-4 pb-2">
        <button v-for="q in ['Come migliorare l\'alimentazione','Un consiglio per lo stress','Riduciamo gli zuccheri']" :key="q" @click="ask(q)"
          class="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-600 hover:border-amber-300 hover:text-amber-700">{{ q }}</button>
      </div>

      <!-- input -->
      <div class="border-t border-slate-200 p-3">
        <div class="flex items-end gap-2">
          <textarea v-model="newMessage" @keydown.enter.exact.prevent="sendMessage" rows="1"
            placeholder="Scrivi al tuo coach…"
            class="max-h-28 min-h-[40px] flex-1 resize-none rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-amber-400 focus:outline-none focus:ring-1 focus:ring-amber-400"
            :disabled="loading"></textarea>
          <button @click="sendMessage" :disabled="loading || !newMessage.trim()"
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500 text-white hover:bg-amber-600 disabled:opacity-40">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>
          </button>
        </div>
        <p class="mt-1.5 flex items-center justify-center gap-1 text-[10px] text-slate-400">
          <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
          I messaggi vengono cancellati al logout per proteggere la privacy
        </p>
      </div>

      <!-- AZIONI + Suggerimenti drawer (collapsed by default) -->
      <div class="shrink-0 border-t border-slate-200 bg-slate-50">
        <button @click="showSuggestions=!showSuggestions"
          class="flex w-full items-center justify-between px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100">
          <span class="flex items-center gap-1.5">
            <svg class="h-4 w-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364-.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>
            Suggerimenti &amp; Azioni
          </span>
          <svg class="h-4 w-4 text-slate-400 transition-transform" :class="{ 'rotate-180': showSuggestions }" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
        </button>
        <div v-if="showSuggestions" class="max-h-[45vh] space-y-3 overflow-y-auto border-t border-slate-200 p-3">
          <!-- Azioni -->
          <div class="flex gap-2">
            <button @click="joinProgramFromAction"
              class="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-teal-600 px-3 py-2 text-xs font-medium text-white hover:bg-teal-700">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
              Iscriviti a un programma
            </button>
            <button @click="ask('Dammi informazioni evidence-based')"
              class="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>
              Fonti evidence-based
            </button>
          </div>
          <!-- Programs -->
          <div class="space-y-1.5">
            <p class="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Programmi</p>
            <button v-for="p in programs" :key="p.id" @click="toggleProgram(p)"
              class="flex w-full items-center gap-2.5 rounded-lg border px-2.5 py-2 text-left transition hover:border-amber-200"
              :class="p.joined ? 'border-teal-200 bg-teal-50' : 'border-slate-200 bg-white'">
              <span class="flex h-7 w-7 items-center justify-center rounded-md bg-amber-50">
                <svg v-if="p.icon==='walk'" class="h-4 w-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 5l7 7-7 7M5 5l7 7-7 7"/></svg>
                <svg v-else-if="p.icon==='mind'" class="h-4 w-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v18M3 12h18"/></svg>
                <svg v-else class="h-4 w-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4"/></svg>
              </span>
              <div class="min-w-0 flex-1">
                <p class="truncate text-xs font-medium text-slate-800">{{ p.name }}</p>
                <p class="truncate text-[11px] text-slate-400">{{ p.desc }}</p>
              </div>
              <span v-if="p.joined" class="rounded-full bg-teal-100 px-1.5 py-0.5 text-[10px] font-semibold text-teal-700">Iscritto</span>
            </button>
          </div>
          <!-- EBM sources -->
          <div class="space-y-1 border-t border-slate-100 pt-2.5">
            <p class="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Fonti scientifiche</p>
            <div v-for="s in ebmSources" :key="s.title" class="rounded-md px-1 py-0.5">
              <p class="text-xs font-medium text-slate-700">{{ s.title }}</p>
              <p class="text-[11px] text-slate-400">{{ s.src }} · {{ s.year }}</p>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>

  <!-- ===================== DOCTOR (compact rail) ===================== -->
  <div v-else class="flex h-full flex-col">
    <div ref="scrollRef" class="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
      <div v-for="(msg, i) in messages" :key="i" :class="['flex', msg.role==='user'?'justify-end':'justify-start']">
        <div :class="['max-w-[85%] whitespace-pre-wrap px-3 py-2 text-sm leading-relaxed',
          msg.role==='user' ? 'rounded-2xl rounded-br-sm bg-teal-600 text-white' : 'rounded-2xl rounded-bl-sm border border-slate-200 bg-slate-50 text-slate-700']">
          {{ msg.content }}
        </div>
      </div>
      <div v-if="loading" class="flex justify-start">
        <div class="rounded-2xl rounded-bl-sm border border-slate-200 bg-slate-50 px-4 py-3">
          <div class="flex space-x-1.5">
            <span class="h-2 w-2 animate-bounce rounded-full bg-teal-400"></span>
            <span class="h-2 w-2 animate-bounce rounded-full bg-teal-400" style="animation-delay:.15s"></span>
            <span class="h-2 w-2 animate-bounce rounded-full bg-teal-400" style="animation-delay:.3s"></span>
          </div>
        </div>
      </div>
    </div>
    <div v-if="!messages.some(m=>m.role==='user')" class="flex flex-wrap gap-1.5 px-4 pb-2">
      <button v-for="q in quickPrompts" :key="q" @click="ask(q)"
        class="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-600 hover:border-teal-300 hover:text-teal-700">{{ q }}</button>
    </div>
    <div class="border-t border-slate-200 p-3">
      <div class="flex items-end gap-2">
        <textarea v-model="newMessage" @keydown.enter.exact.prevent="sendMessage" rows="1"
          :placeholder="selectedContext ? 'Chiedi sui valori del paziente…' : 'Panoramica pazienti, analisi generale…'"
          class="max-h-28 min-h-[40px] flex-1 resize-none rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-teal-400 focus:outline-none focus:ring-1 focus:ring-teal-400"
          :disabled="loading"></textarea>
        <button @click="sendMessage" :disabled="loading || !newMessage.trim()"
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-40">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>
        </button>
      </div>
      <p class="mt-1.5 flex items-center justify-center gap-1 text-[10px] text-slate-400">
        <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
        Messaggi cancellati al logout (privacy)
      </p>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity .2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
