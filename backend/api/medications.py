"""Therapy management (patient_medications) + clinical profile editing."""
from flask import Blueprint, jsonify, request

from extensions import db
from models import Patient, PatientMedication
from api.helpers import get_patient_for, require_auth, require_role

bp = Blueprint("medications", __name__, url_prefix="/api")


def _payload(m: PatientMedication) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "dosage": m.dosage,
        "schedule": m.schedule,
        "active": m.active,
    }


@bp.get("/patients/<int:patient_id>/medications")
@require_auth
def list_medications(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    rows = (
        db.session.query(PatientMedication)
        .filter_by(patient_id=patient.id)
        .order_by(PatientMedication.active.desc(), PatientMedication.name)
        .all()
    )
    return jsonify([_payload(m) for m in rows])


@bp.post("/patients/<int:patient_id>/medications")
@require_role("doctor")
def add_medication(user, patient_id):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        return jsonify({"error": "Paziente non trovato"}), 404
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Nome farmaco obbligatorio"}), 400
    row = PatientMedication(
        patient_id=patient.id, name=name,
        dosage=(body.get("dosage") or "").strip() or None,
        schedule=(body.get("schedule") or "").strip() or None,
        active=bool(body.get("active", True)),
    )
    db.session.add(row)
    db.session.commit()
    return jsonify(_payload(row)), 201


@bp.patch("/medications/<int:medication_id>")
@require_role("doctor")
def update_medication(user, medication_id):
    row = db.session.get(PatientMedication, medication_id)
    if not row:
        return jsonify({"error": "Farmaco non trovato"}), 404
    body = request.get_json(silent=True) or {}
    if "name" in body: row.name = (body["name"] or "").strip() or row.name
    if "dosage" in body: row.dosage = (body["dosage"] or "").strip() or None
    if "schedule" in body: row.schedule = (body["schedule"] or "").strip() or None
    if "active" in body: row.active = bool(body["active"])
    db.session.commit()
    return jsonify(_payload(row))


@bp.delete("/medications/<int:medication_id>")
@require_role("doctor")
def delete_medication(user, medication_id):
    row = db.session.get(PatientMedication, medication_id)
    if not row:
        return jsonify({"error": "Farmaco non trovato"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"ok": True})


@bp.patch("/patients/<int:patient_id>/profile")
@require_role("doctor")
def update_profile(user, patient_id):
    """Clinical-administrative corrections (comorbidities, contacts, job)."""
    patient = db.session.get(Patient, patient_id)
    if not patient:
        return jsonify({"error": "Paziente non trovato"}), 404
    import json
    body = request.get_json(silent=True) or {}
    if "comorbidities" in body:
        patient.comorbidities = json.dumps([c for c in body["comorbidities"] if c.strip()])
    for field in ("phone", "work_pattern", "primary_diagnosis"):
        if field in body:
            setattr(patient, field, (body[field] or "").strip() or None)
    if "height_cm" in body:
        try:
            patient.height_cm = float(body["height_cm"]) if body["height_cm"] else None
        except (TypeError, ValueError):
            return jsonify({"error": "Altezza non valida"}), 400
    db.session.commit()
    return jsonify({"ok": True})
