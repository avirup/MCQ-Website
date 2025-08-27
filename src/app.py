from flask import Flask
from config import Config
from extensions import db, migrate, session
from routes.auth import auth_bp, create_admin_command
from routes.admin import admin_bp
from routes.student import student_bp
from routes.api import api_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    session.init_app(app)

    # 🔴 IMPORTANT: import models so Alembic “sees” them
    with app.app_context():
        import models  # noqa: F401  (ensure Subject, Question, Test, TestQuestion, TestResponse get registered)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(student_bp)
    app.register_blueprint(api_bp, url_prefix="/api")


    app.cli.add_command(create_admin_command)

    return app
