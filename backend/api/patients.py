"""Patient profile, clinical observations (incl. home monitoring) and risk."""
import json
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from extensions import db
from models import (
    Appointment,
    Doctor,
    Encounter,
    Observation,
    Patient,
    PatientMedication,
    RiskAssessment,
    METRIC_CODES,
)
from api.helpers import get_patient_for, parse_date, require_auth, require_role
from services import risk_engine

bp = Blueprint("patients", __name__, url_prefix="/api")


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------
def patient_summary(patient: Patient, evaluation: dict) -> dict:
    return {
        "id": patient.id,
        "full_name": patient.full_name,
        "age": evaluation.get("age"),
        "sex": patient.sex,
        "primary_diagnosis": patient.primary_diagnosis,
        "employer": patient.employer,
        "job_title": patient.job_title,
        "risk_level": evaluation["level"],
        "risk_count": evaluation["risk_count"],
        "protective_count": evaluation["protective_count"],
        "has_critical": evaluation["has_critical"],
    }


def observation_payload(row: Observation) -> dict:
    return {
        "id": row.id,
        "code": row.code,
        "label": row.label,
        "value": row.value,
        "unit": row.unit,
        "reference_range": METRIC_CODES.get(row.code, ("", "", ""))[2],
        "source": row.source,
        "taken_on": row.taken_on.isoformat(),
        "notes": row.notes,
    }


# ---------------------------------------------------------------------------
# Doctor caseload
# ---------------------------------------------------------------------------
@bp.get("/doctor/patients")
@require_role("doctor")
def doctor_patients(user):
    patients = db.session.query(Patient).order_by(Patient.last_name).all()
    out = []
    for p in patients:
        evaluation = risk_engine.evaluate_patient(db.session, p)
        last_enc = (
            db.session.query(Encounter)
            .filter(Encounter.patient_id == p.id)
            .order_by(Encounter.encounter_date.desc())
            .first()
        )
        next_appt = (
            db.session.query(Appointment)
            .filter(Appointment.patient_id == p.id,
                    Appointment.status.in_(["proposto", "confermato"]),
                    Appointment.scheduled_at >= datetime.now(timezone.utc))
            .order_by(Appointment.scheduled_at)
            .first()
        )
        entry = patient_summary(p, evaluation)
        entry["last_encounter"] = last_enc.encounter_date.isoformat() if last_enc else None
        entry["next_appointment"] = next_appt.scheduled_at.isoformat() if next_appt else None
        out.append(entry)
    return jsonify(out)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@bp.get("/patients/<int:patient_id>")
