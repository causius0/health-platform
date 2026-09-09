"""Care pathways: standard prevention / screening / follow-up iter catalogues.

Templates are data (like the anamnesis catalogue): enrolling a worker instantiates
one `CarePathwayStep` per template step, with `due_on` derived from the enrolment
date + offset. Each step kind maps to an obvious CTA in the UI:

    misurazione → "Registra" (home observation)      screening  → "Prenota esame" / "Segna effettuato"
    visita      → "Prenota visita"                   educazione → "Segna completato"
    richiamo    → "Programma richiamo" (operator)

Completing a booked appointment automatically completes the linked step, so the
pathway reflects reality without double bookkeeping.
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models import (
    CarePathway,
    CarePathwayStep,
    PathwayTemplate,
    PathwayTemplateStep,
    TriageAssessment,
)
from services import risk_engine

TEMPLATES = [
    {
        "code": "prevenzione_diabete",
        "name": "Percorso Diabete — prevenzione e compenso",
        "description": "Controllo del compenso glicemico e screening delle complicanze per lavoratori con diabete.",
        "target_text": "Diabete tipo 1 e tipo 2 in attività lavorativa",
        "steps": [
            ("hba1c_trimestrale", "HbA1c trimestrale", "Prelievo per il controllo del compenso glicemico.", "screening", 90, 1, None),
            ("glicemie_domiciliari", "Glicemie domiciliari", "Registrazione settimanale delle glicemie a digiuno nel diario.", "misurazione", 7, 2, "glucose_fasting"),
            ("ed_albuminare", "Esame urine microalbumina", "Screening annuale della nefropatia incipiente.", "screening", 180, 3, None),
            ("fondo_oculare", "Visita fondo oculare", "Screening annuale della retinopatia diabetica.", "visita", 180, 4, None),
            ("piede_diabetico", "Esame del piede", "Valutazione del piede diabetico con l'infermiere o il medico.", "visita", 120, 5, None),
            ("educazione_alimentare", "Educazione alimentare", "Colloquio con definizione di un obiettivo alimentare settimanale.", "educazione", 30, 6, None),
            ("medico_lavoro", "Colloquio con il medico del lavoro", "Valutazione di idoneità e compatibilità delle mansioni.", "visita", 240, 7, None),
        ],
    },
    {
        "code": "prevenzione_ipertensione",
        "name": "Percorso Ipertensione — controllo pressorio",
        "description": "Monitoraggio pressorio e screening del rischio cardiovascolare per lavoratori ipertesi.",
        "target_text": "Ipertensione arteriosa in terapia o di nuova diagnosi",
        "steps": [
            ("pressioni_domiciliari", "Pressioni domiciliari", "Misurazioni mattinali e serali per una settimana al mese.", "misurazione", 7, 1, "bp_systolic"),
            ("profilo_lipidico", "Profilo lipidico", "Colesterolo totale, LDL, HDL e trigliceridi.", "screening", 120, 2, None),
            ("funzione_renale", "Funzione renale ed elettroliti", "Creatinina, eGFR, sodio e potassio.", "screening", 120, 3, None),
            ("ecg", "ECG di controllo", "Elettrocardiogramma basale e valutazione cardiologica.", "visita", 180, 4, None),
            ("educazione_sodio", "Riduzione del sodio", "Colloquio educativo su dieta e stile di vita.", "educazione", 30, 5, None),
            ("medico_lavoro", "Colloquio con il medico del lavoro", "Verifica di idoneità alle mansioni e alle turnazioni.", "visita", 240, 6, None),
        ],
    },
    {
        "code": "screening_metabolico",
        "name": "Screening metabolico",
        "description": "Bilancio preventivo diagnostico per lavoratori con fattori di rischio cardiometabolici.",
        "target_text": "Lavoratori con profilo di rischio medio/alto o familiarità",
        "steps": [
            ("pannello_metabolico", "Esami del sangue metabolici", "Glicemia, profilo lipidico, creatinina.", "screening", 14, 1, None),
            ("antropometria", "Valutazione antropometrica", "Peso, BMI e circonferenza vita.", "misurazione", 7, 2, "weight"),
            ("questionario_benessere", "Questionari di benessere", "Compilazione degli indicatori validati (WEMWBS, BPAAT, WSQ, lavoro).", "educazione", 7, 3, None),
            ("anamnesi_strutturata", "Anamnesi strutturata", "Completamento del questionario anamnestico digitale.", "educazione", 3, 4, None),
            ("colloquio_esito", "Colloquio di restituzione dell'esito", "Restituzione della stratificazione e definizione del piano.", "visita", 21, 5, None),
        ],
    },
    {
        "code": "followup_post_triage",
        "name": "Follow-up post-chiamata",
        "description": "Percorso breve di verifica dopo una chiamata con esito verde o dopo una presa in carico.",
        "target_text": "Lavoratori con chiamata registrata di recente",
        "steps": [
            ("richiamo_72h", "Richiamo entro 72 ore", "Verifica telefonica del sintomo e dell'eventuale esito della visita.", "richiamo", 3, 1, None),
            ("verifica_sintomi", "Verifica in chat", "Aggiornamento rapido sul quadro con l'assistente o l'operatore.", "educazione", 7, 2, None),
            ("valutazione_esito", "Chiusura dell'episodio", "Esito registrato dall'operatore; eventuale visita di controllo.", "visita", 14, 3, None),
        ],
    },
]


def ensure_templates(session: Session) -> None:
    """Insert/refresh the standard catalogue without touching enrollments."""
    for spec in TEMPLATES:
        template = session.query(PathwayTemplate).filter_by(code=spec["code"]).first()
        if template is None:
            template = PathwayTemplate(
                code=spec["code"], name=spec["name"],
                description=spec["description"], target_text=spec["target_text"],
            )
            session.add(template)
            session.flush()
        template.name = spec["name"]
        template.description = spec["description"]
        template.target_text = spec["target_text"]

        existing = {s.code: s for s in template.steps}
        for (code, title, description, kind, offset, step_order, metric) in spec["steps"]:
            row = existing.get(code)
            if row is None:
                row = PathwayTemplateStep(
                    template_id=template.id, code=code, title=title,
                    description=description, kind=kind,
                    offset_days=offset, step_order=step_order, metric_code=metric,
                )
                session.add(row)
            else:
                row.title, row.description, row.kind = title, description, kind
                row.offset_days, row.step_order = offset, step_order
                row.metric_code = metric
    session.commit()


def enroll(session: Session, patient, template_code: str, user_id: int | None,
           started_on: date | None = None) -> CarePathway:
    template = session.query(PathwayTemplate).filter_by(code=template_code, active=True).first()
    if template is None:
        raise ValueError("Percorso non trovato")

    started = started_on or date.today()
    pathway = CarePathway(
        patient_id=patient.id, template_id=template.id,
        status="attivo", started_on=started, created_by_user_id=user_id,
    )
    session.add(pathway)
    session.flush()
    for step in template.steps:
        session.add(CarePathwayStep(
            pathway_id=pathway.id, template_step_code=step.code,
            title=step.title, description=step.description, kind=step.kind,
            due_on=started + timedelta(days=step.offset_days),
            metric_code=step.metric_code,
        ))
    session.flush()
    return pathway


def step_state(step: CarePathwayStep, today: date | None = None) -> str:
    """UI state: completato | programmato | in_attesa | in_ritardo."""
    if step.status == "completato":
        return "completato"
    if step.status == "programmato":
        return "programmato"
    today = today or date.today()
    return "in_ritardo" if step.due_on < today else "in_attesa"


def serialize_pathway(session: Session, pathway: CarePathway) -> dict:
    today = date.today()
    steps = []
    for s in pathway.steps:
        appointment = None
        if s.appointment_id:
            from models import Appointment
            appt = session.get(Appointment, s.appointment_id)
            if appt:
                appointment = {"id": appt.id, "scheduled_at": appt.scheduled_at.isoformat(),
                               "status": appt.status, "kind": appt.kind}
        steps.append({
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "kind": s.kind,
            "metric_code": s.metric_code,
            "due_on": s.due_on.isoformat(),
            "status": step_state(s, today),
            "db_status": s.status,
            "appointment": appointment,
            "completed_on": s.completed_on.isoformat() if s.completed_on else None,
            "outcome": s.outcome,
        })
    done = sum(1 for s in steps if s["status"] == "completato")
    return {
        "id": pathway.id,
        "template_code": pathway.template.code,
        "name": pathway.template.name,
        "description": pathway.template.description,
        "started_on": pathway.started_on.isoformat(),
        "status": pathway.status,
        "progress": round(done / len(steps) * 100) if steps else 0,
        "steps": steps,
    }


def suggest_pathways(session: Session, patient) -> list:
    """Rule-based pathway proposal from diagnosis, risk profile and recent calls.

    The clinician stays in charge — this only ranks what the literature and the
    risk engine already indicate — but it makes the right iter one click away.
    """
    from datetime import timedelta

    enrolled = {
        p.template.code
        for p in session.query(CarePathway).filter_by(patient_id=patient.id, status="attivo")
    }
    evaluation = risk_engine.evaluate_patient(session, patient)
    dx = (patient.primary_diagnosis or "").lower()
    out = []

    def add(code: str, reason: str):
        if code in enrolled or any(x["code"] == code for x in out):
            return
        t = session.query(PathwayTemplate).filter_by(code=code, active=True).first()
        if t:
            out.append({"code": code, "name": t.name, "description": t.description, "reason": reason})

    if "diabete" in dx:
        add("prevenzione_diabete", "Percorso dedicato ai lavoratori con diabete (compenso e complicanze).")
    if "ipertensione" in dx:
        add("prevenzione_ipertensione", "Monitoraggio pressorio e rischio cardiovascolare.")

    recent_triage = (
        session.query(TriageAssessment)
        .filter(
            TriageAssessment.patient_id == patient.id,
            TriageAssessment.status == "completata",
            TriageAssessment.created_at >= datetime.now(timezone.utc) - timedelta(days=30),
        )
        .count()
    )
    if recent_triage:
        add("followup_post_triage", "Chiamata registrata nell'ultimo mese: verifica post-episodio.")

    if evaluation["level"] == "alto" or evaluation["risk_count"] >= 2:
        add("screening_metabolico",
            f"Profilo di rischio {evaluation['level']} ({evaluation['risk_count']} fattori attivi): "
            "bilancio metabolico completo con restituzione dell'esito.")
    return out

