"""Authentication endpoints.

The SPA authenticates with the HttpOnly session cookie; the login response also
returns the CSRF token the client must echo in the `X-CSRF-TOKEN` header.
Bearer-header auth stays available for tests and server-to-server clients.
"""
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, decode_token, set_access_cookies, unset_jwt_cookies

import bcrypt
from extensions import db, limiter
from models import User
from api.helpers import require_auth, user_payload

bp = Blueprint("auth", __name__, url_prefix="/api")


@bp.post("/login")
@limiter.limit("10 per minute")
def login():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username or not password:
        return jsonify({"error": "Username e password obbligatori"}), 400

    user = db.session.query(User).filter_by(username=username).first()
    # bcrypt only hashes the first 72 bytes and pyca-bcrypt raises beyond that:
    # an over-long password can never match a stored hash, so reject it as any
    # other wrong credential instead of a 500.
    if not user or len(password) > 72 or not bcrypt.checkpw(
        password.encode("utf-8"), user.password_hash.encode("utf-8")
    ):
        return jsonify({"error": "Credenziali non valide"}), 401

    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    csrf_token = decode_token(token)["csrf"]
    payload = {
        "user": user_payload(user),
        "csrf_token": csrf_token,
    }
    # extra credential for cookie-less environments; disabled in production
    if current_app.config["AUTH_ISSUE_FALLBACK_TOKEN"]:
        payload["token"] = token
    response = jsonify(payload)
    unset_jwt_cookies(response)  # clear any stale session first
    from flask_jwt_extended import set_access_cookies
    set_access_cookies(response, token)
    return response


@bp.post("/logout")
@require_auth
def logout(user):
    response = jsonify({"ok": True})
    unset_jwt_cookies(response)
    return response


@bp.get("/me")
@require_auth
def me(user):
    from flask_jwt_extended import get_jwt
    payload = user_payload(user)
    payload["csrf_token"] = get_jwt()["csrf"]
    return jsonify(payload)
