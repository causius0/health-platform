"""
Proactive health alerts system.
Analyzes patient data and generates actionable alerts for patients and doctors.
"""
from datetime import datetime, timedelta
from models import LabResult, Visit, Patient
import json


def count_risk_conditions(patient_id, recent_labs, condition_lower, db_session):
    """
    Count risk conditions for a patient based on lab values and clinical factors.

    Args:
        patient_id: Patient ID
        recent_labs: Recent lab results
        condition_lower: Patient condition in lowercase
        db_session: SQLAlchemy session

    Returns:
        Dictionary with risk conditions count and list of identified risks
    """
    risk_conditions = []

    # Risk 1: Poor glycemic control (HbA1c > 7.5%)
    hba1c_results = [lab for lab in recent_labs if lab.test_name == "HbA1c"]
    if hba1c_results:
        latest_hba1c = float(hba1c_results[0].test_value)
        if latest_hba1c > 7.5:
            risk_conditions.append("Controllo glicemico insufficiente (HbA1c > 7.5%)")

    # Risk 2: Elevated fasting glucose (>130 mg/dL)
    glucose_results = [lab for lab in recent_labs if "glicemia" in lab.test_name.lower() and "digiuno" in lab.test_name.lower()]
    if glucose_results:
        latest_glucose = int(glucose_results[0].test_value)
        if latest_glucose > 130:
            risk_conditions.append("Glicemia a digiuno elevata (>130 mg/dL)")

    # Risk 3: High cholesterol (LDL >130 mg/dL)
    ldl_results = [lab for lab in recent_labs if "LDL" in lab.test_name]
    if ldl_results:
        ldl = int(ldl_results[0].test_value)
        if ldl > 130:
            risk_conditions.append("Colesterolo LDL elevato (>130 mg/dL)")

    # Risk 4: High triglycerides (>150 mg/dL)
    trig_results = [lab for lab in recent_labs if "triglicer" in lab.test_name.lower()]
    if trig_results:
        trig = int(trig_results[0].test_value)
        if trig > 150:
            risk_conditions.append("Trigliceridi elevati (>150 mg/dL)")

    # Risk 5: Reduced kidney function (eGFR <60 or Creatinine >1.3)
    egfr_results = [lab for lab in recent_labs if lab.test_name == "eGFR"]
    creat_results = [lab for lab in recent_labs if lab.test_name == "Creatinina"]
    if egfr_results:
        egfr = int(egfr_results[0].test_value)
        if egfr < 60:
            risk_conditions.append("Ridotta funzionalità renale (eGFR <60)")
    elif creat_results:
        creat = float(creat_results[0].test_value)
        if creat > 1.3:
            risk_conditions.append("Ridotta funzionalità renale (Creatinina >1.3)")

    # Risk 6: High blood pressure (from visits or recent measurements)
    patient = db_session.query(Patient).get(patient_id)
    visits = db_session.query(Visit).filter_by(patient_id=patient_id).order_by(Visit.visit_date.desc()).limit(3).all()
    for visit in visits:
        if "mmHg" in visit.doctor_notes:
            # Extract systolic pressure
            import re
            bp_match = re.search(r'(\d{2,3})/(\d{2,3})', visit.doctor_notes)
            if bp_match:
                sys_bp = int(bp_match.group(1))
                if sys_bp > 140:
                    risk_conditions.append("Pressione arteriosa elevata (>140 mmHg)")
                    break

    # Risk 7: Obesity (if BMI data available - using proxies from lipid profile)
    total_chol = [lab for lab in recent_labs if "colesterolo totale" in lab.test_name.lower()]
    hdl = [lab for lab in recent_labs if "HDL" in lab.test_name]
    if total_chol and hdl:
        chol_ratio = float(total_chol[0].test_value) / float(hdl[0].test_value)
        if chol_ratio > 5:
            risk_conditions.append("Profilo lipidico ad alto rischio (ratio Colesterolo/HDL elevato)")

    return {
        "count": len(risk_conditions),
        "conditions": risk_conditions
    }


