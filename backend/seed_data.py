"""Clinically coherent seed data for the Health Platform platform (PostgreSQL).

Creates a small but complete caseload: one occupational physician, five
workers with full relational profiles (demographics, employment, diagnosis),
10 monthly clinical encounters with coherent lab/vital trajectories,
structured anamnesis answers (mapped onto the live question catalogue),
goals + adherence, remote-monitoring plans, follow-ups, appointments, a
triage record, a chat thread waiting for the operator, wellbeing instruments
and a persisted risk assessment each.

Run:  cd backend && python seed_data.py
"""
import json
import math
import random
from datetime import date, datetime, time, timedelta, timezone

import bcrypt

from app import create_app
from extensions import db
from models import (
    AnamnesisAnswer,
    AnamnesisQuestion,
    Appointment,
    CarePathway,
    CarePathwayStep,
    ChatMessage,
    ChatThread,
    Doctor,
    Encounter,
    FollowUp,
    GoalCheckIn,
    HealthGoal,
    MonitoringPlanItem,
    Observation,
    Patient,
    PatientMedication,
    RiskAssessment,
    TriageAssessment,
    User,
    WellbeingAssessment,
)
from services import anamnesis as ana_service
from services import risk_engine, wellbeing
from services import pathways as pathway_service
from services.triage_protocols import DISPOSITIONS, PROTOCOLS, evaluate_protocol

random.seed(42)

app = create_app()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def series(start, end, n, amplitude, phase):
    """Believable monthly trajectory: smooth drift + gentle oscillation + noise."""
    pts = []
    for i in range(n):
        t = i / (n - 1)
        drift = start + (end - start) * t
        wave = amplitude * math.sin((i + phase) * 0.9)
        noise = random.uniform(-amplitude * 0.35, amplitude * 0.35)
        pts.append(drift + 0.5 * wave + noise)
    return pts


def fmt(value, decimals):
    if decimals == 0:
        return int(round(value))
    return round(value, decimals)


# option value lookup by index — keeps seed values in sync with the catalogue.
# Populated inside the app context before answers are written.
_catalogue = {}


def opt(question_code: str, index: int) -> str:
    return _catalogue[question_code]["options"][index]["value"]


# ---------------------------------------------------------------------------
# wipe (FK-safe order)
# ---------------------------------------------------------------------------
WIPE_ORDER = [
    ChatMessage, ChatThread, TriageAssessment, CarePathwayStep, CarePathway,
    Appointment, FollowUp, PatientMedication,
    GoalCheckIn, HealthGoal, MonitoringPlanItem, WellbeingAssessment,
    RiskAssessment, Observation, Encounter, AnamnesisAnswer,
    AnamnesisQuestion, Patient, Doctor, User,
]

with app.app_context():
    for model in WIPE_ORDER:
        model.query.delete()
    db.session.commit()
    ana_service.ensure_catalogue(db.session)
    _catalogue.update({q["code"]: q for q in ana_service.catalogue(db.session)})

# ---------------------------------------------------------------------------
# people
# ---------------------------------------------------------------------------
PASSWORD = "HealthPlatform.Demo2026!"

STAFF = [
    {
        "username": "doctor", "role": "doctor",
        "first_name": "Marco", "last_name": "Bianchi",
        "specialization": "Medicina del lavoro",
        "phone": "+39 051 5550101",
    },
    # NOTE: patient personas are defined below
]

