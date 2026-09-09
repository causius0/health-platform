"""Risk engine — single source of truth for risk stratification.

Replaces the old duplicated logic (backend `alerts.py` + client-side
`computeFlags`). Everything the UI shows about risk comes from here, and every
threshold carries its literature reference so the clinician can see *why*.

Design contract with the client's requirements
----------------------------------------------
* Each factor is evaluated in one of four states:
    - "risk":       the factor is present / above threshold (counts against)
    - "borderline": near threshold, needs monitoring (neutral)
    - "protective": the factor is *negative* for risk — absent, below threshold
                    or controlled — and is therefore treated as a POSITIVE
                    (protective) factor, with its own literature threshold
                    (not merely the absence of risk).
    - "unknown":    no usable data yet.
* Stratification follows the agreed rule on the *number of distinct active
  risk factors*:  >=4 -> Alto, 2-3 -> Medio, 0-1 -> Basso, with escalation to
  Alto whenever a critically-severe factor is present. "Alto" activates the
  specific monitoring path and the occupational-physician referral.
"""
from datetime import date, datetime, timedelta

from models import (
    AnamnesisAnswer,
    AnamnesisQuestion,
    Observation,
    Patient,
)
import json

MODEL_VERSION = "motore-rischio 2.0"

STATE_RISK = "risk"
STATE_BORDERLINE = "borderline"
STATE_PROTECTIVE = "protective"
STATE_UNKNOWN = "unknown"


def _age(patient) -> int:
    if not patient.birth_date:
        return 0
    today = date.today()
    born = patient.birth_date
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def latest_observations(session, patient_id: int, recency_days: int = 180) -> dict:
    """Most recent observation per metric code within the recency window."""
    since = date.today() - timedelta(days=recency_days)
    rows = (
        session.query(Observation)
        .filter(Observation.patient_id == patient_id, Observation.taken_on >= since)
        .order_by(Observation.taken_on.desc(), Observation.id.desc())
        .all()
    )
    latest = {}
    for row in rows:
        # rows already ordered by date DESC; id DESC keeps ties deterministic
        # (e.g. a home reading recorded after the clinic value on the same day)
        latest.setdefault(row.code, row)
    return latest


def anamnesis_answers(session, patient_id: int) -> dict:
    """Answer values keyed by question code."""
    rows = (
        session.query(AnamnesisAnswer, AnamnesisQuestion)
        .join(AnamnesisQuestion, AnamnesisAnswer.question_id == AnamnesisQuestion.id)
        .filter(AnamnesisAnswer.patient_id == patient_id)
        .all()
    )
    return {q.code: a.value for a, q in rows}


def _component(code, label, domain, state, *, severity=None, value_text="—",
               threshold_text=None, protective_threshold_text=None,
               reference=None, protective_reference=None, detail=None):
    return {
        "code": code,
        "label": label,
        "domain": domain,
        "state": state,
        "severity": severity,          # "alta" | "media" | None
        "value_text": value_text,
        "threshold_text": threshold_text,
        "protective_threshold_text": protective_threshold_text,
        "reference": reference,
        "protective_reference": protective_reference,
        "detail": detail,
    }


# ---------------------------------------------------------------------------
# Factor evaluators
# ---------------------------------------------------------------------------
# Each evaluator returns a component dict. Observation-backed evaluators read
# `obs` (latest observation per metric code); lifestyle evaluators read
# `answers` (anamnesis values keyed by question code).

