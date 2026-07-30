"""
Clinically-coherent seed data.

For every patient we generate 10 monthly encounters. Each encounter stores a
focused panel of lab values that are coherent with the patient's pathology.
The values follow realistic, smooth trajectories (therapy response / slow
deterioration) with month-to-month fluctuation so the trend charts show
meaningful, believable fluctuations instead of random noise.

Metrics generated per encounter depend on the condition:
  * diabete tipo 1 / tipo 2  -> HbA1c, glicemia, lipidi, funzione renale
  * ipertensione             -> pressione arteriosa, funzione renale, lipidi
"""

import math
import random
import bcrypt
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, User, Doctor, Patient, LabResult, Visit, HealthGoal, GoalCheckIn

# ----------------------------------------------------------------------------
# Reproducibility
# ----------------------------------------------------------------------------
random.seed(42)

# ----------------------------------------------------------------------------
# Database setup
# ----------------------------------------------------------------------------
engine = create_engine('sqlite:///database.db', echo=False)
Session = sessionmaker(bind=engine)
session = Session()


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


# ----------------------------------------------------------------------------
# Metric catalogue
#   key  -> (label, unit, reference_range, normal_min, normal_max, decimals)
# ----------------------------------------------------------------------------
METRICS = {
    'HbA1c':                   ('HbA1c',                    '%',     '4.0-6.0',  4.0,   6.0,  1),
    'Glicemia a digiuno':      ('Glicemia a digiuno',       'mg/dL', '70-100',   70,    100, 0),
    'Glicemia postprandiale':  ('Glicemia postprandiale',   'mg/dL', '<140',     70,    140, 0),
    'Colesterolo LDL':         ('Colesterolo LDL',          'mg/dL', '<100',     0,     100, 0),
    'Colesterolo HDL':         ('Colesterolo HDL',          'mg/dL', '>40',      40,    80,  0),
    'Colesterolo totale':      ('Colesterolo totale',       'mg/dL', '<200',     0,     200, 0),
    'Trigliceridi':            ('Trigliceridi',             'mg/dL', '<150',     0,     150, 0),
    'Creatinina':              ('Creatinina',               'mg/dL', '0.7-1.3',  0.7,   1.3, 2),
    'eGFR':                    ('eGFR',                     'mL/min','>60',      60,    120, 0),
    'Microalbuminuria':        ('Microalbuminuria',         'mg/g',  '<30',      0,     30,  0),
    'Pressione sistolica':     ('Pressione sistolica',      'mmHg',  '90-120',   90,    120, 0),
    'Pressione diastolica':    ('Pressione diastolica',     'mmHg',  '60-80',    60,    80,  0),
    'Potassio':                ('Potassio',                 'mmol/L','3.5-5.1',  3.5,   5.1, 1),
    'Sodio':                   ('Sodio',                    'mmol/L','136-145', 136,   145, 0),
}


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
        return str(int(round(value)))
    return f"{value:.{decimals}f}"