PEOPLE = [
    {
        "username": "patient1", "first_name": "Mario", "last_name": "Rossi",
        "birth_date": date(1981, 3, 15), "sex": "M",
        "fiscal_code": "RSSMRA81C15H501X", "phone": "+39 333 1110001",
        "height_cm": 175, "employer": "Ceramiche Emiliane SpA", "job_title": "Tecnico di laboratorio qualità",
        "work_pattern": "giornaliero",
        "primary_diagnosis": "Diabete mellito tipo 2",
        "comorbidities": ["Sindrome metabolica"],
        "medications": ["Metformina 850 mg 2x/die", "Lisinopril 10 mg 1x/die", "Atorvastatina 20 mg sera"],
        "trend_key": "diabete-buono",
        "anamnesis": {
            "smoking": ("smoking", 1),                    # ex da ≥12 mesi → protettivo
            "physical_activity": ("physical_activity", 2),  # 3–4 volte → protettivo
            "sedentary_hours": ("sedentary_hours", 1),      # 6–8 ore → neutro
            "alcohol": ("alcohol", 0),                      # occasionale → protettivo
            "sleep": ("sleep", 1),                          # 6–7 ore → neutro
            "nutrition": ("nutrition", 1),                  # disordinata ma accettabile
            "stress": ("stress", 1),                        # medio
            "family_history": ("family_history", 1),        # diabete I grado → rischio
            "occupational_exposures": ("occupational_exposures", 3),
            "work_incidents": ("work_incidents", 0),
            "immunizations": "Influenzale, COVID-19",
            "allergies": "Nessuna nota",
        },
        "adherence": 0.82,
    },
    {
        "username": "patient2", "first_name": "Laura", "last_name": "Bianchi",
        "birth_date": date(1974, 7, 22), "sex": "F",
        "fiscal_code": "BNCLRA74L62H501K", "phone": "+39 333 1110002",
        "height_cm": 164, "employer": "Comune di Bologna", "job_title": "Funzionaria amministrativa",
        "work_pattern": "giornaliero",
        "primary_diagnosis": "Ipertensione arteriosa",
        "comorbidities": [],
        "medications": ["Lisinopril 20 mg 1x/die", "Amlodipina 5 mg 1x/die"],
        "trend_key": "ipertensione-buona",
        "anamnesis": {
            "smoking": ("smoking", 0),
            "physical_activity": ("physical_activity", 2),
            "sedentary_hours": ("sedentary_hours", 1),
            "alcohol": ("alcohol", 0),
            "sleep": ("sleep", 0),
            "nutrition": ("nutrition", 0),
            "stress": ("stress", 0),
            "family_history": ("family_history", 2),
            "occupational_exposures": ("occupational_exposures", 0),
            "work_incidents": ("work_incidents", 0),
            "immunizations": "Influenzale, Tetano, COVID-19",
            "allergies": "Polline (stagionale)",
        },
        "adherence": 0.78,
    },
    {
        "username": "patient3", "first_name": "Giuseppe", "last_name": "Verdi",
        "birth_date": date(1988, 11, 30), "sex": "M",
        "fiscal_code": "VRDGSP88S30H501J", "phone": "+39 333 1110003",
        "height_cm": 178, "employer": "Logistica Padana Srl", "job_title": "Addetto magazzino (muletti)",
        "work_pattern": "turni",
        "primary_diagnosis": "Diabete mellito tipo 2",
        "comorbidities": ["Obesità I grado", "Nefropatia incipiente"],
        "medications": ["Metformina 1000 mg 2x/die", "Insulina glargine 10 U sera", "Sitagliptina 100 mg 1x/die"],
        "trend_key": "diabete-cattivo",
        "anamnesis": {
            "smoking": ("smoking", 3),                      # fumatore attuale → rischio
            "physical_activity": ("physical_activity", 0),  # sedentario → rischio
            "sedentary_hours": ("sedentary_hours", 2),      # >8 ore → rischio
            "alcohol": ("alcohol", 2),                      # >2 unit → rischio
            "sleep": ("sleep", 2),                          # <6 ore → rischio
            "nutrition": ("nutrition", 2),                  # zuccheri/sale → rischio
            "stress": ("stress", 2),                        # alto → rischio
            "family_history": ("family_history", 1),        # diabete I grado → rischio
            "occupational_exposures": ("occupational_exposures", 2),
            "work_incidents": ("work_incidents", 0),
            "immunizations": "Nessuna",
            "allergies": "Nessuna nota",
        },
        "adherence": 0.42,
    },
    {
        "username": "patient4", "first_name": "Anna", "last_name": "Ferrari",
        "birth_date": date(1978, 5, 10), "sex": "F",
        "fiscal_code": "FRANNA78H50H501Z", "phone": "+39 333 1110004",
        "height_cm": 160, "employer": "Call Center Più Servizi", "job_title": "Operatore telefonico",
        "work_pattern": "turni",
        "primary_diagnosis": "Ipertensione arteriosa",
        "comorbidities": ["Dismenorrea", "Cervicalgia"],
        "medications": ["Lisinopril 20 mg 1x/die", "Idroclorotiazide 25 mg 1x/die", "Atorvastatina 20 mg sera"],
        "trend_key": "ipertensione-cattiva",
        "anamnesis": {
            "smoking": ("smoking", 1),
            "physical_activity": ("physical_activity", 1),
            "sedentary_hours": ("sedentary_hours", 1),
            "alcohol": ("alcohol", 1),
            "sleep": ("sleep", 1),
            "nutrition": ("nutrition", 2),
            "stress": ("stress", 1),
            "family_history": ("family_history", 0),        # cardiopatia precoce I grado → rischio
            "occupational_exposures": ("occupational_exposures", 3),
            "work_incidents": ("work_incidents", 0),
            "immunizations": "Influenzale",
            "allergies": "Lattame (lieve)",
        },
        "adherence": 0.55,
    },
    {
        "username": "patient5", "first_name": "Paolo", "last_name": "Costa",
        "birth_date": date(1991, 1, 25), "sex": "M",
        "fiscal_code": "CSTPLA91A25H501G", "phone": "+39 333 1110005",
        "height_cm": 182, "employer": "Studio Tecnico Associati VR", "job_title": "Progettista meccanico",
        "work_pattern": "giornaliero",
        "primary_diagnosis": "Diabete mellito tipo 1",
        "comorbidities": [],
        "medications": ["Insulina asparte 3–4 U pre-pasti", "Insulina glargine 12 U sera"],
        "trend_key": "diabete-tipo1",
        "anamnesis": {
            "smoking": ("smoking", 0),
            "physical_activity": ("physical_activity", 3),
            "sedentary_hours": ("sedentary_hours", 0),
            "alcohol": ("alcohol", 0),
            "sleep": ("sleep", 0),
            "nutrition": ("nutrition", 0),
            "stress": ("stress", 0),
            "family_history": ("family_history", 2),
            "occupational_exposures": ("occupational_exposures", 0),
            "work_incidents": ("work_incidents", 0),
            "immunizations": "Influenzale, Tetano, Epatite B, COVID-19",
            "allergies": "Nessuna nota",
        },
        "adherence": 0.85,
    },
]