def _eval_blood_pressure(patient, obs, answers, sex):
    sys_, dia = obs.get("bp_systolic"), obs.get("bp_diastolic")
    if not sys_ and not dia:
        return _component("pressione_arteriosa", "Pressione arteriosa", "clinico", STATE_UNKNOWN)
    s = sys_.value if sys_ else None
    d = dia.value if dia else None
    value_text = f"{int(s or 0)}/{int(d or 0)} mmHg"
    ref = "Linee guida ESC/ESH 2018 (gestione dell'ipertensione arteriosa)"
    if (s and s >= 180) or (d and d >= 110):
        return _component("pressione_arteriosa", "Pressione arteriosa", "clinico", STATE_RISK,
                          severity="alta", value_text=value_text,
                          threshold_text="≥ 140/90 mmHg", protective_threshold_text="< 130/80 mmHg",
                          reference=ref, detail="Valori in ambito di crisi ipertensiva: richiedono valutazione immediata.")
    if (s and s >= 140) or (d and d >= 90):
        sev = "alta" if (s and s >= 160) or (d and d >= 100) else "media"
        return _component("pressione_arteriosa", "Pressione arteriosa", "clinico", STATE_RISK,
                          severity=sev, value_text=value_text,
                          threshold_text="≥ 140/90 mmHg", protective_threshold_text="< 130/80 mmHg",
                          reference=ref)
    if (s and s >= 130) or (d and d >= 85):
        return _component("pressione_arteriosa", "Pressione arteriosa", "clinico", STATE_BORDERLINE,
                          value_text=value_text, threshold_text="≥ 140/90 mmHg",
                          protective_threshold_text="< 130/80 mmHg", reference=ref)
    return _component("pressione_arteriosa", "Pressione arteriosa", "clinico", STATE_PROTECTIVE,
                      value_text=value_text, threshold_text="≥ 140/90 mmHg",
                      protective_threshold_text="< 130/80 mmHg",
                      reference=ref, protective_reference=ref,
                      detail="Pressione controllata: fattore protettivo confermato.")


def _is_diabetic(patient):
    return "diabete" in (patient.primary_diagnosis or "").lower()


def _eval_hba1c(patient, obs, answers, sex):
    row = obs.get("hba1c")
    if not row:
        return _component("compenso_glicemico", "Compenso glicemico (HbA1c)", "clinico", STATE_UNKNOWN)
    v = row.value
    value_text = f"{v:.1f}%"
    if _is_diabetic(patient):
        ref = "Standard AMD-SID per la cura del diabete mellito (target generale < 7.0%)"
        if v >= 8.5:
            return _component("compenso_glicemico", "Compenso glicemico (HbA1c)", "clinico", STATE_RISK,
                              severity="alta", value_text=value_text, threshold_text="> 7.5%",
                              protective_threshold_text="≤ 7.0% (in target)", reference=ref,
                              detail="Compenso gravemente alterato.")
        if v > 7.5:
            return _component("compenso_glicemico", "Compenso glicemico (HbA1c)", "clinico", STATE_RISK,
                              severity="media", value_text=value_text, threshold_text="> 7.5%",
                              protective_threshold_text="≤ 7.0% (in target)", reference=ref)
        if v > 7.0:
            return _component("compenso_glicemico", "Compenso glicemico (HbA1c)", "clinico", STATE_BORDERLINE,
                              value_text=value_text, threshold_text="> 7.5%",
                              protective_threshold_text="≤ 7.0% (in target)", reference=ref)
        return _component("compenso_glicemico", "Compenso glicemico (HbA1c)", "clinico", STATE_PROTECTIVE,
                          value_text=value_text, threshold_text="> 7.5%",
                          protective_threshold_text="≤ 7.0% (in target)", reference=ref,
                          protective_reference=ref,
                          detail="Diabete in target: fattore protettivo confermato (compensato).")
    # No known diabetes: use the screening threshold
    ref = "ADA Standards of Care 2024 (prediabete HbA1c 5.7–6.4%)"
    if v >= 6.5:
        return _component("compenso_glicemico", "Compenso glicemico (HbA1c)", "clinico", STATE_RISK,
                          severity="alta", value_text=value_text, threshold_text="≥ 5.7%",
                          protective_threshold_text="< 5.7%", reference=ref,
                          detail="Valore in ambito diagnostico per diabete: richiede conferma.")
    if v >= 5.7:
        return _component("compenso_glicemico", "Compenso glicemico (HbA1c)", "clinico", STATE_RISK,
                          severity="media", value_text=value_text, threshold_text="≥ 5.7%",
                          protective_threshold_text="< 5.7%", reference=ref,
                          detail="Ambito di prediabete.")
    return _component("compenso_glicemico", "Compenso glicemico (HbA1c)", "clinico", STATE_PROTECTIVE,
                      value_text=value_text, threshold_text="≥ 5.7%", protective_threshold_text="< 5.7%",
                      reference=ref, protective_reference=ref)


