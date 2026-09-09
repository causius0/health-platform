"""Chat threads: bot coaching with human handoff to the operator.

Thread lifecycle (kind="coach", patient side):
    bot  → (patient escalates) → waiting_operator → (doctor claims) →
    with_operator → (doctor closes) → bot
kind="clinical" threads are the doctor's private assistant about a patient.
"""
import json

from flask import Blueprint, jsonify, request

from extensions import db, limiter
from models import ChatMessage, ChatThread, Patient
from api.helpers import current_user, get_patient_for, require_auth, require_role
from services import risk_engine
from services.chat_safety import ESCALATION_MESSAGE, detect_emergency
from services.context import build_doctor_overview, build_patient_context
from services.llm import get_llm_response

bp = Blueprint("chat", __name__, url_prefix="/api/chat")


def _thread_payload(t: ChatThread) -> dict:
    patient = db.session.get(Patient, t.patient_id)
    return {
        "id": t.id,
        "kind": t.kind,
        "status": t.status,
        "patient_id": t.patient_id,
        "patient_name": patient.full_name if patient else "—",
        "handled_by_user_id": t.handled_by_user_id,
        "subject": t.subject,
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
        "message_count": len(t.messages),
    }


def _message_payload(m: ChatMessage) -> dict:
    return {
        "id": m.id,
        "sender": m.sender,
        "content": m.content,
        "created_at": m.created_at.isoformat(),
    }


@bp.get("/threads")
@require_auth
def list_threads(user):
    if user.role == "patient":
        patient = user.patient_profile
        rows = (
            db.session.query(ChatThread)
            .filter(ChatThread.patient_id == patient.id, ChatThread.kind == "coach")
            .order_by(ChatThread.updated_at.desc())
            .all()
        )
    else:
        rows = (
            db.session.query(ChatThread)
            .filter(
                ChatThread.kind == "coach",
                ChatThread.status.in_(["waiting_operator", "with_operator"]),
            )
            .order_by(ChatThread.updated_at.desc())
            .all()
        )
    return jsonify([_thread_payload(t) for t in rows])


@bp.post("/threads")
@require_auth
def start_thread(user):
    body = request.get_json(silent=True) or {}
    if user.role == "patient":
        patient = user.patient_profile
        # reuse the single active coach thread
        thread = (
            db.session.query(ChatThread)
            .filter(ChatThread.patient_id == patient.id, ChatThread.kind == "coach")
            .order_by(ChatThread.updated_at.desc())
            .first()
        )
        if thread is None:
            thread = ChatThread(patient_id=patient.id, kind="coach", status="bot")
            db.session.add(thread)
            db.session.flush()
            greeting = (
                "Ciao! Sono il tuo coach di prevenzione. Posso spiegarti i tuoi valori, "
                "suggerirti obiettivi settimanali e aiutarti a orientarti nel percorso. "
                "Se preferisci parlare con un operatore, usa il pulsante 'Parla con un operatore'."
            )
            db.session.add(ChatMessage(thread_id=thread.id, sender="bot", content=greeting))
        db.session.commit()
        return jsonify(_thread_payload(thread)), 201

    # doctor: clinical thread about a patient (reuse the existing open one)
    patient_id = body.get("patient_id")
    if not patient_id:
        return jsonify({"error": "patient_id obbligatorio"}), 400
    patient = db.session.get(Patient, int(patient_id))
    if not patient:
        return jsonify({"error": "Paziente non trovato"}), 404
    thread = (
        db.session.query(ChatThread)
        .filter(ChatThread.patient_id == patient.id, ChatThread.kind == "clinical")
        .order_by(ChatThread.updated_at.desc())
        .first()
    )
    if thread is None:
        thread = ChatThread(
            patient_id=patient.id, kind="clinical", status="bot",
            subject=f"Analisi clinica — {patient.full_name}",
        )
        db.session.add(thread)
        db.session.commit()
    return jsonify(_thread_payload(thread)), 201