def analyze_patient_data(patient_id, db_session):
    """
    Analyze patient data and generate proactive health alerts.

    Args:
        patient_id: Patient ID
        db_session: SQLAlchemy session

    Returns:
        List of alert dictionaries with severity, message, and recommendations
    """
    patient = db_session.query(Patient).get(patient_id)
    if not patient:
        return []

    alerts = []
    current_time = datetime.now()

    # Get recent lab results (last 3 months)
    three_months_ago = datetime.now() - timedelta(days=90)
    recent_labs = db_session.query(LabResult)\
        .filter_by(patient_id=patient_id)\
        .filter(LabResult.date >= three_months_ago.strftime('%Y-%m-%d'))\
        .order_by(LabResult.date.desc())\
        .all()

    # Get recent visits
    recent_visits = db_session.query(Visit)\
        .filter_by(patient_id=patient_id)\
        .filter(Visit.visit_date >= three_months_ago.strftime('%Y-%m-%d'))\
        .order_by(Visit.visit_date.desc())\
        .all()

    # Parse medications
    try:
        medications = json.loads(patient.medications) if patient.medications else []
    except:
        medications = []

    condition_lower = patient.condition.lower()

    # ===== RISK THRESHOLD ESCALATION (NEW PREVENTION LOGIC) =====
    # Count risk conditions - if >3, trigger specific monitoring path
    risk_analysis = count_risk_conditions(patient_id, recent_labs, condition_lower, db_session)
    risk_count = risk_analysis["count"]
    risk_conditions = risk_analysis["conditions"]

    if risk_count > 3:
        # High risk - trigger specific monitoring path + occupational physician consultation
        alerts.append({
            "severity": "critical",
            "title": "Rischio elevato identificato",
            "message": f"Trovati {risk_count} fattori di rischio: {', '.join(risk_conditions[:3])}{'...' if len(risk_conditions) > 3 else ''}",
            "recommendation": "PERICOLO ELEVATO: Raccomandata consultazione immediata con il medico del lavoro per valutazione completa.",
            "action": "Consultare medico del lavoro urgentemente per percorso di monitoraggio specifico",
            "icon": "warning",
            "escalation_required": True,
            "monitoring_path": "high_risk",
            "action": "contact_occupational_physician",
            "timestamp": current_time.isoformat(),
            "trigger_value": f"{risk_count} fattori di rischio",
            "trigger_since": "Oggi"
        })
    elif risk_count >= 2:
        # Medium risk - enhanced monitoring
        alerts.append({
            "severity": "warning",
            "title": "Fattori di rischio multipli",
            "message": f"Trovati {risk_count} fattori di rischio: {', '.join(risk_conditions)}",
            "recommendation": "Monitoraggio rafforzato raccomandato. Consulta il medico per piano di prevenzione personalizzato.",
            "icon": "alert",
            "escalation_required": False,
            "monitoring_path": "enhanced_monitoring"
        })

    # ===== CRITICAL ALERTS =====

    # Check HbA1c for diabetes patients
    if "diabete" in condition_lower:
        hba1c_results = [lab for lab in recent_labs if lab.test_name == "HbA1c"]
        if hba1c_results:
            latest_hba1c = float(hba1c_results[0].test_value)
            if latest_hba1c > 8.0:
                alerts.append({
                    "severity": "critical",
                    "title": "HbA1c elevato - Attenzione immediata",
                    "message": f"Il tuo HbA1c è {latest_hba1c}%, significativamente sopra l'obiettivo. Contatta il dottore.",
                    "recommendation": "Chiama il dottore oggi stesso per discutere aggiustamenti alla terapia.",
                    "action": "Contatta il dottore immediatamente per valutare terapia",
                    "icon": "warning",
                    "timestamp": current_time.isoformat(),
                    "trigger_value": f"HbA1c {latest_hba1c}%",
                    "trigger_since": "Oggi"
                })
            elif latest_hba1c > 7.0:
                alerts.append({
                    "severity": "warning",
                    "title": "HbA1c sopra target",
                    "message": f"Il tuo HbA1c è {latest_hba1c}%, leggermente sopra l'obiettivo ideale (<7%).",
                    "recommendation": "Migliora la dieta e l'attività fisica. Controlla le glicemie più spesso.",
                    "icon": "alert"
                })

    # Check blood glucose for diabetes patients
    if "diabete" in condition_lower:
        glucose_results = [lab for lab in recent_labs if "glicemia" in lab.test_name.lower()]
        if glucose_results:
            latest_glucose = int(glucose_results[0].test_value)
            if latest_glucose > 200:
                alerts.append({
                    "severity": "critical",
                    "title": "Glicemia molto alta",
                    "message": f"Glicemia a digiuno: {latest_glucose} mg/dL - Valore critico.",
                    "recommendation": "Controlla la glicemia tra 2 ore. Se rimane alta, contatta il dottore.",
                    "icon": "warning"
                })
            elif latest_glucose > 140:
                alerts.append({
                    "severity": "warning",
                    "title": "Glicemia elevata",
                    "message": f"Glicemia: {latest_glucose} mg/dL - Sopra la norma.",
                    "recommendation": "Rivedi cosa hai mangiato. Controlla più spesso oggi.",
                    "icon": "alert"
                })

    # Check kidney function for diabetes patients
    if "diabete" in condition_lower:
        creatinine_results = [lab for lab in recent_labs if lab.test_name == "Creatinina"]
        egfr_results = [lab for lab in recent_labs if lab.test_name == "eGFR"]

        if creatinine_results:
            creatinine = float(creatinine_results[0].test_value)
            if creatinine > 1.3:
                alerts.append({
                    "severity": "warning",
                    "title": "Funzionalità renale da monitorare",
                    "message": f"Creatinina: {creatinine} mg/dL - Leggermente elevata.",
                    "recommendation": "Bevi più acqua. Riduci proteine animali. Controlla con il dottore.",
                    "icon": "kidney"
                })

        if egfr_results:
            egfr = int(egfr_results[0].test_value)
            if egfr < 60:
                alerts.append({
                    "severity": "critical",
                    "title": "Funzionalità renale ridotta",
                    "message": f"eGFR: {egfr} mL/min - Valore ridotto, possibile nefropatia.",
                    "recommendation": "Contatta il dottore entro 48 ore per valutazione nefrologica.",
                    "icon": "warning"
                })

    # Check blood pressure for hypertension patients
    if "ipertensione" in condition_lower:
        # Get latest blood pressure from visit notes
        for visit in recent_visits:
            if "mmHg" in visit.doctor_notes:
                if "180/110" in visit.doctor_notes or "180" in visit.doctor_notes:
                    alerts.append({
                        "severity": "critical",
                        "title": "Pressione molto alta",
                        "message": "Pressione arteriosa in range critico rilevata durante visita recente.",
                        "recommendation": "Contatta il dottore urgentemente. Non saltare i farmaci.",
                        "icon": "warning"
                    })
                    break
                elif "155/95" in visit.doctor_notes or "155" in visit.doctor_notes:
                    alerts.append({
                        "severity": "warning",
                        "title": "Pressione elevata",
                        "message": "Pressione arteriosa sopra target rilevata recentemente.",
                        "recommendation": "Controlla la pressione a casa. Riduci sale e stress.",
                        "icon": "alert"
                    })
                    break

    # Check cholesterol
    cholesterol_results = [lab for lab in recent_labs if "colesterolo" in lab.test_name.lower()]
    for lab in cholesterol_results:
        if "LDL" in lab.test_name:
            ldl = int(lab.test_value)
            if ldl > 130:
                alerts.append({
                    "severity": "warning",
                    "title": "Colesterolo LDL elevato",
                    "message": f"Colesterolo LDL: {ldl} mg/dL - Sopra l'obiettivo.",
                    "recommendation": "Riduci grassi saturi. Aumenta attività fisica. Parla con il dottore.",
                    "icon": "heart"
                })

    # ===== INFO ALERTS =====

    # Check for recent trends (compare with older results)
    if len(recent_labs) >= 2:
        oldest_hba1c = None
        newest_hba1c = None

        for lab in recent_labs[::-1]:  # Oldest first
            if lab.test_name == "HbA1c" and not oldest_hba1c:
                oldest_hba1c = float(lab.test_value)
            if lab.test_name == "HbA1c" and not newest_hba1c and oldest_hba1c:
                newest_hba1c = float(lab.test_value)
                break

        if oldest_hba1c and newest_hba1c:
            trend = newest_hba1c - oldest_hba1c
            if trend > 0.5:
                alerts.append({
                    "severity": "warning",
                    "title": "Tendenza HbA1c in aumento",
                    "message": f"HbA1c aumentato di {trend:.1f}% negli ultimi 3 mesi.",
                    "recommendation": "Intensifica il controllo glicemico. Parla con il dottore.",
                    "icon": "trend_up"
                })
            elif trend < -0.3:
                alerts.append({
                    "severity": "info",
                    "title": "Ottimo trend HbA1c",
                    "message": f"HbA1c migliorato di {abs(trend):.1f}% - Ottimo lavoro!",
                    "recommendation": "Continua così! Mantieni lo stile di vita attuale.",
                    "icon": "trend_down"
                })

    # Check medication reminders
    if any("insulina" in med.lower() for med in medications):
        alerts.append({
            "severity": "info",
            "title": "Promemoria insulina",
            "message": "Ricorda di prendere l'insulina regolarmente, tutti i giorni alla stessa ora.",
            "recommendation": "Imposta un allarme sul telefono se non l'hai già fatto.",
            "icon": "medication"
        })

    # Check for lifestyle reminders
    alerts.append({
        "severity": "info",
        "title": "Promemoria attività fisica",
        "message": "L'attività fisica regolare aiuta a controllare i valori.",
        "recommendation": "Obiettivo: 30 minuti di camminata al giorno, 5 giorni a settimana.",
        "icon": "activity"
    })

    # Check blood pressure monitoring for hypertension
    if "ipertensione" in condition_lower:
        alerts.append({
            "severity": "info",
            "title": "Monitoraggio pressione arteriosa",
            "message": "Controlla la pressione regolarmente a casa.",
            "recommendation": "Misura la pressione 2 volte al giorno e annota i valori.",
            "icon": "heart"
        })

    # Check foot care for diabetes patients
    if "diabete" in condition_lower:
        alerts.append({
            "severity": "info",
            "title": "Cura dei piedi",
            "message": "La prevenzione è importante per evitare problemi ai piedi.",
            "recommendation": "Ispeziona i piedi giornalmente per tagli, ferite o arrossamenti.",
            "icon": "warning"
        })

    # Regular medication reminder
    if medications:
        alerts.append({
            "severity": "info",
            "title": f"Promemoria farmaci ({len(medications)})",
            "message": "Prendi i farmaci regolarmente per ottenere i migliori risultati.",
            "recommendation": "Prendi tutti i farmaci alla stessa ora ogni giorno.",
            "icon": "medication"
        })

    # Check diet reminders
    if "diabete" in condition_lower:
        alerts.append({
            "severity": "info",
            "title": "Promemoria alimentazione",
            "message": "Una dieta equilibrata è fondamentale per gestire il diabete.",
            "recommendation": "Preferisci carboidrati complessi. Evita zuccheri semplici.",
            "icon": "diet"
        })

    # Check for missed follow-up
    if recent_visits:
        visit_date_str = recent_visits[0].visit_date.split()[0]  # Get just date portion
        last_visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d")
        days_since_visit = (datetime.now() - last_visit_date).days

        if days_since_visit > 60:
            alerts.append({
                "severity": "info",
                "title": "Visita di controllo raccomandata",
                "message": f" Sono passati {days_since_visit} giorni dall'ultima visita.",
                "recommendation": "Prenota una visita di controllo entro 2 settimane.",
                "icon": "calendar"
            })

    return alerts