def _eval_fasting_glucose(patient, obs, answers, sex):
    row = obs.get("glucose_fasting")
    if not row:
        return _component("glicemia_digiuno", "Glicemia a digiuno", "clinico", STATE_UNKNOWN)
    v = row.value
    ref = "ADA Standards of Care 2024 (IFG 100–125 mg/dL)"
    if v >= 200:
        return _component("glicemia_digiuno", "Glicemia a digiuno", "clinico", STATE_RISK, severity="alta",
                          value_text=f"{int(v)} mg/dL", threshold_text="≥ 126 mg/dL",
                          protective_threshold_text="< 100 mg/dL", reference=ref)
    if v >= 126:
        return _component("glicemia_digiuno", "Glicemia a digiuno", "clinico", STATE_RISK, severity="media",
                          value_text=f"{int(v)} mg/dL", threshold_text="≥ 126 mg/dL",
                          protective_threshold_text="< 100 mg/dL", reference=ref)
    if v >= 100:
        return _component("glicemia_digiuno", "Glicemia a digiuno", "clinico", STATE_BORDERLINE,
                          value_text=f"{int(v)} mg/dL", threshold_text="≥ 126 mg/dL",
                          protective_threshold_text="< 100 mg/dL", reference=ref,
                          detail="Ambito di prediabete (IFG).")
    return _component("glicemia_digiuno", "Glicemia a digiuno", "clinico", STATE_PROTECTIVE,
                      value_text=f"{int(v)} mg/dL", threshold_text="≥ 126 mg/dL",
                      protective_threshold_text="< 100 mg/dL", reference=ref, protective_reference=ref)


def _eval_ldl(patient, obs, answers, sex):
    row = obs.get("ldl")
    if not row:
        return _component("colesterolo_ldl", "Colesterolo LDL", "clinico", STATE_UNKNOWN)
    v = row.value
    ref = "Linee guida ESC/EAS 2019 (target < 100 mg/dL a rischio moderato, < 70 ad alto rischio)"
    if v >= 160:
        return _component("colesterolo_ldl", "Colesterolo LDL", "clinico", STATE_RISK, severity="alta",
                          value_text=f"{int(v)} mg/dL", threshold_text="≥ 130 mg/dL",
                          protective_threshold_text="< 100 mg/dL (in target)", reference=ref)
    if v >= 130:
        return _component("colesterolo_ldl", "Colesterolo LDL", "clinico", STATE_RISK, severity="media",
                          value_text=f"{int(v)} mg/dL", threshold_text="≥ 130 mg/dL",
                          protective_threshold_text="< 100 mg/dL (in target)", reference=ref)
    if v >= 100:
        return _component("colesterolo_ldl", "Colesterolo LDL", "clinico", STATE_BORDERLINE,
                          value_text=f"{int(v)} mg/dL", threshold_text="≥ 130 mg/dL",
                          protective_threshold_text="< 100 mg/dL (in target)", reference=ref)
    return _component("colesterolo_ldl", "Colesterolo LDL", "clinico", STATE_PROTECTIVE,
                      value_text=f"{int(v)} mg/dL", threshold_text="≥ 130 mg/dL",
                      protective_threshold_text="< 100 mg/dL (in target)", reference=ref,
                      protective_reference=ref, detail="LDL in target: fattore protettivo confermato.")


def _eval_hdl(patient, obs, answers, sex):
    row = obs.get("hdl")
    if not row:
        return _component("colesterolo_hdl", "Colesterolo HDL", "clinico", STATE_UNKNOWN)
    v = row.value
    floor = 40 if (sex or "M") == "M" else 50
    ref = f"Linee guida ESC/EAS 2019 (HDL basso se < {floor} mg/dL)"
    value_text = f"{int(v)} mg/dL"
    if v < floor:
        return _component("colesterolo_hdl", "Colesterolo HDL", "clinico", STATE_RISK, severity="media",
                          value_text=value_text, threshold_text=f"< {floor} mg/dL",
                          protective_threshold_text=f"≥ {floor} mg/dL", reference=ref)
    return _component("colesterolo_hdl", "Colesterolo HDL", "clinico", STATE_PROTECTIVE,
                      value_text=value_text, threshold_text=f"< {floor} mg/dL",
                      protective_threshold_text=f"≥ {floor} mg/dL", reference=ref, protective_reference=ref)


