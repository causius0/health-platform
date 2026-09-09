# Health Platform — note di architettura

Piattaforma Flask (API) + React 18 (SPA) su PostgreSQL per prevenzione e presa in
carico dei lavoratori. Documentazione utente in `README.md`; diario delle
iterazioni in `PROGRESS.md`.

## Principi

1. **La verità clinica vive nel backend** (`services/risk_engine.py`,
   `services/triage_protocols.py`): il frontend mostra, non calcola.
2. **Soglie e fonti insieme**: ogni soglia del motore di rischio porta il
   riferimento di letteratura visualizzato nell'interfaccia.
3. **Cataloghi come dati**: le domande anamnestiche sono righe di database
   (`anamnesis_questions`); i flag `risk`/`protective` delle opzioni alimentano
   il motore via `services/anamnesis.load_answer_meta()`.
4. **Segreti da ambiente**: nessuna chiave nel codice (vedi `backend/.env.example`).

## Flussi chiave

- **Nuova misurazione** (`POST /patients/<id>/observations`) → ricalcolo rischio →
  nuova `risk_assessments` persistita (audit).
- **Risposta anamnestica** (`PUT /patients/<id>/anamnesis`) → refresh meta opzioni →
  ricalcolo rischio.
- **Triage** (`POST /triage/assessments`) → semaforo + disposition → se arancione
  crea `appointments` (visita urgente/teleconsulto), se verde crea `follow_ups`
  di sicurezza entro 3 giorni.
- **Chat** (`api/chat.py`): thread `coach` (bot → waiting_operator → with_operator →
  bot) e thread `clinical` (medico ↔ assistente su un paziente). Senza
  `OPENROUTER_API_KEY` il bot risponde con il fallback deterministico che usa
  comunque stratificazione e fattori reali del paziente.

## Convenzioni

- Test: `cd backend && ./venv/bin/pytest` (database dedicato
  `health_platform_test`, creato automaticamente).
- Sviluppo: `./run-dev.sh` (backend :5001, frontend :5173 con proxy /api).
- Seed: `./venv/bin/python seed_data.py` — distruttivo, ricrea i dati demo.
- UI in italiano; design system in `frontend/src/style.css` (classi semantiche,
  senza utility framework).
