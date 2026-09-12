/** Chat panel: patient prevention coach; doctor clinical assistant for the
 * selected patient. Both are pure virtual-assistant chats. */
import { useEffect, useRef, useState } from 'react'
import * as api from '../lib/api'
import { formatDateTime, parseTiered } from '../lib/format'
import Icon from './Icon'
import { ConfirmDialog } from './ui'

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

export default function ChatPanel({ role, patientId = null, patientName = '', patientRisk = null }) {
  const [thread, setThread] = useState(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [waiting, setWaiting] = useState(false)
  const [error, setError] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const scrollRef = useRef(null)

  async function openThread(id) {
    setThread(await api.getChatThread(id))
  }

  // Keep the newest message in view: fires on load, on the optimistic send
  // and when the bot reply lands.
  const messageCount = thread?.messages?.length ?? 0
  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messageCount, waiting])

  function fail(err) {
    setError(err?.message || 'Errore di rete')
  }

  async function loadMyThread() {
    const list = await api.getChatThreads()
    if (list.length) await openThread(list[0].id)
    else setThread(null)
  }

  async function openPatientThread() {
    if (!patientId) { setThread(null); return }
    const t = await api.startChatThread({ patient_id: patientId })
    await openThread(t.id)
  }

  useEffect(() => {
    setError('')
    if (role === 'patient') loadMyThread().catch(fail)
    else {
      setThread(null)
      if (patientId) openPatientThread().catch(fail)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role, patientId])

  async function startThread() {
    setBusy(true); setError('')
    try {
      await api.startChatThread({})
      await loadMyThread()
    } catch (err) { fail(err) } finally { setBusy(false) }
  }

  async function send(e) {
    e.preventDefault()
    const content = draft.trim()
    if (!content || !thread || busy) return
    setBusy(true); setWaiting(true); setError('')
    setDraft('')
    // show the message immediately: the local model can take a minute
    const temp = {
      id: `temp-${Date.now()}`,
      sender: role === 'patient' ? 'patient' : 'doctor',
      content,
      created_at: new Date().toISOString(),
    }
    setThread({ ...thread, messages: [...thread.messages, temp] })
    try {
      await api.sendChatMessage(thread.id, content)
      await openThread(thread.id)
    } catch (err) {
      setThread((cur) => cur && { ...cur, messages: cur.messages.filter((m) => m.id !== temp.id) })
      fail(err)
    } finally { setBusy(false); setWaiting(false) }
  }

  async function remove() {
    setError('')
    try {
      await api.deleteThread(thread.id)
      setThread(null)
    } catch (err) { fail(err) }
  }

  const bubbleClass = (sender) =>
    ({ patient: 'bubble-patient', bot: 'bubble-bot', doctor: 'bubble-doctor' }[sender] || 'bubble-bot')

  const canSend = Boolean(thread)
  const placeholder = role === 'patient'
    ? 'Scrivi al coach di prevenzione…'
    : 'Chiedi un’analisi dei dati del paziente…'

  return (
    <div className="chat">
      <div className="chat-head">
        <h3 style={{ textTransform: 'none', letterSpacing: 0 }}>
          {role === 'patient' ? 'Coach di prevenzione' : `Analisi — ${patientName}`}
        </h3>
        {role === 'patient' && (
          <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
            Assistente automatico sui tuoi valori e sul tuo percorso
          </p>
        )}
        {role === 'doctor' && patientRisk && (
          <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
            Rischio <strong>{patientRisk.level}</strong> · {patientRisk.risk_count} fattori attivi,{' '}
            {patientRisk.protective_count} protettivi
          </p>
        )}
      </div>

      <div className="chat-scroll" ref={scrollRef}>
        {!thread && (
          <div className="empty">
            <div className="icon"><Icon name="chat" size={22} /></div>
            <p style={{ maxWidth: 260, margin: '0 auto 10px' }}>
              {role === 'patient'
                ? 'Nessuna conversazione in corso: inizia a scrivere al coach di prevenzione.'
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

        {waiting && (
          <div className="bubble bubble-bot typing" aria-label="L'assistente sta scrivendo…">
            <span className="dot-t" /><span className="dot-t" /><span className="dot-t" />
          </div>
        )}
      </div>

      {error && (
        <div style={{ padding: '6px 12px', fontSize: 12, color: 'var(--danger, #b3261e)', borderTop: '1px solid var(--border)' }}>
          ⚠ {error}
        </div>
      )}

      {thread && (
        <div className="chat-foot">
          <div className="row" style={{ marginBottom: 8, flexWrap: 'wrap' }}>
            <span className="grow" />
            {role === 'patient' && (
              <button className="btn btn-danger btn-sm" onClick={() => setConfirmDelete(true)}>Cancella cronologia</button>
            )}
          </div>

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
          message="Tutti i messaggi verranno eliminati in modo definitivo."
          onConfirm={remove}
          onCancel={() => setConfirmDelete(false)}
        />
      )}
    </div>
  )
}