def _eval_triglycerides(patient, obs, answers, sex):
    row = obs.get("triglycerides")
    if not row:
        return _component("trigliceridi", "Trigliceridi", "clinico", STATE_UNKNOWN)
    v = row.value
    ref = "Linee guida ESC/EAS 2019 (ipetrigliceridemia ≥ 150 mg/dL)"
    if v >= 150:
        sev = "alta" if v >= 200 else "media"
        return _component("trigliceridi", "Trigliceridi", "clinico", STATE_RISK, severity=sev,
                          value_text=f"{int(v)} mg/dL", threshold_text="≥ 150 mg/dL",
                          protective_threshold_text="< 150 mg/dL", reference=ref)
    return _component("trigliceridi", "Trigliceridi", "clinico", STATE_PROTECTIVE,
                      value_text=f"{int(v)} mg/dL", threshold_text="≥ 150 mg/dL",
                      protective_threshold_text="< 150 mg/dL", reference=ref, protective_reference=ref)


def _eval_kidney(patient, obs, answers, sex):
    egfr, alb = obs.get("egfr"), obs.get("microalbuminuria")
    if not egfr and not alb:
        return _component("funzione_renale", "Funzione renale", "clinico", STATE_UNKNOWN)
    g = egfr.value if egfr else None
    a = alb.value if alb else None
    parts = []
    if g is not None:
        parts.append(f"eGFR {int(g)}")
    if a is not None:
        parts.append(f"albuminuria {int(a)} mg/g")
    ref = "Linee guida KDIGO 2024 (CKD: eGFR < 60 o albuminuria ≥ 30 mg/g)"
    if (g is not None and g < 30) :
        return _component("funzione_renale", "Funzione renale", "clinico", STATE_RISK, severity="alta",
                          value_text=", ".join(parts), threshold_text="eGFR < 60 o albuminuria ≥ 30 mg/g",
                          protective_threshold_text="eGFR ≥ 60 e albuminuria < 30 mg/g", reference=ref,
                          detail="Riduzione severa della filtrazione glomerulare.")
    if (g is not None and g < 60) or (a is not None and a >= 30):
        return _component("funzione_renale", "Funzione renale", "clinico", STATE_RISK, severity="media",
                          value_text=", ".join(parts), threshold_text="eGFR < 60 o albuminuria ≥ 30 mg/g",
                          protective_threshold_text="eGFR ≥ 60 e albuminuria < 30 mg/g", reference=ref)
    return _component("funzione_renale", "Funzione renale", "clinico", STATE_PROTECTIVE,
                      value_text=", ".join(parts), threshold_text="eGFR < 60 o albuminuria ≥ 30 mg/g",
                      protective_threshold_text="eGFR ≥ 60 e albuminuria < 30 mg/g",
                      reference=ref, protective_reference=ref)


def _current_bmi(patient, obs):
    bmi_row = obs.get("bmi")
    if bmi_row:
        return bmi_row.value
    weight_row = obs.get("weight")
    if weight_row and patient.height_cm:
        return round(weight_row.value / (patient.height_cm / 100) ** 2, 1)
    return None