@require_auth
def patient_profile(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    evaluation = risk_engine.evaluate_patient(db.session, patient)
    data = patient_summary(patient, evaluation)
    data.update({
        "birth_date": patient.birth_date.isoformat() if patient.birth_date else None,
        "fiscal_code": patient.fiscal_code,
        "phone": patient.phone,
        "height_cm": patient.height_cm,
        "weight_kg": _latest_value(db.session, patient.id, "weight"),
        "bmi": risk_engine._current_bmi(patient, risk_engine.latest_observations(db.session, patient.id)),
        "comorbidities": json.loads(patient.comorbidities or "[]"),
        "medications": [
            {"id": m.id, "name": m.name, "dosage": m.dosage,
             "schedule": m.schedule, "active": m.active}
            for m in db.session.query(PatientMedication)
            .filter_by(patient_id=patient.id)
            .order_by(PatientMedication.active.desc(), PatientMedication.name)
        ],
        "work_pattern": patient.work_pattern,
        "enrolled_on": patient.enrolled_on.isoformat() if patient.enrolled_on else None,
        "assigned_doctor": (
            f"dott. {patient.assigned_doctor.first_name} {patient.assigned_doctor.last_name}"
            if patient.assigned_doctor else None
        ),
        "recommendations": evaluation["recommendations"],
    })
    return jsonify(data)


def _latest_value(session, patient_id, code):
    row = (
        session.query(Observation)
        .filter(Observation.patient_id == patient_id, Observation.code == code)
        .order_by(Observation.taken_on.desc(), Observation.id.desc())
        .first()
    )
    return row.value if row else None


# ---------------------------------------------------------------------------
# Observations (labs, clinic vitals, home measurements)
# ---------------------------------------------------------------------------
@bp.get("/patients/<int:patient_id>/observations")
@require_auth
def patient_observations(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    months = min(int(request.args.get("months", 12)), 36)
    since = date.today() - timedelta(days=30 * months)
    rows = (
        db.session.query(Observation)
        .filter(Observation.patient_id == patient.id, Observation.taken_on >= since)
        .order_by(Observation.taken_on.desc(), Observation.id.desc())
        .all()
    )
    return jsonify([observation_payload(r) for r in rows])


VALID_SOURCES = {"lab", "clinic", "patient_home"}


@bp.post("/patients/<int:patient_id>/observations")
@require_auth
def add_observation(user, patient_id):
    """Patients record home measurements (remote monitoring); doctors record
    clinic/lab values. Every new value triggers a fresh risk assessment that
    is persisted for audit."""
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404

    body = request.get_json(silent=True) or {}
    code = body.get("code", "")
    if code not in METRIC_CODES:
        return jsonify({"error": f"Metrica non riconosciuta: {code}"}), 400
    try:
        value = float(body.get("value"))
    except (TypeError, ValueError):
        return jsonify({"error": "Valore numerico obbligatorio"}), 400
    taken_on = parse_date(body.get("taken_on"), "data misurazione") or date.today()
    if taken_on > date.today() + timedelta(days=1):
        return jsonify({"error": "La data non può essere futura"}), 400

    source = body.get("source") or ("patient_home" if user.role == "patient" else "clinic")
    if source not in VALID_SOURCES:
        return jsonify({"error": "Sorgente non valida"}), 400

    row = Observation(
        patient_id=patient.id, code=code, value=value, source=source,
        taken_on=taken_on, notes=body.get("notes"),
    )
    db.session.add(row)

    # Persist a new assessment so the audit trail reflects the new data
    evaluation = risk_engine.evaluate_patient(db.session, patient)
    db.session.add(_persist_assessment(patient, evaluation))
    db.session.commit()
    return jsonify({
        "observation": observation_payload(row),
        "risk": risk_engine.serialize_assessment(evaluation),
    }), 201


@bp.get("/patients/<int:patient_id>/encounters")
@require_auth
def patient_encounters(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    rows = (
        db.session.query(Encounter)
        .filter(Encounter.patient_id == patient.id)
        .order_by(Encounter.encounter_date.desc())
        .all()
    )
    return jsonify([
        {
            "id": e.id,
            "encounter_date": e.encounter_date.isoformat(),
            "kind": e.kind,
            "facility": e.facility,
            "notes": e.notes,
            "diagnosis": e.diagnosis,
        }
        for e in rows
    ])


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------
def _persist_assessment(patient: Patient, evaluation: dict) -> RiskAssessment:
    return RiskAssessment(
        patient_id=patient.id,
        model_version=evaluation["model_version"],
        level=evaluation["level"],
        risk_count=evaluation["risk_count"],
        protective_count=evaluation["protective_count"],
        components=json.dumps(evaluation["components"]),
        recommendations=json.dumps(evaluation["recommendations"]),
    )


@bp.get("/patients/<int:patient_id>/risk")
@require_auth
def get_risk(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    evaluation = risk_engine.evaluate_patient(db.session, patient)
    return jsonify(risk_engine.serialize_assessment(evaluation))


@bp.post("/patients/<int:patient_id>/risk/recompute")
@require_role("doctor")
def recompute_risk(user, patient_id):
    patient = db.session.get(Patient, patient_id)
    if not patient:
        return jsonify({"error": "Paziente non trovato"}), 404
    evaluation = risk_engine.evaluate_patient(db.session, patient)
    db.session.add(_persist_assessment(patient, evaluation))
    db.session.commit()
    return jsonify(risk_engine.serialize_assessment(evaluation))


@bp.get("/patients/<int:patient_id>/risk/history")
@require_auth
def risk_history(user, patient_id):
    patient, err = get_patient_for(user, patient_id)
    if err:
        return jsonify({"error": err}), 403 if err == "Permesso negato" else 404
    rows = (
        db.session.query(RiskAssessment)
        .filter(RiskAssessment.patient_id == patient.id)
        .order_by(RiskAssessment.computed_at.desc())
        .limit(30)
        .all()
    )
    return jsonify([
        {
            "computed_at": r.computed_at.isoformat(),
            "level": r.level,
            "risk_count": r.risk_count,
            "protective_count": r.protective_count,
            "model_version": r.model_version,
        }
        for r in rows
    ])
