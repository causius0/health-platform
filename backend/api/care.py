"""Care management: goals, check-ins, monitoring plan, follow-ups, appointments."""
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from extensions import db
from models import (
    Appointment,
    CarePathwayStep,
    Encounter,
    FollowUp,
    GoalCheckIn,
    HealthGoal,
    MonitoringPlanItem,
    Patient,
    METRIC_CODES,
)
from api.helpers import BadRequest, get_patient_for, parse_date, parse_datetime, require_auth, require_role

bp = Blueprint("care", __name__, url_prefix="/api")

GOAL_AREAS = {"physical_activity", "nutrition", "smoking", "alcohol", "sleep", "stress", "monitoring"}
APPOINTMENT_KINDS = {"visita_ambulatoriale", "teleconsulto", "visita_specialistica", "esame"}


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------
@bp.get("/patients/<int:patient_id>/goals")
@require_auth
def list_goals(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    goals = (
        db.session.query(HealthGoal)
        .filter(HealthGoal.patient_id == patient.id)
        .order_by(HealthGoal.created_at.desc())
        .all()
    )
    return jsonify([_goal_payload(g) for g in goals])


def _goal_payload(g: HealthGoal) -> dict:
    checkins = sorted(g.checkins, key=lambda c: c.week_of, reverse=True)[:12]
    return {
        "id": g.id,
        "area": g.area,
        "title": g.title,
        "frequency_per_week": g.frequency_per_week,
        "status": g.status,
        "created_by": g.created_by,
        "created_at": g.created_at.isoformat(),
        "checkins": [
            {
                "week_of": c.week_of.isoformat(),
                "completed_days": c.completed_days,
                "note": c.note,
            }
            for c in checkins
        ],
    }


@bp.post("/patients/<int:patient_id>/goals")
@require_auth
def create_goal(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    area = body.get("area") or "physical_activity"
    if not title:
        return jsonify({"error": "Titolo obbligatorio"}), 400
    if area not in GOAL_AREAS:
        return jsonify({"error": "Area non valida"}), 400
    try:
        freq = max(1, min(7, int(body.get("frequency_per_week") or 5)))
    except (TypeError, ValueError):
        return jsonify({"error": "Frequenza non valida"}), 400

    goal = HealthGoal(
        patient_id=patient.id, area=area, title=title,
        frequency_per_week=freq, created_by=user.role,
    )
    db.session.add(goal)
    db.session.commit()
    return jsonify(_goal_payload(goal)), 201


@bp.patch("/goals/<int:goal_id>")
@require_auth
def update_goal(user, goal_id):
    goal = db.session.get(HealthGoal, goal_id)
    if not goal:
        return jsonify({"error": "Obiettivo non trovato"}), 404
    patient, err = get_patient_for(user, goal.patient_id)
    if err:
        return jsonify({"error": err}), 403
    body = request.get_json(silent=True) or {}
    if "status" in body:
        if body["status"] not in ("active", "completed", "abandoned"):
            return jsonify({"error": "Stato non valido"}), 400
        goal.status = body["status"]
        goal.completed_at = datetime.now(timezone.utc) if body["status"] == "completed" else None
    if "frequency_per_week" in body:
        try:
            goal.frequency_per_week = max(1, min(7, int(body["frequency_per_week"])))
        except (TypeError, ValueError):
            return jsonify({"error": "Frequenza non valida"}), 400
    db.session.commit()
    return jsonify(_goal_payload(goal))


@bp.post("/goals/<int:goal_id>/checkin")
@require_auth
def checkin_goal(user, goal_id):
    goal = db.session.get(HealthGoal, goal_id)
    if not goal:
        return jsonify({"error": "Obiettivo non trovato"}), 404
    patient, err = get_patient_for(user, goal.patient_id)
    if err:
        return jsonify({"error": err}), 403
    body = request.get_json(silent=True) or {}
    try:
        days = max(0, min(7, int(body.get("completed_days", 0))))
    except (TypeError, ValueError):
        return jsonify({"error": "Giorni non validi"}), 400
    week_of = parse_date(body.get("week_of"), "settimana") or _monday_of(date.today())
    if week_of.weekday() != 0:
        week_of = _monday_of(week_of)

    row = (
        db.session.query(GoalCheckIn)
        .filter_by(goal_id=goal.id, week_of=week_of)
        .first()
    )
    if row:
        row.completed_days = days
        row.note = body.get("note", row.note)
    else:
        row = GoalCheckIn(
            goal_id=goal.id, patient_id=goal.patient_id,
            week_of=week_of, completed_days=days, note=body.get("note"),
        )
        db.session.add(row)
    db.session.commit()
    return jsonify({"ok": True, "week_of": week_of.isoformat(), "completed_days": days})


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


# ---------------------------------------------------------------------------
# Remote monitoring plan
# ---------------------------------------------------------------------------
@bp.get("/patients/<int:patient_id>/monitoring")
@require_auth
def get_monitoring(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    items = (
        db.session.query(MonitoringPlanItem)
        .filter(MonitoringPlanItem.patient_id == patient.id)
        .order_by(MonitoringPlanItem.created_at)
        .all()
    )
    from models import Observation
    out = []
    for item in items:
        last = (
            db.session.query(Observation)
            .filter(Observation.patient_id == patient.id, Observation.code == item.code)
            .order_by(Observation.taken_on.desc(), Observation.id.desc())
            .first()
        )
        due = None
        if last:
            due = (last.taken_on + timedelta(days=item.frequency_days)).isoformat()
        label, unit, _ref = METRIC_CODES.get(item.code, (item.code, "", ""))
        out.append({
            "id": item.id, "code": item.code, "label": label, "unit": unit,
            "frequency_days": item.frequency_days, "target_text": item.target_text,
            "active": item.active,
            "last_value": last.value if last else None,
            "last_taken_on": last.taken_on.isoformat() if last else None,
            "due_on": due,
            "overdue": bool(due and last and last.taken_on + timedelta(days=item.frequency_days) < date.today()),
        })
    return jsonify(out)


@bp.post("/patients/<int:patient_id>/monitoring")
@require_auth
def add_monitoring(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    body = request.get_json(silent=True) or {}
    code = body.get("code", "")
    if code not in METRIC_CODES:
        return jsonify({"error": "Metrica non riconosciuta"}), 400
    try:
        freq = max(1, min(90, int(body.get("frequency_days") or 7)))
    except (TypeError, ValueError):
        return jsonify({"error": "Frequenza non valida"}), 400
    existing = (
        db.session.query(MonitoringPlanItem)
        .filter_by(patient_id=patient.id, code=code, active=True)
        .first()
    )
    if existing:
        existing.frequency_days = freq
        existing.target_text = body.get("target_text", existing.target_text)
        db.session.commit()
        return jsonify({"ok": True, "id": existing.id, "updated": True})
    item = MonitoringPlanItem(
        patient_id=patient.id, code=code, frequency_days=freq,
        target_text=body.get("target_text"), created_by_user_id=user.id,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"ok": True, "id": item.id}), 201


# ---------------------------------------------------------------------------
# Follow-ups
# ---------------------------------------------------------------------------
@bp.get("/patients/<int:patient_id>/follow-ups")
@require_auth
def list_followups(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    rows = (
        db.session.query(FollowUp)
        .filter(FollowUp.patient_id == patient.id)
        .order_by(FollowUp.due_on.desc())
        .all()
    )
    return jsonify([_followup_payload(r) for r in rows])


def _followup_payload(r: FollowUp) -> dict:
    return {
        "id": r.id,
        "due_on": r.due_on.isoformat(),
        "reason": r.reason,
        "channel": r.channel,
        "status": r.status,
        "outcome": r.outcome,
        "overdue": r.status == "pending" and r.due_on < date.today(),
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "created_at": r.created_at.isoformat(),
    }


@bp.post("/patients/<int:patient_id>/follow-ups")
@require_role("doctor")
def create_followup(user, patient_id):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        return jsonify({"error": "Paziente non trovato"}), 404
    body = request.get_json(silent=True) or {}
    reason = (body.get("reason") or "").strip()
    if not reason:
        return jsonify({"error": "Motivo obbligatorio"}), 400
    due_on = parse_date(body.get("due_on"), "scadenza") or date.today() + timedelta(days=7)
    channel = body.get("channel") or "chiamata"
    if channel not in ("chiamata", "chat", "visita"):
        return jsonify({"error": "Canale non valido"}), 400
    row = FollowUp(
        patient_id=patient.id, created_by_user_id=user.id,
        due_on=due_on, reason=reason, channel=channel,
    )
    db.session.add(row)
    db.session.commit()
    return jsonify(_followup_payload(row)), 201


@bp.patch("/follow-ups/<int:followup_id>")
@require_role("doctor")
def update_followup(user, followup_id):
    row = db.session.get(FollowUp, followup_id)
    if not row:
        return jsonify({"error": "Follow-up non trovato"}), 404
    body = request.get_json(silent=True) or {}
    if "status" in body:
        if body["status"] not in ("pending", "done", "cancelled"):
            return jsonify({"error": "Stato non valido"}), 400
        row.status = body["status"]
        row.completed_at = datetime.now(timezone.utc) if body["status"] == "done" else None
    if "outcome" in body:
        row.outcome = body["outcome"]
    db.session.commit()
    return jsonify(_followup_payload(row))


# ---------------------------------------------------------------------------
# Appointments (office visits / teleconsults — the escalation endpoint)
# ---------------------------------------------------------------------------
@bp.get("/patients/<int:patient_id>/appointments")
@require_auth
def list_appointments(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    rows = (
        db.session.query(Appointment)
        .filter(Appointment.patient_id == patient.id)
        .order_by(Appointment.scheduled_at.desc())
        .limit(50)
        .all()
    )
    return jsonify([_appointment_payload(r) for r in rows])


def _appointment_payload(r: Appointment) -> dict:
    return {
        "id": r.id,
        "kind": r.kind,
        "reason": r.reason,
        "priority": r.priority,
        "scheduled_at": r.scheduled_at.isoformat(),
        "location": r.location,
        "status": r.status,
        "outcome": r.outcome,
        "created_via": r.created_via,
        "created_at": r.created_at.isoformat(),
        "triage_assessment_id": r.triage_assessment_id,
    }


@bp.post("/patients/<int:patient_id>/appointments")
@require_auth
def create_appointment(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    body = request.get_json(silent=True) or {}
    kind = body.get("kind") or "visita_ambulatoriale"
    if kind not in APPOINTMENT_KINDS:
        return jsonify({"error": "Tipo visita non valido"}), 400
    reason = (body.get("reason") or "").strip()
    if not reason:
        return jsonify({"error": "Motivo obbligatorio"}), 400
    scheduled_at = parse_datetime(body.get("scheduled_at"), "data/ora")
    if not scheduled_at:
        raise BadRequest("data/ora appuntamento obbligatoria")
    priority = body.get("priority") or "routine"
    if priority not in ("routine", "urgente"):
        return jsonify({"error": "Priorità non valida"}), 400

    row = Appointment(
        patient_id=patient.id,
        doctor_id=patient.assigned_doctor_id,
        kind=kind, reason=reason, priority=priority,
        scheduled_at=scheduled_at,
        location=body.get("location") or ("Teleconsulto (piattaforma)" if kind == "teleconsulto" else "Ambulatorio Health Platform"),
        status="proposto" if user.role == "patient" else "confermato",
        created_by_user_id=user.id,
        created_via="paziente" if user.role == "patient" else "medico",
    )
    db.session.add(row)
    db.session.commit()
    return jsonify(_appointment_payload(row)), 201


@bp.post("/patients/<int:patient_id>/encounters")
@require_role("doctor")
def create_encounter(user, patient_id):
    """Document an in-person or remote clinical encounter."""
    patient = db.session.get(Patient, patient_id)
    if not patient:
        return jsonify({"error": "Paziente non trovato"}), 404
    body = request.get_json(silent=True) or {}
    kind = body.get("kind") or "controllo"
    if kind not in ("controllo", "urgenza", "followup"):
        return jsonify({"error": "Tipo incontro non valido"}), 400
    encounter_date = parse_date(body.get("encounter_date"), "data") or date.today()
    row = Encounter(
        patient_id=patient.id,
        encounter_date=encounter_date,
        kind=kind,
        facility=(body.get("facility") or "Ambulatorio Health Platform").strip(),
        notes=(body.get("notes") or "").strip() or None,
        diagnosis=(body.get("diagnosis") or "").strip() or None,
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({
        "id": row.id,
        "encounter_date": row.encounter_date.isoformat(),
        "kind": row.kind,
        "facility": row.facility,
        "notes": row.notes,
        "diagnosis": row.diagnosis,
    }), 201


@bp.patch("/appointments/<int:appointment_id>")
@require_auth
def update_appointment(user, appointment_id):
    row = db.session.get(Appointment, appointment_id)
    if not row:
        return jsonify({"error": "Appuntamento non trovato"}), 404
    patient, err = get_patient_for(user, row.patient_id)
    if err:
        return jsonify({"error": err}), 403
    body = request.get_json(silent=True) or {}
    if "status" in body:
        if body["status"] not in ("proposto", "confermato", "completato", "annullato"):
            return jsonify({"error": "Stato non valido"}), 400
        if user.role == "patient" and body["status"] not in ("annullato",):
            return jsonify({"error": "Il paziente può solo annullare"}), 403
        row.status = body["status"]
        # a completed appointment fulfils the pathway step it was booked for
        if body["status"] == "completato" and row.pathway_step_id:
            step = db.session.get(CarePathwayStep, row.pathway_step_id)
            if step and step.status != "completato":
                step.status = "completato"
                step.completed_on = date.today()
        # document the encounter (clinical note written by the operator)
        if body["status"] == "completato" and body.get("clinical_note"):
            db.session.add(Encounter(
                patient_id=row.patient_id,
                encounter_date=date.today(),
                kind="followup" if row.kind == "teleconsulto" else "controllo",
                facility=row.location or "Ambulatorio Health Platform",
                notes=body["clinical_note"],
                diagnosis=row.reason,
            ))
    if "scheduled_at" in body and user.role == "doctor":
        row.scheduled_at = parse_datetime(body["scheduled_at"], "data/ora")
    if "outcome" in body and user.role == "doctor":
        row.outcome = body["outcome"]
    db.session.commit()
    payload = _appointment_payload(row)
    payload["outcome"] = row.outcome
    return jsonify(payload)