def _eval_adiposity(patient, obs, answers, sex):
    bmi = _current_bmi(patient, obs)
    if bmi is None:
        return _component("adiposita", "Indice di massa corporea (BMI)", "clinico", STATE_UNKNOWN)
    ref = "OMS (sovrappeso BMI 25–29.9, obesità ≥ 30)"
    value_text = f"{bmi:.1f} kg/m²"
    if bmi >= 30:
        return _component("adiposita", "Indice di massa corporea (BMI)", "clinico", STATE_RISK, severity="alta",
                          value_text=value_text, threshold_text="≥ 25 kg/m²",
                          protective_threshold_text="18.5 – 24.9 kg/m²", reference=ref,
                          detail="Obesità (BMI ≥ 30).")
    if bmi >= 25:
        return _component("adiposita", "Indice di massa corporea (BMI)", "clinico", STATE_RISK, severity="media",
                          value_text=value_text, threshold_text="≥ 25 kg/m²",
                          protective_threshold_text="18.5 – 24.9 kg/m²", reference=ref,
                          detail="Sovrappeso.")
    if bmi < 18.5:
        return _component("adiposita", "Indice di massa corporea (BMI)", "clinico", STATE_BORDERLINE,
                          value_text=value_text, threshold_text="≥ 25 kg/m²",
                          protective_threshold_text="18.5 – 24.9 kg/m²", reference=ref,
                          detail="Sottopeso: da valutare.")
    return _component("adiposita", "Indice di massa corporea (BMI)", "clinico", STATE_PROTECTIVE,
                      value_text=value_text, threshold_text="≥ 25 kg/m²",
                      protective_threshold_text="18.5 – 24.9 kg/m²", reference=ref, protective_reference=ref)


def _eval_waist(patient, obs, answers, sex):
    row = obs.get("waist")
    if not row:
        return _component("circonferenza_vita", "Circonferenza vita", "clinico", STATE_UNKNOWN)
    v = row.value
    limit = 94 if (sex or "M") == "M" else 80
    hard = 102 if (sex or "M") == "M" else 88
    ref = f"OMS/IDF (aumentata ≥ {limit} cm, sostanzialmente aumentata ≥ {hard} cm)"
    value_text = f"{int(v)} cm"
    if v >= hard:
        return _component("circonferenza_vita", "Circonferenza vita", "clinico", STATE_RISK, severity="alta",
                          value_text=value_text, threshold_text=f"≥ {limit} cm",
                          protective_threshold_text=f"< {limit} cm", reference=ref)
    if v >= limit:
        return _component("circonferenza_vita", "Circonferenza vita", "clinico", STATE_RISK, severity="media",
                          value_text=value_text, threshold_text=f"≥ {limit} cm",
                          protective_threshold_text=f"< {limit} cm", reference=ref)
    return _component("circonferenza_vita", "Circonferenza vita", "clinico", STATE_PROTECTIVE,
                      value_text=value_text, threshold_text=f"≥ {limit} cm",
                      protective_threshold_text=f"< {limit} cm", reference=ref, protective_reference=ref)


# --- anamnesis-backed factors -------------------------------------------------
# Options in the question catalogue carry "risk": true / "protective": true.
# The engine reads those flags so clinicians can re-word questions without
# touching this file.

ANAMNESIS_FACTORS = [
    # (factor_code, label, domain, question_code)
    ("fumo", "Fumo", "stile_di_vita", "smoking"),
    ("attivita_fisica", "Attività fisica", "stile_di_vita", "physical_activity"),
    ("sedentarieta", "Sedentarietà", "lavoro", "sedentary_hours"),
    ("alcol", "Consumo di alcol", "stile_di_vita", "alcohol"),
    ("sonno", "Sonno", "stile_di_vita", "sleep"),
    ("alimentazione", "Alimentazione", "stile_di_vita", "nutrition"),
    ("stress_lavorativo", "Stress e carico lavorativo", "lavoro", "stress"),
    ("familiarita", "Familiarità", "storia_clinica", "family_history"),
]

