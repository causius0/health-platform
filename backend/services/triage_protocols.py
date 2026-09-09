"""Symptom triage protocols for the operator taking a Health Platform call.

Traffic-light model (verde / arancione / rosso), as implemented in the
workplace remote-monitoring literature the client referenced (COVIDApp,
Int. J. Environ. Res. Public Health 2022: daily symptom reporting classified
into green/orange/red alerts with rapid protocol activation) combined with
standard red-flag screening used in telephone triage.

Each protocol is *data*: questions, red-flag answers (→ rosso), conditional
arancione rules (answer- or context-based), and a default verde disposition
with safety-netting advice. The operator is decision support, not autonomous
diagnosis: every outcome names the recommended action and, where applicable,
books the follow-up (teleconsulto / office visit / emergency call).

Patient context (age, diabetes, current risk level) can raise the tier:
the same symptom in a high-risk worker escalates one step.
"""
from datetime import datetime, timedelta, timezone

# Disposition catalogue -------------------------------------------------------
DISPOSITIONS = {
    "emergenza_118": {
        "label": "Chiamare subito il 118 — emergenza",
        "detail": "Non attendere: il quadro descritto richiede l'attivazione del servizio di emergenza medica.",
        "tier": "rosso",
        "make_appointment": None,
    },
    "pronto_soccorso": {
        "label": "Recarsi in Pronto Soccorso oggi",
        "detail": "Valutazione ospedaliera necessaria nelle prossime ore.",
        "tier": "rosso",
        "make_appointment": None,
    },
    "visita_urgente_24h": {
        "label": "Visita in ambulatorio entro 24 ore",
        "detail": "Il medico valuta il lavoratore in ambulatorio; se il quadro peggiora nel frattempo, seguire le istruzioni di sicurezza.",
        "tier": "arancione",
        "make_appointment": {"kind": "visita_ambulatoriale", "priority": "urgente", "within_hours": 24},
    },
    "visita_48h": {
        "label": "Visita in ambulatorio entro 48 ore",
        "detail": "Prenotazione di una visita ravvicinata per escludere complicanze.",
        "tier": "arancione",
        "make_appointment": {"kind": "visita_ambulatoriale", "priority": "urgente", "within_hours": 48},
    },
    "teleconsulto": {
        "label": "Teleconsulto con l'operatore sanitario",
        "detail": "Contatto in videochiamata/telefono per valutazione approfondita e richiesta eventuale di esami.",
        "tier": "arancione",
        "make_appointment": {"kind": "teleconsulto", "priority": "routine", "within_hours": 8},
    },
    "autogestione": {
        "label": "Autogestione con istruzioni di sicurezza",
        "detail": "Percorso domiciliare con istruzioni chiare su quando richiamare; follow-up attivo entro 3 giorni.",
        "tier": "verde",
        "make_appointment": None,
    },
}

YN = {"type": "yes_no", "options": [{"value": "no", "label": "No"}, {"value": "sì", "label": "Sì"}]}


def _p(code, label, description, questions, red, amber, safety_net):
    return {
        "code": code,
        "label": label,
        "description": description,
        "questions": questions,
        "red": red,        # question_id -> {"flag": str, "disposition": code}
        "amber": amber,    # list of {"when": {qid: value} | "context": str, "reason": str, "disposition": code}
        "safety_net": safety_net,
    }


