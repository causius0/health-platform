"""Risk engine unit tests: thresholds, negative→protective reversal, stratification."""
import json
from datetime import date, timedelta

import pytest

from services import risk_engine
from services.risk_engine import (
    STATE_BORDERLINE,
    STATE_PROTECTIVE,
    STATE_RISK,
    STATE_UNKNOWN,
    MODEL_VERSION,
    evaluate_patient,
    _eval_anamnesis_factor,
    _eval_blood_pressure,
    _eval_hba1c,
)


class FakeObs:
    def __init__(self, value):
        self.value = value
        self.taken_on = date.today()


def _component_by_code(components, code):
    return next(c for c in components if c["code"] == code)


# ---------------------------------------------------------------------------
# Blood pressure
# ---------------------------------------------------------------------------
def test_bp_optimal_is_protective():
    c = _eval_blood_pressure(None, {"bp_systolic": FakeObs(122), "bp_diastolic": FakeObs(76)}, {}, "M")
    assert c["state"] == STATE_PROTECTIVE
    assert "ESC/ESH" in c["reference"]
    assert c["protective_threshold_text"] == "< 130/80 mmHg"


def test_bp_high_is_risk():
    c = _eval_blood_pressure(None, {"bp_systolic": FakeObs(148), "bp_diastolic": FakeObs(92)}, {}, "M")
    assert c["state"] == STATE_RISK
    assert c["severity"] == "media"


def test_bp_crisis_is_critical_risk():
    c = _eval_blood_pressure(None, {"bp_systolic": FakeObs(182), "bp_diastolic": FakeObs(112)}, {}, "M")
    assert c["state"] == STATE_RISK
    assert c["severity"] == "alta"


def test_bp_high_normal_is_borderline():
    c = _eval_blood_pressure(None, {"bp_systolic": FakeObs(134), "bp_diastolic": FakeObs(84)}, {}, "M")
    assert c["state"] == STATE_BORDERLINE


def test_bp_missing_is_unknown():
    c = _eval_blood_pressure(None, {}, {}, "M")
    assert c["state"] == STATE_UNKNOWN


# ---------------------------------------------------------------------------
# HbA1c: same value, different meaning by diagnosis
# ---------------------------------------------------------------------------
def _patient_like(diagnosis, sex="M"):
    class P:
        pass

    p = P()
    p.primary_diagnosis = diagnosis
    p.sex = sex
    p.birth_date = date(1985, 5, 5)
    return p


def test_hba1c_in_target_counts_as_protective_for_diabetic():
    patient = _patient_like("Diabete mellito tipo 2")
    c = _eval_hba1c(patient, {"hba1c": FakeObs(6.8)}, {}, "M")
    assert c["state"] == STATE_PROTECTIVE
    assert "AMD-SID" in c["reference"]


def test_hba1c_above_target_is_risk_for_diabetic():
    patient = _patient_like("Diabete mellito tipo 2")
    c = _eval_hba1c(patient, {"hba1c": FakeObs(7.8)}, {}, "M")
    assert c["state"] == STATE_RISK


def test_hba1c_normal_is_protective_for_non_diabetic():
    patient = _patient_like("Ipertensione arteriosa")
    c = _eval_hba1c(patient, {"hba1c": FakeObs(5.4)}, {}, "M")
    assert c["state"] == STATE_PROTECTIVE


# ---------------------------------------------------------------------------
# Anamnesis-backed factors: negative → positive reversal
# ---------------------------------------------------------------------------
def setup_module(module):
    # simulate catalogue metadata as load_answer_meta would
    risk_engine.ANSWER_META = {
        ("smoking", "Fumatore/a attuale"): {"risk": True, "protective": False},
        ("smoking", "Ex fumatore/a (da almeno 12 mesi)"): {"risk": False, "protective": True},
        ("physical_activity", "Sedentario/a"): {"risk": True, "protective": False},
        ("physical_activity", "3–4 volte a settimana"): {"risk": False, "protective": True},
    }


def test_current_smoker_is_risk_with_reference():
    c = _eval_anamnesis_factor("fumo", "Fumo", "stile_di_vita", "smoking",
                               {"smoking": "Fumatore/a attuale"})
    assert c["state"] == STATE_RISK
    assert c["reference"]


def test_ex_smoker_beyond_12_months_is_protective():
    """The client rule: a negative factor (quit smoking, ≥12 months, US Surgeon
    General threshold) is displayed as a protective factor."""
    c = _eval_anamnesis_factor("fumo", "Fumo", "stile_di_vita", "smoking",
                               {"smoking": "Ex fumatore/a (da almeno 12 mesi)"})
    assert c["state"] == STATE_PROTECTIVE
    assert "12 mesi" in (c["protective_reference"] or "")


def test_unknown_answer_is_neither_risk_nor_protective():
    c = _eval_anamnesis_factor("fumo", "Fumo", "stile_di_vita", "smoking", {})
    assert c["state"] == STATE_UNKNOWN


def test_active_lifestyle_is_protective():
    c = _eval_anamnesis_factor("attivita_fisica", "Attività fisica", "stile_di_vita",
                               "physical_activity", {"physical_activity": "3–4 volte a settimana"})
    assert c["state"] == STATE_PROTECTIVE


# ---------------------------------------------------------------------------
# Stratification over the whole patient
# ---------------------------------------------------------------------------
def test_same_day_observations_latest_id_wins(app, _seed):
    """A home measurement recorded after the clinic value on the same day is
    the one the engine and the monitoring plan must consider."""
    from datetime import timedelta as _td

    with app.app_context():
        from extensions import db
        from models import Observation, Patient

        patient = db.session.get(Patient, _seed["patient"])
        today = date.today()
        db.session.add(Observation(patient_id=patient.id, code="bp_systolic",
                                   value=140, source="clinic", taken_on=today))
        db.session.flush()
        db.session.add(Observation(patient_id=patient.id, code="bp_systolic",
                                   value=125, source="patient_home", taken_on=today))
        db.session.commit()

        latest = risk_engine.latest_observations(db.session, patient.id)
        assert latest["bp_systolic"].value == 125
        assert latest["bp_systolic"].source == "patient_home"


def test_full_evaluation_structure(app, _seed):
    with app.app_context():
        from extensions import db
        from models import Patient

        patient = db.session.get(Patient, _seed["patient"])
        result = evaluate_patient(db.session, patient)
        assert result["model_version"] == MODEL_VERSION
        assert result["level"] in ("basso", "medio", "alto")
        codes = [c["code"] for c in result["components"]]
        # every documented factor family is evaluated exactly once
        for expected in ("pressione_arteriosa", "compenso_glicemico", "colesterolo_ldl",
                         "funzione_renale", "adiposita", "fumo", "attivita_fisica"):
            assert codes.count(expected) == 1
        # her HbA1c 7.8% (diabetic) and smoking are active risks
        hba1c = _component_by_code(result["components"], "compenso_glicemico")
        assert hba1c["state"] == STATE_RISK
        smoking = _component_by_code(result["components"], "fumo")
        assert smoking["state"] == STATE_RISK
        # active risks in the fixture: HbA1c 7.8% (diabetic, > 7.5), BP 146/88,
        # current smoking → exactly 3, none critical ⇒ "medio" per the agreed rule
        assert result["risk_count"] == 3
        assert result["level"] == "medio"
