<script setup>
/**
 * Clean clinical trend chart.
 *  - Click a metric chip to ADD / remove its line.
 *  - First selected metric defines the primary axis + reference band.
 *  - Points are coloured by status: in-range = metric colour, out-of-range = red ring.
 */
import { ref, computed, watch } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS, Tooltip, Legend, CategoryScale, LinearScale,
  PointElement, LineElement, Filler
} from 'chart.js'

ChartJS.register(Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement, Filler)

const props = defineProps({
  exams: { type: Array, default: () => [] },
  condition: { type: String, default: '' },
  height: { type: Number, default: 300 }
})

// name -> { label, color, unit, min, max, decimals }
const META = {
  'HbA1c':                  { label: 'HbA1c',              color: '#0d9488', unit: '%',     min: 4.0,  max: 6.0,  decimals: 1 },
  'Glicemia a digiuno':     { label: 'Glicemia digiuno',   color: '#e11d48', unit: 'mg/dL', min: 70,   max: 100,  decimals: 0 },
  'Glicemia postprandiale': { label: 'Glicemia post-pr.',  color: '#f97316', unit: 'mg/dL', min: 70,   max: 140,  decimals: 0 },
  'Colesterolo LDL':        { label: 'Colest. LDL',        color: '#7c3aed', unit: 'mg/dL', min: 0,    max: 100,  decimals: 0 },
  'Colesterolo HDL':        { label: 'Colest. HDL',        color: '#059669', unit: 'mg/dL', min: 40,   max: 80,   decimals: 0 },
  'Colesterolo totale':     { label: 'Colest. totale',     color: '#2563eb', unit: 'mg/dL', min: 0,    max: 200,  decimals: 0 },
  'Trigliceridi':           { label: 'Trigliceridi',       color: '#db2777', unit: 'mg/dL', min: 0,    max: 150,  decimals: 0 },
  'Creatinina':             { label: 'Creatinina',         color: '#0891b2', unit: 'mg/dL', min: 0.7,  max: 1.3,  decimals: 2 },
  'eGFR':                   { label: 'eGFR',               color: '#65a30d', unit: 'mL/min',min: 60,   max: 120,  decimals: 0 },
  'Microalbuminuria':       { label: 'Microalbuminuria',   color: '#ca8a04', unit: 'mg/g',  min: 0,    max: 30,   decimals: 0 },
  'Pressione sistolica':    { label: 'P. sistolica',       color: '#dc2626', unit: 'mmHg',  min: 90,   max: 120,  decimals: 0 },
  'Pressione diastolica':   { label: 'P. diastolica',      color: '#9333ea', unit: 'mmHg',  min: 60,   max: 80,   decimals: 0 },
  'Potassio':               { label: 'Potassio',           color: '#0284c7', unit: 'mmol/L',min: 3.5,  max: 5.1,  decimals: 1 },
  'Sodio':                  { label: 'Sodio',              color: '#475569', unit: 'mmol/L',min: 136,  max: 145,  decimals: 0 },
}

const selected = ref([])

// All unique dates, ascending
const dates = computed(() => {
  const set = [...new Set(props.exams.map(e => (e.date || '').split(' ')[0]))]
  return set.filter(Boolean).sort()
})

// Metric catalogue present in this patient's data
const metrics = computed(() => {
  const present = [...new Set(props.exams.map(e => e.test_name))]
  return present
    .filter(name => META[name])
    .map(name => {
      const series = props.exams
        .filter(e => e.test_name === name)
        .sort((a, b) => (a.date || '').localeCompare(b.date || ''))
      const m = META[name]
      const latest = series[series.length - 1]
      const first = series[0]
      const lv = latest ? parseFloat(latest.test_value) : null
      const fv = first ? parseFloat(first.test_value) : null
      const trend = (lv != null && fv != null) ? lv - fv : 0
      const outRange = latest ? (lv < m.min || lv > m.max) : false
      return {
        name, ...m,
        latest: latest ? latest.test_value : '—',
        trend,            // positive = worsening for most (except HDL, eGFR where up = better)
        outRange,
        count: series.length,
      }
    })
})

// series per metric: { date -> value }
function valuesFor(name) {
  const map = {}
  for (const e of props.exams) {
    if (e.test_name === name) map[(e.date || '').split(' ')[0]] = parseFloat(e.test_value)
  }
  return map
}

