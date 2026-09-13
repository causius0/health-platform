"""API integration tests: auth, anamnesis→risk loop, monitoring, triage, chat handoff."""
from datetime import date

import json


def test_health(client):
    assert client.get("/api/health").status_code == 200


def test_login_rejects_bad_credentials(client):
    r = client.post("/api/login", json={"username": "doctor", "password": "wrong"})
    assert r.status_code == 401


def test_login_rejects_overlong_password(client):
    # bcrypt raises beyond 72 bytes; the API must answer 401, not 500
    r = client.post("/api/login", json={"username": "doctor", "password": "x" * 300})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/me").status_code == 401


def test_patient_profile_access_rules(doctor, worker, _seed):
    pid = _seed["patient"]
    r = doctor.get(f"/api/patients/{pid}")
    assert r.status_code == 200
    body = r.get_json()
    assert body["full_name"] == "Anna Prova"
    assert body["primary_diagnosis"].startswith("Diabete")
    assert body["assigned_doctor"] == "dott. Test Medico"

    # the owner reads her own record; another patient's record is off-limits
    own = worker.get(f"/api/patients/{pid}", headers={})
    assert own.status_code == 200
    foreign = worker.get(f"/api/patients/{_seed['other']}", headers={})
    assert foreign.status_code == 403


def test_anamnesis_roundtrip_changes_risk(doctor, _seed, app):
    pid = _seed["patient"]
    r = doctor.get(f"/api/patients/{pid}/anamnesis", headers={})
    assert r.status_code == 200
    body = r.get_json()
    assert len(body["questions"]) >= 12

    risk_before = body["risk"]["risk_count"]
    smoking_q = next(q for q in body["questions"] if q["code"] == "smoking")
    quit_option = next(o for o in smoking_q["options"] if o.get("protective"))

    # switching smoking → ex-smoker (protective) must reduce the risk count
    r = doctor.put(
        f"/api/patients/{pid}/anamnesis",
        headers={},
        json={"question_id": smoking_q["id"], "value": quit_option["value"]},
    )
    assert r.status_code == 200
    risk_after = r.get_json()["risk"]["risk_count"]
    assert risk_after == risk_before - 1

    with app.app_context():
        from extensions import db
        from models import RiskAssessment

        assert RiskAssessment.query.filter_by(patient_id=pid).count() >= 1


def test_home_observation_triggers_reassessment(worker, _seed, app):
    pid = _seed["patient"]
    r = worker.post(
        f"/api/patients/{pid}/observations",
        headers={},
        json={"code": "bp_systolic", "value": 168, "source": "patient_home"},
    )
    assert r.status_code == 201
    payload = r.get_json()
    assert payload["observation"]["source"] == "patient_home"

    # BP ≥ 160 + existing risks ⇒ alto with a critical component
    risk = payload["risk"]
    assert risk["level"] == "alto"
    assert risk["has_critical"] is True

    with app.app_context():
        from extensions import db
        from models import RiskAssessment

        # the fresh observation must have triggered exactly one persisted assessment
        assert RiskAssessment.query.filter_by(patient_id=pid).count() == 1


def test_triage_flow_books_appointment(doctor, _seed, app):
    pid = _seed["patient"]
    r = doctor.post(
        "/api/triage/assessments",
        headers={},
        json={
            "patient_id": pid,
            "protocol_code": "algie_addominali",
            "answers": {"q1": "no", "q2": "no", "q3": "no",
                        "q4": "sì", "q5": "no", "q6": "no", "q7": "no"},
        },
    )
    assert r.status_code == 201
    payload = r.get_json()
    assert payload["tier"] == "arancione"
    assert payload["appointment"] is not None
    assert payload["appointment"]["priority"] == "urgente"

    with app.app_context():
        from extensions import db
        from models import Appointment

        appt = db.session.get(Appointment, payload["appointment"]["id"])
        assert appt.created_via == "triage"
        assert appt.patient_id == pid


def test_green_triage_creates_safety_net_followup(doctor, _seed, app):
    pid = _seed["patient"]
    r = doctor.post(
        "/api/triage/assessments",
        headers={},
        json={
            "patient_id": pid,
            "protocol_code": "cefalea",
            "answers": {"q1": "no", "q2": "no", "q3": "no", "q4": "no", "q5": "no", "q6": "sì"},
        },
    )
    assert r.status_code == 201
    payload = r.get_json()
    assert payload["tier"] == "verde"
    assert payload["follow_up"] is not None


def test_chat_handoff_lifecycle(worker, doctor, _seed, app):
    pid = _seed["patient"]
    r = worker.post("/api/chat/threads", headers={}, json={})
    assert r.status_code == 201
    thread_id = r.get_json()["id"]

    r = worker.post(f"/api/chat/threads/{thread_id}/messages",
                    headers={}, json={"content": "Ciao, mi sento stanco."})
    assert r.status_code == 201
    reply = r.get_json()["message"]
    assert reply["sender"] == "bot"

    r = worker.post(f"/api/chat/threads/{thread_id}/escalate",
                    headers={}, json={"subject": "Serve un operatore"})
    assert r.status_code == 200
    assert r.get_json()["status"] == "waiting_operator"

    # doctor sees it in the queue and claims it
    r = doctor.get("/api/chat/threads", headers={})
    assert any(t["id"] == thread_id for t in r.get_json())
    r = doctor.post(f"/api/chat/threads/{thread_id}/claim", headers={})
    assert r.get_json()["status"] == "with_operator"

    r = doctor.post(f"/api/chat/threads/{thread_id}/messages",
                    headers={}, json={"content": "Buongiorno, la chiamo entro un'ora."})
    assert r.status_code == 201
    # the doctor message is stored, then the clinical assistant answers
    assert r.get_json()["message"]["sender"] == "bot"

    r = doctor.post(f"/api/chat/threads/{thread_id}/close", headers={})
    assert r.get_json()["status"] == "bot"

    # privacy: patient can delete their own thread
    r = worker.delete(f"/api/chat/threads/{thread_id}", headers={})
    assert r.status_code == 200


def test_wellbeing_submission_scores(worker, _seed):
    pid = _seed["patient"]
    answers = {f"q{i}": 4 for i in range(1, 8)}
    r = worker.post(f"/api/patients/{pid}/wellbeing",
                    headers={},
                    json={"instrument": "wemwbs7", "answers": answers})
    assert r.status_code == 201
    assert r.get_json()["score"] == 28

    bad = worker.post(f"/api/patients/{pid}/wellbeing",
                      headers={},
                      json={"instrument": "wemwbs7", "answers": {"q1": 9}})
    assert bad.status_code == 422


def test_doctor_dashboard_aggregates(doctor):
    r = doctor.get("/api/doctor/dashboard", headers={})
    assert r.status_code == 200
    body = r.get_json()
    assert body["patients"]
    assert all("risk_level" in p for p in body["patients"])


def test_fhir_export_contains_answers(doctor, _seed):
    pid = _seed["patient"]
    r = doctor.get(f"/api/patients/{pid}/anamnesis/export", headers={})
    assert r.status_code == 200
    assert "fhir" in r.content_type
    payload = json.loads(r.data)
    assert payload["resourceType"] == "QuestionnaireResponse"
    assert payload["item"]
