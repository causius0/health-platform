# Diario delle iterazioni

## Iterazione 2 — piattaforma di produzione (settembre 2026)

Rifacimento completo a partire dal feedback del cliente (analisi degli studi del cliente):
- **PostgreSQL relazionale**: profili paziente veri (anagrafica, occupazione, diagnosi),
  osservazioni cliniche unificate (lab/ambulatorio/domicilio), migrazioni Alembic.
- **Anamnesi digitale strutturata**: catalogo domande personalizzabile, risposte con
  provenienza, cartella condivisa lavoratore/medico (fattori di rischio vs punti di
  forza con soglie e fonti), export FHIR. La vecchia box "punti di forza" è stata
  eliminata e ristrutturata.
- **Motore di rischio unificato** (sostituisce alerts.py + logica client-side): soglie
  documentate (ESC/ESH 2018, ADA 2024, AMD-SID, ESC/EAS 2019, KDIGO 2024, OMS 2020,
  Surgeon General 2010), fattore negativo → conteggiato come protettivo, regola
  concordata ≥ 4 fattori → Alto, valutazioni persistite per audit.
- **Triage chiamate**: 9 protocolli sintomatici con semaforo rosso/arancione/verde
  (modello COVIDApp + red flag da triage telefonico), prenotazione automatica di
  visita urgente/teleconsulto, follow-up di sicurezza per i verdi.
- **Indicatori benessere** dai documenti di studio del cliente: WEMWBS-7, BPAAT, WSQ, blocco lavoro
  (WAI, assenze, presentismo WLQ, job strain JCQ) + engagement sul percorso digitale.
- **Chat con supporto umano**: thread persistenti, escalazione a operatore, coda di
  presa in carico nella console medica, fallback offline senza chiave LLM
  (chiave hardcoded rimossa dal codice).
- **Qualità**: app factory + blueprints, 33 test pytest, docker-compose, rimozione
  codice morto (chatbot_broken.py, componenti orfani), fix NameError su obiettivi.

## Iterazione 1 — baseline (giugno 2026)

Demo Flask + Vue3 con SQLite, chatbot OpenRouter e alert lato client.

## Iterazione 3 — test finale e consegna (settembre 2026)

Test black-box completi su React + percorsi: 8 flussi PASS, 1 FAIL
(crash Cartella anamnestica paziente per import mancante). Nessun fix applicato:
tutti i difetti e la roadmap sono documentati in **HANDOFF.md** per il prossimo
sviluppatore.

## Iterazione 4 — implementazione dell'handoff (settembre 2026)

Tutti i bug della §3 e la maggior parte delle azioni §4/§5 dell'handoff precedente
sono implementati: cookie auth + CSRF, rate limiting, audit trail anamnesi, GDPR
(export/anonimizzazione), terapia relazionale con CRUD, documentazione incontri,
inserimento referti, boze triage, centro notifiche, report per azienda, job percorsi,
ESLint + Vitest + CI. Password demo ruotata e riferimenti aziendali rimossi.
Rimanente: revoca chiave OpenRouter, invii email/push, streaming LLM, i18n, test E2E.
