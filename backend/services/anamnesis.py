"""Structured anamnesis: question catalogue, answer metadata, FHIR export.

The catalogue is *data*: clinicians can add/reword questions without touching
code. Lifestyle options carry `risk` / `protective` flags that the risk engine
reads (via `load_answer_meta`), which is what implements the client's rule:
when a monitored factor is negative (absent / below threshold / controlled) it
is treated as a positive (protective) factor, each with its literature-backed
criterion.
"""
import json

from models import AnamnesisAnswer, AnamnesisQuestion, Patient

# section: stile_di_vita | lavoro | storia_clinica
DEFAULT_QUESTIONS = [
    {
        "code": "smoking", "section": "stile_di_vita", "order": 1,
        "prompt": "Fumazione",
        "help_text": "La cessazione del fumo riduce il rischio cardiovascolare già dopo 12 mesi.",
        "options": [
            {"value": "Mai fumato", "label": "Mai fumato", "protective": True},
            {"value": "Ex fumatore/a (da almeno 12 mesi)", "label": "Ex fumatore/a (da almeno 12 mesi)", "protective": True},
            {"value": "Ex fumatore/a (da meno di 12 mesi)", "label": "Ex fumatore/a (da meno di 12 mesi)"},
            {"value": "Fumatore/a attuale", "label": "Fumatore/a attuale", "risk": True},
        ],
    },
    {
        "code": "physical_activity", "section": "stile_di_vita", "order": 2,
        "prompt": "Attività fisica",
        "help_text": "L'OMS raccomanda almeno 150 minuti a settimana di attività moderata.",
        "options": [
            {"value": "Sedentario/a", "label": "Sedentario/a", "risk": True},
            {"value": "1–2 volte a settimana", "label": "1–2 volte a settimana"},
            {"value": "3–4 volte a settimana", "label": "3–4 volte a settimana", "protective": True},
            {"value": "5 o più volte a settimana", "label": "5 o più volte a settimana", "protective": True},
        ],
    },
    {
        "code": "sedentary_hours", "section": "lavoro", "order": 3,
        "prompt": "Tempo seduto in una giornata lavorativa",
        "help_text": "La sedentarietà prolungata (≥ 8 h/die) è un fattore di rischio indipendente.",
        "options": [
            {"value": "Meno di 6 ore", "label": "Meno di 6 ore", "protective": True},
            {"value": "6–8 ore", "label": "6–8 ore"},
            {"value": "Più di 8 ore", "label": "Più di 8 ore", "risk": True},
        ],
    },
    {
        "code": "alcohol", "section": "stile_di_vita", "order": 4,
        "prompt": "Consumo di alcol",
        "options": [
            {"value": "Astemio o occasionale", "label": "Astemio o occasionale", "protective": True},
            {"value": "1–2 unit al giorno", "label": "1–2 unit al giorno"},
            {"value": "Più di 2 unit al giorno o abbuffate", "label": "Più di 2 unit al giorno o abbuffate", "risk": True},
        ],
    },
    {
        "code": "sleep", "section": "stile_di_vita", "order": 5,
        "prompt": "Sonno",
        "help_text": "7–9 ore per notte è l'intervallo raccomandato per gli adulti.",
        "options": [
            {"value": "7–9 ore, di buona qualità", "label": "7–9 ore, di buona qualità", "protective": True},
            {"value": "6–7 ore o qualità irregolare", "label": "6–7 ore o qualità irregolare"},
            {"value": "Meno di 6 ore", "label": "Meno di 6 ore", "risk": True},
            {"value": "Più di 9 ore", "label": "Più di 9 ore", "risk": True},
        ],
    },
    {
        "code": "nutrition", "section": "stile_di_vita", "order": 6,
        "prompt": "Alimentazione",
        "options": [
            {"value": "Equilibrata / mediterranea", "label": "Equilibrata / mediterranea", "protective": True},
            {"value": "Disordinata ma accettabile", "label": "Disordinata ma accettabile"},
            {"value": "Ricca di zuccheri, ultraprocessati o sale", "label": "Ricca di zuccheri, ultraprocessati o sale", "risk": True},
        ],
    },
    {
        "code": "stress", "section": "lavoro", "order": 7,
        "prompt": "Stress percepito e carico lavorativo",
        "help_text": "Alta richiesta e basso controllo sul lavoro (job strain) è un fattore di rischio cardiovascolare.",
        "options": [
            {"value": "Basso o ben gestito", "label": "Basso o ben gestito", "protective": True},
            {"value": "Medio", "label": "Medio"},
            {"value": "Alto, difficile da gestire", "label": "Alto, difficile da gestire", "risk": True},
        ],
    },
    {
        "code": "family_history", "section": "storia_clinica", "order": 8,
        "prompt": "Familiarità",
        "help_text": "Malattie cardiovascolari o diabete in parenti di I grado in età precoce (< 55 anni uomini, < 65 donne).",
        "options": [
            {"value": "Cardiopatia/ictus precoci in I grado", "label": "Cardiopatia/ictus precoci in I grado", "risk": True},
            {"value": "Diabete in I grado", "label": "Diabete in I grado", "risk": True},
            {"value": "Nessuna familiarità rilevante", "label": "Nessuna familiarità rilevante"},
        ],
    },
    {
        "code": "occupational_exposures", "section": "lavoro", "order": 9,
        "prompt": "Esposizioni lavorative",
        "help_text": "Rumore, polveri, solventi, temperature estreme, sollevamento carichi, videoterminale.",
        "options": [
            {"value": "Nessuna esposizione rilevante", "label": "Nessuna esposizione rilevante"},
            {"value": "Esposizione a rumore o polveri", "label": "Esposizione a rumore o polveri", "risk": True},
            {"value": "Movimentazione carichi / mansioni manuali pesanti", "label": "Movimentazione carichi / mansioni manuali pesanti", "risk": True},
            {"value": "Lavoro d'ufficio sedentario prolungato", "label": "Lavoro d'ufficio sedentario prolungato"},
        ],
    },
    {
        "code": "work_incidents", "section": "lavoro", "order": 10,
        "prompt": "Infortuni o incidenti lavorativi negli ultimi 12 mesi",
        "options": [
            {"value": "No", "label": "No"},
            {"value": "Sì, con indennizzo INAIL", "label": "Sì, con indennizzo INAIL", "risk": True},
            {"value": "Sì, senza indennizzo", "label": "Sì, senza indennizzo", "risk": True},
        ],
    },
    {
        "code": "immunizations", "section": "storia_clinica", "order": 11,
        "prompt": "Vaccinazioni",
        "help_text": "Per la sorveglianza sanitaria: influenzale, antitetanica, epatite B, COVID-19.",
        "answer_type": "multi_choice",
        "options": [
            {"value": "Influenzale", "label": "Influenzale"},
            {"value": "Tetano", "label": "Tetano"},
            {"value": "Epatite B", "label": "Epatite B"},
            {"value": "COVID-19", "label": "COVID-19"},
            {"value": "Nessuna", "label": "Nessuna", "risk": True},
        ],
    },
    {
        "code": "allergies", "section": "storia_clinica", "order": 12,
        "prompt": "Allergie o intolleranze",
        "answer_type": "text",
    },
]