_FACTOR_REFERENCES = {
    "fumo": ("Danno attivo da fumo attivo (OMS).",
             "US Surgeon General 2010: a 12 mesi dall'cessazione il rischio di coronaropatia è circa dimezzato rispetto a chi continua a fumare."),
    "attivita_fisica": ("OMS 2020: < 150 min/settimana di attività moderata.",
                        "OMS 2020: ≥ 150 min/settimana di attività moderata (o ≥ 75 min intensa) — livello di attività sufficiente."),
    "sedentarieta": ("Sedentarietà prolungata ≥ 8 h/die associata a maggior rischio cardiometabolico (BMC Public Health 2022, sintesi evidenze).",
                     "Tempo seduto < 6 h/die — ambito a basso rischio nelle sintesi di coorte."),
    "alcol": ("Consumo sopra i limiti indicati (EFSA/OMS: rischio cresce già a basse dosi).",
              "Consumo entro i limiti raccomandati (≤ 2 unit/die uomini, ≤ 1 donna, non tutti i giorni)."),
    "sonno": ("Durata < 6 h o > 9 h associata a maggior rischio cardiometabolico (meta-analisi Cappuccio et al., 2010).",
              "Durata 7–9 h raccomandata da AASM/NSF."),
    "alimentazione": ("Pattern alimentare ricco di bevande zuccherate e alimenti ultraprocessati (linee guida OMS/CREA).",
                      "Pattern equilibrato/mediterraneo (Piramide alimentare CREA-INRAN; OMS)."),
    "stress_lavorativo": ("Alta richiesta + basso controllo (job strain, modello Karasek JCQ) associato a rischio cardiovascolare.",
                          "Bassa tensione percepita e buone risorse di coping."),
    "familiarita": ("Malattia cardiovascolare/diabete in parente di I grado in età precoce (prevenzione cardiovascolare SIP).", None),
}


def _eval_anamnesis_factor(factor_code, label, domain, question_code, answers):
    value = answers.get(question_code)
    if not value:
        return _component(factor_code, label, domain, STATE_UNKNOWN)
    # Find the matching option in the catalogue (passed via answers context:
    # the caller merges option metadata into `answers_meta`).
    meta = ANSWER_META.get((question_code, value))
    risk_flag = bool(meta and meta.get("risk"))
    protect_flag = bool(meta and meta.get("protective"))
    ref_risk, ref_prot = _FACTOR_REFERENCES.get(factor_code, (None, None))
    if risk_flag:
        return _component(factor_code, label, domain, STATE_RISK, severity="media",
                          value_text=str(value), reference=ref_risk,
                          protective_threshold_text="vedi criterio protettivo",
                          protective_reference=ref_prot)
    if protect_flag:
        return _component(factor_code, label, domain, STATE_PROTECTIVE,
                          value_text=str(value), protective_reference=ref_prot,
                          reference=ref_risk,
                          detail="Fattore negativo per rischio → conteggiato come protettivo.")
    return _component(factor_code, label, domain, STATE_BORDERLINE, value_text=str(value),
                      reference=ref_risk)


# Options metadata is populated by the API layer at import time from the
# question catalogue (see services.anamnesis.load_answer_meta). Keeping it as a
# module-level map makes the pure evaluators trivially testable.
ANSWER_META = {}


def evaluate_patient(session, patient, recency_days: int = 180) -> dict:
    """Full risk evaluation for one patient. Pure apart from DB reads."""
    sex = patient.sex or "M"
    obs = latest_observations(session, patient.id, recency_days)
    answers = anamnesis_answers(session, patient.id)

    components = [
        _eval_blood_pressure(patient, obs, answers, sex),
        _eval_hba1c(patient, obs, answers, sex),
        _eval_fasting_glucose(patient, obs, answers, sex),
        _eval_ldl(patient, obs, answers, sex),
        _eval_hdl(patient, obs, answers, sex),
        _eval_triglycerides(patient, obs, answers, sex),
        _eval_kidney(patient, obs, answers, sex),
        _eval_adiposity(patient, obs, answers, sex),
        _eval_waist(patient, obs, answers, sex),
    ]
    for fcode, label, domain, qcode in ANAMNESIS_FACTORS:
        components.append(_eval_anamnesis_factor(fcode, label, domain, qcode, answers))

    risks = [c for c in components if c["state"] == STATE_RISK]
    protectives = [c for c in components if c["state"] == STATE_PROTECTIVE]
    risk_count = len(risks)
    protective_count = len(protectives)
    has_critical = any(c["severity"] == "alta" for c in risks)

    if risk_count >= 4 or (risk_count >= 1 and has_critical):
        level = "alto"
    elif risk_count >= 2:
        level = "medio"
    else:
        level = "basso"

    recs = recommendations(level, risks)
    return {
        "model_version": MODEL_VERSION,
        "level": level,
        "risk_count": risk_count,
        "protective_count": protective_count,
        "borderline_count": sum(1 for c in components if c["state"] == STATE_BORDERLINE),
        "components": components,
        "risks": risks,
        "protectives": protectives,
        "recommendations": recs,
        "has_critical": has_critical,
        "age": _age(patient),
    }


