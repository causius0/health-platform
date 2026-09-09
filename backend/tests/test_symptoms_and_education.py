"""Tests for the review implementations: symptom check-in, education, pathway
suggestions, lab request, dashboard wiring."""
import json
from datetime import date


def test_symptom_questions_catalogue(worker):
    r = worker.get("/api/symptoms/questions")
    assert r.status_code == 200
    ids = [q["id"] for q in r.get_json()]
    assert {"fever", "cough", "dyspnea", "chest_pain", "contact", "severe_other"} == set(ids)


def test_symptom_green_checkin(worker, _seed):
    pid = _seed["patient"]
    answers = {"fever": "no", "cough": "no", "dyspnea": "no",
               "chest_pain": "no", "contact": "no", "severe_other": "no"}
    r = worker.post(f"/api/patients/{pid}/symptom-checkins", json={"answers": answers})
    assert r.status_code == 201
    payload = r.get_json()
    assert payload["tier"] == "verde"
    assert payload["operator_alerted"] is False
    assert payload["followup_scheduled"] is False


def test_symptom_red_creates_urgent_followup(worker, _seed, app):
    pid = _seed["patient"]
    answers = {"fever": "alta", "cough": "secca", "dyspnea": "grave",
               "chest_pain": "no", "contact": "no", "severe_other": "no"}
    r = worker.post(f"/api/patients/{pid}/symptom-checkins", json={"answers": answers})
    assert r.status_code == 201
    payload = r.get_json()
    assert payload["tier"] == "rosso"
    assert payload["followup_scheduled"] is True

    with app.app_context():
        from extensions import db
        from models import FollowUp
        fu = db.session.query(FollowUp).filter_by(patient_id=pid).order_by(FollowUp.id.desc()).first()
        assert fu.reason.startswith("Check-in sintomi rosso")
        assert fu.due_on == date.today()


def test_symptom_orange_from_contact_plus_fever(worker, _seed):
    pid = _seed["patient"]
    answers = {"fever": "leggera", "cough": "secca", "dyspnea": "no",
               "chest_pain": "no", "contact": "sì", "severe_other": "no"}
    r = worker.post(f"/api/patients/{pid}/symptom-checkins", json={"answers": answers})
    payload = r.get_json()
    assert payload["tier"] == "arancione"
    assert payload["operator_alerted"] is True


def test_symptom_invalid_answers_rejected(worker, _seed):
    pid = _seed["patient"]
    r = worker.post(f"/api/patients/{pid}/symptom-checkins",
                    json={"answers": {"fever": "tantissima"}})
    assert r.status_code == 422


def test_symptom_history(worker, _seed):
    pid = _seed["patient"]
    worker.post(f"/api/patients/{pid}/symptom-checkins", json={"answers": {
        "fever": "no", "cough": "no", "dyspnea": "no",
        "chest_pain": "no", "contact": "no", "severe_other": "no"}})
    r = worker.get(f"/api/patients/{pid}/symptom-checkins")
    assert r.status_code == 200
    rows = r.get_json()
    assert rows and rows[0]["tier"] == "verde"


def test_dashboard_includes_symptom_checkins(doctor, _seed):
    r = doctor.get("/api/doctor/dashboard")
    assert r.status_code == 200
    body = r.get_json()
    assert "recent_symptom_checkins" in body
    assert "operator_notifications" in body


def test_pathway_suggestions_by_diagnosis(doctor, _seed):
    pid = _seed["patient"]
    r = doctor.get(f"/api/patients/{pid}/pathways/suggestions")
    assert r.status_code == 200
    codes = [s["code"] for s in r.get_json()]
    assert "screening_metabolico" in codes  # the seeded worker has active risks


def test_mars5_instrument(worker, _seed):
    pid = _seed["patient"]
    instruments = worker.get("/api/wellbeing/instruments").get_json()
    assert any(i["instrument"] == "mars5" for i in instruments)
    r = worker.post(f"/api/patients/{pid}/wellbeing",
                    json={"instrument": "mars5",
                          "answers": {"q1": 4, "q2": 5, "q3": 4, "q4": 4, "q5": 5}})
    assert r.status_code == 201
    assert r.get_json()["score"] == 4.4


def test_education_library(worker):
    r = worker.get("/api/education")
    assert r.status_code == 200
    articles = r.get_json()
    assert len(articles) >= 8
    areas = {a["area"] for a in articles}
    assert {"attività fisica", "alimentazione", "sonno", "stress"} <= areas

    detail = worker.get("/api/education/attivita_fisica_oms").get_json()
    assert detail["body"] and detail["tips"]


def test_lab_request_print_document(doctor, worker, _seed):
    pid = _seed["patient"]
    r = doctor.get(f"/api/patients/{pid}/lab-request?tests=hba1c,ldl")
    assert r.status_code == 200
    html = r.data.decode()
    assert "Richiesta di esami di laboratorio" in html
    assert "Emoglobina glicata" in html
    assert "Anna Prova" in html

    r_empty = doctor.get(f"/api/patients/{pid}/lab-request")
    assert r_empty.status_code == 400

    # worker cannot issue lab requests
    r_worker = worker.get(f"/api/patients/{pid}/lab-request?tests=hba1c")
    assert r_worker.status_code == 403
