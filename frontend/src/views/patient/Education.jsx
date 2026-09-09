/** Evidence-based education library (HAHA2022 "Education" menu). */
import { useMemo, useState } from 'react'
import * as api from '../../lib/api'
import { Empty, Loading } from '../../components/ui'
import { useAsync } from '../../lib/useAsync'

export default function Education() {
  const articles = useAsync(() => api.getEducationArticles(), [])
  const [area, setArea] = useState('tutte')
  const [openId, setOpenId] = useState(null)
  const [detail, setDetail] = useState(null)

  const areas = useMemo(
    () => ['tutte', ...new Set((articles.data || []).map((a) => a.area))],
    [articles.data],
  )
  const visible = (articles.data || []).filter((a) => area === 'tutte' || a.area === area)

  async function toggle(id) {
    if (openId === id) { setOpenId(null); setDetail(null); return }
    setOpenId(id)
    setDetail(await api.getEducationArticle(id))
  }

  return (
    <div className="section">
      <p className="muted" style={{ fontSize: 12.5, margin: 0 }}>
        Contenuti educativi sintetici e basati sull'evidenza, scelti per i temi del tuo percorso.
      </p>

      <div className="row wrap" style={{ gap: 6 }}>
        {areas.map((a) => (
          <button key={a} className="chip"
                  style={area === a ? { borderColor: 'var(--brand)', color: 'var(--brand-strong)', fontWeight: 650 } : undefined}
                  onClick={() => setArea(a)}>
            {a}
          </button>
        ))}
      </div>

      {articles.loading && <Loading />}
      {visible.length === 0 && !articles.loading && <Empty icon="book">Nessun contenuto per questa area.</Empty>}

      <div className="stack" style={{ gap: 10 }}>
        {visible.map((a) => (
          <div key={a.id} className="card">
            <div className="card-body">
              <div className="row-between wrap" style={{ gap: 8 }}>
                <div>
                  <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
                    <strong style={{ fontSize: 13.5 }}>{a.title}</strong>
                    <span className="badge badge-neutral">{a.area}</span>
                    <span className="muted" style={{ fontSize: 11.5 }}>{a.read_minutes} min di lettura</span>
                  </div>
                  <p className="muted" style={{ fontSize: 12.5, marginTop: 3 }}>{a.summary}</p>
                </div>
                <button className="btn btn-secondary btn-sm" onClick={() => toggle(a.id)}>
                  {openId === a.id ? 'Chiudi' : 'Leggi'}
                </button>
              </div>

              {openId === a.id && (
                <div style={{ marginTop: 12, borderTop: '1px dashed var(--border)', paddingTop: 12 }}>
                  {detail ? (
                    <>
                      {detail.body.map((par, i) => (
                        <p key={i} style={{ fontSize: 13, marginBottom: 8 }}>{par}</p>
                      ))}
                      <div className="panel-flat accent-ok" style={{ marginTop: 10 }}>
                        <strong style={{ fontSize: 12 }}>Da provare questa settimana</strong>
                        <ul style={{ margin: '5px 0 0', paddingLeft: 18, fontSize: 12.5 }}>
                          {detail.tips.map((t, i) => <li key={i}>{t}</li>)}
                        </ul>
                      </div>
                      <p className="reference-note" style={{ marginTop: 8 }}>Fonte: {detail.source}</p>
                    </>
                  ) : (
                    <div className="row" style={{ padding: 8 }}><span className="spinner" /></div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
