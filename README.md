# Piattaforma Salute

Piattaforma sanitaria interattiva per la gestione di malattie croniche. Pazienti e dottori possono interagire tramite un'interfaccia in italiano con un assistente AI integrato.

## Caratteristiche

- **Gestione Pazienti:** Dashboard pazienti con profilo, esami recenti, storia visite
- **Gestione Dottori:** Dashboard dottori con lista pazienti, dettagli completi, analisi AI
- **Chatbot AI:** Assistente sanitario per pazienti, assistente medico per dottori
- **Privacy:** Chat cancellata on logout, dati pazienti protetti
- **Italiano:** Interfaccia completamente in italiano
- **Locale:** Database SQLite, nessuna dipendenza cloud esterne

## Tecnologia

- **Backend:** Python 3.9+, Flask, SQLAlchemy
- **Frontend:** Vue.js 3, Vite, Tailwind CSS, Pinia
- **Database:** SQLite locale

## Prerequisiti

### Backend
- Python 3.9+
- pip

### Frontend
- Node.js 16+
- npm

## Installazione

### Clone il repository
```bash
cd ~/GitHub/health-platform
```

### Setup Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Setup Frontend
```bash
cd frontend
npm install
```

## Avvio

### Opzione 1: Entrambi i server (raccomandato)
```bash
# Terminale 1: Backend
cd backend
source venv/bin/activate
python app.py

# Terminale 2: Frontend
cd frontend
npm run dev
```

### Accesso
- Frontend: http://localhost:5173
- Backend API: http://localhost:5000

## Credenziali Demo

**Dottore:**
- Username: `doctor`
- Password: `FEEMsalute2026!`

**Pazienti:**
- Usernames: `patient1`, `patient2`, `patient3`, `patient4`, `patient5`
- Password: `FEEMsalute2026!`

## Dati Demo

Il database include:
- 1 dottore (Dr. Marco Bianchi)
- 5 pazienti con condizioni croniche (diabete, ipertensione)
- ~30 risultati laboratorio per paziente (ultimi 6 mesi)
- ~6 visite per paziente (ultimi 6 mesi)

## Struttura API

- `POST /api/login` - Login
- `POST /api/logout` - Logout + pulizia chat
- `GET /api/me` - Info utente corrente
- `GET /api/patient/:id` - Profilo paziente
- `GET /api/patient/:id/exams` - Esami recenti
- `GET /api/patient/:id/visits` - Visite
- `GET /api/patient/:id/history` - Storia completa
- `GET /api/doctor/patients` - Lista pazienti dottore
- `POST /api/chat/start` - Inizia chat
- `POST /api/chat/message` - Messaggio chatbot
- `DELETE /api/chat/session` - Cancella sessione

## Privacy

- Tutti i messaggi chat vengono cancellati quando l'utente fa logout
- I dottori possono vedere solo i loro pazienti assegnati
- Password hashate con bcrypt
- Token JWT con scadenza 24 ore

## Sviluppo

### Backend
```bash
cd backend
source venv/bin/activate
python app.py
```

### Frontend
```bash
cd frontend
npm run dev
```

### Popolare database
```bash
cd backend
source venv/bin/activate
python seed_data.py
```

## TODO

- [ ] Integrazione LLM reale (Mistral 1B) - vedi CLAUDE.md
- [ ] Rate limiting per produzione
- [ ] Test automatizzati
- [ ] HTTPS per produzione
