/** Shared anamnesis question editor (choice options with risk/protective flags,
 * multi-choice and free text) used by both the worker portal and the clinician. */

function flagOf(o) {
  if (o.risk) return { label: 'fattore di rischio', cls: 'badge-risk' }
  if (o.protective) return { label: 'protettivo', cls: 'badge-ok' }
  return null
}

export default function QuestionEditor({ question, value, onChange }) {
  const q = question
  if (q.answer_type === 'single_choice' && (q.options || []).length) {
    return (
      <div className="option-list">
        {q.options.map((o) => (
          <label key={o.value} className={`option-item${value === o.value ? ' selected' : ''}`}>
            <input type="radio" name={`q_${q.id}`} value={o.value}
                   checked={value === o.value} onChange={() => onChange(o.value)} />
            {o.label}
            {flagOf(o) && <span className={`badge ${flagOf(o).cls} flag`}>{flagOf(o).label}</span>}
          </label>
        ))}
      </div>
    )
  }
  if (q.answer_type === 'multi_choice' && (q.options || []).length) {
    const selected = Array.isArray(value) ? value : (value ? value.split(', ').map((s) => s.trim()) : [])
    function toggle(v, checked) {
      onChange(checked ? [...selected, v] : selected.filter((x) => x !== v))
    }
    return (
      <div className="option-list">
        {q.options.map((o) => (
          <label key={o.value} className={`option-item${selected.includes(o.value) ? ' selected' : ''}`}>
            <input type="checkbox" value={o.value}
                   checked={selected.includes(o.value)} onChange={(e) => toggle(o.value, e.target.checked)} />
            {o.label}
            {flagOf(o) && <span className={`badge ${flagOf(o).cls} flag`}>{flagOf(o).label}</span>}
          </label>
        ))}
        {selected.length > 0 && (
          <p className="reference-note">Risposta salvata come elenco separato da virgole.</p>
        )}
      </div>
    )
  }
  return (
    <input className="input" value={value ?? ''} onChange={(e) => onChange(e.target.value)}
           placeholder="Scrivi qui…" />
  )
}

/** Serialize the editor value for storage (multi-choice → comma-joined). */
export function serializeAnswer(value) {
  return Array.isArray(value) ? value.join(', ') : (value ?? '').toString().trim()
}
