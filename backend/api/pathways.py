"""Care pathway endpoints: enrollment, step actions, booking."""
from datetime import date

from flask import Blueprint, jsonify, request

from extensions import db
from models import CarePathway, CarePathwayStep, PathwayTemplate, Patient
from api.helpers import get_patient_for, parse_date, require_auth, require_role
from services import pathways

bp = Blueprint("pathways", __name__, url_prefix="/api")


@bp.get("/pathways/templates")
@require_role("doctor")
def templates(user):
    rows = db.session.query(PathwayTemplate).filter_by(active=True).all()
    return jsonify([
        {
            "code": t.code, "name": t.name, "description": t.description,
            "target_text": t.target_text,
            "steps": [{"title": s.title, "kind": s.kind, "offset_days": s.offset_days} for s in t.steps],
        }
        for t in rows
    ])


@bp.get("/patients/<int:patient_id>/pathways")
@require_auth
def patient_pathways(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    rows = (
        db.session.query(CarePathway)
        .filter(CarePathway.patient_id == patient.id, CarePathway.status == "attivo")
        .order_by(CarePathway.started_on.desc())
        .all()
    )
    return jsonify([pathways.serialize_pathway(db.session, p) for p in rows])


@bp.get("/patients/<int:patient_id>/pathways/suggestions")
@require_role("doctor")
def suggested_pathways(user, patient_id):
    """Rule-based proposal from diagnosis, risk level and recent calls."""
    patient = db.session.get(Patient, patient_id)
    if not patient:
        return jsonify({"error": "Paziente non trovato"}), 404
    return jsonify(pathways.suggest_pathways(db.session, patient))


@bp.post("/patients/<int:patient_id>/pathways")
@require_role("doctor")
def enroll_patient(user, patient_id):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        return jsonify({"error": "Paziente non trovato"}), 404
    body = request.get_json(silent=True) or {}
    try:
        pathway = pathways.enroll(db.session, patient, body.get("template_code", ""), user.id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    db.session.commit()
    return jsonify(pathways.serialize_pathway(db.session, pathway)), 201


@bp.delete("/care-pathways/<int:pathway_id>")
@require_role("doctor")
def discontinue(user, pathway_id):
    pathway = db.session.get(CarePathway, pathway_id)
    if not pathway:
        return jsonify({"error": "Percorso non trovato"}), 404
    pathway.status = "interrotto"
    db.session.commit()
    return jsonify({"ok": True})


@bp.post("/pathway-steps/<int:step_id>/complete")
@require_auth
def complete_step(user, step_id):
    step = db.session.get(CarePathwayStep, step_id)
    if not step:
        return jsonify({"error": "Passo non trovato"}), 404
    patient, err = get_patient_for(user, step.pathway.patient_id)
    if err:
        return jsonify({"error": err}), 403
    body = request.get_json(silent=True) or {}
    step.status = "completato"
    step.completed_on = parse_date(body.get("completed_on"), "data") or date.today()
    step.outcome = (body.get("outcome") or "").strip() or None
    db.session.commit()
    pathway = db.session.get(CarePathway, step.pathway_id)
    return jsonify(pathways.serialize_pathway(db.session, pathway))


@bp.post("/pathway-steps/<int:step_id>/book")
@require_auth
def book_step(user, step_id):
    """Book the visit/exam that fulfils a step (worker proposes, operator confirms)."""
    step = db.session.get(CarePathwayStep, step_id)
    if not step:
        return jsonify({"error": "Passo non trovato"}), 404
    patient, err = get_patient_for(user, step.pathway.patient_id)
    if err:
        return jsonify({"error": err}), 403
    body = request.get_json(silent=True) or {}
    from api.helpers import parse_datetime
    from datetime import datetime, time, timezone
    from models import Appointment

    from services.triage_protocols import default_appointment_slot

    raw = body.get("scheduled_at")
    when = None
    if raw and "T" in str(raw):
        when = parse_datetime(raw, "data")
    elif raw:
        chosen = parse_date(raw, "data")
        if chosen:
            when = datetime.combine(chosen, time(9, 0), tzinfo=timezone.utc)
    if when is None:
        when = default_appointment_slot(24 * 7)
    kind = "esame" if step.kind == "screening" else "visita_ambulatoriale"
    appt = Appointment(
        patient_id=patient.id,
        doctor_id=patient.assigned_doctor_id,
        kind=kind,
        reason=f"Percorso · {step.title}",
        priority="routine",
        scheduled_at=when,
        location="Ambulatorio Health Platform",
        status="proposto" if user.role == "patient" else "confermato",
        created_by_user_id=user.id,
        created_via="percorso",
        pathway_step_id=step.id,
    )
    db.session.add(appt)
    db.session.flush()
    step.appointment_id = appt.id
    step.status = "programmato"
    db.session.commit()

    pathway = db.session.get(CarePathway, step.pathway_id)
    payload = pathways.serialize_pathway(db.session, pathway)
    return jsonify({
        "pathway": payload,
        "appointment": {
            "id": appt.id, "kind": appt.kind, "scheduled_at": appt.scheduled_at.isoformat(),
            "status": appt.status, "location": appt.location,
        },
    }), 201


@bp.post("/pathway-steps/<int:step_id>/follow-up")
@require_role("doctor")
def schedule_step_followup(user, step_id):
    """Operator-side: schedule the recall call that fulfils a richiamo step."""
    step = db.session.get(CarePathwayStep, step_id)
    if not step:
        return jsonify({"error": "Passo non trovato"}), 404
    pathway = db.session.get(CarePathway, step.pathway_id)
    body = request.get_json(silent=True) or {}
    due_on = parse_date(body.get("due_on"), "scadenza") or step.due_on

    from models import FollowUp
    fu = FollowUp(
        patient_id=pathway.patient_id, created_by_user_id=user.id,
        due_on=due_on, reason=step.title, channel="chiamata",
    )
    db.session.add(fu)
    db.session.flush()
    step.followup_id = fu.id
    step.status = "programmato"
    db.session.commit()
    return jsonify(pathways.serialize_pathway(db.session, pathway)), 201
