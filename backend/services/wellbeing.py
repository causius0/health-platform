"""Wellbeing instruments — validated questionnaires provided in the client evidence review.

The indicator set follows the client's attached study matrix:
  * clinical parameters      -> observations (BP, glucose, weight/BMI/waist,
                                lipids) + symptoms, handled by the risk engine
  * behavioural parameters   -> BPAAT (physical activity), WSQ (sitting time)
  * work-related parameters  -> work-ability item, sickness-absence episodes,
                                presenteeism item, job-strain items
  * digital-pathway usage    -> computed engagement (goals, questionnaires,
                                chat, monitoring compliance)

Instruments (self-compiled by the worker, viewable by both sides):
  - WEMWBS-7  — mental well-being (Warwick-Edinburgh; used in the office-workers
                mHealth RCT, BMC Public Health 2022)
  - BPAAT     — brief physical activity assessment (Marshall et al. 2005)
  - WSQ       — Workforce Sitting Questionnaire (sitting time at work)
  - work      — occupational block (work ability, sickness absence,
                presenteeism, job strain per JCQ-derived items)
"""
import json
from datetime import date, timedelta

from models import GoalCheckIn, HealthGoal, MonitoringPlanItem, Observation, WellbeingAssessment

LIKERT5 = [
    {"value": i, "label": t}
    for i, t in [
        (1, "mai"), (2, "raramente"), (3, "a volte"), (4, "spesso"), (5, "sempre"),
    ]
]

WEMWBS7 = {
    "instrument": "wemwbs7",
    "label": "Benessere mentale (WEMWBS-7)",
    "description": "7 domande sul benessere mentale e psicologico delle ultime 2 settimane.",
    "reference": "Warwick-Edinburgh Mental Well-being Scale, forma breve (SWEMWBS) — usata nello studio mHealth su lavoratori d'ufficio con diabete tipo 2 (BMC Public Health 2022).",
    "questions": [
        {"id": "q1", "text": "Mi sono sentito/a ottimista riguardo al futuro"},
        {"id": "q2", "text": "Mi sono sentito/a utile"},
        {"id": "q3", "text": "Mi sono sentito/a rilassato/a"},
        {"id": "q4", "text": "Mi sono sentito/a interessato/a alle cose"},
        {"id": "q5", "text": "Ho avuto buona energia"},
        {"id": "q6", "text": "Ho affrontato bene i problemi"},
        {"id": "q7", "text": "Mi sono sentito/a vicino/a alle persone che mi circondano"},
    ],
    "answer_type": "scale1_5",
    "options": LIKERT5,
}

BPAAT = {
    "instrument": "bpaat",
    "label": "Attività fisica (BPAAT)",
    "description": "3 domande rapide sull'attività fisica settimanale.",
    "reference": "Brief Physical Activity Assessment Tool (Marshall et al., Med Sci Sports Exerc 2005); soglia OMS 2020 ≥ 150 min/settimana.",
    "questions": [
        {"id": "q1", "text": "In quanti giorni della settimana fai almeno 30 minuti di attività moderata (camminata veloce, bici, giardinaggio)?", "answer_type": "number_0_7"},
        {"id": "q2", "text": "In quanti giorni della settimana fai almeno 20 minuti di attività intensa (corsa, sport, lavori pesanti)?", "answer_type": "number_0_7"},
    ],
    "answer_type": "number",
}

WSQ = {
    "instrument": "wsq",
    "label": "Sedentarietà (WSQ)",
    "description": "Quante ore resti seduto in una giornata tipo.",
    "reference": "Workforce Sitting Questionnaire (validazione Chau et al., 2012); rischio elevato ≥ 8 h/die (sintesi evidenze sedentarietà).",
    "questions": [
        {"id": "q1", "text": "Ore seduto/a durante il lavoro (giornata tipo)", "answer_type": "number_0_12"},
        {"id": "q2", "text": "Ore seduto/a negli spostamenti", "answer_type": "number_0_12"},
        {"id": "q3", "text": "Ore seduto/a nel tempo libero (pasti, TV, schermi)", "answer_type": "number_0_12"},
    ],
    "answer_type": "number",
}

