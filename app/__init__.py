from flask import Flask
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
    return app