function statusOf(name, v) {
  const m = META[name]
  if (!m || v == null || isNaN(v)) return 'normal'
  return (v < m.min || v > m.max) ? 'abnormal' : 'normal'
}

function pointColors(name) {
  const m = META[name]
  const map = valuesFor(name)
  return {
    bg: dates.value.map(d => statusOf(name, map[d]) === 'abnormal' ? '#fff' : m.color),
    border: dates.value.map(d => statusOf(name, map[d]) === 'abnormal' ? '#dc2626' : m.color),
  }
}

// axis min/max per metric so the band always fits
function axisBounds(name) {
  const m = META[name]
  const vals = Object.values(valuesFor(name)).filter(v => !isNaN(v))
  if (!vals.length) return { min: m.min, max: m.max }
  const dmin = Math.min(...vals, m.min)
  const dmax = Math.max(...vals, m.max)
  const pad = (dmax - dmin) * 0.12 || 1
  return { min: dmin - pad, max: dmax + pad }
}

const chartData = computed(() => {
  const labels = dates.value.map(d => {
    const [y, mo, da] = d.split('-')
    return `${da}/${mo}`
  })
  const datasets = selected.value.map((name, i) => {
    const m = META[name]
    const map = valuesFor(name)
    const pc = pointColors(name)
    const data = dates.value.map(d => (map[d] != null ? map[d] : null))
    return {
      label: m.label,
      data,
      borderColor: m.color,
      backgroundColor: m.color + '12',
      borderWidth: 2.5,
      tension: 0.35,
      fill: false,
      spanGaps: true,
      yAxisID: `y${i}`,
      pointRadius: 4.5,
      pointHoverRadius: 6.5,
      pointBorderWidth: 2,
      pointBackgroundColor: pc.bg,
      pointBorderColor: pc.border,
    }
  })
  return { labels, datasets }
})

const chartOptions = computed(() => {
  const scales = {
    x: {
      grid: { display: false },
      border: { color: '#e2e8f0' },
      ticks: { color: '#64748b', font: { size: 11 } },
    },
  }
  selected.value.forEach((name, i) => {
    const m = META[name]
    const b = axisBounds(name)
    const isPrimary = i === 0
    scales[`y${i}`] = {
      type: 'linear',
      position: i % 2 === 0 ? 'left' : 'right',
      min: b.min,
      max: b.max,
      grid: { display: isPrimary, color: '#f1f5f9', drawTicks: false },
      border: { display: false },
      ticks: {
        color: m.color,
        font: { size: 10, weight: '600' },
        padding: 6,
        maxTicksLimit: 5,
        callback: (v) => Number.isInteger(v) ? v : v.toFixed(1),
      },
    }
  })
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { display: false },
      rangeBand: selected.value.length
        ? { axisId: 'y0', min: META[selected.value[0]].min, max: META[selected.value[0]].max }
        : null,
      tooltip: {
        backgroundColor: '#0f172a',
        titleColor: '#e2e8f0',
        bodyColor: '#e2e8f0',
        padding: 10,
        cornerRadius: 8,
        boxPadding: 4,
        usePointStyle: true,
        callbacks: {
          label: (ctx) => {
            const name = selected.value[ctx.datasetIndex]
            const m = META[name]
            const v = ctx.parsed.y
            if (v == null) return null
            const st = statusOf(name, v) === 'abnormal' ? '  ⚠ fuori range' : ''
            return `  ${m.label}: ${Number.isInteger(v) ? v : v.toFixed(m.decimals)} ${m.unit}${st}`
          },
        },
      },
    },
    scales,
  }
})

// reference-range band plugin (primary axis only)
const rangeBandPlugin = {
  id: 'rangeBand',
  beforeDatasetsDraw(chart) {
    const opt = chart.options.plugins.rangeBand
    if (!opt || !opt.axisId) return
    const scale = chart.scales[opt.axisId]
    if (!scale) return
    const { ctx, chartArea } = chart
    const yTop = scale.getPixelForValue(opt.max)
    const yBot = scale.getPixelForValue(opt.min)
    const top = Math.max(yTop, chartArea.top)
    const bot = Math.min(yBot, chartArea.bottom)
    if (bot <= top) return
    ctx.save()
    ctx.fillStyle = 'rgba(16, 185, 129, 0.08)'
    ctx.fillRect(chartArea.left, top, chartArea.right - chartArea.left, bot - top)
    // dashed boundary lines
    ctx.strokeStyle = 'rgba(16, 185, 129, 0.35)'
    ctx.setLineDash([4, 4])
    ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(chartArea.left, top); ctx.lineTo(chartArea.right, top); ctx.stroke()
    ctx.beginPath(); ctx.moveTo(chartArea.left, bot); ctx.lineTo(chartArea.right, bot); ctx.stroke()
    ctx.restore()
  },
}

