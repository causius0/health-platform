# Health Platform — piattaforma di prevenzione e presa in carico

Piattaforma web per la **prevenzione, il monitoraggio remoto e la presa in carico** dei
lavoratori: anamnesi digitale strutturata, stratificazione del rischio con soglie
documentate in letteratura, algoritmi di triage per la gestione delle chiamate e
assistente conversazionale con supporto umano.

## Funzionalità principali

| Area | Cosa fa |
|---|---|
| **Profili paziente relazionali** | Anagrafica, occupazione, diagnosi, terapia, incontri clinici e osservazioni (lab, ambulatorio, domicilio) su PostgreSQL |
| **Percorsi di cura espliciti** | Template di percorso (prevenzione diabete/ipertensione, screening metabolico, follow-up post-chiamata) con tappe datate e azioni dirette: registra misura, prenota visita/esame, programma richiamo. L'appuntamento completato chiude automaticamente la tappa |
| **Anamnesi digitale strutturata** | Catalogo domande personalizzabile (dati, non codice), risposte con provenienza, vista condivisa lavoratore/medico, export interoperabile **FHIR QuestionnaireResponse** |
| **Stratificazione del rischio** | Motore lato server con soglie cliniche e fonti (ESC/ESH, ADA, AMD-SID, ESC/EAS, KDIGO, OMS): un fattore "negativo" (sotto soglia, controllato, cessato ≥ 12 mesi) viene conteggiato come **protettivo**. Regola: ≥ 4 fattori attivi → Alto (percorso specifico + medico del lavoro), 2–3 → Medio, 0–1 → Basso |
| **Monitoraggio remoto** | Piano di misurazioni (frequenza + obiettivo), inserimento misure domiciliari dal portale, ricalcolo automatico del rischio a ogni valore |
| **Triage delle chiamate** | Protocolli sintomatici (dolore toracico, algie addominali, tosse, cefalea, febbre, lombalgia, sintomi urinari, vertigini, altro) con semaforo **rosso/arancione/verde**: red flag → 118/PS; prenotazione automatica di visita urgente o teleconsulto; follow-up di sicurezza per i quadri verdi |
| **Percorso di cura** | Obiettivi settimanali con check-in, follow-up programmati, visite e teleconsulti con stati |
| **Benessere (strumenti validati)** | WEMWBS-7 (benessere mentale), BPAAT (attività fisica), WSQ (sedentarietà), blocco lavoro (capacità lavorativa, assenze, presentismo, job strain) + indice di engagement sul percorso digitale |
| **Chat con supporto umano** | Coach automatico (LLM con fallback deterministico offline) e presa in carico da parte dell'operatore, con cronologia persistente e cancellazione a richiesta |
| **Sicurezza e privacy** | Sessione via cookie HttpOnly + CSRF, rate limiting, audit trail dell'anamnesi, export dati e cancellazione account (GDPR) |

## Avvio rapido (sviluppo)

Requisiti: Python 3.12+, Node 18+, PostgreSQL in esecuzione.

```bash
# 1. Database (crea ruolo e database se assenti)
psql -h localhost -U postgres -c "CREATE ROLE health WITH LOGIN PASSWORD 'health' CREATEDB;"
psql -h localhost -U postgres -c "CREATE DATABASE health_platform OWNER health;"

# 2. Backend
cd backend
python3 -m venv venv && ./venv/bin/pip install -r requirements-dev.txt
cp .env.example .env           # opzionale: imposta DATABASE_URL / OPENROUTER_API_KEY
./venv/bin/python seed_data.py # schema + dati dimostrativi coerenti

# 3. Frontend
cd ../frontend && npm install

# 4. Tutto insieme
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
| `OPENROUTER_API_KEY` | Chiave LLM per la chat; senza chiave l'assistente usa il fallback deterministico |
| `DB_AUTO_CREATE` | `0` in ambienti gestiti con Alembic |

> Nota: le chiavi non vanno mai committate. La vecchia chiave OpenRouter presente
> nel codice è stata rimossa e va revocata dal pannello provider.

## Produzione

`docker-compose.yml` avvia PostgreSQL 18 + backend + frontend (build statica servita
da nginx con proxy `/api`). Il backend espone `GET /api/health` per i check di
liveness.

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
│   ├── wellbeing.py          # punteggi questionari validati + engagement
│   ├── anamnesis.py          # catalogo domande + export FHIR
│   └── llm.py                # OpenRouter + fallback offline
├── migrations/               # Alembic
└── tests/                    # pytest (38 test)
frontend/                     # React 18 + Vite + react-router + chart.js
└── src/
    ├── views/                # Login, patient/ (portale), doctor/ (console)
    ├── components/           # ChatPanel, TrendChart, pathway cards, design system
    └── styles/global.css     # design system (token + componenti)
```
