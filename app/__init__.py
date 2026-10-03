from flask import Flask
from sqlalchemy import inspect, text
from config import Config
from app.database.models import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    from app.routes.system import system_bp
    from app.routes.scans import scans_bp
    from app.routes.reports import reports_bp
    app.register_blueprint(system_bp)
    app.register_blueprint(scans_bp)
    app.register_blueprint(reports_bp)
    with app.app_context():
        db.create_all()
        _upgrade_review_columns()
    return app


def _upgrade_review_columns():
    """Small additive migration for existing local WinDrive MySQL databases."""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    additions = {
        "scan_sessions": {"crash_evidence": "TEXT NULL"},
    }
    with db.engine.begin() as connection:
        for table, columns in additions.items():
            if table not in tables:
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
