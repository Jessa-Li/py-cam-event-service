"""Authentication: POST /auth/login + a `flask seed-admin` CLI command.

Login is the only unauthenticated entry point that mints tokens. Camera-side
credentials are out of scope here — in production cameras would receive a
provisioning token during pairing, not a username/password.
"""
import os

import click
from flask import Blueprint, current_app, jsonify, request
from flask.cli import with_appcontext
from flask_jwt_extended import create_access_token, get_jwt, jwt_required

from .errors import AppError
from .extensions import db, limiter
from .models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
# Tight per-IP limit on the only unauthenticated mint point — brute-forcing
# passwords is the obvious attack here. Keyed on IP (not identity) because
# pre-login there is no identity yet.
@limiter.limit("5 per minute", key_func=lambda: request.remote_addr)
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        raise AppError("email and password are required", code="validation")

    user = User.query.filter_by(email=email).first()
    # Same error for unknown user vs. bad password — don't leak which one.
    if user is None or not user.check_password(password):
        raise AppError(
            "invalid credentials", status_code=401, code="invalid_credentials"
        )

    expires = current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    token = create_access_token(
        identity=str(user.id),
        additional_claims={"is_admin": user.is_admin, "email": user.email},
    )
    current_app.logger.info(
        "login", extra={"ctx_user_id": user.id, "ctx_is_admin": user.is_admin}
    )
    return jsonify(
        access_token=token,
        token_type="Bearer",
        expires_in=int(expires.total_seconds()),
        user=user.to_dict(),
    )


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Echoes the claims on the current token. Useful for the client to
    verify a stored token is still valid without making a real API call."""
    claims = get_jwt()
    return jsonify(
        user_id=claims.get("sub"),
        email=claims.get("email"),
        is_admin=claims.get("is_admin", False),
        expires_at=claims.get("exp"),
    )


def admin_required(fn):
    """Route decorator: 401 without a token, 403 without is_admin=true."""
    from functools import wraps

    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if not get_jwt().get("is_admin"):
            raise AppError("admin required", status_code=403, code="forbidden")
        return fn(*args, **kwargs)

    return wrapper


@click.command("seed-admin")
@with_appcontext
def seed_admin_command():
    """Create or reset the admin user from ADMIN_EMAIL / ADMIN_PASSWORD env vars.

    Idempotent — safe to run on every container start. If the user exists,
    the password is reset to whatever ADMIN_PASSWORD currently holds.
    """
    email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    password = os.environ.get("ADMIN_PASSWORD", "admin")

    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(email=email, is_admin=True)
        user.set_password(password)
        db.session.add(user)
        click.echo(f"created admin {email}")
    else:
        user.set_password(password)
        user.is_admin = True
        click.echo(f"reset admin password for {email}")
    db.session.commit()


def register_cli(app):
    app.cli.add_command(seed_admin_command)
