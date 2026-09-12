"""Test fixtures: dedicated test database, app, client, minimal clinical data."""
import os
import sys
from pathlib import Path

import bcrypt
import psycopg
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from config import Config  # noqa: E402  (needs sys.path first)

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://health:health@localhost:5432/health_platform_test",
)
ADMIN_URL = "postgresql://health:health@localhost:5432/postgres"


def _ensure_test_database():
    dbname = TEST_DB_URL.rsplit("/", 1)[1]
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)
        ).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{dbname}"')


_ensure_test_database()


class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = TEST_DB_URL
    JWT_SECRET_KEY = "test-secret-key-0123456789abcdef0123456789abcdef"
    JWT_ACCESS_TOKEN_EXPIRES = 86400
    CORS_ORIGINS = ["http://localhost:5173"]
    LLM_API_KEY = ""  # force the deterministic fallback in tests
    LLM_MODEL = "test-model"
    LLM_BASE_URL = "http://localhost:1"
    JSON_AS_ASCII = False
    TESTING = True
    RATELIMIT_ENABLED = False


@pytest.fixture(scope="session")
def app():
    from app import create_app

    application = create_app(TestConfig)
    yield application


@pytest.fixture()
def _seed(app):
    """Fresh baseline data per test (doctor + two patients with labs/anamnesis)."""
    import json
    from datetime import date, timedelta

    with app.app_context():
        from extensions import db
        from models import (
            AnamnesisAnswer, AnamnesisQuestion, Doctor, Encounter, Observation,
            Patient, User,
        )
        from services import anamnesis as ana_service

        for table in ("observations", "encounters", "anamnesis_answers",
                      "anamnesis_questions", "risk_assessments", "chat_messages",
                      "chat_threads", "triage_assessments", "care_pathway_steps",
                      "care_pathways", "appointments", "follow_ups",
                      "patients", "doctors", "users"):
            db.session.execute(db.text(f"DELETE FROM {table}"))
        db.session.commit()
        ana_service.ensure_catalogue(db.session)
        ana_service.load_answer_meta(db.session)

        pwd = bcrypt.hashpw(b"test-password", bcrypt.gensalt()).decode()

        doctor_user = User(username="doctor", password_hash=pwd, role="doctor")
        db.session.add(doctor_user)
        patient_user = User(username="patient", password_hash=pwd, role="patient")
        other_user = User(username="patient_other", password_hash=pwd, role="patient")
        db.session.add_all([patient_user, other_user])
        db.session.flush()

        doctor = Doctor(user_id=doctor_user.id, first_name="Test", last_name="Medico")
        db.session.add(doctor)
        db.session.flush()

        patient = Patient(
            user_id=patient_user.id, first_name="Anna", last_name="Prova",
            birth_date=date(1980, 1, 1), sex="F", height_cm=165,
            primary_diagnosis="Diabete mellito tipo 2",
            assigned_doctor_id=doctor.id,
        )
        other = Patient(
            user_id=other_user.id, first_name="Altra", last_name="Persona",
            birth_date=date(1990, 1, 1), sex="M",
        )
        db.session.add_all([patient, other])
        db.session.flush()

        from models import PatientMedication
        db.session.add(PatientMedication(
            patient_id=patient.id, name="Metformina", dosage="850 mg", schedule="2x/die",
        ))

        today = date.today()
        for delta, hba1c, sys_bp in ((90, 8.2, 146), (30, 7.8, 142)):
            enc = Encounter(patient_id=patient.id, encounter_date=today - timedelta(days=delta),
                            kind="controllo")
            db.session.add(enc)
            db.session.flush()
            db.session.add(Observation(patient_id=patient.id, encounter_id=enc.id,
                                       code="hba1c", value=hba1c, source="lab",
                                       taken_on=today - timedelta(days=delta)))
            db.session.add(Observation(patient_id=patient.id, encounter_id=enc.id,
                                       code="bp_systolic", value=sys_bp, source="clinic",
                                       taken_on=today - timedelta(days=delta)))
            db.session.add(Observation(patient_id=patient.id, encounter_id=enc.id,
                                       code="bp_diastolic", value=88, source="clinic",
                                       taken_on=today - timedelta(days=delta)))

        questions = {q.code: q for q in AnamnesisQuestion.query.all()}
        db.session.add(AnamnesisAnswer(
            patient_id=patient.id, question_id=questions["smoking"].id,
            value="Fumatore/a attuale", answered_by="patient",
        ))
        db.session.commit()

        ids = {"patient": patient.id, "other": other.id,
               "doctor_user": doctor_user.id, "patient_user": patient_user.id}
    return ids


@pytest.fixture
def client(app, _seed):
    return app.test_client()


class ApiClient:
    """Test client wrapper that injects the CSRF header on unsafe methods."""

    def __init__(self, client, csrf_token):
        self._client = client
        self._csrf = csrf_token

    def _kw(self, kwargs):
        headers = dict(kwargs.pop("headers", None) or {})
        headers["X-CSRF-TOKEN"] = self._csrf
        kwargs["headers"] = headers
        return kwargs

    def get(self, path, **kw): return self._client.get(path, **self._kw(kw))
    def post(self, path, **kw): return self._client.post(path, **self._kw(kw))
    def put(self, path, **kw): return self._client.put(path, **self._kw(kw))
    def patch(self, path, **kw): return self._client.patch(path, **self._kw(kw))
    def delete(self, path, **kw): return self._client.delete(path, **self._kw(kw))


def _login(app, _seed, username):
    c = app.test_client()
    r = c.post("/api/login", json={"username": username, "password": "test-password"})
    assert r.status_code == 200, r.data
    return ApiClient(c, r.get_json()["csrf_token"])


@pytest.fixture
def doctor(app, _seed):
    """API client authenticated as the doctor (cookie session + CSRF header)."""
    return _login(app, _seed, "doctor")


@pytest.fixture
def worker(app, _seed):
    """API client authenticated as the patient."""
    return _login(app, _seed, "patient")
