"""API blueprint registration."""
from api import anamnesis, auth, care, chat, doctor, education, medications, patients, pathways, privacy, symptoms, triage, wellbeing


def register_blueprints(app):
    app.register_blueprint(auth.bp)
    app.register_blueprint(patients.bp)
    app.register_blueprint(anamnesis.bp)
    app.register_blueprint(care.bp)
    app.register_blueprint(wellbeing.bp)
    app.register_blueprint(triage.bp)
    app.register_blueprint(chat.bp)
    app.register_blueprint(doctor.bp)
    app.register_blueprint(pathways.bp)
    app.register_blueprint(medications.bp)
    app.register_blueprint(privacy.bp)
    app.register_blueprint(symptoms.bp)
    app.register_blueprint(education.bp)