PROTOCOLS = [
    _p(
        "dolore_toracico", "Dolore al petto",
        "Valutazione di dolore o discomfort toracico.",
        [
            {"id": "q1", "text": "Il dolore è costrittivo/opprimente e dura da più di 15 minuti?", **YN},
            {"id": "q2", "text": "Il dolore si estende a braccio, spalla o mandibola?", **YN},
            {"id": "q3", "text": "C'è dispnea a riposo, sudorizione fredda o nausea associata?", **YN},
            {"id": "q4", "text": "Il paziente ha una cardiopatia nota?", **YN},
            {"id": "q5", "text": "Il dolore cambia con la respirazione o è riproducibile premendo sul punto?", **YN},
            {"id": "q6", "text": "Il dolore è già risolto ed era breve (< 20 minuti), senza altri sintomi?", **YN},
        ],
        red={
            "q1": {"flag": "Dolore costrittivo persistente > 15 min", "disposition": "emergenza_118"},
            "q2": {"flag": "Irradiazione a braccio/mandibola", "disposition": "emergenza_118"},
            "q3": {"flag": "Dispnea a riposo / sudorizione fredda", "disposition": "emergenza_118"},
            "q4": {"flag": "Cardiopatia nota con dolore attivo", "disposition": "emergenza_118"},
        },
        amber=[
            {"when": {"q5": "sì"}, "reason": "Dolore muscoloscheletrico suggerito ma non confermato al telefono",
             "disposition": "visita_48h"},
            {"when": {"q6": "sì"}, "reason": "Episodio risolto: esclusione elettrocardiografica consigliata",
             "disposition": "visita_24h"},
        ],
        safety_net="Se il dolore torna, peggiora o compaiono dispnea o sudorazione: chiamare il 118.",
    ),
    _p(
        "algie_addominali", "Dolori addominali",
        "Valutazione di dolore addomicale secondo algoritmo dedicato.",
        [
            {"id": "q1", "text": "L'addome è rigido, teso, al minimo tocco?", **YN},
            {"id": "q2", "text": "C'è vomito con sangue o feci scure (melena)?", **YN},
            {"id": "q3", "text": "Il dolore è intenso e localizzato alla fossa iliaca destra?", **YN},
            {"id": "q4", "text": "Febbre ≥ 38.5 °C associata al dolore?", **YN},
            {"id": "q5", "text": "Il dolore dura da più di 24 ore senza miglioramento?", **YN},
            {"id": "q6", "text": "Vomito ripetuto e impossibilità di assumere liquidi?", **YN},
            {"id": "q7", "text": "Dolore crampiforme lieve, comparsa recente, riferibile ad alimentazione o stress?", **YN},
        ],
        red={
            "q1": {"flag": "Addome rigido (sospetta perforazione/peritonite)", "disposition": "emergenza_118"},
            "q2": {"flag": "Emorragia digestiva (ematemesi/melena)", "disposition": "emergenza_118"},
            "q3": {"flag": "Dolore intenso in fossa iliaca destra (sospetta appendicite)", "disposition": "pronto_soccorso"},
        },
        amber=[
            {"when": {"q4": "sì"}, "reason": "Febbre alta con dolore addominale", "disposition": "visita_urgente_24h"},
            {"when": {"q6": "sì"}, "reason": "Vomito intrattabile: rischio disidratazione/decompensazione",
             "disposition": "visita_urgente_24h"},
            {"when": {"q5": "sì"}, "reason": "Dolore persistente oltre 24 h", "disposition": "visita_48h"},
            {"context": "diabetes", "reason": "Paziente diabetico: il dolore addominale con vomito può precedere una chetoacidosi",
             "disposition": "teleconsulto"},
        ],
        safety_net="Se il dolore migra e si localizza in basso a destra, diventa continuo, o compaiono febbre o vomito: richiamare subito.",
    ),
    _p(
        "tosse", "Tosse",
        "Valutazione di tosse acuta o persistente.",
        [
            {"id": "q1", "text": "C'è dispnea a riposo o difficoltà a parlare?", **YN},
            {"id": "q2", "text": "C'è sangue nell'espettorato?", **YN},
            {"id": "q3", "text": "Dolore toracico presente e persistente?", **YN},
            {"id": "q4", "text": "Febbre ≥ 38.5 °C da più di 3 giorni?", **YN},
            {"id": "q5", "text": "La tosse dura da più di 3 settimane?", **YN},
            {"id": "q6", "text": "Asma o BPCO nota in peggioramento?", **YN},
            {"id": "q7", "text": "Tosse secca senza febbre, comparsa recente, senza altri sintomi?", **YN},
        ],
        red={
            "q1": {"flag": "Dispnea a riposo", "disposition": "emergenza_118"},
            "q2": {"flag": "Emottisi", "disposition": "pronto_soccorso"},
            "q3": {"flag": "Dolore toracico persistente associato", "disposition": "visita_urgente_24h"},
        },
        amber=[
            {"when": {"q4": "sì"}, "reason": "Febbre ≥ 38.5 °C da oltre 3 giorni", "disposition": "visita_urgente_24h"},
            {"when": {"q6": "sì"}, "reason": "Riacutizzazione respiratoria nota", "disposition": "teleconsulto"},
            {"when": {"q5": "sì"}, "reason": "Tosse cronica (> 3 settimane): da approfondire", "disposition": "visita_48h"},
        ],
        safety_net="Se compaiono difficoltà respiratorie, febbre alta persistente o sangue nell'espettorato: richiamare subito.",
    ),
    _p(
        "cefalea", "Cefalea",
        "Valutazione di mal di testa, con screening dei segni d'allarme.",
        [
            {"id": "q1", "text": "La cefalea è arrivata improvvisa e violenta ('la peggiore di sempre')?", **YN},
            {"id": "q2", "text": "C'è febbre con rigidità del collo?", **YN},
            {"id": "q3", "text": "C'è debolezza a un lato, difficoltà a parlare o vedere?", **YN},
            {"id": "q4", "text": "È una cefalea nuova, con pattern diverso dal solito, in età > 50 anni?", **YN},
            {"id": "q5", "text": "Peggiora progressivamente da più giorni nonostante analgesici?", **YN},
            {"id": "q6", "text": "È il consueto mal di testa tensivo/emicranico, già noto?", **YN},
        ],
        red={
            "q1": {"flag": "Cefalea fulminante (sospetta emorragia subaracnoidea)", "disposition": "emergenza_118"},
            "q2": {"flag": "Febbre + rigidità nucale (sospetta meningite)", "disposition": "emergenza_118"},
            "q3": {"flag": "Deficit neurologici focale", "disposition": "emergenza_118"},
        },
        amber=[
            {"when": {"q4": "sì"}, "reason": "Cefalea nuovo-insorta in età matura", "disposition": "visita_48h"},
            {"when": {"q5": "sì"}, "reason": "Cefalea progressiva refrattaria", "disposition": "visita_48h"},
        ],
        safety_net="Se compaiono vomito abbondante, sonnolenza, visione doppia o peggioramento improvviso: chiamare il 118.",
    ),
    _p(
        "febbre", "Febbre",
        "Valutazione di stato febbrile.",
        [
            {"id": "q1", "text": "Temperatura ≥ 39.5 °C non rispondente ai antipiretici?", **YN},
            {"id": "q2", "text": "Confusione, sonnolenza eccessiva o rigidità nucale?", **YN},
            {"id": "q3", "text": "Macchie rosse sulla pelle che non spariscono alla pressione (petecchie)?", **YN},
            {"id": "q4", "text": "Terapia immunosoppressiva o oncologica in corso?", **YN},
            {"id": "q5", "text": "Febbre ≥ 38.5 °C da più di 3 giorni?", **YN},
            {"id": "q6", "text": "Febbre bassa (< 38.5 °C) da meno di 3 giorni con sintomi da raffreddamento?", **YN},
        ],
        red={
            "q1": {"flag": "Iperpirexia refrattaria", "disposition": "pronto_soccorso"},
            "q2": {"flag": "Confusione/rigidità nucale", "disposition": "emergenza_118"},
            "q3": {"flag": "Esantema petechiale", "disposition": "emergenza_118"},
            "q4": {"flag": "Paziente immunocompromesso febbricitante", "disposition": "pronto_soccorso"},
        },
        amber=[
            {"when": {"q5": "sì"}, "reason": "Stato febbrile prolungato", "disposition": "visita_urgente_24h"},
            {"context": "diabetes", "reason": "Diabetico in stato febbrile: monitoraggio glicemico ravvicinato e valutazione",
             "disposition": "teleconsulto"},
        ],
        safety_net="Se la febbre supera 3 giorni, sale sopra 39.5 °C, o compaiono confusione o macchie sulla pelle: richiamare subito.",
    ),
    _p(
        "lombalgia", "Mal di schiena (lombalgia)",
        "Valutazione di dolore lombare, con screening dei segni d'allarme.",
        [
            {"id": "q1", "text": "Perdita di sensibilità a cavallo dell'ano o incontinenza urinaria/fecale?", **YN},
            {"id": "q2", "text": "Debolezza marcata a una gamba (es. caduta del piede)?", **YN},
            {"id": "q3", "text": "Trauma recente o osteoporosi nota?", **YN},
            {"id": "q4", "text": "Febbre associata al dolore?", **YN},
            {"id": "q5", "text": "Dolore che dura da più di 6 settimane o con perdita di peso non intenzionale?", **YN},
            {"id": "q6", "text": "Dolore meccanico acuto, legato a sforzo, senza segni d'allarme?", **YN},
        ],
        red={
            "q1": {"flag": "Segni di sindrome della cauda equina", "disposition": "emergenza_118"},
            "q2": {"flag": "Deficit motorio a una gamba", "disposition": "pronto_soccorso"},
            "q3": {"flag": "Trauma/osteoporosi: sospetta frattura", "disposition": "pronto_soccorso"},
        },
        amber=[
            {"when": {"q4": "sì"}, "reason": "Febbre + lombalgia (spondilodiscite da escludere)", "disposition": "visita_urgente_24h"},
            {"when": {"q5": "sì"}, "reason": "Lombalgia cronica o segni sistemici", "disposition": "visita_48h"},
        ],
        safety_net="Rimanere attivi entro il dolore; se compaiono febbre, debolezza alle gambe o problemi di sfinteri: richiamare subito.",
    ),
    _p(
        "sintomi_urinari", "Sintomi urinari (bruciore/frequenza)",
        "Valutazione di disuria, pollachiuria e sintomi del tratto urinario.",
        [
            {"id": "q1", "text": "Febbre con brividi e dolore alla schiena/fianco?", **YN},
            {"id": "q2", "text": "Impossibilità a urinare?", **YN},
            {"id": "q3", "text": "Sangue nelle urine?", **YN},
            {"id": "q4", "text": "Paziente di sesso maschile o diabetico?", **YN},
            {"id": "q5", "text": "Episodi ripetuti nell'ultimo anno?", **YN},
            {"id": "q6", "text": "Bruciore e frequenza senza febbre, primo episodio?", **YN},
        ],
        red={
            "q1": {"flag": "Sospetta pielonefrite", "disposition": "visita_urgente_24h"},
            "q2": {"flag": "Ritenzione urinaria", "disposition": "pronto_soccorso"},
        },
        amber=[
            {"when": {"q3": "sì"}, "reason": "Ematuria: da escludere causa urologica", "disposition": "visita_48h"},
            {"when": {"q4": "sì"}, "reason": "Maschio/diabetico: IVU a rischio di complicanza", "disposition": "teleconsulto"},
            {"when": {"q5": "sì"}, "reason": "Infezioni ricorrenti: urocoltura e valutazione", "disposition": "teleconsulto"},
        ],
        safety_net="Bere abbondantemente; se compaiono febbre, brividi o dolore ai fianchi: richiamare subito.",
    ),
    _p(
        "vertigini", "Vertigini/stordimento",
        "Valutazione di capogiro o instabilità.",
        [
            {"id": "q1", "text": "Comparsa improvvisa con visione doppia, parole 'impastate' o debolezza a un lato?", **YN},
            {"id": "q2", "text": "Perdita improvvisa dell'udito a un orecchio?", **YN},
            {"id": "q3", "text": "Caduta con incapacità a stare in piedi?", **YN},
            {"id": "q4", "text": "Vertigine persistente da più giorni senza miglioramento?", **YN},
            {"id": "q5", "text": "Assunzione di farmaci antipertensivi con sintomi al cambio di posizione?", **YN},
            {"id": "q6", "text": "Episodi brevi scatenati dai movimenti del capo, udito normale?", **YN},
        ],
        red={
            "q1": {"flag": "Segni neurologici centrali (sospetto ictus)", "disposition": "emergenza_118"},
            "q2": {"flag": "Perdita uditiva improvvisa monolaterale", "disposition": "pronto_soccorso"},
            "q3": {"flag": "Incapacità deambulazione", "disposition": "pronto_soccorso"},
        },
        amber=[
            {"when": {"q4": "sì"}, "reason": "Vertigine persistente", "disposition": "visita_48h"},
            {"when": {"q5": "sì"}, "reason": "Possibile ipotensione ortostatica da farmaci: verifica pressione", "disposition": "teleconsulto"},
        ],
        safety_net="Se compaiono vedo doppio, difficoltà a parlare o debolezza a un lato: chiamare il 118 subito.",
    ),
    _p(
        "altro", "Altro motivo (algoritmo generale)",
        "Screening generale dei segni d'allarme quando il motivo non rientra nei protocolli dedicati.",
        [
            {"id": "q1", "text": "Dolore al petto o difficoltà respiratoria in questo momento?", **YN},
            {"id": "q2", "text": "Perdita di conoscenza o caduta nei giorni scorsi?", **YN},
            {"id": "q3", "text": "Difficoltà improvvisa a parlare, vedere o muoversi?", **YN},
            {"id": "q4", "text": "Sanguinamento che non si arresta?", **YN},
            {"id": "q5", "text": "Sintomo lieve, senza segni d'allarme, presente da pochi giorni?", **YN},
        ],
        red={
            "q1": {"flag": "Dolore toracico/dispnea al momento della chiamata", "disposition": "emergenza_118"},
            "q2": {"flag": "Sincope recente: valutazione urgente", "disposition": "visita_urgente_24h"},
            "q3": {"flag": "Deficit neurologico improvviso", "disposition": "emergenza_118"},
            "q4": {"flag": "Sanguinamento attivo", "disposition": "pronto_soccorso"},
        },
        amber=[
            {"context": "risk_alto", "reason": "Profilo di rischio alto: contatto ravvicinato con l'operatore",
             "disposition": "teleconsulto"},
        ],
        safety_net="Se il sintomo peggiora rapidamente o compaiono i segni d'allarme elencati: richiamare subito.",
    ),
]


