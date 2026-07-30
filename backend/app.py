"""
Flask application with REST API endpoints for health platform.
Includes authentication, patient data, doctor endpoints, and chatbot integration.
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from datetime import timedelta
import os

from models import Base, User, Doctor, Patient, LabResult, Visit, ChatSession, ChatMessage, HealthGoal, GoalCheckIn
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from auth import login_user, get_current_user, cleanup_chat_on_logout
from chatbot import get_llm_response, build_patient_context
from alerts import analyze_patient_data, analyze_doctor_alerts, get_all_doctor_alerts

# Flask app setup
app = Flask(__name__)
CORS(app, supports_credentials=True)

# JWT configuration
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'feem-salute-secret-key-2026')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
jwt = JWTManager(app)

# Database setup
engine = create_engine('sqlite:///database.db', echo=False)
Base.metadata.create_all(engine)
Session = scoped_session(sessionmaker(bind=engine))


# Helper function to get database session
def get_db_session():
    return Session()


# ==================== Authentication Endpoints ====================

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username e password richiesti'}), 400

    token, result, user = login_user(username, password)

    if result == 'success':
        return jsonify({
            'token': token,
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role
            }
        }), 200
    else:
        return jsonify({'error': result}), 401


@app.route('/api/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user and clear chat data (privacy requirement)."""
    identity = get_jwt_identity()
    user_id = int(identity)  # identity is now user_id as string

    # Clear all chat data for this user
    cleanup_chat_on_logout(user_id)

    return jsonify({'message': 'Logout successful, chat data cleared'}), 200


@app.route('/api/me', methods=['GET'])
@jwt_required()
def get_me():
    """Get current user info."""
    user = get_current_user()

    if not user:
        return jsonify({'error': 'Utente non trovato'}), 404

    response = {
        'id': user.id,
        'username': user.username,
        'role': user.role
    }

    # Add role-specific data
    if user.role == 'doctor':
        session = get_db_session()
        doctor = session.query(Doctor).filter_by(user_id=user.id).first()
        session.close()

        if doctor:
            response.update({
                'first_name': doctor.first_name,
                'last_name': doctor.last_name,
                'specialization': doctor.specialization
            })

    elif user.role == 'patient':
        session = get_db_session()
        patient = session.query(Patient).filter_by(user_id=user.id).first()
        session.close()

        if patient:
            response.update({
                'patient_id': patient.id,
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'condition': patient.condition,
                'medications': patient.medications
            })

    return jsonify(response), 200


# ==================== Patient Data Endpoints ====================

@app.route('/api/patient/<int:patient_id>', methods=['GET'])
@jwt_required()
def get_patient(patient_id):
    """Get patient profile."""
    session = get_db_session()
    patient = session.query(Patient).get(patient_id)

    if not patient:
        session.close()
        return jsonify({'error': 'Paziente non trovato'}), 404

    # Check authorization: patient can only see own data, doctor can see assigned patients
    current_user = get_current_user()
    if current_user.role == 'patient' and patient.user_id != current_user.id:
        session.close()
        return jsonify({'error': 'Non autorizzato'}), 403

    response = {
        'id': patient.id,
        'first_name': patient.first_name,
        'last_name': patient.last_name,
        'birth_date': patient.birth_date,
        'condition': patient.condition,
        'medications': patient.medications,
        'doctor_id': patient.doctor_id
    }

    session.close()
    return jsonify(response), 200


@app.route('/api/patient/<int:patient_id>/exams', methods=['GET'])
@jwt_required()
def get_patient_exams(patient_id):
    """Get recent lab results for patient (last 6 months)."""
    session = get_db_session()
    patient = session.query(Patient).get(patient_id)

    if not patient:
        session.close()
        return jsonify({'error': 'Paziente non trovato'}), 404

    # Authorization check
    current_user = get_current_user()
    if current_user.role == 'patient' and patient.user_id != current_user.id:
        session.close()
        return jsonify({'error': 'Non autorizzato'}), 403

    # Get lab results, ordered by date desc
    lab_results = session.query(LabResult)\
        .filter_by(patient_id=patient_id)\
        .order_by(LabResult.date.desc())\
        .all()

    exams = [{
        'id': lr.id,
        'test_name': lr.test_name,
        'test_value': lr.test_value,
        'unit': lr.unit,
        'reference_range': lr.reference_range,
        'date': lr.date,
        'notes': lr.notes
    } for lr in lab_results]

    session.close()
    return jsonify(exams), 200


