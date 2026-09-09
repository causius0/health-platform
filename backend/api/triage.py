"""Triage endpoints: protocols, assessment submission (call handling), history.

Flow for the operator on a Health Platform call:
  1. GET  /api/triage/protocols            → choose the complaint
  2. GET  /api/triage/protocols/<code>     → guided questions
  3. POST /api/triage/assessments          → tier + disposition; automatically
     books the appointment (urgent visit / teleconsult) or schedules the
     safety-net follow-up call, and links them to the record.
"""
import json
from datetime import date, timedelta

from flask import Blueprint, jsonify, request

from extensions import db
from models import Appointment, FollowUp, Patient, TriageAssessment
from api.helpers import require_auth, require_role
from services import risk_engine, triage_protocols

bp = Blueprint("triage", __name__, url_prefix="/api")


@bp.get("/triage/protocols")
@require_role("doctor")
def protocols(user):
    return jsonify(triage_protocols.protocol_summary())


@bp.get("/triage/protocols/<code>")
@require_role("doctor")
def protocol_detail(user, code):
    protocol = triage_protocols.get_protocol(code)
    if not protocol:
        return jsonify({"error": "Protocollo non trovato"}), 404
    return jsonify(protocol)


@bp.post("/triage/drafts")
@require_role("doctor")
def save_draft(user):
    """Suspend a call mid-protocol: save partial answers as a resumable draft."""
    body = request.get_json(silent=True) or {}
    protocol = triage_protocols.get_protocol(body.get("protocol_code", ""))
    if not protocol:
        return jsonify({"error": "Protocollo non trovato"}), 404
    answers = body.get("answers") or {}
    if not isinstance(answers, dict):
        return jsonify({"error": "Risposte non valide"}), 400
    patient_id = body.get("patient_id") or None

    draft = (
        db.session.query(TriageAssessment)
        .filter_by(protocol_code=protocol["code"], status="bozza",
                   operator_user_id=user.id)
        .first()
    )
    if draft is None:
        draft = TriageAssessment(
            patient_id=patient_id, operator_user_id=user.id,
            protocol_code=protocol["code"], complaint_label=protocol["label"],
            status="bozza",
            answers=json.dumps(answers), tier="verde",
            disposition_code="autogestione", disposition_label="Bozza",
        )
        db.session.add(draft)
    else:
        draft.patient_id = patient_id
        draft.answers = json.dumps(answers)
    db.session.commit()
    return jsonify({"id": draft.id, "answers": json.loads(draft.answers)}), 201


