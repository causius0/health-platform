"""Daily symptom check-in: traffic-light triage of worker micro-reports.

Implements the early-detection model from the client's evidence base (COVIDApp:
daily symptom reporting classified verde/arancione/rosso with rapid protocol
activation) adapted to chronic-condition prevention.

Pure rule evaluation (`evaluate`) + persistence helpers. An arancione/rosso
check-in automatically opens a safety-net follow-up call (deduplicated per day).
"""
import json
from datetime import date, timedelta

from sqlalchemy.orm import Session

from models import FollowUp, SymptomCheckIn

# Catalogue exposed to the client so the form is data-driven.
QUESTIONS = [
    {
        "id": "fever",
        "text": "Febbre oggi",
        "options": [
            {"value": "no", "label": "Nessuna"},
            {"value": "leggera", "label": "Leggera (< 37.5 °C)"},
            {"value": "moderata", "label": "Moderata (37.5–39 °C)"},
            {"value": "alta", "label": "Alta (> 39 °C)"},
        ],
    },
    {
        "id": "cough",
        "text": "Tosse",
        "options": [
            {"value": "no", "label": "Nessuna"},
            {"value": "secca", "label": "Secca occasionale"},
            {"value": "persistente", "label": "Persistente / con catarro"},
        ],
    },
    {
        "id": "dyspnea",
        "text": "Difficoltà a respirare",
        "options": [
            {"value": "no", "label": "Nessuna"},
            {"value": "lieve", "label": "Lieve, sotto sforzo"},
            {"value": "grave", "label": "Grave, anche a riposo"},
        ],
    },
    {
        "id": "chest_pain",
        "text": "Dolore al petto",
        "options": [{"value": "no", "label": "No"}, {"value": "sì", "label": "Sì"}],
    },
    {
        "id": "contact",
        "text": "Contatto con casi infettivi negli ultimi 14 giorni",
        "options": [{"value": "no", "label": "No"}, {"value": "sì", "label": "Sì"}],
    },
    {
        "id": "severe_other",
        "text": "Altri sintomi importanti (vomito, diarrea, cefalea intensa)",
        "options": [{"value": "no", "label": "No"}, {"value": "sì", "label": "Sì"}],
    },
]

REQUIRED_IDS = [q["id"] for q in QUESTIONS]

ADVICE = {
    "rosso": "Situazione da non sottovalutare: un operatore sanitario ti richiama "
             "immediatamente. Se i sintomi peggiorano rapidamente chiama il 118.",
    "arancione": "Un operatore sanitario ti richiama entro oggi per una valutazione. "
                 "Rimani a riposo e tieniti idratato.",
    "verde": "Nessun segnale d'allarme oggi: continua il tuo percorso abituale. "
             "Se i sintomi compaiono o peggiorano, rifai il check-in.",
}


def validate_answers(answers) -> dict | None:
    """Return normalized answers, or None when invalid/incomplete."""
    if not isinstance(answers, dict):
        return None
    normalized = {}
    for qid in REQUIRED_IDS:
        value = answers.get(qid)
        allowed = {o["value"] for o in next(q for q in QUESTIONS if q["id"] == qid)["options"]}
        if value not in allowed:
            return None
        normalized[qid] = value
    return normalized


def evaluate(answers: dict) -> dict:
    """Traffic-light rules: rosso → immediate escalation, arancione → operator
    contact today, verde → no alarm."""
    fever = answers.get("fever", "no")
    cough = answers.get("cough", "no")
    dyspnea = answers.get("dyspnea", "no")
    chest_pain = answers.get("chest_pain", "no")
    contact = answers.get("contact", "no")
    severe_other = answers.get("severe_other", "no")

    if dyspnea == "grave" or chest_pain == "sì" or fever == "alta" or \
            (severe_other == "sì" and fever in ("moderata", "alta")):
        alerts = []
        if dyspnea == "grave": alerts.append("dispnea grave a riposo")
        if chest_pain == "sì": alerts.append("dolore al petto")
        if fever == "alta": alerts.append("febbre alta")
        if severe_other == "sì" and fever in ("moderata", "alta"):
            alerts.append("sintomi importanti con febbre")
        return {"tier": "rosso", "advice": ADVICE["rosso"],
                "detail": "Segni d'allarme: " + ", ".join(alerts) + "."}

    if fever == "moderata" or cough == "persistente" or dyspnea == "lieve" or \
            (contact == "sì" and (fever != "no" or cough != "no" or severe_other == "sì")):
        alerts = []
        if fever == "moderata": alerts.append("febbre moderata")
        if cough == "persistente": alerts.append("tosse persistente")
        if dyspnea == "lieve": alerts.append("dispnea lieve")
        if contact == "sì" and (fever != "no" or cough != "no" or severe_other == "sì"):
            alerts.append("contatto con casi infettivi + sintomi")
        return {"tier": "arancione", "advice": ADVICE["arancione"],
                "detail": "Da valutare: " + ", ".join(alerts) + "."}

    return {"tier": "verde", "advice": ADVICE["verde"],
            "detail": "Nessun sintomo significativo segnalato."}


def save_checkin(session: Session, patient, answers: dict, taken_on: date | None = None):
    """Validate, persist and (for non-green tiers) activate the safety-net call.

    Returns (row, result). Deduplicated: one pending follow-up per day+reason.
    """
    normalized = validate_answers(answers)
    if normalized is None:
        raise ValueError("Risposte incomplete o non valide")
    result = evaluate(normalized)
    today = taken_on or date.today()

    row = SymptomCheckIn(
        patient_id=patient.id, taken_on=today,
        answers=json.dumps(normalized), tier=result["tier"],
        advice=result["advice"] + " " + result["detail"],
    )
    session.add(row)

    if result["tier"] in ("arancione", "rosso"):
        reason = f"Check-in sintomi {result['tier']} del {today.isoformat()} — verifica rapida"
        exists = (
            session.query(FollowUp)
            .filter_by(patient_id=patient.id, reason=reason, status="pending")
            .first()
        )
        if not exists:
            session.add(FollowUp(
                patient_id=patient.id,
                created_by_user_id=patient.assigned_doctor.user_id if patient.assigned_doctor else None,
                due_on=today if result["tier"] == "rosso" else today + timedelta(days=1),
                reason=reason,
                channel="chiamata",
            ))
    session.flush()
    return row, result


def latest_for_patient(session, patient_id: int, days: int = 14) -> list:
    since = date.today() - timedelta(days=days)
    return (
        session.query(SymptomCheckIn)
        .filter(SymptomCheckIn.patient_id == patient_id, SymptomCheckIn.taken_on >= since)
        .order_by(SymptomCheckIn.taken_on.desc(), SymptomCheckIn.created_at.desc())
        .all()
    )


def serialize(row: SymptomCheckIn) -> dict:
    return {
        "id": row.id,
        "taken_on": row.taken_on.isoformat(),
        "created_at": row.created_at.isoformat(),
        "tier": row.tier,
        "advice": row.advice,
        "answers": json.loads(row.answers),
    }