@app.route('/api/patient/<int:patient_id>/visits', methods=['GET'])
@jwt_required()
def get_patient_visits(patient_id):
    """Get visit history for patient."""
    session = get_db_session()
    patient = session.query(Patient).get(patient_id)

    if not patient:
        session.close()
        return jsonify({'error': 'Paziente non trovato'}), 404

    # Authorization check
    current_user = get_current_user()
    if current_user.role == 'patient' and patient.user_id != current_user.id:
        session.close()
        return jsonify({'error': 'Non autorizzato'}), 403

    # Get visits, ordered by date desc
    visits = session.query(Visit)\
        .filter_by(patient_id=patient_id)\
        .order_by(Visit.visit_date.desc())\
        .all()

    visit_list = [{
        'id': v.id,
        'visit_date': v.visit_date,
        'visit_type': v.visit_type,
        'doctor_notes': v.doctor_notes,
        'diagnosis': v.diagnosis
    } for v in visits]

    session.close()
    return jsonify(visit_list), 200


@app.route('/api/patient/<int:patient_id>/history', methods=['GET'])
@jwt_required()
def get_patient_history(patient_id):
    """Get full 6-month history for patient (labs + visits)."""
    session = get_db_session()
    patient = session.query(Patient).get(patient_id)

    if not patient:
        session.close()
        return jsonify({'error': 'Paziente non trovato'}), 404

    # Authorization check (doctors only)
    current_user = get_current_user()
    if current_user.role != 'doctor':
        session.close()
        return jsonify({'error': 'Non autorizzato'}), 403

    # Get lab results and visits
    lab_results = session.query(LabResult)\
        .filter_by(patient_id=patient_id)\
        .order_by(LabResult.date.desc())\
        .all()

    visits = session.query(Visit)\
        .filter_by(patient_id=patient_id)\
        .order_by(Visit.visit_date.desc())\
        .all()

    exams = [{
        'id': lr.id,
        'test_name': lr.test_name,
        'test_value': lr.test_value,
        'unit': lr.unit,
        'reference_range': lr.reference_range,
        'date': lr.date,
        'notes': lr.notes
    } for lr in lab_results]

    visit_list = [{
        'id': v.id,
        'visit_date': v.visit_date,
        'visit_type': v.visit_type,
        'doctor_notes': v.doctor_notes,
        'diagnosis': v.diagnosis
    } for v in visits]

    session.close()
    return jsonify({'exams': exams, 'visits': visit_list}), 200


# ==================== Doctor Endpoints ====================

@app.route('/api/doctor/patients', methods=['GET'])
@jwt_required()
def get_doctor_patients():
    """Get all patients assigned to doctor."""
    current_user = get_current_user()

    if current_user.role != 'doctor':
        return jsonify({'error': 'Non autorizzato'}), 403

    session = get_db_session()

    # Get doctor profile
    doctor = session.query(Doctor).filter_by(user_id=current_user.id).first()
    if not doctor:
        session.close()
        return jsonify({'error': 'Profilo dottore non trovato'}), 404

    # Get all patients (demo: all assigned to this doctor)
    patients = session.query(Patient).all()

    patient_list = []
    for p in patients:
        # Determine primary metric based on condition
        condition_lower = p.condition.lower()
        medications_lower = p.medications.lower() if p.medications else ''

        # Check if diabetes patient
        is_diabetes = 'diabete' in condition_lower or 'insulina' in medications_lower or 'metformin' in medications_lower

        if is_diabetes:
            # Get most recent HbA1c for diabetes patients
            primary_lab = session.query(LabResult)\
                .filter_by(patient_id=p.id)\
                .filter(LabResult.test_name == 'HbA1c')\
                .order_by(LabResult.date.desc())\
                .first()
            last_primary_value = primary_lab.test_value if primary_lab else None
            last_primary_unit = '%' if primary_lab else ''

        else:
            # For hypertension and others, get creatinine/kidney function
            primary_lab = session.query(LabResult)\
                .filter_by(patient_id=p.id)\
                .filter(LabResult.test_name == 'Creatinina')\
                .order_by(LabResult.date.desc())\
                .first()
            last_primary_value = primary_lab.test_value if primary_lab else None
            last_primary_unit = ' mg/dL' if primary_lab else ''

        # Get most recent visit
        latest_visit = session.query(Visit)\
            .filter_by(patient_id=p.id)\
            .order_by(Visit.visit_date.desc())\
            .first()

        patient_data = {
            'id': p.id,
            'first_name': p.first_name,
            'last_name': p.last_name,
            'condition': p.condition,
            'medications': p.medications,
            'last_hba1c': last_primary_value if is_diabetes else None,  # For backward compatibility
            'last_creatinine': last_primary_value if not is_diabetes else None,
            'last_visit_date': latest_visit.visit_date if latest_visit else None
        }
        patient_list.append(patient_data)

    session.close()
    return jsonify(patient_list), 200


