"""Time-driven maintenance job for care pathways.

Run daily (cron / systemd timer / container sidecar):

    cd backend && ./venv/bin/python jobs.py

What it does:
  1. pathway steps past `due_on` and still pending → makes sure a safety-net
     follow-up call exists (deduplicated by patient + reason);
  2. reports overdue counts per worker for the operators' morning triage.

Idempotent: repeated runs create nothing new.
"""
from datetime import date, timedelta

from app import create_app
from extensions import db
from models import CarePathway, CarePathwayStep, FollowUp, Patient


def sweep_pathways() -> int:
    created = 0
    today = date.today()
    steps = (
        db.session.query(CarePathwayStep, CarePathway)
        .join(CarePathway, CarePathwayStep.pathway_id == CarePathway.id)
        .filter(CarePathway.status == "attivo", CarePathwayStep.status == "in_attesa")
        .all()
    )
    for step, pathway in steps:
        if step.due_on >= today:
            continue
        if step.kind == "misurazione":
            continue  # the worker records measurements; no call needed
        reason = f"Scaduto nel percorso «{pathway.template.name}»: {step.title}"
        exists = (
            db.session.query(FollowUp)
            .filter_by(patient_id=pathway.patient_id, reason=reason, status="pending")
            .first()
        )
        if exists:
            continue
        db.session.add(FollowUp(
            patient_id=pathway.patient_id,
            created_by_user_id=pathway.created_by_user_id,
            due_on=today + timedelta(days=2),
            reason=reason,
            channel="chiamata",
        ))
        created += 1
    db.session.commit()
    return created


def overdue_summary():
    today = date.today()
    rows = (
        db.session.query(CarePathwayStep, CarePathway, Patient)
        .join(CarePathway, CarePathwayStep.pathway_id == CarePathway.id)
        .join(Patient, CarePathway.patient_id == Patient.id)
        .filter(CarePathway.status == "attivo", CarePathwayStep.status == "in_attesa")
        .all()
    )
    overdue = [(s, p, w) for s, p, w in rows if s.due_on < today and s.kind != "misurazione"]
    for s, _p, w in overdue:
        print(f"  - {w.full_name}: {s.title} (scaduta dal {s.due_on.isoformat()})")
    return len(overdue)


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        n = sweep_pathways()
        print(f"Job percorsi: {n} follow-up di sicurezza creati")
        print(f"Tappe in ritardo a fin di report: {overdue_summary()}")