# ---------------------------------------------------------------------------
# per-pathology metric trajectories (10 monthly points)
# key: (start, end, amplitude, phase)
# ---------------------------------------------------------------------------
TRENDS = {
    "diabete-buono": {
        "hba1c": (8.0, 6.7, 0.35, 0),
        "glucose_fasting": (138, 108, 11, 1),
        "glucose_pp": (185, 150, 14, 2),
        "ldl": (145, 118, 8, 3),
        "hdl": (39, 44, 3, 4),
        "total_cholesterol": (215, 190, 8, 5),
        "triglycerides": (190, 160, 17, 6),
        "creatinine": (0.95, 0.92, 0.05, 7),
        "egfr": (82, 85, 4, 8),
        "microalbuminuria": (28, 18, 6, 9),
        "bp_systolic": (134, 126, 5, 2),
        "bp_diastolic": (86, 79, 4, 3),
        "weight": (88, 82, 1.2, 4),
        "waist": (101, 93, 1.5, 5),
        "bmi": (28.7, 26.8, 0.4, 4),
    },
    "diabete-cattivo": {
        "hba1c": (7.4, 7.7, 0.40, 0),
        "glucose_fasting": (135, 144, 13, 1),
        "glucose_pp": (175, 190, 15, 2),
        "ldl": (150, 142, 9, 3),
        "hdl": (37, 40, 3, 4),
        "total_cholesterol": (225, 212, 10, 5),
        "triglycerides": (210, 198, 19, 6),
        "creatinine": (1.00, 1.16, 0.05, 7),
        "egfr": (78, 67, 5, 8),
        "microalbuminuria": (45, 78, 12, 9),
        "bp_systolic": (136, 138, 6, 1),
        "bp_diastolic": (86, 88, 4, 2),
        "weight": (102, 104, 1.4, 3),
        "waist": (112, 114, 1.6, 4),
        "bmi": (32.2, 32.8, 0.4, 3),
    },
    "diabete-tipo1": {
        "hba1c": (7.9, 7.3, 0.50, 0),
        "glucose_fasting": (155, 125, 18, 1),
        "glucose_pp": (200, 170, 22, 2),
        "ldl": (110, 105, 7, 3),
        "hdl": (48, 52, 4, 4),
        "total_cholesterol": (180, 175, 8, 5),
        "triglycerides": (120, 110, 14, 6),
        "creatinine": (0.85, 0.88, 0.04, 7),
        "egfr": (95, 92, 4, 8),
        "microalbuminuria": (12, 10, 4, 9),
        "bp_systolic": (124, 120, 5, 3),
        "bp_diastolic": (78, 76, 3, 4),
        "weight": (76, 75, 1.0, 2),
        "waist": (82, 81, 1.2, 3),
        "bmi": (22.9, 22.6, 0.3, 2),
    },
    "ipertensione-buona": {
        "bp_systolic": (148, 128, 6, 0),
        "bp_diastolic": (92, 80, 4, 1),
        "creatinine": (0.88, 0.85, 0.05, 2),
        "egfr": (85, 88, 4, 3),
        "ldl": (138, 120, 8, 4),
        "hdl": (52, 55, 3, 5),
        "total_cholesterol": (210, 195, 8, 6),
        "triglycerides": (130, 120, 12, 7),
        "potassium": (4.2, 4.3, 0.2, 8),
        "sodium": (140, 140, 1.5, 9),
        "weight": (68, 66, 0.9, 1),
        "waist": (78, 76, 1.0, 2),
        "bmi": (25.3, 24.5, 0.3, 1),
    },
    "ipertensione-cattiva": {
        "bp_systolic": (152, 143, 7, 0),
        "bp_diastolic": (95, 89, 4, 1),
        "creatinine": (0.95, 1.00, 0.05, 2),
        "egfr": (80, 78, 4, 3),
        "ldl": (148, 141, 9, 4),
        "hdl": (45, 48, 3, 5),
        "total_cholesterol": (225, 216, 9, 6),
        "triglycerides": (155, 146, 14, 7),
        "potassium": (4.1, 4.0, 0.2, 8),
        "sodium": (141, 140, 1.5, 9),
        "weight": (74, 76, 1.0, 5),
        "waist": (86, 88, 1.2, 6),
        "bmi": (28.9, 29.7, 0.3, 5),
    },
}