# ----------------------------------------------------------------------------
# Per-pathology metric trend specifications
#   Each value: (metric_key, start, end, amplitude, phase)
# ----------------------------------------------------------------------------
TRENDS = {
    # --- Diabetes type 2 ----------------------------------------------------
    'diabete tipo 2-buono': [   # Mario Rossi: good control, improving on therapy
        ('HbA1c',                  8.0, 6.7,  0.35, 0),
        ('Glicemia a digiuno',     138, 108,  11,   1),
        ('Glicemia postprandiale', 185, 150,  14,   2),
        ('Colesterolo LDL',        145, 118,  8,    3),
        ('Colesterolo HDL',        39,  44,   3,    4),
        ('Colesterolo totale',     215, 190,  8,    5),
        ('Trigliceridi',           190, 160,  17,   6),
        ('Creatinina',             0.95, 0.92, 0.05, 7),
        ('eGFR',                   82,  85,   4,    8),
        ('Microalbuminuria',       28,  18,   6,    9),
    ],
    'diabete tipo 2-cattivo': [  # Giuseppe Verdi: stubborn, early nephropathy
        ('HbA1c',                  7.4, 7.7,  0.40, 0),
        ('Glicemia a digiuno',     135, 144,  13,   1),
        ('Glicemia postprandiale', 175, 190,  15,   2),
        ('Colesterolo LDL',        150, 142,  9,    3),
        ('Colesterolo HDL',        37,  40,   3,    4),
        ('Colesterolo totale',     225, 212,  10,   5),
        ('Trigliceridi',           210, 198,  19,   6),
        ('Creatinina',             1.00, 1.16, 0.05, 7),
        ('eGFR',                   78,  67,   5,    8),
        ('Microalbuminuria',       45,  78,   12,   9),
    ],
    # --- Diabetes type 1 ----------------------------------------------------
    'diabete tipo 1': [          # Paolo Costa: labile but slowly improving
        ('HbA1c',                  7.9, 7.3,  0.50, 0),
        ('Glicemia a digiuno',     155, 125,  18,   1),
        ('Glicemia postprandiale', 200, 170,  22,   2),
        ('Colesterolo LDL',        110, 105,  7,    3),
        ('Colesterolo HDL',        48,  52,   4,    4),
        ('Colesterolo totale',     180, 175,  8,    5),
        ('Trigliceridi',           120, 110,  14,   6),
        ('Creatinina',             0.85, 0.88, 0.04, 7),
        ('eGFR',                   95,  92,   4,    8),
        ('Microalbuminuria',       12,  10,   4,    9),
    ],
    # --- Hypertension -------------------------------------------------------
    'ipertensione-buona': [      # Laura Bianchi: well controlled, improving
        ('Pressione sistolica',    148, 128,  6,    0),
        ('Pressione diastolica',   92,  80,   4,    1),
        ('Creatinina',             0.88, 0.85, 0.05, 2),
        ('eGFR',                   85,  88,   4,    3),
        ('Colesterolo LDL',        138, 120,  8,    4),
        ('Colesterolo HDL',        52,  55,   3,    5),
        ('Colesterolo totale',     210, 195,  8,    6),
        ('Trigliceridi',           130, 120,  12,   7),
        ('Potassio',               4.2, 4.3,  0.2,  8),
        ('Sodio',                  140, 140,  1.5,  9),
    ],
    'ipertensione-cattiva': [    # Anna Ferrari: stubborn, borderline control
        ('Pressione sistolica',    152, 143,  7,    0),
        ('Pressione diastolica',   95,  89,   4,    1),
        ('Creatinina',             0.95, 1.00, 0.05, 2),
        ('eGFR',                   80,  78,   4,    3),
        ('Colesterolo LDL',        148, 141,  9,    4),
        ('Colesterolo HDL',        45,  48,   3,    5),
        ('Colesterolo totale',     225, 216,  9,    6),
        ('Trigliceridi',           155, 146,  14,   7),
        ('Potassio',               4.1, 4.0,  0.2,  8),
        ('Sodio',                  141, 140,  1.5,  9),
    ],
}


# ----------------------------------------------------------------------------
# Users
# ----------------------------------------------------------------------------
USERS = [
    {
        'username': 'doctor', 'password': 'FEEMsalute2026!', 'role': 'doctor',
        'first_name': 'Marco', 'last_name': 'Bianchi', 'specialization': 'Medicina interna',
    },
    {
        'username': 'patient1', 'password': 'FEEMsalute2026!', 'role': 'patient',
        'first_name': 'Mario', 'last_name': 'Rossi', 'birth_date': '1981-03-15',
        'condition': 'diabete tipo 2', 'trend_key': 'diabete tipo 2-buono',
        'medications': '["Metformina 850mg 2x/die", "Lisinopril 10mg 1x/die", "Atorvastatina 20mg sera"]',
        'anamnesis': '{"physical_activity":"1-2 volte a settimana","nutrition":"Spesso pasti veloci, troppi carboidrati","smoking":"ex fumatore (smesso 3 anni fa)","alcohol":"1-2 bicchieri vino weekend","sleep":"6 ore, spesso interrotto","stress":"medio, turni variabili","protective":["ex fumatore","controlli regolari","rete familiare solida"]}',
        'adherence': 0.82,
    },
    {
        'username': 'patient2', 'password': 'FEEMsalute2026!', 'role': 'patient',
        'first_name': 'Laura', 'last_name': 'Bianchi', 'birth_date': '1974-07-22',
        'condition': 'ipertensione', 'trend_key': 'ipertensione-buona',
        'medications': '["Lisinopril 20mg 1x/die", "Amlodipina 5mg 1x/die", "Metoprololo 50mg 2x/die"]',
        'anamnesis': '{"physical_activity":"3 volte a settimana (camminata)","nutrition":"Equilibrata, troppo sale","smoking":"mai fumato","alcohol":"occasionale","sleep":"7 ore, buon qualità","stress":"basso","protective":["non fuma","attività fisica regolare","buon sonno","alimentazione attenta"]}',
        'adherence': 0.78,
    },
    {
        'username': 'patient3', 'password': 'FEEMsalute2026!', 'role': 'patient',
        'first_name': 'Giuseppe', 'last_name': 'Verdi', 'birth_date': '1988-11-30',
        'condition': 'diabete tipo 2', 'trend_key': 'diabete tipo 2-cattivo',
        'medications': '["Metformina 1000mg 2x/die", "Insulina glargine 10U sera", "Sitagliptina 100mg 1x/die"]',
        'anamnesis': '{"physical_activity":"sedentario","nutrition":"molte merendine e bevande zuccherate","smoking":"10 sigarette/die","alcohol":"2-3 birre giorni feriali","sleep":"5 ore, qualità scarso","stress":"alto, carico di lavoro","protective":["giovane età"]}',
        'adherence': 0.42,
    },
    {
        'username': 'patient4', 'password': 'FEEMsalute2026!', 'role': 'patient',
        'first_name': 'Anna', 'last_name': 'Ferrari', 'birth_date': '1978-05-10',
        'condition': 'ipertensione', 'trend_key': 'ipertensione-cattiva',
        'medications': '["Lisinopril 20mg 1x/die", "Idroclorotiazide 25mg 1x/die", "Atorvastatina 20mg sera"]',
        'anamnesis': '{"physical_activity":"2 volte a settimana","nutrition":"cibi preconfezionati, sale elevato","smoking":"ex fumatrice","alcohol":"vino ai pasti quotidianamente","sleep":"6.5 ore","stress":"medio-alto","protective":["controlli pressori domiciliari","ex fumatrice"]}',
        'adherence': 0.55,
    },
    {
        'username': 'patient5', 'password': 'FEEMsalute2026!', 'role': 'patient',
        'first_name': 'Paolo', 'last_name': 'Costa', 'birth_date': '1991-01-25',
        'condition': 'diabete tipo 1', 'trend_key': 'diabete tipo 1',
        'medications': '["Insulina asparte 3-4U pre-pasti", "Insulina glargine 12U sera"]',
        'anamnesis': '{"physical_activity":"4 volte a settimana (nuoto)","nutrition":"conta carboidrati, attenta","smoking":"mai fumato","alcohol":"raro","sleep":"7.5 ore","stress":"basso","protective":["non fuma","attività fisica regolare","automonitoraggio glicemico","alimentazione attenta","buon sonno"]}',
        'adherence': 0.85,
    },
]


