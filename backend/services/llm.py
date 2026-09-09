"""Chat assistant: OpenRouter LLM with a deterministic clinical fallback.

The API key comes from the environment (never committed). Without a key — or
on any provider error — the assistant answers with a rule-based coach that
still uses the patient's real stratification, so the product degrades
gracefully instead of breaking.
"""
import re

import requests
from flask import current_app

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


def sanitize_user_message(text: str) -> str:
    """Treat user input as data, not instructions: collapse it, cap the length
    and strip lines that try to impersonate system directives."""
    lines = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if lowered.startswith(("system:", "istruzioni:", "instruction:", "assistant:", " sei un", "ignore all")):
            continue
        lines.append(stripped)
    clean = "\n".join(lines)[:2000]
    return clean or "(messaggio vuoto)"


def get_llm_response(user_message: str, context: str, role: str, hints: dict | None = None) -> str:
    hints = hints or {}
    system_prompt = PATIENT_SYSTEM_PROMPT if role != "doctor" else DOCTOR_SYSTEM_PROMPT
    user_message = sanitize_user_message(user_message)
    api_key = current_app.config["OPENROUTER_API_KEY"]
    headers = {"Content-Type": "application/json", "X-Title": "Health Platform"}
    if api_key:  # hosted providers require the key; local Ollama does not
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        response = requests.post(
            current_app.config["OPENROUTER_URL"],
            headers=headers,
            json={
                "model": current_app.config["OPENROUTER_MODEL"],
                "messages": [
                    {"role": "system", "content": f"{system_prompt}\n\n{context}"},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.4,
                "max_tokens": 480,
            },
            timeout=current_app.config["LLM_TIMEOUT"],
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return clean_response(content)
    except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
        current_app.logger.warning("LLM unavailable, using rule-based fallback: %s", exc)
        return rule_based_response(user_message, role, hints)


def clean_response(text: str) -> str:
    text = re.sub(r"[*_#`]+", "", text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines[:10])


# ---------------------------------------------------------------------------
# Deterministic fallback (offline mode)
# ---------------------------------------------------------------------------
def rule_based_response(user_message: str, role: str, hints: dict) -> str:
    msg = user_message.lower()
    first = hints.get("first_name", "")
    risks = hints.get("risks", [])
    protectives = hints.get("protectives", [])
    level = hints.get("level", "basso")

    risk_txt = f"Il tuo profilo attuale mostra: {', '.join(risks[:2])}. " if risks else ""
    prot_txt = f"Punti di forza da mantenere: {', '.join(protectives[:2])}. " if protectives else ""

    if role == "doctor":
        return clean_response(
            "ANALISI DEI DATI: assistente offline — consultare i pannelli di stratificazione e monitoraggio nel workspace. "
            f"Livello di rischio del paziente selezionato: {level.upper()}. "
            + (f"Fattori attivi: {', '.join(risks[:3])}. " if risks else "")
            + "AREE DI ATTENZIONE: verificare trend e aderenza nel tab Monitoraggio. "
            + "SUGGERIMENTI CLINICI: per richieste complesse riconnettere il servizio LLM."
        )

    if any(w in msg for w in ("ciao", "buongiorno", "buonasera", "salve")):
        return clean_response(
            f"Ciao {first}! Sono il tuo coach di prevenzione. "
            + prot_txt
            + "Come posso aiutarti oggi? Posso spiegarti i tuoi valori, darti un obiettivo settimanale o aiutarti a capire i prossimi passi."
        )

    if any(w in msg for w in ("farmaco", "farmaci", "medicina", "pillola", "dos")):
        return clean_response(
            "INFORMAZIONE GENERALE: le domande su farmaci e dosi spettano al tuo medico, che conosce la tua storia clinica.\n"
            "CONSIGLIO PREVENTIVO PERSONALIZZATO: segna su un foglio le domande per il prossimo controllo: sarà più completo.\n"
            "INDICAZIONE CLINICA: Non necessaria in questo caso."
        )

    if any(w in msg for w in ("hba1c", "glicemia", "zucchero", "diabete")):
        return clean_response(
            "INFORMAZIONE GENERALE: l'HbA1c riflette la glicemia media degli ultimi 3 mesi; l'obiettivo per chi ha il diabete è di solito sotto il 7%.\n"
            f"{risk_txt}{prot_txt}"
            "CONSIGLIO PREVENTIVO PERSONALIZZATO: questa settimana, sostituisci una bevanda zuccherata al giorno con acqua o tè non zuccherato.\n"
            "INDICAZIONE CLINICA: porta i valori al prossimo controllo come concordato."
        )

    if any(w in msg for w in ("pressione", "tensione", "cuore")):
        return clean_response(
            "INFORMAZIONE GENERALE: la pressione si considera sotto controllo sotto 130/80 mmHg; misurarla sempre a riposo, seduti, due volte.\n"
            f"{risk_txt}{prot_txt}"
            "CONSIGLIO PREVENTIVO PERSONALIZZATO: questa settimana misura la pressione 3 mattine su 7 e annota i valori nell'area Monitoraggio.\n"
            "INDICAZIONE CLINICA: Non necessaria in questo caso."
        )

    if any(w in msg for w in ("cammin", "sport", "attività", "esercizio", "palestra")):
        return clean_response(
            "INFORMAZIONE GENERALE: l'OMS raccomanda almeno 150 minuti a settimana di attività moderata: circa 30 minuti per 5 giorni.\n"
            f"{prot_txt}"
            "CONSIGLIO PREVENTIVO PERSONALIZZATO: se resti fermo molto, questa settimana prova due interruzioni ogni ora: 2–3 minuti in piedi o a camminare.\n"
            "INDICAZIONE CLINICA: Non necessaria in questo caso."
        )

    if any(w in msg for w in ("sonno", "dormo", "insonnia", "stanco")):
        return clean_response(
            "INFORMAZIONE GENERALE: dormire 7–9 ore aiuta il controllo di pressione e glicemia; la regolarità conta più della quantità.\n"
            "CONSIGLIO PREVENTIVO PERSONALIZZATO: questa settimana fissa un orario di spegnimento luci costante (± 30 minuti) per 5 notti.\n"
            "INDICAZIONE CLINICA: Non necessaria in questo caso."
        )

    if any(w in msg for w in ("rischio", "stratificaz", "punteggio")):
        return clean_response(
            f"INFORMAZIONE GENERALE: la stratificazione conta i fattori di rischio attivi: {level} "
            f"({len(risks)} attivi su soglie cliniche documentate).\n"
            f"{risk_txt}{prot_txt}"
            "CONSIGLIO PREVENTIVO PERSONALIZZATO: concentrati su un solo fattore alla volta: il primo dell'elenco.\n"
            "INDICAZIONE CLINICA: Non necessaria in questo caso."
        )

    if any(w in msg for w in ("visita", "prenota", "appuntamento", "controllo")):
        return clean_response(
            "INFORMAZIONE GENERALE: puoi vedere i prossimi appuntamenti nella sezione Percorso; gli operatori possono prenotare visite e teleconsulti per te.\n"
            "CONSIGLIO PREVENTIVO PERSONALIZZATO: se ti serve una visita, scrivi qui: il messaggio arriva all'operatore sanitario.\n"
            "INDICAZIONE CLINICA: Non necessaria in questo caso."
        )

    # Generic, still personalized
    return clean_response(
        "INFORMAZIONE GENERALE: il tuo percorso si basa su misurazioni reali e soglie cliniche documentate: ogni piccolo obiettivo mantenuto sposta i valori nella direzione giusta.\n"
        f"{risk_txt}{prot_txt}"
        "CONSIGLIO PREVENTIVO PERSONALIZZATO: scegli una sola azione per questa settimana e registra i check-in: l'aderenza è il predittore principale del miglioramento.\n"
        "INDICAZIONE CLINICA: Non necessaria in questo caso."
    )