function toggle(name) {
  const i = selected.value.indexOf(name)
  if (i > -1) selected.value.splice(i, 1)
  else if (selected.value.length < 4) selected.value.push(name)
}
function isSelected(name) { return selected.value.includes(name) }

// better-direction-aware trend arrow: for HDL & eGFR higher is better
function trendArrow(metric) {
  const upGood = ['Colesterolo HDL', 'eGFR']
  const improving = upGood.includes(metric.name) ? metric.trend > 0 : metric.trend < 0
  if (Math.abs(metric.trend) < 1e-6) return { sym: '→', cls: 'text-slate-400' }
  const sym = metric.trend > 0 ? '▲' : '▼'
  const cls = improving ? 'text-emerald-600' : 'text-rose-600'
  return { sym, cls }
}

// auto-select on data load / condition change
watch(() => props.exams, (ex) => {
  if (!ex || !ex.length) return
  selected.value = []
  const cond = (props.condition || '').toLowerCase()
  if (cond.includes('diabete')) {
    ['HbA1c', 'Glicemia a digiuno'].forEach(n => metrics.value.find(m => m.name === n) && selected.value.push(n))
  } else if (cond.includes('ipertensione')) {
    ['Pressione sistolica', 'Pressione diastolica'].forEach(n => metrics.value.find(m => m.name === n) && selected.value.push(n))
  }
  if (!selected.value.length && metrics.value.length) selected.value.push(metrics.value[0].name)
}, { immediate: true })
</script>

<template>
  <div>
    <!-- Metric chips: click to add/remove a line -->
    <div class="flex flex-wrap gap-2 mb-4">
      <button
        v-for="m in metrics" :key="m.name"
        @click="toggle(m.name)"
        :class="[
          'group inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-all',
          isSelected(m.name)
            ? 'bg-white shadow-sm'
            : 'bg-slate-50 border-slate-200 text-slate-500 hover:border-slate-300 hover:text-slate-700'
        ]"
        :style="isSelected(m.name) ? { borderColor: m.color, color: m.color } : {}"
      >
        <span class="h-2.5 w-2.5 rounded-full" :style="{ backgroundColor: m.color }"></span>
        <span>{{ m.label }}</span>
        <span class="font-semibold tabular-nums">{{ m.latest }}<span class="opacity-60 ml-0.5">{{ m.unit }}</span></span>
        <span v-if="m.count > 1" :class="['text-[10px]', trendArrow(m).cls]" :title="'variazione 10 mesi'">{{ trendArrow(m).sym }}</span>
        <span v-if="m.outRange" class="h-1.5 w-1.5 rounded-full bg-rose-500" title="fuori range"></span>
      </button>
    </div>

    <!-- Legend hint -->
    <div class="flex items-center gap-4 mb-2 text-[11px] text-slate-400">
      <span class="flex items-center gap-1.5"><span class="h-2 w-4 rounded-sm bg-emerald-500/20 border border-emerald-500/40"></span> range normale</span>
      <span class="flex items-center gap-1.5"><span class="h-2.5 w-2.5 rounded-full bg-white border-2 border-rose-600"></span> valore fuori range</span>
      <span class="ml-auto">max 4 parametri · {{ selected.length }} attivi</span>
    </div>

    <!-- Chart -->
    <div v-if="selected.length" :style="{ height: height + 'px' }">
      <Line :data="chartData" :options="chartOptions" :plugins="[rangeBandPlugin]" />
    </div>

    <!-- Empty state -->
    <div v-else class="flex flex-col items-center justify-center text-center" :style="{ height: height + 'px' }">
      <svg class="h-10 w-10 text-slate-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 13.5h4l3-8 4 16 3-8h4" />
      </svg>
      <p class="text-sm text-slate-500">Seleziona un parametro per visualizzare l'andamento</p>
    </div>
  </div>
</template>
