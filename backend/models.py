"""Relational domain model for the occupational-health platform.

Design notes
------------
* Every patient is a first-class relational profile (demographics, employment,
  diagnosis) instead of a JSON blob, so clinicians can query and audit data.
* Clinical values live in one `observations` table with numeric values and a
  canonical metric code — labs, clinic vitals and patient home measurements
  share the same schema (distinguished by `source`).
* Anamnesis is a two-part structure: a customizable question catalogue plus
  one versioned answer row per (patient, question), with provenance.
* Risk stratification results are persisted (`risk_assessments`) with the
  model version and full component breakdown for auditability.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------
class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'doctor' | 'patient'
    email: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    doctor_profile: Mapped["Doctor | None"] = relationship(back_populates="user")
    patient_profile: Mapped["Patient | None"] = relationship(
        back_populates="user", foreign_keys="Patient.user_id"
    )


class Doctor(db.Model):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(60), nullable=False)
    last_name: Mapped[str] = mapped_column(String(60), nullable=False)
    specialization: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40))

    user: Mapped[User] = relationship(back_populates="doctor_profile")


class Patient(db.Model):
    """The worker's clinical/administrative profile."""

    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    # Demographics
    first_name: Mapped[str] = mapped_column(String(60), nullable=False)
    last_name: Mapped[str] = mapped_column(String(60), nullable=False)
    birth_date: Mapped[Date | None] = mapped_column(Date)
    sex: Mapped[str | None] = mapped_column(String(1))  # 'M' | 'F'
    fiscal_code: Mapped[str | None] = mapped_column(String(16))
    phone: Mapped[str | None] = mapped_column(String(40))

    # Anthropometrics (current; history lives in observations)
    height_cm: Mapped[float | None] = mapped_column(Float)

    # Clinical
    primary_diagnosis: Mapped[str | None] = mapped_column(String(120))
    comorbidities: Mapped[str | None] = mapped_column(Text)  # JSON list

    # Employment (occupational-health specifics)
    employer: Mapped[str | None] = mapped_column(String(120))
    job_title: Mapped[str | None] = mapped_column(String(120))
    work_pattern: Mapped[str | None] = mapped_column(String(40))  # ufficio|turni|notte|manuali

    # Care assignment
    assigned_doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.id"))
    enrolled_on: Mapped[Date | None] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="patient_profile", foreign_keys=[user_id])
    assigned_doctor: Mapped["Doctor | None"] = relationship()
    observations: Mapped[list["Observation"]] = relationship(back_populates="patient")
    encounters: Mapped[list["Encounter"]] = relationship(back_populates="patient")
    therapies: Mapped[list["PatientMedication"]] = relationship(
        primaryjoin="Patient.id == foreign(PatientMedication.patient_id)",
        order_by="PatientMedication.active.desc(), PatientMedication.name",
        cascade="all, delete-orphan",
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class PatientMedication(db.Model):
    """Therapy in corso (relational, CRUD-managed by the clinician)."""

    __tablename__ = "patient_medications"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(120))
    schedule: Mapped[str | None] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---------------------------------------------------------------------------
# Clinical data
# ---------------------------------------------------------------------------
class Encounter(db.Model):
    """A clinical encounter (periodic control, urgent access, follow-up)."""

    __tablename__ = "encounters"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    encounter_date: Mapped[Date] = mapped_column(Date, nullable=False)
    kind: Mapped[str] = mapped_column(
        String(20), nullable=False, default="controllo"
    )  # controllo | urgenza | followup
    facility: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    patient: Mapped[Patient] = relationship(back_populates="encounters")
    observations: Mapped[list["Observation"]] = relationship(back_populates="encounter")

    __table_args__ = (
        CheckConstraint("kind IN ('controllo','urgenza','followup')", name="ck_encounter_kind"),
    )