WORK = {
    "instrument": "work",
    "label": "Salute e lavoro",
    "description": "Capacità lavorativa, assenze per malattia, presentismo e carico lavorativo.",
    "reference": "Work Limitations Questionnaire (presentismo) e Job Content Questionnaire (Karasek, strain) come nello studio mHealth su dipendenti d'ufficio (BMC Public Health 2022); 'assenze frequenti' = ≥ 3 episodi/anno (JMIR 2017).",
    "questions": [
        {"id": "work_ability", "text": "Come valuti la tua capacità di lavoro attuale? (0 = pessima, 10 = ottima)", "answer_type": "scale0_10"},
        {"id": "absence_episodes", "text": "Episodi di assenza per malattia negli ultimi 12 mesi", "answer_type": "number_0_30"},
        {"id": "absence_days", "text": "Giorni totali di assenza per malattia negli ultimi 12 mesi", "answer_type": "number_0_365"},
        {"id": "presenteeism", "text": "Nei giorni lavorati, quanto la salute ha limitato il tuo rendimento? (0 = per niente, 10 = moltissimo)", "answer_type": "scale0_10"},
        {"id": "demands", "text": "Il lavoro richiede lavoro intenso e frenetico", "answer_type": "scale1_5", "options": LIKERT5},
        {"id": "control", "text": "Ho libertà di decidere come organizzare il mio lavoro", "answer_type": "scale1_5", "options": LIKERT5},
    ],
    "answer_type": "mixed",
}

MARS5 = {
    "instrument": "mars5",
    "label": "Usabilità della piattaforma (MARS)",
    "description": "5 domande su quanto la piattaforma ti risulta facile, chiara e utile.",
    "reference": "Mobile App Rating Scale (MARS), Stoyanov et al. 2015 — usabilità valutata dall'utente come nello studio HAHA2022 (Healthc Inform Res 2024).",
    "questions": [
        {"id": "q1", "text": "La piattaforma è facile da usare"},
        {"id": "q2", "text": "Le informazioni sono chiare e comprensibili"},
        {"id": "q3", "text": "Trovo rapidamente quello che mi serve"},
        {"id": "q4", "text": "L'aspetto grafico è curato e piacevole"},
        {"id": "q5", "text": "Mi fido delle informazioni e dei consigli ricevuti"},
    ],
    "answer_type": "scale1_5",
    "options": LIKERT5,
}

INSTRUMENTS = {i["instrument"]: i for i in (WEMWBS7, BPAAT, WSQ, WORK, MARS5)}


