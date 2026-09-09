"""Symptom check-in endpoints (worker self-report, operator visibility)."""
from flask import Blueprint, jsonify, request

from extensions import db
from api.helpers import get_patient_for, require_auth
from services import symptoms

bp = Blueprint("symptoms", __name__, url_prefix="/api")


@bp.get("/symptoms/questions")
@require_auth
def questions(user):
    return jsonify(symptoms.QUESTIONS)


@bp.get("/patients/<int:patient_id>/symptom-checkins")
@require_auth
def history(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    rows = symptoms.latest_for_patient(db.session, patient.id)
    return jsonify([symptoms.serialize(r) for r in rows])


@bp.post("/patients/<int:patient_id>/symptom-checkins")
@require_auth
def submit(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    body = request.get_json(silent=True) or {}
    try:
        row, result = symptoms.save_checkin(db.session, patient, body.get("answers") or {})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    db.session.commit()
    payload = symptoms.serialize(row)
    payload.update({
        "detail": result["detail"],
        "followup_scheduled": row.tier in ("arancione", "rosso"),
        "operator_alerted": row.tier != "verde",
    })
    return jsonify(payload), 201
