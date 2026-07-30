"""
Seed data for the health platform demo.
Creates 1 doctor and 5 patients with chronic conditions, comprehensive medical histories with 100+ data points per patient.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
from models import Base, User, Doctor, Patient, LabResult, Visit, ChatSession, ChatMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import bcrypt
import random

# Database setup
engine = create_engine('sqlite:///database.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Clear existing data
session.query(ChatMessage).delete()
session.query(ChatSession).delete()
session.query(LabResult).delete()
session.query(Visit).delete()
session.query(Patient).delete()
session.query(Doctor).delete()
session.query(User).delete()
session.commit()

# Password hash (shared password: FEEMsalute2026!)
password_hash = bcrypt.hashpw("FEEMsalute2026!".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Create doctor user and profile
doctor_user = User(
    username="doctor",
    password_hash=password_hash,
    role="doctor"
)
session.add(doctor_user)
session.commit()

doctor = Doctor(
    user_id=doctor_user.id,
    first_name="Marco",
    last_name="Bianchi",
    specialization="Medicina interna"
)
session.add(doctor)
session.commit()

# Patient data with comprehensive medical information
patients_data = [
    {
        "username": "patient1",
        "first_name": "Mario",
        "last_name": "Rossi",
        "birth_date": "1979-03-15",  # 45 years old
        "condition": "diabete tipo 2",
        "medications": '["Metformina 500mg 2x giorno", "Lisinopril 10mg 1x giorno", "Aspirina 81mg 1x giorno"]',
        "allergies": '["Penicillina", "Pollini"]',
        "family_history": '{"father": "Diabete tipo 2", "mother": "Ipertensione", "siblings": "Nessuna patologia cronica"}',
        "blood_type": "A+",
        "height_cm": 175,
        "weight_kg": 82
    },
    {
        "username": "patient2",
        "first_name": "Laura",
        "last_name": "Bianchi",
        "birth_date": "1972-08-22",  # 52 years old
        "condition": "ipertensione",
        "medications": '["Amlodipina 5mg 1x giorno", "Idroclorotiazide 12.5mg 1x giorno", "Omeprazolo 20mg 1x giorno"]',
        "allergies": '["NSAIDs", "Lattosio"]',
        "family_history": '{"father": "Cardiopatia coronarica", "mother": "Ipertensione", "siblings": "Diabete tipo 2"}',
        "blood_type": "B+",
        "height_cm": 162,
        "weight_kg": 68
    },
    {
        "username": "patient3",
        "first_name": "Giuseppe",
        "last_name": "Verdi",
        "birth_date": "1986-11-30",  # 38 years old
        "condition": "diabete tipo 2",
        "medications": '["Metformina 850mg 2x giorno", "Insulina glargine 10 unità sera", "Atorvastatina 20mg 1x giorno"]',
        "allergies": '["Nessuna"]',
        "family_history": '{"father": "Diabete tipo 2", "mother": "Obesità", "siblings": "Diabete tipo 1"}',
        "blood_type": "O+",
        "height_cm": 180,
        "weight_kg": 95
    },
    {
        "username": "patient4",
        "first_name": "Anna",
        "last_name": "Ferrari",
        "birth_date": "1976-05-10",  # 48 years old
        "condition": "ipertensione",
        "medications": '["Lisinopril 20mg 1x giorno", "Amlodipina 5mg 1x giorno", "Metoprololo 50mg 2x giorno"]',
        "allergies": '["Solfonamidi", "Noci"]',
        "family_history": '{"father": "Ictus", "mother": "Ipertensione", "siblings": "Cardiopatia"}',
        "blood_type": "AB+",
        "height_cm": 168,
        "weight_kg": 72
    },
    {
        "username": "patient5",
        "first_name": "Paolo",
        "last_name": "Costa",
        "birth_date": "1991-01-25",  # 35 years old
        "condition": "diabete tipo 1",
        "medications": '["Insulina asparte 3-4 unità prima dei pasti", "Insulina glargine 12 unità sera", "Carnitina 500mg 2x giorno"]',
        "allergies": '["Pollo", "Acari"]',
        "family_history": '{"father": "Nessuna", "mother": "Tireoidite di Hashimoto", "siblings": "Diabete tipo 1"}',
        "blood_type": "A-",
        "height_cm": 178,
        "weight_kg": 70
    }
]

# Comprehensive lab test definitions with Italian terms
lab_tests_comprehensive = [
    # Diabetes-related
    ("HbA1c", "%", "4.0-6.0", "Emoglobina glicata"),
    ("Glicemia a digiuno", "mg/dL", "70-100", "Glicemia basale"),
    ("Glicemia postprandiale", "mg/dL", "<140", "Glicemia dopo pasto"),
    ("Insulina", "µU/mL", "2-20", "Insulina sierica"),
    ("Peptide C", "ng/mL", "0.5-2.0", "Produzione insulina"),

    # Kidney function
    ("Creatinina", "mg/dL", "0.7-1.3", "Funzionalità renale"),
    ("BUN azoto", "mg/dL", "7-20", "Azoto ureico"),
    ("eGFR", "mL/min", ">60", "Filtrazione glomerulare"),
    ("Microalbuminuria", "mg/g", "<30", "Albumina urinaria"),

    # Liver function
    ("ALT", "U/L", "7-56", "Transaminasi ALT"),
    ("AST", "U/L", "10-40", "Transaminasi AST"),
    ("Gamma-GT", "U/L", "9-48", "Gamma-glutamiltransferasi"),
    ("Bilirubina totale", "mg/dL", "0.3-1.2", "Bilirubina"),

    # Lipids
    ("Colesterolo totale", "mg/dL", "<200", "Colesterolo"),
    ("Colesterolo LDL", "mg/dL", "<100", "Colesterolo cattivo"),
    ("Colesterolo HDL", "mg/dL", ">40", "Colesterolo buono"),
    ("Trigliceridi", "mg/dL", "<150", "Trigliceridi"),

    # Cardiovascular
    ("Omocisteina", "µmol/L", "5-15", "Rischio cardiovascolare"),
    ("Troponina", "ng/L", "<14", "Danno cardiaco"),
    ("BNP", "pg/mL", "<100", "Insufficienza cardiaca"),

    # Thyroid
    ("TSH", "mIU/L", "0.4-4.0", "Ormone stimolante tireotide"),
    ("T3 libero", "pg/mL", "2.0-4.4", "Tiroxina libera"),
    ("T4 libero", "ng/dL", "0.8-1.8", "Triiodotironina libera"),

    # Electrolytes
    ("Sodio", "mmol/L", "136-145", "Sodio sierico"),
    ("Potassio", "mmol/L", "3.5-5.1", "Potassio sierico"),
    ("Cloro", "mmol/L", "98-107", "Clouro"),
    ("Magnesio", "mg/dL", "1.7-2.2", "Magnesio"),

    # Blood cells
    ("Emoglobina", "g/dL", "12-16", "Emoglobina"),
    ("Ematocrito", "%", "37-47", "Ematocrito"),
    ("Globuli bianchi", "10^3/µL", "4.5-11.0", "Leucociti"),
    ("Piastrine", "10^3/µL", "150-400", "Piastrine"),

    # Inflammation
    ("PCR", "mg/L", "<3.0", "Proteina C reattiva"),
    ("VES", "mm/h", "<20", "Velocità eritrosedimentazione"),

    # Vitamins
    ("Vitamina D", "ng/mL", "30-100", "25-OH vitamina D"),
    ("Vitamina B12", "pg/mL", "200-900", "Cobalamina"),
    ("Acido folico", "ng/mL", "3-20", "Folati"),

    # Other metabolic
    ("Acido urico", "mg/dL", "3.4-7.0", "Uricemia"),
    ("Ferritina", "ng/mL", "30-300", "Ferritina sierica"),
    ("Ferro sierico", "µg/dL", "50-170", "Ferro"),
]

lab_tests_diabetes = [
    ("HbA1c", "%", "4.0-6.0", "Emoglobina glicata"),
    ("Glicemia a digiuno", "mg/dL", "70-100", "Glicemia basale"),
    ("Glicemia postprandiale", "mg/dL", "<140", "Glicemia dopo pasto"),
    ("Insulina", "µU/mL", "2-20", "Insulina sierica"),
    ("Peptide C", "ng/mL", "0.5-2.0", "Produzione insulina"),
    ("Creatinina", "mg/dL", "0.7-1.3", "Funzionalità renale"),
    ("BUN azoto", "mg/dL", "7-20", "Azoto ureico"),
    ("eGFR", "mL/min", ">60", "Filtrazione glomerulare"),
    ("Microalbuminuria", "mg/g", "<30", "Albumina urinaria"),
    ("Colesterolo totale", "mg/dL", "<200", "Colesterolo"),
    ("Colesterolo LDL", "mg/dL", "<100", "Colesterolo cattivo"),
    ("Colesterolo HDL", "mg/dL", ">40", "Colesterolo buono"),
    ("Trigliceridi", "mg/dL", "<150", "Trigliceridi"),
    ("PCR", "mg/L", "<3.0", "Proteina C reattiva"),
    ("TSH", "mIU/L", "0.4-4.0", "Ormone stimolante tireotide"),
]

lab_tests_hypertension = [
    ("Glicemia a digiuno", "mg/dL", "70-100", "Glicemia basale"),
    ("Creatinina", "mg/dL", "0.7-1.3", "Funzionalità renale"),
    ("BUN azoto", "mg/dL", "7-20", "Azoto ureico"),
    ("eGFR", "mL/min", ">60", "Filtrazione glomerulare"),
    ("Colesterolo totale", "mg/dL", "<200", "Colesterolo"),
    ("Colesterolo LDL", "mg/dL", "<100", "Colesterolo cattivo"),
    ("Colesterolo HDL", "mg/dL", ">40", "Colesterolo buono"),
    ("Trigliceridi", "mg/dL", "<150", "Trigliceridi"),
    ("Sodio", "mmol/L", "136-145", "Sodio sierico"),
    ("Potassio", "mmol/L", "3.5-5.1", "Potassio sierico"),
    ("Magnesio", "mg/dL", "1.7-2.2", "Magnesio"),
    ("Omocisteina", "µmol/L", "5-15", "Rischio cardiovascolare"),
    ("Troponina", "ng/L", "<14", "Danno cardiaco"),
    ("BNP", "pg/mL", "<100", "Insufficienza cardiaca"),
    ("TSH", "mIU/L", "0.4-4.0", "Ormone stimolante tireotide"),
]

visit_types = ["controllo", "urgenza", "followup"]

visit_notes_diabetes = [
    "Paziente in buono controllo glicemico. HbA1c 6.8%, nella norma. Continuare terapia attuale. Monitoraggio domiciliare glicemie appropriato.",
    "HbA1c leggermente elevato (7.2%). Aumentare metformina a 850mg 2x giorno. Educazione alimentare rafforzata. Piano di monitoraggio intensivo.",
    "Glicemia a digiuno nella norma (95 mg/dL). Buona aderenza alla terapia. Controllare HbA1c tra 3 mesi. Valutare riduzione peso.",
    "Rilevata lieve microalbuminuria (45 mg/g). Valutare nefrologo per possibile nefropatia diabetica. Aggiunto ACE-inibitore per protezione renale.",
    "Paziente riferisce nausea vertigini. Considerare cambiamento farmaco. Glicemie stabili. Controllare transaminasi epatica.",
    "Visita di controllo: HbA1c migliorato a 6.5%. Paziente molto motivato. Continuare terapia attuale. Piano educazionale esercizio fisico.",
    "Episodio ipoglicemia notturna. Ridurre insulina glargine a 8 unità. Educazione su riconoscimento sintomi e gestione immediata.",
    "Rilevata retinopatia diabetica precoce. Referto oculologico. Controllare glicemia postprandiale più frequentemente. Valutare neuropatia.",
    "Controllo: paziente ha perso 3 kg. Dieta migliorata. Glicemie migliori. Continuare piano alimentare attuale.",
    "Visita specialista: terapia ottimizzata. Aggiunto DPP-4 inibitore. Piano di riduzione graduale insulina.",
    "Follow-up: paziente riferisce buon controllo con glicemie capillari nella norma. HbA1c atteso 6.6%. Prossima visita tra 2 mesi.",
    "Follow-up post-alimentazione: paziente ha adottato dieta mediterranea. Trigliceridi ridotti. Continuare monitoraggio lipidi.",
    "Visita urgenza: glicemia 320 mg/dL. Cetonemia negativa. Aumentato temporaneamente insulina rapida. Educazione su gestione malattia intercorrente.",
    "Controllo trimestrale: HbA1c stabile 6.7%. eGFR normale. Nessuna complicanza acuta. Continuare terapia attuale.",
    "Controllo piede: nessuna lesione. Sensibilità conservata. Educazione su prevenzione ulcerazioni. Calzature appropriate."
]

visit_notes_hypertension = [
    "Pressione arteriosa ben controllata (125/80 mmHg). Continuare terapia attuale. ECG normale. Monitoraggio domiciliare appropriato.",
    "Pressione elevata (155/95 mmHg). Aumentare dosaggio ACE-inibitore. Aggiungere amlodipina se non miglioramento. Controllare funzionalità renale.",
    "Valori pressori nella norma (120/75 mmHg). Monitorare potassio (4.2 mmol/L). Paziente asintomatico. Continuare follow-up trimestrale.",
    "Paziente riferisce capogiri posturali. Pressione 110/70 mmHg. Ridurre dose diuretico. Controllare pressione in ortostatismo.",
    "ECG normale: ritmo sinusale, assenza alterazioni riposo. Continuare follow-up semestrale. Valutare Holter pressorio 24h.",
    "Controllo cardiologico: frazione di eiezione conservata. Nessuna ipertrofia ventricolare. Continuare terapia antiipertensiva.",
    "Controllo nutrizionale: ridotto apporto sodico. Paziente ha perso 2 kg. Pressione migliorata. Continuare dieta iposodica.",
    "Follow-up: monitoraggio domiciliare mostra valori nella norma. Aderenza terapia buona. Nessun effetto collaterale riferito.",
    "Consulenza nefrologica: filtrazione glomerulare normale. Microalbuminuria assente. Protezione renale ottimale con ACE-inibitore.",
    "Follow-up dosaggio farmaci: ridotto amlodipina per edema caviglie. Pressione stabile. Monitorare segni ritenzione idrica.",
    "Visita urgenza: cefalea severa, pressione 180/110 mmHg. Aggiunto nifedipina sublinguale. Referto Pronto Soccorso esclusa emergenza.",
    "Controllo post-aumento terapia: pressione 118/72 mmHg. Paziente riferisce miglioramento benessere. Continuare nuovo schema.",
    "Valutazione rischio cardiovascolare: score EUROPEO basso. Profilassi primaria ottimale. Continuare statina e antiaggregante.",
    "Esami laboratorio: elettroliti nel range, funzionalità renale conservata. Nessun effetto collaterale da terapia. Buona tollerabilità.",
    "Visita chiusura anno: obiettivi terapeutici raggiunti. Pressione target, no complicanze. Piano mantenimento e monitoraggio."
]

diagnoses_diabetes = [
    "Diabete mellito tipo 2 - malattia metabolica",
    "Diabete mellito tipo 2 - scarso controllo glicemico",
    "Diabete mellito tipo 2 - retinopatia diabetica",
    "Diabete mellito tipo 2 - nefropatia diabetica precoce",
    "Diabete mellito tipo 2 - buona compensazione",
    "Diabete mellito tipo 2 - sindrome metabolica",
    "Diabete mellito tipo 2 - neuropatia periferica sospetta",
    "Diabete mellito tipo 2 - controllo ottimale"
]

diagnoses_hypertension = [
    "Ipertensione arteriosa essenziale - stadio 1",
    "Ipertensione arteriosa essenziale - stadio 2",
    "Ipertensione arteriosa - buon controllo",
    "Ipertensione arteriosa - rischio cardiovascolare intermedio",
    "Ipertensione arteriosa - terapia combinata",
    "Ipertensione arteriosa - cuore anziano normoteso",
    "Ipertensione arteriosa - ipertrofia ventricolare sinistra",
    "Ipertensione arteriosa - nefropatia ipertensiva"
]

def generate_realistic_value(test_name, base_value, variation, patient_data):
    """Generate realistic lab values with some variation based on patient profile."""

    # Age and condition adjustments
    age_factor = 1.0
    if "45" in patient_data.get("birth_date", ""):
        age_factor = 1.05
    elif "52" in patient_data.get("birth_date", ""):
        age_factor = 1.1

    condition = patient_data.get("condition", "").lower()

    if test_name == "HbA1c":
        if "diabete" in condition:
            base_val = 6.5 + random.uniform(-0.8, 1.2)
        else:
            base_val = 5.4 + random.uniform(-0.3, 0.4)
        return f"{base_val + variation:.1f}"

    elif test_name == "Glicemia a digiuno":
        if "diabete" in condition:
            base_val = 110 + random.uniform(-15, 35)
        else:
            base_val = 85 + random.uniform(-10, 15)
        return f"{int(base_val + variation * 10)}"

    elif test_name == "Glicemia postprandiale":
        if "diabete" in condition:
            base_val = 160 + random.uniform(-25, 45)
        else:
            base_val = 115 + random.uniform(-15, 25)
        return f"{int(base_val + variation * 15)}"

    elif test_name == "Insulina":
        if "diabete tipo 2" in condition:
            base_val = 15 + random.uniform(-5, 10)
        else:
            base_val = 8 + random.uniform(-3, 5)
        return f"{base_val + variation:.1f}"

    elif test_name == "Peptide C":
        if "diabete tipo 1" in condition:
            base_val = 0.3 + random.uniform(-0.1, 0.2)
        else:
            base_val = 1.2 + random.uniform(-0.3, 0.5)
        return f"{base_val + variation:.2f}"

    elif test_name == "Creatinina":
        base_val = 0.9 * age_factor + random.uniform(-0.1, 0.2)
        return f"{base_val + variation * 0.05:.2f}"

    elif test_name == "BUN azoto":
        base_val = 14 + random.uniform(-4, 6)
        return f"{int(base_val + variation)}"

    elif test_name == "eGFR":
        base_val = 85 * (2.0 - age_factor * 0.1) + random.uniform(-10, 8)
        return f"{int(base_val + variation * 2)}"

    elif test_name == "Microalbuminuria":
        if "diabete" in condition:
            base_val = 25 + random.uniform(-15, 45)
        else:
            base_val = 10 + random.uniform(-5, 15)
        return f"{int(base_val + variation * 5)}"

    elif test_name == "Colesterolo totale":
        base_val = 195 + random.uniform(-25, 35)
        return f"{int(base_val + variation * 10)}"

    elif test_name == "Colesterolo LDL":
        base_val = 115 + random.uniform(-20, 35)
        return f"{int(base_val + variation * 12)}"

    elif test_name == "Colesterolo HDL":
        base_val = 45 + random.uniform(-8, 12)
        return f"{int(base_val + variation * 3)}"

    elif test_name == "Trigliceridi":
        if "diabete" in condition:
            base_val = 145 + random.uniform(-35, 55)
        else:
            base_val = 110 + random.uniform(-25, 35)
        return f"{int(base_val + variation * 18)}"

    elif test_name == "PCR":
        base_val = 2.5 + random.uniform(-1.5, 3.0)
        return f"{base_val + variation * 0.5:.1f}"

    elif test_name == "TSH":
        base_val = 2.5 + random.uniform(-1.5, 2.0)
        return f"{base_val + variation * 0.3:.2f}"

    elif test_name == "Sodio":
        base_val = 140 + random.uniform(-3, 4)
        return f"{base_val + variation * 0.5:.1f}"

    elif test_name == "Potassio":
        base_val = 4.2 + random.uniform(-0.5, 0.6)
        return f"{base_val + variation * 0.1:.2f}"

    elif test_name == "Magnesio":
        base_val = 2.0 + random.uniform(-0.2, 0.2)
        return f"{base_val + variation * 0.05:.2f}"

    elif test_name == "Omocisteina":
        base_val = 10 + random.uniform(-4, 8)
        return f"{base_val + variation:.1f}"

    elif test_name == "Troponina":
        base_val = 5 + random.uniform(-4, 6)
        return f"{int(base_val + variation)}"

    elif test_name == "BNP":
        base_val = 45 + random.uniform(-30, 50)
        return f"{int(base_val + variation * 10)}"

    elif test_name == "ALT":
        base_val = 25 + random.uniform(-10, 20)
        return f"{int(base_val + variation * 5)}"

    elif test_name == "AST":
        base_val = 22 + random.uniform(-8, 15)
        return f"{int(base_val + variation * 4)}"

    elif test_name == "Gamma-GT":
        base_val = 28 + random.uniform(-12, 25)
        return f"{int(base_val + variation * 6)}"

    elif test_name == "Bilirubina totale":
        base_val = 0.8 + random.uniform(-0.3, 0.5)
        return f"{base_val + variation * 0.1:.2f}"

    elif test_name == "Emoglobina":
        if "Laura" in patient_data.get("first_name", ""):
            base_val = 13.5 + random.uniform(-1.5, 1.2)  # Female reference
        else:
            base_val = 14.5 + random.uniform(-1.5, 1.5)
        return f"{base_val + variation * 0.2:.1f}"

    elif test_name == "Ematocrito":
        if "Laura" in patient_data.get("first_name", "") or "Anna" in patient_data.get("first_name", ""):
            base_val = 40 + random.uniform(-3, 3)
        else:
            base_val = 43 + random.uniform(-4, 4)
        return f"{int(base_val + variation)}"

    elif test_name == "Globuli bianchi":
        base_val = 7.5 + random.uniform(-2.5, 3.0)
        return f"{base_val + variation * 0.5:.1f}"

    elif test_name == "Piastrine":
        base_val = 260 + random.uniform(-80, 120)
        return f"{int(base_val + variation * 20)}"

    elif test_name == "VES":
        base_val = 12 + random.uniform(-8, 15)
        return f"{int(base_val + variation * 3)}"

    elif test_name == "Vitamina D":
        base_val = 35 + random.uniform(-15, 40)
        return f"{int(base_val + variation * 5)}"

    elif test_name == "Vitamina B12":
        base_val = 450 + random.uniform(-150, 300)
        return f"{int(base_val + variation * 50)}"

    elif test_name == "Acido folico":
        base_val = 8 + random.uniform(-4, 8)
        return f"{base_val + variation:.1f}"

    elif test_name == "Acido urico":
        base_val = 5.2 + random.uniform(-1.5, 2.5)
        return f"{base_val + variation * 0.3:.1f}"

    elif test_name == "Ferritina":
        base_val = 120 + random.uniform(-60, 180)
        return f"{int(base_val + variation * 30)}"

    elif test_name == "Ferro sierico":
        base_val = 90 + random.uniform(-30, 60)
        return f"{int(base_val + variation * 15)}"

    return f"{base_value}"

# Create patients with comprehensive medical histories
base_date = datetime(2026, 7, 27)  # Today
total_data_points = 0

for patient_info in patients_data:
    # Create user
    user = User(
        username=patient_info["username"],
        password_hash=password_hash,
        role="patient"
    )
    session.add(user)
    session.commit()

    # Create patient profile with hardcoded doctor assignment
    patient = Patient(
        user_id=user.id,
        first_name=patient_info["first_name"],
        last_name=patient_info["last_name"],
        birth_date=patient_info["birth_date"],
        condition=patient_info["condition"],
        medications=patient_info["medications"],
        doctor_id=doctor_user.id
    )
    session.add(patient)
    session.commit()

    # Determine lab tests based on condition
    if "diabete" in patient_info["condition"].lower():
        lab_tests = lab_tests_diabetes
        visit_notes = visit_notes_diabetes
        diagnoses = diagnoses_diabetes
    else:  # hypertension
        lab_tests = lab_tests_hypertension
        visit_notes = visit_notes_hypertension
        diagnoses = diagnoses_hypertension

    patient_data_points = 0

    # Generate 6 months of lab results with bi-weekly frequency (13 data points per test)
    for week in range(26):  # 26 weeks = 6 months
        lab_date = base_date - timedelta(weeks=week, days=random.randint(0, 3))
        date_str = lab_date.strftime("%Y-%m-%d")

        # Only do lab tests every 2 weeks
        if week % 2 != 0:
            continue

        for i, (test_name, unit, ref_range, description) in enumerate(lab_tests):
            # Add some variation for realism
            week_variation = (week % 4) - 2 + random.uniform(-0.5, 0.5)

            value = generate_realistic_value(test_name, 0, week_variation, patient_info)

            # Add occasional notes
            notes = None
            if random.random() < 0.1:  # 10% chance of having notes
                if test_name == "HbA1c" and float(value) > 7.0:
                    notes = "Valore elevato - raccomandato intensificare terapia"
                elif test_name == "Glicemia a digiuno" and int(value) > 130:
                    notes = "Iperglicemia a digiuno - valutare aggiustamento terapia"
                elif test_name == "Microalbuminuria" and int(value) > 30:
                    notes = "Microalbuminuria presente - monitoraggio nefropatia"

            lab_result = LabResult(
                patient_id=patient.id,
                test_name=test_name,
                test_value=value,
                unit=unit,
                reference_range=ref_range,
                date=date_str,
                notes=notes
            )
            session.add(lab_result)
            patient_data_points += 1

    # Generate comprehensive visits (weekly to bi-weekly)
    for week in range(24):  # 24 weeks
        # Visit every 2 weeks, occasionally weekly
        if week % 2 == 0 or (week % 3 == 0 and random.random() > 0.5):
            visit_date = base_date - timedelta(weeks=week, days=random.randint(0, 2))
            date_str = visit_date.strftime("%Y-%m-%d")

            visit_type = random.choice(visit_types)

            # Select appropriate notes and diagnosis
            note_index = min(week, len(visit_notes) - 1)
            diagnosis = diagnoses[week % len(diagnoses)]

            # Add some variation to notes
            doctor_notes = visit_notes[note_index]
            if random.random() < 0.15:  # 15% chance of additional notes
                additional_notes = [
                    ". Paziente riferisce buon stato generale.",
                    ". Richiesta eco-color doppler arti inferiori.",
                    ". Consigliato aumento attività fisica.",
                    ". Monitoraggio pressorio domiciliare continuato.",
                    ". Paziente soddisfatto della terapia attuale.",
                    ". Valutato compliance - ottima aderenza.",
                    ". Educazione su alimentazione corretta."
                ]
                doctor_notes += random.choice(additional_notes)

            visit = Visit(
                patient_id=patient.id,
                visit_date=date_str,
                visit_type=visit_type,
                doctor_notes=doctor_notes,
                diagnosis=diagnosis
            )
            session.add(visit)
            patient_data_points += 1

    total_data_points += patient_data_points
    print(f"  Generated {patient_data_points} data points for {patient_info['first_name']} {patient_info['last_name']}")

session.commit()
print(f"\n✓ Created 1 doctor (Dr. {doctor.first_name} {doctor.last_name})")
print(f"✓ Created 5 patients with chronic conditions")
print(f"✓ Generated total of {total_data_points} medical data points ({total_data_points//5} average per patient)")
print(f"✓ All patients assigned to Dr. {doctor.last_name}")
print("\nDatabase seeded successfully!")
print("\nCredentials:")
print("  Doctor: doctor / FEEMsalute2026!")
print("  Patients: patient1-5 / FEEMsalute2026!")
print("\nPatient profiles:")
print("  Patient 1: Mario Rossi - Diabete tipo 2, 45 anni")
print("  Patient 2: Laura Bianchi - Ipertensione, 52 anni")
print("  Patient 3: Giuseppe Verdi - Diabete tipo 2, 38 anni")
print("  Patient 4: Anna Ferrari - Ipertensione, 48 anni")
print("  Patient 5: Paolo Costa - Diabete tipo 1, 35 anni")
