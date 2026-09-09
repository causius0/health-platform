"""Deterministic red-flag interceptor for the chat.

Small LLMs cannot be trusted to escalate emergencies reliably (proven in QA:
a chest-pain message received breathing exercises instead of a 118 call).
These patterns are therefore checked BEFORE the model, and a match bypasses
it entirely: the worker gets a fixed escalation message, the thread is routed
to an operator and an immediate follow-up is opened.
"""
import re

# (pattern, emergency label) — Italian symptom phrasings of red-flag presentations
PATTERNS = [
    (r"(dolore|pressione|fastidio).{0,30}(al petto|petto|torace).{0,60}(adesso|in questo momento|forte|intenso|ora)|forte.{0,25}dolore.{0,25}(petto|torace)|(dolore (al|del) petto)",
     "dolore al petto in corso"),
    (r"(mi sento (mancare|svenire)|sto per svenire|perdita di coscienza|sono svenuto)",
     "sensazione di svenimento"),
    (r"(non riesco (a )?(a )?respirare|mancanza di respiro (grave|improvvisa)|asfissi)",
     "difficoltà respiratoria grave"),
    (r"(bocca storta|non riesco a parlare|parole impastate|visto doppio|vista doppia|non sento (il )?braccio)",
     "possibili segni neurologici (ictus)"),
    (r"(sanguina (molto|tanto|tanto)|emorragia|non smette di sanguinare)",
     "sanguinamento non controllato"),
]

ESCALATION_MESSAGE = (
    "⚠ MESSAGGIO AUTOMATICO DI SICUREZZA\n"
    "Quello che descrivi può richiedere un intervento immediato. "
    "Se i sintomi sono presenti in questo momento: INTERROMPI tutto e chiama "
    "subito il 118 (o il numero di emergenza del tuo sito). "
    "Un operatore sanitario della piattaforma ti richiama immediatamente: "
    "resta dove sei, se possibile, fatti accompagnare da qualcuno e tieni "
    "a portata di mano gli eventuali farmaci che assumi."
)


def detect_emergency(text: str) -> str | None:
    """Return the matched red-flag label, or None if no emergency pattern hits."""
    if not text:
        return None
    normalized = " ".join(text.lower().split())
    for pattern, label in PATTERNS:
        if re.search(pattern, normalized):
            return label
    return None