def recommendations(level, risks):
    if level == "alto":
        recs = [
            "Attivare il percorso di monitoraggio specifico (controllo settimanale con coach digitale).",
            "Programmare la visita con il medico del lavoro entro 2 settimane.",
            "Follow-up telefonico dell'operatore sanitario entro 7 giorni.",
        ]
        critical = [c["label"] for c in risks if c["severity"] == "alta"]
        if critical:
            recs.insert(0, "Valori critici rilevati (" + ", ".join(critical) + "): verifica clinica prioritaria.")
        return recs
    if level == "medio":
        return [
            "Rafforzare gli obiettivi di stile di vita con check-in settimanale.",
            "Follow-up entro 14 giorni per verificare l'aderenza.",
            "Rivalutare la stratificazione al prossimo controllo di laboratorio.",
        ]
    return [
        "Mantenere gli obiettivi correnti e i controlli periodici (trimestrali).",
        "Consolidare i fattori protettivi raggiunti.",
    ]


def serialize_assessment(evaluation: dict) -> dict:
    """Public JSON shape for the API layer."""
    return {
        "model_version": evaluation["model_version"],
        "level": evaluation["level"],
        "risk_count": evaluation["risk_count"],
        "protective_count": evaluation["protective_count"],
        "borderline_count": evaluation["borderline_count"],
        "has_critical": evaluation["has_critical"],
        "age": evaluation["age"],
        "recommendations": evaluation["recommendations"],
        "components": evaluation["components"],
    }


# ---------------------------------------------------------------------------
# Alert derivation (feeds the doctor's rail and the patient overview)
# ---------------------------------------------------------------------------
def clinical_alerts(session, patient, evaluation) -> list:
    """Derived (not stored) alerts: critical values, bad trends, overdue care."""
    alerts = []
    today = date.today()

    # Critical active factors
    for c in evaluation["risks"]:
        if c["severity"] == "alta":
            alerts.append({
                "severity": "critical",
                "title": f"{c['label']} — valore critico",
                "message": f"{c['value_text']} (soglia {c['threshold_text']})",
                "patient_id": patient.id,
                "reference": c["reference"],
            })

    # Worsening trends for key metrics
    trend_specs = {
        "hba1c": (0.5, -0.3, "%"),
        "ldl": (20, -20, "mg/dL"),
        "bp_systolic": (10, -10, "mmHg"),
    }
    for code, (up, down, unit) in trend_specs.items():
        rows = (
            session.query(Observation)
            .filter(Observation.patient_id == patient.id, Observation.code == code)
            .order_by(Observation.taken_on.desc())
            .limit(2)
            .all()
        )
        if len(rows) == 2:
            delta = rows[0].value - rows[1].value
            name = rows[0].label
            if delta >= up:
                alerts.append({
                    "severity": "warning",
                    "title": f"{name} in aumento",
                    "message": f"+{delta:.1f} {unit} rispetto al controllo precedente ({rows[0].taken_on.isoformat()})",
                    "patient_id": patient.id,
                })
            elif delta <= down:
                alerts.append({
                    "severity": "info",
                    "title": f"{name} in miglioramento",
                    "message": f"{delta:.1f} {unit} rispetto al controllo precedente",
                    "patient_id": patient.id,
                })

    # Stale observations: no labs in the recency window
    if not evaluation["components"] or all(c["state"] == STATE_UNKNOWN for c in evaluation["components"]):
        alerts.append({
            "severity": "warning",
            "title": "Nessun dato recente",
            "message": "Nessuna misurazione negli ultimi mesi: programmabile un controllo.",
            "patient_id": patient.id,
        })
    return alerts
