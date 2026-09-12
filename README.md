# Health Platform — piattaforma di prevenzione e presa in carico

Piattaforma web per la **prevenzione, il monitoraggio remoto e la presa in carico** dei
lavoratori: anamnesi digitale strutturata, stratificazione del rischio con soglie
documentate in letteratura, algoritmi di triage per la gestione delle chiamate e
assistente conversazionale con supporto umano.

> I dati delle demo (pazienti, datori di lavoro, referti) sono **interamente fittizi**
> e generati da `backend/seed_data.py` per collaudo e presentazione.

## Funzionalità principali

| Area | Cosa fa |
|---|---|
| **Profili paziente relazionali** | Anagrafica, occupazione, diagnosi, terapia, incontri clinici e osservazioni (lab, ambulatorio, domicilio) su PostgreSQL |
| **Percorsi di cura espliciti** | Template di percorso (prevenzione diabete/ipertensione, screening metabolico, follow-up post-chiamata) con tappe datate e azioni dirette: registra misura, prenota visita/esame, programma richiamo. L'appuntamento completato chiude automaticamente la tappa |
| **Anamnesi digitale strutturata** | Catalogo domande personalizzabile (dati, non codice), risposte con provenienza, vista condivisa lavoratore/medico, export interoperabile **FHIR QuestionnaireResponse** |
| **Stratificazione del rischio** | Motore lato server con soglie cliniche e fonti (ESC/ESH, ADA, AMD-SID, ESC/EAS, KDIGO, OMS): un fattore "negativo" (sotto soglia, controllato, cessato ≥ 12 mesi) viene conteggiato come **protettivo**. Regola: ≥ 4 fattori attivi → Alto (percorso specifico + medico del lavoro), 2–3 → Medio, 0–1 → Basso |
| **Monitoraggio remoto** | Piano di misurazioni (frequenza + obiettivo), inserimento misure domiciliari dal portale, ricalcolo automatico del rischio a ogni valore |
| **Grafici di progressione** | Andamento multi-metrica (HbA1c, lipidi, pressione, BMI…) con range di riferimento e punti fuori range evidenziati, sui cruscotti di paziente e medico; delta di progressione nelle tabelle di monitoraggio |
| **Triage delle chiamate** | Protocolli sintomatici (dolore toracico, algie addominali, tosse, cefalea, febbre, lombalgia, sintomi urinari, vertigini, altro) con semaforo **rosso/arancione/verde**: red flag → 118/PS; prenotazione automatica di visita urgente o teleconsulto; follow-up di sicurezza per i quadri verdi |
| **Benessere (strumenti validati)** | WEMWBS-7 (benessere mentale), BPAAT (attività fisica), WSQ (sedentarietà), blocco lavoro (capacità lavorativa, assenze, presentismo, job strain) + indice di engagement sul percorso digitale |
| **Chat con supporto umano** | Coach automatico (**LLM locale** con fallback deterministico offline) e presa in carico da parte dell'operatore, con cronologia persistente e cancellazione a richiesta. Un intercettore deterministico riconosce le frasi di emergenza e bypassa il modello |
| **Sicurezza e privacy** | Sessione via cookie HttpOnly + CSRF (con fallback Bearer per deployment cross-origin), rate limiting, audit trail dell'anamnesi, export dati e cancellazione account (GDPR) |

## Avvio rapido (sviluppo)