def instruments_catalogue():
    return [
        {k: v for k, v in inst.items() if k != "scoring"} for inst in INSTRUMENTS.values()
    ]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def score_instrument(instrument: str, answers: dict):
    """Returns (score, category). Answers keyed by question id.

    Unknown/missing answers raise ValueError so the API layer can return 422.
    """
    if instrument == "wemwbs7":
        total = 0
        for i in range(1, 8):
            v = int(answers.get(f"q{i}"))
            if not 1 <= v <= 5:
                raise ValueError(f"q{i} fuori scala 1–5")
            total += v
        if total <= 19:
            category = "benessere ridotto"
        elif total <= 27:
            category = "benessere moderato"
        else:
            category = "benessere elevato"
        return total, category

    if instrument == "bpaat":
        mod = _int_in(answers.get("q1"), 0, 7, "q1")
        vig = _int_in(answers.get("q2"), 0, 7, "q2")
        if mod >= 5 or vig >= 3:
            return mod + vig, "attivo (≥ soglia OMS)"
        if mod + vig >= 1:
            return mod + vig, "insufficientemente attivo"
        return 0, "sedentario"

    if instrument == "wsq":
        work_h = _num_in(answers.get("q1"), 0, 16, "q1")
        commute_h = _num_in(answers.get("q2"), 0, 16, "q2")
        leisure_h = _num_in(answers.get("q3"), 0, 16, "q3")
        per_day = work_h + commute_h + leisure_h
        if per_day >= 8:
            category = "sedentarietà elevata (≥ 8 h/die)"
        elif per_day >= 6:
            category = "sedentarietà moderata (6–8 h/die)"
        else:
            category = "sedentarietà bassa (< 6 h/die)"
        return round(per_day, 1), category

    if instrument == "work":
        ability = _int_in(answers.get("work_ability"), 0, 10, "work_ability")
        episodes = _int_in(answers.get("absence_episodes"), 0, 365, "absence_episodes")
        days = _int_in(answers.get("absence_days"), 0, 365, "absence_days")
        presenteeism = _int_in(answers.get("presenteeism"), 0, 10, "presenteeism")
        demands = _int_in(answers.get("demands"), 1, 5, "demands")
        control = _int_in(answers.get("control"), 1, 5, "control")

        flags = []
        if ability <= 6:
            flags.append("capacità lavorativa bassa")
        if episodes >= 3:
            flags.append("assenze frequenti (≥ 3 episodi/anno)")
        if presenteeism >= 7:
            flags.append("presentismo elevato")
        if demands >= 4 and control <= 2:
            flags.append("job strain alto (alta richiesta, basso controllo)")

        summary_score = ability - min(episodes, 5) - (presenteeism // 3)
        category = "; ".join(flags) if flags else "nessun segnale critico"
        return summary_score, category

    if instrument == "mars5":
        values = [_int_in(answers.get(f"q{i}"), 1, 5, f"q{i}") for i in range(1, 6)]
        avg = round(sum(values) / len(values), 1)
        category = "da migliorare" if avg < 3 else ("buona" if avg < 4 else "eccellente")
        return avg, category

    raise ValueError(f"Strumento sconosciuto: {instrument}")


def _int_in(value, lo, hi, name):
    v = int(float(value))
    if not lo <= v <= hi:
        raise ValueError(f"{name} fuori intervallo {lo}–{hi}")
    return v


def _num_in(value, lo, hi, name):
    v = float(value)
    if not lo <= v <= hi:
        raise ValueError(f"{name} fuori intervallo {lo}–{hi}")
    return v


# ---------------------------------------------------------------------------
# Digital-pathway engagement (derived metrics, not a questionnaire)
# ---------------------------------------------------------------------------
def compute_engagement(session, patient) -> dict:
    """Adherence/engagement score 0–100 built from platform usage signals.

    Components mirror the 'digital pathway usage' row of the study matrix:
    goal adherence, questionnaire completion, monitoring compliance, chat use.
    """
    today = date.today()
    month_ago = today - timedelta(days=30)

    # 1) Goal adherence: last 4 weeks of check-ins vs target
    goals = session.query(HealthGoal).filter(
        HealthGoal.patient_id == patient.id, HealthGoal.status == "active"
    ).all()
    goal_rows = session.query(GoalCheckIn).filter(
        GoalCheckIn.patient_id == patient.id, GoalCheckIn.week_of >= month_ago
    ).all()
    if goals and goal_rows:
        target = sum(g.frequency_per_week for g in goals) * 4
        done = sum(c.completed_days for c in goal_rows)
        goal_adherence = min(1.0, done / target) if target else 0.0
    elif goals:
        goal_adherence = 0.0
    else:
        goal_adherence = None  # no goals set yet

    # 2) Instrument completion: at least one per instrument in 90 days
    rows = (
        session.query(WellbeingAssessment.instrument)
        .filter(WellbeingAssessment.patient_id == patient.id,
                WellbeingAssessment.taken_on >= today - timedelta(days=90))
        .all()
    )
    filled = {r[0] for r in rows}
    coverage = len(filled) / len(INSTRUMENTS)

    # 3) Monitoring compliance: planned vs delivered home measurements
    plan_items = session.query(MonitoringPlanItem).filter(
        MonitoringPlanItem.patient_id == patient.id, MonitoringPlanItem.active == True  # noqa: E712
    ).all()
    if plan_items:
        expected = 0
        delivered = 0
        for item in plan_items:
            since = date.today() - timedelta(days=30)
            expected += max(1, 30 // max(1, item.frequency_days))
            n = (
                session.query(Observation)
                .filter(Observation.patient_id == patient.id,
                        Observation.code == item.code,
                        Observation.taken_on >= since)
                .count()
            )
            delivered += min(n, max(1, 30 // max(1, item.frequency_days)))
        monitoring = min(1.0, delivered / expected)
    else:
        monitoring = None

    # Weighted composite (0-100); missing components are dropped, not penalized
    parts = [(goal_adherence, 0.4), (coverage, 0.3), (monitoring, 0.3)]
    used_weight = sum(w for v, w in parts if v is not None)
    score = round(sum(v * w for v, w in parts if v is not None) / used_weight * 100) if used_weight else 0

    return {
        "score": score,
        "components": {
            "goal_adherence": None if goal_adherence is None else round(goal_adherence * 100),
            "questionnaire_coverage": round(coverage * 100),
            "monitoring_compliance": None if monitoring is None else round(monitoring * 100),
        },
        "window_days": 30,
        "instruments_completed": sorted(filled),
    }


def answers_json(assessment: WellbeingAssessment):
    return json.loads(assessment.answers)
