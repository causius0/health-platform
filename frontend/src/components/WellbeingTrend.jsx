/** Wellbeing/work indicator trend: score over time per instrument.
 * Covers the study matrix's longitudinal view (e.g. the 4-year Kangbuk cohort). */
import { useMemo, useState } from 'react'
import { Chart, registerables } from 'chart.js'
import { Line } from 'react-chartjs-2'
import { formatDate } from '../lib/format'

Chart.register(...registerables)

const PALETTE = ['#0c6e64', '#175cd3', '#b54708', '#7c3aed']

export default function WellbeingTrend({ assessments = [] }) {
  const byInstrument = useMemo(() => {
    const groups = new Map()
    for (const a of assessments) {
      if (!groups.has(a.instrument)) {
        groups.set(a.instrument, { instrument: a.instrument, label: a.label, rows: [] })
      }
      groups.get(a.instrument).rows.push(a)
    }
    for (const g of groups.values()) g.rows.sort((x, y) => new Date(x.taken_on) - new Date(y.taken_on))
    return [...groups.values()]
  }, [assessments])

  const [selected, setSelected] = useState(null)
  const active = byInstrument.find((g) => g.instrument === selected) || byInstrument[0]

  if (!byInstrument.length) {
    return <div className="empty">Compila i questionari per vedere l'andamento nel tempo.</div>
  }

  const rows = active.rows
  const chartData = {
    labels: rows.map((r) => formatDate(r.taken_on)),
    datasets: [{
      label: active.label,
      data: rows.map((r) => r.score),
      borderColor: PALETTE[0],
      backgroundColor: PALETTE[0],
      borderWidth: 2,
      pointRadius: 3,
      tension: 0.25,
    }],
  }
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false }, ticks: { font: { size: 10 }, maxRotation: 0 } },
      y: { grid: { color: '#eef1f4' }, ticks: { font: { size: 10 } } },
    },
  }

  return (
    <div>
      <div className="row wrap" style={{ gap: 6, marginBottom: 10 }}>
        {byInstrument.map((g) => (
          <button key={g.instrument} className="chip"
                  style={g.instrument === active.instrument
                    ? { borderColor: 'var(--brand)', color: 'var(--brand-strong)', fontWeight: 650 }
                    : undefined}
                  onClick={() => setSelected(g.instrument)}>
            {g.label}
          </button>
        ))}
      </div>
      <div style={{ height: 200 }}>
        <Line data={chartData} options={options} />
      </div>
      <p className="reference-note" style={{ marginTop: 6 }}>
        Punteggio per compilazione · {active.rows.length} rilevazioni · la categoria è
        mostrata nella sezione Indicatori di benessere.
      </p>
    </div>
  )
}