# ==================== Chatbot Endpoints ====================

@app.route('/api/chat/start', methods=['POST'])
@jwt_required()
def start_chat_session():
    """Start new chat session."""
    identity = get_jwt_identity()
    user_id = int(identity)  # identity is now user_id as string

    session = get_db_session()

    # Get user from database to get role
    user = session.query(User).get(user_id)
    if not user:
        session.close()
        return jsonify({'error': 'Utente non trovato'}), 404

    user_role = user.role

    # For doctors, patient_id comes from request
    data = request.get_json() or {}
    patient_id = data.get('patient_id')

    # Create new chat session
    chat_session = ChatSession(
        user_id=user_id,
        patient_id=patient_id if user_role == 'doctor' else None
    )

    session.add(chat_session)
    session.commit()
    session_id = chat_session.id
    session.close()

    return jsonify({'session_id': session_id, 'message': 'Chat session started'}), 200


@app.route('/api/chat/message', methods=['POST'])
@jwt_required()
def send_chat_message():
    """Send message to chatbot and get response."""
    identity = get_jwt_identity()
    user_id = int(identity)  # identity is now user_id as string

    data = request.get_json()
    message = data.get('message')
    session_id = data.get('session_id')

    if not message or not session_id:
        return jsonify({'error': 'Message e session_id richiesti'}), 400

    db = get_db_session()

    # Verify chat session belongs to user
    chat_session = db.query(ChatSession).get(session_id)
    if not chat_session or chat_session.user_id != user_id:
        db.close()
        return jsonify({'error': 'Sessione non valida'}), 403

    # Get user role from database
    user = db.query(User).get(user_id)
    if not user:
        db.close()
        return jsonify({'error': 'Utente non trovato'}), 404

    user_role = user.role

    # Save user message
    user_message = ChatMessage(
        session_id=session_id,
        role='user',
        content=message
    )
    db.add(user_message)
    db.commit()

    # Build context and get LLM response
    patient_id = chat_session.patient_id if user_role == 'doctor' else None

    # For patients, get their own patient_id
    if user_role == 'patient':
        patient = db.query(Patient).filter_by(user_id=user_id).first()
        if patient:
            patient_id = patient.id

    context = build_patient_context(patient_id, user_role, db)
    response = get_llm_response(message, context, user_role)

    # Save assistant message
    assistant_message = ChatMessage(
        session_id=session_id,
        role='assistant',
        content=response
    )
    db.add(assistant_message)
    db.commit()

    db.close()
    return jsonify({'response': response}), 200


@app.route('/api/chat/session', methods=['DELETE'])
@jwt_required()
def delete_chat_session():
    """Delete current chat session and all messages."""
    identity = get_jwt_identity()
    user_id = int(identity)  # identity is now user_id as string

    data = request.get_json() or {}
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id richiesto'}), 400

    db = get_db_session()

    # Verify ownership
    chat_session = db.query(ChatSession).get(session_id)
    if not chat_session or chat_session.user_id != user_id:
        db.close()
        return jsonify({'error': 'Non autorizzato'}), 403

    # Delete all messages
    db.query(ChatMessage).filter_by(session_id=session_id).delete()

    # Delete session
    db.delete(chat_session)
    db.commit()

    db.close()
    return jsonify({'message': 'Sessione cancellata'}), 200


# ==================== Alerts Endpoints ====================

@app.route('/api/patient/<int:patient_id>/alerts', methods=['GET'])
@jwt_required()
def get_patient_alerts(patient_id):
    """Get proactive health alerts for patient."""
    session = get_db_session()
    patient = session.query(Patient).get(patient_id)

    if not patient:
        session.close()
        return jsonify({'error': 'Paziente non trovato'}), 404

    # Authorization check
    current_user = get_current_user()
    if current_user.role == 'patient' and patient.user_id != current_user.id:
        session.close()
        return jsonify({'error': 'Non autorizzato'}), 403

    # Generate alerts based on patient data
    alerts = analyze_patient_data(patient_id, session)

    session.close()
    return jsonify(alerts), 200