# Canonical metric codes used across observations, monitoring plans, and the
# risk engine. Kept in one place so nothing drifts.
METRIC_CODES = {
    "hba1c":              ("HbA1c",                   "%",     "4.0 – 6.0"),
    "glucose_fasting":    ("Glicemia a digiuno",      "mg/dL", "70 – 100"),
    "glucose_pp":         ("Glicemia postprandiale",  "mg/dL", "< 140"),
    "ldl":                ("Colesterolo LDL",         "mg/dL", "< 100"),
    "hdl":                ("Colesterolo HDL",         "mg/dL", "> 40"),
    "total_cholesterol":  ("Colesterolo totale",      "mg/dL", "< 200"),
    "triglycerides":      ("Trigliceridi",            "mg/dL", "< 150"),
    "creatinine":         ("Creatinina",              "mg/dL", "0.7 – 1.3"),
    "egfr":               ("eGFR",                    "mL/min","> 60"),
    "microalbuminuria":   ("Microalbuminuria",        "mg/g",  "< 30"),
    "bp_systolic":        ("Pressione sistolica",     "mmHg",  "90 – 130"),
    "bp_diastolic":       ("Pressione diastolica",    "mmHg",  "60 – 80"),
    "potassium":          ("Potassio",                "mmol/L","3.5 – 5.1"),
    "sodium":             ("Sodio",                   "mmol/L","136 – 145"),
    "weight":             ("Peso",                    "kg",    "—"),
    "bmi":                ("BMI",                     "kg/m²", "18.5 – 24.9"),
    "waist":              ("Circonferenza vita",      "cm",    "< 94 (M) / < 80 (F)"),
}


class Observation(db.Model):
    """A single clinical measurement: lab value, clinic vital or home reading."""

    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounters.id"))
    code: Mapped[str] = mapped_column(String(40), nullable=False)  # METRIC_CODES key
    value: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="lab")
    # lab | clinic | patient_home
    taken_on: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notes: Mapped[str | None] = mapped_column(Text)

    patient: Mapped[Patient] = relationship(back_populates="observations")
    encounter: Mapped[Encounter | None] = relationship(back_populates="observations")

    __table_args__ = (
        Index("ix_obs_patient_code_date", "patient_id", "code", "taken_on"),
        CheckConstraint(
            "source IN ('lab','clinic','patient_home')", name="ck_observation_source"
        ),
    )

    @property
    def label(self) -> str:
        return METRIC_CODES.get(self.code, (self.code,))[0]

    @property
    def unit(self) -> str:
        return METRIC_CODES.get(self.code, ("", ""))[1]


# ---------------------------------------------------------------------------
# Structured anamnesis
# ---------------------------------------------------------------------------
class AnamnesisQuestion(db.Model):
    """Customizable question catalogue (versioned by `active` + updated_at).

    Adding/removing/editing questions is data, not code: the guided patient
    questionnaire and the doctor's view are both generated from this table.
    """

    __tablename__ = "anamnesis_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    section: Mapped[str] = mapped_column(String(40), nullable=False)
    # stile_di_vita | lavoro | storia_clinica | abitudini
    prompt: Mapped[str] = mapped_column(String(300), nullable=False)
    help_text: Mapped[str | None] = mapped_column(String(300))
    answer_type: Mapped[str] = mapped_column(String(20), nullable=False, default="single_choice")
    # single_choice | multi_choice | text | number
    options: Mapped[str | None] = mapped_column(Text)  # JSON list of {value,label,risk,protective?}
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_factor_code: Mapped[str | None] = mapped_column(String(40))
    # links the answer to a factor in the risk engine catalogue
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AnamnesisAnswer(db.Model):
    """One answer per (patient, question), with provenance and timestamps."""

    __tablename__ = "anamnesis_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("anamnesis_questions.id"), nullable=False
    )
    value: Mapped[str] = mapped_column(String(300), nullable=False)
    answered_by: Mapped[str] = mapped_column(String(10), nullable=False, default="patient")
    # patient | doctor
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    question: Mapped[AnamnesisQuestion] = relationship()

    __table_args__ = (
        UniqueConstraint("patient_id", "question_id", name="uq_answer_patient_question"),
    )