# ----------------------------------------------------------------------------
# Visit narrative per pathology
# ----------------------------------------------------------------------------
VISIT_NOTES = {
    'diabete': [
        ('controllo', 'Controllo glicemico trimestrale. Terapia invariata, monitoraggio domiciliare corretto.', 'Diabete mellito - follow-up'),
        ('followup',  'Follow-up post-aggiustamento terapia. Glicemie capillari stabili.', 'Diabete mellito - follow-up terapia'),
        ('controllo', 'Valutazione complicanze: fondo oculare nella norma, piede sano.', 'Diabete mellito - screening complicanze'),
        ('urgenza',   'Paziente riferisce iperglicemia sintomatica. Valutato, stabilizzato in ambulatorio.', 'Diabete mellito - episodio iperglicemico'),
        ('controllo', 'Educazione alimentare rafforzata. Paziente collaborante.', 'Diabete mellito - educazione terapeutica'),
        ('followup',  'Controllo HbA1c: trend in miglioramento. Continuare schema attuale.', 'Diabete mellito - compenso migliorato'),
    ],
    'ipertensione': [
        ('controllo', 'Monitoraggio pressorio ambulatoriale. Terapia confermata.', 'Ipertensione arteriosa - controllo'),
        ('followup',  'Holter pressorio: valori medi nei limiti. Continuare monitoraggio domiciliare.', 'Ipertensione arteriosa - follow-up'),
        ('controllo', 'ECG: ritmo sinusale. Auscultazione cardiaca nei limiti.', 'Ipertensione arteriosa - valutazione cardiaca'),
        ('urgenza',   'Crisi ipertensiva transitoria, gestita in ambulatorio. Terapia rinforzata.', 'Ipertensione arteriosa - crisi ipertensiva'),
        ('controllo', 'Consulenza nefrologica: funzione renale stabile.', 'Ipertensione arteriosa - valutazione renale'),
        ('followup',  'Ridotto apporto sodico, paziente ha perso peso. Pressione migliorata.', 'Ipertensione arteriosa - miglioramento'),
    ],
}


# ----------------------------------------------------------------------------
# Build data
# ----------------------------------------------------------------------------
# Wipe
Base.metadata.create_all(engine)
session.query(GoalCheckIn).delete()
session.query(HealthGoal).delete()
session.query(LabResult).delete()
session.query(Visit).delete()
session.query(Patient).delete()
session.query(Doctor).delete()
session.query(User).delete()
session.commit()

Base.metadata.create_all(engine)