@bp.get("/threads/<int:thread_id>")
@require_auth
def thread_detail(user, thread_id):
    thread = _accessible_thread(user, thread_id)
    if not thread:
        return jsonify({"error": "Conversazione non trovata"}), 404
    payload = _thread_payload(thread)
    payload["messages"] = [_message_payload(m) for m in thread.messages]
    return jsonify(payload)


def _deduct_bot_reply(response):
    """Count (against the rate limit) only patient messages answered by the bot."""
    from flask import g
    return getattr(g, "chat_bot_reply", False) and response.status_code == 201


@bp.post("/threads/<int:thread_id>/messages")
@limiter.limit("30 per hour", deduct_when=_deduct_bot_reply)
@require_auth
def post_message(user, thread_id):
    from flask import g
    thread = _accessible_thread(user, thread_id)
    if not thread:
        return jsonify({"error": "Conversazione non trovata"}), 404
    body = request.get_json(silent=True) or {}
    content = (body.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Messaggio vuoto"}), 400
    if len(content) > 4000:
        return jsonify({"error": "Messaggio troppo lungo"}), 400

    patient = db.session.get(Patient, thread.patient_id)

    if user.role == "doctor":
        sender = "doctor"
        db.session.add(ChatMessage(
            thread_id=thread.id, sender=sender, sender_user_id=user.id, content=content,
        ))
        db.session.flush()
        # the clinician gets an assistant analysis of the message
        context = build_patient_context(db.session, patient, role="doctor") if thread.kind == "clinical" \
            else build_doctor_overview(db.session, user.id)
        reply = get_llm_response(content, context, role="doctor")
        db.session.add(ChatMessage(thread_id=thread.id, sender="bot", content=reply))
        db.session.commit()
        return jsonify({"message": _message_payload(thread.messages[-1])}), 201

    # patient side — messages answered by the bot consume the hourly budget
    if thread.status == "bot":
        g.chat_bot_reply = True

    db.session.add(ChatMessage(
        thread_id=thread.id, sender="patient", sender_user_id=user.id, content=content,
    ))
    db.session.flush()

    # red-flag interceptor: emergencies NEVER reach the LLM. Deterministic
    # escalation message + operator routing + immediate follow-up.
    if thread.kind == "coach" and thread.status == "bot":
        flag = detect_emergency(content)
        if flag:
            from models import FollowUp
            from datetime import date
            thread.status = "waiting_operator"
            thread.subject = f"Emergenza da chat: {flag}"[:200]
            db.session.add(ChatMessage(
                thread_id=thread.id, sender="bot",
                content=f"{ESCALATION_MESSAGE}\n(Rilevato: {flag})",
            ))
            has_pending = (
                db.session.query(FollowUp)
                .filter_by(patient_id=patient.id, status="pending",
                           reason=f"Emergenza da chat: {flag}")
                .first()
            )
            if not has_pending:
                db.session.add(FollowUp(
                    patient_id=patient.id, created_by_user_id=user.id,
                    due_on=date.today(), reason=f"Emergenza da chat: {flag}",
                    channel="chiamata",
                ))
            db.session.commit()
            return jsonify({
                "message": _message_payload(thread.messages[-1]),
                "escalation": True,
                "escalation_reason": flag,
            }), 201

    if thread.status == "waiting_operator":
        # Queued for the human operator: no bot reply
        db.session.commit()
        return jsonify({
            "message": _message_payload(thread.messages[-1]),
            "queued_for_operator": True,
        }), 201

    if thread.status == "with_operator":
        db.session.commit()
        return jsonify({
            "message": _message_payload(thread.messages[-1]),
            "queued_for_operator": True,
        }), 201

    # bot mode: build context and answer
    if thread.kind == "coach":
        context = build_patient_context(db.session, patient, role="patient")
        evaluation = risk_engine.evaluate_patient(db.session, patient)
        hints = {
            "first_name": patient.first_name,
            "level": evaluation["level"],
            "risks": [c["label"] for c in evaluation["risks"]],
            "protectives": [c["label"] for c in evaluation["protectives"]],
        }
    else:
        context = build_patient_context(db.session, patient, role="doctor")
        hints = {}
    reply = get_llm_response(content, context, role="patient" if thread.kind == "coach" else "doctor", hints=hints)
    db.session.add(ChatMessage(thread_id=thread.id, sender="bot", content=reply))
    db.session.commit()
    return jsonify({"message": _message_payload(thread.messages[-1])}), 201


@bp.post("/threads/<int:thread_id>/escalate")
@require_auth
def escalate(user, thread_id):
    thread = _accessible_thread(user, thread_id)
    if not thread:
        return jsonify({"error": "Conversazione non trovata"}), 404
    if user.role != "patient":
        return jsonify({"error": "Solo il lavoratore può richiedere l'operatore"}), 403
    if thread.status not in ("bot",):
        return jsonify({"error": "Conversazione già presa in carico o in coda"}), 400
    body = request.get_json(silent=True) or {}
    thread.subject = (body.get("subject") or thread.subject or "Richiesta operatore")[:200]
    thread.status = "waiting_operator"
    note = (
        "Richiesta di presa in carico registrata. Un operatore sanitario ti risponderà qui "
        "quanto prima. Nel frattempo puoi continuare a scrivere: i messaggi arrivano all'operatore."
    )
    db.session.add(ChatMessage(thread_id=thread.id, sender="bot", content=note))
    db.session.commit()
    return jsonify(_thread_payload(thread))


@bp.post("/threads/<int:thread_id>/claim")
@require_role("doctor")
def claim(user, thread_id):
    thread = db.session.get(ChatThread, thread_id)
    if not thread:
        return jsonify({"error": "Conversazione non trovata"}), 404
    if thread.status not in ("waiting_operator", "with_operator"):
        return jsonify({"error": "Conversazione non in coda"}), 400
    thread.status = "with_operator"
    thread.handled_by_user_id = user.id
    doctor = user.doctor_profile
    doctor_name = f"dott. {doctor.first_name} {doctor.last_name}" if doctor else "Un operatore sanitario"
    db.session.add(ChatMessage(
        thread_id=thread.id, sender="bot",
        content=f"{doctor_name} ha preso in carico la conversazione e ti risponderà qui.",
    ))
    db.session.commit()
    return jsonify(_thread_payload(thread))


@bp.post("/threads/<int:thread_id>/close")
@require_role("doctor")
def close(user, thread_id):
    thread = db.session.get(ChatThread, thread_id)
    if not thread:
        return jsonify({"error": "Conversazione non trovata"}), 404
    if thread.status != "with_operator":
        return jsonify({"error": "Conversazione non in gestione"}), 400
    thread.status = "bot"
    thread.handled_by_user_id = None
    db.session.add(ChatMessage(
        thread_id=thread.id, sender="bot",
        content="L'operatore ha chiuso la presa in carico. Puoi continuare con l'assistente automatico o richiedere di nuovo un operatore.",
    ))
    db.session.commit()
    return jsonify(_thread_payload(thread))


@bp.delete("/threads/<int:thread_id>")
@require_auth
def delete_thread(user, thread_id):
    """GDPR-style deletion: the thread owner removes its history."""
    thread = _accessible_thread(user, thread_id, for_delete=True)
    if not thread:
        return jsonify({"error": "Conversazione non trovata"}), 404
    db.session.delete(thread)
    db.session.commit()
    return jsonify({"ok": True})


def _accessible_thread(user, thread_id, for_delete=False):
    thread = db.session.get(ChatThread, thread_id)
    if not thread:
        return None
    if user.role == "patient":
        if thread.patient_id != user.patient_profile.id or thread.kind != "coach":
            return None
        return thread
    # doctors can access coach threads for handoff and their clinical threads
    if thread.kind == "coach" and thread.status not in ("waiting_operator", "with_operator"):
        return None
    return thread
