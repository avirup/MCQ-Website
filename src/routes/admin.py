# routes/admin.py
from flask import Blueprint, render_template
from routes.auth import admin_required   # 👈 import the decorator

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/")
@admin_required   # 👈 protect this route
def dashboard():
    return render_template("admin/dashboard.html")


@admin_bp.route("/subjects")
@admin_required
def subjects():
    return "Subjects management (coming soon)"

@admin_bp.route("/questions")
@admin_required
def questions():
    return "Questions management (coming soon)"