"""Builds the Italian clinical context string that grounds the chat assistant.

Kept deliberately compact: the LLM sees profile, employment, current risk
stratification (with active and protective factors), anamnesis, latest
observations, recent encounters and upcoming care — everything a coach or a
clinician assistant needs, nothing more.
"""

from models import (
    Appointment,
    Encounter,
    Observation,
    Patient,
    WellbeingAssessment,
)
from services import risk_engine
from services.risk_engine import anamnesis_answers, latest_observations


def _fmt_obs(row: Observation) -> str:
    return f"{row.label} {row.value:g} {row.unit}".strip()


def build_patient_context(session, patient: Patient, role: str) -> str:
    obs = latest_observations(session, patient.id, recency_days=180)
    evaluation = risk_engine.evaluate_patient(session, patient)

    lines = [f"PAZIENTE: {patient.full_name}"]
    age = evaluation.get("age")
    if age:
        lines.append(f"Età: {age} anni" + (f", sesso {'M' if patient.sex == 'M' else 'F'}" if patient.sex else ""))
    if patient.job_title or patient.employer:
        lines.append(f"Lavoro: {patient.job_title or '—'} @ {patient.employer or '—'}"
                     + (f" (orario: {patient.work_pattern})" if patient.work_pattern else ""))
    if patient.primary_diagnosis:
        lines.append(f"Diagnosi principale: {patient.primary_diagnosis}")
    meds = [
        f"{m.name} {m.dosage or ''} {m.schedule or ''}".strip()
        for m in patient.therapies if m.active
    ]
    if meds:
        lines.append("Terapia in corso: " + "; ".join(meds))

    strat = risk_engine.serialize_assessment(evaluation)
    lines.append(
        f"STRATIFICAZIONE DEL RISCHIO: livello {strat['level'].upper()} "
        f"({strat['risk_count']} fattori di rischio attivi, {strat['protective_count']} fattori protettivi)"
    )
    if evaluation["risks"]:
        lines.append("Fattori di rischio attivi: " + "; ".join(
            f"{c['label']} ({c['value_text']})" for c in evaluation["risks"]))
    if evaluation["protectives"]:
        lines.append("Fattori protettivi confermati (riconosci e incoraggia): " + "; ".join(
            c["label"] for c in evaluation["protectives"]))

    answers = anamnesis_answers(session, patient.id)
    if answers:
        lines.append("ANAMNESI (stile di vita/lavoro): " + "; ".join(f"{k}={v}" for k, v in answers.items()))

    if obs:
        lines.append("ULTIME MISURAZIONI (180 giorni): " + "; ".join(_fmt_obs(o) for o in obs.values()))

    encounters = (
        session.query(Encounter)
        .filter(Encounter.patient_id == patient.id)
        .order_by(Encounter.encounter_date.desc())
        .limit(3)
        .all()
    )
    if encounters:
        lines.append("ULTIMI INCONTRI CLINICI: " + "; ".join(
            f"{e.encounter_date.isoformat()} ({e.kind}): {e.diagnosis or e.notes or ''}"
            for e in encounters))

    upcoming = (
        session.query(Appointment)
        .filter(Appointment.patient_id == patient.id,
                Appointment.status.in_(["proposto", "confermato"]))
        .order_by(Appointment.scheduled_at)
        .all()
    )
    if upcoming:
        lines.append("PROSSIMI APPUNTAMENTI: " + "; ".join(
            f"{a.scheduled_at.strftime('%d/%m %H:%M')} {a.kind}" for a in upcoming))

    last_wellbeing = (
        session.query(WellbeingAssessment)
        .filter(WellbeingAssessment.patient_id == patient.id)
        .order_by(WellbeingAssessment.taken_on.desc())
        .limit(4)
        .all()
    )
    if last_wellbeing:
        lines.append("BENESSERE (ultimi questionari): " + "; ".join(
            f"{w.instrument}={w.score:g} ({w.category})" if w.score is not None
            else f"{w.instrument} ({w.category})" for w in last_wellbeing))

    if role == "doctor":
        lines.append(
            "ISTRUZIONI CONTESTO: stai assistendo il medico; usa tono professionale e tecnico."
        )
    else:
        lines.append(
            "ISTRUZIONI CONTESTO: stai assistendo il lavoratore; tono semplice, incoraggiante, mai allarmista."
        )
    return "\n".join(lines)


def build_doctor_overview(session, doctor_user_id: int) -> str:
    patients = session.query(Patient).filter(Patient.assigned_doctor_id.isnot(None)).all()
    lines = ["PANORAMICA CASISTICO (tutti i lavoratori in carico):"]
    for p in patients:
        evaluation = risk_engine.evaluate_patient(session, p)
        key_risks = "; ".join(c["label"] for c in evaluation["risks"][:3]) or "nessuno"
        lines.append(
            f"- {p.full_name} — livello {evaluation['level'].upper()} "
            f"({evaluation['risk_count']} rischi): {key_risks}"
        )
    lines.append("ISTRUZIONI: aiuta il medico a priorizzare; per il dettaglio suggerisci di selezionare il singolo lavoratore.")
    return "\n".join(lines)
