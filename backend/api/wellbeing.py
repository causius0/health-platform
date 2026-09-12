"""Wellbeing instruments: catalogue, submission with scoring, history, engagement."""
import json
from datetime import date

from flask import Blueprint, jsonify, request

from extensions import db
from models import WellbeingAssessment
from api.helpers import get_patient_for, parse_date, require_auth
from services import wellbeing

bp = Blueprint("wellbeing", __name__, url_prefix="/api")


@bp.get("/wellbeing/instruments")
@require_auth
def instruments(user):
    return jsonify(wellbeing.instruments_catalogue())


@bp.get("/patients/<int:patient_id>/wellbeing")
@require_auth
def history(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    rows = (
        db.session.query(WellbeingAssessment)
        .filter(WellbeingAssessment.patient_id == patient.id)
        .order_by(WellbeingAssessment.taken_on.desc())
        .limit(60)
        .all()
    )
    return jsonify([
        {
            "id": r.id,
            "instrument": r.instrument,
            "label": wellbeing.INSTRUMENTS[r.instrument]["label"] if r.instrument in wellbeing.INSTRUMENTS else r.instrument,
            "score": r.score,
            "category": r.category,
            "taken_on": r.taken_on.isoformat(),
            "answers": json.loads(r.answers),
        }
        for r in rows
    ])


@bp.post("/patients/<int:patient_id>/wellbeing")
@require_auth
def submit(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    body = request.get_json(silent=True) or {}
    instrument = body.get("instrument", "")
    if instrument not in wellbeing.INSTRUMENTS:
        return jsonify({"error": "Strumento non riconosciuto"}), 400
    answers = body.get("answers") or {}
    if not isinstance(answers, dict) or not answers:
        return jsonify({"error": "Risposte obbligatorie"}), 400
    try:
        score, category = wellbeing.score_instrument(instrument, answers)
    except (ValueError, TypeError) as exc:
        return jsonify({"error": f"Risposte non valide: {exc}"}), 422

    row = WellbeingAssessment(
        patient_id=patient.id,
        instrument=instrument,
        answers=json.dumps(answers),
        score=score,
        category=category,
        taken_on=parse_date(body.get("taken_on"), "data") or date.today(),
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({
        "id": row.id,
        "instrument": instrument,
        "score": score,
        "category": category,
        "taken_on": row.taken_on.isoformat(),
    }), 201


@bp.get("/patients/<int:patient_id>/engagement")
@require_auth
def engagement(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    return jsonify(wellbeing.compute_engagement(db.session, patient))
