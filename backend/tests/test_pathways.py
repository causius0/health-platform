"""Care pathway API tests: enrollment, step booking, auto-completion."""
from datetime import date, timedelta

from models import Appointment, CarePathwayStep


def _patient_pathways(doctor, seed):
    return doctor.get(f"/api/patients/{seed['patient']}/pathways")


def test_templates_catalogue(doctor):
    r = doctor.get("/api/pathways/templates", headers={})
    assert r.status_code == 200
    codes = [t["code"] for t in r.get_json()]
    assert {"prevenzione_diabete", "prevenzione_ipertensione",
            "screening_metabolico", "followup_post_triage"} <= set(codes)


def test_enroll_and_book_step(doctor, _seed, app):
    pid = _seed["patient"]
    r = doctor.post(f"/api/patients/{pid}/pathways", headers={},
                    json={"template_code": "screening_metabolico"})
    assert r.status_code == 201
    pathway = r.get_json()
    assert pathway["status"] == "attivo"
    assert len(pathway["steps"]) == 5
    assert all(s["status"] == "in_attesa" for s in pathway["steps"])

    # booking the metabolic panel creates an appointment and programs the step
    step = next(s for s in pathway["steps"] if s["kind"] == "screening")
    assert step["title"] == "Esami del sangue metabolici"
    r = doctor.post(f"/api/pathway-steps/{step['id']}/book", headers={}, json={})
    assert r.status_code == 201
    payload = r.get_json()
    assert payload["appointment"]["kind"] == "esame"
    step_after = next(s for s in payload["pathway"]["steps"] if s["id"] == step["id"])
    assert step_after["status"] == "programmato"
    assert step_after["appointment"] is not None

    # completing the appointment auto-completes the pathway step
    with app.app_context():
        from extensions import db
        appt = db.session.get(Appointment, payload["appointment"]["id"])
        appt_id = appt.id
    r = doctor.patch(f"/api/appointments/{appt_id}", headers={},
                     json={"status": "completato"})
    assert r.status_code == 200
    r = _patient_pathways(doctor, _seed)
    step_final = next(
        s for p in r.get_json() for s in p["steps"] if s["id"] == step["id"]
    )
    assert step_final["status"] == "completato"
    assert step_final["completed_on"] is not None


def test_patient_can_complete_but_not_enroll(doctor, worker, _seed):
    pid = _seed["patient"]
    r = worker.post(f"/api/patients/{pid}/pathways", headers={},
                    json={"template_code": "screening_metabolico"})
    assert r.status_code == 403

    # doctor enrolls, patient completes an education step
    pathway = doctor.post(f"/api/patients/{pid}/pathways", headers={},
                          json={"template_code": "screening_metabolico"}).get_json()
    edu = next(s for s in pathway["steps"] if s["kind"] == "educazione")
    r = worker.post(f"/api/pathway-steps/{edu['id']}/complete",
                    headers={}, json={"outcome": "Completato con l'operatore"})
    assert r.status_code == 200
    step_after = next(s for s in r.get_json()["steps"] if s["id"] == edu["id"])
    assert step_after["status"] == "completato"


def test_overdue_steps_flagged(doctor, _seed, app):
    pid = _seed["patient"]
    pathway = doctor.post(f"/api/patients/{pid}/pathways", headers={},
                          json={"template_code": "screening_metabolico"}).get_json()
    with app.app_context():
        from extensions import db
        step = db.session.get(CarePathwayStep, pathway["steps"][0]["id"])
        step.due_on = date.today() - timedelta(days=5)
        db.session.commit()
    pathways_now = _patient_pathways(doctor, _seed).get_json()
    states = [s["status"] for p in pathways_now for s in p["steps"]]
    assert "in_ritardo" in states