def ensure_catalogue(session) -> None:
    """Insert default questions; refresh wording of existing codes without
    touching stored answers."""
    existing = {q.code: q for q in session.query(AnamnesisQuestion).all()}
    for spec in DEFAULT_QUESTIONS:
        row = existing.get(spec["code"])
        if row is None:
            row = AnamnesisQuestion(
                code=spec["code"], section=spec["section"], order=spec["order"],
                prompt=spec["prompt"], help_text=spec.get("help_text"),
                answer_type=spec.get("answer_type", "single_choice"),
                options=json.dumps(spec.get("options", [])),
                risk_factor_code=spec["code"],
            )
            session.add(row)
        else:
            row.prompt = spec["prompt"]
            row.help_text = spec.get("help_text")
            row.options = json.dumps(spec.get("options", []))
            row.section = spec["section"]
            row.order = spec["order"]
    session.commit()


def load_answer_meta(session) -> None:
    """Populate the risk engine's (question, value) -> flags map from the live
    catalogue, so clinicians can re-word options without code changes."""
    from services import risk_engine

    meta = {}
    for q in session.query(AnamnesisQuestion).filter(AnamnesisQuestion.active == True).all():  # noqa: E712
        for opt in json.loads(q.options or "[]"):
            meta[(q.code, opt.get("value"))] = {
                "risk": bool(opt.get("risk")),
                "protective": bool(opt.get("protective")),
            }
    risk_engine.ANSWER_META = meta


def catalogue(session):
    rows = (
        session.query(AnamnesisQuestion)
        .filter(AnamnesisQuestion.active == True)  # noqa: E712
        .order_by(AnamnesisQuestion.order, AnamnesisQuestion.id)
        .all()
    )
    return [
        {
            "id": q.id,
            "code": q.code,
            "section": q.section,
            "prompt": q.prompt,
            "help_text": q.help_text,
            "answer_type": q.answer_type,
            "options": json.loads(q.options or "[]"),
        }
        for q in rows
    ]


def answers_for(session, patient_id: int):
    rows = (
        session.query(AnamnesisAnswer)
        .filter(AnamnesisAnswer.patient_id == patient_id)
        .all()
    )
    by_qid = {}
    for a in rows:
        by_qid[a.question_id] = {
            "value": a.value,
            "answered_by": a.answered_by,
            "updated_at": a.updated_at.isoformat(),
        }
    return by_qid


def export_fhir_questionnaire_response(session, patient: Patient) -> dict:
    """Interoperability: export the anamnesis as a FHIR QuestionnaireResponse
    (Stu3/R4 compatible structure). Observation-linked clinical values remain
    in the `observations` endpoint (FHIR Observation mapping)."""
    items = []
    for q, a in (
        session.query(AnamnesisQuestion, AnamnesisAnswer)
        .join(AnamnesisAnswer, AnamnesisAnswer.question_id == AnamnesisQuestion.id)
        .filter(AnamnesisAnswer.patient_id == patient.id)
        .all()
    ):
        items.append({
            "linkId": q.code,
            "text": q.prompt,
            "answer": [{"valueString": a.value}],
            "extension": [{
                "url": "https://healthplatform.example/fhir/StructureDefinition/answered-by",
                "valueString": a.answered_by,
            }],
        })
    return {
        "resourceType": "QuestionnaireResponse",
        "status": "completed",
        "subject": {"reference": f"Patient/{patient.id}"},
        "authored": patient.created_at.isoformat() if patient.created_at else None,
        "item": items,
    }
