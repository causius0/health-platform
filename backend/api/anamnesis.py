"""Structured anamnesis endpoints (question catalogue + answers + FHIR export)."""
import json

from flask import Blueprint, Response, jsonify, request

from extensions import db
from models import AnamnesisAnswer, AnamnesisAnswerHistory, AnamnesisQuestion
from api.helpers import get_patient_for, require_auth
from services import anamnesis as ana_service
from services import risk_engine

bp = Blueprint("anamnesis", __name__, url_prefix="/api")


def _assessment_with_answers(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return None, err
    catalog = ana_service.catalogue(db.session)
    answers = ana_service.answers_for(db.session, patient.id)
    return (patient, catalog, answers), None


@bp.get("/patients/<int:patient_id>/anamnesis")
@require_auth
def get_anamnesis(user, patient_id):
    loaded, err = _assessment_with_answers(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    patient, catalog, answers = loaded
    evaluation = risk_engine.evaluate_patient(db.session, patient)
    return jsonify({
        "sections": [
            {"key": "stile_di_vita", "label": "Stile di vita"},
            {"key": "lavoro", "label": "Lavoro"},
            {"key": "storia_clinica", "label": "Storia clinica"},
        ],
        "questions": catalog,
        "answers": {str(qid): a for qid, a in answers.items()},
        "risk": risk_engine.serialize_assessment(evaluation),
    })


@bp.put("/patients/<int:patient_id>/anamnesis")
@require_auth
def put_answer(user, patient_id):
    """Upsert one answer (patient self-compile; doctor may correct)."""
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    body = request.get_json(silent=True) or {}
    question_id = body.get("question_id")
    value = (body.get("value") or "").strip()
    if not question_id or not value:
        return jsonify({"error": "question_id e value obbligatori"}), 400
    question = db.session.get(AnamnesisQuestion, int(question_id))
    if not question or not question.active:
        return jsonify({"error": "Domanda non trovata"}), 404
    if question.answer_type != "text" and len(value) > 300:
        return jsonify({"error": "Risposta troppo lunga"}), 400

    row = (
        db.session.query(AnamnesisAnswer)
        .filter_by(patient_id=patient.id, question_id=question.id)
        .first()
    )
    old_value = row.value if row else None
    if row:
        row.value = value
        row.answered_by = user.role
    else:
        row = AnamnesisAnswer(
            patient_id=patient.id, question_id=question.id,
            value=value, answered_by=user.role,
        )
        db.session.add(row)
        db.session.flush()

    # audit trail: record every change (who changed it is the caller's role here;
    # doctor corrections carry their user id)
    db.session.add(AnamnesisAnswerHistory(
        answer_id=row.id, patient_id=patient.id, question_id=question.id,
        old_value=old_value, new_value=value, answered_by=user.role,
        changed_by_user_id=user.id,
    ))

    ana_service.load_answer_meta(db.session)
    evaluation = risk_engine.evaluate_patient(db.session, patient)
    from api.patients import _persist_assessment
    db.session.add(_persist_assessment(patient, evaluation))
    db.session.commit()
    return jsonify({"ok": True, "risk": risk_engine.serialize_assessment(evaluation)})


@bp.get("/patients/<int:patient_id>/anamnesis/history")
@require_auth
def answer_history(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    rows = (
        db.session.query(AnamnesisAnswerHistory)
        .filter(AnamnesisAnswerHistory.patient_id == patient.id)
        .order_by(AnamnesisAnswerHistory.created_at.desc())
        .limit(100)
        .all()
    )
    return jsonify([
        {
            "question": db.session.get(AnamnesisQuestion, r.question_id).prompt,
            "old_value": r.old_value,
            "new_value": r.new_value,
            "answered_by": r.answered_by,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ])


@bp.get("/patients/<int:patient_id>/anamnesis/export")
@require_auth
def export_anamnesis(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    payload = ana_service.export_fhir_questionnaire_response(db.session, patient)
    return Response(
        json.dumps(payload, ensure_ascii=False, indent=2),
        mimetype="application/fhir+json",
        headers={"Content-Disposition": f"attachment; filename=anamnesis_paziente{patient.id}_fhir.json"},
    )