DECIMALS = {
    "hba1c": 1, "glucose_fasting": 0, "glucose_pp": 0, "ldl": 0, "hdl": 0,
    "total_cholesterol": 0, "triglycerides": 0, "creatinine": 2, "egfr": 0,
    "microalbuminuria": 0, "bp_systolic": 0, "bp_diastolic": 0, "potassium": 1,
    "sodium": 0, "weight": 1, "waist": 0, "bmi": 1,
}

VISIT_NOTES = {
    "diabete": [
        ("controllo", "Controllo glicemico trimestrale. Terapia invariata, monitoraggio domiciliare corretto.", "Diabete mellito — follow-up"),
        ("followup", "Follow-up post-aggiustamento terapia. Glicemie capillari stabili.", "Diabete mellito — follow-up terapia"),
        ("controllo", "Valutazione complicanze: fondo oculare nella norma, piede sano.", "Diabete mellito — screening complicanze"),
        ("urgenza", "Paziente riferisce iperglicemia sintomatica. Valutato, stabilizzato in ambulatorio.", "Diabete mellito — episodio iperglicemico"),
        ("controllo", "Educazione alimentare rafforzata. Paziente collaborante.", "Diabete mellito — educazione terapeutica"),
        ("followup", "Controllo HbA1c: trend in miglioramento. Continuare schema attuale.", "Diabete mellito — compenso migliorato"),
    ],
    "ipertensione": [
        ("controllo", "Monitoraggio pressorio ambulatoriale. Terapia confermata.", "Ipertensione arteriosa — controllo"),
        ("followup", "Holter pressorio: valori medi nei limiti. Continuare monitoraggio domiciliare.", "Ipertensione arteriosa — follow-up"),
        ("controllo", "ECG: ritmo sinusale. Auscultazione cardiaca nei limiti.", "Ipertensione arteriosa — valutazione cardiaca"),
        ("urgenza", "Crisi ipertensiva transitoria, gestita in ambulatorio. Terapia rinforzata.", "Ipertensione arteriosa — crisi ipertensiva"),
        ("controllo", "Consulenza nefrologica: funzione renale stabile.", "Ipertensione arteriosa — valutazione renale"),
        ("followup", "Ridotto apporto sodico, paziente ha perso peso. Pressione migliorata.", "Ipertensione arteriosa — miglioramento"),
    ],
}

GOAL_DEFS = {
    "diabete-buono": ("physical_activity", "Camminata veloce 30 minuti", 5),
    "diabete-cattivo": ("nutrition", "Ridurre bevande zuccherate (max 1 a settimana)", 6),
    "diabete-tipo1": ("physical_activity", "Nuoto o bici da 45 minuti", 4),
    "ipertensione-buona": ("stress", "Pausa respirazione guidata 10 minuti", 5),
    "ipertensione-cattiva": ("nutrition", "Ridurre sale e preconfezionati", 6),
}

MONITORING = {
    "diabete-buono": [("glucose_fasting", 7, "80–130 mg/dL a digiuno"), ("weight", 7, "−0,5 kg a settimana"), ("hba1c", 90, "< 7,0%")],
    "diabete-cattivo": [("glucose_fasting", 3, "80–130 mg/dL a digiuno"), ("weight", 7, "stabilizzazione"), ("hba1c", 90, "< 7,5%")],
    "diabete-tipo1": [("glucose_fasting", 7, "80–130 mg/dL a digiuno"), ("hba1c", 90, "< 7,5%")],
    "ipertensione-buona": [("bp_systolic", 7, "< 130 mmHg (media settimanale)")],
    "ipertensione-cattiva": [("bp_systolic", 3, "< 130 mmHg (media settimanale)"), ("weight", 7, "−0,5 kg a settimana")],
}


def appt_when(days_ahead: int, hour: int, minute: int = 0) -> datetime:
    """Next working-day-ish slot in local naive → UTC."""
    d = date.today() + timedelta(days=days_ahead)
    if d.weekday() >= 5:
        d += timedelta(days=2)
    local = datetime.combine(d, time(hour, minute))
    return local.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
