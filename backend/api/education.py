"""Education library + printable lab request (richiesta di laboratorio)."""
from flask import Blueprint, Response, jsonify

from extensions import db
from models import METRIC_CODES
from api.helpers import require_auth, require_role
from services import education

bp = Blueprint("education", __name__, url_prefix="/api")


@bp.get("/education")
@require_auth
def list_articles(user):
    return jsonify(education.summary_list())


@bp.get("/education/<article_id>")
@require_auth
def article(user, article_id):
    found = education.find(article_id)
    if not found:
        return jsonify({"error": "Articolo non trovato"}), 404
    return jsonify(found)


# ---------------------------------------------------------------------------
# Printable lab request (invio richieste di laboratorio)
# ---------------------------------------------------------------------------
LAB_TESTS = [
    ("hba1c", "Emoglobina glicata (HbA1c)"),
    ("glucose_fasting", "Glicemia a digiuno"),
    ("ldl", "Colesterolo LDL"),
    ("hdl", "Colesterolo HDL"),
    ("total_cholesterol", "Colesterolo totale"),
    ("triglycerides", "Trigliceridi"),
    ("creatinine", "Creatininemia"),
    ("egfr", "Filtrato glomerulare (eGFR)"),
    ("microalbuminuria", "Microalbuminuria (urine Mine)"),
]


@bp.get("/patients/<int:patient_id>/lab-request")
@require_role("doctor")
def lab_request(user, patient_id):
    """Print-ready richiesta di laboratorio for the selected analyses."""
    from flask import request as req

    from models import Patient

    patient = db.session.get(Patient, patient_id)
    if not patient:
        return jsonify({"error": "Paziente non trovato"}), 404

    codes = [c for c in (req.args.get("tests", "").split(",")) if c]
    tests = [(c, label) for c, label in LAB_TESTS if c in codes]
    if not tests:
        return jsonify({"error": "Nessuna analisi selezionata"}), 400

    doctor = patient.assigned_doctor
    ref_by_code = {code: METRIC_CODES.get(code, ("", "", "—"))[2] for code, _ in tests}
    rows = "".join(
        f"<tr><td>{i + 1}</td><td>{label}</td><td>{ref_by_code[code]}</td></tr>"
        for i, (code, label) in enumerate(tests)
    )
    html = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<title>Richiesta di laboratorio — {patient.full_name}</title>
<style>
  body {{ font-family: Georgia, 'Times New Roman', serif; color: #17222d; margin: 48px; }}
  header {{ display: flex; justify-content: space-between; align-items: baseline;
           border-bottom: 3px solid #0c6e64; padding-bottom: 12px; }}
  header h1 {{ font-size: 20px; margin: 0; color: #0c6e64; }}
  header .date {{ font-size: 13px; color: #405060; }}
  .patient {{ margin: 28px 0; font-size: 15px; }}
  .patient b {{ font-size: 17px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 15px; }}
  th, td {{ border: 1px solid #cbd3db; padding: 10px 12px; text-align: left; }}
  th {{ background: #e6f2f0; color: #0a5a52; text-transform: uppercase; font-size: 11px; letter-spacing: .06em; }}
  .note {{ margin-top: 28px; font-size: 13px; color: #405060; }}
  .signature {{ margin-top: 64px; display: flex; justify-content: space-between; font-size: 14px; }}
  .signature div {{ border-top: 1px solid #17222d; padding-top: 6px; width: 260px; text-align: center; }}
  footer {{ margin-top: 48px; font-size: 11px; color: #64748b; border-top: 1px solid #e3e7ec; padding-top: 8px; }}
  @media print {{ .no-print {{ display: none; }} }}
</style></head>
<body onload="window.print()">
<header><h1>Richiesta di esami di laboratorio</h1>
<span class="date">Health Platform — {__import__('datetime').date.today().strftime('%d/%m/%Y')}</span></header>
<div class="patient"><b>{patient.full_name}</b> — {patient.birth_date.strftime('%d/%m/%Y') if patient.birth_date else '—'}<br>
{patient.employer or ''}{(' · ' + patient.job_title) if patient.job_title else ''}<br>
Diagnosi: {patient.primary_diagnosis or '—'}</div>
<table><thead><tr><th>#</th><th>Analisi richiesta</th><th>Valori di riferimento</th></tr></thead>
<tbody>{rows}</tbody></table>
<p class="note">Presentarsi a digiuno da almeno 8 ore per gli esami su sangue. Portare con sé
la tessera sanitaria e questa richiesta.</p>
<div class="signature"><div>Il medico<br>{f'dott. {doctor.first_name} {doctor.last_name}' if doctor else ''}</div>
<div>Il lavoratore<br>{patient.full_name}</div></div>
<footer>Documento generato dalla piattaforma Health Platform. Dati protetti — trattamento
riservato ai fini sanitari (art. 13 Reg. UE 2016/679).</footer>
</body></html>"""
    return Response(html, mimetype="text/html")
