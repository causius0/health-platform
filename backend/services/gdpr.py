"""GDPR utilities: full data export and account anonymization."""
import json

from sqlalchemy.orm import Session

from models import (
    AnamnesisAnswer, AnamnesisQuestion, Appointment, CarePathway, ChatThread,
    Encounter, FollowUp, GoalCheckIn, HealthGoal, MonitoringPlanItem,
    Observation, Patient, RiskAssessment, TriageAssessment,
    WellbeingAssessment,
)


def export_patient_data(session: Session, patient: Patient) -> dict:
    """Complete, portable copy of everything the platform holds on a worker."""
    def rows(query, serializer):
        return [serializer(r) for r in query.all()]

    return {
        "profile": {
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "birth_date": patient.birth_date.isoformat() if patient.birth_date else None,
            "sex": patient.sex,
            "phone": patient.phone,
            "height_cm": patient.height_cm,
            "employer": patient.employer,
            "job_title": patient.job_title,
            "work_pattern": patient.work_pattern,
            "primary_diagnosis": patient.primary_diagnosis,
            "comorbidities": json.loads(patient.comorbidities or "[]"),
        },
        "observations": rows(
            Observation.query.filter_by(patient_id=patient.id).order_by(Observation.taken_on),
            lambda o: {"code": o.code, "value": o.value, "source": o.source,
                       "taken_on": o.taken_on.isoformat()},
        ),
        "encounters": rows(
            Encounter.query.filter_by(patient_id=patient.id),
            lambda e: {"date": e.encounter_date.isoformat(), "kind": e.kind,
                       "diagnosis": e.diagnosis, "notes": e.notes},
        ),
        "anamnesis": rows(
            AnamnesisAnswer.query.filter_by(patient_id=patient.id),
            lambda a: {"question": session.get(AnamnesisQuestion, a.question_id).code,
                       "value": a.value, "answered_by": a.answered_by},
        ),
        "risk_assessments": rows(
            RiskAssessment.query.filter_by(patient_id=patient.id),
            lambda r: {"computed_at": r.computed_at.isoformat(), "level": r.level,
                       "risk_count": r.risk_count, "protective_count": r.protective_count},
        ),
        "goals": rows(
            HealthGoal.query.filter_by(patient_id=patient.id),
            lambda g: {"title": g.title, "area": g.area, "status": g.status,
                       "frequency_per_week": g.frequency_per_week},
        ),
        "appointments": rows(
            Appointment.query.filter_by(patient_id=patient.id),
            lambda a: {"kind": a.kind, "reason": a.reason, "status": a.status,
                       "scheduled_at": a.scheduled_at.isoformat()},
        ),
        "follow_ups": rows(
            FollowUp.query.filter_by(patient_id=patient.id),
            lambda f: {"reason": f.reason, "due_on": f.due_on.isoformat(),
                       "status": f.status},
        ),
        "wellbeing": rows(
            WellbeingAssessment.query.filter_by(patient_id=patient.id),
            lambda w: {"instrument": w.instrument, "score": w.score,
                       "category": w.category, "taken_on": w.taken_on.isoformat()},
        ),
        "pathways": rows(
            CarePathway.query.filter_by(patient_id=patient.id),
            lambda p: {"template": p.template.code, "status": p.status,
                       "started_on": p.started_on.isoformat()},
        ),
        "monitoring_plan": rows(
            MonitoringPlanItem.query.filter_by(patient_id=patient.id),
            lambda m: {"code": m.code, "frequency_days": m.frequency_days,
                       "active": m.active},
        ),
        "chats": rows(
            ChatThread.query.filter_by(patient_id=patient.id),
            lambda t: {"subject": t.subject, "status": t.status,
                       "messages": len(t.messages)},
        ),
    }


def anonymize_patient(session: Session, patient: Patient, user) -> None:
    """Right-to-erasure: remove personal data, keep aggregate/clinical history.

    Profile fields are blanked, credentials invalidated, chats and free-text
    notes removed. Clinical measurements are retained in pseudonymized form for
    occupational-health statistics.
    """
    import secrets

    user.password_hash = secrets.token_urlsafe(32)
    user.email = None
    user.username = f"eliminato-{user.id}"

    patient.first_name = "Utente"
    patient.last_name = f"eliminato-{patient.id}"
    patient.birth_date = None
    patient.sex = None
    patient.fiscal_code = None
    patient.phone = None
    patient.comorbidities = None

    # free-text and personal content
    ChatThread.query.filter_by(patient_id=patient.id).delete()
    TriageAssessment.query.filter_by(patient_id=patient.id).delete()
    for enc in Encounter.query.filter_by(patient_id=patient.id):
        enc.notes = None
    for fu in FollowUp.query.filter_by(patient_id=patient.id):
        fu.outcome = None
        fu.reason = "richiamo (dati cancellati su richiesta)"
    for g in HealthGoal.query.filter_by(patient_id=patient.id):
        g.title = "obiettivo (dati cancellati su richiesta)"

    # session housekeeping
    session.flush()
