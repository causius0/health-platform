"""Doctor workspace bootstrap: one call for the whole console."""
import json
from datetime import date as date_type, datetime, timedelta, timezone
from datetime import date

from flask import Blueprint, jsonify

from extensions import db
from models import (
    Appointment,
    CarePathway,
    ChatThread,
    FollowUp,
    Patient,
    SymptomCheckIn,
    TriageAssessment,
    User,
)
from api.helpers import require_role
from services import notifications, risk_engine

bp = Blueprint("doctor", __name__, url_prefix="/api/doctor")


@bp.get("/report")
@require_role("doctor")
def report(user):
    """Management view: pathway adherence, engagement and risk by employer."""
    from models import WellbeingAssessment
    from datetime import date as date_type
    from services.pathways import step_state

    patients = db.session.query(Patient).all()
    grouped = {}
    for p in patients:
        key = p.employer or "—"
        entry = grouped.setdefault(key, {
            "employer": key, "workers": 0,
            "pathway_progress": [], "overdue_steps": 0,
            "risk_counts": [], "engagement": [],
        })
        entry["workers"] += 1

        for pathway in db.session.query(CarePathway).filter_by(patient_id=p.id, status="attivo"):
            done = 0
            for s in pathway.steps:
                if step_state(s) == "completato":
                    done += 1
                elif step_state(s) == "in_ritardo":
                    entry["overdue_steps"] += 1
            if pathway.steps:
                entry["pathway_progress"].append(round(done / len(pathway.steps) * 100))

        evaluation = risk_engine.evaluate_patient(db.session, p)
        entry["risk_counts"].append(evaluation["risk_count"])

        latest_wb = (
            db.session.query(WellbeingAssessment)
            .filter(WellbeingAssessment.patient_id == p.id)
            .order_by(WellbeingAssessment.taken_on.desc())
            .first()
        )
        # absence days from the latest occupational questionnaire
        if latest_wb:
            try:
                answers = json.loads(latest_wb.answers)
                if latest_wb.instrument == "work" and "absence_days" in answers:
                    entry["engagement"].append(int(answers["absence_days"]))
            except (ValueError, TypeError):
                pass

    def avg(values):
        return round(sum(values) / len(values), 1) if values else None

    rows = []
    for key, e in grouped.items():
        rows.append({
            "employer": key,
            "workers": e["workers"],
            "avg_pathway_progress": avg(e["pathway_progress"]),
            "overdue_steps": e["overdue_steps"],
            "avg_risk_factors": avg(e["risk_counts"]),
            "avg_absence_days_12m": avg([d for d in e["engagement"] if isinstance(d, int)]),
        })
    rows.sort(key=lambda r: -(r["overdue_steps"] or 0))
    return jsonify({"generated_at": datetime.now(timezone.utc).isoformat(), "rows": rows})


@bp.get("/dashboard")
@require_role("doctor")
def dashboard(user):
    patients = db.session.query(Patient).order_by(Patient.last_name).all()

    alerts = []
    summaries = []
    for p in patients:
        evaluation = risk_engine.evaluate_patient(db.session, p)
        alerts.extend(risk_engine.clinical_alerts(db.session, p, evaluation))
        summaries.append({
            "id": p.id,
            "full_name": p.full_name,
            "age": evaluation.get("age"),
            "primary_diagnosis": p.primary_diagnosis,
            "job_title": p.job_title,
            "employer": p.employer,
            "risk_level": evaluation["level"],
            "risk_count": evaluation["risk_count"],
            "protective_count": evaluation["protective_count"],
            "has_critical": evaluation["has_critical"],
            "recommendations": evaluation["recommendations"],
        })

    summaries.sort(key=lambda s: ({"alto": 0, "medio": 1, "basso": 2}[s["risk_level"]], s["full_name"]))

    waiting_threads = (
        db.session.query(ChatThread)
        .filter(ChatThread.kind == "coach",
                ChatThread.status.in_(["waiting_operator", "with_operator"]))
        .order_by(ChatThread.updated_at.desc())
        .all()
    )

    today = date.today()
    pending_followups = (
        db.session.query(FollowUp, Patient)
        .join(Patient, FollowUp.patient_id == Patient.id)
        .filter(FollowUp.status == "pending")
        .order_by(FollowUp.due_on)
        .limit(20)
        .all()
    )

    upcoming = (
        db.session.query(Appointment, Patient)
        .join(Patient, Appointment.patient_id == Patient.id)
        .filter(Appointment.status.in_(["proposto", "confermato"]),
                Appointment.scheduled_at >= datetime.now(timezone.utc) - timedelta(hours=2))
        .order_by(Appointment.scheduled_at)
        .limit(15)
        .all()
    )

    recent_triage = (
        db.session.query(TriageAssessment, Patient)
        .join(Patient, TriageAssessment.patient_id == Patient.id)
        .order_by(TriageAssessment.created_at.desc())
        .limit(10)
        .all()
    )

    severity_rank = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: severity_rank.get(a["severity"], 3))

    recent_checkins = (
        db.session.query(SymptomCheckIn, Patient)
        .join(Patient, SymptomCheckIn.patient_id == Patient.id)
        .filter(SymptomCheckIn.taken_on >= date_type.today() - timedelta(days=7))
        .order_by(SymptomCheckIn.created_at.desc())
        .limit(10)
        .all()
    )

    return jsonify({
        "patients": summaries,
        "operator_notifications": notifications.for_doctor(db.session),
        "recent_symptom_checkins": [
            {
                "patient_id": p.id,
                "patient_name": p.full_name,
                "taken_on": c.taken_on.isoformat(),
                "tier": c.tier,
                "answers": json.loads(c.answers),
            }
            for c, p in recent_checkins
        ],
        "alerts": [
            {**a, "patient_name": next((s["full_name"] for s in summaries if s["id"] == a["patient_id"]), "—")}
            for a in alerts[:25]
        ],
        "waiting_threads": [
            {
                "id": t.id,
                "patient_id": t.patient_id,
                "patient_name": next((s["full_name"] for s in summaries if s["id"] == t.patient_id), "—"),
                "status": t.status,
                "subject": t.subject,
                "updated_at": t.updated_at.isoformat(),
            }
            for t in waiting_threads
        ],
        "pending_followups": [
            {
                "id": f.id,
                "patient_id": p.id,
                "patient_name": p.full_name,
                "due_on": f.due_on.isoformat(),
                "reason": f.reason,
                "channel": f.channel,
                "overdue": f.due_on < today,
            }
            for f, p in pending_followups
        ],
        "upcoming_appointments": [
            {
                "id": a.id,
                "patient_id": p.id,
                "patient_name": p.full_name,
                "kind": a.kind,
                "reason": a.reason,
                "priority": a.priority,
                "scheduled_at": a.scheduled_at.isoformat(),
                "status": a.status,
            }
            for a, p in upcoming
        ],
        "recent_triage": [
            {
                "id": t.id,
                "patient_id": p.id,
                "patient_name": p.full_name,
                "complaint_label": t.complaint_label,
                "tier": t.tier,
                "disposition_label": t.disposition_label,
                "created_at": t.created_at.isoformat(),
            }
            for t, p in recent_triage
        ],
    })
