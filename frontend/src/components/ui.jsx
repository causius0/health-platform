import { useEffect, useState } from 'react'
import { RISK_LEVEL_LABEL } from '../lib/format'
import Icon from './Icon'

export function RiskBadge({ level, size }) {
  if (!level) return null
  return (
    <span className={`badge level-${level}`} style={size ? { fontSize: size, padding: '3px 12px' } : undefined}>
      <span className="dot" />
      {RISK_LEVEL_LABEL[level]}
    </span>
  )
}

export function TierBadge({ tier }) {
  if (!tier) return null
  return (
    <span className={`badge tier-${tier}`}>
      <span className="dot" />
      {tier.charAt(0).toUpperCase() + tier.slice(1)}
    </span>
  )
}

export function Badge({ tone = 'neutral', dot, children }) {
  return (
    <span className={`badge badge-${tone}`}>
      {dot && <span className="dot" />}
      {children}
    </span>
  )
}

export function Modal({ title, onClose, children, footer, wide }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose?.() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose?.() }}>
      <div className={`modal${wide ? ' wide' : ''}`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-head">
          <h3>{title}</h3>
          <button className="modal-x" onClick={onClose} aria-label="Chiudi"><Icon name="x" size={16} /></button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  )
}

export function Loading({ label = 'Caricamento…' }) {
  return (
    <div className="row" style={{ justifyContent: 'center', padding: 36, gap: 10, color: 'var(--muted)' }}>
      <span className="spinner" />
      <span style={{ fontSize: 12.5 }}>{label}</span>
    </div>
  )
}

export function Empty({ icon = 'folder', children, action }) {
  return (
    <div className="empty">
      <div className="icon"><Icon name={icon} size={22} /></div>
      <div style={{ maxWidth: 380, margin: '0 auto 8px' }}>{children}</div>
      {action}
    </div>
  )
}

export function Progress({ value, tone }) {
  return (
    <div className="progress">
      <div className={`bar${tone ? ` ${tone}` : ''}`} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  )
}

export function StatTile({ label, value, unit, ref: refText, state, onClick }) {
  return (
    <div className={`tile${state ? ` state-${state}` : ''}`} onClick={onClick} style={onClick ? { cursor: 'pointer' } : undefined}>
      <div className="label">{label}</div>
      <div className="value">
        {value}
        {unit && <span className="unit">{unit}</span>}
      </div>
      {refText && <div className="ref">{refText}</div>}
    </div>
  )
}

export function Field({ label, help, children }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
      {help && <span className="help">{help}</span>}
    </div>
  )
}

/** Accessible confirmation dialog replacing native confirm()/prompt(). */
export function ConfirmDialog({ open, title, message, confirmLabel = 'Conferma', tone = 'primary', input = false, busy, onConfirm, onCancel }) {
  const [text, setText] = useState('')
  useEffect(() => { if (open) setText('') }, [open])
  if (!open) return null
  return (
    <Modal
      title={title}
      onClose={onCancel}
      footer={
        <>
          <button className="btn btn-secondary" onClick={onCancel}>Annulla</button>
          <button className={`btn btn-${tone}`} disabled={busy || (input && !text.trim())} onClick={() => onConfirm(text.trim())}>
            {confirmLabel}
          </button>
        </>
      }
    >
      <p style={{ fontSize: 13 }}>{message}</p>
      {input && (
        <div className="field" style={{ marginTop: 12 }}>
          <label>Esito</label>
          <input className="input" value={text} onChange={(e) => setText(e.target.value)}
                 placeholder="es. paziente contattato, aderenza migliorata" autoFocus />
        </div>
      )}
    </Modal>
  )
}
