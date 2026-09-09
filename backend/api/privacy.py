"""Worker-facing notifications and GDPR export/erasure."""
import json

from flask import Blueprint, Response, jsonify

from extensions import db
from models import Patient
from api.helpers import get_patient_for, require_auth
from services import gdpr, notifications

bp = Blueprint("privacy", __name__, url_prefix="/api")


@bp.get("/patients/<int:patient_id>/notifications")
@require_auth
def patient_notifications(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    items = notifications.for_patient(db.session, patient)
    return jsonify({
        "items": items,
        "unread_count": sum(1 for n in items if n["severity"] in ("critical", "warning")),
    })


@bp.get("/notifications")
@require_auth
def my_notifications(user):
    """Notifications for the authenticated worker (convenience alias)."""
    if user.role != "patient" or not user.patient_profile:
        return jsonify({"items": [], "unread_count": 0})
    items = notifications.for_patient(db.session, user.patient_profile)
    return jsonify({
        "items": items,
        "unread_count": sum(1 for n in items if n["severity"] in ("critical", "warning")),
    })


@bp.get("/patients/<int:patient_id>/data-export")
@require_auth
def export_all_data(user, patient_id):
    """GDPR data portability: complete JSON copy of the worker's data."""
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    payload = gdpr.export_patient_data(db.session, patient)
    return Response(
        json.dumps(payload, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename=dati_paziente{patient.id}.json"},
    )


@bp.delete("/me")
@require_auth
def delete_account(user):
    """Right to erasure: anonymize the worker's personal data and invalidate access."""
    if user.role != "patient" or not user.patient_profile:
        return jsonify({"error": "Solo i lavoratori possono cancellare l'account da qui"}), 403
    gdpr.anonymize_patient(db.session, user.patient_profile, user)
    db.session.commit()
    return jsonify({"ok": True})
