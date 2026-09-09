"""Health Platform — Flask application factory and entrypoint."""
import os

from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from extensions import db, jwt, limiter
from api import register_blueprints
from api.helpers import register_error_handlers


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app, supports_credentials=True, origins=app.config["CORS_ORIGINS"])
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    register_blueprints(app)
    register_error_handlers(app)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "health-platform-backend"})

    with app.app_context():
        # Dev/provisioning convenience: idempotent schema creation (new tables
        # only — column changes go through Alembic). Controlled environments
        # set DB_AUTO_CREATE=0 and manage the schema with backend/migrations.
        from sqlalchemy import inspect

        if os.getenv("DB_AUTO_CREATE", "1") == "1":
            db.create_all()
        if inspect(db.engine).has_table("anamnesis_questions"):
            from services import anamnesis as ana_service
            ana_service.ensure_catalogue(db.session)
            ana_service.load_answer_meta(db.session)
            if inspect(db.engine).has_table("pathway_templates"):
                from services import pathways as pathway_service
                pathway_service.ensure_templates(db.session)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
