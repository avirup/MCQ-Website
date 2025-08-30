from flask import Flask, send_from_directory
from config import Config
from extensions import db, migrate, session, csrf
from routes.auth import auth_bp, create_admin_command
from routes.admin import admin_bp
from routes.student import student_bp
from routes.api import api_bp
from routes.uploads import uploads_bp
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    session.init_app(app)
    csrf.init_app(app)

    # 🔴 IMPORTANT: import models so Alembic “sees” them
    with app.app_context():
        import models  # noqa: F401  (ensure Subject, Question, Test, TestQuestion, TestResponse get registered)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(student_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(uploads_bp)

    # ---- DEV ONLY: serve uploads from disk ----
    # Files are stored in Config.UPLOAD_DIR (e.g., /.../uploads/questions)
    # DB holds relative paths like "<subject_id>/<uuid>.png"
    """ @app.route("/uploads/<path:relpath>")
    def uploads(relpath):
        base_dir = app.config["UPLOAD_DIR"]  # points to ".../uploads/questions"
        return send_from_directory(base_dir, relpath, as_attachment=False) """



    app.cli.add_command(create_admin_command)

    return app