class AnamnesisAnswerHistory(db.Model):
    """Audit trail: every change to an anamnesis answer (who, when, what)."""

    __tablename__ = "anamnesis_answer_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    answer_id: Mapped[int] = mapped_column(
        ForeignKey("anamnesis_answers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("anamnesis_questions.id"), nullable=False
    )
    old_value: Mapped[str | None] = mapped_column(String(300))
    new_value: Mapped[str] = mapped_column(String(300), nullable=False)
    answered_by: Mapped[str] = mapped_column(String(10), nullable=False)
    changed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---------------------------------------------------------------------------
# Risk stratification
# ---------------------------------------------------------------------------
class RiskAssessment(db.Model):
    """Persisted output of the risk engine (audit trail included)."""

    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    model_version: Mapped[str] = mapped_column(String(40), nullable=False)
    level: Mapped[str] = mapped_column(String(10), nullable=False)  # basso|medio|alto
    risk_count: Mapped[int] = mapped_column(Integer, nullable=False)
    protective_count: Mapped[int] = mapped_column(Integer, nullable=False)
    components: Mapped[str] = mapped_column(Text, nullable=False)   # JSON breakdown
    recommendations: Mapped[str | None] = mapped_column(Text)       # JSON list


# ---------------------------------------------------------------------------
# Care management: goals, monitoring, follow-ups, appointments
# ---------------------------------------------------------------------------
class HealthGoal(db.Model):
    __tablename__ = "health_goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    area: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    frequency_per_week: Mapped[int] = mapped_column(Integer, default=5)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|completed|abandoned
    created_by: Mapped[str] = mapped_column(String(10), default="patient")  # patient|doctor
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    checkins: Mapped[list["GoalCheckIn"]] = relationship(back_populates="goal")


class GoalCheckIn(db.Model):
    __tablename__ = "goal_checkins"

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("health_goals.id", ondelete="CASCADE"), nullable=False)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    week_of: Mapped[Date] = mapped_column(Date, nullable=False)  # Monday of the week
    completed_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    goal: Mapped[HealthGoal] = relationship(back_populates="checkins")


class MonitoringPlanItem(db.Model):
    """Remote-monitoring plan: which metric, how often, what target."""

    __tablename__ = "monitoring_plan_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)  # METRIC_CODES key
    frequency_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    target_text: Mapped[str | None] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FollowUp(db.Model):
    __tablename__ = "follow_ups"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    due_on: Mapped[Date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="chiamata")
    # chiamata | chat | visita
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # pending | done | cancelled
    outcome: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Appointment(db.Model):
    """Office/specialist visit booking — the escalation endpoint of the platform."""

    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doctor_id: Mapped[int | None] = mapped_column(ForeignKey("doctors.id"))
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    # visita_ambulatoriale | teleconsulto | visita_specialistica | esame
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="routine")
    # routine | urgente
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="proposto")
    # proposto | confermato | completato | annullato
    outcome: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_via: Mapped[str] = mapped_column(String(20), nullable=False, default="medico")
    # triage | medico | paziente
    # soft audit link (plain integer to avoid a circular FK with triage_assessments)
    triage_assessment_id: Mapped[int | None] = mapped_column(Integer)
    # when the appointment fulfils a pathway step
    pathway_step_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---------------------------------------------------------------------------
# Triage (call-centre decision support)
# ---------------------------------------------------------------------------
class TriageAssessment(db.Model):
    """Record of a symptom-driven protocol run by an operator on a call."""

    __tablename__ = "triage_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int | None] = mapped_column(
        ForeignKey("patients.id", ondelete="SET NULL"), index=True
    )
    operator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    protocol_code: Mapped[str] = mapped_column(String(40), nullable=False)
    complaint_label: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completata")
    # completata | bozza (a call suspended mid-protocol, resumable by the operator)
    answers: Mapped[str] = mapped_column(Text, nullable=False)  # JSON [{id,label,value,red_flag}]
    tier: Mapped[str] = mapped_column(String(12), nullable=False)  # rosso|arancione|verde
    disposition_code: Mapped[str] = mapped_column(String(30), nullable=False)
    disposition_label: Mapped[str] = mapped_column(String(200), nullable=False)
    disposition_detail: Mapped[str | None] = mapped_column(Text)
    red_flags: Mapped[str | None] = mapped_column(Text)  # JSON list
    risk_level_at_triage: Mapped[str | None] = mapped_column(String(10))
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"))
    followup_id: Mapped[int | None] = mapped_column(ForeignKey("follow_ups.id"))
    outcome_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