N_POINTS = 10
today = datetime.now().date()
# 10 monthly dates, oldest = ~9 months ago, newest = today
dates = [(today - timedelta(days=30 * (N_POINTS - 1 - i))).isoformat() for i in range(N_POINTS)]

patients = []

for u in USERS:
    user = User(username=u['username'], password_hash=hash_password(u['password']), role=u['role'])
    session.add(user)
    session.commit()

    if u['role'] == 'doctor':
        session.add(Doctor(user_id=user.id, first_name=u['first_name'],
                           last_name=u['last_name'], specialization=u['specialization']))
        session.commit()
        continue

    patient = Patient(
        user_id=user.id,
        first_name=u['first_name'], last_name=u['last_name'],
        birth_date=u['birth_date'], condition=u['condition'],
        medications=u['medications'], doctor_id=1,
        anamnesis=u.get('anamnesis'),
    )
    session.add(patient)
    session.commit()
    patients.append((patient, u))

# Generate coherent labs + visits
for patient, u in patients:
    specs = TRENDS[u['trend_key']]
    # Pre-compute one series per metric (10 points each)
    series_map = {}
    for metric_key, start, end, amp, phase in specs:
        series_map[metric_key] = series(start, end, N_POINTS, amp, phase)

    cond_bucket = 'diabete' if 'diabete' in u['condition'] else 'ipertensione'
    notes_pool = VISIT_NOTES[cond_bucket]

    for i, date_str in enumerate(dates):
        for metric_key, _start, _end, _amp, _phase in specs:
            label, unit, ref, _nmin, _nmax, decimals = METRICS[metric_key]
            value = fmt(series_map[metric_key][i], decimals)
            session.add(LabResult(
                patient_id=patient.id,
                test_name=label,
                test_value=value,
                unit=unit,
                reference_range=ref,
                date=date_str,
                notes=f'Controllo periodico',
            ))

        # One visit per month, with one urgency near month 4 for realism
        if i == 4:
            vtype, vnotes, vdiag = next((n for n in notes_pool if n[0] == 'urgenza'), notes_pool[0])
        else:
            vtype, vnotes, vdiag = notes_pool[i % len(notes_pool)]
        session.add(Visit(
            patient_id=patient.id,
            visit_date=date_str,
            visit_type=vtype,
            doctor_notes=vnotes,
            diagnosis=vdiag,
        ))

# ---- Prevention layer: goals + weekly check-ins ----
# Each patient gets a realistic goal + 6 weeks of adherence history.
GOAL_DEFS = {
    'diabete tipo 2-buono':     ('physical_activity', 'Camminata 30 minuti', 5),
    'diabete tipo 2-cattivo':  ('nutrition', 'Ridurre bevande zuccherate', 7),
    'diabete tipo 1':          ('physical_activity', 'Attività moderata dopo pasti', 4),
    'ipertensione-buona':      ('physical_activity', 'Camminata 30 minuti', 5),
    'ipertensione-cattiva':    ('nutrition', 'Ridurre sale e preconfezionati', 6),
}

for patient, u in patients:
    area, title, freq = GOAL_DEFS[u['trend_key']]
    goal = HealthGoal(patient_id=patient.id, area=area, title=title,
                      frequency_per_week=freq, status='active')
    session.add(goal)
    session.commit()
    # 6 weeks of check-ins, with a believable adherence story
    rng = random.Random(hash(u['username']) & 0xffff)
    adherence_profile = u.get('adherence', 0.7)
    for w in range(6, 0, -1):
        monday = (today - timedelta(days=today.weekday() + 7 * (w - 1)))
        # recent weeks slightly improving for "good" patients, erratic for others
        done = max(0, min(freq, int(round(freq * (adherence_profile + rng.uniform(-0.25, 0.25))))))
        session.add(GoalCheckIn(
            goal_id=goal.id, patient_id=patient.id,
            week_of=monday.isoformat(), completed_days=done,
        ))
session.commit()

# Report
lab_count = session.query(LabResult).count()
visit_count = session.query(Visit).count()
print(f"OK seed data generato")
print(f"   Pazienti: {len(patients)} | Incontri/paziente: {N_POINTS} | Metriche/incontro: {len(METRICS)}")
print(f"   Lab totali: {lab_count} | Visite: {visit_count}")
for patient, u in patients:
    key_metric = 'HbA1c' if 'diabete' in u['condition'] else 'Pressione sistolica'
    vals = [r.test_value for r in session.query(LabResult)
            .filter_by(patient_id=patient.id, test_name=key_metric).order_by(LabResult.date).all()]
    print(f"   - {patient.first_name} {patient.last_name} [{u['condition']}] "
          f"{key_metric}: {' -> '.join(vals)}")
session.close()
