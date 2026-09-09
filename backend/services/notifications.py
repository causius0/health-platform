"""Derived notifications: what needs attention now, for the worker and the doctor.

Computed from live data (no stored state to keep in sync): overdue/due pathway
steps, imminent appointments, pending follow-up calls and chat threads waiting
for an operator.
"""
from datetime import date, datetime, timedelta, timezone


def for_patient(session, patient) -> list:
    """Worker-facing notifications, most urgent first."""
    from models import (
        Appointment, CarePathway, CarePathwayStep, FollowUp,
    )
    from services.pathways import step_state

    today = date.today()
    out = []

    for pathway in session.query(CarePathway).filter_by(patient_id=patient.id, status="attivo"):
        for step in pathway.steps:
            state = step_state(step, today)
            if state == "completato":
                continue
            if state == "in_ritardo":
                out.append({
                    "severity": "critical",
                    "kind": "pathway",
                    "title": f"In ritardo: {step.title}",
                    "detail": f"Percorso «{pathway.template.name}» — scadenza {step.due_on.isoformat()}",
                    "link": "/portal/percorsi",
                    "date": step.due_on.isoformat(),
                })
            elif step.due_on <= today + timedelta(days=3):
                out.append({
                    "severity": "warning",
                    "kind": "pathway",
                    "title": f"Entro pochi giorni: {step.title}",
                    "detail": f"Percorso «{pathway.template.name}»",
                    "link": "/portal/percorsi",
                    "date": step.due_on.isoformat(),
                })

    for appt in session.query(Appointment).filter_by(patient_id=patient.id, status="confermato"):
        if appt.scheduled_at.date() <= today + timedelta(days=2):
            out.append({
                "severity": "info",
                "kind": "appointment",
                "title": f"Appuntamento {appt.scheduled_at.strftime('%d/%m %H:%M')}",
                "detail": appt.reason,
                "link": "/portal/appuntamenti",
                "date": appt.scheduled_at.date().isoformat(),
            })

    for fu in session.query(FollowUp).filter_by(patient_id=patient.id, status="pending"):
        if fu.due_on < today:
            out.append({
                "severity": "warning",
                "kind": "followup",
                "title": "Richiamo dell'operatore in ritardo",
                "detail": fu.reason,
                "link": "/portal/appuntamenti",
                "date": fu.due_on.isoformat(),
            })

    rank = {"critical": 0, "warning": 1, "info": 2}
    out.sort(key=lambda n: (rank[n["severity"]], n["date"]))
    return out


def for_doctor(session) -> list:
    """Operator-facing pings: overdue follow-ups and chats waiting too long."""
    from models import ChatThread, FollowUp, Patient

    out = []
    rows = (
        session.query(FollowUp, Patient)
        .join(Patient, FollowUp.patient_id == Patient.id)
        .filter(FollowUp.status == "pending")
        .all()
    )
    for fu, p in rows:
        if fu.due_on < date.today():
            out.append({
                "severity": "critical",
                "kind": "followup",
                "title": f"Follow-up in ritardo — {p.full_name}",
                "detail": fu.reason,
                "link": f"/studio?patient={p.id}",
                "date": fu.due_on.isoformat(),
            })

    cutoff = datetime.now(timezone.utc) - timedelta(hours=12)
    threads = (
        session.query(ChatThread, Patient)
        .join(Patient, ChatThread.patient_id == Patient.id)
        .filter(ChatThread.kind == "coach", ChatThread.status == "waiting_operator")
        .all()
    )
    for t, p in threads:
        if t.updated_at < cutoff:
            out.append({
                "severity": "warning",
                "kind": "chat",
                "title": f"Richiesta operatore in attesa — {p.full_name}",
                "detail": t.subject or "Conversazione senza presa in carico da oltre 12 ore",
                "link": "/studio",
                "date": t.updated_at.date().isoformat(),
            })
    return out