@bp.get("/triage/drafts")
@require_role("doctor")
def list_drafts(user):
    rows = (
        db.session.query(TriageAssessment)
        .filter_by(status="bozza", operator_user_id=user.id)
        .order_by(TriageAssessment.created_at.desc())
        .all()
    )
    return jsonify([
        {
            "id": r.id,
            "protocol_code": r.protocol_code,
            "complaint_label": r.complaint_label,
            "patient_id": r.patient_id,
            "answers": json.loads(r.answers),
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ])


@bp.delete("/triage/drafts/<int:draft_id>")
@require_role("doctor")
def delete_draft(user, draft_id):
    draft = db.session.get(TriageAssessment, draft_id)
    if not draft or draft.status != "bozza":
        return jsonify({"error": "Bozza non trovata"}), 404
    db.session.delete(draft)
    db.session.commit()
    return jsonify({"ok": True})


@bp.post("/triage/assessments")
@require_role("doctor")
def create_assessment(user):
    body = request.get_json(silent=True) or {}
    protocol = triage_protocols.get_protocol(body.get("protocol_code", ""))
    if not protocol:
        return jsonify({"error": "Protocollo non trovato"}), 404
    answers = body.get("answers") or {}
    if not isinstance(answers, dict) or not answers:
        return jsonify({"error": "Risposte obbligatorie"}), 400

    patient = None
    if body.get("patient_id"):
        patient = db.session.get(Patient, int(body["patient_id"]))
        if not patient:
            return jsonify({"error": "Paziente non trovato"}), 404

    context = {}
    if patient:
        evaluation = risk_engine.evaluate_patient(db.session, patient)
        context = {
            "diabetes": "diabete" in (patient.primary_diagnosis or "").lower(),
            "age": evaluation.get("age"),
            "risk_level": evaluation["level"],
        }

    result = triage_protocols.evaluate_protocol(protocol, answers, context)
    disposition = triage_protocols.DISPOSITIONS[result["disposition"]]

    # Answer trail: question text + given answer, for the clinical record
    q_by_id = {q["id"]: q for q in protocol["questions"]}
    answer_rows = []
    for qid, value in answers.items():
        q = q_by_id.get(qid)
        if not q:
            continue
        answer_rows.append({
            "id": qid,
            "question": q["text"],
            "value": value,
            "option_label": next(
                (o["label"] for o in q.get("options", []) if str(o["value"]) == str(value)),
                str(value),
            ),
        })

    record = TriageAssessment(
        patient_id=patient.id if patient else None,
        operator_user_id=user.id,
        protocol_code=protocol["code"],
        complaint_label=protocol["label"],
        answers=json.dumps(answer_rows),
        tier=result["tier"],
        disposition_code=result["disposition"],
        disposition_label=disposition["label"],
        disposition_detail=disposition["detail"],
        red_flags=json.dumps(result["red_flags"]) if result["red_flags"] else None,
        risk_level_at_triage=context.get("risk_level"),
    )
    db.session.add(record)
    # the call completes: any suspended draft of the same protocol is superseded
    db.session.query(TriageAssessment).filter_by(
        protocol_code=protocol["code"], status="bozza", operator_user_id=user.id,
    ).delete()
    db.session.flush()

    appointment_payload = None
    followup_payload = None

    make = disposition.get("make_appointment")
    if make and patient:
        slot = triage_protocols.default_appointment_slot(make["within_hours"])
        appt = Appointment(
            patient_id=patient.id,
            doctor_id=patient.assigned_doctor_id,
            kind=make["kind"],
            reason=f"Triage · {protocol['label']} — {disposition['label']}",
            priority=make["priority"],
            scheduled_at=slot,
            location="Teleconsulto (piattaforma)" if make["kind"] == "teleconsulto" else "Ambulatorio Health Platform",
            status="confermato",
            created_by_user_id=user.id,
            created_via="triage",
            triage_assessment_id=record.id,
        )
        db.session.add(appt)
        db.session.flush()
        record.appointment_id = appt.id
        appointment_payload = {
            "id": appt.id, "kind": appt.kind, "priority": appt.priority,
            "scheduled_at": appt.scheduled_at.isoformat(), "location": appt.location,
        }
    elif result["tier"] == "verde" and patient:
        fu = FollowUp(
            patient_id=patient.id,
            created_by_user_id=user.id,
            due_on=date.today() + timedelta(days=3),
            reason=f"Safety-netting post-chiamata: {protocol['label']}",
            channel="chiamata",
        )
        db.session.add(fu)
        db.session.flush()
        record.followup_id = fu.id
        followup_payload = {"id": fu.id, "due_on": fu.due_on.isoformat(), "reason": fu.reason}

    db.session.commit()
    return jsonify({
        "id": record.id,
        "tier": record.tier,
        "disposition_code": record.disposition_code,
        "disposition_label": record.disposition_label,
        "disposition_detail": record.disposition_detail,
        "red_flags": result["red_flags"],
        "trail": result["trail"],
        "safety_net": result["safety_net"],
        "risk_level_at_triage": record.risk_level_at_triage,
        "appointment": appointment_payload,
        "follow_up": followup_payload,
    }), 201


def _payload(r: TriageAssessment) -> dict:
    return {
        "id": r.id,
        "patient_id": r.patient_id,
        "patient_name": r.patient.full_name if r.patient else "—",
        "protocol_code": r.protocol_code,
        "complaint_label": r.complaint_label,
        "tier": r.tier,
        "disposition_code": r.disposition_code,
        "disposition_label": r.disposition_label,
        "disposition_detail": r.disposition_detail,
        "red_flags": json.loads(r.red_flags or "[]"),
        "answers": json.loads(r.answers),
        "risk_level_at_triage": r.risk_level_at_triage,
        "appointment_id": r.appointment_id,
        "followup_id": r.followup_id,
        "operator_user_id": r.operator_user_id,
        "created_at": r.created_at.isoformat(),
    }


@bp.get("/patients/<int:patient_id>/triage")
@require_auth
def patient_triage_history(user, patient_id):
    patient, err = _patient_or_error(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    rows = (
        db.session.query(TriageAssessment)
        .filter(TriageAssessment.patient_id == patient.id,
                TriageAssessment.status == "completata")
        .order_by(TriageAssessment.created_at.desc())
        .limit(30)
        .all()
    )
    return jsonify([_payload(r) for r in rows])


@bp.get("/triage/assessments")
@require_role("doctor")
def recent_assessments(user):
    rows = (
        db.session.query(TriageAssessment)
        .filter(TriageAssessment.status == "completata")
        .order_by(TriageAssessment.created_at.desc())
        .limit(50)
        .all()
    )
    return jsonify([_payload(r) for r in rows])


@bp.patch("/triage/assessments/<int:assessment_id>/outcome")
@require_role("doctor")
def set_outcome(user, assessment_id):
    record = db.session.get(TriageAssessment, assessment_id)
    if not record:
        return jsonify({"error": "Valutazione non trovata"}), 404
    body = request.get_json(silent=True) or {}
    record.outcome_notes = (body.get("outcome") or "").strip() or None
    db.session.commit()
    return jsonify(_payload(record))


def _patient_or_error(user, patient_id):
    from api.helpers import get_patient_for
    return get_patient_for(user, patient_id)