def get_protocol(code: str):
    for protocol in PROTOCOLS:
        if protocol["code"] == code:
            return protocol
    return None


def protocol_summary():
    """Lightweight catalogue for the operator's UI."""
    return [
        {"code": p["code"], "label": p["label"], "description": p["description"],
         "n_questions": len(p["questions"])}
        for p in PROTOCOLS
    ]


def evaluate_protocol(protocol, answers: dict, context: dict) -> dict:
    """Run a protocol against collected answers.

    `answers` maps question_id -> value ("sì"/"no" for yes/no questions).
    `context` may carry: diabetes (bool), age (int), risk_level ("basso"|"medio"|"alto").

    Returns tier, disposition, red flags, and the reasoning trail shown to the
    operator.
    """
    trail = []
    red_flags = []

    for qid, spec in protocol["red"].items():
        if answers.get(qid) == "sì":
            red_flags.append(spec["flag"])
            trail.append(f"Segno d'allarme: {spec['flag']} → {DISPOSITIONS[spec['disposition']]['label']}")
            return {
                "tier": "rosso",
                "disposition": spec["disposition"],
                "red_flags": red_flags,
                "trail": trail,
                "safety_net": protocol["safety_net"],
            }

    applied = []
    for rule in protocol["amber"]:
        when = rule.get("when")
        matched = True
        if when:
            matched = all(answers.get(q) == v for q, v in when.items())
        elif rule.get("context"):
            matched = bool(context.get(rule["context"]))
        if matched:
            applied.append(rule)

    if applied:
        # The most serious of the triggered arancione dispositions wins.
        order = ["visita_urgente_24h", "visita_48h", "teleconsulto"]
        best = min(applied, key=lambda r: order.index(r["disposition"]) if r["disposition"] in order else 99)
        for rule in applied:
            trail.append(f"Arancione: {rule['reason']} → {DISPOSITIONS[rule['disposition']]['label']}")
        return {
            "tier": "arancione",
            "disposition": best["disposition"],
            "red_flags": red_flags,
            "trail": trail,
            "safety_net": protocol["safety_net"],
        }

    tier = "verde"
    disposition = "autogestione"
    note = None
    # Risk modulation: a high-risk worker never leaves the call without an
    # operator contact point.
    if context.get("risk_level") == "alto":
        tier = "arancione"
        disposition = "teleconsulto"
        note = "Profilo di rischio alto: il protocollo prevede il teleconsulto anche per quadri lievi."
        trail.append(note)

    trail.append("Nessun segno d'allarme rilevato: percorso di autogestione con istruzioni di sicurezza.")
    return {
        "tier": tier,
        "disposition": disposition,
        "red_flags": red_flags,
        "trail": trail,
        "safety_net": protocol["safety_net"],
    }


def default_appointment_slot(within_hours: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=within_hours)
