# Health Platform

Un piattaforma sanitaria interattiva per l'interazione tra pazienti e dottori.
Piattaforma di gestione delle malattie croniche dove i pazienti possono monitorare la loro salute e interagire con un coach sanitario AI, mentre i dottori possono monitorare i dati dei pazienti e fare domande sui pazienti tramite un assistente AI.

## Tecnologia

- **Backend:** Python con Flask, SQLAlchemy, SQLite
- **Frontend:** Vue.js 3 con Vite, Tailwind CSS, Pinia
- **Database:** SQLite locale
- **Autenticazione:** Token JWT con cookie HttpOnly (scadenza 24 ore)
- **AI:** Chatbot con modello locale (placeholder per integrazione Mistral)

## Struttura del Progetto

```
health-platform/
├── backend/
│   ├── app.py                  # App Flask con tutti gli endpoint API
│   ├── models.py               # Modelli SQLAlchemy (User, Patient, Doctor, LabResult, Visit, ChatSession, ChatMessage)
│   ├── auth.py                 # Gestore autenticazione
│   ├── chatbot.py              # Integrazione AI + costruzione contesto
│   ├── seed_data.py            # Dati iniziali (5 pazienti + 1 dottore)
│   ├── requirements.txt         # Dipendenze Python
│   └── database.db             # Database SQLite (generato)
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── main.js             # Inizializzazione app Vue
│   │   ├── App.vue             # Componente root
│   │   ├── style.css           # Stili globali con Tailwind
│   │   ├── components/
│   │   │   ├── LoginForm.vue         # Pagina login
│   │   │   ├── PatientDashboard.vue  # Vista paziente
│   │   │   ├── DoctorDashboard.vue   # Vista dottore
│   │   │   ├── PatientCard.vue       # Riepilogo paziente
│   │   │   ├── PatientDetailModal.vue # Dettagli paziente
│   │   │   └── ChatInterface.vue      # Chat (comune entrambe)
│   │   ├── stores/
│   │   │   └── auth.js            # Store autenticazione (Pinia)
│   │   └── utils/
│   │       ├── api.js             # Client API con auth headers
│   │       └── formatters.js      # Utilità formatting italiano
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
├── CLAUDE.md                    # Questo file
└── README.md                    # Istruzioni setup
```

## Endpoint API

### Autenticazione
- `POST /api/login` - Autentica utente, restituisce token JWT
- `POST /api/logout` - Termina sessione e pulisce chat (privacy)
- `GET /api/me` - Ottieni info utente corrente

### Dati Paziente
- `GET /api/patient/:id` - Profilo paziente
- `GET /api/patient/:id/exams` - Esami laboratorio recenti (ultimi 6 mesi)
- `GET /api/patient/:id/visits` - Storia visite
- `GET /api/patient/:id/history` - Storia completa 6 mesi (esami + visite)

### Dottore
- `GET /api/doctor/patients` - Lista tutti i pazienti assegnati

### Chatbot
- `POST /api/chat/start` - Inizia nuova sessione chat
- `POST /api/chat/message` - Invia messaggio, ottieni risposta AI
- `DELETE /api/chat/session` - Termina sessione e pulisce messaggi

## Credenziali Demo

**Dottore:**
- Username: `doctor`
- Password: `FEEMsalute2026!`
- Dr. Marco Bianchi (specializzazione in medicina interna)

**Pazienti:**
- Username: `patient1-5`
- Password: `FEEMsalute2026!`
- Patient 1: Mario Rossi (Diabete tipo 2, 45 anni)
- Patient 2: Laura Bianchi (Ipertensione, 52 anni)
- Patient 3: Giuseppe Verdi (Diabete tipo 2, 38 anni)
- Patient 4: Anna Ferrari (Ipertensione, 48 anni)
- Patient 5: Paolo Costa (Diabete tipo 1, 35 anni)

## Privacy e Sicurezza

- **Chat history:** I messaggi vengono cancellati on logout tramite query DELETE per proteggere la privacy
- **Patient data:** Accessibile solo al dottore assegnato (per demo: tutti a Dr. Bianchi)
- **Password hashing:** bcrypt con sale
- **Session management:** Token JWT stateless con scadenza 24 ore
- **SQL injection:** SQLAlchemy con query parametrizzate

## TODO prima del shipping

### Integrazione LLM (CRITICO)

Sostituire `mock_llm_response()` in `backend/chatbot.py` con chiamate reali al modello Mistral.

1. Installare Ollama: `brew install ollama` (Mac) o https://ollama.ai
   OPPURE installare LM Studio: https://lmstudio.ai

2. Scaricare modello Mistral 7B Instruct:
   - Ollama: `ollama pull mistral`
   - LM Studio: Download mistral-7b-instruct-gguf

3. Aggiornare funzione `get_llm_response()`:
   - Impostare variabile ambiente `LLM_ENDPOINT`:
     * Ollama: `http://localhost:11434/api/generate`
     * LM Studio: `http://localhost:1234/v1/chat/completions`
   - Impostare `LLM_MODEL`: `"mistral"` (Ollama) o `"mistral-7b-instruct"` (LM Studio)

4. Testare l'integrazione:
   - Eseguire test di chat in italiano
   - Verificare che il contesto del paziente sia incluso
   - Verificare risposte utili e in italiano

5. Security checklist:
   - Prompt injection: Sanitizzare tutti gli input utente
   - Rate limiting: Aggiungere rate limit per utente
   - Context window: Troncare se >4096 token

## Localizzazione

- Tutta l'interfaccia utente è in italiano
- Formato date: DD/MM/YYYY (es. 27/07/2026)
- Formato numeri: virgola decimale (es. 1,5 invece di 1.5)
- Termini medici: diabete, ipertensione, glicemia, HbA1c, creatinina, ecc.

## Avvio

### Backend
```bash
cd backend
source venv/bin/activate
python seed_data.py  # Popola database
python app.py         # Avvia server Flask (port 5000)
```

### Frontend
```bash
cd frontend
npm install
npm run dev           # Avvia Vite dev server (port 5173)
```

Entrambi i server possono essere avviati con `./run.sh` (quando creato).

## Note Implementative

- **Pulizia chat on logout:** Implementata con DELETE query su chat_sessions e chat_messages quando l'utente fa logout
- **Assegnazione dottore:** Hardcoded nel seed_data - tutti i pazienti assegnati a Dr. Bianchi
- **Tipo visita:** Enum con constraint CHECK per 'controllo', 'urgenza', 'followup' in italiano
- **Rate limiting:** Differito per demo scope, documentato come requisito produzione