def analyze_doctor_alerts(patient_id, db_session):
    """
    Generate doctor-focused alerts for patient monitoring.

    Args:
        patient_id: Patient ID
        db_session: SQLAlchemy session

    Returns:
        List of doctor alert dictionaries
    """
    patient = db_session.query(Patient).get(patient_id)
    if not patient:
        return []

    alerts = []

    # Get comprehensive lab data
    six_months_ago = datetime.now() - timedelta(days=180)
    all_labs = db_session.query(LabResult)\
        .filter_by(patient_id=patient_id)\
        .filter(LabResult.date >= six_months_ago.strftime('%Y-%m-%d'))\
        .order_by(LabResult.date.desc())\
        .all()

    # Get visits
    visits = db_session.query(Visit)\
        .filter_by(patient_id=patient_id)\
        .order_by(Visit.visit_date.desc())\
        .all()

    condition_lower = patient.condition.lower()

    # ===== DOCTOR-SPECIFIC ALERTS =====

    # Critical lab values needing attention
    if "diabete" in condition_lower:
        hba1c_results = [lab for lab in all_labs if lab.test_name == "HbA1c"]
        if hba1c_results:
            latest_hba1c = float(hba1c_results[0].test_value)
            if latest_hba1c > 8.0:
                alerts.append({
                    "severity": "critical",
                    "title": f"{patient.first_name} {patient.last_name} - HbA1c critico",
                    "message": f"HbA1c: {latest_hba1c}% - Richiede intervento immediato.",
                    "action": "Contattare paziente oggi. Considerare raddoppiare metformina o aggiungere insulina.",
                    "patient_id": patient_id,
                    "icon": "critical"
                })

    # Kidney function monitoring
    creatinine_results = [lab for lab in all_labs if "creatinina" in lab.test_name.lower() or "egfr" in lab.test_name.lower()]
    for lab in creatinine_results:
        if "creatinina" in lab.test_name.lower():
            value = float(lab.test_value)
            if value > 1.3:
                alerts.append({
                    "severity": "warning",
                    "title": f"{patient.first_name} - Funzionalità renale",
                    "message": f"Creatinina: {value} mg/dL - Possibile nefropatia.",
                    "action": "Valutare referto nefrologico e aggiustamento farmaci.",
                    "patient_id": patient_id,
                    "icon": "kidney"
                })

    # Treatment adherence alerts
    if visits:
        last_visit = visits[0]
        visit_date_str = last_visit.visit_date.split()[0]  # Get just date portion
        last_visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d")
        days_since_visit = (datetime.now() - last_visit_date).days

        if days_since_visit > 90:
            alerts.append({
                "severity": "info",
                "title": f"{patient.first_name} - Follow-up mancante",
                "message": f"Paziente senza visita da {days_since_visit} giorni.",
                "action": "Contattare paziente per prenotare visita di controllo.",
                "patient_id": patient_id,
                "icon": "calendar"
            })

    # Trend analysis for doctor
    if len(all_labs) >= 4:
        # Get HbA1c trend
        hba1c_values = [float(lab.test_value) for lab in all_labs if lab.test_name == "HbA1c"]
        if len(hba1c_values) >= 2:
            avg_hba1c = sum(hba1c_values) / len(hba1c_values)
            if avg_hba1c > 7.5:
                alerts.append({
                    "severity": "warning",
                    "title": f"{patient.first_name} - Controllo glicemico insufficiente",
                    "message": f"HbA1c medio 6 mesi: {avg_hba1c:.1f}%",
                    "action": "Riconsiderare terapia completamente. Educazione intensiva.",
                    "patient_id": patient_id,
                    "icon": "trend_up"
                })

    # Medication optimization alerts
    if "diabete" in condition_lower:
        glucose_results = [lab for lab in all_labs if "glicemia" in lab.test_name.lower()]
        high_glucose_count = sum(1 for lab in glucose_results if int(lab.test_value) > 140)

        if len(glucose_results) > 0 and high_glucose_count / len(glucose_results) > 0.6:
            alerts.append({
                "severity": "warning",
                "title": f"{patient.first_name} - Glicemie frequentemente elevate",
                "message": f"{high_glucose_count}/{len(glucose_results)} glicemie sopra 140 mg/dL.",
                "action": "Valutare aderenza terapia o aggiustamento dosaggio.",
                "patient_id": patient_id,
                "icon": "glucose"
            })

    return alerts


def get_all_doctor_alerts(doctor_id, db_session):
    """
    Get all alerts for all patients under a doctor.

    Args:
        doctor_id: Doctor user ID
        db_session: SQLAlchemy session

    Returns:
        List of all alerts for the doctor's patients
    """
    # Get all patients for this doctor
    patients = db_session.query(Patient).filter_by(doctor_id=doctor_id).all()

    all_alerts = []
    for patient in patients:
        patient_alerts = analyze_doctor_alerts(patient.id, db_session)
        all_alerts.extend(patient_alerts)

    # Sort by severity (critical first, then warning, then info)
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    all_alerts.sort(key=lambda x: severity_order.get(x.get("severity", "info"), 3))

    return all_alerts
