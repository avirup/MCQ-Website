""" from flask import Blueprint

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/admin/login", methods=["GET", "POST"])
def login():
    return "Admin login page" """



# routes/auth.py
from __future__ import annotations
import os
from functools import wraps

import bcrypt
from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort,
)
import click
from flask.cli import with_appcontext

auth_bp = Blueprint("auth", __name__)


# ---------- Helpers ----------

def _admin_secret_path() -> str:
    path = current_app.config.get("ADMIN_SECRET_FILE")
    if not path:
        raise RuntimeError("ADMIN_SECRET_FILE is not configured.")
    return path


def _read_hashed_password() -> bytes | None:
    """Read bcrypt hash stored on disk. Returns bytes or None if missing."""
    try:
        with open(_admin_secret_path(), "rb") as f:
            data = f.read().strip()
            return data if data else None
    except FileNotFoundError:
        return None


def _verify_password(plaintext: str) -> bool:
    hashed = _read_hashed_password()
    if not hashed:
        # No admin password has been set yet
        return False
    try:
        return bcrypt.checkpw(plaintext.encode("utf-8"), hashed)
    except ValueError:
        # Hash on disk is malformed
        return False


# ---------- Decorator ----------

def admin_required(view_func):
    """Require admin session for protected routes."""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if session.get("is_admin") is True:
            return view_func(*args, **kwargs)
        # Not logged in → redirect to login with ?next=<path>
        next_url = request.full_path if request.query_string else request.path
        return redirect(url_for("auth.login", next=next_url))
    return wrapper


# ---------- Routes ----------

@auth_bp.route("/admin/login", methods=["GET", "POST"])
def login():
    # If already logged in, go to admin home
    if session.get("is_admin") is True:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        password = request.form.get("password", "")
        next_url = request.args.get("next") or request.form.get("next") or url_for("admin.dashboard")

        if not _read_hashed_password():
            flash("Admin password is not set. Ask the maintainer to run: flask create-admin", "error")
            return render_template("auth/login.html", next=next_url), 400

        if _verify_password(password):
            session["is_admin"] = True
            flash("Logged in successfully.", "success")
            return redirect(next_url)
        else:
            flash("Invalid password.", "error")

    # GET or failed POST
    next_url = request.args.get("next", url_for("admin.dashboard"))
    return render_template("auth/login.html", next=next_url)


@auth_bp.route("/admin/logout", methods=["POST"])
def logout():
    if session.get("is_admin"):
        session.pop("is_admin", None)
        flash("Logged out.", "success")
    return redirect(url_for("auth.login"))


# ---------- CLI: create-admin ----------

@click.command("create-admin")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="The admin password to hash and write to ADMIN_SECRET_FILE.",
)
@with_appcontext
def create_admin_command(password: str):
    """
    Hash the given password with bcrypt and store it in ADMIN_SECRET_FILE.
    The file is created if it does not exist.
    """
    if not password or len(password) < 6:
        raise click.ClickException("Password must be at least 6 characters.")

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))

    path = _admin_secret_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Write the raw hash bytes; bcrypt.hashpw returns bytes starting with b"$2b$..."
    with open(path, "wb") as f:
        f.write(hashed)

    # Tighten permissions on POSIX systems (best-effort; Windows will ignore)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass

    click.echo(f"Wrote bcrypt hash to: {path}")
