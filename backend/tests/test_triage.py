"""Triage protocol engine tests: traffic-light tiers and escalation."""
from services.triage_protocols import (
    DISPOSITIONS,
    PROTOCOLS,
    evaluate_protocol,
    get_protocol,
)


def test_every_protocol_is_wellformed():
    for p in PROTOCOLS:
        assert p["questions"], p["code"]
        qids = {q["id"] for q in p["questions"]}
        assert set(p["red"]).issubset(qids), p["code"]
        for rule in p["amber"]:
            assert "disposition" in rule
        assert p["safety_net"]


def test_disposition_catalogue_matches_tiers():
    for code, d in DISPOSITIONS.items():
        if code in ("emergenza_118", "pronto_soccorso"):
            assert d["tier"] == "rosso"
        elif code == "autogestione":
            assert d["tier"] == "verde"
        else:
            assert d["tier"] == "arancione"


def test_chest_pain_red_flag_goes_to_emergency():
    protocol = get_protocol("dolore_toracico")
    result = evaluate_protocol(protocol, {"q1": "sì"}, {})
    assert result["tier"] == "rosso"
    assert result["disposition"] == "emergenza_118"
    assert result["red_flags"]


def test_abdominal_pain_persistent_is_orange_with_visit():
    protocol = get_protocol("algie_addominali")
    answers = {"q1": "no", "q2": "no", "q3": "no", "q4": "no",
               "q5": "sì", "q6": "no", "q7": "no"}
    result = evaluate_protocol(protocol, answers, {"diabetes": False, "age": 38, "risk_level": "medio"})
    assert result["tier"] == "arancione"
    assert result["disposition"] == "visita_48h"
    assert result["trail"]


def test_diabetic_with_abdominal_vomiting_escalates_to_teleconsult():
    protocol = get_protocol("algie_addominali")
    answers = {"q1": "no", "q2": "no", "q3": "no", "q4": "no",
               "q5": "no", "q6": "no", "q7": "sì"}
    # mild picture, but the diabetes context rule fires
    result = evaluate_protocol(protocol, answers, {"diabetes": True, "age": 38, "risk_level": "medio"})
    assert result["tier"] == "arancione"
    assert result["disposition"] == "teleconsulto"


def test_mild_picture_stays_green():
    protocol = get_protocol("cefalea")
    answers = {"q1": "no", "q2": "no", "q3": "no", "q4": "no", "q5": "no", "q6": "sì"}
    result = evaluate_protocol(protocol, answers, {"risk_level": "basso"})
    assert result["tier"] == "verde"
    assert result["disposition"] == "autogestione"
    assert result["safety_net"]


def test_high_risk_worker_never_leaves_green():
    """Risk modulation: alto profile ⇒ at least a teleconsult for mild calls."""
    protocol = get_protocol("cefalea")
    answers = {"q1": "no", "q2": "no", "q3": "no", "q4": "no", "q5": "no", "q6": "sì"}
    result = evaluate_protocol(protocol, answers, {"risk_level": "alto"})
    assert result["tier"] == "arancione"
    assert result["disposition"] == "teleconsulto"


def test_red_flag_wins_over_everything():
    protocol = get_protocol("vertigini")
    answers = {"q1": "sì", "q4": "sì", "q5": "sì"}
    result = evaluate_protocol(protocol, answers, {"risk_level": "basso"})
    assert result["tier"] == "rosso"
    assert result["disposition"] == "emergenza_118"