# ---------------------------------------------------------------------------
# Wellbeing instruments (validated questionnaires provided in the client evidence review)
# ---------------------------------------------------------------------------
class WellbeingAssessment(db.Model):
    __tablename__ = "wellbeing_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instrument: Mapped[str] = mapped_column(String(30), nullable=False)
    # wemwbs7 | bpaat | wsq | work
    answers: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    score: Mapped[float | None] = mapped_column(Float)
    category: Mapped[str | None] = mapped_column(Text)
    taken_on: Mapped[Date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---------------------------------------------------------------------------
# Care pathways (prevention / screening / follow-up / call-to-appointment)
# ---------------------------------------------------------------------------
class PathwayTemplate(db.Model):
    """Catalogue of standard pathways (data, not code: clinicians can add more)."""

    __tablename__ = "pathway_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    target_text: Mapped[str | None] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    steps: Mapped[list["PathwayTemplateStep"]] = relationship(
        order_by="PathwayTemplateStep.step_order", cascade="all, delete-orphan"
    )


class PathwayTemplateStep(db.Model):
    __tablename__ = "pathway_template_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("pathway_templates.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    # misurazione | screening | visita | educazione | richiamo
    offset_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # metric the worker can record from the app when the step is a measurement
    metric_code: Mapped[str | None] = mapped_column(String(40))


class CarePathway(db.Model):
    """A worker enrolled in a pathway template."""

    __tablename__ = "care_pathways"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[int] = mapped_column(
        ForeignKey("pathway_templates.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="attivo")
    # attivo | completato | interrotto
    started_on: Mapped[Date] = mapped_column(Date, nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    template: Mapped[PathwayTemplate] = relationship()
    steps: Mapped[list["CarePathwayStep"]] = relationship(
        order_by="CarePathwayStep.due_on", cascade="all, delete-orphan"
    )


class CarePathwayStep(db.Model):
    """One actionable step of an enrolled pathway."""

    __tablename__ = "care_pathway_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    pathway_id: Mapped[int] = mapped_column(
        ForeignKey("care_pathways.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pathway: Mapped[CarePathway] = relationship(viewonly=True, overlaps="steps")
    template_step_code: Mapped[str | None] = mapped_column(String(50))
    metric_code: Mapped[str | None] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    due_on: Mapped[Date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_attesa")
    # in_attesa | programmato | completato
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"))
    followup_id: Mapped[int | None] = mapped_column(ForeignKey("follow_ups.id"))
    completed_on: Mapped[Date | None] = mapped_column(Date)
    outcome: Mapped[str | None] = mapped_column(Text)


class SymptomCheckIn(db.Model):
    """Daily symptom micro-report from the worker (COVIDApp-style traffic light).

    Green = keep going; orange = operator contact; red = emergency escalation.
    Powers early detection and rapid protocol activation in the workplace.
    """

    __tablename__ = "symptom_checkins"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    taken_on: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    answers: Mapped[str] = mapped_column(Text, nullable=False)  # JSON answers
    tier: Mapped[str] = mapped_column(String(12), nullable=False)  # verde|arancione|rosso
    advice: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---------------------------------------------------------------------------
# Chat: persistent threads with bot + human handoff
# ---------------------------------------------------------------------------
class ChatThread(db.Model):
    __tablename__ = "chat_threads"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="coach")
    # coach: paziente ↔ assistente/operatore. clinical: medico ↔ assistente (contesto paziente)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="bot")
    # bot | waiting_operator | with_operator | closed
    handled_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    subject: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="thread",
        order_by="ChatMessage.created_at",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    thread_id: Mapped[int] = mapped_column(
        ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender: Mapped[str] = mapped_column(String(12), nullable=False)
    # patient | bot | doctor
    sender_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    thread: Mapped[ChatThread] = relationship(back_populates="messages")
