"""API helpers: role guards, access checks, serialization."""
from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from extensions import db
from models import Doctor, Patient, User


def current_user() -> User | None:
    verify_jwt_in_request()
    uid = get_jwt_identity()
    return db.session.get(User, int(uid))


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({"error": "Utente non trovato"}), 401
        return fn(user, *args, **kwargs)
    return wrapper


def require_role(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify({"error": "Utente non trovato"}), 401
            if user.role not in roles:
                return jsonify({"error": "Permesso negato"}), 403
            return fn(user, *args, **kwargs)
        return wrapper
    return decorator


def get_patient_for(user: User, patient_id: int) -> tuple[Patient | None, str | None]:
    """Fetch a patient enforcing role access. Returns (patient, error)."""
    patient = db.session.get(Patient, patient_id)
    if not patient:
        return None, "Paziente non trovato"
    if user.role == "patient" and patient.user_id != user.id:
        return None, "Permesso negato"
    return patient, None


def user_payload(user: User) -> dict:
    payload = {"id": user.id, "username": user.username, "role": user.role}
    if user.role == "doctor" and user.doctor_profile:
        d = user.doctor_profile
        payload.update({"doctor_id": d.id, "full_name": f"dott. {d.first_name} {d.last_name}",
                        "specialization": d.specialization})
    if user.role == "patient" and user.patient_profile:
        p = user.patient_profile
        payload.update({"patient_id": p.id, "full_name": p.full_name})
    return payload


def json_list(rows):
    return jsonify(rows) if not isinstance(rows, tuple) else rows


def parse_date(value, field="data"):
    from datetime import date, datetime

    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
        except ValueError:
            raise BadRequest(f"Formato di {field} non valido (ISO atteso)")


def parse_datetime(value, field="data/ora"):
    from datetime import datetime

    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            from datetime import timezone
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        raise BadRequest(f"Formato di {field} non valido (ISO atteso)")


class BadRequest(Exception):
    def __init__(self, message):
        self.message = message


def register_error_handlers(app):
    @app.errorhandler(BadRequest)
    def handle_bad_request(exc):
        return jsonify({"error": exc.message}), 400

    @app.errorhandler(404)
    def handle_404(_):
        return jsonify({"error": "Risorsa non trovata"}), 404

    @app.errorhandler(429)
    def handle_429(_):
        return jsonify({"error": "Troppe richieste: riprova più tardi."}), 429

    @app.errorhandler(500)
    def handle_500(_):
        db.session.rollback()
        return jsonify({"error": "Errore interno del server"}), 500
