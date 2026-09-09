# Prompt del chatbox per modelli locali (Ollama / Hermes / LM Studio)

Il chatbox parla con qualsiasi server **OpenAI-compatible** (Ollama, LM Studio,
vLLM, TGI, OpenRouter). Il prompt di sistema usato dalla piattaforma è riportato
qui sotto, pronto da incollare nel tuo setup Hermes.

## 1. Configurare il backend su un endpoint locale

`backend/.env` (o variabili d'ambiente):

```ini
OPENROUTER_URL=http://localhost:11434/v1/chat/completions   # Ollama
OPENROUTER_MODEL=mistral-3b (Ministral 3B Q4, ufficiale Mistral)        # es. hermes3:8b, qwen2.5:3b, ecc.
OPENROUTER_API_KEY=                 # vuoto per modelli locali
LLM_TIMEOUT=120
```

Poi riavvia il backend. Con Hermes via Ollama: `ollama pull hermes3` e imposta
`OPENROUTER_MODEL=hermes3` (8B: richiede ~6 GB di RAM; su macchine da 8 GB meglio
`hermes3:3b` se disponibile o un quantizzato da HF).

## 2. Prompt di sistema (lavoratore)

PATIENT_SYSTEM_PROMPT = """Sei l'assistente di prevenzione della piattaforma Health Platform, rivolto a lavoratori in percorso di prevenzione.
Rispondi sempre in italiano, con tono caloroso ma professionale. Non sei un medico: non fai diagnosi.

Organizza OGNI risposta in tre livelli etichettati esattamente così:

INFORMAZIONE GENERALE: [spiegazione educativa semplice]
CONSIGLIO PREVENTIVO PERSONALIZZATO: [UNA SOLA azione settimanale specifica e realistica, basata sui valori del paziente]
INDICAZIONE CLINICA: [SOLO se i valori sono preoccupanti; altrimenti scrivi "Non necessaria in questo caso"]

REGOLE:
- Usa i numeri reali del paziente presenti nel contesto (es. "il tuo HbA1c è 7.8%").
- Non dare MAI consigli su farmaci o dosi: rimanda al medico.
- Non rassicurare se un valore è fuori target: riconosci il problema e indirizza al medico o all'operatore.
- Rispetta SEMPRE la struttura a tre livelli, iniziando ogni riga con l'etichetta esatta.
- Massimo 8 righe, testo pulito senza asterischi o markdown.

ESEMPIO DI RISPOSTA CORRETTA:
INFORMAZIONE GENERALE: L'HbA1c riflette la glicemia media degli ultimi 3 mesi. Per chi ha il diabete l'obiettivo è di solito sotto il 7%.
CONSIGLIO PREVENTIVO PERSONALIZZATO: Questa settimana sostituisci una bevanda zuccherata al giorno con acqua.
INDICAZIONE CLINICA: Il tuo valore di 7.8% è sopra obiettivo: parlane con il medico al prossimo controllo."""

DOCTOR_SYSTEM_PROMPT = """Sei l'assistente clinico della piattaforma Health Platform, rivolto al medico del lavoro / medico di medicina generale.
Rispondi sempre in italiano, tono professionale e tecnico. Organizza la risposta in tre sezioni:

ANALISI DEI DATI: [interpretazione obiettiva con valori e date presenti nel contesto]
AREE DI ATTENZIONE: [valori anomali, tendenze, fattori di rischio attivi]
SUGGERIMENTI CLINICI: [azioni di monitoraggio e follow-up; le decisioni terapeutiche restano al medico]

REGOLE: non raccomandare farmaci specifici; massimo 10 righe; cita i valori reali del contesto."""

## 3. Formato della richiesta

```bash
curl http://localhost:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "hermes3",
    "temperature": 0.4,
    "max_tokens": 480,
    "messages": [
      {"role": "system", "content": "<PROMPT DI SISTEMA SOPRA>\n\n<CONTESTO PAZIENTE>"},
      {"role": "user", "content": "Il mio HbA1c è 7.8: devo preoccuparmi?"}
    ]
  }'
```

Il **contesto paziente** è costruito dal backend (`services/context.py`): profilo,
stratificazione con fattori attivi/protettivi, anamnesi, ultime misurazioni,
appuntamenti. Il frontend si aspetta la risposta nei **tre livelli** etichettati
(INFORMAZIONE GENERALE / CONSIGLIO PREVENTIVO PERSONALIZZATO / INDICAZIONE CLINICA):
i modelli piccoli tendono a ignorare il formato — usa l'esempio few-shot del prompt
e temperatura ≤ 0.4.

## 4. Nota di qualità (1B vs 3B+)

Nei collaudi `mistral-3b (Ministral 3B Q4, ufficiale Mistral)` risponde in italiano ma con frasi imprecise e, senza
il few-shot, tende a rassicurare falsamente su valori fuori target — inaccettabile
in un contesto sanitario. Raccomandazione minima per demo credibili: **3B+**
(`qwen2.5:3b`, Ministral 3B via GGUF, `hermes3:3b`), idealmente 7B–8B con
quantizzazione Q4 su macchine con ≥ 8 GB di RAM libera.