@app.route('/api/doctor/alerts', methods=['GET'])
@jwt_required()
def get_doctor_alerts():
    """Get all proactive alerts for doctor's patients."""
    current_user = get_current_user()

    if current_user.role != 'doctor':
        return jsonify({'error': 'Non autorizzato'}), 403

    session = get_db_session()

    # Get all alerts for this doctor's patients
    alerts = get_all_doctor_alerts(current_user.id, session)

    session.close()
    return jsonify(alerts), 200


@app.route('/api/doctor/patient/<int:patient_id>/alerts', methods=['GET'])
@jwt_required()
def get_doctor_patient_alerts(patient_id):
    """Get doctor-focused alerts for specific patient."""
    current_user = get_current_user()

    if current_user.role != 'doctor':
        return jsonify({'error': 'Non autorizzato'}), 403

    session = get_db_session()
    patient = session.query(Patient).get(patient_id)

    if not patient:
        session.close()
        return jsonify({'error': 'Paziente non trovato'}), 404

    # Generate doctor-specific alerts
    alerts = analyze_doctor_alerts(patient_id, session)

    session.close()
    return jsonify(alerts), 200


# ==================== Prevention Layer (Goals / Check-ins / Anamnesis) ====================

def _serialize_goal(g, db):
    checkins = db.query(GoalCheckIn).filter_by(goal_id=g.id).order_by(GoalCheckIn.week_of.desc()).all()
    return {
        'id': g.id,
        'patient_id': g.patient_id,
        'area': g.area,
        'title': g.title,
        'frequency_per_week': g.frequency_per_week,
        'status': g.status,
        'created_at': g.created_at.isoformat() if g.created_at else None,
        'completed_at': g.completed_at.isoformat() if g.completed_at else None,
        'checkins': [
            {'id': c.id, 'week_of': c.week_of, 'completed_days': c.completed_days}
            for c in checkins
        ],
    }


@app.route('/api/patient/<int:patient_id>/goals', methods=['GET'])
@jwt_required()
def get_patient_goals(patient_id):
    """Get all prevention goals for a patient (worker or authorized doctor)."""
    db = get_db_session()
    patient = db.query(Patient).get(patient_id)
    if not patient:
        db.close()
        return jsonify({'error': 'Paziente non trovato'}), 404
    current_user = get_current_user()
    if current_user.role == 'patient' and patient.user_id != current_user.id:
        db.close()
        return jsonify({'error': 'Non autorizzato'}), 403
    goals = db.query(HealthGoal).filter_by(patient_id=patient_id).order_by(HealthGoal.created_at.desc()).all()
    result = [_serialize_goal(g, db) for g in goals]
    db.close()
    return jsonify(result), 200


@app.route('/api/goals', methods=['POST'])
@jwt_required()
def create_goal():
    """Create a new prevention goal (the concrete output of a guided path)."""
    db = get_db_session()
    data = request.get_json() or {}
    current_user = get_current_user()
    # Resolve patient: workers act on themselves; doctors act on a named patient
    if current_user.role == 'patient':
        patient = db.query(Patient).filter_by(user_id=current_user.id).first()
        if not patient:
            db.close()
            return jsonify({'error': 'Profilo paziente non trovato'}), 404
        patient_id = patient.id
    else:
        patient_id = data.get('patient_id')
    if not patient_id:
        db.close()
        return jsonify({'error': 'patient_id richiesto'}), 400
    g = HealthGoal(
        patient_id=patient_id,
        area=data.get('area', 'physical_activity'),
        title=data.get('title', 'Nuovo obiettivo'),
        frequency_per_week=int(data.get('frequency_per_week', 5)),
        status='active',
    )
    db.add(g)
    db.commit()
    result = _serialize_goal(g, db)
    db.close()
    return jsonify(result), 201


@app.route('/api/goals/<int:goal_id>', methods=['PATCH'])
@jwt_required()
def update_goal(goal_id):
    """Update a goal (status, frequency)."""
    db = get_db_session()
    g = db.query(HealthGoal).get(goal_id)
    if not g:
        db.close()
        return jsonify({'error': 'Obiettivo non trovato'}), 404
    data = request.get_json() or {}
    if 'status' in data:
        g.status = data['status']
        if data['status'] == 'completed':
            g.completed_at = datetime.utcnow()
    if 'frequency_per_week' in data:
        g.frequency_per_week = int(data['frequency_per_week'])
    db.commit()
    result = _serialize_goal(g, db)
    db.close()
    return jsonify(result), 200


