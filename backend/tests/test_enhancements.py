"""Tests for the HANDOFF §3/§4/§5 additions: medications, notifications, GDPR,
triage drafts, report, encounter documentation and audit history."""
from datetime import date


def test_medications_crud(doctor, worker, _seed):
    pid = _seed["patient"]
    # seeded therapy row exists and the profile exposes it
    r = doctor.get(f"/api/patients/{pid}/medications")
    assert r.status_code == 200 and len(r.get_json()) == 1
    r = doctor.get(f"/api/patients/{pid}")
    assert r.get_json()["medications"][0]["name"] == "Metformina"

    r = doctor.post(f"/api/patients/{pid}/medications",
                    json={"name": "Lisinopril", "dosage": "10 mg", "schedule": "1x/die"})
    assert r.status_code == 201
    med_id = r.get_json()["id"]

    r = doctor.patch(f"/api/medications/{med_id}", json={"active": False})
    assert r.get_json()["active"] is False
    assert doctor.delete(f"/api/medications/{med_id}").status_code == 200

    # worker can read but not write
    assert worker.post(f"/api/patients/{pid}/medications",
                       json={"name": "Autoprescrizione"}).status_code == 403


def test_notifications_for_worker(worker):
    r = worker.get("/api/notifications")
    assert r.status_code == 200
    body = r.get_json()
    assert "items" in body and "unread_count" in body


def test_gdpr_export_and_anonymize(worker, doctor, _seed, app):
    pid = _seed["patient"]
    r = worker.get(f"/api/patients/{pid}/data-export")
    assert r.status_code == 200
    body = r.get_json()
    assert body["profile"]["last_name"] == "Prova"
    assert body["observations"]

    r = worker.delete("/api/me")
    assert r.status_code == 200

    with app.app_context():
        from extensions import db
        from models import Patient
        p = db.session.get(Patient, pid)
        assert p.first_name == "Utente"
        assert p.user.password_hash not in (None, "")


def test_anamnesis_audit_history(doctor, _seed):
    pid = _seed["patient"]
    anamnesis = doctor.get(f"/api/patients/{pid}/anamnesis").get_json()
    q = next(q for q in anamnesis["questions"] if q["code"] == "smoking")
    protective = next(o for o in q["options"] if o.get("protective"))
    doctor.put(f"/api/patients/{pid}/anamnesis",
               json={"question_id": q["id"], "value": protective["value"]})
    r = doctor.get(f"/api/patients/{pid}/anamnesis/history")
    assert r.status_code == 200
    history = r.get_json()
    assert history and history[0]["old_value"] == "Fumatore/a attuale"


def test_triage_draft_save_and_discard(doctor, _seed):
    r = doctor.post("/api/triage/drafts", json={
        "patient_id": _seed["patient"],
        "protocol_code": "tosse",
        "answers": {"q1": "no"},
    })
    assert r.status_code == 201
    drafts = doctor.get("/api/triage/drafts").get_json()
    assert len(drafts) == 1 and drafts[0]["answers"] == {"q1": "no"}

    # completing the same protocol supersedes the draft
    r = doctor.post("/api/triage/assessments", json={
        "patient_id": _seed["patient"], "protocol_code": "tosse",
        "answers": {"q1": "no", "q2": "no", "q3": "no", "q4": "no",
                    "q5": "no", "q6": "no", "q7": "sì"},
    })
    assert r.status_code == 201
    assert doctor.get("/api/triage/drafts").get_json() == []


def test_doctor_report(doctor, _seed):
    r = doctor.get("/api/doctor/report")
    assert r.status_code == 200
    rows = r.get_json()["rows"]
    assert rows and all("employer" in row and "workers" in row for row in rows)


def test_encounter_documentation(doctor, _seed, app):
    pid = _seed["patient"]
    r = doctor.post(f"/api/patients/{pid}/encounters", json={
        "kind": "followup",
        "notes": "Teleconsulto eseguito, paziente stabile.",
        "diagnosis": "Controllo glicemico",
    })
    assert r.status_code == 201
    from tests.test_api import test_doctor_dashboard_aggregates  # noqa: F401
    r = doctor.get(f"/api/patients/{pid}/encounters")
    assert any(e["notes"] == "Teleconsulto eseguito, paziente stabile." for e in r.get_json())


def test_appointment_completion_writes_encounter(doctor, _seed, app):
    pid = _seed["patient"]
    appt = doctor.post(f"/api/patients/{pid}/appointments", json={
        "kind": "visita_ambulatoriale", "reason": "Controllo",
        "scheduled_at": "2026-09-20T09:00:00Z",
    }).get_json()
    r = doctor.patch(f"/api/appointments/{appt['id']}",
                     json={"status": "completato", "clinical_note": "Esito regolare."})
    assert r.status_code == 200
    r = doctor.get(f"/api/patients/{pid}/encounters")
    assert any(e["notes"] == "Esito regolare." for e in r.get_json())


def test_chat_red_flag_interceptor(worker, _seed, app):
    """Emergency phrasings bypass the LLM, escalate the thread and open an
    immediate follow-up — QA-5 regression test."""
    pid = _seed["patient"]
    r = worker.post("/api/chat/threads", json={})
    assert r.status_code == 201
    tid = r.get_json()["id"]

    r = worker.post(f"/api/chat/threads/{tid}/messages",
                    json={"content": "Ho un dolore forte al petto in questo momento e mi sento mancare"})
    assert r.status_code == 201
    payload = r.get_json()
    assert payload["escalation"] is True
    assert payload["escalation_reason"] == "dolore al petto in corso"
    assert "118" in payload["message"]["content"]

    with app.app_context():
        from extensions import db
        from models import ChatThread, FollowUp
        t = db.session.get(ChatThread, tid)
        assert t.status == "waiting_operator"
        fu = db.session.query(FollowUp).filter_by(patient_id=pid).order_by(FollowUp.id.desc()).first()
        assert fu.reason.startswith("Emergenza da chat")
        assert fu.due_on == date.today()


def test_detect_emergency_patterns():
    from services.chat_safety import detect_emergency
    assert detect_emergency("ho un dolore al petto forte adesso") is not None
    assert detect_emergency("mi sento mancare") is not None
    assert detect_emergency("non riesco a respirare bene") is not None
    assert detect_emergency("ho la bocca storta da stamattina") is not None
    assert detect_emergency("mi fa male la schiena") is None
    assert detect_emergency("vorrei consigli sul cibo") is None
