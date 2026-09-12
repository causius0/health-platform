import { metricDelta } from '../lib/format'

/** One-line "▲ 142 → 136 (−4.2%)" progression hint for a plan-table row. */
export default function DeltaLine({ observations, code }) {
  const d = metricDelta(observations, code)
  if (!d) return null
  const arrow = d.pct === null ? '' : d.pct > 0 ? '▲' : d.pct < 0 ? '▼' : '＝'
  return (
    <div style={{ fontSize: 10.5, color: 'var(--muted)', marginTop: 2 }}>
      {arrow} {d.prev} → {d.latest}{d.pct !== null && ` (${d.pct > 0 ? '+' : ''}${d.pct}%)`}
    </div>
  )
}
