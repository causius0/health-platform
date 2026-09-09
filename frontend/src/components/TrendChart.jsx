/** Multi-metric trend chart over observations, with reference-range hints. */
import { useMemo, useState } from 'react'
import { Chart, registerables } from 'chart.js'
import { Line } from 'react-chartjs-2'
import { formatDate } from '../lib/format'

Chart.register(...registerables)

const REF = {
  hba1c: { max: 7.0, label: 'target < 7.0' },
  glucose_fasting: { max: 130, label: '< 130' },
  glucose_pp: { max: 140, label: '< 140' },
  ldl: { max: 100, label: '< 100' },
  triglycerides: { max: 150, label: '< 150' },
  bp_systolic: { max: 130, label: '< 130' },
  bp_diastolic: { max: 80, label: '< 80' },
  bmi: { min: 18.5, max: 24.9, label: '18.5–24.9' },
  waist: { max: 94, label: '< 94' },
}

const METRIC_LABEL = {
  hba1c: 'HbA1c', glucose_fasting: 'Glicemia', glucose_pp: 'Glicemia pp', ldl: 'LDL', hdl: 'HDL',
  triglycerides: 'Trigliceridi', bp_systolic: 'P. sistolica', bp_diastolic: 'P. diastolica',
  weight: 'Peso', bmi: 'BMI', waist: 'Vita', creatinine: 'Creatinina',
  egfr: 'eGFR', microalbuminuria: 'Microalb.', total_cholesterol: 'Colest. tot.',
}

const PALETTE = ['#0c6e64', '#175cd3', '#b54708', '#7c3aed']

function isOutOfRange(code, v) {
  const ref = REF[code]
  if (!ref) return false
  if (ref.min !== undefined && ref.max !== undefined) return v < ref.min || v > ref.max
  return ref.max !== undefined ? v > ref.max : v < ref.min
}

export default function TrendChart({ observations = [], initialCode = '', maxLines = 4 }) {
  const available = useMemo(() => {
    const byCode = new Map()
    for (const o of observations) {
      if (!byCode.has(o.code)) byCode.set(o.code, { code: o.code, n: 0 })
      byCode.get(o.code).n++
    }
    return [...byCode.values()]
      .filter((m) => m.n >= 2)
      .sort((a, b) => b.n - a.n)
      .slice(0, 14)
  }, [observations])

  const [selected, setSelected] = useState(() => {
    const first = available.filter((m) => m.n >= 2).slice(0, 1).map((m) => m.code)
    return initialCode && available.some((m) => m.code === initialCode) ? [initialCode] : first
  })

  function toggle(code) {
    setSelected((cur) => {
      if (cur.includes(code)) return cur.filter((c) => c !== code)
      if (cur.length >= maxLines) return cur
      return [...cur, code]
    })
  }

  const series = selected
    .map((code) => ({
      code,
      rows: observations
        .filter((o) => o.code === code)
        .slice()
        .sort((a, b) => new Date(a.taken_on) - new Date(b.taken_on)),
    }))
    .filter((s) => s.rows.length)

  const dates = [...new Set(series.flatMap((s) => s.rows.map((r) => r.taken_on)))]
    .sort((a, b) => new Date(a) - new Date(b))

  const data = {
    labels: dates.map((d) => formatDate(d)),
    datasets: series.map((s, idx) => ({
      label: METRIC_LABEL[s.code] || s.code,
      data: dates.map((d) => s.rows.find((r) => r.taken_on === d)?.value ?? null),
      borderColor: PALETTE[idx % PALETTE.length],
      backgroundColor: PALETTE[idx % PALETTE.length],
      borderWidth: 2,
      pointRadius: (ctx) => (ctx.raw !== null && isOutOfRange(s.code, ctx.raw) ? 4.5 : 2.5),
      pointBackgroundColor: (ctx) =>
        ctx.raw !== null && isOutOfRange(s.code, ctx.raw) ? '#b42318' : PALETTE[idx % PALETTE.length],
      tension: 0.25,
      spanGaps: true,
    })),
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'nearest', intersect: false },
    plugins: {
      legend: {
        display: selected.length > 1,
        labels: { boxWidth: 10, boxHeight: 10, font: { size: 11 } },
      },
      tooltip: { callbacks: { label: (item) => `${item.dataset.label}: ${item.raw}` } },
    },
    scales: {
      x: { grid: { display: false }, ticks: { font: { size: 10 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } },
      y: { grid: { color: '#eef1f4' }, ticks: { font: { size: 10 } } },
    },
  }

  if (!series.length) {
    return <div className="empty">Nessuna serie con almeno due misurazioni.</div>
  }

  return (
    <div>
      <div className="row wrap" style={{ gap: 6, marginBottom: 10 }}>
        {available.map((m) => (
          <button
            key={m.code}
            className="chip"
            style={selected.includes(m.code) ? { borderColor: 'var(--brand)', color: 'var(--brand-strong)', fontWeight: 650 } : undefined}
            onClick={() => toggle(m.code)}
          >
            {METRIC_LABEL[m.code] || m.code}
          </button>
        ))}
      </div>
      <div style={{ height: 240 }}>
        <Line data={data} options={options} />
      </div>
      {REF[series[0].code] && (
        <p className="reference-note" style={{ marginTop: 6 }}>
          Riferimento {METRIC_LABEL[series[0].code]}: {REF[series[0].code].label} · i punti rossi sono fuori range.
        </p>
      )}
    </div>
  )
}
