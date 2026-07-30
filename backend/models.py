"""
Database models for the health platform.
Includes User, Patient, Doctor, LabResult, Visit, ChatSession, ChatMessage models.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, CheckConstraint, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

# Database configuration
DATABASE_URL = 'sqlite:///database.db'
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


class User(Base):
    """User model for authentication."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # 'doctor' or 'patient'
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class Doctor(Base):
    """Doctor profile model."""
    __tablename__ = 'doctors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    specialization = Column(String(100))

    user = relationship("User", backref="doctor_profile")

    def __repr__(self):
        return f"<Doctor(id={self.id}, name='{self.first_name} {self.last_name}')>"


class Patient(Base):
    """Patient profile model with chronic conditions."""
    __tablename__ = 'patients'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    birth_date = Column(String(10))  # ISO format: YYYY-MM-DD
    condition = Column(String(50), nullable=False)  # 'diabetes', 'hypertension', etc.
    medications = Column(Text)  # JSON array of medication names
    doctor_id = Column(Integer, ForeignKey('users.id'))
    anamnesis = Column(Text)  # JSON: lifestyle anamnesis (risk + protective factors)

    user = relationship("User", backref="patient_profile", foreign_keys=[user_id])
    doctor = relationship("User", foreign_keys=[doctor_id])

    def __repr__(self):
        return f"<Patient(id={self.id}, name='{self.first_name} {self.last_name}', condition='{self.condition}')>"


class LabResult(Base):
    """Laboratory test results for patients."""
    __tablename__ = 'lab_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    test_name = Column(String(100), nullable=False)
    test_value = Column(String(50), nullable=False)
    unit = Column(String(20))
    reference_range = Column(String(50))
    date = Column(String(10), nullable=False)  # ISO format: YYYY-MM-DD
    notes = Column(Text)

    patient = relationship("Patient", backref="lab_results")

    def __repr__(self):
        return f"<LabResult(id={self.id}, test_name='{self.test_name}', value='{self.test_value}')>"


class Visit(Base):
    """Doctor visit records."""
    __tablename__ = 'visits'

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    visit_date = Column(String(10), nullable=False)  # ISO format: YYYY-MM-DD
    visit_type = Column(String(20), nullable=False)  # 'controllo', 'urgenza', 'followup'
    doctor_notes = Column(Text)
    diagnosis = Column(Text)

    __table_args__ = (
        CheckConstraint("visit_type IN ('controllo', 'urgenza', 'followup')", name='check_visit_type'),
    )

    patient = relationship("Patient", backref="visits")

    def __repr__(self):
        return f"<Visit(id={self.id}, date='{self.visit_date}', type='{self.visit_type}')>"


class ChatSession(Base):
    """Chat session for transient message storage."""
    __tablename__ = 'chat_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    patient_id = Column(Integer, ForeignKey('patients.id'))  # For doctor inquiries about patients
    started_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="chat_sessions")
    patient = relationship("Patient", backref="chat_sessions")

    def __repr__(self):
        return f"<ChatSession(id={self.id}, user_id={self.user_id})>"


class ChatMessage(Base):
    """Chat messages (transient - cleared on logout)."""
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", backref="messages")

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, role='{self.role}', timestamp='{self.timestamp}')>"


class HealthGoal(Base):
    """Worker-set prevention goals (the concrete, measurable output of a guided path)."""
    __tablename__ = 'health_goals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    area = Column(String(30), nullable=False)  # physical_activity, nutrition, smoking, alcohol, sleep, stress
    title = Column(String(200), nullable=False)
    frequency_per_week = Column(Integer, default=5)
    status = Column(String(20), default='active')  # active, completed, abandoned
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    patient = relationship("Patient", backref="goals")

    def __repr__(self):
        return f"<HealthGoal(id={self.id}, patient_id={self.patient_id}, area='{self.area}')>"


class GoalCheckIn(Base):
    """Weekly check-in against a goal (the adherence tracker)."""
    __tablename__ = 'goal_checkins'

    id = Column(Integer, primary_key=True, autoincrement=True)
    goal_id = Column(Integer, ForeignKey('health_goals.id'), nullable=False)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    week_of = Column(String(10), nullable=False)  # ISO date (Monday of the week)
    completed_days = Column(Integer, nullable=False, default=0)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    goal = relationship("HealthGoal", backref="checkins")

    def __repr__(self):
        return f"<GoalCheckIn(id={self.id}, goal_id={self.goal_id}, week='{self.week_of}', days={self.completed_days})>"