with app.app_context():
    # users
    doctor_user = User(username="doctor", password_hash=hash_password(PASSWORD), role="doctor",
                       email="m.bianchi@healthplatform.it")
    db.session.add(doctor_user)
    db.session.flush()
    doctor = Doctor(user_id=doctor_user.id, first_name="Marco", last_name="Bianchi",
                    specialization="Medicina del lavoro", phone="+39 051 5550101")
    db.session.add(doctor)
    db.session.flush()

    patients = []
    for spec in PEOPLE:
        user = User(username=spec["username"], password_hash=hash_password(PASSWORD),
                    role="patient", email=f"{spec['username']}@demo.healthplatform.it")
        db.session.add(user)
        db.session.flush()
        patient = Patient(
            user_id=user.id,
            first_name=spec["first_name"], last_name=spec["last_name"],
            birth_date=spec["birth_date"], sex=spec["sex"],
            fiscal_code=spec["fiscal_code"], phone=spec["phone"],
            height_cm=spec["height_cm"],
            employer=spec["employer"], job_title=spec["job_title"],
            work_pattern=spec["work_pattern"],
            primary_diagnosis=spec["primary_diagnosis"],
            comorbidities=json.dumps(spec["comorbidities"]),
            assigned_doctor_id=doctor.id,
            enrolled_on=date.today() - timedelta(days=300),
        )
        db.session.add(patient)
        db.session.flush()
        # therapy as relational rows (name + posology parsed from the spec)
        for med in spec["medications"]:
            import re
            match = re.match(r"^(.*?(?:mg|U|g)(?:\s*\d*)?)\s*((?:\dx/die|sera|mattina|pre-pasti|\d-\d U.*)?.*)$", med)
            name, dosage = (match.group(1).strip(), match.group(2).strip()) if match else (med, None)
            db.session.add(PatientMedication(
                patient_id=patient.id, name=name or med, dosage=dosage or None,
            ))
        patients.append((patient, spec))

    N_POINTS = 10
    dates = [date.today() - timedelta(days=30 * (N_POINTS - 1 - i)) for i in range(N_POINTS)]

    for patient, spec in patients:
        specs = TRENDS[spec["trend_key"]]
        series_map = {k: series(s, e, N_POINTS, a, ph) for k, (s, e, a, ph) in specs.items()}
        bucket = "diabete" if "diabete" in spec["primary_diagnosis"].lower() else "ipertensione"
        notes_pool = VISIT_NOTES[bucket]

        # --- encounters + observations -------------------------------
        for i, day in enumerate(dates):
            if i == 4:
                kind, notes, diagnosis = next(n for n in notes_pool if n[0] == "urgenza")
            else:
                kind, notes, diagnosis = notes_pool[i % len(notes_pool)]
            encounter = Encounter(
                patient_id=patient.id, encounter_date=day, kind=kind,
                facility="Ambulatorio Health Platform" if kind != "followup" else "Teleconsulto",
                notes=notes, diagnosis=diagnosis,
            )
            db.session.add(encounter)
            db.session.flush()
            for code, values in series_map.items():
                db.session.add(Observation(
                    patient_id=patient.id, encounter_id=encounter.id, code=code,
                    value=fmt(values[i], DECIMALS[code]), source="lab" if code in (
                        "hba1c", "glucose_fasting", "glucose_pp", "ldl", "hdl",
                        "total_cholesterol", "triglycerides", "creatinine", "egfr",
                        "microalbuminuria", "potassium", "sodium",
                    ) else "clinic",
                    taken_on=day, notes="Controllo periodico",
                ))

        # --- anamnesis answers ---------------------------------------
        questions = {q.code: q for q in AnamnesisQuestion.query.all()}
        for code, spec_value in spec["anamnesis"].items():
            if isinstance(spec_value, tuple):
                _qcode, idx = spec_value
                value = opt(_qcode, idx)
            else:
                # multi-choice and free-text answers are stored verbatim
                value = spec_value
            db.session.add(AnamnesisAnswer(
                patient_id=patient.id, question_id=questions[code].id,
                value=value, answered_by="patient",
            ))

        # --- goal + adherence ----------------------------------------
        area, title, freq = GOAL_DEFS[spec["trend_key"]]
        goal = HealthGoal(patient_id=patient.id, area=area, title=title,
                          frequency_per_week=freq, status="active", created_by="doctor")
        db.session.add(goal)
        db.session.flush()
        rng = random.Random(hash(spec["username"]) & 0xFFFF)
        profile = spec["adherence"]
        for w in range(6, 0, -1):
            monday = date.today() - timedelta(days=date.today().weekday() + 7 * (w - 1))
            done = max(0, min(freq, int(round(freq * (profile + rng.uniform(-0.25, 0.25))))))
            db.session.add(GoalCheckIn(goal_id=goal.id, patient_id=patient.id,
                                       week_of=monday, completed_days=done))

        # --- remote monitoring plan + some home measurements ----------
        for code, freq_days, target in MONITORING[spec["trend_key"]]:
            db.session.add(MonitoringPlanItem(
                patient_id=patient.id, code=code, frequency_days=freq_days,
                target_text=target, created_by_user_id=doctor_user.id,
            ))
        # home BP readings (systolic, diastolic) for the monitored workers
        home_bp = {
            "ipertensione-cattiva": (152, 94),
            "diabete-cattivo": (136, 86),
            "ipertensione-buona": (128, 78),
        }
        if spec["trend_key"] in home_bp:
            base_sys, base_dia = home_bp[spec["trend_key"]]
            for d_ago in (1, 3, 5, 8, 10):
                db.session.add(Observation(
                    patient_id=patient.id, code="bp_systolic",
                    value=int(base_sys + random.uniform(-6, 6)), source="patient_home",
                    taken_on=date.today() - timedelta(days=d_ago), notes="Misurazione domiciliare",
                ))
                db.session.add(Observation(
                    patient_id=patient.id, code="bp_diastolic",
                    value=int(base_dia + random.uniform(-5, 5)), source="patient_home",
                    taken_on=date.today() - timedelta(days=d_ago), notes="Misurazione domiciliare",
                ))

        # --- wellbeing instruments ------------------------------------
        wb_specs = {
            "diabete-buono": dict(wemwbs=[4, 4, 3, 4, 4, 4, 3], bpaat=(3, 1), wsq=(6.5, 1.0, 3.5),
                                  work=(7, 1, 4, 3, 3, 3)),
            "diabete-cattivo": dict(wemwbs=[2, 2, 2, 3, 2, 2, 3], bpaat=(0, 0), wsq=(9.0, 1.0, 4.0),
                                    work=(5, 3, 21, 7, 4, 2)),
            "diabete-tipo1": dict(wemwbs=[5, 4, 4, 5, 4, 5, 5], bpaat=(4, 2), wsq=(5.0, 0.5, 3.0),
                                  work=(9, 0, 0, 1, 2, 4)),
            "ipertensione-buona": dict(wemwbs=[4, 4, 4, 4, 4, 4, 4], bpaat=(3, 1), wsq=(5.5, 1.0, 3.0),
                                       work=(8, 1, 3, 2, 2, 4)),
            "ipertensione-cattiva": dict(wemwbs=[3, 3, 3, 3, 3, 3, 3], bpaat=(1, 0), wsq=(7.5, 1.0, 3.5),
                                         work=(6, 2, 9, 5, 3, 3)),
        }
        wb = wb_specs[spec["trend_key"]]
        taken = date.today() - timedelta(days=12)

        wem_answers = {f"q{i+1}": v for i, v in enumerate(wb["wemwbs"])}
        score, category = wellbeing.score_instrument("wemwbs7", wem_answers)
        db.session.add(WellbeingAssessment(
            patient_id=patient.id, instrument="wemwbs7", answers=json.dumps(wem_answers),
            score=score, category=category, taken_on=taken,
        ))
        bpaat_answers = {"q1": wb["bpaat"][0], "q2": wb["bpaat"][1]}
        score, category = wellbeing.score_instrument("bpaat", bpaat_answers)
        db.session.add(WellbeingAssessment(
            patient_id=patient.id, instrument="bpaat", answers=json.dumps(bpaat_answers),
            score=score, category=category, taken_on=taken,
        ))
        wsq_answers = {f"q{i+1}": v for i, v in enumerate(wb["wsq"])}
        score, category = wellbeing.score_instrument("wsq", wsq_answers)
        db.session.add(WellbeingAssessment(
            patient_id=patient.id, instrument="wsq", answers=json.dumps(wsq_answers),
            score=score, category=category, taken_on=taken,
        ))
        work_answers = {
            "work_ability": wb["work"][0], "absence_episodes": wb["work"][1],
            "absence_days": wb["work"][2], "presenteeism": wb["work"][3],
            "demands": wb["work"][4], "control": wb["work"][5],
        }
        score, category = wellbeing.score_instrument("work", work_answers)
        db.session.add(WellbeingAssessment(
            patient_id=patient.id, instrument="work", answers=json.dumps(work_answers),
            score=score, category=category, taken_on=taken,
        ))

        db.session.flush()
    print("  → anagrafiche, incontri, anamnesi, obiettivi, monitoraggio, benessere creati")

    # convenience handles
    p_by_username = {s["username"]: p for p, s in patients}
    p3, p4 = p_by_username["patient3"], p_by_username["patient4"]
    p1 = p_by_username["patient1"]

    # --- follow-ups --------------------------------------------------
    fu_done = FollowUp(patient_id=p1.id, created_by_user_id=doctor_user.id,
                       due_on=date.today() - timedelta(days=10), reason="Esito controllo trimestrale",
                       channel="chiamata", status="done",
                       outcome="Paziente informato, aderenza buona. Prossimo controllo a 3 mesi.",
                       completed_at=datetime.now(timezone.utc) - timedelta(days=10))
    fu_pending = FollowUp(patient_id=p3.id, created_by_user_id=doctor_user.id,
                          due_on=date.today() + timedelta(days=2),
                          reason="Verifica aderenza obiettivo alimentazione e riesame glicemie",
                          channel="chiamata", status="pending")
    fu_overdue = FollowUp(patient_id=p4.id, created_by_user_id=doctor_user.id,
                          due_on=date.today() - timedelta(days=3),
                          reason="Raccogliere misurazioni pressorie domiciliari mancanti",
                          channel="chiamata", status="pending")
    db.session.add_all([fu_done, fu_pending, fu_overdue])
    db.session.flush()

    # --- appointments ------------------------------------------------
    appt_visit = Appointment(
        patient_id=p3.id, doctor_id=doctor.id, kind="visita_ambulatoriale",
        reason="Triage · Dolori addominali — visita entro 48 ore",
        priority="urgente", scheduled_at=appt_when(1, 10, 30),
        location="Ambulatorio Health Platform", status="confermato",
        created_by_user_id=doctor_user.id, created_via="triage",
    )
    appt_tele = Appointment(
        patient_id=p4.id, doctor_id=doctor.id, kind="teleconsulto",
        reason="Riesame pressione domiciliare e terapia",
        priority="routine", scheduled_at=appt_when(3, 14, 0),
        location="Teleconsulto (piattaforma)", status="proposto",
        created_by_user_id=doctor_user.id, created_via="medico",
    )
    db.session.add_all([appt_visit, appt_tele])
    db.session.flush()

    # --- triage record (the seeded example call) ----------------------
    protocol = next(p for p in PROTOCOLS if p["code"] == "algie_addominali")
    answers = {"q1": "no", "q2": "no", "q3": "no", "q4": "no", "q5": "sì", "q6": "no", "q7": "no"}
    evaluation = risk_engine.evaluate_patient(db.session, p3)
    triage_result = evaluate_protocol(
        protocol, answers,
        {"diabetes": True, "age": evaluation["age"], "risk_level": evaluation["level"]},
    )
    triage = TriageAssessment(
        patient_id=p3.id, operator_user_id=doctor_user.id,
        protocol_code="algie_addominali", complaint_label="Dolori addominali",
        answers=json.dumps([
            {"id": "q1", "question": "L'addome è rigido, teso, al minimo tocco?", "value": "no", "option_label": "No"},
            {"id": "q5", "question": "Il dolore dura da più di 24 ore senza miglioramento?", "value": "sì", "option_label": "Sì"},
        ]),
        tier=triage_result["tier"],
        disposition_code=triage_result["disposition"],
        disposition_label=DISPOSITIONS[triage_result["disposition"]]["label"],
        disposition_detail="Visita ravvicinata per escludere complicanze.",
        red_flags=None, risk_level_at_triage=evaluation["level"],
        appointment_id=appt_visit.id, created_at=datetime.now(timezone.utc) - timedelta(hours=26),
    )
    db.session.add(triage)
    appt_visit.triage_assessment_id = triage.id

    # --- care pathways (prevention / screening / follow-up) -----------
    def seed_pathway(patient, template_code, started, *, done=(), overdue=()):
        path = pathway_service.enroll(db.session, patient, template_code, doctor_user.id, started)
        for step in path.steps:
            code = step.template_step_code
            if code in done:
                step.status = "completato"
                step.completed_on = max(started, step.due_on - timedelta(days=5))
                step.outcome = "Eseguito, esito regolare." if step.kind in ("screening", "visita") else None
            elif code in overdue:
                step.status = "in_attesa"  # due_on in the past → shown as "in ritardo"
        return path

    pathway_service.ensure_templates(db.session)

    today = date.today()
    seed_pathway(
        p1, "prevenzione_diabete", today - timedelta(days=240),
        done={"hba1c_trimestrale", "glicemie_domiciliari", "ed_albuminare",
              "piede_diabetico", "educazione_alimentare"},
        overdue={"fondo_oculare"},                     # next action: prenota la visita
    )
    seed_pathway(
        p_by_username["patient2"], "prevenzione_ipertensione", today - timedelta(days=150),
        done={"pressioni_domiciliari", "profilo_lipidico", "funzione_renale", "educazione_sodio"},
    )
    seed_pathway(
        p3, "prevenzione_diabete", today - timedelta(days=10),
        overdue={"glicemie_domiciliari"},
    )
    seed_pathway(
        p4, "prevenzione_ipertensione", today - timedelta(days=190),
        done={"profilo_lipidico", "funzione_renale", "educazione_sodio"},
        overdue={"pressioni_domiciliari", "ecg"},
    )

    # Paolo: pathway nearly complete, last step booked with the physician
    path5 = seed_pathway(
        p_by_username["patient5"], "prevenzione_diabete", today - timedelta(days=300),
        done={"hba1c_trimestrale", "glicemie_domiciliari", "ed_albuminare",
              "fondo_oculare", "piede_diabetico", "educazione_alimentare"},
    )
    step_ml = next(s for s in path5.steps if s.template_step_code == "medico_lavoro")
    appt_ml = Appointment(
        patient_id=p_by_username["patient5"].id, doctor_id=doctor.id,
        kind="visita_ambulatoriale", reason="Percorso · Colloquio con il medico del lavoro",
        priority="routine", scheduled_at=appt_when(15, 11, 0),
        location="Ambulatorio Health Platform", status="confermato",
        created_by_user_id=doctor_user.id, created_via="percorso",
        pathway_step_id=step_ml.id,
    )
    db.session.add(appt_ml)
    db.session.flush()
    step_ml.appointment_id = appt_ml.id
    step_ml.status = "programmato"

    # Giuseppe: post-triage recall pathway, linked to the pending follow-up call
    path3b = seed_pathway(p3, "followup_post_triage", today - timedelta(days=1))
    step_recall = next(s for s in path3b.steps if s.template_step_code == "richiamo_72h")
    step_recall.followup_id = fu_pending.id
    step_recall.status = "programmato"

    # --- chat: coach thread for patient3, escalated, waiting operator --
    thread = ChatThread(patient_id=p3.id, kind="coach", status="waiting_operator",
                        subject="Glicemie alte e mal di pancia: cosa fare?")
    db.session.add(thread)
    db.session.flush()
    chat_lines = [
        ("bot", "Ciao Giuseppe! Sono il tuo coach di prevenzione. Posso spiegarti i tuoi valori, suggerirti obiettivi settimanali e aiutarti a orientarti nel percorso."),
        ("patient", "Ciao, da due giorni le glicemie sono alte (180-200) e ho mal di pancia. Preoccupa?"),
        ("bot", "INFORMAZIONE GENERALE: valori tra 180 e 200 mg/dL sono sopra l'obiettivo e con dolore addominale vanno riferiti subito.\nCONSIGLIO PREVENTIVO PERSONALIZZATO: questa settimana misura la glicemia a digiuno e 2 ore dopo cena, ogni giorno.\nINDICAZIONE CLINICA: con dolore addominale persistente contatta il medico entro oggi."),
        ("patient", "Ok, ma preferirei parlare con qualcuno."),
    ]
    base_time = datetime.now(timezone.utc) - timedelta(hours=5)
    for i, (sender, content) in enumerate(chat_lines):
        db.session.add(ChatMessage(thread_id=thread.id, sender=sender, content=content,
                                   created_at=base_time + timedelta(minutes=i * 7)))

    # --- persisted risk assessments (audit baseline) -------------------
    for patient, spec in patients:
        evaluation = risk_engine.evaluate_patient(db.session, patient)
        db.session.add(RiskAssessment(
            patient_id=patient.id,
            model_version=evaluation["model_version"],
            level=evaluation["level"],
            risk_count=evaluation["risk_count"],
            protective_count=evaluation["protective_count"],
            components=json.dumps(evaluation["components"]),
            recommendations=json.dumps(evaluation["recommendations"]),
        ))

    db.session.commit()

    # --- report --------------------------------------------------------
    print("OK — seed completato")
    print(f"   Utenti: doctor + {len(patients)} pazienti | password: {PASSWORD}")
    for patient, spec in patients:
        evaluation = risk_engine.evaluate_patient(db.session, patient)
        key = "hba1c" if "diabete" in spec["primary_diagnosis"].lower() else "bp_systolic"
        vals = [f"{o.value:g}" for o in Observation.query.filter_by(patient_id=patient.id, code=key)
                .order_by(Observation.taken_on).all()]
        print(f"   - {patient.full_name:16s} [{spec['primary_diagnosis']:24s}] rischio {evaluation['level']:5s} "
              f"({evaluation['risk_count']} attivi / {evaluation['protective_count']} protettivi) "
              f"{key}: {' → '.join(vals[:1] + ['…'] + vals[-1:])}")
