# routes/uploads.py
from flask import Blueprint, current_app, send_from_directory
from pathlib import Path

uploads_bp = Blueprint("uploads", __name__)

@uploads_bp.route("/uploads/<path:relpath>")
def serve_upload(relpath):
    base_dir = Path(current_app.config["UPLOAD_DIR"]).resolve()
    return send_from_directory(base_dir, relpath)