Requisiti: Python 3.12+, Node 18+, PostgreSQL in esecuzione, [Ollama](https://ollama.com) per l'assistente.

```bash
# 1. Database (crea ruolo e database se assenti)
psql -h localhost -U postgres -c "CREATE ROLE health WITH LOGIN PASSWORD 'health' CREATEDB;"
psql -h localhost -U postgres -c "CREATE DATABASE health_platform OWNER health;"

# 2. LLM locale (una tantum)
ollama pull mistral-3b        # Ministral 3B Q4_K_M, ~2 GB

# 3. Backend
cd backend
python3 -m venv venv && ./venv/bin/pip install -r requirements-dev.txt
cp .env.example .env          # le impostazioni predefinite puntano già a Ollama locale
./venv/bin/python seed_data.py # schema + dati dimostrativi (fittizi) coerenti

# 4. Frontend
cd ../frontend && npm install

# 5. Tutto insieme
./run-dev.sh                   # backend :5001 · frontend :5173
```

Account dimostrativi (password `HealthPlatform.Demo2026!`): `doctor`, `patient1`…`patient5`.

## Test e migrazioni

```bash
cd backend
./venv/bin/pytest                       # suite di test (motore di rischio, triage, API)
./venv/bin/alembic upgrade head         # schema in ambienti controllati (DB_AUTO_CREATE=0)
```

## Configurazione

Variabili d'ambiente (vedi `backend/.env.example`):

| Variabile | Scopo |
|---|---|
| `DATABASE_URL` | Connessione PostgreSQL (default `postgresql+psycopg://health:health@localhost:5432/health_platform`) |
| `JWT_SECRET_KEY` | Segreto JWT — **impostarne uno robusto in produzione** |
| `LLM_BASE_URL` | Endpoint chat **OpenAI-compatible**. Default: `http://localhost:11434/v1/chat/completions` (Ollama locale). Funzionano anche LM Studio e vLLM |
| `LLM_MODEL` | Modello locale (default `mistral-3b`) |
| `LLM_API_KEY` | Vuota per l'inferenza locale; impostarla solo per provider hosted |
| `LLM_TIMEOUT` | Timeout per richiesta (i piccoli modelli locali su CPU possono impiegare un minuto) |
| `DB_AUTO_CREATE` | `0` in ambienti gestiti con Alembic |
| `CORS_ORIGINS` | Origin abilitati per il browser (default `http://localhost:5173`) |
| `AUTH_ISSUE_FALLBACK_TOKEN` | `1` (default) emette anche un Bearer token per client che scartano i cookie |

L'inferenza è **locale**: nessuna chiave di servizio, nessun dato clinico inviato a
provider esterni. Se Ollama non risponde, il coach deterministico assume il controllo
e la chat resta utilizzabile.

## Produzione

`docker-compose.yml` avvia PostgreSQL 18 + backend + frontend (build statica servita
da nginx con proxy `/api`). Il backend raggiunge Ollama sull'host tramite
`host.docker.internal`. Il backend espone `GET /api/health` per i check di liveness.
Al primo avvio, popolare il database demo: `docker compose exec backend python seed_data.py`.

### Deployment pubblico (GitHub Pages + tunnel)

Il frontend è una SPA statica e può essere pubblicato su **GitHub Pages**
(`.github/workflows/pages.yml`): l'URL dell'API si imposta a deployment-time in
`frontend/public/config.js` (vedi `config.example.js`) puntandolo al tunnel pubblico
che espone il backend di questa macchina (es. `cloudflared tunnel --url http://localhost:5001`).
L'LLM resta in esecuzione locale: le chat viaggiano fino a questo Mac via tunnel e il
modello risponde da Ollama.

## Architettura

```
backend/
├── app.py                    # factory Flask + blueprints
├── config.py                 # configurazione da ambiente
├── models.py                 # modelli relazionali (SQLAlchemy 2.0)
├── api/                      # auth, patients, anamnesis, care, pathways, wellbeing, triage, chat, doctor
├── services/
│   ├── risk_engine.py        # catalogo fattori + soglie + fonti + stratificazione
│   ├── pathways.py           # template percorsi + iscrizione + serializzazione
│   ├── triage_protocols.py   # protocolli sintomatici (semaforo)
│   ├── chat_safety.py        # intercettore emergenze (bypassa l'LLM)
│   ├── wellbeing.py          # punteggi questionari validati + engagement
│   ├── anamnesis.py          # catalogo domande + export FHIR
│   └── llm.py                # endpoint OpenAI-compatible (Ollama locale) + fallback offline
├── migrations/               # Alembic
└── tests/                    # pytest (59 test)
frontend/                     # React 18 + Vite + react-router + chart.js
└── src/
    ├── views/                # Login, patient/ (portale), doctor/ (console)
    ├── components/           # ChatPanel, TrendChart, DeltaLine, pathway cards, design system
    ├── lib/                  # client API, format helpers, data-fetching hook
    └── styles/global.css     # design system (token + componenti)
```
