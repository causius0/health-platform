# HANDOFF — Health Platform: stato, miglioramenti implementati e lavoro rimanente

> Documento di consegna aggiornato all'8 settembre 2026, dopo l'iterazione che ha
> implementato le azioni della sezione §3 (tutti i bug), la maggior parte della §4
> (roadmap) e della §5 (qualità/sicurezza) della versione precedente di questo
> documento. Ciò che resta è elencato in §R.

## Stato della piattaforma

- **Frontend React 18** (Vite, react-router, chart.js) con percorsi di cura espliciti.
- **Backend Flask** su PostgreSQL con cookie HttpOnly + CSRF, rate limiting,
  audit trail, GDPR (export/anonimizzazione) e job di manutenzione percorsi.
- **Verifica**: 46 test pytest · 9 test Vitest · ESLint pulito · build di produzione OK ·
  smoke test browser sui flussi principali (login cookie, cartella, percorsi con
  prenotazione/auto-completamento, triage rosso/arancione/verde, chat con presa in
  carico, report aziende).

## Implementato in questa iterazione

| Area | Cosa |
|------|------|
| Autenticazione | Sessione via cookie HttpOnly + CSRF double-submit; nessun token in localStorage; rate limiting su login e chat |
| Percorsi | Tappe `misurazione` con metrica collegata: "Registra" precompila la metrica e chiude la tappa; chi prenota la visita chiude la tappa al completamento dell'appuntamento |
| Terapia | Tabella relazionale `patient_medications` con CRUD per l'operatore e vista read-only per il lavoratore |
| Incontri | L'operatore documenta gli incontri (anche esito visita → `Encounter` automatico) |
| Laboratorio | Inserimento referti (`source=lab`) dall'interfaccia dell'operatore |
| Triage | Boze salvabili/riprendibili per chiamate sospese; risk level del lavoratore mostrato nella console |
| Notifiche | Centro promemoria derivato (tappe scadute/imminenti, appuntamenti, richiami) con badge nella navigazione |
| Report | Aggregazione per datore di lavoro: avanzamento percorsi, tappe in ritardo, fattori di rischio medi, giorni di assenza |
| Audit | Storico di ogni modifica anamnestica (`anamnesis_answer_history`) |
| GDPR | Export completo dei dati e cancellazione account con anonimizzazione |
| Job | `backend/jobs.py` (cron giornaliero): follow-up di sicurezza per tappe scadute, idempotente |
| Qualità | ESLint (9) con regole hooks + `no-undef` (avrebbe intercettato il bug del crash), Vitest + Testing Library, CI GitHub Actions (pytest + lint + test + build), migrazione Alembic rigenerata |
| Branding | Rimossi i riferimenti all'azienda dal codice e dai documenti; password demo ruotata (`HealthPlatform.Demo2026!`) |

## §R — Lavoro rimanente (settembre 2026)

Implementato nell'ultima iterazione (vedi tabella sopra): check-in sintomi giornaliero
con semaforo (COVIDApp), suggerimenti percorsi, MARS-5 usabilità, library educativa,
richiesta di laboratorio stampabile, trend indicatori benessere, notifiche operatore
(`for_doctor` riparato e collegato alla dashboard), rate-limit storage condiviso in
produzione, flag token fallback.

Rimanente, in ordine di priorità:

1. **Revoca della chiave OpenRouter** storica (esterno: pannello del provider).
2. **Invii reali di notifiche** (email/push): centro promemoria in-app + `jobs.py` sono
   il punto di aggancio; serve provider SMTP/push e preferenze utente.
3. **Streaming LLM** (SSE) e modello locale per il fallback offline.
4. **Test E2E browser** (Playwright): il collaudo end-to-end è ancora manuale.
5. **i18n**: stringhe in italiano hard-coded; estrarre solo se servirà l'inglese.
6. **Calendar drag&drop** per l'agenda ambulatorio (l'agenda per giorno esiste già).
7. **Verifica del modulo sintomi su browser reale**: l'ultima sessione di collaudo
   browser è stata interrotta dal degrado dell'ambiente di test incorporato; la catena
   API è verificata via pytest e curl, il rendering del form usa gli stessi pattern
   già collaudati (chip-select + submit).

## LLM locale (Ollama / Hermes)

Il chatbox gira su qualunque endpoint OpenAI-compatible. Setup locale collaudato
su questo Mac (8 GB RAM): Ollama via brew (servizio attivo) con **Ministral 3B
Instruct 2512 Q4_K_M**, GGUF ufficiale di Mistral, importato come `mistral-3b`
(~2 GB su disco, ~2.5 GB RAM in uso). Il backend legge `backend/.env`:
`OPENROUTER_URL=http://localhost:11434/v1/chat/completions`,
`OPENROUTER_MODEL=mistral-3b`, chiave vuota, `LLM_TIMEOUT=120`. Collaudato
end-to-end sia sul chat lavoratore sia sull'analisi clinica del medico.
Prompt di sistema completo e payload per Hermes: `docs/chat-prompt-hermes.md`.
Il fallback deterministico resta attivo se il modello non risponde.

## Note operative

- Avvio: `./run-dev.sh` (backend :5001, frontend :5173). Job percorsi: `python jobs.py`
  da cron giornaliero.
- Test: `cd backend && pytest -q` (DB dedicato `health_platform_test`) ·
  `cd frontend && npm run test && npm run lint`.
- Schema DB: da qui in poi solo migrazioni Alembic incrementali; **non rigenerare**
  la revisione iniziale (include il seed dei cataloghi anamnesi/percorsi).
- Il banner rosso in basso (`FatalBoundary` in `App.jsx`) segnala errori fatali del
  frontend: se compare, è un bug da correggere, non decorazione.

Screenshot dei collaudi: `/tmp/gui-shots/` (sessioni del 7–8 settembre).