@app.route('/api/goals/<int:goal_id>/checkin', methods=['POST'])
@jwt_required()
def goal_checkin(goal_id):
    """Record a weekly check-in against a goal (adherence tracker)."""
    db = get_db_session()
    from datetime import datetime as _dt
    g = db.query(HealthGoal).get(goal_id)
    if not g:
        db.close()
        return jsonify({'error': 'Obiettivo non trovato'}), 404
    data = request.get_json() or {}
    completed_days = int(data.get('completed_days', 0))
    week_of = data.get('week_of')
    if not week_of:
        # default to Monday of current week
        t = _dt.utcnow().date()
        week_of = (t - timedelta(days=t.weekday())).isoformat()
    # upsert check-in for this goal+week
    existing = db.query(GoalCheckIn).filter_by(goal_id=goal_id, week_of=week_of).first()
    if existing:
        existing.completed_days = completed_days
        checkin = existing
    else:
        checkin = GoalCheckIn(goal_id=goal_id, patient_id=g.patient_id,
                              week_of=week_of, completed_days=completed_days)
        db.add(checkin)
    db.commit()
    db.close()
    return jsonify({'ok': True, 'week_of': week_of, 'completed_days': completed_days}), 201


@app.route('/api/patient/<int:patient_id>/anamnesis', methods=['GET', 'PUT'])
@jwt_required()
def patient_anamnesis(patient_id):
    """Get or update the lifestyle anamnesis (risk + protective factors)."""
    db = get_db_session()
    patient = db.query(Patient).get(patient_id)
    if not patient:
        db.close()
        return jsonify({'error': 'Paziente non trovato'}), 404
    current_user = get_current_user()
    if current_user.role == 'patient' and patient.user_id != current_user.id:
        db.close()
        return jsonify({'error': 'Non autorizzato'}), 403
    if request.method == 'PUT':
        data = request.get_json() or {}
        patient.anamnesis = data.get('anamnesis')
        db.commit()
    db.close()
    import json as _json
    try:
        parsed = _json.loads(patient.anamnesis) if patient.anamnesis else None
    except Exception:
        parsed = None
    return jsonify({'anamnesis': parsed}), 200


@app.route('/api/doctor/activity', methods=['GET'])
@jwt_required()
def doctor_activity_feed():
    """Cross-patient feed of worker prevention activity (the interoperability hook).

    Surfaces goals set and check-ins recorded, newest first, so the operator can
    see what workers are actually doing between visits.
    """
    current_user = get_current_user()
    if current_user.role != 'doctor':
        return jsonify({'error': 'Non autorizzato'}), 403
    db = get_db_session()
    patients = db.query(Patient).filter_by(doctor_id=current_user.id).all()
    pmap = {p.id: p for p in patients}
    items = []
    # recent goals
    for g in db.query(HealthGoal).filter(HealthGoal.patient_id.in_(list(pmap))).order_by(HealthGoal.created_at.desc()).limit(50).all():
        items.append({
            'type': 'goal',
            'patient_id': g.patient_id,
            'patient_name': f"{pmap[g.patient_id].first_name} {pmap[g.patient_id].last_name}",
            'title': g.title,
            'area': g.area,
            'status': g.status,
            'ts': g.created_at.isoformat() if g.created_at else None,
            'detail': f"Obiettivo: {g.title} ({g.frequency_per_week}x/sett)",
        })
    # recent check-ins
    for c in db.query(GoalCheckIn).filter(GoalCheckIn.patient_id.in_(list(pmap))).order_by(GoalCheckIn.created_at.desc()).limit(50).all():
        g = db.query(HealthGoal).get(c.goal_id)
        pct = int(round(100 * c.completed_days / g.frequency_per_week)) if g else 0
        items.append({
            'type': 'checkin',
            'patient_id': c.patient_id,
            'patient_name': f"{pmap[c.patient_id].first_name} {pmap[c.patient_id].last_name}",
            'title': g.title if g else 'Obiettivo',
            'area': g.area if g else None,
            'status': 'completed' if pct >= 80 else 'active',
            'ts': c.created_at.isoformat() if c.created_at else None,
            'detail': f"Aderenza {pct}% ({c.completed_days}/{g.frequency_per_week} giorni)",
            'pct': pct,
        })
    items.sort(key=lambda x: x['ts'] or '', reverse=True)
    db.close()
    return jsonify(items[:40]), 200


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Risorsa non trovata'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Errore interno del server'}), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=True)
