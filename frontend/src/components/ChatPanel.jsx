/** Role-aware chat panel: patient coach with human handoff; doctor queue and
 * clinical assistant for the selected patient. */
import { useEffect, useRef, useState } from 'react'
import * as api from '../lib/api'
import { formatDateTime, parseTiered } from '../lib/format'
import Icon from './Icon'
import { ConfirmDialog, Modal } from './ui'

const SENDER_LABEL = { patient: 'Lavoratore', bot: 'Assistente', doctor: 'Operatore' }

function TieredBubble({ content }) {
  const t = parseTiered(content)
  if (!t.advice && !t.clinical) return <span>{content}</span>
  const clinical = t.clinical && t.clinical.toLowerCase() !== 'non necessaria in questo caso.'
  return (
    <>
      <span className="tier-label">Informazione generale</span>
      {t.general}
      {t.advice && (
        <div className="tier-block">
          <span className="tier-label">Consiglio della settimana</span>
          {t.advice}
        </div>
      )}
      {clinical && (
        <div className="tier-block">
          <span className="tier-label" style={{ color: 'var(--warn)' }}>Indicazione clinica</span>
          {t.clinical}
        </div>
      )}
    </>
  )
}

export default function ChatPanel({ role, patientId = null, patientName = '', patientRisk = null, onThreadsChanged }) {
  const [mode, setMode] = useState(role === 'doctor' ? 'queue' : 'coach')
  const [threads, setThreads] = useState([])
  const [thread, setThread] = useState(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [showEscalate, setShowEscalate] = useState(false)
  const [escalateSubject, setEscalateSubject] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const scrollRef = useRef(null)

  async function openThread(id) {
    setThread(await api.getChatThread(id))
    requestAnimationFrame(() => {
      const el = scrollRef.current
      if (el) el.scrollTop = el.scrollHeight
    })
  }

  async function loadThreads({ openFirst = true } = {}) {
    const list = await api.getChatThreads()
    setThreads(list)
    if (openFirst && list.length) {
      if (role === 'patient') await openThread(list[0].id)
      else {
        const first = list.find((t) => t.status === 'waiting_operator') || list[0]
        await openThread(first.id)
      }
    } else if (!list.length) {
      setThread(null)
    }
  }

  function fail(err) {
    setError(err?.message || 'Errore di rete')
  }

  useEffect(() => {
    loadThreads().catch(fail)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (role !== 'doctor') return
    setThread(null)
    setError('')
    if (mode === 'queue') loadThreads().catch(fail)
    else if (patientId) openPatientThread().catch(fail)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, patientId])

  async function openPatientThread() {
    if (!patientId) { setThread(null); return }
    const t = await api.startChatThread({ patient_id: patientId })
    await openThread(t.id)
  }

  async function startThread() {
    setBusy(true); setError('')
    try {
      await api.startChatThread({})
      await loadThreads()
      onThreadsChanged?.()
    } catch (err) { fail(err) } finally { setBusy(false) }
  }

  async function send(e) {
    e.preventDefault()
    const content = draft.trim()
    if (!content || !thread || busy) return
    setBusy(true); setError('')
    try {
      await api.sendChatMessage(thread.id, content)
      setDraft('')
      await openThread(thread.id)
    } catch (err) { fail(err) } finally { setBusy(false) }
  }

  async function escalate() {
    setBusy(true); setError('')
    try {
      await api.escalateThread(thread.id, escalateSubject || 'Richiesta operatore')
      setShowEscalate(false)
      setEscalateSubject('')
      await Promise.all([openThread(thread.id), loadThreads({ openFirst: false })])
      onThreadsChanged?.()
    } catch (err) { fail(err) } finally { setBusy(false) }
  }

  async function claim() {
    setBusy(true); setError('')
    try {
      await api.claimThread(thread.id)
      await Promise.all([openThread(thread.id), loadThreads({ openFirst: false })])
      onThreadsChanged?.()
    } catch (err) { fail(err) } finally { setBusy(false) }
  }

  async function close() {
    setBusy(true); setError('')
    try {
      await api.closeThread(thread.id)
      await Promise.all([openThread(thread.id), loadThreads({ openFirst: false })])
      onThreadsChanged?.()
    } catch (err) { fail(err) } finally { setBusy(false) }
  }

  async function remove() {
    setError('')
    try {
      await api.deleteThread(thread.id)
      setThread(null)
      await loadThreads({ openFirst: false })
    } catch (err) { fail(err) }
  }

  const bubbleClass = (sender) =>
    ({ patient: 'bubble-patient', bot: 'bubble-bot', doctor: 'bubble-doctor' }[sender] || 'bubble-bot')

  const statusBadge = thread?.status === 'waiting_operator'
    ? { label: 'In attesa di operatore', cls: 'badge-warn' }
    : thread?.status === 'with_operator'
      ? { label: 'Gestita da operatore', cls: 'badge-info' }
      : null

  const canSend = thread && (
    role === 'patient' ||
    thread.status === 'with_operator' ||
    mode === 'patient'
  )

  const placeholder = role === 'patient'
    ? thread?.status === 'bot' ? 'Scrivi al coach di prevenzione…' : 'Scrivi: il messaggio arriva all’operatore…'
    : mode === 'patient' ? 'Chiedi un’analisi dei dati del paziente…' : 'Rispondi al lavoratore…'

  const queueThreads = role === 'doctor' && mode === 'queue' ? threads : []

  return (
    <div className="chat">
      <div className="chat-head">
        <div className="row-between">
          <div>
            <h3 style={{ textTransform: 'none', letterSpacing: 0 }}>
              {role === 'patient'
                ? 'Coach di prevenzione'
                : mode === 'queue' ? 'Presa in carico richieste' : `Analisi — ${patientName}`}
            </h3>
            {role === 'patient' && (
              <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
                Assistente automatico con possibilità di parlare con un operatore
              </p>
            )}
            {role === 'doctor' && mode === 'patient' && patientRisk && (
              <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
                Rischio <strong>{patientRisk.level}</strong> · {patientRisk.risk_count} fattori attivi,{' '}
                {patientRisk.protective_count} protettivi
              </p>
            )}
          </div>
          {role === 'doctor' && (
            <div className="segmented">
              <button className={mode === 'queue' ? 'active' : ''} onClick={() => setMode('queue')}>Coda</button>
              <button className={mode === 'patient' ? 'active' : ''} onClick={() => setMode('patient')}
                      disabled={!patientId} title={!patientId ? 'Seleziona prima un lavoratore dall’elenco' : undefined}>
                Paziente
              </button>
            </div>
          )}
        </div>
      </div>

      {queueThreads.length > 1 && (
        <div className="chat-threads" style={{ padding: '8px 12px', borderBottom: '1px solid var(--border)', maxHeight: 130, overflowY: 'auto' }}>
          {queueThreads.map((t) => (
            <button
              key={t.id}
              onClick={() => openThread(t.id).catch(fail)}
              className={`row-between btn btn-sm ${thread?.id === t.id ? 'btn-secondary' : 'btn-ghost'}`}
              style={{ width: '100%', marginBottom: 4, justifyContent: 'space-between', textAlign: 'left' }}
            >
              <span style={{ fontWeight: thread?.id === t.id ? 600 : 400 }}>{t.patient_name || `#${t.id}`}</span>
              <span className={`badge ${t.status === 'waiting_operator' ? 'badge-warn' : t.status === 'with_operator' ? 'badge-info' : ''}`}>
                {t.status === 'waiting_operator' ? 'in attesa' : t.status === 'with_operator' ? 'in carico' : 'bot'}
              </span>
            </button>
          ))}
        </div>
      )}

      <div className="chat-scroll" ref={scrollRef}>
        {!thread && (
          <div className="empty">
            <div className="icon"><Icon name="chat" size={22} /></div>
            <p style={{ maxWidth: 260, margin: '0 auto 10px' }}>
              {role === 'patient'
                ? 'Nessuna conversazione in corso. Puoi iniziare a scrivere al coach oppure richiedere un operatore.'
                : mode === 'queue'
                  ? 'Nessuna richiesta di presa in carico in coda.'
                  : 'Seleziona un paziente per iniziare.'}
            </p>
            {role === 'patient' && (
              <button className="btn btn-primary btn-sm" disabled={busy} onClick={startThread}>
                Inizia la conversazione
              </button>
            )}
          </div>
        )}

        {thread && thread.messages.map((m) => (
          <div key={m.id} className={`bubble ${bubbleClass(m.sender)}`}>
            {(role === 'doctor' || m.sender === 'patient') && (
              <div style={{ fontSize: 10, opacity: 0.75, marginBottom: 2 }}>{SENDER_LABEL[m.sender]}</div>
            )}
            {m.sender === 'bot' ? <TieredBubble content={m.content} /> : m.content}
            <div className="meta">{formatDateTime(m.created_at)}</div>
          </div>
        ))}
      </div>

      {error && (
        <div style={{ padding: '6px 12px', fontSize: 12, color: 'var(--danger, #b3261e)', borderTop: '1px solid var(--border)' }}>
          ⚠ {error}
        </div>
      )}

      {thread && (
        <div className="chat-foot">
          <div className="row" style={{ marginBottom: 8, flexWrap: 'wrap' }}>
            {statusBadge && (
              <span className={`badge ${statusBadge.cls}`}><span className="dot" />{statusBadge.label}</span>
            )}
            <span className="grow" />
            {role === 'doctor' && thread.status === 'waiting_operator' && (
              <button className="btn btn-primary btn-sm" onClick={claim} disabled={busy}>Prendi in carico</button>
            )}
            {role === 'doctor' && thread.status === 'with_operator' && (
              <button className="btn btn-secondary btn-sm" onClick={close} disabled={busy}>Chiudi e torna al bot</button>
            )}
            {role === 'patient' && (
              <button className="btn btn-danger btn-sm" onClick={() => setConfirmDelete(true)}>Cancella cronologia</button>
            )}
          </div>

          {role === 'patient' && thread.status === 'bot' && (
            <div className="row" style={{ marginBottom: 8 }}>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowEscalate(true)}>
                Parla con un operatore
              </button>
            </div>
          )}

          <form className="form-row" onSubmit={send}>
            <input
              className="input"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={placeholder}
              disabled={!canSend || busy}
            />
            <button className="btn btn-primary" type="submit" disabled={!canSend || busy || !draft.trim()}>
              Invia
            </button>
          </form>
        </div>
      )}

      {confirmDelete && (
        <ConfirmDialog
          open
          tone="danger" confirmLabel="Cancella definitivamente"
          title="Cancellare la conversazione?"
          message="Tutti i messaggi verranno eliminati in modo definitivo. L'operatore non potrà più consultarli."
          onConfirm={remove}
          onCancel={() => setConfirmDelete(false)}
        />
      )}

      {showEscalate && (
        <Modal
          title="Richiedi un operatore sanitario"
          onClose={() => setShowEscalate(false)}
          footer={
            <>
              <button className="btn btn-secondary" onClick={() => setShowEscalate(false)}>Annulla</button>
              <button className="btn btn-primary" disabled={busy} onClick={escalate}>Invia richiesta</button>
            </>
          }
        >
          <div className="field">
            <label>Di cosa vuoi parlare?</label>
            <input
              className="input"
              value={escalateSubject}
              onChange={(e) => setEscalateSubject(e.target.value)}
              placeholder="es. ho bisogno di aiuto con la dieta"
            />
            <span className="help">I messaggi già scritti e i prossimi arriveranno direttamente all’operatore.</span>
          </div>
        </Modal>
      )}
    </div>
  )
}
